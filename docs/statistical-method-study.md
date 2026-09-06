# Statistical method study: when thirty clusters are not enough

**Question:** does our registered interval actually deliver its advertised coverage, and how often would its rule promote a genuinely worse candidate?

**Status:** executed local study, using exact enumeration of synthetic populations. No live model, production customer, or human judgment was sampled. The complete [JSON artifact](assets/statistical-method-study-v1.json) retains every possible loss count, its probability, both intervals, and both decisions—not just the headline averages. Generator: `cx_eval_lab/statistical_study.py`, run at code revision `e0df6cb`.

This is a completed method comparison, not production qualification. It deliberately tests the normal interval already used in the lab and exposes its failure. The alternative is valid only for the special binomial problem described below; it is not a replacement for arbitrary paired, clustered, or sequential inference.

## Register the experiment before interpreting the result

| Design element | Registered choice |
| --- | --- |
| Sampling unit | Independent customer; one binary outcome per customer |
| Baseline | Always succeeds |
| Candidate | Fails with fixed probability `p` |
| True contrast | Candidate minus baseline success: `−p` |
| Margin | 0.03: degradation of three percentage points |
| Confidence interval | Two-sided 95%; its lower endpoint is used for the decision |
| Promotion rule | Lower endpoint is at least −0.03 |
| Methods | Existing cluster-mean normal interval; equal-tailed exact binomial interval transformed to the contrast |
| Stopping | One fixed sample; no interim looks |
| Computation | Enumerate `k=0,…,n`, weighted by the binomial probability of each count |
| Judge perturbation | In one arm of the study, all genuine candidate failures are mislabeled as successes |

With one outcome per independent customer, each paired difference is zero or minus one. If `K` is the number of candidate losses, `K ~ Binomial(n,p)`. That reduction is what permits the binomial comparison. It would be wrong to apply it unchanged when the baseline can fail, the candidate can improve on it, or repeated outcomes share latent dependence.

The binomial interval is constructed by inverting binomial tail probabilities. Normal approximations can be inaccurate with few observed failures; the exact interval can be asymmetric and conservative. The implementation follows the tail equations documented by [NIST](https://itl.nist.gov/div898/software/dataplot/refman2/auxillar/exacbino.htm). The study's results and examples below are our own computations, not NIST deployment recommendations.

## Results: coverage and promotion are different measurements

“Coverage” is the probability that the computed interval contains the **true** contrast over repeated samples from the specified population. “False promotion” is the probability of passing when true degradation exceeds the margin. Neither is the probability that one particular candidate is safe.

| Customers | True loss rate | Normal coverage | Exact coverage | Normal false promotion | Exact false promotion |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 30 | 4% | 70.51% | 99.37% | 29.39% | 0.00% |
| 100 | 4% | 90.60% | 96.41% | 8.72% | 0.00% |
| 200 | 4% | 89.80% | 97.23% | 1.25% | 0.27% |

These are probability-weighted enumerations, not Monte Carlo estimates. There is no simulation standard error; floating-point arithmetic still has numerical error. Every reported probability can be recomputed from `count_outcomes` in the artifact. Coverage need not improve monotonically at these discrete sample sizes.

There is a cost to conservative inference. When degradation is only 1% and therefore inside the 3% margin, the exact method promotes in 40.46% of samples at `n=200`; the normal rule promotes in 67.67%. These are promotion probabilities for an acceptable population, not false-promotion rates. A method that never promotes can avoid false promotions while being operationally useless. Measure power and evidence-collection cost as well as error control.

## Kata 05: thirty ties, unjustified certainty

**Know:** a sample with no discordant pairs does not prove that the population has no discordance. Minimum sample count and method validity are separate checks.

**Predict:** the baseline and candidate both pass for all thirty customers. What interval does the existing normal rule return? Does meeting the thirty-cluster minimum fix its uncertainty estimate?

```bash
uv run python -m unittest tests.test_statistical_study -v
uv run python -m cx_eval_lab.statistical_study \
  --output artifacts/runs/statistical-method-study.json
```

Choose a new output filename on rerun. The command refuses to overwrite retained evidence. It uses no network or API key and supports at most 500 customers per binomial calculation.

??? success "Solution: derive the false promotion"
    Every cluster difference is zero, so the sample variance and standard error are zero. The teaching normal interval becomes `[0,0]`; its lower bound clears `−0.03`.

    In a population with a true loss rate of 4%, the probability of observing no losses among thirty customers is `0.96**30 = 0.2938576432`. Enumerating all other counts shows that only this zero-loss count promotes here. Thus the false-promotion probability is 29.39%, even though the count threshold is satisfied.

    With zero observed losses, the two-sided 95% exact interval has upper loss limit `1 − 0.025**(1/n)`. At thirty customers that is approximately 11.57%, so the contrast interval is approximately `[−0.1157, 0]`. Non-inferiority is not established.

**Extend:** calculate the minimum zero-loss sample size needed for this upper limit to clear 3%. The answer is 122 independent observations under this special fixed-sample model. This is not a general sample-size recommendation: the answer changes with confidence, margin, observed losses, dependence, and stopping policy.

**Interview answer:** “A minimum cluster count is a prerequisite, not method qualification. I test coverage and false promotion against known populations, especially at zero variance and sparse discordance. A narrow interval can reflect a broken approximation rather than strong evidence.”

## Kata 06: two correct averages, two different questions

**Know:** clustering changes the independence assumption; weighting defines whose outcome matters. They are distinct decisions.

**Situation:** fifteen customers each have one task that changes from failure to success. Another fifteen customers each have nine tasks that all change from success to failure.

**Predict:** what is the average change for an equally weighted customer? What is the pooled change across all tasks?

??? success "Solution: write both denominators"
    Each small customer improves by `+1`; each large customer degrades by `−1`. The equal-customer contrast is `(15×1 + 15×−1)/30 = 0`.

    Across tasks there are fifteen gains and 135 losses. The task-weighted contrast is `(15−135)/150 = −0.8`.

    `unequal_cluster_example()` executes both calculations through the current paired-comparison code. Its `point_difference` is equal-customer weighted, while its reported baseline and candidate rates are pooled over tasks. Do not subtract those rates and assume you have reconstructed the registered contrast.

**Extend:** decide which estimand fits a service commitment to customers and which fits a task-volume capacity decision. Document the choice before looking at the winning result. A future task-weighted interval must account for clustered sampling; relabeling the equal-customer interval is not a fix.

**Interview answer:** “I specify both the independent sampling unit and the target weighting. A customer-average improvement and a task-average improvement can disagree without arithmetic error. The report must expose the estimand instead of hiding it behind an overall success rate.”

## Kata 07: more data, confidently wrong labels

**Know:** an interval covers the population parameter of the observations fed to it. It cannot discover truth systematically erased by the grader.

**Situation:** the candidate truly loses on 10% of customers. A broken judge marks every loss successful. Evaluate two hundred independent customers using both methods.

**Predict:** does switching to an exact interval solve the problem? Does increasing sample size help?

??? success "Solution: separate observed and true populations"
    The observed loss probability is `p × (1−hidden_loss_probability)`. Here it is zero, although the true loss probability is 10%.

    Both methods have 0% coverage of the true contrast and a 100% false-promotion probability in this deliberately extreme perturbation. Even the exact interval now has an upper observed-loss limit near 1.83%, below the 3% margin. It is behaving appropriately for the observed labels and misleadingly for the real outcome.

    Independent executable verification or reviewed human labels must expose the missing failures. Calibration uncertainty, false passes by slice, and abstentions belong in the evidence packet. Simply collecting more labels from the same broken judge strengthens the wrong conclusion.

**Extend:** set `hidden_loss_probability` to 0.5, then 0.8, and inspect coverage of the true contrast versus the observed-label contrast. In a real study those error rates must be estimated with uncertainty; this generator knows them by construction.

**Interview answer:** “Sampling uncertainty is not measurement validity. I qualify the grader separately and propagate calibration uncertainty where justified. A statistically precise estimate of biased labels cannot authorize deployment.”

## Adopt, adapt, reject—and what remains unproven

- **Adopt:** executable qualification studies with retained count-level evidence; report coverage, promotion, power, estimand, and label assumptions.
- **Adapt:** exact binomial inference only for this one-directional, independent binary-loss design. The function is not registered as a general release method.
- **Reject:** treating thirty clusters, zero observed failures, or a passing synthetic comparison as deployment qualification. The existing normal method remains `lab_only` and is retained as the inspected teaching counterexample.

This study does not qualify unequal-cluster intervals, general paired outcomes, sequential peeking, rare-event importance sampling, or noisy-label correction. Those need their own experiments. It also does not show that a statistical pass overcomes authorization violations, missing semantic qualification, canary guardrails, or operational rollback requirements. See the [delivery map](primer-delivery-map.md) for the remaining implementation work.
