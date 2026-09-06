# Production Evals: Watch and Localize

Offline evaluation helps decide what may ship. Production evaluation is a sensor: it tells you whether the deployed system still behaves as intended and supplies the evidence needed to localize failure.

## WATCH the live contract

Monitor leading signals such as tool errors, policy violations, latency, escalation, and abstention alongside lagging outcomes such as verified resolution, repeat contact, customer impact, and cost per successful outcome. Sample semantic grading asynchronously off the request path so the evaluator does not become a second production dependency.

Every signal needs a denominator, slice, owner, action threshold, and review cadence. A dashboard without a response contract is decoration.

## Preserve traceability

For every scored sample, retain the relevant application version, model and prompt version, retrieval context, tool results, rubric version, and judge version—subject to privacy and retention policy.

## LOCALIZE with a Trace taxonomy

Start at the first bad span, not the final answer. Classify the earliest causal failure using a small taxonomy whose categories route to different fixes:

1. Environment or input
2. Retrieval miss
3. Tool selection or execution
4. Reasoning failure
5. Policy or format
6. Out of scope

“Hallucination” is a symptom, not a useful root-cause category. A missing source and an ignored source require different repairs.

Localize at all three levels introduced in Foundations: inspect the failing step or component, the trajectory that connected the steps, and the externally verified outcome. Correlation identifiers must cross model, retrieval, tool, and system-of-record boundaries so the trace can actually be reconstructed.

## Close the learning loop

Cluster reviewed failures, prioritize them by severity, frequency, recency, and strategic value, then turn confirmed incidents into versioned regression cases. A targeted fix should pass its reproduced failure, the broad regression suite, and sealed acceptance before chapter 11 allows exposure to expand.

## Offline and online evidence have different jobs

| Evidence | Strength | Limitation |
| --- | --- | --- |
| Curated offline cases | Controlled, reproducible, diagnosable | Can drift away from real traffic |
| Deployment simulation | Replays current-like requests before exposure | Still depends on recorded context and simulated outcomes |
| Shadow evaluation | Tests a candidate on live distribution without user-visible writes | Costs inference; suppressing effects can alter behavior |
| Canary | Measures real behavior at limited exposure | Risk remains; small samples have low power |
| A/B test | Estimates relative user or business outcomes | Requires valid assignment, guardrails, and enough time |
| Continuous evaluation | Detects drift and creates learning material | Sampling, delayed labels, and evaluator drift complicate trends |

Offline evidence earns the right to expose a candidate. Online evidence verifies transfer and decides whether exposure should change.

## Define signal contracts

Every production signal needs:

```yaml
signal: verified_refund_resolution_7d
definition: eligible cases with correct final state and no repeat contact within seven days
numerator: resolved_eligible_cases_without_repeat_contact
denominator: eligible_cases_with_matured_7d_outcome
slices: [language, workflow, release, risk]
owner: cx-product-owner
cadence: daily
alert:
  type: control_relative_and_absolute_floor
  action: hold_or_rollback
label_delay: 7d
```

Changing the denominator can create a trend without changing behavior. Version definitions and label-maturity rules.

## Define CX outcomes precisely

Operationally convenient proxies are not interchangeable with customer success. Keep these outcome families separate:

| Outcome | Numerator | Denominator | What it proves | What it can hide |
| --- | --- | --- | --- | --- |
| **Containment** | Eligible interactions that did not enter a human queue during the defined window | All eligible automated interactions | The automated channel retained the interaction | Abandonment, silent failure, or a later repeat contact |
| **Deflection** | Eligible demand that did not create the otherwise expected assisted contact | Eligible demand under a registered counterfactual or comparison design | Assisted demand may have been avoided | Whether the customer's problem was solved |
| **Verified resolution** | Matured cases with the correct external state, no prohibited effect, and no qualifying repeat contact | Eligible cases whose outcome window has matured | The customer objective was achieved under the product contract | Longer-term dissatisfaction outside the window |
| **Adoption** | Eligible users or tasks that used the capability as defined | Users or tasks offered a genuine opportunity to use it | People used the feature | Whether use was successful, voluntary, or valuable |
| **Quality-adjusted business value** | Verified value created minus reviewed failure, recovery, human-work, and operating costs | A declared unit such as eligible case, verified success, or exposed user | Benefit survives quality and cost constraints | Intangible or delayed harms not represented in the value model |

“No human handoff” therefore cannot be reported as “resolved.” A conversation can be contained because the user gives up. Deflection needs a credible counterfactual, not merely the absence of a ticket. Adoption is exposure-dependent and can rise while quality falls.

One conservative verified-resolution rule is:

\[
R_i = \mathbb{1}(\text{permitted objective achieved})
      \cdot \mathbb{1}(\text{external state verified})
      \cdot \mathbb{1}(\text{no hard violation})
      \cdot \mathbb{1}(\text{no qualifying repeat contact in } W)
\]

The aggregate is calculated only over eligible cases whose window \(W\) has matured. Record exclusion reasons rather than silently shrinking the denominator.

### Bite-sized synthetic cohort

Suppose 100 eligible refund conversations mature after seven days:

- 88 never reach a human, so containment is 88%;
- 82 end with a correct verified state;
- 4 of those 82 repeat-contact about the same unresolved problem;
- 1 of the remaining cases contains an unauthorized financial effect.

Verified resolution is therefore \((82 - 4 - 1) / 100 = 77\%\), not 88%. Whether deflection is 88% cannot be inferred without an appropriate comparison showing which assisted contacts would otherwise have occurred.

For value, pre-register units and costs:

\[
\text{quality-adjusted value}
= V_{\text{verified outcomes}}
- C_{\text{human work}}
- C_{\text{recovery}}
- C_{\text{model+tools}}
- C_{\text{reviewed harm}}
\]

Do not assign a convenient zero to unmeasured harm. Mark it unknown and constrain the claim.

## Leading, lagging, and diagnostic signals

### Leading controls

- authorization and policy violations;
- duplicate or irreversible effects;
- tool errors and timeouts;
- retrieval misses or stale evidence;
- refusal, abstention, and escalation;
- trace completeness;
- service errors, saturation, latency, tokens, and cost.

### Lagging outcomes

- verified resolution;
- repeat contact;
- reversal or compensation;
- customer complaint or satisfaction;
- human handling time;
- financial or operational impact.

### Diagnostics

- model, prompt, retrieval index, and tool version;
- first causal failure;
- path length and retries;
- judge disagreement;
- new failure clusters;
- slice and cohort shifts.

Leading signals support fast containment. Lagging outcomes test whether the product created value. Diagnostics explain where to intervene.

## Instrument portable traces

A useful trace crosses model, retrieval, tool, and external-state boundaries:

```json
{
  "trace_id": "tr-817",
  "session_id": "sess-41",
  "release": "cx-agent-rc4",
  "case_or_sample_id": "sample-2026-09-06-00817",
  "model": "provider/model-version",
  "prompt_version": "refund-v5",
  "retrieval_index": "policy-index-v5",
  "tool_schema": "refund-tools-v2",
  "policy_version": "refund-policy-v3",
  "events": [],
  "final_outcome": "pending",
  "latency_ms": 1840,
  "token_usage": {"input": 920, "output": 146},
  "estimated_cost_usd": 0.014,
  "evaluator_versions": ["state-v2", "grounding-v1"]
}
```

Use standard telemetry conventions where they fit, while keeping domain-specific state and policy evidence. The local trace remains provider-neutral so observability vendors can be replaced.

## Protect sensitive payloads

Prompts, completions, retrieved content, and tool arguments may contain personal, proprietary, or secret data. Do not log full payloads by default.

Separate:

- low-sensitivity operational metadata;
- access-controlled evaluation payloads;
- hashed or tokenized identifiers;
- governed raw evidence with retention/deletion policy.

Redact before general telemetry export, restrict access by role, record review purpose, and test redaction. A trace that cannot be safely inspected is not solved by copying it into more systems.

## Sample by risk and information value

Use layered sampling:

- deterministic safety and service controls on 100% where cheap;
- full capture of state-changing or critical events;
- stratified semantic samples by release, workflow, language, and risk;
- higher rates for new versions and emerging clusters;
- disagreement and uncertainty sampling for human review;
- small unbiased samples for prevalence estimates.

Adaptive sampling improves discovery but biases raw rates. Retain inclusion probabilities or keep a separate representative stream for population estimates.

## Deployment simulation

Deployment simulation applies a candidate to recent production-like conversations with the previous assistant completion removed. It can reveal pre-release failures on realistic requests while avoiding direct exposure.

Safe pattern:

```text
recent de-identified context
→ remove old assistant action/answer
→ replay candidate in sandboxed tools or read-only mode
→ score trace and simulated state
→ compare forecast with old behavior and later observed outcomes
```

Controls include consent/legal basis where applicable, de-identification, no live writes, time-window recording, traffic coverage, candidate/baseline pairing, and explicit limits on conclusions. Traditional synthetic cases remain valuable for rare risks and controlled faults.

## Shadow evaluation

Shadowing mirrors selected requests to a candidate without allowing user-visible side effects. For state-changing workflows:

- replace writes with sandboxed simulations;
- record what would have happened;
- preserve the same readable state where safe;
- compare proposed actions, traces, quality, latency, and cost;
- prevent the candidate from contacting users or external systems.

Shadow behavior may differ from live behavior when suppressed writes alter later context. Document the gap.

## Canary and control

A canary receives real exposure. Pre-register:

- eligible traffic and exclusions;
- allocation or routing method;
- maximum exposure and blast radius;
- bake period and minimum effective sample;
- hard rollback events;
- absolute floors and control-relative metrics;
- guard bands and hysteresis;
- decision owner and automated authority.

Do not wait for statistical significance after a confirmed unauthorized financial action. Severity-based rollback and statistical performance rollback are separate trigger classes.

## Delayed outcomes and censoring

Some labels mature later: repeat contact after seven days, chargeback after weeks, or satisfaction after survey response. Keep provisional and matured cohorts separate.

At time \(t\), calculate the denominator only from samples whose outcome window has matured. Otherwise the newest release can look artificially good because its failures have not had time to appear.

Track missing outcomes and differential response. Survey responders may not represent all users.

## Drift

Drift can affect:

- input topics, languages, and lengths;
- workflow and tool paths;
- retrieval corpus and freshness;
- output and embedding distributions;
- failure taxonomy;
- outcome prevalence;
- judge agreement;
- latency and cost.

Distribution change is a trigger for investigation, not proof of harm. Pair drift signals with task and outcome evaluation.

## Three alert layers

1. **Synchronous controls:** deterministic permission, schema, privacy, and prohibited-action enforcement in the request path.
2. **Rollout controls:** service errors, latency, critical events, cost, and control-relative outcomes that hold or roll back exposure.
3. **Asynchronous semantic evaluation:** sampled groundedness, quality, trajectory, and failure clustering outside the request path.

Avoid placing a probabilistic judge synchronously in every request unless its latency, availability, error modes, and fallback behavior are part of the product design.

## Incident response

```text
detect
→ stop promotion
→ bound blast radius
→ disable or roll back risky capability
→ preserve evidence
→ identify first causal failure
→ reproduce
→ add or repair cases and graders
→ fix
→ rerun broad gates
→ staged re-release
→ postmortem
```

The incident is not closed when the symptom disappears. It needs a reviewed regression, grader repair, or explicit explanation of why it cannot be tested.

## Eval-system metrics

Measure the measurement system itself:

| Metric | Definition |
| --- | --- |
| Escaped regression rate | Regressions discovered after the gate that existing evidence should have caught |
| False-block rate | Releases blocked by invalid cases, broken graders, or non-material noise |
| Serious-failure protection | Reviewed severe failures converted into regression, grader repair, or documented limitation |
| Incident-to-case latency | Time from confirmed incident to approved reproducible protection |
| Offline-to-live predictive validity | Relationship between offline forecast and canary/live outcomes |
| Judge drift | Change in agreement, class errors, or abstention on stable reviewed samples |
| Trace completeness | Eligible samples with reconstructable required spans and versions |
| Review yield | Human-reviewed samples that produce a new case, rubric repair, or confirmed insight |

These metrics should improve decision quality, not reward indiscriminate case creation or alert volume.

## Worked example: canary regression

Synthetic canary evidence after 1,000 matured eligible conversations in each arm (2,000 total):

| Signal | Control | Candidate | Interpretation |
| --- | ---: | ---: | --- |
| Verified resolution | 840/1,000 | 852/1,000 | Candidate point estimate is higher |
| Repeat contact | 110/1,000 | 96/1,000 | Promising lagging result |
| Duplicate refund | 0 | 1 | Immediate hard rollback event |
| p95 latency | 1.9 s | 2.1 s | Inside 3 s budget |
| Trace completeness | 99.7% | 99.8% | Investigable |

The candidate rolls back despite better average outcomes. Investigation finds a timeout after commit followed by a retry. The team preserves the trace, minimizes the scenario, adds a state invariant and trajectory case, fixes idempotency recovery, and reruns offline plus shadow gates before another canary.

## Artifact: production sample

```yaml
sample_id: prod-review-2026-09-06-817
selection:
  stream: state_changing_events
  inclusion_probability: 1.0
  reason: refund_write
versions:
  release: cx-agent-rc4
  model: provider/model-version
  prompt: refund-v5
  policy: refund-policy-v3
  trace_schema: cx-trace-v1
outcomes:
  immediate: refund_submitted
  seven_day: pending_maturity
evaluations:
  deterministic_state: pass
  trajectory: pass
  groundedness: abstain
review:
  required: true
  reason: judge_insufficient_evidence
privacy:
  payload_store: restricted
  retention_days: 30
```

## Failure modes

| Failure mode | What it causes | Repair |
| --- | --- | --- |
| Dashboard without action | Metrics accumulate but exposure never changes | Give every signal an owner and response contract |
| Uniform semantic sampling | Cost is high and rare risk is missed | Combine representative, stratified, and event-triggered streams |
| Adaptive sample reported raw | Prevalence is biased | Preserve inclusion probabilities or separate estimate stream |
| Newest cohort includes immature labels | Candidate looks artificially good | Use matured denominators and censoring rules |
| Full payload logging | Privacy and security exposure | Separate metadata and governed evidence stores |
| Drift alert equals failure | Harmless distribution change creates incidents | Confirm with task and outcome evidence |
| Shadow called production proof | Suppressed effects change behavior | Document limitations and proceed to bounded canary |
| Incident fixed without regression | Same mechanism can recur | Produce incident-to-case receipt |

## Exercise: design the production sampling policy

You can afford semantic judging on 5% of one million monthly conversations. Refund writes are 2% of traffic, Turkish traffic is 8%, and a new release will initially receive 1% exposure.

Design streams that support safety detection, release comparison, and population estimates.

??? success "Answer outline"
    Run cheap deterministic permission, schema, service, and state controls on all eligible events; retain every consequential refund write for governed review/evaluation; maintain a small unbiased random sample for population estimates; stratify semantic samples by release, language, workflow, and risk so the 1% canary and Turkish traffic receive useful support; oversample errors, abstentions, and emerging clusters for diagnosis; record selection probabilities; keep diagnostic samples out of unweighted prevalence estimates; and define owner/action rules plus label-maturity windows before rollout.

## Verification checklist

- [ ] Offline, deployment-simulation, shadow, canary, and live claims remain distinct.
- [ ] Every signal has a definition, denominator, slice, owner, and action.
- [ ] Traces cross model, retrieval, tool, and outcome boundaries.
- [ ] Sensitive payloads have access and retention controls.
- [ ] Sampling supports representative estimates and rare-risk discovery.
- [ ] Delayed outcomes use matured cohorts.
- [ ] Hard rollback and statistical rollback are separate.
- [ ] Incidents produce reproducible protection or an explicit limitation.
- [ ] Eval-system health is measured, not assumed.

## Primary reading

- [OpenAI — Predicting model behavior by simulating deployment](https://openai.com/index/deployment-simulation/)
- [OpenTelemetry — Semantic conventions for generative AI systems](https://opentelemetry.io/docs/specs/semconv/gen-ai/)
- [Google SRE Workbook — Canarying releases](https://sre.google/workbook/canarying-releases/)
- [LangSmith — Evaluation concepts](https://docs.langchain.com/langsmith/evaluation-concepts)
