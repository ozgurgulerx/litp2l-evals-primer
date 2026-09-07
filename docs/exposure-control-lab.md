# Exposure control: evidence must change routing

The candidate works in shadow, receives a canary cohort, and expands. A simulated service failure then prevents task completion, so its traffic is restricted. After two healthy windows and an explicit resume, it returns to canary. A wrong-order refund triggers rollback even though the ordinary outcome labels have not matured.

This sequence now runs against the primer's actual mock-agent implementations and independent order ledgers. The [retained packet](assets/exposure-control-v1.json) contains **280 routed synthetic requests and 349 agent executions**: 280 baseline executions and 69 candidate executions, including shadow and counterfactual evaluations. Every execution is local. No customer traffic, money, deployment credentials or live model was involved.

## The executed sequence

| Window | Starting stage / nominal candidate share | Declared intervention | Candidate-served requests out of 40 | Paired observations | Resulting stage |
| --- | --- | --- | ---: | ---: | --- |
| 1 | Shadow / 0% | Healthy | 0 | 40 | Canary / 5% |
| 2 | Canary / 5% | Healthy | 4 | 4 | Expanded / 25% |
| 3 | Expanded / 25% | Service unavailable | 13 | 13 | Restricted / 5% |
| 4 | Restricted / 5% | Healthy | 4 | 4 | Restricted / 5% |
| 5 | Restricted / 5% | Healthy + explicit resume | 4 | 4 | Canary / 5% |
| 6 | Canary / 5% | Wrong-order selection | 4 | 4 | Rolled back / 0% |
| 7 | Rolled back / 0% | Healthy + attempted resume | 0 | 0 | Rolled back / 0% |

The interventions are intentionally injected through one fixed test harness. They exercise the controller; they are not a measured history of one production model spontaneously changing behavior. Customer requests repeat a narrow synthetic scenario across separate mock worlds. These windows are not independent evidence of population reliability.

The router designates which result is served. Baseline and candidate execute in separate disposable ledgers, so a shadow candidate cannot alter the baseline world. Running both arms in clones provides counterfactual outcomes unavailable for the same real customer in ordinary production. Actual shadowing must isolate or suppress external effects and document how that changes behavior.

## The implemented contract

`cx_eval_lab/exposure_control.py` owns the immutable state and decisions. `cx_eval_lab/exposure_study.py` executes the agent arms, records routing and full artifacts, derives observations from their grades, and applies the controller.

| Control | Local rule | Boundary |
| --- | --- | --- |
| Identity | Candidate, baseline and exposure revision must match | Names in this study are trusted harness identifiers, not signed deployment attestations |
| Cohort | Stable customer hash; expansion preserves the earlier cohort | Nominal percentages are not exact small-sample counts or hard financial caps |
| Freshness | Router requires a clock; telemetry older than 30 simulation units routes to baseline | Clock and state distribution are trusted local inputs |
| Campaign expiry | No candidate routing at or after time 120 | Fresh results do not automatically renew the campaign |
| Maturity | Every submitted row must be mature and both outcomes present before quality-based progression | Maturity timestamps are artificial here, not observed seven-day follow-up outcomes |
| Cohort completeness | A pending window's identity, bounds, customer membership and maturity schedule are pinned | The collector must still establish complete membership before the first submission |
| Replay | Reject consumed windows, reused artifact references, overlap and wrong exposure revisions | Evidence authenticity and durable distributed deduplication are not implemented |
| Hard stop | Observed wrong-order commits trigger rollback before maturity and ordinary replay checks | The study recognizes incidents only when a completed batch is inspected |
| Quality restriction | Candidate pass rate below 90%, or paired point loss above 10 percentage points, restricts exposure | These are **illustrative policy thresholds**, not statistically qualified release tests |
| Guard band | A positive loss up to 10 points, while meeting the floor, holds rather than expands | A guard band does not control repeated-testing error |
| Recovery | Restricted state needs two healthy windows and explicit resume; it returns only to canary | Resume is a local simulation choice, not authenticated production approval |
| Rollback | Latched at baseline; later green results cannot reactivate this state | Returning to baseline does not undo previously completed side effects |

The minimum of two paired observations is deliberately small to exercise routing with forty synthetic requests. It is **not a sample-size recommendation**. Use the [statistical method study](statistical-method-study.md) and [evidence spine](evidence-spine.md) to see why sample counts and point differences cannot establish non-inferiority. Neither this controller nor the existing `lab_only` receipts grant production authority. `ExposureDecision` fixes `deployment_authorized=False` and does not accept a caller override.

The retained v1 sequence above remains unbudgeted. [Kata 95](#kata-95-two-refunds-is-not-five-percent) now injects an optional shared action/currency budget through the same execution path. It is a separate in-process experiment, not a retroactive property of the original packet.

## Kata 24: five percent is not a hard cap

**Know:** stable assignment, nominal allocation and actual exposure answer different questions.

**Task:** before running the study, predict whether exactly two of forty customers must receive a nominal 5% canary. Check whether every member of the 5% cohort remains included at 25%.

```bash
uv run python -m cx_eval_lab.exposure_study \
  --output /tmp/primer-exposure-my-first-run.json
uv run python -m unittest tests.test_exposure_control -v
```

Choose a new output path for another run. The command refuses overwrite and makes no network or model calls.

??? success "Solution: inspect actual routing, not only the configured weight"
    In this fixed synthetic population, four customers fall into the nominal 5% bucket and thirteen into the 25% bucket. Stable hashing does not promise an exact fraction in a small population. Unequal customer activity can make the request fraction differ further from the customer fraction.

    The hash uses customer and candidate identity; the threshold increases without rerandomizing the cohort. `test_shadow_canary_expansion_and_stable_nested_cohorts` verifies repeatability and nesting. Every request in the retained study records its selected arm and the actual arm executions.

    A production exposure budget needs more than a percentage: cap distinct affected customers, request count, consequential writes, monetary value, concurrent actions and elapsed time as appropriate. Add those limits at the action/traffic boundary rather than assuming a load-balancer weight enforces them. The retained v1 study implements the campaign time limit, but not those other hard caps. Kata 95 adds optional in-process refund count/currency caps; customer, request and in-flight concurrency caps remain unimplemented.

**Interview answer:** “I record assignment and realized exposure separately. Sticky cohorts help interpretation, but a nominal percentage is not a hard cap on customers, requests or financial consequences.”

## Kata 25: missing labels cannot disappear from the denominator

A window contains two passing rows and one missing mature label. The controller holds. The collector resubmits the same window with only the two passing rows.

**Task:** predict the result. Then keep all rows but fill the missing label. Finally stop delivering telemetry altogether.

??? success "Solution: pin the cohort and expire the routing permission"
    Dropping the row returns `pending_cohort_mismatch`; it cannot turn a hold into an expansion. The state binds the pending cohort before returning a maturity or missing-label hold. The same complete cohort can be assessed when its missing outcome arrives. A different window cannot silently skip that unresolved cohort.

    No controller callback occurs if telemetry stops completely. Therefore `route(..., now=...)` independently checks freshness and sends new requests to baseline after the deadline. It also enforces the fixed campaign expiry even when telemetry stays healthy. Tests cover both failure paths.

    Pending membership does not prove the first submission was complete. An external collector still needs a registered enrollment manifest and reconciliation against actual routed requests. Outcome revisions need auditable lineage. A content hash is not proof that an operator reported every failure.

    A fixed cohort below the toy minimum remains held; it is not silently padded with new customers. Re-registering a study or replacing expired evidence requires an explicit new campaign process, which this local state machine does not implement.

**Extend:** add a delayed repeat-contact failure, not merely a missing Boolean. Explain why pending outcomes cannot be treated as successes and why success-conditioned survey response is not random missingness.

**Interview answer:** “I freeze the enrolled cohort, preserve missingness and label maturity, and reconcile it with routing. A deadline must be enforced by the serving path because a stalled controller cannot issue its own stop instruction.”

## Kata 26: rollback is not containment or repair

Window 6 contains four wrong-order commits. Its ordinary labels are scheduled to mature fifty simulation units later. The next window routes entirely to baseline.

**Predict:** how many wrong-order commits occurred before rollback? Did rollback reverse any of them?

??? success "Solution: four effects remain to be reconciled"
    All four committed before the batch was evaluated. The controller immediately rolls back **when it receives that batch**, without waiting for ordinary label maturity. It does not interrupt the batch after the first bad action, cancel in-flight tasks or reverse a refund.

    A hard-stop policy is not proof of timely containment. A production implementation needs an independent event-driven stop path, action-boundary enforcement, propagation to queued/delegated work and an incident reconciliation procedure. Measure detection time, interruption time and completed effects before containment; do not report only that the final stage says “rolled back.”

    The unit tests also accept a severe incident report from an older exposure revision as a stop signal. Rejecting it as a stale quality window must not hide a newly learned consequential failure. Identity still has to match the candidate/baseline campaign.

**Extend:** connect the affected order IDs to the [process-recovery study](process-recovery-study.md). Distinguish safe retry, compensation, refund reconciliation and customer notification. None is equivalent to sending future traffic to an older model.

**Interview answer:** “Rollback controls future exposure. Containment stops active work, and remediation deals with effects already committed. I measure and test all three rather than use rollback as a synonym for recovery.”

## Kata 27: recovery needs stronger evidence than a single green window

The candidate fails at expanded exposure, improves in the next window, and asks to expand again. Separately, imagine both baseline and candidate fail every task: their paired difference is zero.

**Task:** explain why neither observation is enough to expand. Test an explicit resume before and after the required healthy-window count. Try it after a hard rollback.

??? success "Solution: absolute quality, hysteresis and a latched stop"
    The controller evaluates the candidate's absolute floor as well as its paired point difference. Matching a failing baseline does not establish acceptable quality. `test_equally_bad_arms_do_not_earn_expansion` rejects that counterexample.

    Restriction preserves a smaller nominal cohort. One healthy window does not restore exposure; two healthy windows plus explicit resume return the candidate only to canary. Replayed windows cannot increment the healthy streak, and a new non-green window resets it. This reduces oscillation but does not establish statistical error control.

    Hard rollback is latched. A new campaign requires an explicit, separately reviewed initialization after investigation and requalification; a `resume=True` argument cannot revive the rolled-back state. The retained study's final window demonstrates that refusal.

**Interview answer:** “I separate absolute acceptability, relative regression and operational recovery. Hysteresis prevents flapping; it does not replace uncertainty estimates or confer authority to restart after a serious incident.”

## Connecting the lab to an application deployment

### Kata 95: two refunds is not five percent

**Predict:** run the existing healthy candidate at a nominal 5% canary, but allow only two served-candidate refunds and EUR 9,000 cents across the campaign. The selected order costs EUR 4,500 cents. Do baseline counterfactuals consume the allowance? What does the customer receive after the cap is exhausted?

Run from the repository root; no model or external payment service is called:

```python
from cx_eval_lab.action_budget import ActionBudget
from cx_eval_lab.exposure_control import ExposureState, transition
from cx_eval_lab.exposure_study import execute_window

budget = ActionBudget(2, {"EUR": 9000})
state = ExposureState("cx-simulation-v1", "baseline-v1", stage="canary",
                      percent=5, last_end=10)
window, artifacts, served = execute_window(state, 2, "healthy", action_budget=budget)
candidate = [row["candidate"] for row in artifacts if row["served"] == "candidate"]
completed = sum(row["task_completed"] for row in candidate)
denied = sum(row["denied_attempts"] for row in candidate)
snapshot = budget.snapshot()
decision = transition(state, window, now=20)
assert (served, completed, denied) == (4, 2, 2)
assert snapshot["charged_actions"] == 2
assert snapshot["charged_cents"] == {"EUR": 9000}
assert snapshot["remaining_actions"] == 0
assert sum(row["baseline"]["task_completed"] for row in artifacts) == 40
assert [row["output"]["claimed_outcome"] for row in candidate] == [
    "refunded", "refunded", "needs_review", "needs_review",
]
assert decision.state.stage == "restricted"
assert decision.deployment_authorized is False
print({"served": served, "completed": completed, "denied": denied,
       "charged_cents": snapshot["charged_cents"], "stage": decision.state.stage})
```

??? success "Solution: enforce effects and preserve unfinished work"
    Four of forty requests are selected, as in the fixed cohort example. Only two candidate refunds commit; the other two hit `budget_action_limit`. Forty baseline counterfactuals still complete in their isolated worlds without spending candidate allowance. Per-row `effect_scopes` distinguish baseline, shadow and served-candidate execution. EUR 9,000 cents is €90, not a price estimate or a currency-converted global budget.

    Inspect `candidate[i]["action_budget"]` for before/after accounting and each order's `execution_namespace`, events and final state. The shared budget's snapshot contains charges and denials. Repeated order/key strings in independent worlds do not deduplicate each other: the evaluator creates distinct namespaces. Exact replay within the original world consumes no additional allowance. Reconstructing a new world with an already-bound namespace fails closed rather than inventing historical effect evidence.

    The reference agent previously ignored a returned `blocked` status and falsely claimed a refund. It now accepts `committed` or `already_committed`, and inspects authoritative order state for any other returned status, just as it does after timeout. No recorded refund means the existing unconfirmed message and `needs_review`; a recorded commit can be reported even if its acknowledgement was ambiguous. These response-path tests do not replace independent grading of the resulting message and ledger.

    Completion among selected requests is `2/4`, not `2/2` after discarding denials. The unchanged illustrative controller calls this `illustrative_quality_regression` and restricts exposure. Its reason describes delivered outcomes under the capped policy, not proof of an intrinsic model-quality regression. Investigate the policy constraint separately; report unfinished work and review burden. Do not quietly remove denied cases or mint a fresh campaign allowance to improve the score.

**Boundary tests:** `uv run python -m unittest tests.test_action_budget tests.test_reference_denial -v` exercises concurrent attempts for the last unit, currency isolation, authorization failure, fault seams, timeout/replay, reset and ambiguous accounting. An exact replay is free; a new-key retry is a new effect. Consumed worlds cannot reset, and an unknown accounting/effect failure retains its reservation and latches further new effects rather than releasing possibly spent capacity.

**Limits:** the budget and effect state are in memory under one shared lock. They are not durable across interpreter loss, a distributed service, an authenticated campaign registry, an in-flight concurrency limit or protection against hostile Python code with process access. This snippet creates records in memory; Kata 96 adds a separately versioned retained packet. The historical unbudgeted v1 artifact is unchanged. Durable enforcement remains required follow-up work.

### Kata 96: a hash is not a replay

**Question:** someone changes a denied refund into a success and recomputes the report hash. What evidence lets a reviewer detect the change? Start with the [retained budgeted campaign](assets/budgeted-exposure-v1.json), not its summary alone.

The fixed local study executes three windows using one shared two-effect, EUR 9,000-cent budget. Each window registers forty requests. Baseline counterfactuals and shadow executions use isolated mock effects; only served candidate effects consume campaign allowance.

| Entering stage | Served candidate requests | Candidate completions | Cumulative charged effects | Cumulative budget denials |
| --- | ---: | ---: | ---: | ---: |
| Shadow | 0 | 40 shadow completions | 0 | 0 |
| Canary | 4 | 2 | 2 | 2 |
| Restricted | 4 | 0 | 2 | 6 |

Restriction does not replenish the budget. Forty baseline controls complete in each window. Shadow completions are not served successes and must not inflate the canary denominator.

Generate a fresh packet at a new path, then verify it in the same source/interpreter environment:

```sh
uv run python -m cx_eval_lab.budgeted_exposure_study --output /tmp/my-budgeted-campaign.json
uv run python -m cx_eval_lab.budgeted_exposure_study --verify /tmp/my-budgeted-campaign.json
```

The output command refuses an existing destination. The packet retains case records, messages, tool events, order ledgers, execution namespaces, scope labels, before/after budget balances, charges, denials, controller observations and decisions. Source and interpreter fingerprints bind the comparison environment.

??? success "Solution: compare complete executions, not self-consistent summaries"
    Verification first checks the current source/interpreter inventory and outer hash, then re-executes the fixed evaluator-owned program. It compares the complete normalized packet, including evidence and decisions. It does not run code, select an agent or accept policy configuration from the submitted packet. Changing a tool result, scope, charge or decision and recomputing the outer hash is insufficient: the fixed replay must agree too.

    Only registered per-trial `elapsed_ms` fields are normalized for replay, after requiring finite nonnegative numbers. The outer hash still covers their retained values. Timing measurements naturally vary between executions; this verification does not establish their truth or performance significance. Boolean substitutions for integer counts, missing records and extra fields are not equivalent JSON evidence.

    Try changing a denial to success in a copy and recomputing `report_hash` with `canonical_hash`. Verification should reject it. Then change only a valid elapsed time and recompute the hash: replay may accept that timing-only change. Explain why neither result authenticates who originally ran the experiment.

**Portability and authority:** exact replay requires the recorded source bytes and interpreter identity. A retained macOS packet may correctly fail verification on Linux or after a source change. Generate and verify a new packet there; do not rewrite the old inventory and call it reproduced. Hashes and local replay establish consistency with this fixed mock program, not signed provenance, human calibration, model quality, durable enforcement or production qualification. `deployment_authorized` remains false.

### Kata 97: the packet exists, but did CI verify it?

**Question:** a job uploads a JSON packet after running the campaign. Is that enough to claim its replay passed? No: generation, verification, retention and release authority are separate checks.

The conformance workflow now contains this required step:

```yaml
- name: Generate and replay a fresh budgeted exposure campaign
  shell: bash
  run: |
    uv run python -m cx_eval_lab.budgeted_exposure_study --output ci-evidence/budgeted-exposure.json
    uv run python -m cx_eval_lab.budgeted_exposure_study --verify ci-evidence/budgeted-exposure.json
```

Both commands use the runner's current source/interpreter identity. CI does not try to pass off the historical macOS artifact as a fresh Linux execution. The existing always-run upload step includes `ci-evidence/`, so available failure evidence is retained too. An uploaded file is not a passing verdict: inspect the generation and verification exit statuses and the job conclusion.

??? success "Solution: require the replay, retain the failure, withhold release authority"
    Remove the second command and run `uv run python -m unittest tests.test_budgeted_ci -v`. The structural regression must fail. It also rejects conditional skipping, `continue-on-error`, a different output/verify path or loss of the always-run evidence upload. Restore the command before continuing.

    Next, generate a packet locally, alter a charge and recompute its outer hash as in Kata 96. The verifier must exit nonzero. A CI workflow that masks that exit code, such as by appending `|| true`, no longer enforces replay. The exact-command regression rejects that wiring change; the study's semantic mutation tests independently check that altered evidence is refused.

    Passing these checks establishes local software conformance. The YAML configuration is not evidence that a cloud job ran, that branch protection requires it, or that an application was deployed. Before claiming enforcement, retain an actual run URL and revision, job conclusion, downloaded artifact and replay result, and separately inspect the repository's required-check configuration. Keep production authorization false until the application-specific qualification and deployment controls are satisfied.

**Interview checkpoint:** explain why a failed run can still have an uploaded artifact, why fresh same-runner replay avoids a portability mismatch, and why a required green software check cannot substitute for calibrated model evidence or a production release decision.

### Hard action budgets: implementation contract

**Status: first in-process boundary and retained replayable packet implemented; durable enforcement remains open.** A 5% cohort cannot enforce a two-refund cap. Nor can a post-return counter account safely for a tool that committed a refund and then timed out. Katas 95–96 join budget accounting to the effect boundary and retain replayable evidence while preserving the unbudgeted historical study. The design requirements below remain the contract for reviewing this implementation and its remaining extensions.

The existing path is `execute_window` → `run_case` → `MultiOrderWorld` → `RefundWorld._commit_refund`. The last function updates the authoritative mock refund keys and is also reached by the deliberately unsafe test seams. Enforcing only in `route`, the agent or the normal tool wrapper would leave other effect paths uncovered.

**Scope decision for the next study:** cap **served candidate refund effects**, across all windows of one campaign. Keep baseline counterfactual executions and shadow candidate executions in separate, explicitly labeled simulated-effect scopes. The current harness runs a baseline even for requests served by the candidate, and both arms can write to their separate mock ledgers. Sharing one budget blindly across all those executions would let baseline/shadow work consume the candidate's exposure allowance. This scoping decision does not make real shadowing effect-free; a real shadow path must independently prevent external writes.

| Implementation boundary | Required behavior | Regression evidence |
| --- | --- | --- |
| Campaign ownership | Create one evaluator-owned budget outside the window loop; pass it through the case/world constructors. Candidate code cannot select its accounting scope. Restriction, resume and world reset cannot restore capacity. | Different served customers, orders and windows compete for the same remaining allowance. Historical calls without a budget retain their original behavior. |
| Exact effect accounting | Limit total new refund effects and separate integer amounts per currency. Charge authoritative seed amounts/currencies, not untrusted requested values. No implicit FX conversion; an unregistered currency is denied. | Exact count and amount boundaries pass; the next new effect blocks. Invalid/negative/Boolean caps fail configuration. EUR spending cannot consume USD allowance. |
| Atomic single-process boundary | Serialize replay check, current action validation, cap check, consumption and state update under the shared boundary. A lock around the budget counter alone is insufficient if effect/replay checks remain outside it. Explicitly constrain this first integration to its in-process mock state. | Two synchronized attempts competing for the last unit yield only one new effect. Authorization failures consume nothing. Fault-injected new effects cannot bypass the budget. |
| Timeout and replay | A committed effect consumes allowance before an acknowledgement can be lost. Exact replay consumes nothing; a new key is a new attempted effect. An ambiguous failure must not free capacity without authoritative reconciliation. | Timeout-after-commit retains consumption; same-action replay works at exhaustion; new-key retry blocks. Inject a failure between accounting and effect completion to verify conservative handling or atomic rollback. |
| Execution identity | Use a trusted campaign/execution namespace plus operation identity. The namespace is stable across retries of the same execution but distinct for independent mock worlds. Bind order, amount and currency; changed parameters are not replay. | Identical `order-a` and key strings in independent worlds are not falsely deduplicated. Recreating/resetting a world does not authorize another effect under a consumed identity. |
| Outcome interpretation | Retain actual budget denials, completed effects and task outcomes separately. A budget-denied refund is unfinished work, not an agent success; do not silently drop it from the served cohort. | Report registered/routed requests, attempted actions, budget-denied actions, committed counts/amounts, resolution and review load. Separate intrinsic candidate-quality diagnostics from outcomes under the capped policy. |

**Proposed test sequence:** configure two new effects, USD 4,000 and EUR 4,500. Serve one eligible USD 4,000 request and one eligible EUR 4,500 request in distinct worlds; both exhaust their currency allowances and together exhaust the count. Exact retries add nothing. A third new request must be denied even if the cohort rule selects it. Reverse the order, run competing attempts, inject timeout-after-commit, and repeat after a simulated restriction/resume. These are expected results to test, not observations already obtained.

The campaign's allowance and consumption must survive whatever failure model the study claims. A shared Python lock cannot establish crash durability or multi-process enforcement. The existing [recovery worker](process-recovery-study.md) offers a separate durable integration point: its `issue_payment` function performs replay lookup, current approval validation and payment insertion under `BEGIN IMMEDIATE`. A durable extension must check/account budget in that same transaction, then test separate processes competing for capacity and kill-after-commit recovery. Do not join a durable budget to a separate in-memory effect and call the pair atomic.

Preserve old artifacts and publish a new budgeted study identity with policy, scope, execution namespaces, before/after balances, denials and source manifest. Re-grading must reconstruct those facts from retained evidence. Passing the budget controls would establish a bounded local enforcement property, not statistically qualified release evidence, a live-model result or production authorization. Concurrency caps on in-flight work, request/customer caps, authenticated updates and real-service reconciliation remain separate requirements.

Google's canary guidance connects limited exposure, evaluation and the release process; it also distinguishes canary behavior from service-wide averages. Use release-specific outcomes rather than allowing a large healthy baseline population to hide a small failing candidate cohort. [Google SRE Workbook: Canarying Releases](https://sre.google/workbook/canarying-releases/)

Argo Rollouts provides a concrete orchestration example: analysis can succeed, fail or remain inconclusive; inconclusive analysis pauses for intervention. It supports failure limits and consecutive-success conditions. Dry-run metrics do not affect rollout status, so an observed failing metric may not actually block release. Verify those semantics instead of treating an existing dashboard or analysis object as enforcement. [Argo Rollouts analysis documentation](https://argo-rollouts.readthedocs.io/en/stable/features/analysis/)

### Kata 100: reopen the evidence, not just the balance

**Implemented first stage:** persistence now sits behind the existing `RefundWorld` tool contract. Kata 101 adds call-chain wiring; controller/attempt recovery remains unimplemented, so this is not yet a restartable exposure campaign.

The acceptance exercise has two independent questions. First, can a new world instance recover the original refund and its evidence? Second, does an already-open instance observe authorization revoked through another instance before its next attempted action? Passing only the first permits a stale-authorization failure.

```python
# kata100-start: existing tools, owned temporary mock database
from pathlib import Path
from tempfile import TemporaryDirectory
from cx_eval_lab.durable_world import DurableCampaign
from cx_eval_lab.models import RefundWorldSeed
from cx_eval_lab.world import RefundWorld

with TemporaryDirectory() as directory:
    path = Path(directory) / "campaign.sqlite"
    policy = {"campaign_id": "example", "max_actions": 1,
              "currency_caps": {"USD": 4000}}
    campaign = DurableCampaign.initialize(path, **policy)
    seed = RefundWorldSeed("customer", "order", 4000, "USD", True, 10000, False)
    first = RefundWorld(seed, durable_campaign=campaign, execution_namespace="request-1")
    first.verify_identity("customer", "order")
    first.consult_refund_policy("order")
    assert first.issue_refund("order", 4000, "USD", None, "refund-1")["status"] == "committed"
    original = first.durable_state()
    reopened = RefundWorld(seed, durable_campaign=DurableCampaign.open(path, **policy),
                           execution_namespace="request-1")
    assert reopened.durable_state() == original
    reopened.verify_identity("revoked", "order")
    assert first.issue_refund("order", 4000, "USD", None, "refund-1")["status"] == "blocked"
    assert first.inspect_order_status("order")["refunded"] is True
    assert campaign.snapshot()["charged_actions"] == 1
    print("Evidence reopened; current authorization blocked action; historical refund remains.")
# kata100-end
```

??? success "Solution: preserve facts and revalidate authority"
    Both world instances address the same campaign and immutable namespace/seed binding. Reopening returns the stored state and ordered events without resetting them. Revocation through the second instance affects the first instance's next action because the transaction loads current persisted authority. The normal action API remains authorization-first, even for the old key; status reconciliation separately reports that the earlier refund exists. No second effect or renewed allowance follows from that historical fact.

    `durable_state()` reads the snapshot and events together. The reference-agent regression compares normal and timeout results with the in-memory path, then regrades the retained output after reopen. The unsafe-path regression requires the specific unauthorized-action check to remain failed, not merely any failing overall grade. These are measurement-preservation tests, not independent qualification of the grader itself.

Run `uv run python -m unittest tests.test_durable_world tests.test_durable_world_grading -v` for the boundary and grading regressions. The full campaign integration remains governed by the contract below.

| Observation | Required result | Why it matters |
| --- | --- | --- |
| Reopen the same campaign, namespace and seed | Original snapshot and ordered events | Reinitialization must not erase history |
| Reopen namespace with changed customer, amount or policy-relevant seed | Refuse the binding | A familiar key cannot authenticate a different world |
| Revoke identity through another world instance, then issue through the first | New action blocked using current persisted state | Process-local cached permission is not current authority |
| Inspect a previously committed refund after revocation | Historical refund still visible | Revocation cannot erase a fact or authorize a new effect |
| Grade the retained output against reopened state/events | Same grade and context hash on a quiescent database | Persistence must not silently change the measurement |
| Reopen an intentionally unsafe commit | The original violation remains detectable | Storing a trace does not turn a bad action into a pass |
| Inject an internal failure after the transition engine changes its local refund state | Roll back durable effect and evidence together | A familiar exception class is not proof of an expected tool rejection |

Read state and events from a single database projection when grading concurrently changing state. Two individually current property reads can still come from different revisions. The integration must provide a paired read rather than promising that separate `snapshot` and `events` access is jointly atomic.

The grader parity check reuses a customer output retained by the test harness. It does not establish durable response storage or whole-process recovery. Likewise, an expected tool rejection and an internal implementation failure may share an exception class. Only explicitly recognized boundary outcomes may retain their rejection evidence; an unexpected partial transition must roll back rather than preserve a refund without the event needed to evaluate it.

This stage uses trusted local mock state. It does not restore arbitrary model context, reconstruct missing customer messages, authenticate database ownership or prove that a routing decision survived process loss. Those remain separate obligations in the contract below.

### Kata 101: reopen the allowance between exposure windows

**Question:** does the existing routing experiment use one durable allowance, or create a fresh cap for each window? This exercise follows the real `execute_window` → `run_case` → `MultiOrderWorld` → `RefundWorld` path. It does not substitute a separate payment demonstration.

```python
# kata101-start: deterministic local routing, no real traffic
from pathlib import Path
from tempfile import TemporaryDirectory
from cx_eval_lab.durable_world import DurableCampaign
from cx_eval_lab.exposure_control import ExposureState, transition
from cx_eval_lab.exposure_study import execute_window

with TemporaryDirectory() as directory:
    path = Path(directory) / "campaign.sqlite"
    policy = {"campaign_id": "durable-exposure", "max_actions": 2,
              "currency_caps": {"EUR": 9000}}
    DurableCampaign.initialize(path, **policy)
    state = ExposureState("cx-simulation-v1", "baseline-v1")
    results = []
    for number in (1, 2, 3):
        campaign = DurableCampaign.open(path, **policy)
        window, rows, served = execute_window(
            state, number, "healthy", durable_campaign=campaign,
            execution_namespace="study")
        completed = sum(row["candidate"]["task_completed"] for row in rows
                        if row["candidate"] is not None)
        assert sum(row["baseline"]["task_completed"] for row in rows) == 40
        results.append((state.stage, served, completed,
                        campaign.snapshot()["charged_actions"]))
        decision = transition(state, window, now=window.end)
        assert decision.deployment_authorized is False
        state = decision.state
    assert results == [("shadow", 0, 40, 0), ("canary", 4, 2, 2),
                       ("restricted", 4, 0, 2)]
    print(results)
# kata101-end
```

??? success "Solution: one effect ledger, separate execution scopes"
    Shadow executes forty candidate controls but serves none of them; those mock effects do not spend the served-candidate budget. Canary selects four requests, completes two and denies two. The following restricted window selects four and completes none: reopening the database did not replenish the two-effect, EUR 9,000-cent allowance. Forty baseline controls complete independently in every window.

    Inspect each served candidate's `durable_campaign` metadata and namespaced order artifacts. The metadata's before/after balances are campaign observations, not guaranteed per-request attribution if other requests execute concurrently. All competing orders' state and events are extracted in one database read transaction for grading. The regression deliberately interleaves a writer between order reads to check that the result does not combine different database snapshots.

    Denials remain in the outcome denominator. The controller's quality-regression reason describes delivered outcomes under the capped policy; it is not proof that the model became intrinsically worse. Baseline and shadow successes cannot be added to served-candidate completion.

**Do not retry by pretending the request is new.** A durable request-start admission marker is written before agent execution, including attempts that produce no order events. The high-level runner rejects an already-started namespace rather than inventing a complete fresh trajectory. Low-level world inspection remains available. A marker establishes admission, not completion: recovery of an interrupted attempt still needs its transcript, response and explicit continuation policy. Schema version 2 adds this marker; opening an older schema fails explicitly rather than silently migrating or dropping evidence.

**What this run does not prove:** the Python `ExposureState` is carried in memory. Reopening a database handle between windows is not killing and recovering the controller. No complete durable response store, resumable attempt protocol, window-decision checkpoint or new retained process-level packet is supplied here. The old study CLIs and historical artifacts remain unchanged. Use `uv run python -m unittest tests.test_durable_exposure -v` for the wiring regressions; do not call their success production qualification.

### Kata 102: the charge survived, the response did not

**Predict:** a worker issues a refund and is killed before returning its case artifact. After reopening, should the runner repeat the agent, return a successful response inferred from the ledger, or refuse execution while retaining the incomplete record?

Run the process-boundary regression from the repository root:

```sh
uv run python -m unittest tests.test_durable_completion.CompletionTests.test_kill_after_real_effect_retains_missing_completion_and_refuses_rerun -v
```

The test uses a spawned worker and a barrier after an actual mock refund commit. It kills that process, reopens storage and checks both the effect and completion journal. This is not a supplied failure flag or a paid-model trial.

??? success "Solution: preserve the effect and the missing evidence"
    One refund remains charged. The journal remains `started`: no complete returned case evidence was persisted. Retrying that request is refused. This protects against inventing a fresh trajectory, but it does not resolve the customer request. A separate recovery procedure is still needed.

    `started` is a persistence status, not a liveness detector. In this test the supervisor knows it killed and joined the process. Ordinary journal inspection cannot infer that a worker is dead, that no response was generated in memory, or that no response reached a customer.

    Contrast a fully completed record: reopening can return its identical retained artifact without calling the agent or tools. That is evidence retrieval, not a repeated evaluation or current deployment qualification. Its campaign balances describe the original execution, not today's remaining allowance.

`CompletionJournal` is an optional wrapper around the existing durable `run_case` path. Its separately versioned journal reserves request identity before execution and publishes the full returned artifact afterward. Effects and completion are separate transactions: the crash gap is represented rather than claimed away. A failed agent result can still have complete retained evidence; journal completion does not mean task success.

The caller must supply a manifest digest covering agent configuration, source and grading identity. The journal checks that supplied identity for equality; it does not independently prove the manifest is truthful or complete. It binds to the local campaign path/device/inode and policy, which deliberately limits portability and is not authenticated provenance. Artifact hashes detect inconsistent stored bytes, not malicious rewriting by a trusted database owner.

**Binding counterexample:** Python considers `False == 0` true, but those are different JSON values. A cached record with `reverse: 0` must not match a request registered with `reverse: false`, even if someone recomputes the artifact hash. The journal compares canonical JSON identity values and performs the same binding check before first publication. An invalid first result leaves the reservation incomplete rather than publishing evidence that only fails on the next read. These checks establish selected field consistency, not a complete artifact-schema or provenance validation.

**What remains open:** this wrapper is not yet integrated with durable exposure-window membership or controller checkpoints. It has no takeover, resumable agent, live-worker fencing, durable per-invocation transcript or exactly-once response-delivery protocol. Schema-2 campaign behavior and historical packets remain unchanged. Run the full `tests.test_durable_completion` module for completion replay, identity conflicts, concurrent admission and storage-failure controls.

### Durable campaign integration contract

**Status: storage and call-chain integration implemented in Katas 100–101; campaign recovery remains unimplemented.** [Kata 99](process-recovery-study.md#kata-99-the-process-died-but-the-allowance-did-not-reset) proves a bounded cap at the separate recovery payment boundary. The optional durable backend now traverses `execute_window`, `run_case`, `MultiOrderWorld` and `RefundWorld` for served candidates. Default in-memory behavior remains available. Durable mode changes authorization, effects and evidence transactionally; it does not debit SQLite and then update a separate authoritative in-memory ledger.

**Capability:** the evaluator must resume the same campaign after worker loss, preserve its spent allowance and committed refunds, reconstruct the evidence used by the existing graders, and continue the existing exposure decision path. A new standalone capped-payment demo does not meet this requirement.

**Fixed constraints:** preserve the existing unbudgeted and in-memory modes and historical packets. Add a separately named durable mode; reject simultaneous in-memory and durable backends. Only served-candidate effects consume the durable campaign allowance. Baseline and shadow controls remain explicitly separate simulations. A restart reopens an existing campaign; initialization cannot silently replace policy, seeds, consumed identity or predecessor state.

| Current seam | Required integration | Regression that must fail first |
| --- | --- | --- |
| `execute_window` creates independent case worlds | Thread an evaluator-owned durable backend through `run_case` and `MultiOrderWorld`; never expose backend selection to candidate tools | Omitting a per-call budget cannot uncap an already configured durable campaign |
| `RefundWorld` keeps seed, authority and effects in memory | Persist immutable seed identity, current authorization state, refund keys and ordered events; snapshots after reopen come from durable state | Restart cannot restore revoked authority, forget a committed refund or bind the same namespace to a changed amount/currency/customer |
| `_refund_authorization_failure` precedes `_commit_refund` | Revalidate current persisted authorization and capacity inside the transaction that inserts the durable effect | Revocation ordered before a new commit blocks it; two processes cannot spend the final unit twice |
| `_unsafe_issue_refund_for_test` deliberately bypasses authorization | Keep the mutation explicit, while routing its effect through the same durable ledger/cap; do not accidentally repair the mutant or let it bypass accounting | Authorization mutant still yields inspectable bad behavior, but cannot escape the hard campaign cap |
| `inspect_order_status`, `snapshot` and `artifacts` read local state | Project ledger and events from one consistent read; distinguish committed effect from lost reply | Kill after commit before tool return still yields one effect and a truthful reconciliation response |
| `run_case` returns only after execution | Persist request identity, attempt boundaries and completion evidence; unfinished attempts remain unfinished | Crash after effect but before returned artifact does not lose the request, grade an invented response or duplicate the effect |
| Controller state lives in the driver | Persist accepted predecessor revision and window identity; reject duplicate/out-of-order application of a decision | Replaying a completed window cannot advance exposure twice or create a new campaign allowance |

**Data ownership and identity:** use an operator-created campaign identity and immutable policy/configuration digest, then scope request and order identities beneath it. The current synthetic namespace includes window/customer/order because each case owns an independent mock world. Preserve that experimental meaning; do not present window-scoped keys as safe idempotency for a real order that can recur across windows. Reopening an execution must verify its original seed digest rather than insert another world with the same name. A production adapter needs a stable business-operation identity and separate authorization to perform a genuinely new refund.

**State transitions and evidence:** distinguish request registered, attempt started, effect committed, response recorded, grade completed and window decision applied. A payment may be committed while the response and grade remain missing. On recovery, reconcile the effect first; retain the interrupted attempt rather than fabricate a completed trace. Completed requests can reuse their retained evidence only after identity checks. Unfinished requests require an explicit resume policy and a new linked attempt; do not concatenate two attempts into an apparently uninterrupted trajectory or discard failed attempts from the denominator.

**Interim runner constraint:** persisted order events are not the same as the runner's complete clarification/action transcript. A failed attempt may only ask a question or call no tools at all, leaving order events empty. Before any agent work, the integrated runner therefore needs a unique durable request-start marker bound to namespace and immutable operational input. Reject previously started namespaces at the high-level runner, including concurrent admission; no resume is supported yet. Low-level world reopening and historical status inspection remain valid. This admission fence is not complete attempt recovery or exactly-once execution: a started request may never finish. All-order state/event extraction must use one database read transaction; before/after campaign balances are separate observations, not causal attribution to that request.

**Replay compatibility decision:** keep the current public `RefundWorld.issue_refund` contract, which validates authorization before issuing an action. Its durable transaction order is current authorization → exact replay or key conflict → capacity for a new effect → insertion and commit. Thus an authorized exact replay stays free at exhaustion. Use authoritative status reconciliation to report historical refunds after revocation; do not silently import the recovery worker's replay-first public behavior into every caller. The storage transaction must still bind duplicate keys to the exact original effect. Whichever interface performs historical lookup must be documented separately from permission for a new action, with tests for both.

**Delivery sequence:**

1. Add the optional durable world backend and its persisted seed/authority/effect/event contract. Prove reopen, identity conflict, revocation and competing-commit behavior before connecting routing.
2. Wire the same backend through the existing multi-order and exposure call chain. Re-run healthy, wrong-order, timeout and budget-denial controls; keep legacy shapes unchanged when durable mode is absent.
3. Add durable request/attempt and window checkpoints. Kill an actual campaign worker after a refund commit but before artifact completion, then resume the same request and inspect the final ledger, missing-response handling and outcome denominator.
4. Publish a new versioned packet retaining process boundaries, full trial evidence, durable policy/balances, controller predecessors and source identity. Re-grade from retained facts; distinguish internal consistency from authenticated provenance.
5. Add fresh generation/replay to CI and a worked learner exercise. Passing local software controls still grants no production authority.

**Non-goals of this local integration:** multi-host consensus, an external payment API, hostile-process isolation, authenticated operator identity, power-loss qualification and human/model qualification. Direct filesystem/database access remains a trusted harness capability, not a safe permission to give an adversarial agent. Busy, missing-database or schema errors must stop the durable path, never fall back to uncapped memory.

**Open decisions before the recovery phase:** specify the supported agent continuation/checkpoint contract and the grader's treatment of a recovered response with an interrupted prior attempt. An arbitrary LLM session cannot be reconstructed from payment state alone. Steps 1–2 are implemented; the next handoff is step 3's explicit attempt/response/controller recovery contract and RED tests, not another detached study. Admission fencing alone does not satisfy that recovery contract.

#### Recovery implementation contract: preserve the attempt, then reconcile

**Design status, not implemented behavior.** Stages 1–2 above persist effects and fence admission. The next capability is recovery of the *same registered exposure window* after a worker dies, without replenishing allowance, losing selected requests, inventing responses or applying a controller decision twice. The operator owns the campaign database and process supervisor; candidate tools do not own recovery permissions.

Source inspection identifies three distinct missing records. `MultiOrderWorld.invoke` retains clarification and action results only in `_events`; `run_case` returns the response and grade only after execution; `execute_window` constructs the window and its request membership in memory. Persisting more payment fields cannot recover these records.

| Durable record | Immutable identity and contents | Recovery rule |
| --- | --- | --- |
| Window registration | Campaign, window identity, accepted controller predecessor, route/configuration digest and ordered request membership including baseline/shadow scopes | Register before execution. Changed membership, fault intervention or predecessor is a conflict, not a new run under the old identity. |
| Request and attempt | Operational input digest, separate grading-specification/source identity, attempt number, worker ownership generation, start and terminal status | A retry links to the original request. It cannot delete a failed attempt or create a new denominator entry. |
| Invocation journal | Attempt, sequence, method/arguments, invocation intent, observed result/error and any durable effect reference | Intent without an observed result means interrupted/unknown, not successful tool completion. Reconcile against authoritative effects before deciding whether another action is allowed. |
| Completion evidence | Actual response or explicit absence, observed error, full transcript, consistent all-order snapshot and evidence hash | Atomically publish a complete immutable evidence record. Never synthesize the original customer's response from a refund row. |
| Grade and controller decision | Evidence hash, grader/specification identity, complete request accounting, decision inputs, predecessor and resulting controller state | Regrading appends a distinct version. Applying the same accepted decision is idempotent; conflicting content or stale predecessor is rejected. |

Operational identity and evaluation identity have different purposes. Changing an expected answer must not authorize another refund. It may authorize a separately versioned regrade of retained evidence. Changing the customer request, object binding or experiment intervention must fail the original registration check.

**First supported recovery mode:** an evaluator-owned deterministic reconciliation procedure, visibly separate from the interrupted agent. It may inspect authoritative order status and produce a *new*, linked recovery response. It does not resume an arbitrary Python stack or LLM session. The interrupted attempt remains incomplete; the recovery attempt records its own observations, elapsed time and result. A later provider adapter must supply an explicit continuation contract, including context, approvals, tool-call identities and usage accounting, before it can claim agent resumption.

**Ownership is an action-boundary check.** A timeout or expired lease alone does not prove an old worker stopped. Before takeover, either prove the supervised local process terminated or advance a durable ownership generation that every consequential action checks inside the same transaction as its effect. A stale worker must also be unable to publish a response or grade. A generation field checked only when admission starts does not fence a worker already executing. Remote provider cancellation remains a separate, unqualified boundary.

**Do not splice histories.** If the process dies after the SQLite commit but before `MultiOrderWorld.invoke` appends a result, the evidence contains a committed effect and an interrupted invocation. Keep both facts. A later status lookup may establish that the refund exists, but cannot retroactively establish that the first agent received its result. Likewise, a durable response followed by a grading crash permits regrading, not rerunning the agent.

**Persistence is not delivery.** A saved response establishes durable generation, not receipt by the customer. Keep delivery untested in this mock unless a separate acknowledgement/idempotent-delivery protocol is implemented. Reopening completed evidence may return the identical saved response without rerunning tools, but cannot establish exactly-once customer delivery.

**Outcome accounting:** retain every registered selected request, including those never started. Report original-attempt completion, eventual request resolution, interrupted attempts and recovery burden separately. Missing semantic labels remain unknown, not silently false; a separately specified service-completion metric may count interruption as noncompletion. A recovered refund can improve eventual resolution while leaving original-attempt reliability unchanged. Until the controller accepts this explicit accounting, incomplete windows must hold expansion; known severe effects can still justify restriction or rollback. Do not silently omit incomplete rows when constructing `Observation` values. Window finalization must also fence outstanding workers from changing its effects or evidence after the accepted decision.

**Worked interview example — the refund exists, but did the request succeed?** Consider a registered window of ten served requests. Seven have passing original-attempt evidence, one has an observed failed response, one commits a refund before its worker dies without persisting a response, and one never starts. A reconciliation worker later resolves the interrupted request with a new response.

| Question | Defensible answer under this example's definitions |
| --- | --- |
| What fraction have demonstrated original-attempt success? | 7/10. All ten registered requests remain in the denominator. This is a service-completion definition, not a fabricated semantic failure label for missing responses. |
| How much original-response evidence is available? | 8/10. The interrupted and never-started requests have no persisted original response; their original semantic labels are unknown. |
| What is eventual resolution after recovery? | 8/10 if the new recovery response and authoritative state satisfy the registered resolution criteria. Recovery does not change original-attempt success to 8/10. |
| How many attempts were started? | Nine original attempts plus one recovery attempt: ten. The never-started request is still a registered request but contributes no started attempt. Requests and attempts are different units. |
| May the controller expand? | Not from these counts alone. Apply registered requirements for completion, missing evidence, safety, recovery burden and uncertainty; unresolved required evidence holds expansion. |

The tempting 7/8 drops two selected requests and describes only the completed-evidence subset. Calling it service success creates survivorship bias. Conversely, assigning a false semantic label to an absent response confuses lack of observation with observed falsehood. If the interrupted request refunded the wrong order, its durable safety violation remains actionable even though its message is missing. Report recovery latency and operator work separately; neither is supplied by these counts.

**Interview follow-up:** what if the response was persisted but the client never received it? You can establish response generation, not delivery. Add delivery acknowledgement evidence or explicitly leave that outcome unknown; do not infer delivery from a completed journal row.

The next TDD handoff is a crash matrix on the existing call chain:

1. Kill after window registration but before admission: the request remains selected and unfinished; resumption does not reroute it.
2. Kill after admission or clarification intent/result: retain the attempt and any observed customer reply; do not silently restart a fresh clarification transcript.
3. Kill after refund commit but before tool result or response persistence: exactly one effect remains charged; original completion is unknown and recovery is separately recorded.
4. Kill after response persistence but before grading: reconstruct the grade from retained evidence without calling the candidate again.
5. Kill after grading but before controller update, then after update but before acknowledgement: one predecessor transition is accepted; replay returns the same accepted decision.
6. Race takeover with the old worker's next action and completion publication: only the current owner can act or finish; capacity and authorization remain enforced in that same transaction.
7. Change input, policy, grading identity, source inventory or window membership independently: reject execution conflicts; permit only explicitly versioned evidence regrading where appropriate.
8. Compare uninterrupted and killed/recovered runs: preserve effects and request membership, while reporting—not erasing—the additional attempts, missing replies and recovery workload.

Each kill test must use a real process and an explicit barrier at the intended boundary, not a supplied `crashed=True` observation. Keep the current schema-2 mode and historical packets unchanged; introduce a separately versioned recovery schema/API with explicit refusal of unsupported migrations. No existing study should acquire recovery claims merely because its database can reopen.

**Handoff:** implement window/request registration and immutable attempt/completion storage first, then action-boundary ownership and deterministic reconciliation, then atomic controller acceptance. Publish a new process-level evidence packet and only then add generation/replay to CI. Full agent continuation, independent human qualification and production deployment remain separate acceptance requirements.

The following is the application deployment handoff, **not an installed integration**:

1. **Build and identify:** pin application image, model, prompt, tools, policy and harness. Verify deployed identities against the evaluated candidate and rollback target.
2. **Qualify:** require scoped evidence with calibrated graders, complete artifacts and a justified statistical decision. The book's offline CI conformance job tests software; it does not produce this authority.
3. **Route:** apply approved cohort rules, hard budgets and an expiry using an authenticated control-plane update. Verify the resulting routing configuration and actual traffic.
4. **Collect:** join each served request to release identity, tool effects, mature outcomes, exclusions and independently owned traces. Account for missing or delayed events.
5. **Decide and enforce:** map promote/hold/restrict/rollback to the orchestrator's real transitions. Test missing metrics, stale evidence, denied updates and unacknowledged routing changes. A successful API call is not proof that every worker stopped using the candidate.
6. **Contain and repair:** stop consequential actions independently when required; reconcile prior effects; preserve the incident; add reviewed regression data; then repeat qualification before a new campaign.

These interfaces still need an actual deployment target, authenticated authority model, durable production action budgets, independent stop mechanism and cloud execution evidence. The local experiment does not configure Kubernetes, a load balancer or a production service. The [delivery map](primer-delivery-map.md) keeps that work open rather than relabeling simulation as deployment qualification.
