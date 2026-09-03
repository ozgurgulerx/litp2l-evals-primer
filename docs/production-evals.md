# Production Evals

Offline evaluation helps decide what to ship. Production evaluation tells you whether the deployed system still behaves as intended.

## Connect three loops

1. **Pre-release:** compare a candidate with the current baseline on a versioned suite.
2. **Progressive delivery:** monitor guarded traffic while exposure increases.
3. **Continuous learning:** turn reviewed incidents and representative traces into new regression cases.

## Preserve traceability

For every scored sample, retain the relevant application version, model and prompt version, retrieval context, tool results, rubric version, and judge version—subject to privacy and retention policy.

## Define action thresholds

A dashboard without an owner or action is decoration. Every gate and alert needs a threshold, response, owner, and review cadence.

<!-- Add your release gates, monitoring topology, and incident loop here. -->

