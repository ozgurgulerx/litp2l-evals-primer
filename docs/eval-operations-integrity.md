# Operating the evaluation service and protecting integrity

An evaluation suite is itself a production system. It has retries, quotas, caches, schemas, partial artifacts, access controls, and failure modes that can change the reported score. Operate software health and model capability as separate but joined evidence streams.

## Evaluation-service architecture

```text
registered manifest
        │
        ▼
case × arm × trial scheduler ── quota and budget policy
        │
        ▼
isolated environment runner ─── trace + usage + state receipts
        │
        ▼
deterministic graders ────────── hard failures and localization
        │
        ▼
qualified semantic graders ──── criterion scores and abstentions
        │
        ▼
immutable artifact store ─────── raw records + hashes
        │
        ▼
paired analysis ──────────────── intervals, slices, uncertainty
        │
        ▼
evidence receipt ─────────────── authority ceiling and expiry
```

## Resumable runs

A run fragment is keyed by `run_id`, `case_id`, and `trial_index` and bound to one manifest hash. Resuming with an identical fragment is idempotent. Resuming with different content for the same key is a conflict: quarantine it and stop aggregation.

`resume_run` in `cx_eval_lab/advanced.py` demonstrates the merge rule over supplied fragments without mutable global state. It is not a scheduler, persistent store, or trace-producing runner. A production store also needs atomic writes, checksums, lifecycle states, access control, retention, and deletion enforcement.

### Run lifecycle

| State | Meaning | Permitted transition |
| --- | --- | --- |
| Registered | Manifest accepted; no trial authority | Schedule |
| Running | Some fragments complete | Resume or cancel |
| Partial | Interruption or quota prevented completion | Resume under the same manifest |
| Complete | Every registered key has one valid fragment | Grade and aggregate |
| Quarantined | Conflict, corruption, or provenance failure | Investigate; never aggregate silently |
| Expired | Relevant system or evaluator changed | Re-run under a new manifest |

Retries need categories. Infrastructure retries that reproduce the same logical trial stay attached to that trial. Model retries are additional stochastic attempts and must not replace failures. Selectively retrying only failed candidates biases the result.

## Quotas, flakiness, and cost attribution

Record provider, model, request identifiers, attempt number, retry reason, rate-limit delay, tool calls, judge calls, storage, and human review. Distinguish:

- **software health:** runner crashed, quota exhausted, artifact corrupt, tool sandbox unavailable;
- **model capability:** wrong action, unsafe claim, unsuccessful recovery;
- **environment validity:** impossible task, stale fixture, nondeterministic dependency;
- **evaluator health:** parser failure, judge abstention, conflicting graders.

A flaky task is not automatically excluded. Estimate flake rate using a reference implementation and environment-only repeats, repair deterministic infrastructure faults, and retain exclusions with reasons. LangChain's [Deep Agents evaluation account](https://www.langchain.com/blog/how-we-build-evals-for-deep-agents) is a useful reference for separating software tests from model-behaviour evaluations.

Cost attribution should include candidate, baseline, tools, retrieval, simulator, graders, human review, storage, and retries according to a registered accounting policy. The current OpenAI adapter records response identifiers, SDK token usage, and cost only when explicit token rates are registered. It does not yet claim full task cost.

## Executed campaign: reserve before judging

The [retained judge-campaign study](assets/judge-campaign-study-v1.json) contains four actual deterministic refund-agent executions, their mock-world tool traces, paired artifacts, scripted judge evidence, a SQLite ledger snapshot and a recomputable cost breakdown. No live model or paid call is involved. Agent latency and price use the explicitly synthetic measurement profile; judge outcomes and calibration counts are fixtures, not empirical qualification.

Its registered judge allowance is **1,000 micro-USD**, with **600 micro-USD reserved before each invocation**. One micro-USD is $0.000001. The first scripted judge returns a 360-micro-USD estimate; the second simulates a timeout with unknown cost.

| Trial in execution order | Judge dispatch | Known judge estimate | Reservation still held | Campaign occupancy afterward |
| --- | --- | --- | --- | --- |
| Baseline, repetition 0 | Completed fixture | 360 | 0 | 360 |
| Candidate, repetition 0 | Timeout fixture | Unknown | 600 | 960 |
| Baseline, repetition 1 | Denied before dispatch | No new charge | No new reservation | 960 |
| Candidate, repetition 1 | Denied before dispatch | No new charge | No new reservation | 960 |

The third request would require `960 + 600 = 1,560`, above the 1,000 allowance. The system refuses to dispatch it. It does not set the timeout's cost to zero to make room.

```bash
uv run --extra openai python -m unittest \
  tests.test_campaign_budget tests.test_budgeted_judge tests.test_campaign_study -v
uv run python -m cx_eval_lab.campaign_study \
  --output /tmp/primer-judge-campaign-my-first-run.json
```

Choose a fresh output path on another run. The CLI refuses to overwrite an existing report. It uses a temporary local database during execution, then retains the full ledger rows in the report; this teaching command is not a long-running service. The ledger API itself can reopen an operator-owned database across processes and restarts.

### Kata 38: is an unknown bill free budget?

**Know:** an admission allowance, a reservation, an observed estimate, and a provider invoice are different objects. The implemented occupancy rule is:

```text
occupied = finalized known estimates
         + reservations for pending or unknown-cost invocations
admit only if occupied + next reservation <= registered allowance
```

**Task:** compute occupancy after the first two calls. Then change the first observed estimate to 700, exceeding its 600 reservation. Should the system clamp it, keep admitting calls because the total is below 1,000, or stop?

??? success "Solution: retain uncertainty; never clamp an overrun"
    After the first call, only 360 is occupied; 240 of its reservation becomes available. After the second, occupancy is 960. The known judge subtotal remains 360, not 960: the held 600 is neither an observed charge nor proof of a maximum provider invoice.

    A reported estimate of 700 must be recorded as 700. `CampaignLedger.finalize` marks a reservation overrun and latches subsequent admission closed, even if some numerical allowance remains. The per-call bound assumption has failed. Already admitted calls may still complete and add expenditure; stopping new admission cannot undo them.

    `usd_to_micro` rounds each estimate upward using exact integer arithmetic on its decimal representation. A tiny positive charge cannot round to zero. Tests deliberately reduce the caller's Decimal precision and still obtain 1,235 micro-USD from $0.0012345. Invalid or nonfinite values are not valid zero-cost settlements.

**Extend:** the four-process test releases four workers against room for one reservation. Exactly one is admitted. `BEGIN IMMEDIATE` puts the occupancy check and insertion in the same SQLite transaction; a separate check followed by an unprotected insert would permit over-allocation.

**Interview answer:** “I reserve before dispatch, preserve unknown costs, and reconcile actual evidence rather than guessing zero. An overrun invalidates the reservation assumption and stops further admission. An estimate-based local allowance is not an invoice guarantee.”

### Kata 39: retry after the worker disappears

A worker commits a reservation, then exits before persisting a judgment. You cannot tell from the ledger whether a provider accepted the request.

**Task:** reopen the database and reserve the same invocation again. Next reuse that ID with changed evidence. Finally finalize an existing invocation twice, once with identical evidence and once with a different cost.

??? success "Solution: idempotency is not permission to resend"
    The existing invocation is not admitted again. Its reservation remains occupied. Changed request or judge-configuration hashes under the same ID are conflicts. Identical finalization returns the existing receipt; different finalization cannot overwrite it. The subprocess regression exits with `os._exit` after reservation and verifies durability and duplicate-admission rejection from the parent. Separate tests exercise changed identities and conflicting finalization.

    The paired runner derives evaluator-owned IDs from manifest, case, repetition and arm. Identical text in two arms therefore has distinct IDs. The wrapper removes this operational ID before calling the inner judge; it never adds arm or repetition labels to provider-visible evidence.

    `BudgetedSemanticJudge` preserves provider audit separately from its campaign receipt. If finalization cannot be confirmed, it abstains and retains the uncommitted judgment diagnostically. Inspect the durable ledger: a commit may have succeeded before an error became visible. The audit does not assert that every error necessarily left an uncommitted reservation. Malformed numeric evidence is preserved as a diagnostic, not passed onward as a usable measurement.

**Limits:** this is suppression of duplicate **judge dispatch**, not provider-side exactly-once execution. Ordinary standalone grading generates fresh IDs unless the caller supplies a stable one. Re-running a paired experiment still executes the application agents before judge admission: the entire runner is not resumable and application charges are not capped by this wrapper. No automated reconciliation or release of ambiguous reservations is implemented; operator-reviewed reconciliation needs a separately retained evidence trail.

**Deadline exercise:** admission at the exact registered deadline is denied. Previously admitted work may finish afterward and its cost is retained. A backward clock jump latches admission closed. Tests use an injected fixture clock; these are admission semantics, not proof of server cancellation or real-time deadline guarantees.

**Interview answer:** “I distinguish the logical trial, invocation and provider request. After an ambiguous crash I retain the reservation and reconcile evidence; I do not create a new invocation ID merely to bypass the stop.”

### Kata 40: the cost report is incomplete—and so is the comparison

Each of the four application-agent trials has an invented $0.08 measurement profile. One judge estimate is $0.00036, one is unknown, and two judges were never dispatched.

**Task:** calculate the known subtotal and the complete selected estimate. Can the team use the resulting baseline/candidate success rates to claim a better agent?

??? success "Solution: keep known, unknown, and not dispatched separate"
    Application estimates sum to 320,000 micro-USD. The known judge estimate is 360. The known subtotal is 320,360 micro-USD, or $0.32036. There is one unknown component, so `complete_selected_estimate_micro_usd` is null. The two denied invocations add no **new** judge dispatch cost in this packet; earlier ambiguous attempts can still consume money and remain represented in the ledger.

    `summarize_packet_costs` first validates retained artifacts and replays grades with caller-supplied calibration trust. It does not authenticate provider billing or treat the packet's synthetic calibration hash as production authority. It leaves the application's existing `cost_usd` field unchanged and reports evaluation overhead separately.

    These totals cover only selected agent/judge estimates for new dispatches in this packet. They exclude prior attempts, tool services, infrastructure, storage and human review. Never add reservation occupancy to the known subtotal as if both were observed charges, and never sum retry packets without reconciling invocation identities.

    This fixed execution order and exhausted budget produce missing judgments that depend on scheduling position. The two agents are the same deterministic implementation. The study demonstrates admission and accounting, not superiority or non-inferiority. A real comparison must pre-register budget allocation, pair completion, ordering/counterbalancing, retries and missingness handling; preserve incomplete pairs and withhold unsupported promotion.

**Extend:** `run_study(unknown_second=False, budget_micro_usd=2000)` is a separate, explicitly larger-allowance control: all four scripted judge estimates are known, yielding 321,440 micro-USD for the selected total. This is an accounting counterexample, not a matched-budget model experiment.

**Interview answer:** “A known subtotal is not a complete cost. Budget stops are software-health outcomes that can bias model comparisons. I report them, preserve incomplete pairs, and do not convert missing judgment into evidence that one model is worse.”

### What this control does not authorize

The ledger enforces atomic local admission against operator-declared estimated-cost reservations and a call-count/deadline policy. It assumes an operator-owned local filesystem and trusted clock/client; it is not a distributed coordinator or protection against a privileged actor replacing the database. Snapshots and hashes aid inspection, not authentication.

It neither proves that the per-call reservation bounds a real bill nor controls charges from callers that bypass the wrapper. Real operation still needs validated pricing bounds, provider-side quotas where available, agent/tool budgets, reconciliation, cancellation semantics, protected storage and authenticated registry admission. Campaign receipts are retained evidence; the production release gate does not yet consume them as an independent prerequisite. No receipt here authorizes deployment or exposure expansion.

## Model-versus-harness factorial experiment

Leaderboards often attribute a system score to the model even though tools, budgets, context policy, and orchestration materially affect it. Run a factorial comparison:

1. Hold model fixed and vary harness.
2. Hold harness fixed and vary model.
3. Use the same cases, trial pairs, budgets, and graders.
4. Estimate model, harness, and interaction effects.

The scorer's four-cell hand-authored fixture is:

| Model | Harness 1 | Harness 2 |
| --- | ---: | ---: |
| A | 0.70 | 0.80 |
| B | 0.75 | 0.85 |

Average model B minus A is `+0.05`; average harness 2 minus 1 is `+0.10`. In this synthetic fixture, the harness effect is twice the model effect. That does not prove the same relationship elsewhere; it demonstrates the attribution calculation and the evidence the manifest must pin.

Add cost and latency to every cell. If the design is incomplete—for example model B never ran on harness 1—do not infer separate effects from a confounded comparison.

## Evaluation integrity is a runtime boundary

Register what the candidate may access:

| Information surface | Example policy |
| --- | --- |
| Repository history | Allowed for realistic coding tasks, prohibited for a sealed patch-reconstruction test |
| Internet/search | Allowed when the product has it; scope and timestamp recorded |
| Known answers or fixes | Prohibited unless the task explicitly tests reproduction |
| Grader code | Read-only or hidden according to threat model |
| Sealed labels | Inaccessible to candidate and optimisation loop |
| Scoring state | Fresh or content-addressed; candidate cannot modify it |

Cursor's [benchmark reward-hacking investigation](https://cursor.com/blog/reward-hacking-coding-benchmarks) illustrates why permitted information access must be explicit. The lesson is not that browsing or repository history is universally forbidden; it is that the benchmark claim must match the information boundary.

### Integrity mutants

- Mount a known solution artifact into the candidate environment.
- Let the candidate edit the grader or tests.
- Reuse a contaminated cache keyed without prompt or code version.
- Expose sealed labels through trace metadata.
- Drop failed rows before aggregation.
- Retry candidate failures but not baseline failures.
- Change the judge prompt after seeing the candidate outputs.

`evaluate_integrity` rejects any contaminated run regardless of score improvement.

## Optimising the evaluator and agent together

Keep three evidence channels:

1. development judge used for iteration;
2. independent executable checks;
3. independent human or differently constructed semantic verification.

The synthetic divergence experiment raises the development-judge score by `+0.12` while independent verification falls by `−0.08`. The candidate is rejected. Versioning and sealed data reduce risk, but the decisive lesson is empirical: show the divergence and require independent evidence rather than assuming the optimisation judge remains valid.

## Simulator qualification and deployment backtesting

A simulator is another model. Before using it to predict a release:

- register outcome probabilities or rankings;
- freeze simulator, prompt, persona distribution, and tools;
- compare with overlapping human interactions;
- measure realism by failure-mode and ranking preservation, not fluency;
- inspect differential validity across language, risk, and task slices;
- compare pre-release predictions with mature post-release outcomes.

The executable scoring function computes decision accuracy and Brier score from supplied probabilities and outcomes. In the four-row hand-authored fixture, accuracy is `0.50` and Brier score is `0.375`; it demonstrates the calculation but does not qualify a simulator. OpenAI's [deployment-simulation work](https://openai.com/index/deployment-simulation/) provides a first-party operational comparison pattern. Its reported results do not establish transfer to this CX environment.

## Offline-to-live validity

For each release, preserve:

```yaml
offline_forecast:
  eligible_population: ...
  expected_resolution_delta: ...
  expected_human_minutes_delta: ...
  expected_hard_failures: ...
online_observation:
  shadow: ...
  canary: ...
  mature_outcome_window: ...
forecast_error:
  by_metric: ...
  by_slice: ...
suite_action:
  keep | recalibrate | constrain | retire
```

A release can fail because the agent changed, because traffic shifted, or because the offline suite stopped predicting customer outcomes. Treat forecast error as an evaluation-system metric.

## Evidence added in this chapter

- **Executable scorer/merge fixtures:** idempotent fragment merge with conflict rejection, factorial attribution, integrity checks, and simulator scoring.
- **Demonstrated fixture behavior:** hand-authored inputs expose separate model/harness effects, reject development-judge divergence, and reject declared contamination.
- **Artifact:** `advanced-protocols-v1.json`, containing fixture inputs and expected derived values rather than captured service traces.
- **Limitations:** no distributed worker pool, live quota exhaustion, persistent artifact store, or production simulator backtest was run.
- **Authority:** `lab_only`.

## Exercise: partial run after quota exhaustion

A 1,000-pair experiment stops after 730 candidate calls and 810 baseline calls. The team aggregates completed rows and reports the candidate as superior. What is wrong?

??? success "Answer"
    The registered pairs are incomplete and missingness may depend on arm, latency, or failure. Do not compare unpaired convenience subsets without a pre-registered missing-data method. Preserve partial fragments, resume the missing keys under the same manifest and retry policy, reject conflicts, and aggregate only after the completion contract is satisfied. Report quota failure as software-health evidence separately from model capability.
