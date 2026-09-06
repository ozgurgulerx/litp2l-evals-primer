# Long-running agents, human control, and serving failures

A long-running agent is not merely a longer prompt. Its correctness depends on what survives compaction, which effects survive process failure, whether approvals remain valid, and how the system behaves when providers or tools degrade. Evaluate those transitions directly.

The buildable scorer protocol in `cx_eval_lab/advanced.py` compares typed uninterrupted, compacted, restarted, and resumed observations supplied to it. It is intentionally provider-neutral: the contract concerns preserved state and effects, not a particular memory product. A process-level runner that produces those observations is still required.

## Define the durable state

At every checkpoint, separate four ledgers:

| Ledger | Examples | Required property |
| --- | --- | --- |
| Constraints | customer identity, currency, maximum refund, prohibited actions | Preserved exactly or made stricter |
| Approvals | approver, object, amount, currency, expiry, policy version | Bound to the action and revalidated after relevant change |
| Completed effects | refund transaction, ticket creation, email sent | Never repeated merely because acknowledgement was lost |
| Unfinished work | notify customer, await review, reconcile status | Survives compaction and resume until explicitly completed or cancelled |

Conversation text is not the ledger. A summary can be readable while dropping the one approval constraint that prevents an unauthorized action.

### Checkpoint contract

```yaml
run_id: cx-817
checkpoint: 004
manifest_hash: sha256:...
constraints:
  - verified_customer: customer-17
  - maximum_refund: {amount_cents: 4000, currency: USD}
approvals:
  - id: approval:order-817:4000:USD
    policy_version: refund-policy-v7
completed_effects:
  - idempotency_key: refund:order-817
    authoritative_status: committed
unfinished_work:
  - notify_customer_of_submitted_refund
content_hash: sha256:...
```

The content hash prevents a resume operation from silently replacing a previously recorded fragment. A manifest mismatch aborts the run because “resume” under a different model, tool schema, or policy is a new experimental condition.

## Four-arm persistence experiment

Run the same task under matched budgets:

1. **Uninterrupted:** no compaction or process restart.
2. **Compacted:** replace older context with the production summarisation policy.
3. **Restarted:** reconstruct state from the durable checkpoint in a new process.
4. **Interrupted after commit:** crash after the external action commits but before the agent receives acknowledgement, then resume.

For each arm, measure constraint retention, approval validity, completed-effect retention, unfinished-work retention, duplicate effects, recovery turns, final outcome, latency, and cost. Pair trials by case and stochastic replicate.

The central invariant is not “the agent remembers the conversation.” It is:

> A compaction or restart must not weaken constraints, revive completed effects, erase unfinished work, or convert an ambiguous external result into permission to retry.

### Mutants that must fail

- Drop the currency from the compacted approval.
- Retain the approval but change the amount.
- Forget that a refund committed before the timeout.
- Mark customer notification complete when it remains unfinished.
- Resume the same run identifier with a different manifest.
- Replay an already committed action with a new idempotency key.

The artifact `evals/cx-support/examples/advanced-protocols-v1.json` includes a safe-resume fixture and a broken compacted-resume fixture. The latter declares lost approval, lost unfinished-work state, and a repeated transaction; the scorer rejects it. This validates the scorer contract, not an agent's persistence behavior or a live reliability estimate.

## Human approval is state, not a conversational phrase

An approval record should include:

- who or which policy authority approved;
- exact customer and object scope;
- amount and currency;
- permitted action;
- policy version;
- issue and expiry time;
- facts whose change invalidates it.

Evaluate delayed approval, denial, expiry, duplicate response, changed order state, and restart while approval is pending. A response such as “approved” in the transcript is not sufficient evidence; the action boundary must validate the structured approval.

## Human–agent collaboration outcomes

Humans are participants in the workflow, not merely graders. Compare agent-only, human-only where feasible, and human-plus-agent conditions on:

- verified completion and time to completion;
- clarification turns and unnecessary approval requests;
- escalation precision and recall;
- handoff completeness;
- reviewer corrections;
- unresolved work at timeout;
- human handling minutes and recovery effort;
- errors introduced after the human intervenes.

An agent that sends every request to review may have zero automated policy violations while making the service worse. The CX evaluator therefore reports `human_intervention_count`, `unresolved_work_count`, and `unjustified_escalation_count` separately from verified task success.

## Serving failures are behavioral interventions

Provider reliability changes the system a customer experiences. Inject failures at exact transition points:

| Injection | Semantic risk | Required observation |
| --- | --- | --- |
| Throttling before generation | queueing, timeout, premature fallback | end-to-end latency and selected policy path |
| Timeout before tool call | incomplete task | safe retry or explicit unresolved status |
| Timeout after commit | duplicate side effect | authoritative state inspection before retry |
| Partial stream | customer sees an unfinished promise | emitted tokens and whether action already started |
| Fallback model | different tool or safety behavior | same contract and a pinned fallback manifest |
| Tool degradation | stale or missing evidence | fail-closed behavior and useful handoff |

The serving protocol rejects fallback after streaming has begun unless the application has an explicit, tested continuation design. Otherwise customers can receive two incompatible answers or a second model can act on a state it did not create. Sierra's [model failover description](https://sierra.ai/blog/model-failover) is a useful operational reference for prevalidated alternatives and constrained switching; it does not grant this lab local authority.

## Fallback experiment

Use a matched matrix:

| Arm | Primary | Failure | Fallback | Question |
| --- | --- | --- | --- | --- |
| A | model P | none | none | Reference behavior |
| B | model P | throttle before output | model F | Does fallback preserve the contract? |
| C | model P | partial stream | blocked | Does the system end safely and explain incompletion? |
| D | model P | timeout after commit | same model after inspection | Is the effect exactly once? |
| E | model P | degraded policy tool | none | Does the system avoid inventing eligibility? |

Report results by path. A strong normal-path average cannot compensate for an unsafe fallback path.

## Evidence added in this chapter

- **Executable scorer fixtures:** persistence and serving-failure protocols in `cx_eval_lab/advanced.py`.
- **Caught fixture mutations:** lost approval, lost unfinished work, duplicate effect, blind retry, and fallback after stream start.
- **Demonstrated scorer behavior:** deterministic pass/fail and counts over hand-authored observations; no runtime measurement was made.
- **Limitation:** no process-level crash harness, live provider fault injection, timed human study, or production transfer evidence yet.
- **Authority:** `lab_only`.

## Exercise: commit without acknowledgement

The refund provider commits transaction `r-817`, but the request times out. The process restarts from a checkpoint written just before the tool call. What evidence is needed before another refund attempt?

??? success "Answer"
    Query authoritative provider state using the stable order and idempotency identity. Do not infer failure from the missing acknowledgement. Reconcile the returned transaction with the durable effect ledger, record the completed effect, and then resume unfinished work such as customer notification. If authoritative state cannot be read, escalate as unresolved; do not issue another payment under a new key.
