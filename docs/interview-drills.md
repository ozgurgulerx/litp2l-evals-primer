# Interview & Design Drills

This page converts the supplied research bank into a smaller practice system. The [complete 118-question appendix](interview-question-bank.md) preserves every canonical ID, variant and source answer outline; the drills below develop selected questions more deeply. The aim is not to memorise definitions. It is to practise turning an ambiguous request into a valid measurement and release decision.

## Answer contract

For a complete numerical answer, work through [Katas 90–92: the calibration decision workshop](calibration-decision-workshop.md). Supplied confusion matrices connect rare false passes, abstention, independent sample requirements, prevalence shift and human-review capacity to one bounded decision. Its worked solutions are authored examples, not a report of an employer's interview or actual judge qualification.

A strong senior answer should normally expose seven moves:

1. **Decision** — What decision will the evidence inform: diagnose, select, release, expand, constrain, or roll back?
2. **Construct** — What quality, capability, risk, or outcome is actually being measured?
3. **Population and unit** — Which users/tasks and what unit: case, trial, session, claim, tool call, or outcome?
4. **Evidence** — Which dataset roles, environments, traces, graders, humans, and external state are authoritative?
5. **Analysis** — Which denominators, slices, paired comparisons, uncertainty, and validity checks apply?
6. **Action rule** — Which hard invariants, non-inferiority margins, superiority claims, operational bounds, and abstention rules change exposure?
7. **Learning loop** — How do failures, incidents, and evaluator drift improve the suite without contaminating acceptance evidence?

This is a reasoning frame, not a script. A concise answer may combine several moves, but skipping the decision, population, or authority usually produces a metric catalogue rather than an evaluation design.

## Thirteen-theme drill map

| Theme | Diagnostic question | Primary chapter | Proof to sketch |
| --- | --- | --- | --- |
| 1 · Fundamentals & metrics | What does “good” mean for this exact decision? | [Foundations](foundations.md); [Metrics](metrics.md) | Evaluation contract and metric vector |
| 2 · Benchmarks & contamination | What construct and protocol produced this score? | [Benchmark Reproducibility](benchmark-reproducibility.md) | Complete run manifest |
| 3 · Human evaluation | Who has authority to label the construct, and how reliable is the process? | [Human Evaluation](human-evaluation.md) | Protocol, overlap, disagreement, adjudication |
| 4 · LLM-as-a-judge | Against what frozen human evidence is the judge qualified? | [LLM as a Judge](llm-as-a-judge.md) | Criterion-specific calibration report |
| 5 · Robustness & adversarial | What may vary and what must remain invariant? | [Robustness, Safety & Fairness](robustness-safety.md) | Threat-linked transformation suite |
| 6 · Bias & fairness | Which groups, intersections, and outcomes could differ unfairly? | [Robustness, Safety & Fairness](robustness-safety.md) | Crossed-slice report with support and uncertainty |
| 7 · Calibration & uncertainty | Does confidence match empirical correctness at the decision boundary? | [Metrics](metrics.md); [LLM as a Judge](llm-as-a-judge.md) | Reliability/risk–coverage curve |
| 8 · Prompt evaluation & dataset curation | Did one controlled intervention help on independent evidence? | [Dataset Design](dataset-design.md); [Build Lab](build-the-system.md) | Paired prompt experiment and dataset release |
| 9 · Reproducibility & statistics | Would the decision survive rerun, resampling, and reasonable analysis choices? | [Metrics](metrics.md); [Benchmark Reproducibility](benchmark-reproducibility.md) | Paired interval plus manifest |
| 10 · Tooling, MLOps & continuous evaluation | Can evidence move portably from trace to gate to incident? | [Production Evals](production-evals.md); [System Studies](system-studies.md) | Provider-neutral trace and release packet |
| 11 · RAG, agents & system evaluation | Where did the system fail: retrieval, claim, action, trajectory, or state? | [RAG & Research Evals](rag-research-evals.md); [Agent Evals](agent-evals.md) | Atomic claims and partial-order trajectory |
| 12 · Interpretability | Does the explanation reveal a causal mechanism or merely sound plausible? | [Robustness, Safety & Fairness](robustness-safety.md) | Intervention with predicted behavioral effect |
| 13 · Safety, RLHF & alignment | Did optimisation improve independent human value without new harmful behavior? | [Robustness, Safety & Fairness](robustness-safety.md) | Held-out preference, safety, and capability vector |

## Theme drills and answer checks

### 1. Fundamentals & evaluation metrics

**Prompt:** Design an evaluation framework for a new customer-support LLM.

A strong answer begins with the user promise and failure cost, then defines cases, trials, traces, external outcomes, slices, dataset roles, graders, uncertainty, and a staged release rule. It does not begin by choosing an evaluation framework or a generic “accuracy” metric.

**Counterprompt:** BLEU, ROUGE, and semantic similarity all improve, but verified refund resolution falls. Which result wins?

The external outcome wins for the release decision because surface similarity is not the product construct. Diagnose why the proxies moved in the wrong direction; do not discard them if they remain useful diagnostics.

**Evidence receipt:** one evaluation contract connecting every metric to a decision and failure cost.

### 2. Benchmarks & contamination

**Prompt:** A candidate model gains five points on a public benchmark. What can you conclude?

Only that it scored higher under a particular task revision, prompt, few-shot setup, inference configuration, answer extractor, harness, and budget. Ask about uncertainty, exclusions, contamination, saturation, and distance from the deployment workload before claiming broader capability.

**Counterprompt:** How would you make the result harder to game?

Use fresh temporal/private cases, controlled transformations, provenance and overlap analysis, hidden acceptance labels, stable anchor cases, and independent product evidence. No single decontamination check proves absence of exposure.

**Evidence receipt:** benchmark manifest plus a two-harness discrepancy report.

### 3. Human evaluation & annotation

**Prompt:** Two reviewers disagree on 40% of groundedness labels. What do you do?

Slice disagreement, inspect ambiguous items, confirm reviewer authority, clarify observable rubric anchors, retrain/qualify reviewers, repeat a controlled subset, and adjudicate consequential cases. Preserve legitimate ambiguity instead of forcing artificial consensus.

**Counterprompt:** Should a domain expert or end user be the gold label?

It depends on the construct. A policy or medical fact may require expert authority; usefulness and preference may require target users. Encode a label hierarchy when both perspectives matter.

**Evidence receipt:** frozen instructions, reviewer qualifications, blinded overlap, agreement, item-level labels, disagreement reasons, adjudication, and protocol version.

### 4. LLM-as-a-judge

**Prompt:** When may an LLM judge block a release?

Only for a named criterion and population where frozen independent human evidence demonstrates sufficient agreement, false-pass/false-block behavior, stability, and bias controls. Its authority needs thresholds, abstention, requalification triggers, and an escalation path.

**Counterprompt:** Overall agreement is 92%, so is the judge ready?

Not necessarily. Rare unsafe failures can be hidden by prevalence. Inspect the confusion matrix, especially false passes, and slice by language, length, answer position, model identity, difficulty, and risk.

**Evidence receipt:** calibration report with qualification, failure slices, risk–coverage, and authority decision.

### 5. Robustness & adversarial evaluation

**Prompt:** How would you test robustness to prompt wording?

Define meaning-preserving transformations, validate that the expected answer truly remains invariant, run paired trials, and report both average and worst-case degradation. Separate benign variation from attacks that change the task.

**Counterprompt:** How would you test indirect prompt injection?

Place adversarial instructions in retrieved or tool-returned content under a stated attacker capability and budget. Check data exfiltration, unauthorized actions, policy bypass, safe refusal, and benign false positives in actual system state—not just the final prose.

**Evidence receipt:** threat model, transformation generator/version, human validation sample, crossed benign/attack suite, severity, and promoted regressions.

### 6. Bias & fairness

Compute [the raw and standardized language gap](robustness-safety.md#worked-micro-kata-a-raw-gap-and-a-case-mix-explanation), then defend why neither result alone establishes fairness.

**Prompt:** Global task success is 90%. Is the system fair?

The aggregate cannot answer. Define the relevant outcome and groups, inspect language/workflow/risk intersections with support and uncertainty, control for case mix where appropriate, and examine worst-slice failure mechanisms. Attribute use must satisfy privacy and governance requirements.

**Counterprompt:** Turkish success is lower, but Turkish cases are harder. What next?

Report the raw disparity and a like-for-like or stratified analysis; do not erase either. Expand representative coverage, inspect measurement equivalence and reviewer calibration by language, then decide against a pre-registered protected-slice rule.

**Evidence receipt:** crossed-slice report with denominators, intervals, missingness, case mix, and remediation owner.

### 7. Calibration & uncertainty

**Prompt:** A model says it is 90% confident. What does calibrated mean?

Across comparable predictions near 0.9, roughly 90% should be correct under the stated population and scoring rule. Calibration is not accuracy: a cautious weak model can be calibrated, and an accurate model can be overconfident.

**Counterprompt:** Which metric would you report?

Use reliability diagrams plus a proper score such as Brier or log loss; ECE can summarize but depends on binning. For automation, report selective risk versus coverage at the threshold and show slice behavior.

**Evidence receipt:** probability/correctness pairs, binning rule, reliability curve, Brier/NLL/ECE, threshold sensitivity, and abstention action.

### 8. Prompt evaluation & dataset curation

**Prompt:** How would you evaluate a prompt change before shipping?

Register the claimed effect, hold other system components fixed where attribution matters, run baseline and candidate on paired trials, use optimisation data for iteration, preserve sealed acceptance, and apply independent hard, slice, statistical, latency, and cost rules.

**Counterprompt:** A production incident is fixed. Where does the case go?

Minimise and review a privacy-safe reproduction, classify it as regression data, record incident lineage and failure taxonomy, version the release, rerun the baseline, check duplicates/near-duplicates, and keep it out of sealed evidence once used for tuning.

**Evidence receipt:** prompt/system manifest, paired report, and reviewed dataset-change record.

### 9. Reproducibility & statistics

**Prompt:** Candidate success is 84% versus 82%. Ship?

Not from those point estimates. State the estimand and unit, use paired evidence when both systems see the same cases, handle repeated trials and clusters, calculate an interval, inspect protected slices, then compare with the registered superiority or non-inferiority margin.

**Counterprompt:** Zero severe failures occurred in 100 trials. Is the true rate zero?

No. A rough 95% upper bound from the rule of three is about 3%. Rare, severe events need larger/exposure-targeted suites, mechanism-based tests, and hard runtime controls.

**Evidence receipt:** per-trial paired data, analysis code, interval, minimum-detectable-effect rationale, multiplicity policy, and decision.

### 10. Tooling, MLOps & continuous evaluation

**Prompt:** How would you select an eval platform?

Start from required cases, environments, traces, custom graders, comparisons, CI, production sampling, access controls, scale, and export. Run the same small acceptance suite in shortlisted tools and compare evidence fidelity, operational fit, and exit cost—not stars or dashboard polish.

**Counterprompt:** How do you evaluate continuously without judging every request?

Run cheap deterministic controls broadly, capture consequential events, maintain a representative stream for prevalence, stratify new releases and risk slices, oversample uncertainty/failures for diagnosis, record inclusion probabilities, and route mature findings into reviewed regressions.

**Evidence receipt:** adapter export proving the case/trace/result/manifest remains usable outside the vendor.

### 11. RAG, agents & system evaluation

**Prompt:** Retrieval recall is high but answer quality is poor. How do you localize it?

Inspect ranking/noise and evidence placement, evaluate generation on oracle context, decompose the response into atomic claims, grade support/correctness/citation authority separately, and check whether the answer used the provided evidence.

**Counterprompt:** An agent succeeds through a different tool path than the reference. Pass or fail?

Use final authoritative state, required/forbidden actions, partial-order constraints, permissions, side effects, recovery, and resource use. Do not require exact path equality when multiple safe paths are valid.

**Evidence receipt:** retrieval result, atomic-claim table, normalized trace, trajectory grade, final state, budgets, and outcome.

### 12. Interpretability

**Prompt:** The model provides a convincing rationale. Is it faithful?

Plausibility is not causal evidence. State the proposed mechanism, intervene on the cited evidence/feature/tool result, predict how behavior should change, include controls, and measure whether the effect is stable across relevant cases.

**Counterprompt:** Can interpretability replace behavioral safety tests?

No, unless the method has validated causal and predictive linkage for the decision—an unusually high bar. Use it as complementary evidence and preserve behavioral, adversarial, and outcome checks.

**Evidence receipt:** intervention plan, preregistered behavioral prediction, controls, observed effect, limitations, and decision relevance.

### 13. Safety, RLHF & alignment

Work through [optimization pressure reverses the verdict](robustness-safety.md#worked-micro-kata-optimization-pressure-reverses-the-verdict): compute paired task changes and preference conventions, reject the proxy winner, and explain why the alternative still needs qualification.

**Prompt:** How do you know RLHF improved the system?

Compare against the base/SFT system on held-out preference evidence plus independent capability, factuality, fairness, harmful-compliance, false-refusal, robustness, and production-shaped tasks. Validate the reward model separately and look for reward overoptimisation.

**Counterprompt:** Safety wants more refusal; product wants less. Resolve it.

Measure harmful compliance and benign false refusal separately by risk class, build the frontier, set non-compensating constraints, improve detection/policy boundaries, and escalate genuinely ambiguous high-risk cases. A single refusal rate hides both harms.

**Evidence receipt:** preference-data audit, reward-model validation, post-optimisation independent suite, safety frontier, and release constraints.

## Whiteboard drills

### Paired bootstrap

Write per-case differences first:

```python
def paired_bootstrap(candidate, baseline, draws, rng):
    differences = [c - b for c, b in zip(candidate, baseline, strict=True)]
    estimates = []
    for _ in range(draws):
        sample = rng.choices(differences, k=len(differences))
        estimates.append(sum(sample) / len(sample))
    return sorted(estimates)
```

Explain the unit of resampling. If several stochastic trials share one case, naively resampling trials treats dependent observations as independent; resample cases or use a hierarchical method.

### Judge-bias reversal

```text
human-labelled pair (A, B)
→ judge blinded pair (A, B)
→ judge blinded pair (B, A)
→ compare preference after label normalization
→ stratify reversals by length and model identity
```

A reversal inconsistency is diagnostic. Consistency after swapping is still not proof of human validity.

### RAG evaluator

```text
query + expected evidence set
→ retrieve ranked chunks
→ score recall/precision/rank
→ generate answer
→ split into atomic claims
→ grade correctness, support, citation entailment, authority, completeness
→ add latency/cost and end-to-end task outcome
```

Oracle-context generation isolates whether the generator can answer when retrieval succeeds.

### Agent evaluator

```text
reset environment
→ run one trial under declared budgets
→ validate tool names, arguments, permissions, and partial order
→ inspect irreversible effects and final authoritative state
→ grade outcome, safety, recovery, conversation, efficiency, operations
```

Challenge the evaluator with a successful alternate path, a false-success claim, a policy bypass, and a timeout-after-commit retry.

### Confidence calibration

Given `(confidence, correctness)` pairs, draw the reliability curve, calculate Brier score, then vary the abstention threshold. The release question is not only “is ECE small?” but “at this coverage, is false-pass risk safe enough for the assigned action?”

### Release gate

Write the order explicitly:

```text
lineage → deterministic validity → grader authority → hard invariants
→ slice floors → registered comparative claim → operations
→ shadow → canary → expansion or rollback
```

Missing required evidence is a blocker, not zero.

### Perturbation harness

```text
base case + expected decision
→ apply a named transformation with a recorded seed
→ verify whether the transformation preserves or changes the label
→ run base and variant as a pair
→ grade task correctness and the expected relation separately
→ slice by transformation family and severity
→ promote reviewed novel failures into regression/adversarial data
```

Include a paraphrase, translated request, irrelevant distractor, label-changing eligibility flip, indirect injection, and tool fault. A consistently wrong pair is invariant but not correct; report both properties.

### Atomic factuality

```text
response
→ split into independently verifiable material claims
→ bind each claim to cited/retrieved evidence and an as-of time
→ label correctness, support, contradiction, and verifiability separately
→ score citation entailment, completeness, resolution, and source authority
→ aggregate only after preserving the claim table and materiality
```

Test four cells explicitly: correct/supported, correct/unsupported, wrong/supported-by-stale-evidence, and wrong/unsupported. This prevents “groundedness” from silently becoming a substitute for truth.

## Senior scenario drills

### The aggregate improves; one slice regresses

Ask whether the slice was protected, its support and uncertainty, whether the comparison is like-for-like, and which action was registered. The options are fix, block, constrain exposure to supported slices, or use a governed non-hard exception. Reweighting after the result is not a valid repair.

### Offline passes; production fails

Preserve the trace and external state, bound exposure, identify the earliest causal failure, reproduce it, locate the missing population/threat/environment assumption, repair the case or grader, and requalify before staged re-release. Measure incident-to-case latency and whether the repaired suite predicts the next canary.

### Human and judge disagree

Do not choose the cheaper answer by default. Confirm human authority and protocol quality, inspect criterion/slice errors, adjudicate consequential cases, tighten the rubric if ambiguity is avoidable, and reduce or revoke judge authority until new frozen evidence supports it.

### A stakeholder wants one quality score

Offer a decision-specific dashboard: hard invariants, protected slices, task outcome, uncertainty, latency, reliability, and cost. Aggregate only if weights have a defensible meaning for that decision, and never allow a weighted gain to compensate for a prohibited action.

## Evidence receipts

After practising a theme, save a minimal receipt:

```yaml
drill_id: judge-authority-01
date: 2026-09-06
decision: allow_advisory_triage_only
construct: grounded_policy_explanation
population: english_and_turkish_refund_explanations
unit: response
evidence:
  dataset: judge-calibration-v1
  human_protocol: groundedness-human-v2
  judge: groundedness-judge-v3
analysis:
  false_pass_rate_among_decided_human_fails: 0.125
  slices_reviewed: [language, length, risk]
limitations:
  - only 32 human-fail examples received an automated pass_or_fail decision
next_action: collect_and_review_more_high-risk_failures
```

The receipt should make the decision reproducible, not merely say that the answer “covered evals.”

## Self-review rubric

Score each answer 0, 1, or 2 on these dimensions:

| Dimension | 0 | 1 | 2 |
| --- | --- | --- | --- |
| Decision | No action named | General purpose | Exact decision and exposure consequence |
| Construct | Metric substituted for quality | Construct named | Construct, failure costs, and limits explicit |
| Population/unit | Missing | One named | Population, slices, unit, and dependence clear |
| Evidence/authority | Tool list | Graders/dataset named | Authority, provenance, role separation, calibration clear |
| Analysis | Point estimate | Some slices/statistics | Paired/clustered uncertainty and validity matched to design |
| Gate | “Pass if score is good” | Threshold named | Independent rule types, missing evidence, abstention, rollback |
| Learning | No feedback loop | “Add failures” | Reviewed promotion, versioning, contamination and predictive validity |

A total score is useful for practice, but any zero on decision, evidence authority, or gate is a non-compensating weakness for a senior design answer.

## Practice order

1. Answer one theme drill in two minutes using the seven-move contract.
2. Expand it into a ten-minute system design with one synthetic example.
3. Draw the relevant whiteboard artifact without a vendor API.
4. Attack your own answer with a contamination, denominator, authority, or rare-event counterexample.
5. Save the evidence receipt and promote any durable insight into the running CX lab.

This page is the practice index. The linked chapters remain the full explanations and source-grounded reference.
