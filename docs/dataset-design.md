# Dataset Design

The evaluation set is a model of the world you care about. Its omissions become blind spots.

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

## Guard against contamination

Separate authoring, tuning, and final holdout sets. Version them, restrict unnecessary access to holdouts, and treat unexplained score jumps as an investigation trigger.

<!-- Add your sampling strategy and dataset review checklist here. -->

