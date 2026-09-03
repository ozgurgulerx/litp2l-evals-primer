# Shipping Checklist

Use this as a starting gate, then adapt it to the risk and operating context of your system.

## Evaluation contract

- [ ] The user-visible promise and prohibited behaviors are explicit.
- [ ] Each metric is tied to a release or operating decision.
- [ ] Quality, safety, latency, and cost constraints are recorded.

## Evidence

- [ ] Core, boundary, adversarial, and regression cases are represented.
- [ ] Dataset provenance and versions are traceable.
- [ ] Important cohorts are large enough to inspect separately.
- [ ] Tuning data and holdout data are separated.

## Measurement

- [ ] Rubrics describe observable evidence.
- [ ] Model-based graders are calibrated against human judgment.
- [ ] Score changes include slices and uncertainty, not only an average.
- [ ] Evaluator, prompt, and rubric versions are pinned or recorded.

## Release and operation

- [ ] The candidate is compared with the current baseline.
- [ ] Regressions have an explicit block, exception, or rollback decision.
- [ ] Production signals have owners and action thresholds.
- [ ] Reviewed production failures feed the regression suite.

<!-- Replace this checklist with your own non-negotiable shipping standard. -->

