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
