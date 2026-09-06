# Micro-katas: learn by breaking and repairing an evaluation

Each kata asks you to predict a result, run a small experiment, explain the failure, and inspect a solution. The reference solution remains working. Try your changes in a separate branch or scratch copy, then use the regression tests to check your reasoning.

These first three katas exercise real defects found in the refund grader. They use synthetic customers and local code; no model key is needed. Run commands from the repository root after `uv sync --group dev`.

## Kata 01: a trusted sentence that lies

**Know first:** transaction correctness and explanation correctness are separate evaluation surfaces. A registered message template establishes wording; its factual prerequisites establish whether that wording is true here.

**Situation:** identity verification succeeds, the order is read, and the policy says the order is ineligible. No refund occurs. An agent returns:

```python
AgentOutput(
    message="I could not verify the account.",
    claimed_outcome="not_refunded",
)
```

**Predict:** should the outcome grader pass? Should the whole case pass? What changes if the message is “The refund needs human approval”?

**Task:** write the smallest prerequisite table that rejects both false explanations while accepting “The order is not eligible.” Include a case where verification succeeded earlier but has since been revoked.

**Run the executable solution checks:**

```bash
uv run python -m unittest tests.test_template_facts -v
```

The historical grader accepted both false explanations. The repaired grader rejects them through `template_factual_prerequisites`. The valid ineligibility explanation passes. Current identity state overrides historical success when evaluating authorization readiness.

??? success "Solution and reasoning"
    For the account-verification sentence, require evidence of failed verification and absence of a current verified binding. For pending approval, require an eligible order above the approval threshold, a current identity and policy binding, no current applicable approval, and a review outcome. For ineligibility, require a current policy lookup identifying the order as ineligible. An execution-failure sentence requires an execution failure.

    The implementation is `_template_facts_match` in `cx_eval_lab/evaluators.py`; the regression cases are in `tests/test_template_facts.py`. A false template must fail even when the transaction count is correct. Missing evidence is not proof of the negative claim.

**Extend:** add an eligible high-value case whose approval has already been granted. Explain why “needs human approval” is stale. Then add denied approval and distinguish denial from pending approval.

**Interview answer to know:** “I grade the backend effect and customer explanation independently. Templates reduce language variability, but every factual statement still needs object-scoped, current evidence. I test the grader with false explanations that share the correct outcome enum.”

**Evidence limit:** the checks validate this mock world's represented facts. They do not establish the truth of arbitrary natural language or the validity of a production identity system.

## Kata 02: the same message in a different situation

**Know first:** a semantic judgment is a function of the output, supplied evidence, rubric, evaluator configuration, and qualified scope. A message hash alone cannot bind its truth to a customer situation.

**Situation:** “Instruction recorded” is judged against a trace with one committed refund. Copy the passing receipt to a case with no committed refund, keeping the wording identical.

**Predict:** which hashes stay the same? Which evidence must invalidate the copied receipt?

**Task:** define a canonical evidence packet including case identity, customer request, dataset version, policy version, ordered tool events, final state, and execution error. Hash the structured outcome and escalation claims as well as transaction, settlement, and arrival claims.

```bash
uv run python -m unittest tests.test_semantic_context -v
```

The tests first accept a correctly bound receipt, then change one dimension at a time: case identity, customer wording, trace, final state, and policy. Each changed context is unqualified. Legacy receipts without a context hash remain readable but cannot qualify a new judgment.

??? success "Solution and reasoning"
    Compute `hash_evidence_context(case, events, state, policy_version=...)` in the evaluator, and compare it with `receipt.evidence_context_hash`. Separately compare message and complete structured-claim hashes. Require a permitted calibration receipt, the correct criterion, a passing decision, and no abstention.

    See `hash_evidence_context`, `hash_structured_claims`, and `_semantic_receipt_qualifies` in `cx_eval_lab/evaluators.py`. The test's accepted calibration hash is a synthetic fixture, not human qualification evidence. The [Semantic Grading Lab](semantic-grading-lab.md) now adds registry checks for evaluator configuration, criterion, joint scope, expiry, revocation, error bounds, and abstention.

**Extend:** alter only the escalation reason. Then reorder two tool events. Both changes must invalidate the original judgment. Explain why reformatting a dictionary should not change a canonical hash, while changing event order should.

**Interview answer to know:** “I cache a judge result against the exact evidence packet and evaluator configuration, not just response text. Changed state or context requires re-grading. Content hashes establish identity and mutation detection; trusted provenance establishes who may issue the judgment.”

**Evidence limit:** this kata repairs receipt binding. The connected stage and registry are exercised separately in [Katas 08–10](semantic-grading-lab.md); a live judge and independent human calibration study remain delivery requirements.

## Kata 03: a point gain is not superiority evidence

**Know first:** observed improvement, uncertainty, and a release claim are different objects. A scalar threshold can test gate plumbing without establishing statistical superiority.

**Situation:** candidate success is 0.90 and baseline success is 0.85. The configured minimum gain is 0.02. No paired outcomes or confidence interval are supplied.

**Predict:** the arithmetic check passes. What claim does that support? What additional evidence would a superiority decision need?

```bash
uv run python -m unittest tests.test_illustrative_gain tests.test_trust_repair -v
```

??? success "Solution and reasoning"
    Name the scalar rule `illustrative_point_gain:task_success`. It checks whether the observed difference exceeds the configured floor. Keep its authority local to the lab. Statistical superiority requires an appropriate registered contrast, uncertainty method, sampling unit, stopping policy, and evidence that the lower bound exceeds the superiority boundary.

    For non-inferiority, an interval from −0.02 to +0.10 with a margin of 0.03 clears the inclusive lower-bound rule because −0.02 is above −0.03. It does not establish superiority because the interval includes zero. See [Metrics](metrics.md) and [Evidence Spine](evidence-spine.md).

**Extend:** change the lower bound to −0.031. Explain the resulting decision without saying the systems are equivalent or that the candidate is proven worse.

**Interview answer to know:** “I distinguish a point estimate from a statistical claim. I register the estimand, acceptable degradation, independent sampling unit, and stopping rule before seeing candidate results. Inconclusive evidence can justify holding exposure.”

## Kata 04: recompute a grade, not just an average

**Know first:** retaining `passed=True` lets you recompute a success rate, but not determine whether the original grader was correct. Independent re-grading needs the input, response, tool evidence, state, and grading configuration.

**Situation:** a report contains twenty paired trial summaries. Someone changes a customer message, drops a failed case from both arms, or copies a passing summary onto a different execution.

**Predict:** which changes would a row-count check detect? Which require a registered population hash? Why is checking an artifact hash insufficient if the editor can also change the hash?

**Task:** retain an immutable execution artifact for each trial; reference its digest from the summary. Validate identity links and reconstruct the deterministic evaluation. Calibration authority must be independently supplied, not asserted inside the packet.

```bash
uv run python -m unittest tests.test_trial_replay -v
uv run python -m cx_eval_lab experiment \
  --minimum-independent-clusters 5 \
  --output artifacts/runs/replay-kata-04.json
uv run python -m cx_eval_lab replay \
  --input artifacts/runs/replay-kata-04.json
```

Use a new output filename if it already exists: experiment artifacts cannot be overwritten. Five clusters here deliberately exercise a **synthetic lab pass**, not a statistically qualified promotion. Replay prints `replayed 20 trials; authority: lab_only; no model calls`.

??? success "Solution and reasoning"
    `TrialArtifact` in `cx_eval_lab/artifacts.py` stores canonical JSON. The runner retains the case, agent-visible input, initial/final state, ordered tool events, complete output including runtime evidence when available, measurements and provenance, execution error, semantic receipt slot, domain policy version, and original evaluation. Each artifact binds the arm, case, repetition, and manifest hash.

    `replay_packet` verifies hashes and identity links, rejects duplicate or missing references, reconstructs `evaluate_case` inputs, and compares the retained evaluation and summary with the recomputed result. It checks population membership against the manifest and requires both arms and all repetitions. It does not accept calibration authority merely because a packet lists a hash.

    Tests change messages, remove artifacts or whole cases, change summaries and manifest bindings, duplicate records, and attempt self-authorization. A fresh-process CLI test verifies portability and malformed-JSON rejection. Another test changes the message **and recomputes its hash**: replay still detects disagreement with the retained grade.

**Extend:** change the grader while retaining an old packet. Design a separate reassessment artifact referencing the original digest, old/new grader revisions, and changed checks. This version-migration workflow remains a next implementation step; never overwrite historical grades.

**Interview answer to know:** “I retain execution evidence separately from grader decisions. Replay validates references and recomputes grades under a pinned implementation. A digest detects changes relative to a trusted reference; it is not proof that a run happened, that world state was true, or that release is safe.”

**Evidence limits:** this is deterministic re-grading of retained mock-world executions, not agent re-execution or production attestation. The CLI uses the installed grader; it does not download or enforce its revision. Population validation covers case/customer/slice membership, not independent verification of every source-file hash. No semantic stage is selected in this CLI example, so receipts are null here; [Katas 08–10](semantic-grading-lab.md) exercise the connected optional stage. A party able to rewrite all evidence and trusted references can fabricate a self-consistent packet; external provenance and storage controls remain necessary.

## What comes next

[Katas 08–10](semantic-grading-lab.md) now exercise calibration bounds, scoped qualification, negative versus unknown judgments, and retained judge evidence. Their judge is a synthetic control double; live semantic accuracy remains unmeasured.

[Katas 05–07](statistical-method-study.md) now cover statistical false promotion, unequal-cluster estimands, and biased judge labels, with executed enumeration results and worked solutions.

The [delivery map](primer-delivery-map.md) tracks the complete book and interview-preparation objective. Upcoming katas deepen dataset improvement, human annotation, empirical judge calibration, general clustered/sequential inference, retrieval, process recovery, CI/CD, canary exposure, and frontier-risk decisions. Those further exercises remain pending until their runnable checks and worked solutions exist.
