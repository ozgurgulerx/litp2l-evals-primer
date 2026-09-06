# Sequential decisions: ten looks are not one test

A candidate sits exactly at the registered unacceptable loss boundary. Testing once at the final sample size falsely promotes it in **3.54%** of the constructed experiments. Applying the same nominal 5% test at ten cumulative checkpoints and promoting on the first pass raises that probability to **11.08%**.

Those numbers are computed by the executable study, not sampled model results. The [retained evidence](assets/sequential-study-v1.json) enumerates first-crossing probabilities, decision boundaries and remaining probability mass. There is no Monte Carlo sampling error; arithmetic still uses floating-point approximations.

## Register the claim before choosing a method

This deliberately narrow experiment assumes a baseline that always succeeds. Each independent customer contributes one candidate-loss indicator, \(X_i\in\{0,1\}\), with constant probability \(p\). The target is evidence that the loss probability is **strictly below 3%**:

\[
H_0:p\ge p_0=0.03,\qquad H_1:p<p_0.
\]

Equality belongs to the null in this lab. A promotion at \(p=0.03\) therefore counts as false promotion. This convention is explicit; do not silently substitute it for the inclusive interval decision used in the earlier non-inferiority exercise. Boundary conventions and the claim being tested belong in the registered policy.

The maximum sample size is 500. Decisions are inspected at 50, 100, …, 500 customers. The experiment fixes \(\alpha=0.05\) and, for the likelihood-ratio method, a design alternative \(p_1=0.01\). That alternative is a test-design choice, not a known fact about the candidate.

| Method | Rule | False promotion at true loss 3% | Promotion at true loss 1% | Expected observations at true loss 1% |
| --- | --- | ---: | ---: | ---: |
| Fixed final | One exact lower-tail binomial test at 500 | 3.54% | 93.29% | 500.00 |
| Repeated fixed | Same 5% fixed-sample test at every look; stop on first pass | 11.08% | 95.73% | 234.12 |
| Bonferroni | Ten registered tests, each at 0.5% | 0.85% | 66.72% | 390.29 |
| Likelihood ratio | Stop when accumulated evidence reaches 20 | 2.40% | 81.02% | 335.68 |

Expected observations include experiments that reach 500 without promotion. The repeated-fixed method's attractive power and speed do not come with the advertised overall 5% false-promotion guarantee. None of the methods must use exactly 5% of the allowance: discrete outcomes, the horizon and the look schedule can make the achieved error lower.

## Kata 28: count first crossings, not marginal passes

**Know:** cumulative looks share data. Adding their marginal pass probabilities double-counts paths; treating ten correlated looks as one fixed test ignores extra chances to stop.

**Task:** reproduce the table. Then inspect `first_crossings` for the repeated-fixed method. Why do the probabilities refer to the first promotion, not every checkpoint at which a path would pass?

```bash
uv run python -m cx_eval_lab.sequential_study \
  --output /tmp/primer-sequential-my-first-run.json
uv run python -m unittest tests.test_sequential_study -v
```

Use a fresh output path for another run. No model or external service is called.

??? success "Solution: make promotion an absorbing state"
    The implementation tracks probability mass at each cumulative loss count among paths that have not promoted. At the next observation, mass splits between a loss and a non-loss. At a decision checkpoint, promoting mass is recorded and removed before the next step. It can never be promoted twice.

    For each method, first-promotion mass plus never-promoted mass sums to one. Expected stopping cost is the sum of each first-crossing mass times its sample count, plus the final horizon times the remaining mass.

    `test_dynamic_enumeration_matches_all_binary_paths` independently enumerates all 64 binary paths of a six-observation experiment. It checks each first-crossing mass, total promotion probability and expected stopping time against the dynamic calculation. This is stronger than testing only whether a final percentage lies between zero and one.

**Extend:** evaluate a different pre-registered look schedule. Bonferroni's per-look threshold must reflect the number of allowed tests. Adding looks after inspecting outcomes is not the registered fixed-schedule procedure.

**Interview answer:** “I evaluate the probability of ever making the release decision under the null, not just the error rate at one checkpoint. Cumulative windows are dependent, so I account for stopping paths or use a method with valid time-uniform control.”

## Kata 29: build one valid sequential evidence process

At sample count \(n\), let \(k=\sum_i X_i\). The worked likelihood ratio is

\[
E_n=\left(\frac{p_1}{p_0}\right)^k
    \left(\frac{1-p_1}{1-p_0}\right)^{n-k},\qquad E_0=1.
\]

**Task:** calculate \(E_{150}\) for zero observed losses. Does it cross \(1/\alpha=20\)? What does that crossing mean—and what does it not mean?

??? success "Solution: evidence against a registered null, not a posterior probability"
    With \(p_0=0.03\), \(p_1=0.01\), and no losses, \(E_{150}=(0.99/0.97)^{150}\approx21.356\). It crosses the threshold at that scheduled look.

    It does not mean a 95% probability that the candidate is safe, a 21-times improvement in task performance, or permission to deploy. It is accumulated likelihood evidence for this specified Bernoulli comparison.

    For our constructed model, the expected one-step multiplier under an iid null loss probability \(p\) is

    \[
    p\frac{p_1}{p_0}+(1-p)\frac{1-p_1}{1-p_0}
    =1+\frac{(p-p_0)(p_1-p_0)}{p_0(1-p_0)}\le1.
    \]

    Thus the nonnegative process has no upward conditional drift under the null. The code works in log space and compares `log_evidence` with `-log(alpha)`; it need not form a huge likelihood ratio or overflow `1/alpha`.

The time-uniform guarantee uses Ville's inequality: a nonnegative supermartingale starting at one crosses \(1/\alpha\) with probability at most \(\alpha\). Howard and colleagues develop this principle and its relation to likelihood-ratio testing. The equation above is the derivation for this lab's specific Bernoulli model, not an implementation of their full framework. [Time-uniform Chernoff bounds, Sections 2.3 and 4.6](https://arxiv.org/html/1808.03204v8)

**Extend:** the evidence process can support inspection at arbitrary stopping times under its assumptions; this experiment uses the same ten looks for comparability. Change `looks` to every integer from 1 through 500 and recompute. Do not retune \(p_1\) using the completed test data and assume the original guarantee still applies. Adaptive or mixture constructions require their own valid design.

**Interview answer:** “I can monitor evidence with an anytime-valid method, but its null, sampling model and initialization must remain valid. An evidence threshold is not a posterior safety probability or a substitute for policy and operational controls.”

## Kata 30: optional-stopping validity does not repair bad data

The study includes two executed counterexamples:

- **Hidden failures:** true loss is 10%, but every loss is mislabeled as success. The likelihood-ratio method falsely promotes with probability **100%** by the horizon.
- **Perfect dependence:** one Bernoulli outcome with loss probability 3% is copied into all 500 rows. The method falsely promotes with probability **97%**, despite each row having the nominal marginal loss probability.

**Task:** explain why neither result contradicts the sequential guarantee.

??? success "Solution: identify which assumption no longer holds"
    In the hidden-failure case, the test sees an observed loss probability of zero. Its inference concerns that corrupted label process, not the underlying truth. Optional-stopping control does not calibrate a judge or recover unobserved failures.

    In the dependent case, there is one independent unit, not 500. With probability 97%, every row is zero and the process eventually crosses. After observing the first zero, the remaining outcomes are known to be zero; the conditional null requirement behind the multiplier argument no longer holds. Matching marginal frequencies is insufficient.

    Some sequential methods support structured dependence under appropriate conditional assumptions. This counterexample does not show that all dependence invalidates all sequential inference. It shows that copying one unit into hundreds of supposedly independent observations invalidates this experiment's model.

**Extend:** combine customer/session clustering with judge errors. Decide what the independent unit is, how uncertainty in the reference labels enters the analysis, and which assumptions would permit any claimed bound. The earlier [statistical method study](statistical-method-study.md) adds unequal-cluster estimands and sparse-failure interval counterexamples; it does not qualify every clustered sequential method.

**Interview answer:** “Anytime validity handles a specified stopping problem. It does not turn repeated tasks from one customer into independent data, repair biased labels, or justify transfer to an untested population.”

## Kata 31: restarting a test is not free

Suppose twenty **independent**, newly sampled release experiments each have the likelihood-ratio method's 2.3963% false-promotion probability from this study. The team ships if any experiment promotes.

**Predict:** is the family-level risk still below 5%?

??? success "Solution: keep the campaign-level error budget"
    Under the stated independence assumption, the probability of at least one false promotion is

    \[
    1-(1-0.023962935647)^{20}\approx0.3844.
    \]

    That is about 38.44%, not 5%. Optional-stopping validity inside one experiment does not provide a free fresh allowance for every candidate, slice or restarted campaign.

    One conservative approach is to allocate a total family error budget across registered experiments, with the allocated levels summing to the family limit. This controls the union of valid constituent tests without requiring independence. It still requires each constituent test to satisfy its own assumptions. More efficient multiple-testing or online-error-control methods need their own design and validation.

    If the team reuses the same sealed data to tune candidates, the independent-experiment formula above no longer describes the process. Do not present 38.44% as its exact risk. Record holdout exposure, preserve untouched acceptance evidence and separate candidate development from evaluation. Restarting an evidence process over optimized-on data does not restore independence.

**Interview answer:** “I budget error across the decisions the organization will actually make—looks, candidates, slices and campaigns. A valid test inside one run does not automatically validate the release-selection procedure around it.”

## What this implementation qualifies

The code and exhaustive small-path tests establish the computation for the registered synthetic Bernoulli experiment. The likelihood-ratio argument supports a mathematical time-uniform bound under its stated assumptions; the finite-horizon enumeration illustrates achieved risk and power. It does not establish live-model capability, general paired-outcome statistics, clustered customer traffic, delayed-label collection, noisy-judge correction or deployment authority.

A confidence sequence is a sequence of intervals with simultaneous coverage over time, not just one repeatedly inspected fixed interval. This lab implements a fixed-null test, not a general confidence-sequence library. [Howard et al., Time-uniform confidence sequences](https://arxiv.org/abs/1810.08240)

The [Exposure Control Lab](exposure-control-lab.md) still uses visibly illustrative point thresholds. Connecting qualified statistical evidence to that controller requires registered populations, source and grader binding, a valid observation process and an authorized deployment integration. This study explains and tests part of that reasoning; it does not silently upgrade existing `lab_only` receipts.
