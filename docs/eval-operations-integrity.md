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

`resume_run` in `cx_eval_lab/advanced.py` demonstrates this rule without mutable global state. A production store also needs atomic writes, checksums, lifecycle states, access control, retention, and deletion enforcement.

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

## Model-versus-harness factorial experiment

Leaderboards often attribute a system score to the model even though tools, budgets, context policy, and orchestration materially affect it. Run a factorial comparison:

1. Hold model fixed and vary harness.
2. Hold harness fixed and vary model.
3. Use the same cases, trial pairs, budgets, and graders.
4. Estimate model, harness, and interaction effects.

The executable four-cell example is:

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

The executable backtest computes decision accuracy and Brier score from registered probabilities. In the four-row synthetic example, accuracy is `0.50` and Brier score is `0.375`; a confident simulator can sound realistic while predicting poorly. OpenAI's [deployment-simulation work](https://openai.com/index/deployment-simulation/) provides a first-party operational comparison pattern. Its reported results do not establish transfer to this CX environment.

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

- **Executable operations:** idempotent resume with conflict rejection, factorial attribution, integrity evaluation, and simulator backtesting.
- **Observed synthetic results:** separate model and harness effects; development-judge improvement rejected by independent regression; contaminated scores rejected.
- **Artifact:** `advanced-protocols-v1.json`.
- **Limitations:** no distributed worker pool, live quota exhaustion, persistent artifact store, or production simulator backtest was run.
- **Authority:** `lab_only`.

## Exercise: partial run after quota exhaustion

A 1,000-pair experiment stops after 730 candidate calls and 810 baseline calls. The team aggregates completed rows and reports the candidate as superior. What is wrong?

??? success "Answer"
    The registered pairs are incomplete and missingness may depend on arm, latency, or failure. Do not compare unpaired convenience subsets without a pre-registered missing-data method. Preserve partial fragments, resume the missing keys under the same manifest and retry policy, reject conflicts, and aggregate only after the completion contract is satisfied. Report quota failure as software-health evidence separately from model capability.
