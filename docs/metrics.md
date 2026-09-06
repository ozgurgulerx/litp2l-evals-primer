# Metrics

A useful score preserves the distinctions needed for a decision. Aggregate numbers are summaries, not explanations. This chapter owns both metric interpretation and the runner that turns a versioned specification into repeatable evidence.

## Match the measurement to the claim

=== "Deterministic"

    Use exact checks for properties such as schema validity, tool selection, citations, or task completion when the rule is genuinely crisp.

=== "Reference-based"

    Compare against known outputs when legitimate variation is limited and the reference is authoritative.

=== "Rubric-based"

    Use structured human or model judgment for qualities such as completeness, groundedness, or tone.

## Worst value-weighted slice

Report performance by risk, capability, language, customer segment, and other meaningful cohorts. Put the worst value-weighted slice beside the overall result: a small cohort may carry most of the revenue, harm, or operational risk, and an average can conceal its regression.

Every slice must have a reason to exist, an owner, and a denominator. Pre-register gating slices; treat newly discovered slices as exploratory until they have enough evidence for a decision.

## Report n and uncertainty

Never publish a rate without its sample size **n** and a confidence interval. A five-point movement on forty cases may be ordinary sampling noise; the correct action can be “watch and gather evidence” rather than “block” or “ship.” Use paired candidate-versus-baseline outcomes when the same cases are available.

An interval is useful only when its method fits the sampling and measurement process. The [executed method study and Katas 05–07](statistical-method-study.md) show three concrete failures: zero observed variance hiding rare losses, a customer-weighted contrast disagreeing with pooled task rates, and exact inference becoming confidently wrong when judge labels hide real failures. Report these assumptions alongside the interval; `n ≥ 30` does not validate them.

## Measure repeatability

One run is not a verdict for a nondeterministic system. Repeat trials at the blast radius the application demands and report the distribution, not only the best attempt.

- **pass@k** asks whether at least one of *k* attempts succeeds. It measures capability.
- **pass^k** asks whether all *k* attempts succeed. It measures reliability.

Pin and record model, prompt, judge, retrieval index, tool environment, and runtime versions. Temperature zero removes only one source of variance; judge and environment variance remain.

## Make the runner produce evidence

The evaluation runner should execute the same case manifest against the baseline and candidate, preserve per-case results, calculate slices and intervals, record dependency versions, and emit a decision-ready report. The runner implements the golden set as an executable specification; it must not collapse evidence into one scalar before the release policy sees it.

## Pair quality with operating constraints

Track cost and latency alongside task quality. A candidate that improves quality but violates the serving envelope is not an unconditional win.

## Define the estimand before the metric

An **estimand** is the quantity the study intends to estimate. Examples:

- probability that an eligible refund is resolved in one session on August traffic;
- change in Turkish groundedness from baseline to candidate on the same cases;
- rate of unauthorized transactions under a named attack suite;
- p95 end-to-end latency at a fixed concurrency and tool profile;
- cost per verified successful outcome.

The metric is the calculation. The estimand states the population, outcome, comparison, and conditions that give the calculation meaning.

```yaml
estimand:
  population: August 2026 chat refund requests under policy-v3
  outcome: verified resolution without repeat contact in seven days
  comparison: candidate-rc4 minus shipping-v3
  assignment: paired replay on identical synthetic world states
  unit: case
  repeats_per_case: 3
```

## Match scales to claims

| Scale | Example | Safe summary |
| --- | --- | --- |
| Binary | invariant passed | rate, numerator/denominator, interval |
| Count | tool calls | distribution, median, tail, conditional mean |
| Continuous | latency | quantiles and distribution under named load |
| Ordinal | rubric level 0–3 | level distribution and threshold rate |
| Pairwise | A, B, tie, both bad | win/tie/both-bad rates with order controls |
| Ranking | ordered candidates | rank model plus uncertainty and judge design |

Do not turn an ordinal scale into precise arithmetic without defending the distance between levels.

## Classification metrics

For a binary grader:

|  | Human/reference positive | Human/reference negative |
| --- | ---: | ---: |
| Grader positive | true positive (TP) | false positive (FP) |
| Grader negative | false negative (FN) | true negative (TN) |

\[
\text{Precision}=\frac{TP}{TP+FP},\quad
\text{Recall}=\frac{TP}{TP+FN},\quad
F_1=\frac{2PR}{P+R}
\]

The positive class must be named. For a release-blocking failure detector, a “positive” may mean unsafe. A false negative then becomes a **false pass**, which can be much more costly than a false alert.

Accuracy can be misleading under imbalance. A grader that predicts “safe” for all 990 safe and 10 unsafe items is 99% accurate and detects none of the unsafe cases.

## Reference-based text metrics

### Exact match

Use when the output contract is genuinely exact: an ID, normalized option, schema, or executable result. Do not use it for open-ended explanations with many valid phrasings.

### BLEU and ROUGE

BLEU emphasizes n-gram precision and was designed for corpus-level machine-translation evaluation. ROUGE variants emphasize overlap useful in summarization settings. Both can be useful diagnostics when overlap is part of the task, but neither proves factuality, usefulness, or policy compliance.

### Embedding and learned metrics

BERTScore-like semantic similarity tolerates paraphrase but can reward semantically related wrong answers. Validate any learned metric on task-specific human labels and important counterexamples.

### Executable metrics

When possible, run the result: execute code tests, compare database state, validate JSON, check a citation span, or inspect a transaction ledger. Executable evidence is often stronger than text similarity, though the tests and environment still require validation.

## Task and retrieval metrics

Choose task metrics from the behavior:

- exact task completion or final-state success;
- retrieval recall@k, precision@k, MRR, or nDCG;
- atomic-claim support and contradiction;
- citation entailment and completeness;
- tool argument correctness;
- policy-invariant violation count;
- multi-turn resolution and repeat-contact rate;
- human or qualified-judge rubric outcomes.

An end-to-end task metric and component diagnostics answer different questions. Retain both.

## pass@k and pass^k

If independent trials each succeed with probability \(p\), then:

\[
\text{pass@k}=1-(1-p)^k
\]

\[
\text{pass}^k=p^k
\]

At \(p=0.8\), `pass@3 = 0.992`, while `pass^3 = 0.512`. The same agent can look highly capable when retries are allowed and unreliable when every run must succeed.

The independence assumption is often imperfect: trials share cases, prompts, tools, and infrastructure. Report the empirical distribution and clustered design rather than using the formulas blindly.

## Units and dependence

Possible units include:

- case;
- stochastic trial within case;
- conversation;
- customer;
- document;
- claim;
- tool call;
- time window.

Ten trials on each of ten cases produce 100 executions, not 100 independent product situations. Analyze within-case pairing and cluster uncertainty at the level that was sampled independently.

Likewise, 20 claims from one answer share context and generation. Treating them as 20 independent reports overstates precision.

## Confidence intervals

A point estimate does not express sampling uncertainty. For proportions, use a defensible binomial interval such as Wilson or an exact method when appropriate. For paired candidate-baseline differences, resample cases as pairs.

### Bite-sized paired bootstrap

```python
from random import Random


def paired_bootstrap(baseline, candidate, draws=10_000, seed=17):
    rng = Random(seed)
    deltas = [new - old for old, new in zip(baseline, candidate, strict=True)]
    estimates = []
    for _ in range(draws):
        sample = [deltas[rng.randrange(len(deltas))] for _ in deltas]
        estimates.append(sum(sample) / len(sample))
    estimates.sort()
    return estimates[int(.025 * draws)], estimates[int(.975 * draws)]
```

The resampling unit must be the independent case or cluster. Bootstrapping baseline and candidate separately discards the pairing and usually wastes information.

For paired binary outcomes, the discordant cases carry the change signal. McNemar-style reasoning or a paired bootstrap can be appropriate; choose and document the method before reading the desired result.

## Power and minimum detectable effect

Before running an expensive evaluation, ask:

- What improvement would change the release decision?
- What baseline rate and variance are plausible?
- How many independent cases are available?
- How many repeats are needed for within-case variance?
- Which slices need their own decision?
- What false-positive and false-negative risks are acceptable?

A suite too small to detect the minimum meaningful effect should not be used to make a superiority claim. It may still enforce hard deterministic invariants or discover failures.

Avoid post-hoc power as a substitute for reporting estimates and intervals. The design question belongs before data collection.

## Non-inferiority, superiority, and equivalence

These are different claims:

- **Non-inferiority:** the candidate is not worse than baseline by more than margin \(\delta\).
- **Superiority:** the candidate improves the registered outcome beyond uncertainty and the meaningful threshold.
- **Equivalence:** differences in both directions remain inside a pre-registered equivalence region.

The margin comes from product consequences, historical variation, and stakeholder tolerance—not from whichever value makes the candidate pass.

### Inconclusive is a valid state

If evidence does not support either release or rejection, say **Inconclusive**. Options include gathering more independent cases, increasing repeats for unstable cases, narrowing the release claim, or holding exposure at a safer stage.

Do not convert “failed to detect a difference” into “the systems are equal.”

## Multiple comparisons

Large dashboards create many chances for an apparently significant movement. Separate:

- pre-registered gating metrics and slices;
- secondary diagnostics;
- exploratory discoveries.

Use appropriate multiplicity control when making several confirmatory claims. For exploratory slices, publish them as hypotheses for validation rather than silently promoting the most extreme result to a gate.

## Rare critical failures

When zero failures are observed in \(n\) independent trials, the observed rate is zero but the true rate is not proven zero. A rough 95% upper bound is approximately \(3/n\) under simple binomial assumptions.

Zero failures in 100 trials therefore remains compatible with a rate near 3%. For high-consequence events, combine:

- deterministic prevention;
- risk-enriched and adversarial tests;
- larger exposure evidence;
- production monitoring;
- rapid rollback;
- explicit limits on the claim.

## Calibration and proper scores

When a system emits probabilities, evaluate both discrimination and calibration. A calibrated 0.8 prediction should be correct about 80% of the time for comparable events.

- **Brier score** is mean squared error of probability predictions.
- **Negative log-likelihood** strongly penalizes confident wrong predictions.
- **Expected calibration error** summarizes binned reliability gaps but depends on binning and can hide local failures.
- **Reliability diagrams** show predicted confidence against observed frequency.

These probability-calibration metrics are different from qualifying an LLM judge against human labels. Chapter 5 covers judge calibration and selective abstention.

### Worked calibration example

Use ten synthetic automation decisions whose `confidence` is the probability that the proposed resolution is correct:

| ID | Confidence | Correct? | Squared error |
| --- | ---: | ---: | ---: |
| P01 | 0.95 | 1 | 0.0025 |
| P02 | 0.90 | 1 | 0.0100 |
| P03 | 0.85 | 0 | 0.7225 |
| P04 | 0.80 | 1 | 0.0400 |
| P05 | 0.75 | 1 | 0.0625 |
| P06 | 0.65 | 0 | 0.4225 |
| P07 | 0.60 | 1 | 0.1600 |
| P08 | 0.55 | 0 | 0.3025 |
| P09 | 0.40 | 0 | 0.1600 |
| P10 | 0.30 | 1 | 0.4900 |

The Brier score is the mean squared probability error:

\[
\text{Brier}=\frac{1}{n}\sum_{i=1}^{n}(p_i-y_i)^2
             =\frac{2.3725}{10}=0.23725
\]

For log loss, clip probabilities only by a predeclared numerical rule and compute:

\[
\text{NLL}=-\frac{1}{n}\sum_{i=1}^{n}
\left[y_i\log p_i+(1-y_i)\log(1-p_i)\right]
=0.663855
\]

Using fixed bins `[0.00, 0.60)`, `[0.60, 0.80)`, and `[0.80, 1.00]`:

| Confidence bin | Support | Mean confidence | Empirical accuracy | Absolute gap | Weighted ECE contribution |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0.00–0.59 | 3 | 0.416667 | 0.333333 | 0.083333 | 0.025 |
| 0.60–0.79 | 3 | 0.666667 | 0.666667 | 0.000000 | 0.000 |
| 0.80–1.00 | 4 | 0.875000 | 0.750000 | 0.125000 | 0.050 |

Therefore **Brier = 0.23725**, **NLL = 0.663855**, and **ECE = 0.075** under this exact binning rule. ECE would change under different bins; that sensitivity is why the table and reliability diagram matter more than the headline alone.

### Thresholds turn calibration into an action

Suppose the system automates only when confidence meets a threshold and sends the rest to review:

| Automation threshold | Automated / 10 | Coverage | Wrong among automated | Selective risk |
| --- | ---: | ---: | ---: | ---: |
| 0.60 | 7 | 70% | 2 | 28.6% |
| 0.80 | 4 | 40% | 1 | 25.0% |
| 0.90 | 2 | 20% | 0 | 0% observed |

Raising the threshold lowers coverage and the observed error count here, but ten cases cannot establish a safe real-world error bound. Report support and uncertainty by action-critical slice; select the threshold from failure cost and review capacity; then validate it on an independent set. Recalibration can improve probability meaning without changing ranking, while a better discriminating model may improve risk–coverage even if its raw probabilities need recalibration.

The inspectable companion is `evals/cx-support/examples/probability-calibration-v1.json`. Its test recomputes Brier, NLL, ECE, and the threshold order from the row-level synthetic data.

### Calibration failure modes

| Failure | Why it matters | Repair |
| --- | --- | --- |
| One global reliability curve | A dominant easy slice hides overconfidence on a risky slice | Plot and score protected/risk slices with support |
| ECE without bin definition | The result cannot be reproduced and can move with binning | Freeze bins or estimator and publish bin rows |
| Confidence taken from prose | “I am 90% sure” may not be a stable probability interface | Define and validate the confidence extraction contract |
| Threshold tuned on the calibration report | Risk–coverage is optimistically biased | Choose on development/calibration data; confirm on held-out evidence |
| Recalibration called capability improvement | Probabilities improve while decisions do not | Report discrimination, calibration, and action outcomes separately |

## Latency and cost

Report end-to-end and critical component latency, especially p50, p95, and p99 under a named load. Percentiles are not generally additive: retrieval p95 plus generation p95 does not necessarily equal end-to-end p95 because the slow requests may differ.

Cost per successful task should include:

- unsuccessful attempts;
- retries;
- model and judge tokens;
- retrieval and tool calls;
- simulator and human review when part of the experiment;
- infrastructure costs included by policy.

\[
\text{cost per success} = \frac{\text{total measured cost}}{\text{verified successful outcomes}}
\]

If there are no successes, the value is undefined or infinite—not zero.

## Pareto decisions

A candidate dominates another when it is no worse on all registered objectives and better on at least one. Otherwise the systems occupy a trade-off frontier requiring a declared product objective.

Examples:

- cheaper with non-inferior quality and unchanged safety;
- faster with a small quality loss inside an approved margin;
- higher quality but outside the cost budget;
- better average quality with a protected-slice regression.

Never let a weighted aggregate compensate for a hard invariant.

## Worked example: candidate versus baseline

The same 120 synthetic cases are replayed against both systems.

| Measure | Baseline | Candidate | Interpretation |
| --- | ---: | ---: | --- |
| Verified success | 100/120 | 104/120 | Point estimate +3.3 percentage points |
| Paired 95% interval | — | −1.2 to +7.6 points | Superiority not established |
| Turkish success | 18/24 | 19/24 | Too little evidence for a strong slice claim |
| Unauthorized transactions | 0/120 | 1/120 | Hard-invariant failure |
| p95 latency | 1,850 ms | 1,710 ms | Faster under the registered synthetic load |
| Cost per success | $0.41 | $0.39 | Slightly cheaper in the synthetic profile |

The candidate is faster and cheaper and has a higher task-success point estimate. It still blocks because of the unauthorized transaction. If that violation were absent, a release sold as a quality improvement would remain inconclusive; a release sold as a cost reduction might proceed to a controlled canary if non-inferiority and all other gates passed.

## Artifact: decision-ready metric report

```yaml
experiment: cx-rc4-vs-shipping-v3
estimand: paired change in verified task success on refund-acceptance-v2
unit: case
cases: 120
repeats_per_case: 1
results:
  baseline_success: {numerator: 100, denominator: 120}
  candidate_success: {numerator: 104, denominator: 120}
  paired_delta: 0.033
  paired_ci_95: [-0.012, 0.076]
  unauthorized_actions: 1
  p95_latency_ms: 1710
  cost_per_success_usd: 0.39
slices:
  language_tr: {baseline: "18/24", candidate: "19/24"}
decision:
  quality_claim: inconclusive
  release: block
  blocking_rule: unauthorized_actions_must_equal_zero
```

The figures are synthetic and teach the interpretation contract.

## Failure modes

| Failure mode | Misleading result | Repair |
| --- | --- | --- |
| Rate without denominator | 90% appears equally strong at n=10 and n=10,000 | Publish numerator, denominator, and interval |
| Independent comparison of paired cases | Variance is inflated and case difficulty ignored | Preserve case-level pairs |
| Trials treated as independent cases | Precision is overstated | Cluster at the sampled case/customer level |
| No registered estimand | Metric changes with the argument | Freeze population, outcome, contrast, and unit |
| Mean ordinal score | Label distribution and severe failures disappear | Show levels and threshold counts |
| Accuracy on imbalanced grader data | Unsafe class is never detected | Report class-conditional errors |
| p95 components added | End-to-end tail is misstated | Measure end-to-end critical paths directly |
| Zero observed failures means zero risk | Small sample looks certain | Bound the claim and add prevention/monitoring |
| Many slices searched | Random extreme becomes a “finding” | Separate confirmatory and exploratory analysis |

## Exercise: choose the decision

A candidate improves overall success from 82% to 86% on 50 cases. The paired interval is −2 to +10 points. It reduces cost by 25%, keeps all hard invariants at zero observed violations, and meets every protected-slice floor. The registered release objective is cost reduction with a 3-point non-inferiority margin.

What can and cannot be claimed?

??? success "Answer"
    The evidence does not establish a quality improvement because the interval includes zero, so superiority is not established. For the cost-reduction objective, test the non-inferiority contrast against the pre-registered 3-point margin. The lower bound of −2 points is above the registered −3-point margin, so non-inferiority is established under the inclusive boundary rule, assuming this is the correctly constructed interval for the registered estimand. The 25% cost reduction is a supported point estimate under the measured profile, while “zero observed violations in 50 cases” is not proof of zero risk.

The executable companion is `assess_non_inferiority` in `cx_eval_lab/gate.py`. Its regression test fixes the boundary convention: a lower bound equal to `−margin` qualifies; a lower bound below it does not. This helper interprets a supplied interval—it does not estimate one from point rates.

## Executed paired slice comparison

The candidate passes six of eight trials; the baseline passes two. Yet the candidate breaks both repetitions of the one required-slice case. Open the [retained packet and report](assets/paired-slices-v1.json) before calling the candidate an improvement.

This study runs four invented refund cases through both deterministic controls, twice each: **16 agent executions, eight pairs, four cases and three customer clusters**. The tools execute the reference refund workflow in isolated mock state. The baseline deliberately gives an incorrect outcome enum on ordinary requests; the candidate moves that error to requests containing “special request.” Neither control consults the evaluator's expected answer. This is a visible-request-controlled bug, not measured model behavior or a demographic disparity study.

| Population | Cases / pairs / customers | Baseline pass | Candidate pass | Trial-weighted change |
| --- | --- | --- | --- | --- |
| Overall | 4 / 8 / 3 | 2/8 | 6/8 | +50 percentage points |
| `risk:general` — exploratory | 3 / 6 / 2 | 0/6 | 6/6 | +100 points |
| `risk:protected` — required | 1 / 2 / 1 | 2/2 | 0/2 | −100 points |

The report also includes an exploratory `all` slice identical to the overall population. Do not add these slice denominators: membership overlaps. The word *protected* is an invented policy label here, not a claim about a protected characteristic.

### Kata 62: an overall improvement conceals a regression

**Predict:** which pairs improved, which regressed, and why is the equal-customer-weighted difference not +50 points? What does the required slice justify concluding?

Run from the repository root after installing the locked environment:

```bash
uv run python -m unittest tests.test_paired_slices tests.test_paired_slices_artifact -v
uv run python -m cx_eval_lab.paired_slices --output /tmp/paired-slices-study.json
```

Choose a new output path if that file already exists; the CLI refuses to overwrite evidence. Latency and cost in this packet come from the **invented default measurement profile**. They are not measurements of the executed tools or estimates of model operating cost. The manifest deliberately says `working-tree-unpinned`; this packet is not a committed-source attestation.

Inspect the retained evidence without trusting its report's pass flags:

```python
import json
from pathlib import Path
from cx_eval_lab.paired_slices import derive_slice_report

study = json.loads(Path("docs/assets/paired-slices-v1.json").read_text())
report = derive_slice_report(study["packet"], ("risk:protected",))
assert report == study["report"]
assert report["overall"]["pair_count"] == 8
assert report["overall"]["customer_count"] == 3
assert len(report["overall"]["changes"]["fixed"]) == 6
assert len(report["overall"]["changes"]["regressed"]) == 2
for pair in report["pairs"]:
    print(pair["case_id"], pair["trial_index"], pair["outcome"],
          pair["candidate"]["failed_checks"])
```

`derive_slice_report` replays complete legacy trial artifacts, checks the manifest and pair joins, and requires the full case—including customer and slice membership—to agree across arms and repetitions. It also checks each retained agent input against its case and the reconstructed full case list against the manifest's dataset hash, preserving the baseline's repetition-zero execution order. This API requires a **canonical case-list hash**, not a raw dataset-file byte hash; missing or incompatible registration is rejected. It rejects changed grades inconsistent with replay. A caller's accepted semantic calibration hashes are separate inputs; a receipt's presence alone does not establish qualification. This API supports `refund-trial-v1`, not the newer native multi-order packet schema.

??? success "Solution: inspect changes before interpreting the average"
    `case-0`, `case-1` and `case-2` each contribute two fixed pairs. `case-3` contributes two regressed pairs. There are no unchanged pairs. On the failing arm the ledger contains the refund, but the enum says it did not happen; `claimed_outcome_matches_state` fails. The method therefore detects a concrete explanation/structure inconsistency rather than an absent transaction.

    The pooled difference is `(6 − 2) / 8 = 0.50`. But `case-0` and `case-1` share a customer. Their four pairs contribute one customer's mean change, +1. The remaining customers contribute +1 and −1. Equal customer weighting gives `(1 + 1 − 1) / 3 = 1/3`, or approximately +33.3 points. These are different estimands, not competing calculations of the same estimand. Choose the target weighting before seeing results; neither is automatically the right population quantity.

    The observed required-slice regression is real **within this constructed execution**. Its two repetitions do not create two independent customers. The slice has one customer, so the report supplies no interval. Overall there are only three clusters against the manifest's minimum of 30, so its teaching comparison is inconclusive too. The diagnostic returns `hold`, with `deployment_authorized=False`.

    This diagnostic is not the full release gate: `hold` does not excuse known deterministic failures. A release policy that forbids the demonstrated claim/state contradiction must still block it. Likewise, a missing interval does not make the observed regression disappear. Preserve the failed pairs for diagnosis while withholding an unsupported population claim.

**Interview answer criteria:** distinguish trial, case and customer; compute both weighted differences; identify the regressed pairs; separate observed defect, population uncertainty and deployment authority. Explain why repeating the same customer cannot repair weak independent support.

### Kata 63: missing support is not zero performance

**Predict:** what should the report say if a required language slice has no cases? What changes if the candidate supplies unqualified prose on every case? Can you delete a required slice after seeing the result?

```python
from cx_eval_lab.paired_slices import derive_slice_report, run_study

missing = run_study(required_slices=("language:missing",))["report"]
row = next(r for r in missing["slices"] if r["slice"] == "language:missing")
assert row["pair_count"] == 0
assert row["baseline_rate"] is None and row["candidate_rate"] is None
assert row["status"] == "hold" and row["issues"] == ["missing_slice"]

unknown = run_study(unqualified_candidate=True)["report"]
assert len(unknown["overall"]["changes"]["unqualified"]) == 8
assert unknown["overall"]["eligible_pair_count"] == 0
assert unknown["overall"]["comparison"] is None
assert unknown["status"] == "hold"

original = run_study()
try:
    derive_slice_report(original["packet"], ())
except ValueError:
    print("Cannot silently drop the manifest-bound required slice.")
else:
    raise AssertionError("Required slice policy changed without rejection")
```

??? success "Solution: preserve unknowns and the declared population"
    An empty required slice has no numerator or denominator from which to estimate performance. Its rates are `null`, not 0% or 100%, and it holds the diagnostic. Adding an unsupported required label before executing a new study is a useful negative control; it is not evidence that an earlier experiment tested that population.

    In the unknown-prose control, the candidate returns a message outside the trusted templates without a qualifying semantic receipt. All eight pairs are labelled `unqualified`, not eight proven behavioral regressions. The report preserves each arm's failed checks: a known structural defect may coexist with an unknown semantic judgment. Nothing is relabelled as safe. Joint-quality inference is withheld rather than silently dropping these pairs.

    When only some pairs are qualified, displayed rates describe that subset, with its denominator. They are not missingness-adjusted estimates for the original population. Inspect whether qualification failure is associated with difficult cases, languages or the candidate itself. A lower judge budget can change which outcomes are observable without improving the agent.

    The sorted required-slice policy is hashed into the manifest before the local study runs. Passing a different list to this packet's report derivation is rejected. This establishes local content consistency, **not authenticated preregistration**: someone able to rewrite the whole packet and manifest can rewrite that declaration. Real confirmation needs independently controlled registration and source/evidence authority. Older packets with no slice-policy binding can be analysed exploratorily only, and still need the compatible full-dataset binding described above.

    Exploratory rows do not change this diagnostic's gate status. If an exploratory finding motivates a new release requirement, register a new experiment and collect appropriate evidence; do not retrospectively present a selected slice as confirmatory. Overlapping slices share observations, and the current teaching intervals do not supply joint or multiplicity-adjusted guarantees.

**Extend:** propose an untouched follow-up population for the failed slice, a method justified for its sampling design, and an independent check on semantic-label error. Explain why “collect 30 customers” is only a sample-count rule—not qualification of an interval method. Use the [statistical counterexamples](statistical-method-study.md) before assigning statistical authority.

**Evidence boundary:** the retained artifact and tests exercise actual local mock-tool executions and replay-derived slice diagnostics. The cases, controls and measurement profile are synthetic. They do not establish real customer performance, current judge validity, authenticated execution history or deployment permission. The next implementation step is the same joined diagnostic for native multi-order evidence, followed by representative, independently qualified observations.

## Verification checklist

- [ ] Every gating metric maps to a registered estimand and product claim.
- [ ] Numerators, denominators, exclusions, and uncertainty are present.
- [ ] Candidate and baseline are paired where the same cases are used.
- [ ] Repeated trials are distinguished from independent cases.
- [ ] Protected slices have owners and enough support for their authority.
- [ ] Superiority, non-inferiority, equivalence, and inconclusive are not conflated.
- [ ] Rare critical failures retain independent gate rules.
- [ ] Cost and latency use complete, reproducible measurement profiles.
- [ ] Confirmatory and exploratory comparisons are labeled.

## Primary reading

!!! note "Research-to-practice boundary: extreme-tail estimates"
    [Research-to-Practice Evidence](research-to-practice.md#rare-failure-estimation)
    examines Five-Nines/CEM importance sampling. It is a promising research
    estimator, not public proof of a production release control. Local use must
    validate generator coverage, proposal support, weight stability, known-rate
    recovery, and offline-to-live calibration.

- [HELM: Holistic Evaluation of Language Models](https://arxiv.org/abs/2211.09110)
- [On Calibration of Modern Neural Networks](https://arxiv.org/abs/1706.04599)
- [Semantic Uncertainty: Linguistic Invariances for Uncertainty Estimation in Natural Language Generation](https://arxiv.org/abs/2302.09664)
- [Lessons from the Trenches on Reproducible Evaluation of Language Models](https://arxiv.org/abs/2405.14782)
