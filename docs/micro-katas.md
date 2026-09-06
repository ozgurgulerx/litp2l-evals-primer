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

[Katas 28–31](sequential-decisions-lab.md) compute repeated-look false promotion, derive sequential likelihood evidence, break label and independence assumptions, and budget across release campaigns. Exact synthetic path enumeration supports the worked results, not general deployment qualification.

[Katas 24–27](exposure-control-lab.md) execute shadow/canary/expansion/restriction/rollback routing, preserve pending cohorts, expire stale routing and separate rollback from containment. The retained 280-request study is simulation-only.

[Katas 21–23](order-resolution-study.md) execute real competing-order refunds, reject clarification after action and preserve rejected attempts. Their 16-trial study uses deterministic agents and scripted customers, not live-model qualification.

[Katas 18–20](semantic-grading-lab.md#kata-18-reconstruct-calibration-from-the-labels) reconstruct calibration counts from retained rows, preserve adjudication, reject declared split leakage and connect incident learning to independent requalification. The executed four-row example is synthetic and remains unqualified.

[Katas 16–17](ci-gate-lab.md) exercise expected rejection in CI and the distinction between software conformance, candidate qualification, and application deployment. The command is verified locally; cloud execution and canary control remain separate milestones.

[Katas 13–15](frontier-risk-decisions.md) now cover a bounded safety case, detection versus containment, and reliability-adjusted autonomy. They are worked reasoning and calculation exercises, not executed frontier-risk experiments.

[Katas 11–12](process-recovery-study.md) now exercise actual process interruption, durable-effect reconciliation, changed idempotency arguments, and approval revocation. Their payment service is a local mock; no real money or live agent is involved.

[Katas 08–10](semantic-grading-lab.md) now exercise calibration bounds, scoped qualification, negative versus unknown judgments, and retained judge evidence. Their judge is a synthetic control double; live semantic accuracy remains unmeasured.

[Katas 36–37](semantic-grading-lab.md#kata-36-a-passing-json-verdict-is-not-a-usable-judgment) exercise the optional provider adapter through fake envelopes, the installed SDK's in-memory HTTP transport, and paired-run replay. They distinguish refusal/incomplete responses from negative judgments, reproduce endpoint drift and malformed metering, and calculate known versus unknown evaluation cost. These are offline software tests, not a live judge qualification study.

[Katas 05–07](statistical-method-study.md) now cover statistical false promotion, unequal-cluster estimands, and biased judge labels, with executed enumeration results and worked solutions.

The [delivery map](primer-delivery-map.md) tracks the complete book and interview-preparation objective. Upcoming katas deepen dataset improvement, human annotation, empirical judge calibration, general clustered/sequential inference, retrieval, process recovery, CI/CD, canary exposure, and frontier-risk decisions. Those further exercises remain pending until their runnable checks and worked solutions exist.
