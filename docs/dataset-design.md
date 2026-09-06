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

### Executed sampling study: the same system, different apparent failure rates

A risk-enriched sample reports **37.5% failures**. Reweighting those same eight observations to the registered population gives **18.75%**. Neither number alone establishes that the population is below a 35% failure threshold: the design-aware interval is **18.75%–56.25%**.

The [retained sampling study](assets/sampling-study-v1.json) makes that disagreement inspectable. Its finite synthetic population contains 16 requests: twelve routine requests with one failure, and four risk-stratum requests with three failures. The true overall failure rate is `4/16 = 25%`. Outcomes are fixed, correct binary labels in this exercise, not predictions from an LLM judge. “Risk” is a registered stratum, not an instruction to choose individual requests after reading their labels.

Both designs inspect eight requests, selected uniformly **without replacement within each stratum**:

| Design | Routine selected / available | Risk selected / available | Inclusion probabilities: routine / risk | Expected raw failure rate | Expected population-weighted rate |
| --- | --- | --- | --- | --- | --- |
| Proportional stratified | 6/12 | 2/4 | 1/2; 1/2 | 25% | 25% |
| Risk-enriched stratified | 4/12 | 4/4 | 1/3; 1 | 41.67% | 25% |

“Expected” means the average over the complete sampling distribution—not the value every realized sample must return. Proportional stratification is self-weighting here; it is not identical to an unrestricted simple random sample of eight requests. The enriched design performs a census of the risk stratum and samples fewer routine requests. Its larger expected raw rate does not mean the system got worse.

### Kata 70: recover the target population without hiding the risk slice

**Predict:** the worked enriched sample contains four clean routine requests and all four risk requests. Three of its eight observations fail. Which population does the raw rate describe? How much weight should each observation carry?

```bash
uv run python -m cx_eval_lab.sampling_study --output /tmp/sampling-study.json
uv run python -m unittest tests.test_sampling_study -v
```

Choose a new output path for another run. The artifact retains the frame, fixed design, synthetic truth, selected worked-example IDs, observed labels, inclusion probabilities, weights and estimates. The estimator itself receives only frame membership and the selected labels; the separate qualification calculation uses complete synthetic truth to evaluate the method.

Under the registered design, a routine observation has inclusion probability `4/12 = 1/3` and design weight `3`. A risk observation has inclusion probability `4/4 = 1` and weight `1`. The estimated failure total is therefore `0 × 3 + 3 × 1 = 3`; dividing by the **known population size 16**, not the sample size eight, gives `3/16 = 18.75%`.

More generally, for a fixed population of size \(N\), binary failure labels \(y_i\), and positive inclusion probabilities \(\pi_i\), the Horvitz–Thompson population-mean estimator is:

\[
\widehat p_{HT}=\frac{1}{N}\sum_{i\in s}\frac{y_i}{\pi_i}.
\]

For this fixed-quota stratified design it equals \(\sum_h(N_h/N)\bar y_h\). The weights sum to the known population size because each stratum contributes exactly its registered quota. In other designs, dividing by the observed sum of weights is a ratio estimator, not automatically the same estimator. These are **sampling weights**, not subjective severity weights. [Statistics Canada explains design weights as inverse inclusion probabilities](https://www150.statcan.gc.ca/n1/edu/power-pouvoir/ch6/5214809-eng.htm).

??? success "Solution: fix the population estimate, retain the slice finding"
    The raw rate is `3/8 = 37.5%`. It describes the eight selected observations and overweights the risk stratum relative to this population. The weighted estimate is `0.75 × 0/4 + 0.25 × 3/4 = 18.75%`. It is a valid realized estimate under the stated sampling design; it is not the known truth of 25%. Unbiasedness means the estimator averages to the truth across possible samples, not that a particular sample is exact.

    Across the enriched design's possible samples, the expected raw rate is `0.5 × 1/12 + 0.5 × 3/4 = 5/12`, approximately 41.67%. Its expected weighted rate is `0.75 × 1/12 + 0.25 × 3/4 = 1/4`. The design changes the expected mix of observed failures, not the underlying system. The proportional design uses equal inclusion probabilities, so its raw and weighted rates agree for every realized sample.

    Keep the risk-stratum result beside the overall estimate: three of its four requests fail, and this stratum was fully observed. Weighting must not conceal that result or compensate for a separately prohibited action. A 35% overall threshold in this exercise is an arithmetic teaching choice, not a proposed safety tolerance. A hard safety rule can still block even if the overall population estimate is favorable.

    Do not choose the four clean routine requests to obtain a favorable estimate. The worked sample is an explicitly selected illustration from the registered sampling space, not evidence that a random draw happened historically. The distribution analysis includes every possible sample, including those containing the routine failure. In an operational study, retain the randomization procedure and selection event before labels are inspected.

**Interview answer criteria:** name the population and sampling unit; derive inclusion probabilities and both estimates; distinguish design weights from harm severity; explain design-unbiasedness; preserve the high-risk finding and independent release constraints.

### Kata 71: a corrected point estimate still does not justify clearance

**Predict:** should an illustrative `failure_rate ≤ 35%` check clear the worked sample? What changes if one selected label is missing, a stratum has zero inclusion probability, or requests from the same customer are selected together?

The raw point heuristic exceeds 35%; the weighted point heuristic is below it. The uncertainty-aware diagnostic holds because the interval crosses the threshold. A weighted estimate without a design-matched uncertainty calculation cannot settle this disagreement.

```python
import json
from pathlib import Path
from cx_eval_lab.sampling_study import estimate_sample, replay_study

report = replay_study(json.loads(Path("docs/assets/sampling-study-v1.json").read_text()))
inputs = report["inputs"]
worked = report["worked_example"]
result = estimate_sample(
    inputs["frame"], inputs["allocations"]["enriched"], worked["rows"],
    alpha=inputs["alpha"], threshold=inputs["thresholds"][0],
)
assert result == worked["estimate"]
assert result["raw_failure_rate"] == 0.375
assert result["ht_failure_rate"] == 0.1875
assert result["decisions"]["interval"] == "hold"
print(result["interval"], result["decisions"])

# Do not discard an unlabeled selected request and keep the old weights.
incomplete = [{**row, "failure": None} if i == 0 else dict(row)
              for i, row in enumerate(worked["rows"])]
try:
    estimate_sample(inputs["frame"], inputs["allocations"]["enriched"], incomplete)
except ValueError:
    print("Missing label rejected; obtain evidence or register another method.")
else:
    raise AssertionError("Incomplete labels must not establish an estimate")
```

Here the unknown quantity in each stratum is its integer number of failures, \(M_h\). Given \(N_h\), \(n_h\) and \(M_h\), the observed failure count follows a hypergeometric distribution:

\[
P(X_h=x)=\frac{\binom{M_h}{x}\binom{N_h-M_h}{n_h-x}}{\binom{N_h}{n_h}}.
\]

This is sampling without replacement, with a finite-population correction—not repeated independent Bernoulli generation. The [R statistical reference documents this distribution and its support](https://stat.ethz.ch/R-manual/R-devel/library/stats/html/Hypergeometric.html).

The implementation tries every candidate \(M_h=0,\ldots,N_h\). For an overall error budget of 0.05 and two strata, it retains counts for which **both inclusive tails** `P(X ≤ observed)` and `P(X ≥ observed)` exceed `0.05 / (2 × 2) = 0.0125`. It then combines stratum endpoints with population weights. The per-stratum error allocation and union bound give a conservative simultaneous interval; it is not a normal approximation or a generic confidence interval for arbitrary adaptive samples.

??? success "Solution: uncertainty and support are separate from arithmetic"
    With zero failures among four of twelve routine requests, the retained routine failure counts range from zero to six. Observing every risk request pins its failure count to three. Combining endpoints yields `(0 + 3)/16` through `(6 + 3)/16`, or **[18.75%, 56.25%]**. The risk census has no sampling uncertainty for those four fixed labels, but the routine sample still does. No observed routine failures does not imply no routine failures in the frame.

    The point heuristics are deliberately named as illustrative. The interval diagnostic clears a numerical threshold only when its upper bound is at or below it; it exceeds the threshold only when its lower bound is above it; otherwise it holds. Even a numerical clearance does not authorize deployment. This study supplies no live population, authenticated collection, calibrated judge or application safeguards.

    A missing selected label is not a pass. Dropping it changes the effective observation mechanism. The estimator rejects incomplete labels rather than silently retaining the original inclusion probability and shrinking the denominator. If a stratum has zero probability of selection, its population contribution cannot be estimated by this method. If its probability is unknown, do not invent a weight. The implementation also rejects duplicate IDs, foreign frame members, incorrect quotas and probabilities inconsistent with the registered design.

    Requests in a frozen finite frame can have fixed correlated outcomes; the design-based calculation conditions on those outcomes and randomizes selection. But if the actual sampling unit is a customer or session, selecting that unit jointly changes the design. Repeated model runs also add another source of variability. Neither setting is covered by pretending that the same request-level sampling design was used. Define the desired future/customer population separately from this fixed frame.

**Interview answer criteria:** derive why census and partial-sample uncertainty differ; distinguish a point heuristic, interval diagnostic and deployment authority; explain the unknown-probability, missing-label and wrong-sampling-unit failures; state what a finite-frame interval does not cover.

**Inspect the entire sampling distribution:** the proportional design has `choose(12,6) × choose(4,2) = 5,544` possible ID sets; the enriched design has `choose(12,4) × choose(4,4) = 495`. The report groups equally scored samples by stratum failure counts and records their combinatorial multiplicities. Summing a cell's statistic times its probability recovers design expectation, interval coverage and threshold-decision probabilities. These are exact finite sampling-space calculations, not 6,039 new model executions or a Monte Carlo estimate.

Both 35% and 20% thresholds are registered in the study. At 20%, the known 25% population rate is above the limit; inspect how often each point heuristic nevertheless clears and how the interval diagnostic behaves. A false-clear probability and a false-block probability answer different questions. Keep “hold” separate from both. Do not select a threshold after reading results and describe its performance as a preregistered guarantee.

| Design, true failure rate 25%, limit 20% | Raw point false clear | Weighted point false clear | Interval false clear | Interval hold / block |
| --- | --- | --- | --- | --- |
| Proportional | 25% | 25% | 0% | 100% / 0% |
| Risk-enriched | 0% | 66.67% | 0% | 66.67% / 33.33% |

Correcting selection bias does not make a point-threshold rule reliable. Conversely, the enriched raw rule's zero false clears at 20% is not proof of a better estimator: it always blocks in this population, including at the more permissive 35% limit where the true rate is below the threshold. At 35%, both interval diagnostics hold on every possible sample. A method that avoids errors by withholding a conclusion has a different operating cost from one that reliably decides.

For the displayed population, both interval procedures cover the truth on every possible sample. The report also checks **all 65 binary count populations** (`routine failures 0…12 × risk failures 0…4`), not just this convenient example. Minimum overall coverage is `131/132 ≈ 99.24%` for proportional allocation and `98/99 ≈ 98.99%` for enriched allocation—above the nominal 95%, reflecting conservative discrete intervals. Those results apply only to the registered sizes, allocations and confidence level. They are not a 99% claim about future application safety.

The weighted estimator's mean squared error is `0.0078125` under both designs in this example; the enriched raw estimator's is `0.03125` because its sampling-mix bias contributes to error. These errors are in squared proportion units, not percentage points. Thus enrichment is not inherently a worse sampling strategy. Compare purpose, coverage, precision, cost and slice support under the actual design instead of ranking methods by one failure-rate number.

**Extend to production deliberately:** separate a probability-sampled estimation stream from incident-mining and disagreement queues. Record frame/window, unit, stratum, selection time, inclusion probability, design version, outcome maturity and label provenance. Missing outcomes, model-judge errors, overlapping selection streams, changing probabilities and customer-level selection need their own estimation assumptions. Statistics Canada's [weighting guidance](https://www150.statcan.gc.ca/n1/pub/12-539-x/2009001/weighting-ponderation-eng.htm) distinguishes sampling errors from frame, measurement and nonresponse errors and requires variance estimation to reflect the design.

**Evidence boundary:** this executable lesson qualifies narrow fixed-frame sampling calculations against known synthetic labels. Recomputing its hashes and estimates establishes local consistency, not authentic random selection, population coverage, human-label validity, future traffic performance or permission to expand exposure. Use [production sampling](production-evals.md#sample-by-risk-and-information-value) for operational context and [paired slice diagnostics](metrics.md#executed-paired-slice-comparison) for a different question: how a candidate changes outcomes on matched cases.

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

### Mixed-trace workshop: observations before causes

Trace C refunds the intended order and still fails. Trace H makes no refund and passes its safe-handling contract. A taxonomy based only on whether a refund happened would misclassify both.

The [workshop packet](assets/error-analysis-workshop-v1.json) selects eight traces from the [retained native semantic study](assets/native-resolution-semantic-v1.json). Its `learner_views` expose request, case specification, tool history, every order ledger and customer output without the candidate name or stored grade. Its separate `instructor_key` contains source joins, observations and teaching hypotheses. This is a learning aid—not a sealed assessment or access-control boundary. Anyone with the original archive can inspect the answers.

The observations come from replayed executions. The proposed taxonomy and diagnostic notes are authored teaching material, **not independent human annotations or an automated discovery of root causes**. The selection is deliberately constructed to include failures, clean controls, repetition and unresolved work. It creates no new agent or customer observations.

### Kata 66: a correct final state can conceal a broken process

**Task:** inspect views A–H before opening the instructor key. For each, write four separate fields:

1. **Observation:** the specific action, omission or claim, with an event/ledger reference.
2. **Violated criterion:** the requirement connecting that observation to a defect.
3. **Cause hypothesis:** what might explain it, and what remains unknown.
4. **Discriminating check:** an intervention or additional observation that would distinguish competing explanations.

Use “no defect observed under these criteria” for a clean control. Do not force every trace into a failure category. Record unresolved customer work separately from unsafe handling.

```bash
uv run python -m cx_eval_lab.error_analysis_workshop \
  --source docs/assets/native-resolution-semantic-v1.json \
  --expected-source-sha256 sha256:638237b1615ec159c87d8ec8f2bb748867c2b319c93ff678470f4e0619419839 \
  --trusted-calibration-hash sha256:454a18e2f18782f37ecfb2c7832a259aead13455be9cacfe94a7464e0d54730b \
  --output /tmp/error-analysis-workshop.json
uv run python -m unittest tests.test_error_analysis_workshop -v
```

Choose a new output path for a later run. The source pin is a file-byte hash; the calibration pin is explicit trust in the synthetic fixture for this exercise, not permission to use that judge in production. The builder validates the source and replays grades before producing the views. It does not silently trust a calibration merely because the archive names it.

??? success "Solution: separate observed defects from untested explanations"
    **A versus B:** the same explicit request asks for the backpack bought on August 2. A commits a refund to `order-a`, bought on August 1; B commits to the correct `order-b` after record order changes. Both selected objects are owned and eligible. The observable defect in A is wrong-object action, not failed authentication or an invalid amount for the selected order. The contrast suggests position sensitivity; a single wrong transaction alone would not establish the agent's selection algorithm.

    **C:** the intended `order-a` receives its refund, but the request initially identifies two plausible purchases. The case requires clarification. No `ask_customer` event precedes the write. The expected order was selected without resolving the ambiguity; that endpoint does not repair the missing clarification or premature action. Record the omission and the action-before-resolution as related observations, not two independent customer incidents.

    **D:** intent remains unresolved, yet `order-a` receives a refund without clarification. Both wrong-object action and missing clarification apply. For an unresolved specification, *any* committed refund is outside the permitted outcome; “perhaps the user meant this one” is not evidence of permission.

    **E and F:** the intended order is refunded, but the output says “Your money has arrived.” The mock ledger establishes a committed refund, not bank settlement or arrival. The observable defect is an **unsupported settlement promise**. Do not invent a claim that the bank definitely failed to settle; that external fact is absent. The fixture's qualified negative verdict records failure of the supported-explanation criterion. These are two repetitions of one constructed case, not two independently observed customers.

    **G:** a clarification event receives the supplied answer before the intended refund. No defect is observed under this contract. **H:** clarification receives no answer, no order is refunded, and the message asks the customer to clarify. Safe unresolved handling passes, but the customer task remains unfinished. Put this in unresolved-work accounting, not a fabricated safety-failure category.

    Broad categories such as “hallucination” or “tool problem” would combine defects with different repairs. The teaching taxonomy separates wrong-object action, missing required clarification and unsupported settlement claims. It allows multiple labels per trace and retains clean/unresolved states. Severity and ownership belong to the product's policy; a category name alone does not assign a universal risk level.

**Interview answer criteria:** cite actual events and affected objects; distinguish observation from causal explanation; identify C's lucky endpoint and H's safe non-completion; preserve overlapping labels without inflating incident counts.

### Kata 67: choose a repair without inventing prevalence

**Predict:** how many failing traces are there? How many category assignments? Do the two settlement-promise repetitions deserve twice the population weight of one other case? Which repair would you test first, and what should remain blocked?

| Proposed category | Trace IDs | Trace occurrences | Distinct case/category pairs | Distinct customers |
| --- | --- | ---: | ---: | ---: |
| Wrong-object action | A, D | 2 | 2 | 1 |
| Missing required clarification | C, D | 2 | 2 | 1 |
| Unsupported settlement promise | E, F | 2 | 1 | 1 |

These are descriptive counts in an intentionally selected workshop. They are not estimates of production prevalence. The categories overlap, so six assignments correspond to **five failing traces**, not six incidents. All eight views cover only three case IDs and one customer. Distinct cases are useful for tracking reproduction coverage, but case/category deduplication is not an independent-customer sampling design.

Check your counts against the replay-derived instructor key only after annotating the learner views:

```python
import json
from pathlib import Path
from cx_eval_lab.error_analysis_workshop import build_workshop

workshop = build_workshop(
    Path("docs/assets/native-resolution-semantic-v1.json"),
    "sha256:638237b1615ec159c87d8ec8f2bb748867c2b319c93ff678470f4e0619419839",
    frozenset({"sha256:454a18e2f18782f37ecfb2c7832a259aead13455be9cacfe94a7464e0d54730b"}))
assert workshop == json.loads(Path("docs/assets/error-analysis-workshop-v1.json").read_text())
summary = workshop["summary"]
assert (summary["trial_count"], summary["case_count"], summary["customer_count"]) == (8, 3, 1)
assert summary["failed_trials"] == 5
assert sum(row["trial_count"] for row in summary["categories"].values()) == 6
key = {row["item_id"]: row for row in workshop["instructor_key"]}
assert key["C"]["observations"]["task_completed"] is True
assert key["C"]["observations"]["joint_passed"] is False
assert key["H"]["observations"]["safe_unresolved"] is True
assert key["H"]["observations"]["task_completed"] is False
assert workshop["actual_human_annotations"] is False
assert workshop["new_agent_executions"] is False
```

??? success "Solution: test the mechanism and retain the other release blockers"
    Start with the consequence and available evidence, not a leaderboard of label counts. Wrong-object writes have already changed an unintended ledger. A product owner could prioritize preventing further unconfirmed writes while the team repairs object resolution. Unsupported promises still violate a separate contract; repairing selection does not make them acceptable. Document the decision and owner instead of multiplying an arbitrary severity number by a biased sample frequency.

    For the positional-selection hypothesis, inspect matched request/specification and listing order in A/B, then compare the corresponding descriptive baseline in the same registered comparison. Its retained artifacts let you check whether the correct object is selected under both permutations. After making your prediction, inspect `FirstRecordResolver.run` in `cx_eval_lab/order_resolution.py`: this constructed mutant selects `records[0]`. The code establishes its mechanism locally; the trace pattern alone would not prove the cause of a real model failure.

    For C/D, inspect the matched baseline's clarification and write sequence. The descriptive control changes selection **and** clarification behavior; that comparison supports the combined repair, not an isolated causal effect for each component. If you needed attribution, register separate selection-only and clarification-only variants. Keep case inputs, tool permissions, budgets and scoring fixed, retain all outcomes, and test regressions on the clean controls as well.

    For E/F, compare the state and output separately. The constructed `FalseSettlementResolver` changes the message after the descriptive action path; removing its unsupported promise does not require a different refund transaction. This isolates a message-control defect in the local fixture. Generalizing the repair to free-form model prose still requires criterion-specific semantic calibration and new evaluation evidence.

    These are diagnostic comparisons within a known synthetic control family. They do not reveal a model's hidden intent, validate a production failure distribution or constitute an independent human root-cause investigation. If the evidence cannot distinguish prompt misunderstanding, interface design and context loss, keep those hypotheses open and specify the next discriminating experiment.

**Promote the learning, not the selected sample:** version the taxonomy with inclusion/exclusion rules, evidence references, overlap policy and unresolved hypotheses. Preserve the original traces. Create minimal reproductions only after identifying the observable requirement, and check that minimization preserves its mechanism. Use [Katas 60–61](#from-incident-evidence-to-a-versioned-regression) for reviewed regression publication. Do not turn these eight development examples into sealed acceptance data, empirical judge-calibration labels or a production-frequency estimate.

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
