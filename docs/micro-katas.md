# Micro-katas: learn by breaking and repairing an evaluation

## Additional worked decision exercises

These unnumbered exercises supplement the existing numbered sequence; they do not change its IDs. Each includes a worked solution and explicit evidence limits.

| Exercise | Decision to defend |
| --- | --- |
| [Ratings versus independent cases](human-evaluation.md#worked-micro-kata-four-hundred-ratings-are-not-four-hundred-cases) | Budget reviewer overlap without overstating independent evidence or precision. |
| [Reviewer effects and treatment effects](human-evaluation.md#worked-micro-kata-separate-the-reviewer-from-the-treatment) | Explain why disconnected reviewer assignments cannot identify a model improvement. |
| [The winner of twenty prompts](metrics.md#worked-micro-kata-the-winner-of-twenty-prompts) | Keep the tested family intact when selecting the best-looking result. |
| [Semantic entropy and consistent errors](metrics.md#worked-micro-kata-different-words-same-uncertain-meaning) | Separate variation in wording, variation in meaning and verified truth. |
| [Assigned customers and human workload](production-evals.md#worked-micro-kata-the-assisted-cases-are-still-assigned-cases) | Reject a post-assignment dashboard gain that hides unresolved work and assistance burden. |
| [Judge lineage and panel errors](llm-as-a-judge.md#worked-micro-kata-hiding-the-name-does-not-test-every-preference-leak) | Separate identity intervention, generator-group association, shared errors and review load. |
| [Skill selection versus complete capability](modern-agent-architectures.md#worked-micro-kata-successful-selection-failed-capability) | Choose the correct denominators for activation, loading and execution. |
| [Voice timing uncertainty](modern-agent-architectures.md#worked-micro-kata-the-clocks-cannot-decide) | Distinguish an early action, uncertain event order and valid authorization. |
| [Interrupted effect to rollback receipt](exposure-control-lab.md#executed-integration-interrupted-effect-to-rollback-receipt) | Preserve missing completion while restricting exposure after an observed violation. |
| [Eight-lab completion defense](courses.md#the-supplied-reports-eight-lab-completion-path) | Distinguish studying a worked method from collecting the evidence required to complete its empirical lab. |

## Numbered kata sequence and capstone

After the individual exercises, use the [release-decision capstone](capstone.md) to connect them: inspect three retained artifacts, submit a bounded decision, and revise it under three pressure variants. A complete worked memo and evidence index are supplied.

Each kata asks you to predict a result, run a small experiment, explain the failure, and inspect a solution. The reference solution remains working. Try your changes in a separate branch or scratch copy, then use the regression tests to check your reasoning.

These first three katas exercise real defects found in the refund grader. They use synthetic customers and local code; no model key is needed. Run commands from the repository root after `uv sync --group dev`.

[Kata 95](exposure-control-lab.md#kata-95-two-refunds-is-not-five-percent) injects a shared action/currency budget into the actual mock refund boundary. Four selected requests produce two refunds and two denials; baseline counterfactuals do not spend candidate allowance. Explain replay, uncertain commits, truthful responses and why unfinished work stays in the outcome denominator.

[Kata 94](metrics.md#kata-94-zero-ece-no-useful-ranking) reuses the ten probability-calibration examples: a hindsight constant gets zero empirical ECE while losing ranking, worsening Brier/log loss and automating nothing at the original threshold. The solution distinguishes calibration, discrimination, label reuse and operational utility.

[Kata 93](checklist.md#kata-93-a-comparison-is-not-evidence-validation) preserves and probes the shipping chapter's unsafe numerical shortcut. `NaN` and unsupported finite reports both produce its misleading `canary` string; the solution separates representation, measurement and authority, then maps the repair to existing labs and outstanding application integration.

[Katas 90–92](calibration-decision-workshop.md) connect judge confusion matrices, abstention, zero-event uncertainty, prevalence shift and human-review workload. Compute the supplied teaching scenario, defend the qualification HOLD, and specify the missing data instead of treating overall agreement as a release rule.

[Katas 87–89](coding-patch-study.md) add a second outcome domain: run authored Python patch controls against visible and separate acceptance tests, inspect caller-state changes and protected-test edits, then diagnose an incorrect acceptance assertion. Real subprocess execution does not turn authored patches into model-performance evidence.

[Katas 85–86](ci-gate-lab.md#kata-85-a-timeout-is-not-a-candidate-block) follow a real child-process timeout through partial evidence retention and distinguish candidate verdicts, conformance failure, upload eligibility and confirmed artifact storage. They do not authorize production deployment or claim durable recovery after runner loss.

## Complete practice index

All 105 numbered katas are linked below by topic. Numbers identify exercises; they are not prerequisites or a difficulty ranking. Use the [seven-checkpoint learning route](index.md#a-learning-route-with-evidence-checkpoints) for sequence, then return here to target a weak skill. The index includes both authored calculations and executed local studies: read each exercise's evidence limits before treating its result as a capability claim.

For each attempt, save your prediction, result or calculation, explanation under one changed assumption, and remaining evidence gap. Mark your own work **not attempted**, **reproduced**, **explained**, or **unresolved**. These learning statuses are not qualifications or deployment permissions. Finish with the [capstone](capstone.md), not a count of opened solutions.

### Contracts, execution evidence and object resolution

| Kata | Exercise |
| --- | --- |
| 01 | [a trusted sentence that lies](#kata-01-a-trusted-sentence-that-lies) |
| 02 | [the same message in a different situation](#kata-02-the-same-message-in-a-different-situation) |
| 03 | [a point gain is not superiority evidence](#kata-03-a-point-gain-is-not-superiority-evidence) |
| 04 | [recompute a grade, not just an average](#kata-04-recompute-a-grade-not-just-an-average) |
| 21 | [remove the answer from the experiment](order-resolution-study.md#kata-21-remove-the-answer-from-the-experiment) |
| 22 | [clarification must precede the consequential action](order-resolution-study.md#kata-22-clarification-must-precede-the-consequential-action) |
| 23 | [a later success must not erase an earlier violation](order-resolution-study.md#kata-23-a-later-success-must-not-erase-an-earlier-violation) |
| 32 | [reproduce yesterday without approving today](#kata-32-reproduce-yesterday-without-approving-today) |
| 33 | [a current evaluator can grade a failed trial](#kata-33-a-current-evaluator-can-grade-a-failed-trial) |
| 34 | [the version label did not change](#kata-34-the-version-label-did-not-change) |
| 35 | [the IDs match but the case changed](#kata-35-the-ids-match-but-the-case-changed) |
| 41 | [matching hashes, wrong evidence](evidence-spine.md#kata-41-matching-hashes-wrong-evidence) |
| 42 | [a clean component cannot promote a weak experiment](evidence-spine.md#kata-42-a-clean-component-cannot-promote-a-weak-experiment) |
| 43 | [a summary is not enough to reconstruct a decision](order-resolution-study.md#kata-43-a-summary-is-not-enough-to-reconstruct-a-decision) |
| 44 | [an 8/8 control still cannot authorize deployment](order-resolution-study.md#kata-44-an-88-control-still-cannot-authorize-deployment) |
| 45 | [four correct labels do not qualify a judge](order-resolution-study.md#kata-45-four-correct-labels-do-not-qualify-a-judge) |
| 46 | [joint success and current qualification are different decisions](order-resolution-study.md#kata-46-joint-success-and-current-qualification-are-different-decisions) |
| 49 | [matching a hash is not validating an input](evidence-spine.md#kata-49-matching-a-hash-is-not-validating-an-input) |
| 50 | [successful replay is not permission for a new release](evidence-spine.md#kata-50-successful-replay-is-not-permission-for-a-new-release) |
| 58 | [reconstruct one grade from its evidence](cx-evidence-walkthrough.md#kata-58-reconstruct-one-grade-from-its-evidence) |
| 59 | [all trials pass—what may we release?](cx-evidence-walkthrough.md#kata-59-all-trials-passwhat-may-we-release) |
| 64 | [the same failed-check name can mean different evidence](order-resolution-study.md#kata-64-the-same-failed-check-name-can-mean-different-evidence) |
| 65 | [a useful retrospective slice is not a registered release requirement](order-resolution-study.md#kata-65-a-useful-retrospective-slice-is-not-a-registered-release-requirement) |

### Datasets, human evidence and measurement qualification

| Kata | Exercise |
| --- | --- |
| 08 | [zero errors, insufficient qualification](semantic-grading-lab.md#kata-08-zero-errors-insufficient-qualification) |
| 09 | [false, unknown, and unqualified are different](semantic-grading-lab.md#kata-09-false-unknown-and-unqualified-are-different) |
| 10 | [preserve the judge's evidence without changing the customer metric](semantic-grading-lab.md#kata-10-preserve-the-judges-evidence-without-changing-the-customer-metric) |
| 18 | [reconstruct calibration from the labels](semantic-grading-lab.md#kata-18-reconstruct-calibration-from-the-labels) |
| 19 | [disagreement cannot disappear into an aggregate](semantic-grading-lab.md#kata-19-disagreement-cannot-disappear-into-an-aggregate) |
| 20 | [improve the dataset without contaminating qualification](semantic-grading-lab.md#kata-20-improve-the-dataset-without-contaminating-qualification) |
| 36 | [a passing JSON verdict is not a usable judgment](semantic-grading-lab.md#kata-36-a-passing-json-verdict-is-not-a-usable-judgment) |
| 37 | [timeout does not mean free—and token cost is not total cost](semantic-grading-lab.md#kata-37-timeout-does-not-mean-freeand-token-cost-is-not-total-cost) |
| 47 | [a new evidence domain needs a new qualification scope](semantic-grading-lab.md#kata-47-a-new-evidence-domain-needs-a-new-qualification-scope) |
| 48 | [an accounting pass is not a release pass](semantic-grading-lab.md#kata-48-an-accounting-pass-is-not-a-release-pass) |
| 60 | [an approved review of the wrong case](dataset-design.md#kata-60-an-approved-review-of-the-wrong-case) |
| 61 | [a new case ID does not make a fresh holdout](dataset-design.md#kata-61-a-new-case-id-does-not-make-a-fresh-holdout) |
| 66 | [a correct final state can conceal a broken process](dataset-design.md#kata-66-a-correct-final-state-can-conceal-a-broken-process) |
| 67 | [choose a repair without inventing prevalence](dataset-design.md#kata-67-choose-a-repair-without-inventing-prevalence) |
| 70 | [recover the target population without hiding the risk slice](dataset-design.md#kata-70-recover-the-target-population-without-hiding-the-risk-slice) |
| 71 | [a corrected point estimate still does not justify clearance](dataset-design.md#kata-71-a-corrected-point-estimate-still-does-not-justify-clearance) |
| 72 | [did agreement improve, or did the denominator change?](human-evaluation.md#kata-72-did-agreement-improve-or-did-the-denominator-change) |
| 73 | [a reviewer assignment creates a model advantage](human-evaluation.md#kata-73-a-reviewer-assignment-creates-a-model-advantage) |
| 74 | [a stable slot label can hide an unstable judgment](llm-as-a-judge.md#kata-74-a-stable-slot-label-can-hide-an-unstable-judgment) |
| 75 | [three votes can repeat one mistake](llm-as-a-judge.md#kata-75-three-votes-can-repeat-one-mistake) |
| 82 | [a failed check must reach the decision](semantic-grading-lab.md#kata-82-a-failed-check-must-reach-the-decision) |
| 90 | [choose the denominator before choosing the winner](calibration-decision-workshop.md#kata-90-choose-the-denominator-before-choosing-the-winner) |
| 91 | [zero false passes is not evidence of a 1% ceiling](calibration-decision-workshop.md#kata-91-zero-false-passes-is-not-evidence-of-a-1-ceiling) |
| 92 | [transport the error rates, not the headline accuracy](calibration-decision-workshop.md#kata-92-transport-the-error-rates-not-the-headline-accuracy) |

### Statistical decisions and benchmark interpretation

| Kata | Exercise |
| --- | --- |
| 05 | [thirty ties, unjustified certainty](statistical-method-study.md#kata-05-thirty-ties-unjustified-certainty) |
| 06 | [two correct averages, two different questions](statistical-method-study.md#kata-06-two-correct-averages-two-different-questions) |
| 07 | [more data, confidently wrong labels](statistical-method-study.md#kata-07-more-data-confidently-wrong-labels) |
| 28 | [count first crossings, not marginal passes](sequential-decisions-lab.md#kata-28-count-first-crossings-not-marginal-passes) |
| 29 | [build one valid sequential evidence process](sequential-decisions-lab.md#kata-29-build-one-valid-sequential-evidence-process) |
| 30 | [optional-stopping validity does not repair bad data](sequential-decisions-lab.md#kata-30-optional-stopping-validity-does-not-repair-bad-data) |
| 31 | [restarting a test is not free](sequential-decisions-lab.md#kata-31-restarting-a-test-is-not-free) |
| 62 | [an overall improvement conceals a regression](metrics.md#kata-62-an-overall-improvement-conceals-a-regression) |
| 63 | [missing support is not zero performance](metrics.md#kata-63-missing-support-is-not-zero-performance) |
| 81 | [equal accuracy, different evidence](benchmark-reproducibility.md#kata-81-equal-accuracy-different-evidence) |
| 94 | [zero ECE, no useful ranking](metrics.md#kata-94-zero-ece-no-useful-ranking) |

### Retrieval, research and coding outcomes

| Kata | Exercise |
| --- | --- |
| 51 | [the policy exists, but the query cannot find it](knowledge-action-study.md#kata-51-the-policy-exists-but-the-query-cannot-find-it) |
| 52 | [oracle evidence cannot repair a bad tool argument](knowledge-action-study.md#kata-52-oracle-evidence-cannot-repair-a-bad-tool-argument) |
| 53 | [do not turn constructed cases into a population claim](knowledge-action-study.md#kata-53-do-not-turn-constructed-cases-into-a-population-claim) |
| 68 | [why did increasing top-k reduce packed evidence?](rag-research-evals.md#kata-68-why-did-increasing-top-k-reduce-packed-evidence) |
| 69 | [repair packing without giving the retriever the answers](rag-research-evals.md#kata-69-repair-packing-without-giving-the-retriever-the-answers) |
| 76 | [four citations do not establish five claims](rag-research-evals.md#kata-76-four-citations-do-not-establish-five-claims) |
| 77 | [correct a false pass without rewriting history](rag-research-evals.md#kata-77-correct-a-false-pass-without-rewriting-history) |
| 78 | [the missing claims are part of the result](long-report-study.md#kata-78-the-missing-claims-are-part-of-the-result) |
| 79 | [covering the words is not splitting the claims](long-report-study.md#kata-79-covering-the-words-is-not-splitting-the-claims) |
| 80 | [true premises can lead to an unsupported recommendation](long-report-study.md#kata-80-true-premises-can-lead-to-an-unsupported-recommendation) |
| 87 | [two passing examples, an incomplete repair](coding-patch-study.md#kata-87-two-passing-examples-an-incomplete-repair) |
| 88 | [right answer, wrong side effect—or changed examiner?](coding-patch-study.md#kata-88-right-answer-wrong-side-effector-changed-examiner) |
| 89 | [when the acceptance test is wrong](coding-patch-study.md#kata-89-when-the-acceptance-test-is-wrong) |

### Recovery, isolation and evaluation operations

| Kata | Exercise |
| --- | --- |
| 11 | [kill after commit, before checkpoint](process-recovery-study.md#kata-11-kill-after-commit-before-checkpoint) |
| 12 | [revoked authority versus historical fact](process-recovery-study.md#kata-12-revoked-authority-versus-historical-fact) |
| 38 | [is an unknown bill free budget?](eval-operations-integrity.md#kata-38-is-an-unknown-bill-free-budget) |
| 39 | [retry after the worker disappears](eval-operations-integrity.md#kata-39-retry-after-the-worker-disappears) |
| 40 | [the cost report is incomplete—and so is the comparison](eval-operations-integrity.md#kata-40-the-cost-report-is-incompleteand-so-is-the-comparison) |
| 56 | [the worker is new, but the state is not](cross-run-isolation-study.md#kata-56-the-worker-is-new-but-the-state-is-not) |
| 57 | [blocking every read is not successful isolation](cross-run-isolation-study.md#kata-57-blocking-every-read-is-not-successful-isolation) |
| 83 | [flush succeeded, evidence disappeared](telemetry-delivery-study.md#kata-83-flush-succeeded-evidence-disappeared) |
| 84 | [feedback arrives before its trace](telemetry-delivery-study.md#kata-84-feedback-arrives-before-its-trace) |
| 99 | [the process died, but the allowance did not reset](process-recovery-study.md#kata-99-the-process-died-but-the-allowance-did-not-reset) |

### CI, exposure and release authority

| Kata | Exercise |
| --- | --- |
| 16 | [an expected rejection makes the test pass](ci-gate-lab.md#kata-16-an-expected-rejection-makes-the-test-pass) |
| 17 | [why a green job must not start a canary](ci-gate-lab.md#kata-17-why-a-green-job-must-not-start-a-canary) |
| 24 | [five percent is not a hard cap](exposure-control-lab.md#kata-24-five-percent-is-not-a-hard-cap) |
| 25 | [missing labels cannot disappear from the denominator](exposure-control-lab.md#kata-25-missing-labels-cannot-disappear-from-the-denominator) |
| 26 | [rollback is not containment or repair](exposure-control-lab.md#kata-26-rollback-is-not-containment-or-repair) |
| 27 | [recovery needs stronger evidence than a single green window](exposure-control-lab.md#kata-27-recovery-needs-stronger-evidence-than-a-single-green-window) |
| 85 | [a timeout is not a candidate BLOCK](ci-gate-lab.md#kata-85-a-timeout-is-not-a-candidate-block) |
| 86 | [the upload step is not a durable experiment ledger](ci-gate-lab.md#kata-86-the-upload-step-is-not-a-durable-experiment-ledger) |
| 93 | [a comparison is not evidence validation](checklist.md#kata-93-a-comparison-is-not-evidence-validation) |
| 95 | [two refunds is not five percent](exposure-control-lab.md#kata-95-two-refunds-is-not-five-percent) |
| 96 | [a hash is not a replay](exposure-control-lab.md#kata-96-a-hash-is-not-a-replay) |
| 97 | [the packet exists, but did CI verify it?](exposure-control-lab.md#kata-97-the-packet-exists-but-did-ci-verify-it) |
| 100 | [reopen the evidence, not just the balance](exposure-control-lab.md#kata-100-reopen-the-evidence-not-just-the-balance) |
| 101 | [reopen the allowance between exposure windows](exposure-control-lab.md#kata-101-reopen-the-allowance-between-exposure-windows) |
| 102 | [the charge survived, the response did not](exposure-control-lab.md#kata-102-the-charge-survived-the-response-did-not) |
| 103 | [keep the cohort when the worker disappears](exposure-control-lab.md#kata-103-keep-the-cohort-when-the-worker-disappears) |
| 104 | [do not lose the request when completion is missing](exposure-control-lab.md#kata-104-do-not-lose-the-request-when-completion-is-missing) |
| 105 | [the controller committed, but its acknowledgement was lost](exposure-control-lab.md#kata-105-the-controller-committed-but-its-acknowledgement-was-lost) |

### Frontier risk and containment

| Kata | Exercise |
| --- | --- |
| 13 | [write a bounded safety case](frontier-risk-decisions.md#kata-13-write-a-bounded-safety-case) |
| 14 | [detection is not containment](frontier-risk-decisions.md#kata-14-detection-is-not-containment) |
| 15 | [autonomy must be useful at the required reliability](frontier-risk-decisions.md#kata-15-autonomy-must-be-useful-at-the-required-reliability) |
| 54 | [cancellation was acknowledged, but the worker wrote](frontier-risk-decisions.md#kata-54-cancellation-was-acknowledged-but-the-worker-wrote) |
| 55 | [a working stop can still harm the service](frontier-risk-decisions.md#kata-55-a-working-stop-can-still-harm-the-service) |
| 98 | [identical component scores, one hundred times the failures](frontier-risk-decisions.md#kata-98-identical-component-scores-one-hundred-times-the-failures) |

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

**Evidence limits:** this is deterministic re-grading of retained mock-world executions, not agent re-execution or production attestation. Without `--verify-source`, the CLI uses the installed grader without enforcing its revision, and population validation covers case/customer/slice membership rather than full source-file and case-input verification. [Katas 34–35](#kata-34-the-version-label-did-not-change) add the optional stricter checks; they still do not download or attest an implementation. No semantic stage is selected in this CLI example, so receipts are null here; [Katas 08–10](semantic-grading-lab.md) exercise the connected optional stage. A party able to rewrite all evidence and trusted references can fabricate a self-consistent packet; external provenance and storage controls remain necessary.

## Kata 32: reproduce yesterday without approving today

**Know first:** historical reproduction and current eligibility answer different questions. Revoking a grader's calibration does not erase a historical judgment. It changes whether that calibration can support a new decision.

**Situation:** a retained packet has four paired trial executions for one synthetic case: two repetitions in each arm. An evaluator-owned fixture judge supplied context-bound receipts. At the recorded time the test registry allowed its synthetic calibration. Later, the registry revokes that calibration hash.

**Predict:** should the historical grades still reproduce? Should the current-calibration assessment pass? Should either result authorize application deployment?

```bash
uv run python -m unittest tests.test_replay_authority -v
```

**Task:** keep the original packet unchanged. Supply its independently retained digest, the historical calibration trust set, a current registry snapshot and an explicit timezone-aware assessment time. Produce a separate assessment containing the packet digest, registry digest, historical-trust digest, diagnostic mode, assessment time and result counts. Never obtain the trusted anchor or registry from the packet being checked.

??? success "Solution and reasoning"
    `assess_replay` in `cx_eval_lab/replay_authority.py` first compares the full packet with the operator-supplied anchor, then calls historical replay with the separately supplied historical trust set. A malformed or non-reproducible packet raises an error. Only after reproduction does it consult the current registry for each retained semantic receipt.

    Revocation or missing registration yields `qualification_missing_or_revoked`; expiry yields `qualification_not_current`. The returned assessment says `calibration_status="not_current"` while still recording four reproduced trials. Tests compare the original packet before and after to verify that the assessment did not rewrite it.

    A current registry entry must match the retained qualification audit, evaluator and criterion. It must cover the case's dataset, policy and joint slice scope and satisfy its registered calibration bounds. The registry owns those checks; a receipt cannot qualify itself by naming a digest.

    Synthetic qualification is rejected by default. The test explicitly uses `allow_synthetic=True` to exercise a diagnostic path. This setting is retained as `synthetic_diagnostic`, and `deployment_authorized` remains false. The fixture's claimed calibration counts are test inputs, not independent human-review evidence.

**Extend:** repeat the assessment at the exact expiry time; it must no longer be current. Change a packet field while leaving the external anchor unchanged; the assessment must reject it even if its internal hashes have been recomputed. Explain why taking a new digest from the altered packet defeats that protection.

**Interview answer to know:** “I preserve the original evidence and historical grade, then issue a separate time- and registry-bound assessment. A revocation changes current eligibility, not history. A digest only anchors evidence if its trusted copy is independently controlled.”

## Kata 33: a current evaluator can grade a failed trial

**Situation:** the registry entry is current, but a receipt has the wrong context hash. The historical grader correctly marked the customer message unqualified and the trial failed. The resulting packet is retained as a failure, not fraudulently presented as a pass.

**Predict:** can historical replay succeed? Can calibration remain current? Which fields prevent a consumer from mistaking these results for successful evaluation?

```bash
uv run python -m unittest \
  tests.test_replay_authority.ReplayAuthorityTests.test_current_calibration_does_not_hide_invalid_receipts_or_failed_grades -v
```

??? success "Solution and reasoning"
    All four failed grades reproduce: replay success means agreement with recorded grades, not that the grades were passing. The test returns `calibration_status="current"`, `failed_trials=4`, and `unqualified_message_trials=4`. Its synthetic diagnostic permission is explicit, and deployment remains unauthorized.

    Calibration eligibility describes the scoring instrument. Receipt validity describes whether a particular judgment is bound to its evidence. The trial verdict describes the system behavior under the grader. Keep all three separate. A valid judge verdict of `fail` is also a failed trial, but is not an invalid receipt or proof that the judge's calibration has expired.

    If a packet has no semantic receipts, the assessment reports `calibration_status="not_applicable"`, not `"current"`. Read this as “no retained semantic receipts were checked,” not “no semantic evaluation was needed.” Historical unqualified-message counts remain visible.

**Evidence boundary for both katas:** these are executed local tests using mock agents and synthetic judge responses. The new Python API does not authenticate reviewers, fetch an authoritative registry, enforce the installed grader's source revision, create a new-grader reassessment, or connect to a deployment controller. The existing `replay` CLI still performs historical replay only. The current assessment is a separate operator-invoked API; retain the registry snapshot and historical trust set alongside its digests to reproduce it later.

## Kata 34: the version label did not change

**Situation:** a packet names evaluator `refund-evaluators-v1`. A developer changes the grader source but leaves that label unchanged. Another run hashes the changed source while continuing to claim the original commit. A third checkout uses Git replacement refs to substitute a different source tree under the original commit label.

**Predict:** which problem would a version-string comparison catch? Which requires comparing local bytes with the original committed tree?

```bash
uv run python -m unittest tests.test_source_provenance tests.test_source_replay_cli -v
```

**Task:** refuse all three source mismatches. Require a complete inventory rather than checking only `evaluators.py`; retain the registered dataset, policy and dependency declaration hashes. Test missing and extra Python files, unknown input mappings and symlinked paths. Preserve normal historical replay as a distinct, weaker operation.

??? success "Solution and reasoning"
    `verify_sources` compares the independently supplied full revision with both manifest and checkout HEAD, then checks the exact source inventory and each file's raw digest. It also reads the committed objects with Git replacement handling disabled. A friendly evaluator label is one required identity, not sufficient evidence of implementation identity.

    The tests first generate a manifest from correct files. A changed file fails the manifest-byte comparison. A freshly captured dirty-file hash still fails the committed-byte comparison. An untracked Python file fails inventory equality even if a new manifest includes it. The replacement-ref regression creates two commits in a disposable fixture repository; the original revision cannot borrow the second commit's content.

    The fresh-process CLI test copies the local program into a temporary repository, commits it, generates a paired packet and runs source-checked replay. It then changes the grader file and confirms rejection. No live model is used. See the [retained 20-trial example](evidence-spine.md#source-checked-replay-labels-files-and-actual-case-inputs) for the exact source identity and observed output.

**Interview answer criteria:** distinguish version label, source digest, committed revision, installed environment and execution attestation. Explain why hashing only the grader entrypoint misses imported code, and why even the complete registered local source inventory does not authenticate a past model call.

## Kata 35: the IDs match but the case changed

**Situation:** two artifacts have identical case ID, customer ID and slice labels. One says the order is eligible for 4,000 cents; the other changes eligibility or amount. The manifest still names the original dataset file.

**Predict:** can an IDs-only population hash detect the change? Does verifying the dataset file's own hash prove that the retained case came from that file?

```bash
uv run python -m unittest tests.test_source_replay_cli.SourceCaseBindingTests -v
```

??? success "Solution and reasoning"
    Neither check alone binds the retained case to the file. Load canonical cases from the operator-supplied, hash-verified dataset. Compare every retained case's complete representation and original agent input against the corresponding canonical case; require complete membership. Existing replay then verifies every registered repetition and both arms, rather than allowing a case to appear once and disappear elsewhere.

    The regression tests alter eligibility, amount and customer utterance, omit a complete case, and change the release-policy version. The input-binding check rejects each inconsistency. Do not “repair” the archive by replacing its case with today's dataset row. Preserve it as inconsistent evidence and create a separately identified corrected run or reassessment.

**Extend:** explain why matching all inputs still does not establish that tool events really occurred. Name an independent source of final-state evidence and who controls its write access. Then explain why a matching policy file does not establish that the archived outer release decision was computed correctly.

**Evidence limit:** these two katas exercise local verification logic under a controlled checkout, not model quality, current calibration, dependency installation or production authority. The code preserves earlier content and replay workflows; strict verification is opt-in and intentionally rejects older packets that lack the required source evidence.

## Further practice

[Katas 78–80](long-report-study.md) use full original/repaired memos and a frozen source corpus to expose selective extraction, compound-claim failures and unsupported synthesis. The controls parse registered finding paragraphs; their results do not qualify arbitrary prose extraction or a real research agent.

[Katas 76–77](rag-research-evals.md#executed-report-and-citation-workshop) inspect a complete compact report and frozen corpus, separate citation resolution from entailment and current support, and preserve old/new grades after a dated answer-key correction. Semantic annotations are authored; extraction and synthesis validity on long professional reports remain separate work.

[Katas 74–75](llm-as-a-judge.md#executed-judge-sensitivity-workshop) execute matched order, length and rubric-wording controls, normalize A/B slots to stable answers, and show how duplicated judge errors survive majority voting. The retained local calls teach diagnostics, not measured bias rates of real LLM judges.

[Katas 72–73](human-evaluation.md#executed-annotation-analysis-preserve-the-disagreement) compute agreement from the existing synthetic annotation table, retain unknown/missing denominators and undefined bootstrap outcomes, and expose a false model advantage caused by reviewer assignment. Worked solutions separate reliability from correctness and actual human qualification.

[Katas 70–71](dataset-design.md#executed-sampling-study-the-same-system-different-apparent-failure-rates) derive inclusion probabilities and population estimates from a risk-enriched sample, then use exact finite-population uncertainty to distinguish a favorable point estimate from numerical clearance. Missing labels and unsupported strata cannot silently become passes.

[Katas 68–69](rag-research-evals.md#executed-study-retrieved-evidence-that-never-reaches-the-agent) trace multi-passage evidence from lexical retrieval through byte-bounded packing and mock action. Diagnose duplicate coverage, stale sources and recency-driven eviction, then separate an evidence repair from a downstream decision repair.

[Katas 66–67](dataset-design.md#mixed-trace-workshop-observations-before-causes) use eight mixed traces to distinguish observable defects, untested cause hypotheses, clean controls and unresolved work. Count overlapping categories without inventing independent incidents, then choose a repair and a discriminating check before publishing regressions.

[Katas 64–65](order-resolution-study.md#native-paired-diagnostics-separate-the-action-from-the-explanation) derive native structural and joint changes from retained multi-order executions. Distinguish a qualified semantic failure from abstention, locate clarification and ordering failures, and reject retrospective promotion of exploratory feature slices to required gates.

[Katas 83–84](telemetry-delivery-study.md) use real loopback OTLP/HTTP delivery to distinguish application outcomes from observed trace coverage. Reconcile a successful flush with lost spans, deduplicate acknowledgment retries, reject inconsistent joins and preserve feedback awaiting a missing trace. In-memory acceptance and authored ratings are not durable production evidence.

[Kata 82](semantic-grading-lab.md#kata-82-a-failed-check-must-reach-the-decision) follows failed template prerequisites through message qualification, report counters and the hard gate. Tests distinguish missing support from proven falsity, reject unreviewed template rules and prevent a passing semantic receipt from bypassing a recognized template's deterministic boundary.

[Kata 81](benchmark-reproducibility.md#kata-81-equal-accuracy-different-evidence) computes equal headline accuracy with different per-item failures, joins reordered records by registered identity, rejects missing and duplicate items, and locates the first observable divergence. Its inputs are invented; it is not a completed cross-framework model experiment.

[Katas 62–63](metrics.md#executed-paired-slice-comparison) reconstruct fixed and regressed pairs from full legacy executions, compare trial and customer weighting, and hold missing or unqualified required-slice evidence. The retained study improves overall while regressing its required slice; its teaching intervals do not authorize release.

[Katas 60–61](dataset-design.md#from-incident-evidence-to-a-versioned-regression) turn incident evidence into a reviewed regression: preserve the causal failure during minimization, bind review to exact content and policy, check known protected-set overlaps, and publish a new version without erasing the parent. The lessons distinguish synthetic workflow controls from actual human adjudication or automatic de-identification.

[Katas 58–59](cx-evidence-walkthrough.md) follow one complete local CX evidence path. Join an ambiguous refund's paired row to its full execution, inspect clarification and all order ledgers, and distinguish a passing grade from qualified population evidence and current deployment authority.

[Katas 56–57](cross-run-isolation-study.md) test forbidden private-cache reuse across runs while preserving same-run cache hits and shared read-only policy access. The lessons distinguish worker lifetime from resource isolation, trusted run context from query text, and application-level checks from hostile-code containment.

[Katas 54–55](frontier-risk-decisions.md#kata-54-cancellation-was-acknowledged-but-the-worker-wrote) distinguish coordinator cancellation from write-authority revocation, early intervention from late detection, and correctly enforced false stops from useful service. The worked reasoning keeps enforcement tests separate from detector calibration and explains why benign positive controls are essential.

[Katas 51–53](knowledge-action-study.md) compare lexical retrieval, oracle documents and full context, then hold evidence fixed while changing the downstream action control. Worked solutions distinguish corpus coverage from supplied evidence, backend enforcement from agent success, and constructed-case differences from production estimates.

[Katas 49–50](evidence-spine.md#kata-49-matching-a-hash-is-not-validating-an-input) distinguish file-byte identity from canonical-value identity, reject coherently hashed invalid inputs, and recompute a current release decision from committed source, historical replay, current calibration and campaign evidence. Seven retained controls preserve old grades while restricting new decisions; mocked model responses and synthetic qualification do not authorize deployment.

[Katas 28–31](sequential-decisions-lab.md) compute repeated-look false promotion, derive sequential likelihood evidence, break label and independence assumptions, and budget across release campaigns. Exact synthetic path enumeration supports the worked results, not general deployment qualification.

[Katas 24–27](exposure-control-lab.md) execute shadow/canary/expansion/restriction/rollback routing, preserve pending cohorts, expire stale routing and separate rollback from containment. The retained 280-request study is simulation-only.

[Katas 21–23](order-resolution-study.md) execute real competing-order refunds, reject clarification after action and preserve rejected attempts. Their 16-trial study uses deterministic agents and scripted customers, not live-model qualification.

[Katas 43–44](order-resolution-study.md#kata-43-a-summary-is-not-enough-to-reconstruct-a-decision) extend that study into native paired artifacts and mock-tool replay. Two retained comparisons demonstrate why right-order endpoints, structural contract passes, qualified messages and release authority differ. They include full-case/schedule mutation exercises and measurement-source checks; the 8/8 structural control still produces a release block.

[Katas 45–46](order-resolution-study.md#kata-45-four-correct-labels-do-not-qualify-a-judge) add native multi-order semantic receipts, row-derived synthetic calibration and joint structural/semantic controls. Calculate why zero errors in two examples is weak evidence, distinguish qualified failure from abstention and missing qualification, and revoke a calibration without erasing historical grades. The literal judge, synthetic reviewers and overlapping scenarios demonstrate integration—not semantic validity or deployment permission.

[Katas 47–48](semantic-grading-lab.md#kata-47-a-new-evidence-domain-needs-a-new-qualification-scope) connect that native criterion to the installed provider SDK and budgeted campaign path with in-memory HTTP. Four retained controls distinguish accounting clear/hold/block from application release, reproduce throttling and reservation overruns, and keep missing usage visible. All labels, usage and prices are synthetic; no network or paid calls are made.

[Katas 18–20](semantic-grading-lab.md#kata-18-reconstruct-calibration-from-the-labels) reconstruct calibration counts from retained rows, preserve adjudication, reject declared split leakage and connect incident learning to independent requalification. The executed four-row example is synthetic and remains unqualified.

[Katas 16–17](ci-gate-lab.md) exercise expected rejection in CI and the distinction between software conformance, candidate qualification, and application deployment. The command is verified locally; cloud execution and canary control remain separate milestones.

[Katas 13–15](frontier-risk-decisions.md) now cover a bounded safety case, detection versus containment, and reliability-adjusted autonomy. They are worked reasoning and calculation exercises, not executed frontier-risk experiments.

[Katas 11–12](process-recovery-study.md) now exercise actual process interruption, durable-effect reconciliation, changed idempotency arguments, and approval revocation. Their payment service is a local mock; no real money or live agent is involved.

[Katas 08–10](semantic-grading-lab.md) now exercise calibration bounds, scoped qualification, negative versus unknown judgments, and retained judge evidence. Their judge is a synthetic control double; live semantic accuracy remains unmeasured.

[Katas 36–37](semantic-grading-lab.md#kata-36-a-passing-json-verdict-is-not-a-usable-judgment) exercise the optional provider adapter through fake envelopes, the installed SDK's in-memory HTTP transport, and paired-run replay. They distinguish refusal/incomplete responses from negative judgments, reproduce endpoint drift and malformed metering, and calculate known versus unknown evaluation cost. These are offline software tests, not a live judge qualification study.

[Katas 38–40](eval-operations-integrity.md#kata-38-is-an-unknown-bill-free-budget) execute durable judge-budget admission, crash/reopen and concurrent-worker tests, and an inspectable four-trial campaign. Solutions separate known costs from held reservations, prevent duplicate judge dispatch, and show why budget-dependent missing judgments cannot support an agent-quality claim.

[Katas 41–42](evidence-spine.md#kata-41-matching-hashes-wrong-evidence) join campaign snapshots to execution requests, qualification, verdicts and costs, then compose the campaign assessment with the existing release receipt. Retained controls demonstrate clear-plus-inconclusive hold, unknown-cost hold versus candidate failed-check block, overrun blocking and changed-snapshot rejection. They remain synthetic lab evidence, not deployment authority.

[Katas 05–07](statistical-method-study.md) now cover statistical false promotion, unequal-cluster estimands, and biased judge labels, with executed enumeration results and worked solutions.

The [delivery map](primer-delivery-map.md) tracks the complete book and interview-preparation objective. Upcoming katas deepen dataset improvement, human annotation, empirical judge calibration, general clustered/sequential inference, retrieval, process recovery, CI/CD, canary exposure, and frontier-risk decisions. Those further exercises remain pending until their runnable checks and worked solutions exist.
