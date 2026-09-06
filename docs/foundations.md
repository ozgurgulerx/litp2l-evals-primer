# Foundations

## Why LLM applications need control systems

Large language models (LLMs) are probabilistic AI models. They are useful when written or spoken language needs to be processed or generated. They are also useful for tasks with a large solution space, where the right action or tool depends on the current context and state.

This flexibility creates two engineering requirements:

1. Put a **harness** around the model to constrain and contain its behavior. The harness owns permissions, tool access, input and output validation, execution limits, and other deterministic controls.
2. Build an **evaluation system** that measures performance before and after deployment. Offline evidence gates CI/CD; live evidence decides whether a canary should expand, hold, or roll back.

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

An eval is a **decision contract** that defines acceptable performance for a specific use case: the test cases, graders, metrics, critical slices, and required thresholds.

It turns measured behavior into a decision: ship, hold, constrain, expand, or roll back.

That contract connects evaluation to the release process:

- **Pull request:** Run fast deterministic checks on every change.
- **Pre-release:** Run broader model-graded, human-calibrated, and end-to-end suites.
- **Production:** Use canaries, monitoring, sampled traces, and business outcomes to verify that offline results transfer to real traffic.

A candidate must meet its quality, safety, latency, and cost thresholds without regressing a critical customer or risk slice. The release gate reads these thresholds as independent rules. It does not blend them into one average where a quality gain can hide a security failure.

When the gates pass, increase exposure gradually across users and traffic. A new workflow, language, or customer segment is a new use case or slice and needs its own cases, criteria, and thresholds. When a gate fails, block or roll back the release, inspect the traces, perform a post-mortem, and promote the failure into a permanent regression case.

**Evals turn probabilistic model behavior into controlled engineering decisions.**

!!! success "The running example is now executable"
    We use one CX agent throughout the primer. Its first slice handles five refund situations in a resettable mock world: an ordinary eligible refund, a high-value refund requiring approval, an ineligible request, a timeout after payment commit, and a Turkish prompt-injection attempt. A safe reference implementation passes; known-bad implementations prove that the graders can catch policy bypass and duplicate refunds. See [Part II: The CX Eval Lab](build-the-system.md).

The example starts deliberately small. We will add stateful conversations, retrieval, broader support workflows, model judges, and production controls only when the product has a reason to need them. The previous suite remains in place as the agent grows, so new capability cannot silently erase old guarantees.

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

## From evidence to a release gate

The runner and the gate have different jobs.

The **eval runner measures**. It runs versioned cases against the candidate and the current production baseline, then records quality, slice results, traces, latency, and cost. The **release gate decides**. It reads that evidence against a policy agreed before the run and returns an action such as block, constrain, canary, or expand.

A runtime guardrail is separate again. It checks permissions, approvals, schemas, and budgets on each request. The release gate verifies that those controls work across the test set; it does not replace them.

### One decision, several independent rules

A release decision is a vector of named constraints:

`[hard invariants, non-inferiority, superiority, slice floors, latency, cost]`

| Rule | What it asks | CX-agent example |
| --- | --- | --- |
| **Hard invariant** | Did anything happen that is unacceptable even once? | Zero unauthorized or duplicate refunds. |
| **Non-inferiority** | Did the candidate become worse than production by more than the agreed margin? | No protected language may lose more than 1 percentage point of task success. |
| **Superiority** | Does the evidence support the improvement being claimed? | A release sold as a quality upgrade must show a meaningful task-success gain, not a small movement inside normal eval noise. |
| **Slice floor** | Does each important population meet its own minimum bar? | Turkish refund requests must pass their floor even when the global average improves. |
| **Operational bound** | Does the system still fit its latency, cost, reliability, and capacity budgets? | p95 model-and-tool latency stays below 3 seconds and cost stays below the approved amount per successful resolution. |

A candidate can pass four rules and fail the fifth. If that fifth rule is blocking, the release does not proceed. The metrics keep their own meaning rather than compensating for one another.

### Improvement depends on the reason for the change

Each release should prove the benefit used to justify the change. Quality improvement is not always that benefit.

| Change | What should improve | What should be protected |
| --- | --- | --- |
| Model or prompt upgrade | The quality metric named in the proposal | Safety, protected slices, latency, and cost |
| Cost optimization | Cost per successful task | Quality within its non-inferiority margin |
| Latency optimization | The relevant latency percentile | Quality and safety |
| Security patch | The security control or hard invariant | Existing behavior within its allowed margin |
| New language or workflow | Acceptance on the new slice | Existing slices and operational budgets |

This avoids a common mistake: demanding that every number rise on every release. A cheaper candidate can be the better candidate if quality holds. A security fix does not need to invent a quality gain. A change claiming better answers, however, should provide evidence that the answers really improved.

### Where the thresholds come from

Set the thresholds before running the evaluation. Start with the product promise, the cost of a wrong decision, and the operating limits of the service.

For latency, work backwards from the user journey. If a CX response must complete within 5 seconds at p95, and networking, retrieval, and application work already consume 2 seconds, the model-and-tool path has 3 seconds left:

`5 seconds total - 2 seconds fixed work = 3 seconds for the model and tools`

For cost, start with the value or avoided cost of a successful task. Suppose a human-assisted resolution costs $4, the business wants to retain at least $3 of savings, and the rest of the automated stack costs $0.20. That leaves $0.80 for the model and tool path:

`$4.00 avoided cost - $3.00 required saving - $0.20 other costs = $0.80`

Measure cost per **successful** task, including retries, tool calls, judge calls, and failed attempts. Cost per request can look healthy while failures quietly make each completed task expensive.

A non-inferiority margin is the largest loss the product and risk owners are prepared to accept. A superiority threshold is the smallest gain worth the cost and risk of changing production. Statistics tell us whether the observed result clears those bars; they do not decide what the business should tolerate.

### Worked example: a CX agent release

| Metric | Production | Candidate | Gate rule | Result |
| --- | ---: | ---: | --- | --- |
| Unauthorized actions | 0 | 0 | Must remain zero | **Pass** |
| Task success | 82.0% | 82.3% | Quality claim requires at least a 2-point gain | **Fail** |
| Turkish task success | 78.0% | 77.5% | Must not fall by more than 1 point | **Pass** |
| p95 model-and-tool latency | 2.1 s | 4.2 s | Must remain below 3 s | **Fail** |
| Cost per successful resolution | $0.60 | $0.95 | Must remain at or below $0.80 | **Fail** |

The candidate moves task success by 0.3 percentage points but doubles latency and breaks the cost budget. It has not earned a release. The small quality movement cannot pay for the failed operational rules.

### Where the gate runs

The same decision policy can be mounted at two points:

1. **Before deployment:** A CI job runs the offline suite, compares candidate and baseline, writes a report, and applies the release policy. A blocking verdict makes the job fail. In GitHub, that job becomes a required status check on the protected branch.
2. **During rollout:** A small canary receives real traffic. The promotion gate reads live quality and service-level indicators over a predefined window, then expands, holds, constrains, or rolls back the release.

<figure class="release-gate-diagram">
  <img
    src="../assets/generated/release-gate-control-loop.png"
    alt="Evaluation cases and model candidates flow through measurement and several independent release constraints, then into a production canary that can expand or roll back."
  >
  <ol class="release-gate-stages" aria-label="Release-gate flow">
    <li>
      <strong>Evaluation inputs</strong>
      <span>Cases, candidate, baseline, and pinned graders</span>
    </li>
    <li>
      <strong>Eval runner</strong>
      <span>Measures the candidate against the baseline</span>
    </li>
    <li>
      <strong>Evidence</strong>
      <span><code>report.json</code> and <code>gate-policy.json</code></span>
    </li>
    <li>
      <strong>Release gate</strong>
      <span>Block, constrain, or start a canary</span>
    </li>
    <li>
      <strong>Production canary</strong>
      <span>Observe a small share of live traffic</span>
    </li>
    <li>
      <strong>Promotion gate</strong>
      <span>Expand, hold, or roll back</span>
    </li>
  </ol>
  <figcaption>
    The runner produces evidence. The release gate applies every constraint, and live canary evidence determines whether exposure expands or rolls back.
  </figcaption>
</figure>

A small implementation usually has four artifacts:

- `cases.jsonl`: versioned inputs, expected outcomes, and slice labels.
- `report.json`: candidate and baseline measurements produced by the runner.
- `gate-policy.json`: margins, floors, hard vetoes, and operational budgets.
- `gate.py`: a deterministic policy evaluator that prints the reasons and exits with a non-zero status when a blocking rule fails.

With those four artifacts in place, the GitHub Actions wiring can stay simple. In the first CX lab slice, one command runs the cases and applies the policy. A later production version can split measurement and policy into separate jobs while preserving the same evidence contract:

```yaml
name: Eval release gate

on: pull_request

jobs:
  eval-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
      - name: Run the deterministic eval and apply the release policy
        run: uv run python -m cx_eval_lab eval --agent reference --output report.json
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: eval-report
          path: report.json
```

The final enforcement step is repository configuration: mark `eval-gate` as a required status check so a failed job blocks the merge. GitHub documents this under [protected branches and required status checks](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches). Google SRE's [canarying guidance](https://sre.google/workbook/canarying-releases/) covers the second mounting point, where production evidence decides whether exposure should increase.

**Evals measure behavior. Release gates turn that evidence into exposure decisions. Runtime controls enforce permissions and safety limits on every request.**

## Canonical vocabulary

| Term | Definition | CX example |
| --- | --- | --- |
| Product promise | User-visible behavior the system is accountable for | Resolve eligible refunds without unauthorized or duplicate transactions |
| Evaluation contract | Observable criteria, evidence, slices, and decision rules for one promise | State, policy, trajectory, quality, latency, and cost requirements |
| Task | Reusable specification of a behavior to exercise | Handle a refund request under policy-v3 |
| Case | One concrete scenario and initial state | Turkish request after a timeout that committed |
| Trial | One execution of a case under a pinned configuration and seed | Case `refund-tr-07`, seed 17, candidate rc4 |
| Trace | Recorded sequence of relevant model, retrieval, tool, and state events | Verify → policy → refund timeout → inspect |
| Outcome | Externally verified terminal result | Exactly one refund transaction exists |
| Grader | Versioned procedure that judges permitted evidence | `duplicate-refund-v2` reads ledger state |
| Metric | Summary computed from grader or operational results | Verified success rate with numerator and denominator |
| Slice | Named subset with a reason, owner, and denominator | `language:tr AND fault:timeout-after-commit` |
| Experiment | Controlled comparison of systems on a versioned protocol | rc4 versus shipping-v3 on acceptance-v2 |
| Gate | Deterministic policy mapping evidence to exposure | Block on any unauthorized action |
| Guardrail | Runtime control applied to an individual request | Server rejects refund before identity verification |
| Benchmark | Reusable task collection and protocol for a defined construct | A browsing suite or internal agent-task set |

The terms describe different objects. A gate does not measure; a metric does not decide; a guardrail does not prove the system works; one trial is not a dataset.

## Evaluation purposes beyond one grid cell

The earlier three-axis grid is a teaching entry point. Real programmes use more than capability and regression purposes:

| Purpose | Decision |
| --- | --- |
| Exploration | What can this system do, and where does it fail? |
| Optimization | Which intervention improves the registered objective? |
| Regression | Did a protected behavior break? |
| Qualification | Is a grader, simulator, tool, or harness trustworthy enough for a role? |
| Acceptance | Does the complete candidate meet an independently owned release contract? |
| Diagnostic | Which component caused the observed failure? |
| Monitoring | Is live behavior still inside the operating contract? |
| Research | What measurement method or causal hypothesis does the evidence support? |

Always name lifecycle, purpose, level, and authority. “Online trajectory diagnostic” conveys far more than “agent eval.”

## Separate specification, prevention, measurement, and decision

Consider unauthorized refunds:

1. **Specification:** identity and eligibility must precede payment.
2. **Prevention:** the server rejects unauthorized writes.
3. **Measurement:** cases and graders verify attempts and final state.
4. **Decision:** any observed violation blocks the release.
5. **Learning:** a new attack becomes a reviewed regression case.

None substitutes for the others. A runtime control can contain a model mistake but still indicate poor behavior; an offline eval can find a risk but cannot stop a live tool call.

## Start from failure cost

| Error | Consequence | Measurement response |
| --- | --- | --- |
| Slightly verbose explanation | Small interaction cost | Diagnostic or soft quality threshold |
| Incorrect bank-arrival promise | Customer misinformation | Groundedness floor and correction workflow |
| Unnecessary human escalation | Operating cost and delay | Escalation and false-refusal metric |
| Unauthorized refund | Financial and control failure | Deterministic prevention plus hard release invariant |
| Duplicate refund | Financial loss and reconciliation burden | Idempotency control, state grader, immediate rollback trigger |

Expected value can prioritize ordinary work. It should not automatically turn irreversible or regulated failures into compensable averages.

## Measurement validity

Before trusting a result ask:

- **Construct:** does the evaluation measure the named product behavior?
- **Internal:** were candidate and baseline compared under controlled conditions?
- **External:** does the sample represent the deployment population and environment?
- **Reliability:** do repeated measurements remain stable enough for the decision?
- **Predictive:** did offline evidence forecast canary and production outcomes?

A precise score on the wrong construct remains wrong.

## Evidence hierarchy

Use the cheapest strong evidence available, then combine layers where needed:

1. Schema, type, and invariant checks.
2. Executable state and outcome tests.
3. Reference-based comparisons.
4. Behavioral and metamorphic relations.
5. Qualified model judges.
6. Structured human evaluation.
7. Controlled online experiments and verified business outcomes.

The order is not a universal ranking. Human evidence defines many semantic constructs; executable state is stronger for whether money moved.

## Reading the earlier release table correctly

The five-row release table above is an **illustrative decision-vector example**, not a statistically complete experiment. It omits case counts, pairing, and intervals to show independent rules. In a real report:

- `0 unauthorized actions` becomes `0 observed in n named trials`, not “proved safe”;
- the 78.0% to 77.5% Turkish movement is not automatically a non-inferiority pass without a paired estimate and uncertainty against the margin;
- latency must be measured end to end under a registered load; percentile components should not be added unless the budget decomposition is explicitly fixed;
- every price and cost profile must be versioned.

Chapter 3 supplies the missing statistical interpretation.

## Artifact: evaluation contract

```yaml
contract_id: refund-resolution-v1
product_promise: resolve permitted refunds accurately and safely
population:
  workflows: [refund]
  languages: [en, tr]
  policy: refund-policy-v3
units:
  case: initial world plus customer request
  trial: one reset execution
  outcome: verified ledger and escalation state
surfaces:
  outcome: exactly the permitted final state
  policy: no unauthorized or duplicate effect
  trajectory: required checks precede writes
  grounding: explanation follows policy and state evidence
  conversation: clear next step across the thread
  efficiency: bounded turns, calls, tokens, and retries
  operations: latency, cost, error, and trace budgets
gates:
  hard:
    unauthorized_actions: 0
    duplicate_transactions: 0
  quality:
    comparison: paired_non_inferiority
    margin: product-owned
  rollout: [offline, shadow, canary, wider_release]
owners:
  product: cx-domain-owner
  measurement: evaluation-owner
  release: release-owner
```

The values are a synthetic template. Real margins and owners must be approved before results are seen.

## Failure modes

| Failure mode | What it hides | Repair |
| --- | --- | --- |
| “We have evals” | No decision, population, or authority | Write the evaluation contract |
| Model-only target | Tools and environment disappear | Define the complete system under test |
| One aggregate score | Safety or slice regressions compensate | Preserve independent surfaces and rules |
| Metric before promise | Easy measurement becomes the goal | Start with user outcome and failure cost |
| Guardrail called an eval | Runtime containment is mistaken for evidence | Test the guardrail across cases and mutants |
| One successful demo | Stochastic reliability is unknown | Define trials, repeats, and sampling |
| Offline-only programme | Traffic and drift remain invisible | Add shadow, canary, monitoring, and learning |
| Threshold chosen after results | Desired candidate determines policy | Pre-register margins and exceptions |

## Exercise: turn a vague goal into a contract

Vague goal: “Make the support bot better.” Write a contract for a release that claims lower cost without worse customer resolution.

??? success "Answer outline"
    Define the target population and verified resolution outcome; compare candidate and shipping baseline on paired cases; choose a product-owned non-inferiority margin; measure cost per verified success including retries; preserve hard authorization, privacy, and duplicate-action invariants; pre-register language/workflow slice floors; record model, prompt, tools, data, graders, policy, and price versions; and allow exposure to move only from offline evidence to shadow/canary if all independent rules pass. The release may claim lower measured cost, not general quality improvement, unless superiority is separately demonstrated.

## Worked checkpoint: seven surfaces, one failed refund conversation

The customer says, “Refund the blue backpack I bought yesterday—not the one from last week.” The mock session has verified identity. Both orders belong to that customer; only yesterday's order is the intended target. The agent selects last week's order, creates one refund, and replies, “Your money has arrived.” The payment ledger records an accepted refund instruction, not bank settlement. This is a **constructed reasoning example**, not an additional recorded trial.

Before reading the solution, write a verdict for each surface. Do not infer missing measurements, and do not turn one successful API response into successful customer resolution.

| Surface | Evidence needed | Verdict for the supplied facts |
| --- | --- | --- |
| Outcome | Intended target, final ledger for both orders, permitted amount and currency | Fail: the requested order was not refunded and another order was changed. |
| Policy | Customer binding, eligibility, required approval, authorization scope and duplicate ledger effects | Customer ownership and one transaction are supported. Eligibility and approval compliance are unknown from this description. Backend access permission does not establish customer intent. |
| Trajectory / tool use | Model-visible candidates, argument values, reads, checks and write ordering | Wrong-object argument selection fails. Whether all mandatory checks preceded the write requires the actual trace. |
| Grounding / factuality | Exact customer message and authoritative transaction/settlement evidence | Fail: “money has arrived” exceeds the supplied evidence. The correct outcome enum would not repair this sentence. |
| Conversation | Full request, corrections, clarification turns and customer-facing next step | Fail on respecting the explicit target constraint. The final message also gives an unsupported resolution; politeness cannot compensate. |
| Efficiency | Turns, tool calls, retries, token usage and verified successes | Unmeasured. A short conversation is not evidence of efficient resolution; a failed run still consumes resources. |
| Operations | Timing, provider/tool errors, measured prices, trace completeness and environment | Unmeasured. A successful write does not establish latency or cost compliance. |

These are the same seven surfaces used in the contract above. Different names such as “tool correctness” and “trajectory,” or “factuality” and “grounding,” describe views of the same checks here, not extra mandatory taxonomies. The four planes describe ownership and lifecycle; the three axes describe where a measurement belongs. Start with this seven-row evidence table, then use the other maps when they answer a specific question.

### Micro-exercise: choose the repair, not just the metric

Propose one runtime prevention and one evaluation check for each observed failure. Then explain why neither an authorization test nor a schema validator is sufficient.

??? success "Worked solution"
    **Wrong object:** resolve the customer's description against candidate records and bind the chosen object to the request before committing. Ask a targeted clarification if the description remains ambiguous; do not require needless clarification when it is already resolvable. The backend still verifies ownership and write permissions independently. Evaluate final state across all candidate objects, not only the expected object: otherwise an unintended extra refund can disappear from the score.

    **False settlement claim:** expose distinct states such as instruction accepted, processing and settlement confirmed. For deterministic wording, require the exact factual prerequisites. For free-form wording, assess the claim against retained current evidence using a qualified semantic stage or independent review. An allowed string or a valid enum does not establish truth.

    **Missing evidence:** retain the original customer request, candidate records shown to the agent, ordered tool events, complete output and final state, plus usage and timing provenance. Missing evidence produces an unknown or unqualified result according to the registered contract; it must not silently count as a pass.

    **Decision:** this trace fails the stated task contract. Do not promote it because other dimensions look good. Conversely, one failed trace does not estimate the population failure rate. A registered hard-stop rule may block release on this event; a reliability claim still requires an appropriate sample and uncertainty treatment.

### Dataset improvement: keep the incident and test the boundary

Create one minimized regression with both owned orders, the disambiguating customer phrase and the expected ledgers. For this constructed scenario, label its provenance as synthetic; no observed incident or original execution trace exists. When applying the exercise to a real failure, link the case to the reviewed incident and preserve its raw evidence separately under appropriate access controls. Add boundary variants: reversed candidate order, a correction before commitment, an actually ambiguous date, an unauthorized lookalike order and a refund instruction whose settlement is still pending.

Do not claim that six variants are six independent customers. Group related variants for splitting and uncertainty analysis. Put the revealed example into development/regression use; evaluate generalization on separately sourced, unseen ambiguity cases. If it changes the judge rubric, requalify that judge on independent calibration data rather than grading its own newly memorized examples.

For a deliberately small arithmetic example, suppose two attempts cost 0.04 and 0.06 currency units, with only the second independently verified as successful. Observed cost per verified success is `(0.04 + 0.06) / 1 = 0.10`, not 0.06. If neither succeeds, the denominator is zero: report zero verified successes and total cost, not a misleading finite cost-per-success value. This arithmetic is illustrative, not a measured price or a population estimate.

### Interview checkpoint and executable follow-through

**Prompt:** “All API calls returned success and the response schema passed. Why would you block this candidate?”

**Answer criteria:** distinguish API success from intended final state; wrong-but-authorized from unauthorized actions; settlement evidence from transaction acceptance; unknown measurements from passes; a regression finding from a population reliability estimate. Name one retained artifact and one independently checked outcome for each claim. A strong answer also explains how the incident improves the dataset without contaminating final acceptance evidence.

Now run [Kata 01](micro-katas.md#kata-01-a-trusted-sentence-that-lies) for explanation prerequisites, [Kata 04](micro-katas.md#kata-04-recompute-a-grade-not-just-an-average) for retained evidence and [Order Resolution Study](order-resolution-study.md) for competing owned objects. These are separate implemented exercises; they do not yet constitute one integrated, live-model-qualified experiment. Continue with [Dataset Design](dataset-design.md) to turn the boundary variants into a controlled dataset lifecycle.

## Verification checklist

- [ ] Product promise and prohibited outcomes are observable.
- [ ] System, environment, harness, cases, and trials are distinct.
- [ ] Lifecycle, purpose, level, and authority are named.
- [ ] All seven surfaces have evidence or an explicit gap.
- [ ] Guardrails, graders, metrics, and gates have separate jobs.
- [ ] Thresholds follow product consequences and are pre-registered.
- [ ] Illustrative numbers are not presented as empirical claims.
- [ ] The learning loop can change specifications and regression coverage.
