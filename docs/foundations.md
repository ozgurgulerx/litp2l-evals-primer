# Foundations

## Why LLM applications need control systems

Large language models (LLMs) are probabilistic AI models. They are useful when written or spoken language needs to be processed or generated. They are also useful for tasks with a large solution space, where the right action or tool depends on the current context and state.

This flexibility creates two engineering requirements:

1. Put a **harness** around the model to constrain and contain its behavior. The harness owns permissions, tool access, input and output validation, execution limits, and other deterministic controls.
2. Build an **evaluation system** that continuously measures performance and gates releases through CI/CD.

The same model can produce different responses to the same prompt. One successful run therefore does not prove that the application will behave correctly in production.

## What deterministic checks can verify

Even when model outputs vary, many properties can be verified with deterministic code:

- **Exact answers and contracts:** Check expected values, schemas, required fields, formats, and numerical invariants.
- **Code and SQL:** Execute the output in a sandbox and run unit, integration, security, or performance tests against it.
- **Agent behavior:** Run the requested actions in a controlled environment, inspect the tool calls and trajectory, and verify the resulting state.
- **Structured JSON:** Validate the schema, data types, ranges, relationships, and business rules.
- **Facts and citations:** Check claims against trusted evidence and verify citation existence, provenance, and support. Some support and entailment decisions may still require semantic judgment.

Use deterministic graders wherever a hard contract exists. They are cheaper, faster, more reproducible, and easier to debug than subjective graders.

## When semantic judgment is required

Free-form text is different. Code can still check structural properties such as format, required sections, prohibited content, citation presence, or length. However, it usually cannot fully determine an output's semantic quality.

Qualities such as relevance, coherence, completeness, tone, helpfulness, and faithfulness require a clear rubric applied by human reviewers or a calibrated LLM judge. An LLM judge is also a probabilistic model, so it must be evaluated against trusted human labels, versioned, monitored for bias and variance, and recalibrated when it changes.

This gives us a grading hierarchy:

1. Use deterministic checks wherever possible.
2. Use human or model judgment only where semantic evaluation is genuinely required.
3. Combine both when an output has structural, behavioral, and semantic requirements.

## Evals as decision contracts

An eval is not just a score. It is a **decision contract** that defines acceptable performance for a specific use case: the test cases, graders, metrics, critical slices, and required thresholds.

That contract connects evaluation to the release process:

- **Pull request:** Run fast deterministic checks on every change.
- **Pre-release:** Run broader model-graded, human-calibrated, and end-to-end suites.
- **Production:** Use canaries, monitoring, sampled traces, and business outcomes to verify that offline results transfer to real traffic.

A candidate must meet its quality, safety, latency, and cost thresholds without regressing a critical customer or risk slice. These thresholds form a vector of constraints rather than one average score: an improvement in quality cannot compensate for a security failure.

When the gates pass, increase exposure gradually across users and traffic. A new workflow, language, or customer segment is a new use case or slice and needs its own cases, criteria, and thresholds. When a gate fails, block or roll back the release, inspect the traces, perform a post-mortem, and promote the failure into a permanent regression case.

**Evals turn probabilistic model behavior into controlled engineering decisions.**

## Start with the product promise

Write the user-visible behavior in plain language. Then split it into claims that can be observed independently.

| Question | Working note |
| --- | --- |
| Who relies on the system? | _Add the primary user and affected stakeholders._ |
| What must it accomplish? | _Describe the task without naming a metric._ |
| What must never happen? | _List unacceptable harms and failures._ |
| What trade-offs are allowed? | _Record latency, cost, and quality boundaries._ |

## Define the unit of evaluation

A unit might be a single response, a tool call, a conversation, or a completed workflow. Choose the smallest unit that still captures the behavior you need to judge.

## Write the evaluation contract

Use this sentence as a starting point:

> Given **[context]**, when the system **[acts]**, it should **[observable behavior]**, subject to **[constraints]**.

## The control system: four planes

An evaluation programme is a control system, not merely a test suite. Its four planes form a closed loop.

| Plane | Responsibility | Typical evidence |
| --- | --- | --- |
| **Specification** | Define good behavior, prohibited behavior, users, risk tiers, and operating constraints before measurement begins. | Product promise, observable criteria, hard invariants, error budget |
| **Measurement** | Build trustworthy instruments and evidence. | Dataset roles, deterministic graders, calibrated judges, human adjudication |
| **Release** | Compare a candidate with the current system and decide how exposure may change. | Paired results, protected-slice gates, shadow and canary evidence |
| **Learning** | Turn live behavior back into improved specifications and regression protection. | Sampled traces, incident clusters, promoted regression cases |

The loop closes when learning rewrites the specification. A programme without a learning plane becomes stale at the rate its traffic changes.

## The evaluation grid: three axes

Every evaluation type occupies one cell in a three-axis grid. Naming all three coordinates prevents a vague “we have evals” claim.

| Axis | Values | Question |
| --- | --- | --- |
| **Lifecycle** | Offline · online | Is this controlled pre-release evidence or a production sensor? |
| **Purpose** | Capability · regression | Are we discovering what the system can do or protecting behavior that must not break? |
| **Level** | Step / component · Trajectory · Outcome | Are we grading one operation, the path through the system, or the verified final state? |

A single agent run may therefore need all three levels: a step-level tool check, a trajectory check for required and forbidden actions, and an outcome check against external state. Later chapters build and operate particular cells of this grid.
