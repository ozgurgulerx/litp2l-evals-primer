# Knowledge-to-action: does better evidence repair the task?

A refund agent receives the right policy, computes the right decision, and sends the wrong refund amount. The server rejects the write. Retrieval succeeded; the agent did not complete the task; the authorization boundary worked. Calling the whole trace a “RAG failure” would send the engineer toward the wrong repair.

This study separates those outcomes by executing local document retrieval, policy interpretation and mock ledger operations. The downstream agents are deliberately simple deterministic controls. The experiment teaches attribution and evidence extraction; it does not measure a language model's knowledge, reasoning or production reliability.

## What the comparison changes

Hold the case, corpus, downstream agent and backend contract fixed within each comparison. Change only the evidence-access arm:

| Arm | Evidence intervention | What remains difficult |
| --- | --- | --- |
| Retrieval | Rank corpus documents by lexical overlap and supply the top result | Vocabulary mismatch, stale high-ranked documents, policy interpretation and action arguments |
| Oracle documents | Supply the evaluator-selected current policy directly | Reading the supplied policy, choosing a decision and executing it correctly |
| Full context | Supply the entire small corpus, including competing versions | Selecting applicable evidence from distractors, then interpreting and acting |

An oracle is an experimental intervention, not a deployable source of answers. Its selection uses evaluator knowledge unavailable to ordinary retrieval. Keep that selection outside the agent interface; do not supply an expected outcome alongside the document. Full context is a different intervention: it removes omission by retrieval but preserves evidence-selection work. Its context size also differs, so this comparison is not a matched-token efficiency study.

Sierra's τ-Knowledge evaluates document access together with simulated backend updates. Its reported oracle-document intervention improves performance without eliminating downstream failures. That motivates our separation of evidence, decisions and effects; this tiny local study neither reproduces Sierra's benchmark nor transfers its results to our agents. [Sierra's first-party τ³ report](https://sierra.ai/blog/bench-advancing-agent-benchmarking-to-knowledge-and-voice) (checked 6 September 2026).

## Extract observations from executions

Register the corpus, cases, evidence arms, downstream controls and outcome contract before inspecting results. Use a fresh ledger for each execution. Reusing a refunded order across arms would let an earlier intervention change the next arm's starting state. Record each arm's context size, but do not call document counts token costs or invent prices for this local computation.

Retain the query, corpus and versions, actual ranking, supplied context, selected policy, explicit decision, tool arguments and results, and the initial and final ledger. Derive observations after execution:

| Observation | Evidence used | Invalid shortcut |
| --- | --- | --- |
| Required knowledge available | Evaluator requirements compared with the corpus | Assume an index contains the needed version |
| Required knowledge supplied | Requirements compared with actual context document IDs | Treat a high lexical score as relevance |
| Policy selection | Selected document and its applicability/version | Assume every supplied document was used |
| Decision correctness | Observable decision compared with the authoritative case contract | Treat abstention as a correct denial |
| Action correctness | Attempted arguments, backend responses and final state | Ignore rejected attempts because no bad write committed |
| Task completion | Required resolution and final-state conditions together | Treat a safe but unresolved request as completed |

The deterministic control exposes an explicit decision. That makes policy interpretation inspectable in this lab. It is not a measurement of hidden model reasoning. With a model, evaluate observable claims, plans where appropriate, tool choices and outcomes; do not infer a faithful internal explanation from a fluent rationale.

The useful comparison is crossed: run each evidence arm with the correct downstream control and again with the wrong-amount mutant. Comparing ordinary retrieval with a weak agent against oracle access with a stronger agent would confound the evidence and agent changes. The crossed controls do not establish a statistical interaction estimate; they make the selected failure mechanisms visible.

## Reproduce the local experiment

```bash
uv run python -m unittest tests.test_knowledge_action -v
uv run python -m cx_eval_lab.knowledge_action \
  --output /tmp/primer-knowledge-action-my-first-run.json
```

Use a fresh output filename. The CLI runs the controls, replays their retained evidence and refuses to overwrite an existing report. All operations are local; no provider credential or paid call is needed.

The two documents intentionally expose a lexical mismatch:

- `doc-a`, obsolete `policy-v1`: “Refund blue backpack orders within 90 days.”
- `doc-b`, active `policy-v2`: “Reimbursements for luggage purchases within 30 days.”

These are invented policies. The query ranker counts unique overlapping lowercase alphanumeric tokens, with document ID as the tie-breaker. It does not know that “refund” and “reimbursement” are related. The policy control receives the active version from trusted request context and reads a **structured window field**, not the prose sentence. This isolates evidence access and action execution; it does not test natural-language rule extraction or discovery of the active policy version.

| Case | Query and order age | Retrieved document | Required resolution |
| --- | --- | --- | --- |
| `case-01` | “Refund blue backpack.”; 10 days | Obsolete `doc-a` | Refund under the active 30-day rule |
| `case-02` | “Refund blue backpack after 45 days.”; 45 days | Obsolete `doc-a` | Deny under the active 30-day rule |
| `case-03` | “Reimbursements for luggage purchases.”; 10 days | Active `doc-b` | Refund |

All orders are for 4,000 cents in the local mock. The wrong-amount mutant asks for 4,001 cents whenever its decision is to refund. The server independently rejects the mismatch. The active policy exists in the corpus for every case, but the retrieval arm supplies it for only one of the three cases.

The runner requires exactly one active policy in the corpus before executing. Consequently, corpus availability is a validated precondition here, not a measured missing-knowledge challenge. A corpus with no active policy or conflicting active documents is rejected at setup; it does not silently become an unsuccessful retrieval trial. A future missing-knowledge study needs a separate registered outcome for that condition.

### Observed results

The [retained execution packet](assets/knowledge-action-study-v1.json) contains the full input registration, per-trial context, decisions, attempted effects, derived grades and summary. Reproduce its grades without a network call:

```python
import json
from pathlib import Path
from cx_eval_lab.knowledge_action import replay_study

report = json.loads(Path("docs/assets/knowledge-action-study-v1.json").read_text())
assert len(replay_study(report)) == 18
```

Replay recomputes retrieval and mock executions using the local implementation and checks the full report. It does not authenticate an external run or pin the installed source revision. Keep that distinction from the stronger source checks in [Katas 49–50](evidence-spine.md#kata-49-matching-a-hash-is-not-validating-an-input).

The local run executes 18 fresh-ledger trials: three cases × three evidence arms × two downstream controls. Counts below are over the three cases within each row, not over independent production users.

| Downstream control | Evidence arm | Required evidence supplied | Correct decisions | Completed tasks | Blocked attempts | Completed denials |
| --- | --- | --- | --- | --- | --- | --- |
| Policy control | Retrieval | 1/3 | 1/3 | 1/3 | 0 | 0 |
| Policy control | Oracle | 3/3 | 3/3 | 3/3 | 0 | 1 |
| Policy control | Full context | 3/3 | 3/3 | 3/3 | 0 | 1 |
| Wrong-amount mutant | Retrieval | 1/3 | 1/3 | 0/3 | 1 | 0 |
| Wrong-amount mutant | Oracle | 3/3 | 3/3 | 1/3 | 2 | 1 |
| Wrong-amount mutant | Full context | 3/3 | 3/3 | 1/3 | 2 | 1 |

Two details matter. First, the mutant's oracle improvement from zero to one completed task comes from the **correct denial**, not a repaired refund. Second, both retrieval controls abstain on the two cases where only the stale document is supplied. The absence of rejected writes in those trials is not successful task completion.

The packet also records context volume: retrieval supplies 43, 43 and 52 document-text characters across the three cases; oracle supplies 52 each; full context supplies 95 each. These counts exclude request and metadata and are **not token counts, latency or monetary costs**. A no-action trace has zero attempted arguments to inspect; its vacuously true argument-consistency check is not evidence of action capability. Read it alongside `action_attempt_count`, the explicit decision and the final-state check.

For `case-01` with the mutant and oracle access, the extracted trace is: active `doc-b` supplied → decision `refund` → requested 4,001 cents → backend `arguments_mismatch` → empty refund ledger → failed task. The correct control requests 4,000 cents and commits the required refund in its own fresh ledger. These traces support the stage diagnosis without an input flag declaring “action failure.”

## Kata 51: the policy exists, but the query cannot find it

**Know:** corpus coverage, retrieval recall and end-to-end completion are different denominators.

**Task:** run the same cases under retrieval, oracle documents and full context. Find a case whose required policy exists in the corpus but is absent from the retrieved context. Compare its decision and final state after supplying the oracle document. Then inspect a stale-policy case: does the control use the obsolete rule, or leave the request unresolved?

??? success "Solution: localize the repaired stage"
    A corpus-coverage check can pass while top-one required-evidence recall fails. A lexical match measures word overlap, not policy validity. Inspect the ranked document IDs and the actual context before blaming interpretation.

    If the same downstream control completes the same task after receiving the oracle document, the intervention repairs this constructed failure under the tested configuration. That is evidence for an access bottleneck in this case—not a population-wide causal estimate and not proof that every remaining failure is reasoning.

    Full-context success supplies a second useful control: the policy interpreter can choose the current rule when both current and stale documents are present. Reverse their order to test whether the result depends on accidental corpus ordering. A corpus that fits entirely in this toy context says nothing about production context limits.

    Refusing to use stale evidence can be correct defensive behavior while still leaving the service request unresolved. Keep the unresolved outcome visible. The user needed a resolution, not merely the absence of an unsafe write.

**Extend:** add paraphrases with disjoint wording, multiple jointly required documents, effective-date boundaries and two equally applicable rules. Freeze acceptance examples before tuning retrieval. Compare query rewriting or another search interface while retaining the same downstream control and declared resource limits. Those extensions are not established by the three-arm study alone.

**Interview answer:** “I first check whether the required knowledge exists, then whether it reaches the agent, then whether the agent uses it correctly. Oracle and full-context interventions help localize failures, but their privileged evidence and different context budgets limit what I can generalize.”

## Kata 52: oracle evidence cannot repair a bad tool argument

**Know:** successful enforcement and successful assistance are separate outcomes.

**Task:** give the wrong-amount mutant the oracle policy. Inspect its explicit decision, attempted refund amount, backend rejection and unchanged ledger. Compare it with the correct downstream control. Finally inspect an ineligible order, for which the correct resolution is denial and no write.

??? success "Solution: score the attempt and the effect separately"
    The mutant can read the applicable document and decide correctly to refund, yet send an amount that violates the backend contract. Its rejected action is a failed agent attempt. The server's refusal is successful enforcement. Neither result erases the other.

    For an eligible order, an unchanged ledger is not the required outcome: the refund remains undone. For an ineligible order, no write may be exactly right—but only when the response actually resolves the request as denied under the applicable policy. An abstention or missing decision is not interchangeable with that denial.

    The correct control must succeed on the eligible case using the same backend. This positive control prevents a reject-everything implementation from looking robust. Preserve rejected arguments and error results in the trace; a grader that inspects only committed writes misses the mutant's failure mechanism.

    Re-execute from retained inputs and compare the complete event/state result. Altering an event and recomputing its content hash should still fail replay because the altered trace is not what the registered deterministic control produces. Hash equality alone cannot establish semantic consistency or real execution provenance.

**Extend:** change the currency or object ID, retry after rejection, and separate a denied wrong write from a wrong write that actually commits. The latter requires repair at the enforcement boundary as well as the agent. Do not weaken server validation to make a model appear more capable.

**Interview answer:** “Correct retrieval is necessary but insufficient. I measure the decision, attempted arguments, enforcement outcome and final state independently. A rejected unsafe call is a control success and an agent failure; a safe unresolved task is still unresolved.”

## Kata 53: do not turn constructed cases into a population claim

**Task:** suppose an oracle arm repairs two of three selected examples. May you claim a 67-percentage-point production improvement? Would repeating these deterministic examples one hundred times provide three hundred independent cases?

??? success "Solution: count cases, interventions and replications honestly"
    No. The examples were constructed to expose specific mechanisms, not sampled from a production population. Their arm difference describes this finite demonstration. Repeating a deterministic execution checks repeatability and isolation; it does not increase population coverage or create independent customers.

    Retain case-level paired outcomes before reporting an aggregate. Also report rejected calls, unresolved work and successful denials. A control that refunds eligible requests but mishandles denials must not hide behind a single average.

    A live-model successor needs a frozen representative case set, a registered unit of independence, repeated stochastic trials within cases, matched model settings, explicit resource accounting, and qualified outcome extraction. Report all randomized arms, including tool failures and missing outcomes. Do not compute success only over trials where retrieval already worked; conditioning on a stage affected by the intervention changes the comparison.

**Key points to remember:** oracle access is privileged; full context changes context volume; model and harness effects need separate controls; task success does not subsume enforcement; repeated trials are not new population units; scorer conformance is not deployment qualification.

## What this study cannot justify

No live model, embedding service, human user, payment provider or production deployment is involved. The policy language is intentionally restricted and the backend is a local mock. There is no measured semantic generalization, calibrated user simulator, monetary efficiency estimate, statistical release claim, or authority to expand traffic. Use the [evidence spine](evidence-spine.md), [semantic grading lab](semantic-grading-lab.md) and [release gates](checklist.md) to identify the additional evidence a real successor would need.
