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
