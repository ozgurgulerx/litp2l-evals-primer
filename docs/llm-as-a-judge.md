# LLM as a Judge

Model-based graders can scale nuanced evaluation, but their output is measurement—not ground truth.

## Design the rubric first

A strong rubric describes observable evidence, separates dimensions, and defines what each score means. Avoid asking a judge to infer unstated product policy.

## Calibrate against people

Create a human-labeled calibration set, measure agreement, inspect disagreements, and revise the rubric before trusting a large run.

## Control common biases

- Randomize candidate order when comparing outputs.
- Hide irrelevant model identity and metadata.
- Test verbosity and style sensitivity.
- Require evidence or a short rationale for the assigned grade.
- Recalibrate when the judge model, prompt, or rubric changes.

!!! warning "Judge drift"
    A silent judge-model update can change the measuring instrument. Pin versions when possible and keep a stable calibration suite.

<!-- Add judge prompts, calibration results, and failure analyses here. -->

