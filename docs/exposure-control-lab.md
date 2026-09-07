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

**Limits:** the budget and effect state are in memory under one shared lock. They are not durable across interpreter loss, a distributed service, an authenticated campaign registry, an in-flight concurrency limit or protection against hostile Python code with process access. The snippet creates new execution records in memory; it does not publish a new retained, independently replayable budgeted release packet. The historical v1 artifact is unchanged. Durable enforcement and a versioned budgeted packet remain required follow-up work.

### Hard action budgets: implementation contract

**Status: first in-process boundary implemented; durable enforcement and a retained budgeted release packet remain open.** A 5% cohort cannot enforce a two-refund cap. Nor can a post-return counter account safely for a tool that committed a refund and then timed out. Kata 95 joins budget accounting to the effect boundary while preserving the unbudgeted historical study. The design requirements below remain the contract for reviewing this implementation and its remaining extensions.

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

The following is the implementation handoff, **not an installed integration**:

1. **Build and identify:** pin application image, model, prompt, tools, policy and harness. Verify deployed identities against the evaluated candidate and rollback target.
2. **Qualify:** require scoped evidence with calibrated graders, complete artifacts and a justified statistical decision. The book's offline CI conformance job tests software; it does not produce this authority.
3. **Route:** apply approved cohort rules, hard budgets and an expiry using an authenticated control-plane update. Verify the resulting routing configuration and actual traffic.
4. **Collect:** join each served request to release identity, tool effects, mature outcomes, exclusions and independently owned traces. Account for missing or delayed events.
5. **Decide and enforce:** map promote/hold/restrict/rollback to the orchestrator's real transitions. Test missing metrics, stale evidence, denied updates and unacknowledged routing changes. A successful API call is not proof that every worker stopped using the candidate.
6. **Contain and repair:** stop consequential actions independently when required; reconcile prior effects; preserve the incident; add reviewed regression data; then repeat qualification before a new campaign.

These interfaces still need an actual deployment target, authenticated authority model, durable production action budgets, independent stop mechanism and cloud execution evidence. The local experiment does not configure Kubernetes, a load balancer or a production service. The [delivery map](primer-delivery-map.md) keeps that work open rather than relabeling simulation as deployment qualification.
