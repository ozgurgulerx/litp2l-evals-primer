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

This is a focused **resolution contract**, not full CX qualification. `semantic_message_qualified` is false for every trial: the report does not claim to evaluate the truth of arbitrary customer-facing prose. It does not import the existing semantic calibration registry or paired statistical release gate. The backend's existing amount, currency, identity, policy and approval checks remain in use, but these four cases do not exercise their entire state space.

Customer replies are scripted and returned regardless of question quality. Human comprehension, simulator realism, multilingual ambiguity, long conversations, confirmation revocation and live model reliability remain unmeasured. The next evidence milestone is a frozen model/rubric comparison on independently constructed cases, with metered repeated trials and qualified semantic grading. The [delivery map](primer-delivery-map.md) keeps that requirement open.
