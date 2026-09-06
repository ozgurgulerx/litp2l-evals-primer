# Dataset Design

The evaluation set is a model of the world you care about. Its omissions become blind spots.

!!! important "This chapter owns acceptance evidence"
    **Sealed acceptance** sets and **Label access** control live here. The frozen calibration set that validates an LLM judge lives in chapter 5. The split is deliberate: acceptance data tests the system; calibration data tests the measuring instrument.

## Build in layers

1. **Core cases** represent the common, intended path.
2. **Boundary cases** probe ambiguity, long context, and unusual inputs.
3. **Adversarial cases** target known failure mechanisms.
4. **Regression cases** preserve failures discovered in development or production.

## Give every case a reason to exist

Record provenance, scenario, expected behavior, risk level, and the rubric version. A case without provenance or intent is hard to maintain and harder to trust.

```yaml
id: example-001
scenario: Describe the user and situation
input: Add the exact system input
expected_behavior:
  - State an observable requirement
risk: medium
source: synthetic
rubric_version: v1
```

## Treat the golden set as an executable specification

Expected evidence should describe observable facts, permitted trajectories, and required outcomes—not one brittle reference sentence. Version cases and graders together so the suite can be executed by the same runner against a baseline and a candidate.

## Access-oriented stores and overlays

One monolithic golden set creates conflicting incentives. This abbreviated view focuses on access separation before the complete seven-role taxonomy below.

| Store or overlay | Who may see labels? | Job |
| --- | --- | --- |
| Optimisation | Builders | Improve prompts, retrieval, tools, and orchestration |
| Regression | Builders | Prevent understood failures from recurring |
| Frozen calibration | Judge owners and adjudicators | Validate the grader; covered in chapter 5 |
| Sealed acceptance | Independent release owner | Test generalisation beyond material used to build the candidate |
| Production shadow | Restricted or delayed | Represent the current live distribution |
| Safety overlay | Restricted by risk | Apply stricter access and non-compensable authority to safety cases in any appropriate role |

This is not a second role list. **Safety is an overlay**; capability and adversarial roles appear in the canonical seven below.

## Enforce label access

The team tuning the system must not hold the labels that accept its release. Builders may inspect optimisation and known-regression labels; sealed acceptance labels remain with an independent release owner. Record access, exports, and dataset joins as part of the evaluation architecture.

## Stay fresh without leaking labels

Use three coordinated stores: a stable core for longitudinal comparison, a rotating temporal holdout for freshness, and an independently held sealed acceptance slice for release. Promote confirmed production failures into regression protection only after they are understood; never silently change the set behind a trend line.

Once a case or label enters a prompt, fine-tuning set, or optimisation loop, it no longer measures generalisation. Retire contaminated or saturated cases, preserve their history, and treat unexplained score jumps as an investigation trigger.

## Canonical seven dataset roles

The runnable system uses seven roles. **Safety is an overlay**, not a contradictory eighth role: a safety case can be adversarial, regression, sealed acceptance, or production shadow, with stricter access and release authority.

| Role | Main question | Mutation policy | Typical visibility |
| --- | --- | --- | --- |
| Capability | Can the system show the behavior at all? | Changes during exploration | Builders |
| Optimisation | Which candidate change improves the target behavior? | Actively used during development | Builders |
| Regression | Does a repaired failure stay repaired? | Add through reviewed promotion | Builders and CI |
| Adversarial | Does behavior hold under a named attack or stressor? | Grows with threat discovery | Risk-controlled |
| Judge calibration | Does a grader agree with independently reviewed labels? | Frozen for one grader version | Judge owners/adjudicators |
| Sealed acceptance | Does the complete system generalize beyond development material? | Independently maintained | Release owner |
| Production shadow | What is happening on the current traffic distribution? | Time-windowed and reviewed | Restricted operations/review |

Do not duplicate the same case into every role without recording lineage. If a production-shadow failure becomes a regression case, create a promotion receipt linking the source observation to a de-identified, minimized test case.

## Design the sampling frame

A dataset is a sample from a population. Write the intended population before collecting cases:

```yaml
population:
  product: cx-support-agent
  workflows: [refund, status, cancellation, escalation]
  languages: [en, tr]
  channels: [chat]
  risk_window: current-policy-v3
  traffic_window: 2026-08-01/2026-08-31
  excluded:
    - voice-only interactions
    - orders governed by legacy-policy-v1
```

Without this, “90% success” has no defined target.

### Combine sampling strategies

| Sample | Purpose | Reporting rule |
| --- | --- | --- |
| Representative random | Estimate dominant traffic | Preserve production weights |
| Stratified | Compare languages, workflows, or segments | Report stratum support and weighted aggregate separately |
| Risk-enriched | Exercise rare severe outcomes | Never call its raw rate production prevalence |
| Boundary | Probe decision thresholds | Report by boundary, not as ordinary traffic |
| Temporal | Detect current drift | Record window and freshness |
| Disagreement | Improve rubrics and graders | Do not use alone for system quality estimates |

An evaluation suite can contain all six, but each result must state which population it estimates.

## Specify every case as an evidence contract

Extend the minimal YAML with environment, trajectories, evidence, and lifecycle metadata:

```yaml
case_id: refund-timeout-tr-001
dataset_role: regression
dataset_version: refund-regression-v1.1
provenance:
  kind: deidentified_synthetic_reproduction
  source_incident: incident-sim-014
  reason: duplicate refund after ambiguous timeout
scenario:
  language: tr
  workflow: refund
  risk: critical
  initial_state:
    eligible: true
    amount_cents: 4200
    refund_transactions: 0
  fault: timeout_after_commit
expected_evidence:
  required_before_write: [verify_identity, consult_refund_policy]
  required_after_ambiguous_write: [inspect_order_status]
  prohibited: [second_refund_transaction]
  final_state:
    refund_transaction_count: 1
review:
  status: approved
  policy_version: refund-policy-v3
  reviewer_pool: cx-policy-v1
  reviewed_at: 2026-09-06
lifecycle:
  supersedes: null
  expires_when: refund-policy-v3-retired
```

Expected evidence is broader than one reference response. It permits legitimate language variation while preserving state and policy invariants.

## Start with error analysis

For open-ended behavior, collect traces and classify failures before creating dozens of generic graders. A practical loop is:

1. Sample outputs and traces.
2. Inspect them without looking only at aggregate scores.
3. Cluster mutually actionable failure modes.
4. Estimate frequency and severity separately.
5. Write observable criteria for the important clusters.
6. Create the smallest cases that reproduce them.
7. Validate that a known-bad candidate fails and a reference candidate passes.

Good failure categories point to different repairs. “Hallucination” is often too broad; `retrieval_miss`, `stale_policy_selected`, `ignored_evidence`, and `false_success_claim` are more actionable.

## Use synthetic data deliberately

Synthetic generation is useful for coverage, not automatic truth. Use it to create:

- controlled combinations of workflow, language, persona, risk, and fault;
- paraphrases and boundary variations;
- attacks tied to a threat model;
- rare failures unsafe or expensive to collect;
- deterministic fixtures with known state.

Require a generation manifest:

```json
{
  "generator": "scenario-template-v2",
  "seed": 817,
  "policy_version": "refund-policy-v3",
  "requested_slices": ["language:tr", "fault:timeout-after-commit"],
  "review_required": true,
  "generated_case_ids": ["refund-timeout-tr-001"]
}
```

Review synthetic cases for impossibility, duplicated semantics, label leakage, unrealistic wording, and unintended answer changes. Store the realized case, not only the generation prompt.

## Improve datasets through a controlled lifecycle

```text
observe
→ cluster
→ prioritize
→ reproduce
→ minimize and de-identify
→ adjudicate expected behavior
→ choose dataset role
→ deduplicate and check contamination
→ version and diff
→ replay baseline and candidate
→ monitor continued utility
```

### Observe and cluster

Combine production samples, canary traces, support escalations, simulator failures, adversarial results, and evaluator disagreements. Cluster by causal mechanism, not only surface wording.

### Prioritize

Use severity, frequency, recency, strategic value, slice coverage, reversibility, and detectability. Rare irreversible financial or privacy failures may outrank common tone issues.

### Reproduce and minimize

Reduce a long incident to the smallest scenario that retains the causal mechanism. Preserve required preconditions and remove identifying details. A minimized case is easier to understand and less likely to capture irrelevant production noise.

### Adjudicate

Policy and domain owners determine expected behavior. If the correct behavior is genuinely ambiguous, update the product contract or preserve multiple acceptable outcomes. Do not force a label just to make automation convenient.

### Assign a role

A discovered failure usually enters regression after repair. A newly hypothesized attack may enter adversarial. A current-traffic sample can remain production shadow. A case used to tune the candidate must not quietly remain sealed acceptance.

### Version and diff

Publish additions, removals, label changes, slice changes, and reasons. Historical trend lines must retain the dataset version used at the time.

```yaml
release: refund-regression-v1.1
base: refund-regression-v1.0
changes:
  added:
    - case_id: refund-timeout-tr-001
      reason: protect fixed duplicate-refund incident
  relabeled: []
  superseded: []
reviewers: [policy-owner, evaluation-owner]
```

## Dataset health

Growth is not quality. Track a portfolio of health signals:

| Signal | Question | Bad interpretation to avoid |
| --- | --- | --- |
| Behavior coverage | Which product promises and failure modes have cases? | “More rows means more coverage” |
| Slice coverage | Which workflows, languages, risks, and intersections have support? | Treating one case as a stable rate |
| Redundancy | How many cases protect the same mechanism? | Removing all near-neighbors as duplicates |
| Label disagreement | Where is expected behavior unclear? | Calling all disagreement reviewer error |
| Freshness | Does the suite reflect current policy and traffic? | Replacing the stable core every week |
| Contamination | Which labels or cases entered optimization? | Assuming public data remains sealed |
| Grader sensitivity | Do known-bad systems fail for the intended reason? | Trusting a suite that every mutant passes |
| Predictive validity | Do offline results forecast canary/live behavior? | Treating offline accuracy as self-validating |
| Incident protection | What share of reviewed serious failures became a case, grader repair, or documented limitation? | Rewarding indiscriminate case growth |
| Maintenance debt | Which cases are stale, flaky, ownerless, or unexplained? | Silently deleting them |

### A coverage ledger

```yaml
behavior: safe_timeout_recovery
owner: payments-platform
surfaces: [outcome, policy, tool_trajectory]
cases:
  core: 1
  boundary: 2
  regression: 1
  adversarial: 0
slices:
  en: 3
  tr: 1
known_gap: no multi-turn customer retry case
next_review: 2026-10-01
```

The ledger admits gaps. “100% edge-case coverage” is not a credible state.

## Control duplication without erasing boundaries

Use exact hashes, normalized text, embedding similarity, metadata, and human review. Two messages can be textual duplicates but belong to different policies or world states; two differently worded cases can test the same mechanism.

Keep cases when they add one of:

- a new decision boundary;
- a protected population;
- a distinct failure mechanism;
- temporal or policy coverage;
- stochastic reliability evidence;
- a simpler reproduction of a serious incident.

## Detect contamination and leakage

Track whether inputs, labels, references, or grader rationales were exposed through prompts, fine-tuning, retrieval, debugging, or optimization. Use:

- access-controlled sealed labels;
- immutable export logs;
- joins between training and evaluation inventories;
- exact and semantic overlap scans;
- canary phrases where appropriate;
- time-based and private acceptance sets;
- suspicious-score-change review.

If a case enters optimization, reclassify it. Its history remains useful, but it no longer demonstrates unseen generalization.

## Retire and supersede transparently

Retire a case when its policy is obsolete, scenario impossible, label invalid, or value fully duplicated. Record the reason and keep the historical version. Supersede rather than edit in place when the meaning changes.

Never delete a difficult case merely because it blocks a desired release.

## Worked example: incident to regression

Synthetic incident:

> A Turkish customer asks for a partial refund. The payment service commits the refund but times out. The agent retries, creating a duplicate transaction.

The review produces:

| Stage | Output |
| --- | --- |
| Classification | `workflow:refund`, `language:tr`, `fault:timeout-after-commit`, `severity:critical` |
| First causal failure | Agent did not inspect authoritative state after ambiguity |
| Minimal fixture | One eligible order, one ambiguous committed write, deterministic ledger |
| Expected relation | First write-related action after timeout is inspection, not retry |
| Outcome invariant | Exactly one transaction |
| Dataset role | Regression after the repair; adversarial variant for injected retry instruction |
| Release effect | Hard block on duplicate transaction |

One incident creates several linked protections instead of one brittle transcript: environment fault, trajectory rule, final-state invariant, Turkish explanation case, and a dataset release receipt.

## From incident evidence to a versioned regression

A failure is an observation. A regression case is a reviewed specification of what must not recur. Copying the failed conversation into a test file skips the important decisions: whether the incident is reproducible, what behavior was actually wrong, which preconditions matter, whether the data is safe to retain, and where the case may be used.

The local exercise below makes those decisions explicit. It uses synthetic refund data and a controlled failure agent; it does not ingest customer logs or establish that a real reviewer approved the labels. The earlier partial-refund story remains a design illustration. The executable control uses the existing lab's refund contract, whose scope must not be silently expanded to partial refunds.

From the repository root:

```bash
uv run python -m unittest tests.test_incident_regression tests.test_incident_artifact -v
uv run python -m cx_eval_lab.incident_regression \
  --output /tmp/primer-incident-regression-my-first-run.json
```

Use a fresh output filename; the CLI refuses to overwrite evidence. The registered transformation removes synthetic greeting padding and distractor order IDs from this constructed case. It is not a general-purpose minimizer or privacy scrubber. The failure control uses the lab's deliberately faulty duplicate-effect tool mode; observing its duplicate does not demonstrate that the protected production tool facade permits the same action.

### Observed promotion and rejection controls

The [retained study packet](assets/incident-regression-v1.json) starts with an executed synthetic incident: the refund commits, the response times out, and the blind-retry mutant creates a second transaction. The new `regression-v1` release contains one minimized case linked to the unchanged empty `regression-v0` parent. Its diff changes the case ID, dataset version, greeting padding and distractor IDs; the timeout precondition remains.

| Check | Observed result | What it supports |
| --- | --- | --- |
| Source failure | Two transactions; case fails | The incident contains an executed duplicate-after-timeout failure |
| Released-case reference rerun | One transaction; case passes | The case still permits the registered correct recovery |
| Released-case mutant rerun | Two transactions; fails outcome, duplicate and recovery checks | Minimization and serialization preserve the protected failure |
| Missing or rejected review | Promotion rejected | A failure alone cannot authorize a dataset addition |
| Pending privacy review | Promotion rejected | Behavior approval cannot replace the separate retention decision |
| Stale proposal digest | Promotion rejected | A review does not float across case or target changes |
| Reviewer equals proposer | Promotion rejected | The local distinct-identity constraint is enforced |
| Known sealed lineage or calibration-content overlap | Promotion rejected | Supplied protected-role conflicts cannot be ignored |

The seven negative controls are attempted promotions, not seven independent incidents. `conformance_passed` means these rejections and the reference/mutant contrast reproduced as registered. It does not mean the dataset is representative, human-reviewed, free of all sensitive data or eligible for acceptance testing.

`RegressionRelease.materialize()` reconstructs every retained case for the CX runner under the new release version. Stored parent entries remain unchanged. A separate populated-parent regression test adds a second case, checks preservation of the first entry and rejects re-adding duplicate operational content under a newer version. Parent entry validation recomputes content identity from the parsed case rather than trusting its supplied `content_hash`.

Current protected-inventory checks include the added incident/case **and carried-forward parent entries**. Tests reproduce a previously missed conflict where an old case becomes reserved for sealed acceptance or calibration while the new case is unrelated. The release is now rejected when any available parent group, source-incident digest or recomputed case-content digest conflicts. Original source content that was not retained in a parent entry cannot be inferred from its digest; complete lineage resolution still needs the operator's protected evidence store.

Run this from the repository root to re-execute the deterministic study and compare the complete retained result, rather than accepting its stored pass flags:

```python
import json
from pathlib import Path
from cx_eval_lab.incident_regression import replay_study

report = json.loads(Path("docs/assets/incident-regression-v1.json").read_text())
assert replay_study(report)
assert report["reruns"]["reference"]["final_state"]["refund_transaction_count"] == 1
assert report["reruns"]["mutant"]["final_state"]["refund_transaction_count"] == 2
assert all(control["rejected"] for control in report["controls"].values())
```

This replay is a deterministic re-execution comparison, not an authenticated history of a production incident. The receipt's `proposer_hash` field names the **full proposal digest**, not a hash of the proposer identity. It includes the proposed case, source binding, transformation, policy and target version/role. Keep these meanings explicit when adapting the schema. Reviewer authorization, trusted parent-release retrieval, full lineage inventories and actual privacy assessment remain operator responsibilities beyond this local fixture.

### Kata 60: an approved review of the wrong case

**Know:** review is bound to content and policy, not just a familiar case ID or a person-shaped string.

**Task:** reproduce a timeout-after-commit failure, prepare a minimal regression, and obtain a review of that exact proposal. Then change a causal precondition while leaving the case ID and approval text unchanged. Should the new dataset release accept it?

??? success "Solution: bind review to the case that will actually run"
    No. Bind the decision to the source incident, full proposed case and applicable domain policy. If the proposal changes, the old approval no longer covers it. A timeout flag, expected outcome, amount or permission boundary can change the mechanism even when the request text is unchanged.

    The incident must retain the observed execution. For an ambiguous commit, inspect the first committed effect, the timeout and the next write or state-inspection action. A supplied `failure=true` flag is not the evidence. Run the reference and controlled failure on the proposed case to check that the reproduction still distinguishes the behavior being protected. Then reconstruct the case from the released dataset and rerun: testing only the in-memory proposal would miss a serialization or publication error.

    Keep the source artifact unchanged. A privacy-reviewed minimized reproduction is a new artifact linked to the source; it is not a redacted file that silently replaces the original evidence. The original may need restricted storage and its own retention policy. A public learning repository should contain synthetic reproductions, not customer transcripts.

    Review has several independent questions: Is the expected behavior correct under the policy? Does the minimized case preserve the mechanism? Is the retained data appropriate for the intended audience? Is the reviewer authorized and independent of the proposer? Passing one question cannot substitute for the others. A checked privacy-review field does not prove that automatic anonymization occurred.

    In this local exercise, distinct synthetic reviewer/proposer IDs and content-bound receipts test the workflow. They do not authenticate people, prove expertise or certify de-identification. A production service needs independently controlled identity, reviewer assignments and protected source evidence in addition to these checks.

**Extend:** the policy changes so that escalation becomes mandatory rather than optional. Preserve the historical release and produce a new review/release under the new policy. Compare old and new grades explicitly; do not rewrite yesterday's labels and report the new trend as if the measurement never changed.

**Interview answer:** “I promote a reviewed reproduction, not a transcript. The approval binds the source, proposed case and policy. I preserve lineage, test the causal failure and require new review when the case changes.”

### Kata 61: a new case ID does not make a fresh holdout

**Know:** independence follows origin and exposure, not filenames. Regression usefulness and acceptance independence are different properties.

**Task:** a failure family has already been used to tune the system. Someone paraphrases it, changes its case ID and proposes it for sealed acceptance. Another proposal belongs to a customer/session group already reserved for judge calibration. What should the dataset service check before assigning a role?

??? success "Solution: separate regression protection from independent acceptance"
    Keep known development failures useful as regression cases, with their lineage visible. Do not call their derivatives untouched acceptance data. Compare operator-held lineage and grouping assignments across roles, not only exact prompt hashes or new IDs. A customer/session group reserved for an independent measurement cannot be made independent by renaming its rows.

    A role-conflict check is only as complete as its operator-supplied inventory and lineage/group assignments. It cannot prove the absence of previously unrecorded exposure or discover every semantic paraphrase. In this exercise, known overlaps with sealed-acceptance or judge-calibration groups block automatic regression promotion and require a deliberate split decision. That is a conservative workflow policy, not a universal ban on every form of cross-role reuse. Never clear the conflict by silently deleting the protected inventory entry. A reviewed migration must record how exposure changes what the old set can justify.

    Exact duplicate checks solve a different problem: they prevent identical cases from inflating a version diff and apparent coverage. They do not discover paraphrases, shared causal mechanisms or every hidden relationship. Conversely, identical wording in different policies or world states may be a valuable boundary pair. Record both semantic review and exact identity without conflating them.

    Publish a new regression version linked to its parent, with the added case, source lineage, review binding and explicit diff. Keep the previous release available. Returning new records without modifying parent bytes preserves history in this workflow; it does not make a local writable JSON file tamper-proof. Rerun reference and failure controls on the released cases. A case-count increase is not success if the mutant now passes because the minimized fixture lost its timeout.

**Extend:** an acceptance failure has been disclosed to builders. It may now be valuable regression evidence, but that exposure has changed its acceptance status. Record retirement or reassignment through a reviewed transition, and obtain new independent acceptance evidence. Do not move the same case back into a sealed directory and call it unseen.

**Interview answer:** “A new ID does not reset exposure. I track lineage and grouping, keep regression separate from acceptance, reject known split conflicts, and version changes without erasing the original measurement.”

## Artifact: dataset review report

```json
{
  "dataset": "refund-regression-v1.1",
  "cases": 36,
  "roles": {"regression": 36},
  "slice_support": {"language:en": 27, "language:tr": 9},
  "critical_behaviors": {
    "unauthorized_refund": 6,
    "duplicate_refund": 4,
    "false_success_claim": 5
  },
  "exact_duplicates": 0,
  "semantic_review_queue": 3,
  "labels_disputed": 2,
  "stale_policy_cases": 1,
  "known_gaps": ["multi-turn cancellation after escalation"],
  "decision": "approve after stale case is superseded"
}
```

This is synthetic data. It demonstrates the report contract; it does not claim production coverage.

## Failure modes

| Failure mode | Symptom | Repair |
| --- | --- | --- |
| One monolithic golden set | Tuning and acceptance labels mix | Separate seven roles and visibility |
| Unweighted risk-enriched sample | Failure rate appears catastrophic | Label sampling design and use weights only for target estimates |
| Synthetic data accepted automatically | Impossible cases and leaked labels enter CI | Review realized cases and provenance |
| Case count as quality | Suite grows while behavior coverage stays flat | Maintain coverage ledger and redundancy review |
| Silent relabeling | Trend moves without a system change | Version labels and publish diffs |
| Production trace copied verbatim | Privacy and irrelevant detail leak | Minimize, de-identify, and preserve mechanism |
| Every failure becomes a case | Noise and transient incidents bloat suite | Require adjudication and role decision |
| Stale cases deleted | Historical claims cannot be reproduced | Supersede with retained history |

## Exercise: improve a weak dataset

A team has 500 English happy-path prompts written by one engineer. All labels are visible to prompt authors. The suite has grown for a year, but no case records why it exists. Production now includes Turkish customers and tool-based refunds.

Design the first dataset release that could support a release decision.

??? success "Answer outline"
    Inventory and preserve the 500 cases, then deduplicate and classify them rather than deleting them. Define the current population and product contract. Create separate optimization, regression, adversarial, judge-calibration, sealed-acceptance, and production-shadow stores plus a capability area. Add reviewed Turkish, tool-trajectory, policy-boundary, timeout, and state-outcome cases. Protect sealed labels from builders. Record provenance, reason, expected evidence, policy, risk, slices, owners, and lifecycle. Validate graders with reference and mutant agents. Publish a version diff, coverage ledger, known gaps, and sampling design. Do not infer production quality from the old convenient set.

## Verification checklist

- [ ] The intended population and exclusions are explicit.
- [ ] The seven dataset roles have separate mutation and access policies.
- [ ] Safety and privacy controls apply across roles.
- [ ] Every case has provenance, reason, expected evidence, owner, and lifecycle.
- [ ] Representative, stratified, and risk sampling are reported distinctly.
- [ ] Synthetic cases are reviewed and stored with generation metadata.
- [ ] Failure promotion is de-identified, adjudicated, deduplicated, and versioned.
- [ ] Dataset health includes coverage, disagreement, freshness, contamination, and predictive validity.
- [ ] Changes publish a diff and preserve historical reproducibility.
- [ ] Known gaps remain visible.

## Primary reading

- [OpenAI — Evaluation best practices](https://platform.openai.com/docs/guides/evaluation-best-practices)
- [LangSmith — Evaluation concepts](https://docs.langchain.com/langsmith/evaluation-concepts)
- [OpenAI — Predicting model behavior by simulating deployment](https://openai.com/index/deployment-simulation/)
- [Lessons from the Trenches on Reproducible Evaluation of Language Models](https://arxiv.org/abs/2405.14782)
