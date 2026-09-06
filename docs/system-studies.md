# Comparative system studies

This part studies how other teams, papers, and codebases handle the same evaluation problems we meet in the CX lab. It is not a leaderboard and not a vendor catalogue. Every subject is read through the same CX decision contract, so the comparison leads to an engineering choice.

## The same CX decision contract

Each study starts with the same question:

> Can this approach help us show that the CX agent followed policy, used tools safely, reached the right external state, stayed within operational bounds, and earned a specific exposure decision?

We then compare:

- the unit under test: response, step, trajectory, conversation, or outcome;
- environment and state modelling;
- trace and version contracts;
- deterministic, human, and model-based graders;
- judge or simulator calibration;
- repeated trials and uncertainty;
- dataset separation and contamination controls;
- CI, canary, rollback, and exception handling;
- production sampling and incident-to-regression learning;
- portability, cost, operational burden, and failure modes.

## Adopt, adapt, or reject

Every study ends with three explicit decisions:

| Decision | Meaning |
| --- | --- |
| **Adopt** | The pattern fits the CX contract and can enter the lab directly |
| **Adapt** | The idea is useful but needs a smaller, safer, or provider-neutral implementation |
| **Reject** | The trade-off, dependency, evidence quality, or scope does not fit this system |

The decision must link to a code change, experiment, documented non-goal, or open question. “Interesting” is not an outcome.

## Initial study programme

| Study | Central question | Candidate CX experiment |
| --- | --- | --- |
| OpenAI Agents SDK and agent evals | How much runtime tracing and evaluation plumbing should the SDK own? | Run the same five cases through deterministic and OpenAI runtimes, then normalize both traces |
| Anthropic's agent-eval guidance | How should tasks, trials, graders, transcripts, and outcomes be separated? | Map its vocabulary to one refund case and compare the resulting artifact boundaries |
| τ-bench and τ²-bench | How do benchmarks model policy, tools, state, users, and multi-turn success? | Port one failure pattern into the mock CX world without importing benchmark answers |
| OpenTelemetry GenAI conventions | Which trace fields can be standardized without losing CX-specific meaning? | Export one canonical trace to an OTel-shaped representation and round-trip key evidence |
| Phoenix and AgentEvals | What reusable trace and evaluator abstractions can be delegated to open source? | Implement an optional adapter while keeping the local kernel runnable alone |
| Braintrust and other evaluation platforms | Which experiment, dataset, and comparison services save work, and where does platform coupling begin? | Send one existing report through an adapter and compare reproducibility, authority, and exit paths |
| CX-agent builders | How do support-focused teams define resolution, containment, escalation, and business value? | Reconcile one external outcome definition with our verified-resolution denominator contract |

## Study record template

Each completed study will include:

1. Source versions and review date.
2. The problem the system is trying to solve.
3. Its evaluation object and evidence flow.
4. The strongest design choice and its assumptions.
5. Failure modes, blind spots, and operational cost.
6. A reproducible CX experiment using synthetic data.
7. Results against the existing release policy.
8. The adopt, adapt, or reject decision.
9. Follow-up changes to the primer, lab, or research-question register.

The point is cumulative understanding. A study is complete only when it changes what we can explain, build, measure, or deliberately decline.

## Compare abstractions before products

The research inventory separates five tool jobs:

| Job | Representative systems | What to study |
| --- | --- | --- |
| Model/benchmark execution | LM Evaluation Harness, LightEval, HELM, OpenCompass | Task configuration, prompting, extraction, scoring, reproducibility |
| Application regression | Promptfoo, DeepEval | Dataset-to-candidate matrices, assertions, semantic graders, CI |
| Agent environments | Inspect, agent benchmark harnesses | Tools, state, solvers, trajectories, budgets, sandboxing |
| Trace/experiment platforms | Phoenix, Langfuse, Opik, MLflow, Weave | Instrumentation, datasets, scorers, comparisons, online evaluation |
| Human/data operations | Annotation queues and labeling systems | Reviewer protocol, adjudication, dataset correction, access |

One product can cover several jobs. That does not mean the underlying concepts should be collapsed.

## Portability contract

The local kernel owns:

- case and dataset manifests;
- system, environment, and harness versions;
- normalized traces;
- grader inputs and outputs;
- human and judge calibration reports;
- experiment comparisons;
- release-policy decisions;
- incident-to-case receipts.

An adapter may send these objects to an external platform or translate an external trace back into the local schema. The platform must not become the only place where the evidence can be interpreted.

```python
class EvaluationAdapter:
    def export_cases(self, dataset_manifest): ...
    def normalize_trace(self, provider_trace): ...
    def export_scores(self, case_results): ...
    def import_annotations(self, review_batch): ...
```

Portability checks:

1. Can an experiment be replayed without the hosted UI?
2. Are raw case-level results exportable?
3. Are judge prompts, rubrics, and versions visible?
4. Can traces preserve domain-specific state evidence?
5. Do proprietary metrics have documented semantics?
6. Can the release gate run locally and fail closed?
7. What data, credentials, or payloads leave the boundary?
8. What happens when a product or API is retired?

This matters because platform lifecycles change. Concepts, schemas, and evidence should outlive a particular hosted evaluation surface.

## Worked comparison: the same refund case

Target case: timeout after refund commit. Required evidence:

- exactly one transaction in final state;
- identity and policy checks before the write;
- ledger inspection immediately after ambiguous commit;
- no unsupported claim that funds settled;
- latency and cost recorded.

| Approach | Natural strength | Adaptation needed | Authority kept local |
| --- | --- | --- | --- |
| Promptfoo-style matrix | Provider/prompt comparison and CI assertions | Custom executable state and trajectory adapter | Final-state invariant and release gate |
| DeepEval-style tests | Python test workflow and semantic/agent metrics | Use local world fixture and human-qualified graders | Expected state, policy, and judge authority |
| Inspect-style task | Agent, tools, solver, scorer, and sandbox composition | Normalize its sample/log into CX trace | Product policy and release decision |
| Phoenix/Langfuse/Opik-style platform | Trace inspection, datasets, experiments, annotation | Redact payloads and preserve exportable manifests | Dataset roles, calibration, and gate policy |
| Local kernel | Precise synthetic state, mutants, deterministic gate | Less ready-made visualization and collaboration | Entire evidence contract |

The decision is not “pick the winner.” It is:

- **Adopt** portable trace and experiment ideas.
- **Adapt** external scorer interfaces behind the local grader contract.
- **Reject** any workflow that makes a platform score authoritative without task-specific calibration.

## Worked study: judge adapter

Suppose an external library returns:

```json
{"metric": "answer_relevance", "score": 0.86, "reason": "Relevant and concise"}
```

The local contract requires:

```json
{
  "criterion": "next_step_relevance",
  "label": "pass",
  "evidence": ["response sentence 2", "policy-v3 §4.2"],
  "judge_version": "next-step-v1",
  "qualification_report": "next-step-v1-human-gold-v2",
  "authority": "diagnostic_only"
}
```

The adapter can retain the external score as diagnostic metadata. It cannot infer the local criterion, evidence, qualification, or authority. Those are evaluation-design decisions.

## Operational case patterns

External case studies are most useful as falsifiers of an architecture assumption. Vendor-reported effect sizes remain vendor evidence unless independently reproduced.

### Serving infrastructure can change semantics

[Anthropic’s September 2025 postmortem](https://www.anthropic.com/engineering/a-postmortem-of-three-recent-issues) describes three infrastructure bugs that intermittently degraded model responses. One routing issue initially affected about 0.8% of Sonnet 4 requests and reached 16% in its worst impacted hour after a load-balancing change. Existing benchmarks, safety evals, performance metrics, spot checks, and small canaries did not localize the reports quickly; Anthropic subsequently described more sensitive evaluations, quality evaluation on true production systems, and faster debugging tools.

**Transfer to the CX lab:** treat serving platform, batching/routing, inference configuration, and hardware path as part of the system manifest. Run behavioral canaries through the exact candidate serving path and stratify by it. Healthy HTTP, latency, or offline model scores cannot prove semantic equivalence.

### Execute domain semantics when possible

[OpenAI’s in-house data-agent report](https://openai.com/index/inside-our-in-house-data-agent/) describes curated questions paired with manually authored reference SQL, execution of generated and reference queries, and comparison of both SQL and resulting data rather than string equality. The report frames these evals as continuously run development tests and production canaries.

**Transfer to the CX lab:** two syntactically different plans may be equivalent and two similar-looking plans may change different state. Grade query results, transaction ledgers, permissions, and external outcomes before semantic resemblance.

### Integrated workflows can reduce glue, but the claim needs a boundary

[OpenAI’s AgentKit announcement](https://openai.com/index/introducing-agentkit/) reported a Carlyle customer claim of reduced development time and increased agent accuracy from an integrated evaluation platform. The same page was later updated to say the Agent Builder and Evals products would be wound down in 2026.

**Transfer to the CX lab:** shared datasets, traces, graders, and comparisons can reduce integration work, but a vendor-published customer metric is not a controlled universal result. Product lifecycle changes also validate the portability contract: local manifests, raw results, calibration, and gate policy must outlive the UI.

### Broken measurement can dominate the model score

Across benchmark and application case studies, scaffolding, answer extraction, environment state, permission handling, and graders can produce larger score changes than the model change under discussion.

**Transfer to the CX lab:** every evaluator gets known-good and known-bad tests. When a score moves unexpectedly, replay frozen outputs through old and new evaluator versions before attributing the movement to the candidate.

### Case-study decision record

```yaml
source: anthropic-infrastructure-postmortem-2025-09-17
observed_fact: serving bugs caused intermittent semantic degradation
inference: offline model qualification alone cannot cover serving-path behavior
cx_experiment:
  mutate: routing_or_inference_profile
  hold_fixed: [case, prompt, model_artifact, grader]
  compare: [semantic_outcome, trace_version, latency, error]
decision:
  adopt: exact-serving-path behavioral canary
  adapt: privacy-safe production sampling
  reject: infrastructure SLOs as a semantic-quality proxy
```

The record separates what the source reported from the local inference and the experiment that must test it.

## Dynamic behavioral evaluation

Static cases are necessary for regression and paired comparison, but they do not explore every path through an agent. Recent evaluation systems increasingly generate or adapt multi-turn scenarios around a specified behavior. They are best treated as coverage amplifiers: they discover candidate failures that humans validate and promote into stable datasets.

| Pattern | Evaluation object | Strong use | Main limitation |
| --- | --- | --- | --- |
| [Petri](https://www.anthropic.com/research/petri-open-source-auditing) | An auditor explores many user-specified scenarios through simulated users and tools, followed by multidimensional judging | Broad behavioral auditing and unexpected-failure discovery | Simulator, auditor, tool, and judge artifacts can create or miss behavior |
| [Bloom](https://www.anthropic.com/research/bloom) | One researcher-specified behavior becomes many generated scenarios through understanding, ideation, rollout, and judgment stages | Deeper targeted elicitation and comparative behavioral measurement | Generated suites still need construct, realism, judge, and diversity validation |
| [Giskard dynamic multi-turn tests](https://docs.giskard.ai/oss/checks/tutorials/multi-turn) | A simulated user adapts its next turn to the application response while the full trace remains shared | Stateful application QA for goals that cannot be represented by one prompt | Generated user behavior is not a production-user distribution by default |

Petri and Bloom are complementary rather than interchangeable. Petri is useful for broad hypothesis exploration across many scenarios; Bloom turns one named behavior into a deeper generated evaluation suite and supports configuration such as a seed for reproducibility. As of May 2026, Anthropic reported transferring ongoing Petri development to Meridian Labs, illustrating why tool ownership and lifecycle belong in a dated adoption record.

### Safe promotion loop

```text
named behavior + threat model
          ↓
generated scenarios and adaptive rollouts
          ↓
human review: realism, target behavior, severity, leakage
          ↓
calibrated grading + repeated seeds + baseline comparison
          ↓
novel confirmed failures ──→ fixed regression/adversarial cases
          ↓
stable release suite + production monitoring
```

Before a generated behavioral suite can influence a gate, validate:

- that the target behavior is observable and not merely a plausible rationale;
- scenario realism, difficulty, diversity, and absence of hidden-label leakage;
- simulator fidelity, termination, non-collusion, and tool permissions;
- auditor coverage and whether it steers the system into artificial behavior;
- judge agreement, false-pass/false-block rates, abstention, and slice authority;
- repeated-seed stability, configuration/version capture, and cost;
- novelty against the existing dataset and promotion into human-reviewed fixed cases.

### Bite-sized example

Target behavior: **retrying an irreversible write after an ambiguous timeout**.

1. Generate scenarios that vary transaction type, language, timeout timing, user pressure, and status-tool availability.
2. Let an adaptive simulator insist, “Just retry—it probably failed.”
3. Grade the ledger state, action order, supported user claim, and duplicate side effect independently.
4. Human-review every newly found failure; deduplicate it; add one minimal representative to the adversarial set and one production-confirmed example to regression only when provenance permits.

A generated score alone must not block a release. The gate consumes the qualified grader report and reviewed dataset version, while raw generated cases remain discovery evidence.

## Tool-selection matrix

| Need | First candidate | Why | Do not assume |
| --- | --- | --- | --- |
| Fast polyglot prompt/model CI | Promptfoo | Declarative comparison and red-team workflow | It proves real-world task outcome automatically |
| Python application tests | DeepEval | Test-runner ergonomics and metric interfaces | Built-in thresholds are calibrated for this product |
| Model benchmark reproduction | LM Evaluation Harness or LightEval | Standard task execution and backends | Benchmark score transfers to an agent product |
| Stateful agent evaluation | Inspect or local environment | Task/tool/scorer composition | Default environment matches production |
| Trace-to-dataset loop | Phoenix, Langfuse, Opik, MLflow, or Weave | Experiments, annotations, online samples | Hosted telemetry is a safe source of truth by default |
| RAG diagnostics | RAGAS-style metrics plus local checks | Retrieval/generation decomposition | Model-graded proxies need no human qualification |

Selections must be reverified against current official documentation, licensing, data handling, export support, and maintenance before adoption.

## Licensing and deployment are architecture

“Open source,” “source available,” self-hostable, and hosted SaaS are not interchangeable. Before adoption, record:

- exact repository and license at the reviewed revision;
- whether the desired server, UI, or enterprise feature uses a different license;
- restrictions relevant to redistribution, managed service, or internal modification;
- where prompts, traces, labels, and credentials are processed;
- self-hosting dependencies and operational burden;
- export, backup, deletion, and migration paths;
- maintenance activity and security-response process.

License text and product terms can change. The book therefore teaches a dated verification record rather than copying the research snapshot’s license matrix into a timeless recommendation. Obtain qualified legal review when license interpretation affects a real deployment.

## Full tool inventory from the research corpus

This inventory records what to investigate; it is not a timeless ranking.

| System | Primary abstraction | Best study question |
| --- | --- | --- |
| Promptfoo | Declarative application matrix, assertions, red team, CI | How do Git-native cases and provider comparisons map to the local release gate? |
| DeepEval | Python tests and application/RAG/agent metrics | Which evaluator interfaces improve ergonomics without importing unqualified thresholds? |
| Langfuse | Traces, datasets, experiments, annotations, online evaluation | How does a reviewed production trace become a portable dataset case? |
| Opik | Tracing, experiments, online evaluation, self-hostable workflow | What evidence remains exportable and reproducible outside the platform? |
| Phoenix | OpenTelemetry-oriented tracing, datasets, experiments, evaluators | Can domain-specific state and grader evidence round-trip through its trace model? |
| MLflow GenAI evaluation | Experiment tracking, traces, scorers, production workflow | How do model/application versions join with a local decision manifest? |
| W&B Weave | Tracing, evaluation, datasets, experiment artifacts | Which artifact-lineage patterns transfer without hosted-only dependency? |
| LM Evaluation Harness | Model benchmark task execution and scoring | Which prompt, few-shot, backend, and extractor defaults enter a result? |
| LightEval | Configurable model benchmark execution | Can the same task reproduce per-item scores across two harnesses? |
| HELM | Holistic scenario × metric evaluation and reporting | How does multi-metric transparency inform the seven-surface report? |
| OpenCompass | Large model/dataset configuration ecosystem | What is gained and lost when breadth drives the harness design? |
| LMMS-Eval | Multimodal model evaluation | How must the evidence schema change for image, audio, and video inputs? |
| Inspect AI | Dataset, solver/agent/tools, scorer, sandbox, logs | How does a stateful CX task map into a general agent-eval environment? |
| Giskard | Generated tests, stateful dynamic multi-turn scenarios, agent/RAG checks, vulnerability scanning | How should adaptive generated scenarios be reviewed before entering a gate? |
| Petri | Broad simulated-user/tool behavioral auditing with auditor and judge roles | Which discovered behaviors survive human validation and fixed-case reproduction? |
| Bloom | Targeted behavior-to-scenario generation, rollout, and judgment pipeline | Can a generated suite elicit one named behavior reproducibly across systems? |
| Ragas | RAG metrics and test generation | Which retrieval/generation proxies agree with local human and deterministic evidence? |
| TruLens | Trace evaluation and RAG/agent feedback functions | How does per-span feedback support first-causal-failure localization? |
| AutoEvals | Small scorer library | Can scorers remain composable and independent of orchestration? |
| Label Studio | General human annotation workflows | How do rubric, overlap, adjudication, and exports map to the human-eval protocol? |
| Argilla | Feedback and dataset curation | How are corrections, preferences, and review states preserved in versioned datasets? |
| Microsoft Promptflow | Flow experimentation and evaluation | What migration and ecosystem dependencies affect a new adoption? |
| SWE-bench | Repository issue benchmark and environment | How much measured coding-agent performance belongs to scaffolding and execution? |
| OpenAI simple-evals | Transparent reference benchmark implementations | Which evaluator implementations are useful as readable references rather than a platform dependency? |
| OpenAI Evals / hosted eval surfaces | Historical registry and hosted evaluation workflows | Which concepts remain portable when product surfaces change or retire? |
| BIG-bench | Broad historical task collection | What does an archived or saturated benchmark still contribute to longitudinal study? |
| EvalAI | Challenge and leaderboard hosting | When is challenge infrastructure the real requirement rather than application evaluation? |
| LM-Flow | Training/fine-tuning/inference toolkit with evaluation | Why should a broad model-development toolkit not define application-eval architecture? |

For every tool study, verify the current repository, official documentation, release activity, license, data path, security boundary, and export contract on the review date. Popularity and old star counts stay outside the architectural decision.

## Multimodal extension

The primary CX lab is text-and-tool based, but the framework extends to image, audio, video, and documents. Add modality-specific evidence rather than applying text judges blindly:

- image regions, OCR, visual grounding, and spatial relations;
- speech recognition, speaker turns, latency, and acoustic quality;
- video temporal consistency, scene coverage, and safety;
- document layout, tables, charts, and citation coordinates;
- cross-modal instruction and retrieval attacks.

A future study should port one synthetic damaged-invoice case through LMMS-Eval or a comparable multimodal harness while preserving the same dataset-role, grader-calibration, and release-gate rules.

## Benchmark-study programme

Use small reproductions to learn measurement rather than chase leaderboard coverage:

1. Run one multiple-choice task through LM Evaluation Harness and LightEval with identical rendered prompts.
2. Compare answer extraction and per-item scores.
3. Change one prompt-template choice and observe sensitivity.
4. Run one agent case through local and Inspect-style abstractions.
5. Export one trace to an OTel-shaped representation and round-trip required fields.
6. Send one local experiment to a trace platform, export it, and reproduce the gate locally.

Every study publishes manifests, per-case differences, and adopt/adapt/reject decisions.

## Failure modes in tool studies

| Failure mode | Result | Repair |
| --- | --- | --- |
| Ranking by GitHub stars | Popularity becomes architecture | Compare task fit, evidence, maintenance, licensing, and exit path |
| Quick-start copied as methodology | Tool defaults define the construct | Start with the local evaluation contract |
| Built-in metric trusted | Unknown grader gains authority | Calibrate on human or deterministic evidence |
| Different defaults compared | Harness effect appears as model effect | Freeze rendered prompts, budgets, and scoring |
| Hosted-only evidence | Reproduction fails after migration | Export normalized cases, traces, and scores |
| Vendor demo treated as case study | Marketing result becomes proof | Reproduce a synthetic CX experiment |

## Exercise: select a stack

A Python team needs application regression tests, a stateful agent sandbox, production trace review, and reproducible model benchmarks. It wants one tool for everything.

Design a minimal layered stack and identify the canonical data boundary.

??? success "Answer outline"
    Use the local case/trace/grader/release schemas as the canonical boundary. A Python application test layer such as DeepEval can provide test ergonomics; Inspect or the local mock world can execute stateful agent tasks; a trace platform such as Phoenix, Langfuse, Opik, MLflow, or Weave can support review and production sampling; LM Evaluation Harness or LightEval can own model benchmark reproduction. Add only adapters that provide concrete value. Keep human labels, calibration reports, manifests, and gate decisions exportable and locally interpretable.

## Study completion checklist

- [ ] Official documentation, version, license, and review date are recorded.
- [ ] The tool job and target evaluation object are explicit.
- [ ] One existing synthetic CX case is reproduced.
- [ ] Defaults and hidden assumptions are identified.
- [ ] Data and credential boundaries are reviewed.
- [ ] Per-case evidence can be exported and replayed.
- [ ] External metrics cannot gain unqualified release authority.
- [ ] Adopt, adapt, and reject decisions change an artifact or non-goal.
