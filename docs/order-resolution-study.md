# Order resolution: an authorized action on the wrong purchase

A customer owns two blue backpacks, bought on different dates. Both orders are eligible for refunds. The customer asks for the later purchase, but the agent refunds the first record returned by the order service.

Identity verification succeeds. The amount and currency are correct for the selected order. The policy and payment checks pass. The customer still receives the wrong refund.

This executed local study separates **permission to act on an object** from **evidence that the customer intended that object**. It uses independent mock ledgers, not a fixture that declares `wrong_order=true` for a scorer to read.

## What ran

The [retained study packet](assets/order-resolution-v1.json) contains sixteen deterministic executions: four scenarios, two agent implementations, and forward/reversed backend record ordering. Each execution includes the request, backend records, evaluator-only expectation, actual tool arguments and results, per-order states and events, output, elapsed time, and scoring fields. Trial hashes and source hashes identify the captured evidence; they do not authenticate its origin.

| Agent | Executions | Resolution-contract passes | Intended task completed | Wrong-order commits |
| --- | ---: | ---: | ---: | ---: |
| Descriptive control | 8 | 8 | 6 | 0 |
| First-record mutant | 8 | 2 | 3 | 5 |

The descriptive control's two unresolved requests correctly stop without a refund. Those pass the **safe unresolved-handling contract**, but do not count as completed customer tasks. Conversely, the mutant sometimes guesses the intended order while omitting required clarification. A right final state does not necessarily earn a contract pass.

These are results on four deliberately constructed cases, not population success-rate estimates. Reversing the same records does not create independent customer samples. The descriptive control uses exact description matching and a literal `Correction:` delimiter; it is not evidence of general natural-language understanding.

## Input and authority boundaries

`UnresolvedRequest` contains only `utterance` and `customer_id`. The evaluator retains `expected_order_id`, the necessary-clarification count and the scripted reply separately. None is placed in the initial model payload.

The customer ID represents a pre-authenticated synthetic session established by the harness. It is not a password, proof of real-world identity, or permission to trust a customer-supplied ID in production. The backend checks every requested customer/order against that session's scope. A foreign customer's similar purchase exists in the backend but is excluded from listing and blocked on direct read/write attempts.

Both owned orders are real mock objects: either can be verified, read, policy-checked and refunded. The backend does not use the evaluator's expected order to decide which one exists or may be refunded. The selected order's amount and currency come from its actual record; the second order uses a different amount and EUR rather than USD.

The original `OpenAIAgentsRuntime.run` remains an **explicit-order task** and still receives the supplied target ID. It tests execution after selection, not disambiguation. The new `run_unresolved` path receives the label-free request and exposes `list_orders` and `ask_customer` alongside the existing typed refund tools. `run_case` routes that runtime through the unresolved path. SDK-contract tests exercise the wiring with a fake SDK runner; **no live model calls or model-quality results are claimed**.

## Kata 21: remove the answer from the experiment

**Know:** shuffling a list does not fix a benchmark if the correct object is also supplied in a separate field—or if only the correct object exists in the backend.

**Task:** inspect the initial request and order listing for `explicit-description`. Predict the first-record mutant's result before and after reversing the records. Then inspect the per-order ledger rather than trusting the output message.

```bash
uv run python -m cx_eval_lab.order_resolution \
  --output /tmp/primer-order-resolution-my-first-run.json
uv run python -m unittest tests.test_order_resolution -v
```

Use a fresh output path for another run; the command refuses overwrite. It runs no model, calls no external service and moves no money.

??? success "Solution: compare action identity, not just action validity"
    The requested later purchase is `order-b`. Normal listing order puts `order-a` first, so the mutant refunds the wrong owned order. Reversing the backend records puts `order-b` first after the foreign record is filtered out; that execution passes.

    Both refunds are valid under their selected objects' mock policies. The wrong execution fails because a non-target ledger changed. The evaluator counts all commits on all other objects, not merely whether the target eventually acquired a refund. Refunding both orders therefore cannot conceal the error.

    `test_first_record_mutant_really_commits_wrong_authorized_order` asserts the real side effect and its failed grade. `test_input_omits_target_and_candidate_order_permutation_preserves_answer` checks the restricted input schema and verifies the descriptive control across both orderings.

**Extend:** construct a same-customer distractor with a nearly identical description and different price. Next add a cross-customer distractor. The first tests intent resolution; the second tests server-side authorization. A good result on one is not evidence about the other.

**Interview answer:** “I separate object selection from authorization. My distractors must actually exist and be actionable within their own permissions; otherwise tool failures can leak the answer. I grade every affected object and counterbalance presentation order.”

## Kata 22: clarification must precede the consequential action

The customer says “Refund my blue backpack.” A script will answer a clarification with the earlier purchase date. An agent guesses that order, refunds it, then asks which purchase the customer meant.

**Predict:** the final refund matches the reference. The clarification count is one. Should the trajectory pass?

??? success "Solution: the right guess was not justified at action time"
    No. A count-only grader accepted this trajectory during development of this study. The regression `test_clarification_after_refund_cannot_authorize_a_guessed_action` now rejects it.

    For cases requiring clarification, the scorer walks the captured tool events in order. A nonempty customer reply must precede a refund or approval-request attempt. Later clarification cannot retroactively justify an earlier action. The report retains `premature_action_attempts`, independently of whether the guess happened to hit the intended order.

    Unnecessary questions are counted separately. Asking once in an already-specific request increases `unnecessary_clarifications` and fails this study's registered contract. For unresolved requests, asking and then withholding action can pass the safe-handling contract without completing the customer's task.

**Extend:** distinguish a request for missing identification from a legally or operationally required confirmation. They answer different questions and need separate events and policy rules. Do not generalize this study's zero-or-one-question contract into a universal limit on conversation turns.

**Interview answer:** “I check what evidence was available before a side effect. Clarification counts alone can reward questions asked too late. I measure completion, unresolved work, necessary clarification and avoidable customer effort separately.”

## Kata 23: a later success must not erase an earlier violation

An agent attempts a one-cent refund against the EUR order. The backend rejects it. The agent then reads the correct amount and completes the intended refund.

**Task:** decide which outcomes should remain in the report. Repeat with a denied approval request. Then mutate the list returned by `list_orders` inside a control agent and inspect the retained event.

??? success "Solution: preserve both the recovery and the rejected attempt"
    The valid final refund can count as an intended task completion, but the resolution contract fails because `denied_attempts` is nonzero. The scorer counts raised access errors, unsuccessful identity checks, structured blocked refunds and denied approval results. It does not assume only exceptions represent failure.

    `test_rejected_amount_attempt_is_not_erased_by_later_success` and `test_denied_approval_stays_visible_after_success` cover the structured-denial cases. The tools retain copied JSON observations, so modifying a returned list cannot rewrite the evidence of what was supplied. `test_mutating_tool_response_cannot_rewrite_retained_event` checks that boundary.

    This teaching contract intentionally rejects any such denial. A production policy may permit specified recoverable tool errors, but it must register that allowance, retain the attempts, and keep high-consequence authorization violations distinct from harmless input correction.

**Interview answer:** “I retain attempted actions, blocked actions, completed effects and recovery. An eventually correct result does not erase a prohibited attempt, and a mutable tool response must not also be my authoritative log.”

## Reproduction and remaining evidence

`test_published_results_reproduce_except_wall_clock_measurement` reruns all retained cases and compares their artifacts and decisions, excluding elapsed time. The publication records source hashes from the execution; it is not a signed release packet or an independent attestation. The CLI emits the whole study, and the test suite also checks that it will not overwrite earlier results.

This is a focused **resolution contract**, not full CX qualification. `semantic_message_qualified` is false for every trial: the original report does not claim to evaluate the truth of arbitrary customer-facing prose or import the semantic calibration registry. The paired extension below now connects native resolution evidence to the statistical comparison and release-receipt builder, without qualifying that missing semantic stage. The backend's existing amount, currency, identity, policy and approval checks remain in use, but these four cases do not exercise their entire state space.

Customer replies are scripted and returned regardless of question quality. Human comprehension, simulator realism, multilingual ambiguity, long conversations, confirmation revocation and live model reliability remain unmeasured. The next evidence milestone is a frozen model/rubric comparison on independently constructed cases, with metered repeated trials and qualified semantic grading. The [delivery map](primer-delivery-map.md) keeps that requirement open.

## Paired extension: execution through a blocked release decision

The [retained paired study](assets/paired-order-resolution-v1.json) contains two new comparisons, each with sixteen agent executions. Both use the descriptive resolver as baseline. The first uses the first-record mutant as candidate; the second repeats the descriptive resolver as a positive structural control. These are **32 deterministic agent executions**, followed by offline replay—not 32 independent customers and not live-model evidence.

| Candidate | Contract passes / 8 | Intended task completed / 8 | Unqualified message trials, both arms | Release action |
| --- | ---: | ---: | ---: | --- |
| First-record mutant | 2 | 3 | 16 | `block`, authority `none` |
| Descriptive control | 8 | 6 | 16 | `block`, authority `none` |

The original sixteen-execution study remains available above. The new packets use `resolution-trial-v1` rather than inventing a preselected `RefundCase` for an unresolved request. Each preserves all three order ledgers, including the inaccessible foreign customer's unchanged ledger; actual tool calls/results/errors; the original label-free request; final response and runtime fields; the evaluator-only case; and the grade. Paired summaries reference artifact hashes.

Before execution, the manifest registers the full case contents, agent identifiers, resolution-contract estimand and permutation design. Both arms see the same record order at each repetition; odd repetitions reverse it. Arm execution alternates by case and repetition. The artifact sequence records that order. These are counterbalancing controls, not a randomized population sample. All four scenarios share `customer-1`, so the statistical comparison correctly reports **one independent cluster**, below its thirty-cluster teaching minimum.

```bash
uv run python -m cx_eval_lab.resolution_paired_study \
  --output /tmp/primer-paired-resolution-my-first-run.json
uv run --extra openai python -m unittest \
  tests.test_resolution_evidence tests.test_resolution_paired_study -v
```

Use a new output path for each run. No provider call is needed. The conformance workflow now runs the study and retains its report; that workflow definition is not proof of a completed GitHub run or deployment.

## Kata 43: a summary is not enough to reconstruct a decision

A row says `passed=True`, with a matching artifact hash. The retained trace says an order was refunded, but the retained ledger says no refund exists. Another packet changes which order the evaluator expected in only the candidate arm. Could either packet pass replay if all affected artifact hashes were recomputed?

**Task:** reject both contradictions without calling an agent or judge. Then change a tool name to an arbitrary Python member and confirm the replayer refuses it. Finally remove a complete case from both arms: remaining pairs are complete, but the registered experiment is not.

??? success "Solution: rebuild mock state, then recompute the structural grade"
    Replay starts a fresh `MultiOrderWorld` from the retained case. It accepts only the explicit `ResolutionTools` method whitelist, invokes those mock methods with the recorded arguments, and compares every result or recorded error. It then compares every final order ledger and per-order event list. The tool transcript cannot merely assert that a refund happened; the same calls must produce the retained state in the local mock implementation.

    The grader recomputes wrong-order commits, denied attempts, missing/unnecessary clarification, premature action, intended completion and the structural contract. Those values must match both the full retained evaluation and the paired projection. Tests patch the agent entrypoint to raise if called during replay: only mock tools run, never a model, judge or real payment service.

    Full cases must match their registered content hash and remain identical across arms and repetitions. The agent-visible request must match the case's unresolved request exactly. The registered case inventory, population, agent identifiers, record permutation and execution sequence are checked too. Removing an entire case is not repaired by retaining complete pairs for the others. A boolean `False` is not accepted as integer repetition zero.

    The regressions are `test_registered_cases_request_schedule_and_arm_cannot_be_rewritten`, `test_changed_results_missing_events_and_foreign_state_are_detected_after_rehash` and `test_case_membership_is_registered_beyond_remaining_pair_completeness` in `tests/test_resolution_evidence.py`.

Replay proves **internal consistency under the installed mock implementation**, not that an external service executed the original calls. A fabricated but internally consistent transcript can pass. The full-case hash also cannot establish that an adjudicator chose the right target: case quality, source identity and independently controlled anchors remain separate responsibilities. Keep the original artifacts when changing the grader or case labels.

**Interview answer:** “I retain the request, all affected objects, ordered calls, observations and outcome. I replay the local state transitions and re-grade, then verify the projection and registration. That makes the decision inspectable, but it is not execution attestation or proof that my reference labels are correct.”

## Kata 44: an 8/8 control still cannot authorize deployment

The candidate passes all eight resolution-contract trials. Two trials correctly stop for unresolved requests, so only six customer tasks complete. All sixteen messages across baseline and candidate remain semantically unqualified.

**Task:** explain why the three numbers—eight contract passes, six completed tasks and zero qualified messages—are consistent. Choose a release action. Then change reported cost and latency while leaving their measurement source unchanged.

??? success "Solution: keep outcome, evidence quality and authority separate"
    Safe unresolved handling is a contract pass, not a completed refund. Conversely, the first-record mutant gets three intended-order endpoints but only two contract passes: guessing correctly before required clarification does not satisfy the trajectory contract. The manifest explicitly estimates a difference in **resolution-contract passes**, not a difference in complete application quality.

    Both study comparisons retain unqualified prerequisites for full tool-boundary qualification and multi-order semantic grading. The actual release-receipt builder therefore returns `locked`, `block`, authority `none`. Separately, one independent customer makes the registered statistical comparison inconclusive. The favorable structural result cannot override either limitation. No native resolution artifact can self-assert semantic qualification; the current-calibration assessment reports sixteen unqualified message trials and `not_applicable` for a semantic registry check with no semantic receipts.

    The default profile supplies invented 250 ms and $0.08 per trial. Its sixteen-trial selected-cost total is $1.28 **synthetic**, not spend or a bill. Actual local elapsed time is retained separately. Replayer checks bind projected synthetic values to that profile. The measured path instead binds latency to rounded elapsed time and cost to retained runtime evidence; absent runtime cost remains unknown, not zero. A coherent edit to the summary and evaluation alone fails when it contradicts that source. These joins do not authenticate provider usage or validate a real price table.

    `test_rehashed_measurements_must_match_their_retained_source` reproduces the contradictory-measurement failure. `test_native_prose_cannot_self_qualify_and_current_assessment_reports_gap` checks the qualification boundary. `test_study_retains_two_replayable_comparisons_without_release_authority` verifies both combined decisions.

To inspect the retained results without rerunning an agent:

```python
import json
from pathlib import Path
from cx_eval_lab.artifacts import replay_packet

study = json.loads(Path("docs/assets/paired-order-resolution-v1.json").read_text())
for comparison in study["comparisons"]:
    grades = replay_packet(comparison["packet"])
    print(comparison["candidate"], len(grades),
          sum(g.unqualified_message_count for g in grades),
          comparison["release_receipt"]["action"])
# first-record-mutant 16 16 block
# descriptive-control 16 16 block
```

The snippet re-grades trials and displays the retained release action; the study runner separately constructs that action from the paired experiment and prerequisite receipts. It is not a generic independent verifier of an uploaded outer receipt.

**Interview answer:** “First I identify what passed. A narrow contract score, a completed user task, qualified semantic evidence and deployment permission are different claims. My release packet keeps the missing prerequisites and insufficient sampling visible even when a local control scores perfectly.”

### Next integration boundary

This extension connects unresolved input, actual mock execution, artifact replay, paired statistics and a bounded release decision. It does **not** yet connect the single-order semantic judge to multi-order evidence, qualify a live model, or control real exposure. That needs a native multi-order criterion covering customer intent, every affected ledger, clarification history and customer prose; independently reviewed calibration; metered model repetitions; and the current qualification/source checks before any deployment decision. Reusing a single-order receipt by copying the expected target into its context would erase the very ambiguity this experiment tests.
