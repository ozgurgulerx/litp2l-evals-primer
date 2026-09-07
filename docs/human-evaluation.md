# Human Evaluation

Human evaluation is not a ceremonial check after automated scoring. It is the process used to define a construct, test whether people can apply that definition consistently, and create evidence against which automated graders can be qualified.

!!! important "Human labels are measurements"
    A label is produced by a person, protocol, interface, evidence packet, and aggregation rule. Change any of those and the measuring instrument changes. “Human ground truth” is too strong when the task is ambiguous or the rubric is underspecified.

## Start with the decision

Do not ask reviewers whether an answer is “good.” State what their labels will decide.

| Decision | Useful human task | Poor substitute |
| --- | --- | --- |
| Is a response grounded? | Mark each factual claim as supported, contradicted, or unsupported using supplied evidence | Overall writing preference |
| Which response resolves the customer’s problem better? | Blind pairwise comparison with a tie option and explicit criteria | One unanchored 1–10 score |
| Can a semantic judge block releases? | Independently label a frozen qualification set | Reviewing only judge disagreements |
| What failures matter in production? | Classify a stratified trace sample and record new failure modes | Rating a convenient sample of recent conversations |

The unit of annotation must match the construct. A tool argument can be reviewed at the step level; coherence needs a thread; resolution may require the final system-of-record state.

## Write an annotation protocol

A reproducible protocol fixes:

1. **Population:** which traffic, workflows, languages, risks, and time window the sample represents.
2. **Unit:** response, claim, turn, trace, session, or verified outcome.
3. **Evidence:** what the reviewer may see and what must be hidden.
4. **Question:** one observable criterion at a time.
5. **Scale:** categorical, ordinal, pairwise, ranking, or free-text diagnosis.
6. **Unknown rule:** when evidence is insufficient or the rubric does not apply.
7. **Reviewers:** required expertise, language, training, and conflicts.
8. **Aggregation:** majority, median, probabilistic model, or adjudication.
9. **Quality control:** pilot, anchors, duplicate items, attention checks, and drift review.
10. **Versioning:** protocol, rubric, interface, evidence, and reviewer-pool versions.

### Prefer observable labels

Replace vague criteria with evidence a reviewer can point to.

| Vague | Observable |
| --- | --- |
| Helpful | Identifies the eligible option, gives the next action, and does not request information already supplied |
| Correct | Every material claim follows from the supplied policy and verified order state |
| Good tone | Acknowledges inconvenience once, avoids blame, and does not obscure the action with filler |
| Safe | Does not expose private data, exceed authorization, or execute a prohibited state change |

One label should not combine correctness, style, policy, and outcome. When a score fails, the team needs to know what to repair.

## Choose the response format

### Categorical labels

Use `pass`, `fail`, and `insufficient_evidence` for a crisp release criterion. The third category prevents reviewers from inventing evidence.

### Ordinal scales

Use anchored levels when quality genuinely has ordered degrees. Every level needs positive and negative anchors.

```yaml
criterion: resolution_explanation
scale:
  0: "Incorrect or claims an action that did not occur"
  1: "Correct status, but no useful next step"
  2: "Correct status and next step; material detail missing"
  3: "Correct, complete, concise, and consistent with verified state"
```

Do not assume that the distance from 0 to 1 equals the distance from 2 to 3. An ordinal mean can be convenient, but the distribution and threshold counts remain important.

### Pairwise comparison

Pairwise tasks often make relative preference easier: show responses A and B in randomized order and ask which better satisfies a named criterion. Include `tie` and `both_unacceptable`; otherwise reviewers may be forced to endorse a bad answer.

Pairwise preference is not absolute acceptability. Candidate B can beat A while both fail the release floor.

### Ranking

Ranking several alternatives is useful for preference research but creates more cognitive load and dependence between observations. Use it deliberately, not because a leaderboard is visually appealing.

## Sample for the decision, not convenience

A random sample estimates the dominant traffic distribution. It may almost never include a rare high-risk case. Combine sampling designs:

- **Representative sample** for expected user experience.
- **Stratified sample** for languages, workflows, customer groups, and model versions.
- **Risk sample** for rare but severe failures.
- **Disagreement sample** for rubric and judge diagnosis.
- **Fresh temporal sample** for drift.

Always retain sampling weights when a deliberately balanced review set is used to estimate production prevalence. A set with 50% Turkish cases is excellent for comparison but should not be reported as the unweighted global failure rate if production is 8% Turkish.

## Train and qualify reviewers

Reviewer training should include:

- the decision and construct;
- inclusion and exclusion rules;
- positive, negative, boundary, and insufficient-evidence anchors;
- a blinded qualification batch;
- feedback on disagreements;
- a rule for escalation rather than improvisation.

Domain expertise depends on the task. A fluent speaker may judge clarity; a policy specialist may be required to judge eligibility; only authoritative state can prove whether a refund occurred.

## Reliability is necessary, not sufficient

**Raw agreement** is the proportion of identical labels. It is easy to read but ignores agreement expected by chance.

**Cohen’s κ** adjusts two-reviewer categorical agreement for chance:

\[
\kappa = \frac{p_o-p_e}{1-p_e}
\]

where \(p_o\) is observed agreement and \(p_e\) is agreement expected from the reviewers’ marginal label frequencies.

Fleiss’ κ extends the idea to multiple reviewers for some categorical designs. Krippendorff’s α supports multiple reviewers, missing labels, and different distance functions. None proves validity: reviewers can agree perfectly on the wrong interpretation.

Report at least:

- number of items and labels;
- label distribution;
- raw agreement;
- an appropriate agreement statistic and interval;
- disagreement by slice and criterion;
- missing/abstained labels;
- adjudication rate;
- protocol and reviewer-pool versions.

!!! warning "Prevalence can distort agreement statistics"
    When almost every item has the same label, high raw agreement can coexist with an unintuitive κ. Inspect the confusion table and prevalence instead of treating one coefficient as a universal pass/fail score.

## Separate disagreement from error

Disagreement can mean:

1. one reviewer made a mistake;
2. the evidence packet was incomplete;
3. the rubric was unclear;
4. the case contains two legitimate interpretations;
5. the construct is genuinely subjective;
6. the reviewer pool represents different user values.

The correct response is not always majority vote. Record a disagreement reason, revise the rubric if needed, and preserve `ambiguous` when ambiguity is part of reality.

## Adjudication

Adjudication produces a reviewed label and a learning record. The adjudicator should see the independent labels and rationales only after making an initial blind assessment where practical.

```json
{
  "case_id": "cx-017",
  "criterion": "grounded_status",
  "labels": ["pass", "fail", "fail"],
  "adjudicated_label": "fail",
  "reason": "The response says the refund settled; the ledger only shows submitted.",
  "rubric_change": "Clarify that pending and settled are distinct states.",
  "protocol_version": "grounding-v1.1"
}
```

Do not silently overwrite the original labels. They are evidence about measurement difficulty and future judge risk.

## Worked example: eight synthetic CX conversations

Three reviewers inspect the response, relevant policy excerpt, tool trace, and final order state. They label **resolution explanation** as `pass`, `fail`, or `unknown`.

| Case | Situation | R1 | R2 | R3 | Reviewed result |
| --- | --- | --- | --- | --- | --- |
| H01 | Eligible refund completed and clearly explained | pass | pass | pass | pass |
| H02 | Agent claims success but no transaction exists | fail | fail | fail | fail |
| H03 | Transaction pending; response says “completed” | fail | fail | pass | fail |
| H04 | Policy document missing from evidence | unknown | unknown | fail | unknown |
| H05 | Correct refusal with concise reason | pass | pass | pass | pass |
| H06 | Correct result but needlessly accusatory tone | fail | pass | fail | fail |
| H07 | Turkish response uses an ambiguous settlement term | unknown | pass | unknown | unknown |
| H08 | Correct escalation and explicit next step | pass | pass | pass | pass |

The small table is a teaching sample, not evidence for a release. It exposes useful problems:

- H03 needs a stronger state anchor.
- H04 proves `unknown` is necessary.
- H06 shows that “resolution explanation” still mixes factual and interaction criteria.
- H07 requires a Turkish-language anchor or specialist review.

The next action is to split factual status from tone, refine anchors, and run a larger blinded pilot. It is not to average the labels and declare the rubric calibrated.

### Executed annotation analysis: preserve the disagreement

The table above gives R1 and R2 **75% raw agreement** and **κ = 25/41 ≈ 0.610**. Removing the cases where either reviewer says `unknown` increases raw agreement to **83.33%**, but leaves only six of eight cases. That change does not mean the reviewers improved.

The [retained rater study](assets/rater-study-v1.json) analyzes the existing synthetic annotation fixture without replacing it. It preserves all 24 original labels and the four authored adjudication records, then adds pairwise calculations, resampling sensitivity and a separate reviewer-assignment counterexample. These are executable analyses of supplied teaching labels, not newly collected human ratings. The source has situation descriptions, not full conversation/tool evidence or individual reviewer rationales; absent evidence must not be invented.

### Kata 72: did agreement improve, or did the denominator change?

**Predict:** compute R1/R2 agreement with `unknown` as a third category. Then exclude cases containing `unknown`. Finally, change R1's H04 annotation to missing. Are these three analyses measuring the same thing?

```bash
uv run python -m cx_eval_lab.rater_study --output /tmp/rater-study.json
uv run python -m unittest tests.test_rater_study -v
```

Use a new output path on subsequent runs. Start with the R1/R2 confusion table, with R1 on rows and R2 on columns. Neither axis is independent ground truth.

| R1 label / R2 label | pass | fail | unknown | R1 total |
| --- | --- | --- | --- | --- |
| pass | 3 | 0 | 0 | 3 |
| fail | 1 | 2 | 0 | 3 |
| unknown | 1 | 0 | 1 | 2 |
| R2 total | 5 | 2 | 1 | 8 |

The diagonal contains six agreements. The marginal-frequency term is `(3×5 + 3×2 + 2×1)/8² = 23/64`. Therefore `κ = (48/64 − 23/64)/(1 − 23/64) = 25/41`. This is an unweighted nominal-category statistic: it does not impose an ordinal distance between `pass`, `fail` and `unknown`. The [scikit-learn statistical reference](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.cohen_kappa_score.html) documents this definition and the possibility of undefined κ.

```python
import json
from pathlib import Path
from cx_eval_lab.rater_study import pair_metrics, replay_study

report = replay_study(json.loads(Path("docs/assets/rater-study-v1.json").read_text()))
fixture = report["inputs"]["source_fixture"]
labels = {(r["case_id"], r["reviewer"]): r["label"] for r in fixture["annotations"]}
pairs = [{"item_id": item["case_id"],
          "left": labels[item["case_id"], "R1"],
          "right": labels[item["case_id"], "R2"]} for item in fixture["items"]]
original = pair_metrics(pairs)
assert original == report["pair_metrics"]["R1:R2"]
assert original["full"]["kappa_exact"] == "25/41"
assert original["binary_decidable"]["n"] == 6

# A sensitivity check, not an edit to the source annotation archive.
missing = [{**row, "left": None} if row["item_id"] == "H04" else dict(row)
           for row in pairs]
changed = pair_metrics(missing)
assert changed["full"]["n"] == 7
assert abs(changed["full"]["observed_agreement"] - 5/7) < 1e-12
assert labels["H04", "R1"] == "unknown"
print(original["full"]["observed_agreement"], changed["full"]["observed_agreement"])
```

??? success "Solution: distinguish an unknown judgment from an absent observation"
    With all three categories, H04's `unknown/unknown` is an agreement. It means both reviewers declined to decide from the supplied evidence—not that the answer passed. H07's `unknown/pass` is a disagreement worth investigating. Keep unknown rates beside agreement; a reviewer who declines every item should not earn release authority for being consistent.

    The binary-decidable projection removes H04 and H07 because at least one reviewer says `unknown`. It has five agreements among six items, or 83.33%, with κ = 2/3. Its coverage is 6/8. This describes agreement conditional on both reviewers making a binary judgment. It does not repair the two difficult cases or estimate agreement on all original items.

    If R1's H04 annotation is missing (`null`), that pair has seven observed items and five agreements, or 5/7. The missing value is not an additional category and must not become a pass or fail. Other reviewer pairs remain analyzable when their own two observations are present. Report each pair's included IDs, exclusions and denominator; do not publish one unlabeled “agreement n.”

    The four adjudications remain separate records linked to the original item, labels and rubric. H06's adjudicated failure does not erase R2's pass or solve the mixed factual/tone criterion. The adjudication may guide a rubric revision; it is not independent evidence of reviewer accuracy simply because it has a final-looking label. Preserve uncertainty, provenance and unresolved reasons when preparing judge-calibration data.

**Uncertainty needs another explicit definition.** A binomial interval for the agreement indicator assumes independently sampled items under a stable annotation process; it is not an interval for κ. For six agreements in eight items, the 95% exact-binomial calculation gives approximately **34.91%–96.81%**. The report includes this assumption-labelled calculation, but eight fixed teaching items do not establish representative sampling. Rater dependence within an item is part of the agreement observation; dependence between sampled items or uncertainty from choosing a different reviewer pool needs a different analysis.

The registered R1/R2 item-bootstrap resamples whole paired observations, never the two reviewer columns independently. Its five occupied pair cells have counts `3, 2, 1, 1, 1`. The implementation enumerates 495 cell-count configurations, weighted by their multinomial multiplicities, representing all `8⁸ = 16,777,216` ordered resamples. It is exact for this empirical resampling distribution—not exact inference about a human population.

Some resamples contain only one agreeing category. Then `p_o = p_e = 1`, so κ is `0/0`, not zero or one. Their probability is `(3⁸ + 2⁸ + 1)/8⁸ = 3409/8388608`, about **0.04064%**. The report retains that undefined mass and labels its finite-value percentile range as **conditional on κ being defined**. It is descriptive sensitivity, not a coverage-qualified 95% κ confidence interval. Silently replacing undefined values or dropping them without reporting their mass changes the reported procedure.

The conditional 2.5th and 97.5th percentiles here are `5/53 ≈ 0.09434` and `1`. The broad range is worth showing alongside the point value 0.610, but its endpoints do not qualify the reviewer pool. Small selected examples, a mixed criterion and an unrepresentative reviewer pool are not repaired by exact enumeration.

**Interview answer criteria:** reconstruct the confusion table and marginals; distinguish agreement, acceptability and accuracy; report unknowns and missingness separately; state the projection's denominator; preserve item pairing and undefined resamples; explain why neither adjudication nor a κ threshold alone qualifies a judge.

### Kata 73: a reviewer assignment creates a model advantage

**Predict:** baseline and candidate have identical response content on four cases. A synthetic strict reviewer passes two cases; a synthetic lenient reviewer passes all four. What happens if baseline is assigned only to the strict reviewer and candidate only to the lenient reviewer?

| Assignment | Baseline observed pass rate | Candidate observed pass rate | Apparent candidate gain |
| --- | --- | --- | --- |
| Confounded: strict → baseline; lenient → candidate | 50% | 100% | +50 points |
| Crossed: both reviewers evaluate both arms | 75% | 75% | 0 points |

These labels are authored controls, not observations of real strict or lenient people. The artifact retains matching case IDs and equal baseline/candidate content hashes, the full synthetic potential-rating table and the observations exposed by each assignment. Each reviewer gives identical labels to both arms on the same case. “Strict” and “lenient” name different **pass propensities on the same items**, not established reviewer error or a fitted latent-severity parameter.

??? success "Solution: repair assignment before interpreting the arm difference"
    The confounded comparison changes the reviewer at the same time as the model label. Its +50-point gap cannot be attributed to the candidate. The crossed design exposes both reviewers to both arms on every case. Their individual paired arm differences are zero, so the panel's paired difference is also zero. The two pass propensities remain different; balancing assignment reveals rather than eliminates that fact.

    A real study cannot observe every person's counterfactual rating under every possible presentation. This constructed potential-rating table is a negative control showing that an analysis can report an advantage when arm content is held identical. It does not estimate how much a real reviewer pool is biased. Collect balanced overlap, hide model identity, randomize presentation order and retain assignments to test that empirically.

    Crossing alone does not solve carryover: seeing one answer may influence a later judgment of its duplicate. Specify order, spacing and any between-reviewer assignment before collection. For larger incomplete panels, estimate reviewer effects only under a connected design with enough overlap and a suitable model. Two disconnected reviewer pools cannot be made comparable merely by subtracting their average scores.

    Nor does zero gain prove acceptable outputs. Both variants may make the same mistake. Compare each against an independent factual or executable criterion where available, and retain `both_unacceptable` in preference tasks. Agreement and balanced assignment improve measurement design; neither creates an external correctness reference.

**Before using the analysis on actual human labels:** freeze criterion and evidence access; identify the sampling unit; arrange reviewer expertise and conflicts; register overlap and blinding; preserve missingness and disagreements; adjudicate with provenance; and keep development, calibration and acceptance cases separate. Treat the earlier H06 mixed criterion as a design problem to repair before collection, not noise to average away. Revisions produce linked new labels or rubric versions, not rewritten original ratings.

**Interview answer criteria:** identify assignment confounding; compare matched per-reviewer differences; explain why crossing differs from randomization and does not remove carryover; separate pass propensity from accuracy; specify what independent evidence would justify using these labels to qualify a model judge.

**Evidence boundary:** local replay validates calculations, assignment joins and retained synthetic inputs. No actual humans or models were evaluated. The resampling range is not population qualification; hashes are not proof of independent adjudication; the original eight-item criterion remains deliberately imperfect. Next steps require a real blinded pilot and independent validation. [Katas 70–71](dataset-design.md#executed-sampling-study-the-same-system-different-apparent-failure-rates) address sample selection; the [semantic grading lab](semantic-grading-lab.md) addresses how qualified evidence enters the judge lifecycle.

### Worked micro-kata: separate the reviewer from the treatment

For a continuous measurement with a defensible equal-interval scale, consider the illustrative model `rating = intercept + treatment_effect + reviewer_offset`. Two reviewers score identical baseline/candidate items:

| Reviewer | Baseline | Candidate |
| --- | ---: | ---: |
| Strict | 2 | 3 |
| Lenient | 4 | 5 |

**Exercise:** anchor the strict reviewer's offset at zero. Recover the intercept, reviewer offset and treatment contrast. What happens if only the strict-baseline and lenient-candidate cells are collected?

**Solution:** the intercept is 2, the lenient offset is 2, and both within-reviewer treatment differences are 1. Observing only the two diagonal cells gives a difference of 3, but cannot distinguish treatment from reviewer effects. Infinitely many allocations of that difference fit those two observations. A more sophisticated model does not create the missing overlap; a prior can impose an allocation, which must be reported as assumption-sensitive rather than identified by these data.

This table has no noise and is authored, so it provides no standard errors or population inference. A real crossed model might use `y_ir = mu + beta*treatment_i + u_i + v_r + error_ir`, with item effect `u_i` and reviewer effect `v_r`, plus justified interactions when reviewers respond differently to treatment. Retain item, reviewer, treatment and presentation identifiers. Estimate variance components from sufficient replicated, connected data; inspect residuals, reviewer-by-treatment effects and sensitivity to reviewer exclusion. One shared anchor is not automatically enough support for a useful fit.

Do not fit this linear example blindly to a four-level rubric: ordinal labels need an appropriate ordinal model and explicit thresholds, while binary pass/fail labels can use a suitable binary-response model. Expertise and target-user preference remain distinct constructs, not offsets to subtract until reviewers agree. Check model predictions against held-out ratings and external correctness evidence where available. Rater adjustment does not establish truth, erase legitimate disagreement or make a nonrandomized treatment contrast causal.

## Artifact: annotation specification

```yaml
annotation_study: cx-resolution-v1
population: refund conversations from synthetic release candidate rc-3
sample:
  representative: 60
  turkish_oversample: 20
  high_risk: 20
unit: complete_thread_with_verified_final_state
criteria:
  - factual_status
  - next_step_quality
  - interaction_quality
labels: [pass, fail, insufficient_evidence]
reviewers_per_item: 3
blinding:
  hide_model: true
  randomize_candidate_order: true
adjudication:
  trigger: disagreement_or_high_risk
versions:
  protocol: v1
  rubric: v1.2
  interface: v1
```

The corresponding result artifact should preserve per-reviewer labels, timestamps, rationales, sampling weights, adjudication, and exclusions. Do not retain personal reviewer details in broadly accessible experiment reports.

## Failure modes

| Failure mode | Symptom | Repair |
| --- | --- | --- |
| Undefined construct | Reviewers explain “helpful” differently | Split into observable criteria and add anchors |
| Convenience sampling | Scores look strong but omit difficult traffic | Define population and stratify by risk and slice |
| Forced choice | Reviewers select a winner when both fail | Add tie, both-unacceptable, or unknown |
| Unblinded identity | Preferred model wins before content is read | Hide identity and randomize order |
| Adjudication leakage | Judge owners tune against acceptance labels | Separate calibration and sealed acceptance access |
| Majority erases ambiguity | Contentious cases become falsely certain labels | Preserve disagreement reasons and ambiguous status |
| Reviewer drift | Labels change after several weeks | Insert anchors and run periodic requalification |
| One reviewer per item | Error and ambiguity are invisible | Overlap a planned subset and adjudicate high-risk cases |

## Exercise: repair a weak study

A team asks one support manager to rate 30 English conversations from the newest model from 1–5 for “quality.” The manager knows which model produced every response. The mean rises from 4.1 to 4.3, so the team ships globally.

Identify at least six problems and propose a minimum defensible redesign.

??? success "Answer"
    The construct is undefined; the scale is unanchored; one reviewer prevents reliability assessment; the sample is small and convenient; Turkish and risk slices are absent; model identity is visible; the comparison may not be paired; uncertainty is missing; absolute acceptability is not tested; final state is unavailable; and a global rollout is not justified. A better design pre-registers separate factual, policy, and interaction criteria; samples paired baseline/candidate threads across traffic and risk slices; hides identity and randomizes order; uses multiple trained reviewers on overlapping items; allows unknown/both-unacceptable; adjudicates disagreements; reports sample sizes, agreement, slice results, and intervals; and treats the result as only one input to a staged release gate.

## Verification checklist

- [ ] The annotation question maps to one decision.
- [ ] The unit and evidence packet match the construct.
- [ ] Labels have anchors and an unknown rule.
- [ ] Sampling represents traffic and rare risk separately.
- [ ] Reviewers are trained, qualified, and blinded where possible.
- [ ] Agreement and disagreement are reported by criterion and slice.
- [ ] Adjudication preserves original labels and reasons.
- [ ] Protocol and reviewer-pool changes create new versions.
- [ ] Human preference is not treated as proof of authoritative outcome.

## Primary reading

- [Chatbot Arena: an open platform for evaluating LLMs by human preference](https://arxiv.org/abs/2403.04132)
- [Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena](https://arxiv.org/abs/2306.05685)
- [HELM: Holistic Evaluation of Language Models](https://arxiv.org/abs/2211.09110)

The next chapter uses frozen, independently produced human evidence to qualify model-based judges. Human evaluation remains the reference process, but its own validity and uncertainty stay visible.
