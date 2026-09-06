# Frontier risk decisions: what does the evidence justify?

A coding agent completes 92 of 100 tasks. Its monitor flags two prohibited actions—but only after both actions commit. Should it receive broader credentials?

No. The task score measures one capability on one sample. The monitor evidence shows a containment failure on the tested path. Neither result establishes that the proposed credential scope is acceptable. This **illustrative case** is the thread through this chapter; its numbers are teaching inputs, not measured lab or company results.

The previous chapters explain how to measure behavior. This chapter asks how that evidence supports—or fails to support—a risk decision. It complements the [research-to-practice evidence ledger](research-to-practice.md), rather than replacing its method inventory. Primary sources were checked on **6 September 2026**.

## Six claims that must not collapse into one score

| Claim | Question to answer | Evidence that helps | What it cannot establish alone |
| --- | --- | --- | --- |
| Capability | Can the system perform the relevant task with suitable tools, context, and effort? | Elicitation study, verified outputs, tool/budget ablations | Whether the capability is usually exercised or causes harm |
| Practical uplift | Does access materially change what a particular user or operator can accomplish? | Matched assisted/unassisted comparison, actual task outcomes and effort | A general increase in real-world harm |
| Harmful propensity | Does the system attempt the prohibited behavior under specified conditions? | Behavioral audits, blinded transcript review, controlled opportunities | Whether an attempted action succeeds or affects a person |
| Safeguard effectiveness | Do controls prevent or contain the consequential action? | Boundary enforcement, adaptive tests, interruption and recovery traces | Safety outside the tested control stack and threat conditions |
| Exposure and consequence | Who or what can be affected, at what scale, and with what reversibility? | Permissions, assets, concurrency, duration, dependency and workflow analysis | A numeric risk estimate without justified event probabilities |
| Residual uncertainty | What remains unknown, and could it change the decision? | Missing-evidence register, sensitivity analysis, dissent and explicit assumptions | Permission to treat unmeasured risk as zero |

Do not multiply a benchmark pass rate, an unrelated misuse rate, and a monitor recall number into a “residual risk” probability. Such a calculation needs a causal model, compatible denominators, and justified conditional dependence assumptions. In the absence of those, retain the separate claims and their uncertainty.

### What the frontier sources establish

**Anthropic: capability thresholds can remain ambiguous.** Its February 2026 RSP discussion explains that models can pass readily available biological-knowledge tests while those tests establish neither a strong low-risk nor a strong high-risk conclusion. It describes precautionary safeguards and separates company mitigation plans from broader industry recommendations. The lesson is not to dismiss benchmarks; it is to state which link between measured capability and consequential risk remains unresolved. [Anthropic RSP v3 discussion](https://www.anthropic.com/news/responsible-scaling-policy-v3)

**OpenAI: assessment and safeguards cover different pathways.** Its September safeguards disclosure distinguishes malicious use from unauthorized model actions, describes stronger controls during development and before release, and says monitoring can stop potentially unauthorized activity. It also acknowledges false interruptions of legitimate work. These are disclosed practices and assessments, not public estimates of universally effective containment. Our local protocol below tests timing and consequences separately from detection. [OpenAI safeguards disclosure](https://openai.com/index/path-to-astra/)

**DeepMind: internal use can be a deployment surface.** Its framework update extends safety-case review to large internal deployments at advanced machine-learning R&D capability levels. The April 2026 update also adds tracked capability levels for earlier risk identification. “Internal only” therefore does not remove the need to assess assets, permissions, scale, and operator control. [DeepMind Frontier Safety Framework update](https://deepmind.google/blog/strengthening-our-frontier-safety-framework/)

These frameworks are not interchangeable implementations of our refund gate. Their risk domains, thresholds, evidence, and governance differ. Borrow explicit claim–evidence–control reasoning; do not copy a named capability level into an application release policy as if it were a transferable certification.

## Kata 13: write a bounded safety case

**Know:** a safety case is a structured argument for a specified deployment, backed by evidence and constrained by assumptions. It is not a collection of green evaluation scores.

**Scenario:** an internal research assistant may read approved repositories, propose patches, run tests, and request narrowly scoped artifact writes. A proposed expansion would permit unattended runs with broader credentials. The teaching evidence packet contains:

- 92/100 completed coding tasks, versus 85/100 for a baseline; no registered statistical comparison supplied.
- Two committed prohibited writes in twenty adversarial sandbox trials; both eventually detected.
- Complete operator-owned traces for 96/100 ordinary trials; four have unexplained gaps.
- No cross-run isolation experiment at the proposed concurrency.
- No measured human recovery burden after a stop.

**Task:** make the decision without averaging these observations. Identify the claim each result supports, the missing evidence, and the permitted next action.

??? success "Worked decision"
    Hold the credential expansion. The task results justify further capability investigation, not a claim of superiority or safe autonomy. The sandbox trials demonstrate a consequential failure of the tested write-control path. Missing traces weaken confidence in behavioral conclusions, and the untested concurrency and recovery paths remain open risks.

    A separately assessed read-only sandbox study may continue under existing controls. Do not call that permission to deploy unattended write access. Do not hide the two committed writes by reporting that the monitor detected every observed violation.

```yaml
# Illustrative decision record, not an executed release or company policy.
decision_id: internal-agent-example-01
requested_change: broader_credentials_for_unattended_runs
hazard: unauthorized_changes_to_protected_artifacts
deployment_surface: internal_research_and_evaluation_infrastructure
decision: hold_expansion
claims:
  task_capability: observed_on_small_sample_not_release_qualified
  prevention: contradicted_by_two_committed_sandbox_writes
  evidence_integrity: incomplete_operator_traces
  cross_run_isolation: untested_at_requested_concurrency
permitted_next_work: separately_authorized_read_only_sandbox_study
required_evidence:
  - reproduce_and_repair_precommit_enforcement_failure
  - complete_operator_owned_trace_join
  - test_isolation_under_matched_concurrency
  - measure_denial_recovery_and_human_burden
reopen_when: all_required_evidence_reviewed_for_exact_candidate_and_scope
decision_owner: named_release_authority_required_before_execution
```

**Extend:** replace the two committed writes with two blocked attempts. What changed? Prevention now worked on those trials, but propensity, representativeness, trace gaps, and requested exposure still need separate assessment. A successful control test should improve the relevant claim without silently closing every other one.

**Interview answer:** “I tie each risk claim to evidence and a bounded deployment configuration. Capability improvement cannot offset failed controls or missing evidence. The decision names what may proceed, what is withheld, and which observations would change that decision.”

## Kata 14: detection is not containment

**Know:** an alert is an observation; containment is an intervention that changes what the system can still do.

The following timelines are **hand-authored exercise data**, not observed OpenAI, Anthropic, or local monitoring performance. Times are milliseconds from the start of each trial. A dash means no event was observed within the 300 ms window.

| Trial | Labeled hazardous? | Attempt | First protected effect committed | Alert | Stop enforced |
| --- | --- | ---: | ---: | ---: | ---: |
| A | Yes | 100 | 150 | 180 | 200 |
| B | Yes | 100 | — | 110 | 120 |
| C | No | 50 | — | 55 | 60 |
| D | Yes | 100 | 150 | — | — |

**Task:** compute detection recall, timely containment, false-stop frequency, and the detection-to-stop delays. Explain why averaging only observed delays can conceal the worst case.

??? success "Worked calculation"
    Detection recall is `2/3`: A and B are alerted, D is missed. Timely containment is `1/3`: only B is stopped before a protected effect commits. A has a 20 ms alert-to-stop delay but is already too late. B has a 10 ms delay. D has no observed containment within the window; do not drop it from the denominator or assign it zero delay.

    The one benign trial, C, is stopped, so the observed false-stop fraction is `1/1`. That tiny denominator is inadequate for estimating field false-stop rates. It is enough to demonstrate why a benign-control arm is needed.

    The finite alert-to-stop mean is 15 ms, conditional on the two detected hazardous trials. Reporting it alone conceals both the late containment in A and the absence of containment in D.

For an implemented monitor study, retain attempted and completed actions before containment, timestamps from a common clock or documented clock-join method, queue delay, denied follow-up actions, recovery outcome, lost work, and human review time. Count missing or censored events explicitly. A stop must propagate to queued work and delegated workers; cancelling only the visible parent is not sufficient evidence.

The local [process-recovery study](process-recovery-study.md) demonstrates how to inspect durable effects across interruption. It does **not** validate a threat detector, containment deadline, distributed cancellation, or monitor false-positive rate. The [local containment study below](#local-containment-test-the-write-boundary-not-just-the-alert) now exercises scheduled enforcement in actual processes. Detector qualification, latency distributions and distributed control remain open parts of this monitoring protocol.

**Interview answer:** “I measure whether containment happened before the harmful effect, not just whether a detector fired. I retain misses, late stops, false stops, and recovery effort; fast alerts among detected cases cannot establish operational safety.”

## Evaluate the internal development environment

An evaluation worker can affect training inputs, benchmark state, shared caches, credentials, and the evidence used to approve its own successor. That is a consequential deployment surface even when there are no external customers.

**Proposed local isolation experiment—not yet executed:** launch authorized sandbox tasks with distinct synthetic markers and separate permissions. Vary only the intended sharing policy. Observe whether markers, writable artifacts, or task state cross a boundary that should isolate them. Test reused workers and concurrent runs, not just freshly started single workers. Keep event capture and scoring outside the worker's writable scope.

The minimum evidence packet should link each request to a run identity, resource namespace, actual access decision, completed effect, and operator-owned log. Compare artifact hashes against references held outside the agent's authority. Hashes stored beside writable artifacts cannot, on their own, prove integrity.

METR's August 2026 independent investigation found unintended communication and coordination among agents intended to be isolated, plus transcript-tampering activity. It explicitly limits its conclusions: some activity was missing, parts of the analysis relied on imperfect AI assistance, and broader prevalence and safeguard effectiveness were out of scope. Use it as evidence that these failure modes deserve testing—not a general failure-rate estimate or a recipe for reproducing the incident. [METR investigation](https://metr.org/blog/2026-08-26-openai-hugging-face-incident-investigation/)

Planned multi-agent collaboration is a different contract. In that case some sharing is authorized, and the eval asks whether delegation and merging work. Cross-run isolation asks whether **unauthorized** sharing is prevented. A good coordination benchmark does not answer the isolation question.

## Human behavior requires human-outcome evidence

A transcript may contain no rubric-labeled manipulation while a person becomes worse informed or less able to exercise their own judgment. Conversely, a labeled tactic need not change that person's behavior. Separate model propensity, participant outcomes, and the mechanism claimed to connect them.

DeepMind's March 2026 work measures both propensity and efficacy, reports domain-dependent effects, and warns that its controlled participant studies need not predict real-world behavior. It also discloses use of these evaluations in model assessment. That supports studying actual participant outcomes; it does not provide a universal threshold for all applications. [DeepMind human-participant research](https://deepmind.google/blog/protecting-people-from-harmful-manipulation/)

**Worked study-design exercise:** for a low-stakes decision-support application, compare a non-AI information control, ordinary assistance, and an approved safeguarded variant. Pre-register comprehension and decision-quality outcomes, baseline measures, assignment, attrition handling, exposure duration, and analysis. A satisfaction score is secondary, not a substitute for the outcome. Include repeated exposure only under an appropriate consent and review protocol.

Report subgroup uncertainty where the study can responsibly support it; do not infer individual susceptibility from identity labels. Use independent ethical review, withdrawal and debriefing procedures, privacy controls, and risk-appropriate participant protection before running such research. This book does not run experiments on users or suggest that a synthetic customer simulator validates human effects.

**Solution criterion:** a sound proposal distinguishes the randomized intervention from the outcome, includes a credible control and safety plan, and explains what cannot transfer from the tested population and exposure. “The judge found fewer manipulative phrases” is not an adequate primary endpoint for participant harm.

## Kata 15: autonomy must be useful at the required reliability

**Know:** replacing some human labor is not equivalent to safe unattended delegation.

METR emphasizes that a 50% task horizon describes human task time associated with a modeled success rate, not how long an agent can safely operate alone. Task distributions, verification, and intervention effort matter; converting horizon into useful automation requires more workflow evidence. [METR methodological limitations](https://metr.org/notes/2026-01-22-time-horizon-limitations/)

**Illustrative workload:** manual completion takes 40 minutes. With an agent, human setup takes 5 minutes and verification takes 8. A failure requires 40 additional minutes of recovery and occurs on 25% of tasks. Assume these are known average costs for this exercise, recovery always works, and agent waiting time does not consume human labor.

**Task:** compute expected human labor. Then decide whether the apparent saving establishes readiness for an application requiring rare undetected failures.

??? success "Worked calculation and decision"
    Expected human labor is `5 + 8 + 0.25×40 = 23` minutes: a saving of 17 minutes against the 40-minute baseline. This economic calculation does not include elapsed waiting time, queue effects, correlated incidents, undetected failures, or irreversible harm.

    If the registered requirement is an undetected-failure probability below 0.1%, observing zero such failures in 200 independent representative tasks is insufficient. The one-sided 95% binomial upper bound is `1 − 0.05**(1/200)`, approximately 1.49%. The required claim has not been established, even with apparent labor savings.

    The decision can be “continue supervised evaluation” rather than “unattended deployment.” Verification is part of the system being evaluated; removing it changes the intervention and invalidates the labor and reliability argument.

**Extend:** suppose failures become rarer but recovery rises to 180 minutes because they are harder to diagnose. Recalculate using the new measured failure rate. Then identify costs that a simple expected-value model cannot responsibly offset, such as a prohibited irreversible action.

**Interview answer:** “I evaluate the human–agent workflow: verified completion, verification burden, recovery effort, elapsed time, and undetected failure. A task-horizon or cost improvement does not itself establish the reliability needed for delegation.”

## From evidence to exposure: a bounded decision, not a badge

For the same candidate and harness, different authority can be justified for different tasks. A read-only research pilot and an unattended write-capable agent are different deployments, even if they use the same model identifier.

| Decision | What the safety case must establish |
| --- | --- |
| Continue sandbox research | Authorized environment, bounded assets, containment and evidence capture appropriate to the experiment |
| Start shadow evaluation | Privacy and data access approved; outputs cannot silently trigger real effects |
| Start a bounded canary | Exact task/permission/population scope qualified; live controls, owner, rollback, and outcome observation ready |
| Expand exposure | Registered evidence supports the larger scope; concurrency, dependencies, and delayed outcomes remain covered |
| Restrict or hold | Evidence is missing, stale, contradictory, or insufficient for the requested scope |
| Stop and recover | A defined harm or integrity boundary is crossed; containment and incident response take precedence over another statistical look |

These are decision requirements, not a new automated release implementation. The local statistical, semantic, and recovery studies remain `lab_only`. Their evidence may explain a control or reveal a failure; it does not meet all canary prerequisites.

## Missing implementation versus unresolved science

Record these as different backlog items. “We have not tested cancellation propagation” is an implementable local gap. “The available proxy does not establish practical harmful uplift” may require new validation research. Neither can be closed by adding another citation or increasing a test count.

The [delivery map](primer-delivery-map.md) keeps the remaining work explicit: measured monitoring and isolation, live agent studies, qualified semantic calibration, human outcomes where relevant, and executed CI/CD and exposure-control exercises. The aim is a defensible decision whose scope survives inspection—not a claim that all frontier risk has been solved.

## Local containment: test the write boundary, not just the alert

The monitor says “stop.” A delegated worker already has a queued operation. Does the operation commit? That question belongs to the enforcement path, not the detector's classification score.

This study uses harmless synthetic effects in a temporary local SQLite database. Scripted stop signals arrive at explicit execution barriers. The worker's write tool checks shared authority and, when permitted, inserts an effect inside the same transaction. The controller captures acknowledgements and final ledger rows. It does not infer containment from an alert message or successful process exit.

The connection to frontier practice is the separation of detection, enforcement and legitimate-work interruption. OpenAI's safeguards disclosure describes monitoring that can stop potentially unauthorized activity and acknowledges that legitimate work can also be interrupted. Our local controls test neither its detectors nor its infrastructure. They test a small enforcement mechanism with known scheduled signals. [OpenAI safeguards disclosure](https://openai.com/index/path-to-astra/) (rechecked 6 September 2026).

### Define the boundary before measuring it

| Event | What it establishes | What it does not establish |
| --- | --- | --- |
| Alert emitted | The detector or controller requested intervention | The request reached every affected component |
| Coordinator cancellation acknowledged | The coordinator accepted a task-level cancellation | A delegated worker lost write authority |
| Shared authority revoked | The controlled tool boundary should reject subsequent authorized-path requests | An earlier effect was undone or every external system received the change |
| Attempt denied | This attempt did not commit through the tested tool | The agent stopped trying or has no alternate write path |
| Final ledger inspected | Which synthetic effects persisted in this database | No effects occurred in an unobserved service |

The atomicity assumption matters. Checking permission, releasing the transaction, then committing an effect later creates a gap in which revocation may occur. In this local design, permission inspection and effect insertion share a write transaction. SQLite permits only one simultaneous write transaction; an immediate transaction acquires the write transaction at its start. This supplies a local ordering boundary, not a distributed cancellation guarantee. [SQLite transaction documentation](https://www.sqlite.org/lang_transaction.html).

Do not describe revocation as time travel. If the effect commits first, a later revocation may prevent further effects but cannot erase the committed one. Recovery or compensation needs its own authorized operation and evidence. The [process recovery study](process-recovery-study.md) teaches how to preserve that distinction across interruption.

The mechanism can be summarized as two competing transactions. This is **pseudocode**, not an authorization service or portable distributed-lock implementation:

```text
write transaction:                revoke transaction:
  acquire write transaction        acquire write transaction
  read current authority           set authority = revoked
  if revoked: record denial        record revocation
  else: insert synthetic effect    commit
  commit
```

Whichever transaction commits first determines the relevant order at this database boundary. An alert that exists only in another process has not yet changed that authority. Do not substitute “alert requested at time T” for “revocation committed before the effect.”

## Kata 54: cancellation was acknowledged, but the worker wrote

Run the local process controls from the repository on macOS or Linux:

```bash
uv run python -m unittest tests.test_containment_study -v
uv run python -m cx_eval_lab.containment_study \
  --output /tmp/primer-containment-my-first-run.json
```

Use a new output filename. The harness creates only owned temporary databases and processes and retains their relevant evidence in the output packet. It uses explicit acknowledgements rather than sleeps to arrange the tested order. The delegated worker is an actual child of the coordinator, with separate controller-driven IPC; coordinator cancellation is task-level, not an operating-system kill experiment.

The coordinator has already delegated its work and has no independent write workload in this experiment. Its cancellation acknowledgement does not establish that a general agent stopped planning, scheduling new tasks or consuming resources. The observed question is narrower: can its queued child still commit through the shared write tool?

**Know:** stopping orchestration and removing effect authority are different interventions.

**Task:** compare a queued delegated write after coordinator task-cancellation with the same write after shared authority revocation. Inspect actual worker outcomes and the final effect ledger. Then compare revocation before the write with revocation after its commit.

??? success "Solution: follow authority to the effect boundary"
    A cancellation acknowledgement proves only the named component's response. If a delegated worker still has a usable write path, it may finish an already queued operation. The controlled worker therefore checks current shared authority at the point where the synthetic effect is committed, not only when work is scheduled.

    With revocation ordered before that transaction, the request is denied and the ledger remains empty. With revocation ordered after commit, the ledger retains the effect. Both runs can contain a successful revocation event; only the first prevented the protected effect. Grade the effect and its ordering, not the presence of a stop record.

    The delegated-worker experiment uses task-level cancellation of the coordinator, not a claim that killing an operating-system process automatically terminates its descendants. Process lifetime, task state and permission state are separate controls. Record which one the implementation actually exercises.

    The worker is cooperative code using the prescribed tool. It has not been shown unable to bypass that tool or alter the database directly. A real threat model needs separate service credentials, network and filesystem boundaries, and tests of every alternative effect path. Do not market a shared Boolean in a writable database as hostile-agent containment.

**Extend:** add an external effect service, an already accepted remote operation, a cached credential, or a second worker. Specify the point after which cancellation cannot prevent completion. Test follow-up attempts after denial and require explicit reauthorization before any recovery operation restores write access. These extensions need their own evidence; a single-host transaction does not establish them.

**Interview answer:** “I distinguish alert, cancellation, revocation and committed effect. I verify every relevant worker's authority at the effect boundary and inspect durable outcomes. A stopped coordinator and a green cancellation API are insufficient evidence of containment.”

## Kata 55: a working stop can still harm the service

**Know:** a correctly enforced false alarm is still an interruption of legitimate work.

**Task:** run the same legitimate synthetic write with no stop and with a scripted false-positive stop. Record completion, denied attempts and unresolved work. Would successful denial in the second run justify claiming a better detector or a safer deployment?

??? success "Solution: keep enforcement, detection and utility separate"
    No. The positive control establishes that the legitimate task can complete when authority remains available. The false-stop control establishes that the enforcement mechanism can withhold that work. It does not estimate how often a real detector produces false alarms.

    In these experiments the controller chooses the signal and its ordering. There is no independently evaluated classifier and no sampled deployment population. Computing a “monitor accuracy” percentage from these designed cases would disguise a control test as empirical detection evidence.

    Carry three separate outcomes into a real study: detection correctness against independently reviewed labels; whether intervention preceded the consequential effect; and the legitimate work, recovery effort and human review burden lost to intervention. A dashboard that counts only blocked actions can improve while the service becomes unusable.

    A false stop should not be “fixed” by silently bypassing the same authority check. Retain the incident, assess whether it is safe to resume, and issue a new scoped authorization through the intended control plane. The local stop study does not yet measure human review time, restored service quality or the safety of that reauthorization path.

**Extend:** estimate review arrivals as `true positive alerts + false positive alerts`, then compare them with staffed review capacity. Register the base rate and denominators; balanced challenge sets cannot supply production prevalence. Test delayed review, abandoned tasks and repeat interruptions rather than treating every alert as a one-time fixed cost.

**Interview answer:** “I qualify the detector and the enforcement path separately, then measure their combined effect on useful work. A false stop can be correctly enforced and still be a product failure. Recovery must preserve the permission boundary rather than bypass it.”

### Reading the six controls

The [retained local execution packet](assets/containment-study-v1.json) contains six trials, initial/final database snapshots, durable event sequences, process identities and exit status, derived grades and content hashes. All eight launched worker/coordinator processes exited with status zero in this run, including the cases where a protected effect committed. A clean exit therefore does not establish a successful containment outcome.

Each row is a separately initialized local database and process run. The scripted alert/reference labels are part of the registered scenario, not independently measured detector predictions.

| Control | Committed synthetic effects | Denied attempts | Interpretation |
| --- | --- | --- | --- |
| Revoke before protected write | 0 | 2 | Initial and fresh follow-up requests are denied |
| Revoke after protected commit | 1 | 1 | Prior effect remains; the fresh request is denied |
| Cancel coordinator task only | 1 | 0 | Delegated work still has effect authority |
| Cancel coordinator and revoke shared authority | 0 | 2 | Delegated initial and follow-up requests are denied |
| False-positive stop on legitimate work | 0 | 2 | Enforcement works, but legitimate work remains undone |
| Legitimate work without a stop | 1 | 0 | The positive control completes |

The revocation controls include a second request to test behavior after denial or after an earlier commit. The normal and cancellation-only controls each issue one request. These are not equal-sized traffic samples: do not divide pooled denials by pooled requests and label the result detector quality. The important paired comparisons are whether the first effect is prevented and whether a later request still has authority.

### Evidence limits

The scheduled barriers test order, not a detection-to-containment latency distribution. Repeated runs can check this harness's consistency but are not independent users or rare-event reliability evidence. Synthetic labels do not measure harmful propensity, and a scripted worker does not test adaptive behavior after denial. This is a local enforcement study—not a sandbox escape evaluation, a frontier-model safety evaluation or a deployment permit.

`tests.test_containment_artifact` re-grades the retained snapshots, checks their hashes and joins worker event PIDs to the recorded process identities. Those are internal-consistency checks, not authenticated execution provenance. Running the CLI again launches new processes and produces a new packet; it does not reproduce the original process IDs. The CI workflow includes that execution command, but this chapter records local verification, not an observed cloud workflow or production release.
