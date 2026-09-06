# Follow one CX evidence packet

Sixteen trial records pass. The release decision is still `hold`. This is not a contradiction: passing constructed examples, qualifying a measuring instrument, establishing a population comparison and authorizing traffic are different claims.

This walkthrough follows one refund request through the existing multi-order system. It joins the chapters into a runnable route rather than introducing another harness. By the end, you should be able to locate the evidence behind a grade, explain its qualification limits and defend the resulting release decision.

!!! warning "What actually executes"
    The agent is a deterministic description-matching control, the business tools are mock services, and the installed OpenAI SDK receives synthetic HTTP responses from an in-memory transport. No model inference or paid call occurs. Calibration labels, reviewers, prices, prerequisite assertions and clocks are teaching fixtures. Actual local code executes and source bytes are checked; real model capability and deployment readiness are not established.

## Choose the right route

| Your immediate question | Entry point | What it demonstrates |
| --- | --- | --- |
| How do I write my first grader? | [Five-case CX lab](build-the-system.md#run-it-locally) | Deterministic invariants and known-bad mutants |
| How do the evidence components join? | This walkthrough and `current_release_study` | Multi-order execution, semantic-stage plumbing, accounting, replay and current decision |
| Does a real model perform well? | A separately registered, budgeted study | Still requires actual calls, representative cases and independent calibration; the first two routes cannot answer it |

Run the joined study from a controlled checkout, using a new output path:

```bash
uv sync --locked --extra openai
uv run --locked --extra openai python -m cx_eval_lab.current_release_study \
  --output /tmp/primer-cx-walkthrough-my-first-run.json
```

The command registers the checkout's current commit, executes a **new** experiment and compares source files with committed bytes. Do not edit package source or locked inputs and then expect source consistency to pass. The CLI preserves a failed report and returns nonzero when its registered controls do not reproduce. A successful exit means the controls behaved as expected, including the release hold and six blocks; it does not mean “ship.”

On 7 September 2026, a clean local clone at `4ed96a785600c75149f7cb1d966d2dc14d8a9e9a`, with a newly created locked environment, reproduced those seven decisions. This is a local reproducibility check, not an independent audit or cloud CI observation. The examples below inspect the already [retained v2 packet](assets/current-release-study-v2.json), whose original source revision is `96c76da0d02804fcea846f6e1b0de0e534afabe9`. Inspecting an old record does not claim that today's checkout is its original source. Exact source-checked reproduction requires the recorded revision; rerunning today's command creates a differently identified experiment.

## Kata 58: reconstruct one grade from its evidence

**Know:** a case label, agent-visible input, observed state and grade have different owners. The harness may know the expected order; the agent must resolve it from permitted information.

**Task:** find candidate repetition zero of `ambiguous-description`. Identify what the agent saw, why it asked a question, which order changed, and what supports the customer explanation. Join the paired row to the full artifact by hash, not array position.

Run these Python blocks in the same session from the repository root:

```python
import json
from pathlib import Path
from cx_eval_lab.evidence import canonical_hash

study = json.loads(Path("docs/assets/current-release-study-v2.json").read_text())
packet = study["packet"]
matches = [row for row in packet["candidate_trials"]
           if row["case_id"] == "ambiguous-description" and row["trial_index"] == 0]
assert len(matches) == 1
paired = matches[0]
artifacts = [a for a in packet["trial_artifacts"]
             if a["artifact_hash"] == paired["artifact_hash"]]
assert len(artifacts) == 1
trial = artifacts[0]["payload"]
assert canonical_hash(trial) == paired["artifact_hash"]
assert trial["identity"]["arm"] == "candidate"
print(trial["agent_input"])
print([event["tool"] for event in trial["tool_events"]])
print([(row["order"]["order_id"], row["state"]["refund_transaction_count"])
       for row in trial["orders"]])
```

??? success "Solution: follow intent, action, state and explanation separately"
    The input is customer `customer-1` asking “Refund my blue backpack.” It contains no evaluator target designation. `list_orders` returns two owned backpacks with different purchase dates. The agent asks which item/date the customer means; the scripted answer specifies 1 August. It then verifies identity, reads `order-a`, consults policy and requests a 4,000-cent USD refund with key `refund:order-a`.

    The final transaction counts are `order-a: 1`, `order-b: 0`, `order-c: 0`. Inspect all ledgers: a correct transaction on A would not excuse an extra transaction on B. The structural checks cover wrong-order commits, missing and unnecessary clarifications, denied attempts and premature actions. Customer intent is graded independently of the server's authorization boundary: another owned order could be authorized yet wrong for this request.

    The output says “Your refund has been confirmed,” with transaction status `committed`, settlement status `not_claimed` and no arrival commitment. A mock ledger commit does not prove funds have settled. The native semantic stage records a judgment against the complete situation, not the enum alone. Its context-bound receipt and raw judge response are retained. In this study that response is scripted; it tests integration, not natural-language accuracy.

    The hash join only checks consistency with the loaded record. A producer that controls the record and its anchor could rewrite both. This inspection is not full re-grading or authenticated provenance. The [evidence spine](evidence-spine.md#kata-50-successful-replay-is-not-permission-for-a-new-release) explains the separate replay and trusted-operator-input checks performed by the runnable study.

**Extend:** compare a wrong-but-authorized order with a foreign customer's order. Which should the server reject, and which must the evaluator detect even if the server permits the action? Then remove the clarification from an ambiguous request. A good grader must detect premature action, not merely check the final response wording.

**Interview answer:** “I join the compact score to its full execution. I separate object resolution from authorization, inspect every affected ledger and bind explanation grading to the exact request, trace and final state.”

## Locate the qualification and cost evidence

| Evidence needed | Location in this packet | Important distinction |
| --- | --- | --- |
| Agent-visible request | `trial.agent_input` | `trial.case.expected_order_id` is harness-only ground truth |
| Actual mock-tool calls and state | `trial.tool_events`, `trial.orders` | A response enum is not proof of a side effect |
| Prose and structured claims | `trial.output` | Committed does not mean settled |
| Bound judgment | `trial.semantic_evaluation_receipt` | Binds message, claims, context, criterion, evaluator and calibration |
| Judge request/response and usage | `study.transport`, `trial.semantic_stage.judgment` | SDK response fields here come from a mock transport |
| Qualification evidence | `study.calibration`, `trial.semantic_stage.qualification` | Admission with synthetic diagnostics enabled is not human calibration |
| Paired summary and manifest | `packet.candidate_trials`, `packet.manifest` | Compact rows reference full artifacts rather than replace them |
| Current decision components | `study.assessments[*].assessment.checks` | Historical grades and current eligibility can differ |

There are two policy identities: manifest `policy_version` names the release contract, while semantic registration `policy_version` names the domain policy being judged. They are intentionally different. Joining them as though they were the same field would reject correct evidence or qualify the wrong criterion.

The calibration fixture has two truthful and two false examples, with zero observed errors. Its reported class-error upper bounds are nevertheless about **77.6%**. The deliberately permissive 80% fixture threshold allows the integration controls to run; it is not a defensible production tolerance. Do not relabel these rows as independent human evidence or reuse them as sealed acceptance data. See [calibration ingestion](semantic-grading-lab.md#kata-18-reconstruct-calibration-from-the-labels) for the row-to-registry method.

Cost also has distinct meanings. Sixteen synthetic agent profiles contribute $1.28. Sixteen mocked judge calls contribute an estimated $0.00576 under invented token rates. Four separate calibration calls are outside that paired-run total, as are human and infrastructure costs. The 250 ms per-case profile is synthetic; `elapsed_ms` records local control execution, not model-service latency. Neither number is production performance evidence.

## Kata 59: all trials pass—what may we release?

**Know:** repetitions do not create independent customers, and a valid old judgment is not permanent qualification.

**Task:** explain the current hold and the revoked-calibration block without changing any historical trial grade. Identify what must change before a real canary can be considered.

```python
decisions = {row["name"]: row["assessment"] for row in study["assessments"]}
current = decisions["current-diagnostic"]
comparison = current["checks"]["base_receipt"]["comparison"]
assert current["checks"]["replay"]["replayed_trials"] == 16
assert current["checks"]["replay"]["failed_trials"] == 0
assert comparison["pair_count"] == 8
assert comparison["independent_cluster_count"] == 1
assert comparison["status"] == "inconclusive"
assert current["action"] == "hold"
assert decisions["revoked"]["action"] == "block"
assert decisions["revoked"]["checks"]["replay"]["failed_trials"] == 0
assert all(d["deployment_authorized"] is False for d in decisions.values())
```

??? success "Solution: preserve the grades and restrict the decision"
    Four cases times two repetitions times two arms produce sixteen executions and eight pairs—but every case belongs to one customer. Baseline and candidate are the same deterministic control. Both rates are 1.0 and the point difference is zero. The registered comparison lacks independent evidence and returns no interval: it is inconclusive. Passing bookkeeping and replay cannot repair that limitation.

    The registry is current only at the exercise's frozen diagnostic clock. Revoking its calibration leaves the sixteen historical grades intact but blocks using that qualification now. Expiry, disallowing synthetic labels, wrong source revision, changed case inputs and unqualified application prerequisites also block for their own reasons. None of these seven conditions grants deployment authority.

    Do not fix the hold by lowering the cluster minimum, changing customer IDs or loosening qualification tolerances after seeing the data. Collect genuinely independent observations under a registered sampling design, qualify the chosen statistical method for its intended regime and obtain independent grader calibration. Thirty clusters is not itself proof that a clustered normal interval has acceptable coverage; sparse and all-tie outcomes remain important counterexamples.

    A real canary additionally needs an approved candidate, environment and exposure policy; current authoritative prerequisites; hard action budgets; mature outcome feedback; a rollback target; and an independently enforceable stop path. The [Exposure Control Lab](exposure-control-lab.md) teaches those transitions in simulation. It is not connected to this receipt as an authorized real-traffic router. Book publication CI, application qualification and traffic authority remain separate.

**Interview answer:** “All trial grades can pass while the release holds. I need independent population evidence and current evaluator qualification, then a separate controlled deployment contract. I preserve historical results when revocation changes what they justify today.”

## What to do next

To turn trace inspection into a failure taxonomy and repair decision, use [Katas 66–67](dataset-design.md#mixed-trace-workshop-observations-before-causes). The mixed-trace workshop keeps observations separate from proposed causes and demonstrates why safe non-completion, lucky endpoints and repeated symptoms need different treatment.

For pair-level diagnosis of the native workflow, continue with [Katas 64–65](order-resolution-study.md#native-paired-diagnostics-separate-the-action-from-the-explanation). They replay the retained semantic controls into separate structural and joint comparisons and exploratory clarification slices, without rewriting the original evidence or release decisions.

Use [dataset design](dataset-design.md) to replace constructed cases with a versioned, reviewed sampling plan; use [semantic grading](semantic-grading-lab.md) to qualify the instrument; use [statistical studies](statistical-method-study.md) to challenge the proposed inference. Then take an approved application through [CI gates](ci-gate-lab.md) and the [exposure-control protocol](exposure-control-lab.md). The local demonstration supplies a working evidence chain and inspectable failure controls. The empirical qualification and real deployment remain work to perform, not authority inherited from this book.
