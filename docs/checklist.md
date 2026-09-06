# Release Gates & Shipping

A release gate is the enforcement point for the evaluation contract. It decides whether a candidate may change exposure; the checklist is the close, not the decision mechanism.

## Pre-register the decision contract

For high-consequence or internal frontier workloads, supplement this application gate with a [bounded safety case](frontier-risk-decisions.md). A capability result, a detected violation, and effective containment are separate claims. Neither a green task score nor the label “internal only” substitutes for evidence about the requested permissions, assets, and exposure.

Write the rules, thresholds, gating slices, minimum evidence, decision owner, exception path, and known-good rollback target before seeing candidate results. A gate invented after the data arrives is a rationalization. Every override must be named, logged, scoped, time-boxed, and paired with a monitoring trigger.

## Four rule types

The [CI Gate Lab](ci-gate-lab.md) now runs passing, insufficient-evidence, and policy-violation controls, retains their packets, and replays the grades. The configured workflow makes book publication depend on these software checks. It does not grant application deployment authority.

1. **Hard invariant** — zero confirmed violations; never traded against an aggregate gain.
2. **Non-inferiority** — the candidate stays within a risk-derived margin of the baseline on each protected slice, with paired uncertainty.
3. **Superiority** — the improvement used to justify greater exposure must be evidenced, not merely higher as a point estimate.
4. **Operational bound** — latency, error rate, and cost per verified success remain inside fixed service constraints.

A release is a vector of these named constraints, not a single average score. Naming the rule type makes clear which arguments are valid: a margin can be negotiated; a hard invariant cannot.

## Earn exposure in stages

1. **Shadow** — execute against representative traffic without affecting users; validate instrumentation and compare decisions.
2. **Canary** — expose one bounded cohort or action class with explicit blast-radius limits.
3. **Progressive rollout** — increase exposure only when the previous stage satisfies the same pre-registered release vector.

Autonomy is earned per action class. Answering a question, changing an account, and moving money require separate ladders and evidence bars.

## Rollback thresholds

Separate two trigger classes:

- **Immediate severity-based rollback:** a confirmed safety, security, authorization, or irreversible-effect violation acts without waiting for statistics.
- **Statistical rollback:** a quality or operating regression acts after minimum effective exposure, a confidence threshold, and a persistence window are satisfied.

Use distinct expand, hold, constrain, and rollback boundaries to create guard bands and hysteresis, preventing a noisy metric near a threshold from repeatedly reversing the decision. Name the rollback authority, rehearse the path, and prefer graduated rollback—such as returning one action class to human approval—when risk permits.

## Shipping checklist

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
- [ ] The four rule types and protected slices are pre-registered.
- [ ] Shadow, canary, and progressive-rollout stages have explicit entry and exit evidence.
- [ ] Immediate and statistical rollback thresholds are distinct and rehearsed.
- [ ] Regressions have an explicit block, exception, constrain, or rollback decision.
- [ ] Production signals have owners and action thresholds.
- [ ] Reviewed production failures feed the regression suite.

## Build a release packet

A reviewer should be able to reproduce the decision without asking which dashboard tab was used.

Required packet:

1. change objective and claimed benefit;
2. candidate and current production baseline;
3. system, environment, and harness manifests;
4. dataset versions and access roles;
5. grader qualification and calibration reports;
6. per-case paired results, slices, denominators, and uncertainty;
7. hard-invariant and operational evidence;
8. known gaps and exclusions;
9. gate-policy version and machine-readable decision;
10. rollout, monitoring, rollback, and exception plans;
11. named approvals and timestamps.

Screenshots can help review but are not the source of truth.

## Governance and ownership

Evaluation is a decision system, so ownership cannot stop at “the AI team.” Engineering can build the measurement mechanism; the Business or domain owner must define what good, harmful, and valuable mean for the workflow. Separate authorship, measurement, and release authority when consequence justifies it.

| Role | Owns | Must not decide alone |
| --- | --- | --- |
| Business or domain owner | User promise, eligibility, material harm, value definition, protected workflow rules | Whether an engineering convenience redefines customer success |
| Product owner | Scope, intended population, release claim, feature and fallback experience | Whether a measured risk is technically acceptable without domain input |
| Evaluation owner | Evaluation contract, dataset roles, rubric validity, grader qualification, uncertainty, evidence packet | Product priority or production exposure |
| AI/application engineer | Candidate implementation, prompt/tools/retrieval versions, defect repair, reproducible runs | Acceptance on data used to tune the candidate |
| Data steward | Provenance, access, retention, consent/legal-basis workflow, correction and deletion controls | Model quality or product release |
| Security/privacy/risk owner | Threat model, sensitive-data controls, required oversight, non-waivable policy | Business value trade-offs outside the control mandate |
| Platform/SRE owner | Reliability, capacity, telemetry, canary automation, rollback readiness | Semantic quality or user-policy meaning |
| Release owner | Integrates authorised evidence and changes exposure; records decision and exceptions | Rewriting thresholds after results arrive |
| Incident commander | Containment, evidence preservation, recovery, post-incident coordination | Quietly closing an incident without regression protection or a recorded limitation |

One person may hold several roles in a small team, but the responsibilities and conflicts still exist. Record which hat approved each decision.

### Requirements-to-evidence traceability

Every material requirement should link forward to evidence and every blocking result should link back to authority:

| Requirement | Control/eval | Evidence | Decision | Owner |
| --- | --- | --- | --- | --- |
| Refund only an authenticated eligible order | Identity, policy, and state-transition graders | Per-case trace plus final ledger state | Hard invariant | Domain + evaluation |
| Never pay twice after an ambiguous timeout | Idempotency and inspect-before-retry trajectory checks | Fault-injection trial | Hard invariant | Engineering + SRE |
| Turkish experience is non-inferior | Protected-slice paired interval | Sealed acceptance report | Non-inferiority | Product + release |
| Cost falls without harming resolution | Matured verified outcomes and cost-per-success | Candidate/baseline experiment | Superiority on cost, non-inferiority on quality | Product + finance/domain |

Maintain a versioned chain:

```text
requirement and authority
→ evaluation contract
→ case/data provenance
→ grader and calibration version
→ experiment manifest and result
→ gate-policy rule
→ approval, exposure, and monitoring signal
→ incident or retirement record
```

This chain is the minimum requirements-to-evidence traceability needed to explain why a release was allowed. It is also how an audit can find a stale rubric, expired exception, unapproved dataset, or model change that bypassed requalification.

### Change control and oversight

Treat changes to models, prompts, tools, retrieval corpora, data transformations, rubrics, judge models, thresholds, simulators, price tables, and outcome definitions as versioned changes. Classify materiality, state which evidence must be rerun, review old/new disagreement, and record who approved new authority.

Human oversight must be an engineered control, not a slogan. Define which actions require review, what evidence the reviewer sees, how long they have, what happens on timeout, whether the action is reversible, and how reviewer decisions enter calibration without contaminating sealed acceptance data.

Governance records should include access logs, retention/deletion policy, data/model/system lineage, approvals, exceptions, incident evidence, and user remediation where applicable. Jurisdiction-specific legal assessment is separate; the book supplies an engineering evidence pattern, not legal advice.

## Use an AI test pyramid

| Layer | Typical contents | Cadence |
| --- | --- | --- |
| Deterministic base | schemas, permissions, state transitions, tool contracts, security checks | every change |
| Behavioral regression | representative cases, slices, retrieval checks, model judges | pull request or protected change |
| Expensive qualification | repeats, adversarial suites, simulators, strong judges, human review | scheduled or pre-promotion |
| Production control | shadow, canary, outcomes, drift, incidents | continuously during exposure |

Run the cheapest decisive checks first. A schema failure should not pay for 1,000 judge calls.

## Gate in dependency order

```text
lineage and manifest complete?
→ deterministic software and permission checks pass?
→ dataset and grader valid?
→ hard invariants pass?
→ absolute and slice floors pass?
→ claimed non-inferiority or superiority established?
→ latency, reliability, capacity, and cost pass?
→ shadow evidence passes?
→ bounded canary
→ progressive expansion
```

Later success does not erase an earlier blocker.

## Deterministic policy example

```python
def release_action(report, policy):
    failures = []
    if report.unauthorized_actions > policy.max_unauthorized_actions:
        failures.append("hard:unauthorized_actions")
    if report.duplicate_transactions > policy.max_duplicate_transactions:
        failures.append("hard:duplicate_transactions")
    if report.quality_ci_low < -policy.non_inferiority_margin:
        failures.append("quality:non_inferiority")
    if report.p95_latency_ms > policy.max_p95_latency_ms:
        failures.append("operations:p95_latency")
    if report.cost_per_success_usd is None:
        failures.append("operations:missing_cost")
    elif report.cost_per_success_usd > policy.max_cost_per_success_usd:
        failures.append("operations:cost_per_success")
    return {"action": "block" if failures else "canary", "failures": failures}
```

The policy consumes a report; it does not rerun graders or reinterpret traces. Keep measurement and decision boundaries testable.

## Risk-tier release profiles

| Profile | Example | Evidence and exposure |
| --- | --- | --- |
| Read-only low consequence | Draft FAQ answer | Offline regression, semantic sample, small canary |
| Reversible account action | Update communication preference | Strong identity/tool checks, audit, bounded canary |
| Financial state change | Issue refund | Hard authorization/idempotency invariants, sealed acceptance, full write-event monitoring, immediate rollback |
| High-consequence domain | Legal, medical, security-sensitive action | Domain-owner policy, expert evidence, restricted autonomy, human oversight as required |

Risk changes the required evidence and action authority. It does not justify vague thresholds.

## Shadow and canary entry criteria

### Enter shadow only when

- offline blockers pass;
- trace completeness is verified;
- side effects are suppressed or sandboxed;
- sampling and privacy controls are approved;
- candidate and baseline are comparable;
- exit and rollback conditions are registered.

### Enter canary only when

- shadow results support the intended traffic;
- side effects have runtime controls;
- maximum exposure and action class are bounded;
- immediate and statistical rollback automation is tested;
- on-call ownership exists;
- the known-good rollback target is deployable.

## Exception handling

An Exception is a governed decision to proceed despite a non-hard requirement. It must never silently turn a failure into a pass.

```yaml
exception_id: exc-2026-017
failed_rule: operations:p95_latency
hard_invariant: false
scope:
  workflow: status-read-only
  traffic_max_percent: 2
  expires_at: 2026-09-13T00:00:00Z
reason: collect bounded evidence for a known cold-start regression
compensating_controls:
  - exclude refund writes
  - auto_rollback_if_p95_ms_above_3500_for_10m
owner: release-owner
approvers: [product-owner, sre-owner]
follow_up: perf-issue-42
```

Exceptions require a reason, owner, scope, expiry, compensating controls, and follow-up. Hard authorization, privacy, and irreversible-effect invariants are not exception candidates in this book’s policy.

## Rollback as a tested capability

Test rollback before the canary:

- configuration and model revision revert;
- feature or action-class disable;
- tool permission removal;
- traffic routing to the known-good baseline;
- in-flight state reconciliation;
- evidence preservation;
- alert delivery and ownership;
- user/customer remediation where required.

Measure time to detect, decide, and contain. A rollback document that has never been exercised is a hypothesis.

## Artifact: release manifest

```yaml
release_id: cx-agent-rc4
objective:
  type: cost_reduction
  claim: lower cost per verified success with non-inferior resolution
baseline: cx-agent-v3
system:
  model: provider/model-version
  prompt: refund-v5
  tools: refund-tools-v2
  policy: refund-policy-v3
evidence:
  dataset: refund-acceptance-v2
  experiment: rc4-vs-v3-2026-09-06
  graders: [state-v2, trajectory-v2, groundedness-v1]
  calibration_report: groundedness-v1-report
gate_policy: refund-gate-v2
decision:
  action: canary
  reasons:
    - all hard invariants passed on named trials
    - non_inferiority established for registered resolution outcome
    - cost objective met under price-table-v3
rollout:
  first_stage_percent: 1
  maximum_financial_exposure_usd: 500
  rollback_target: cx-agent-v3
  policy: refund-canary-v1
approvals:
  product: approved
  evaluation: approved
  sre: approved
known_gaps:
  - Turkish high-value cases remain human-approved only
```

The values are synthetic. The manifest demonstrates lineage and decision structure.

## Worked example: one candidate, two possible claims

Synthetic evidence:

- quality delta: +0.5 points, interval −1.0 to +2.0;
- cost per verified success: down 22%;
- no observed hard violations in the named suite;
- all protected slices meet registered non-inferiority margins;
- latency remains inside budget.

If the release objective is **better quality**, evidence is inconclusive. If the registered objective is **lower cost with non-inferior quality**, the candidate may earn a canary. The same numbers support different actions because the claim differs.

## Failure modes

| Failure mode | Consequence | Repair |
| --- | --- | --- |
| One weighted score | Safety and cost compensate invisibly | Independent named rules |
| Gate written after results | Candidate determines policy | Pre-register and version the policy |
| Missing baseline | Absolute score lacks regression context | Compare with shipping configuration |
| Unqualified judge blocks | Measurement error stops releases | Require criterion-specific authority |
| CI runs only happy paths | Fast green check gives false confidence | Tier suites by risk and cost |
| Canary without blast limit | Experiment becomes uncontrolled rollout | Bound users, traffic, action, and value |
| Exception without expiry | Temporary waiver becomes policy | Scope, owner, expiry, controls, follow-up |
| Rollback not rehearsed | Detection does not produce containment | Test the complete rollback path |

## Exercise: decide whether to ship

A candidate passes average quality, latency, and cost. Turkish quality is below its pre-registered floor, but the team says Turkish traffic is only 8%. The release adds no new Turkish capability.

What should the gate return, and what options remain?

??? success "Answer"
    Return `block` or `constrain` because a protected slice floor is an independent rule; global traffic share cannot compensate. Options include fixing and rerunning, restricting the candidate to supported slices if routing and disclosure are safe, holding Turkish traffic on the baseline, or using a time-boxed non-hard exception only if the policy explicitly permits it and owners approve compensating controls. Do not relabel the floor after seeing the result.

## Verification checklist for the gate itself

- [ ] Known-good evidence produces the expected canary action.
- [ ] Each known-bad mutant fails for the intended rule.
- [ ] Missing required evidence fails closed.
- [ ] Hard failures cannot be overridden by aggregate gains.
- [ ] Judge authority is checked before its score can block.
- [ ] Policy, price, data, and evaluator versions enter the decision.
- [ ] Exceptions remain visible, scoped, and expiring.
- [ ] Canary and rollback controls have been exercised.
