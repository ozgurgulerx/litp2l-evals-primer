# Source Coverage Ledger

This ledger prevents the book from becoming a selective summary. It maps every substantive theme in the supplied research corpus to its teaching home, supporting example, and inspectable artifact.

!!! important "What coverage means"
    A theme is not covered because its name appears once. Coverage requires an explanation, assumptions or limitations, a worked or counterexample, and an artifact or exercise where the topic permits one. Executable claims additionally require running-system evidence.

## Source inventory

| Research source | Primary contribution | Canonical treatment |
| --- | --- | --- |
| Best GitHub Repositories for LLM Evaluation in 2026 | Tool categories, quick starts, licensing, portability, model/application/production layers | System Studies, Benchmark Reproducibility, Courses |
| LLM and AI Evaluation Interview Question Bank | Thirteen-topic evaluation taxonomy, evidence hierarchy, benchmark map, senior whiteboards | All Part I chapters, Interview & Design Drills, and exercises |
| LLM Evaluation Around OpenAI Deep Research | Research-agent capability, browsing benchmarks, safety, source authority, temporal fragility, validity | RAG & Research Evals, Robustness, Benchmark Reproducibility |
| Best Courses and YouTube Resources for Learning LLM Evaluation | Learning routes, eight practical labs, tool practice, human/statistics gaps | Courses, Part II lab, Source Coverage Ledger |
| Eval-Driven AI Programming | Error-analysis-first discipline, evaluator patterns, calibration, experiments, CI/CD, capstone | Dataset Design, Metrics, Judge Calibration, Build Lab |
| Evals, Observability and Release Gates for Production AI Systems | Control loop, telemetry, release policy, canaries, incidents, governance, ownership, economics | Production Evals and Release Gates |
| Evaluating LLM-Based AI Systems: Research Review and Production Blueprint | 2025–26 frontier methods, deployment evidence, extreme-tail reliability, stateful personalization, evaluator meta-evaluation, dynamic audits, monitorability, and realtime modalities | Research-to-Practice Evidence plus linked Part I chapters |

The PDF and DOCX files supplied with the corpus are companion renderings of the same titled research. Their editable Markdown counterparts are the canonical content inputs; format duplication does not create a second curriculum requirement.

## Section-level completeness audit

This second map checks the structure of each source, not only the combined topic taxonomy.

| Source | Source sections retained | Portal treatment |
| --- | --- | --- |
| GitHub repository landscape | Ranked shortlist; comparison dimensions; licence implications; quick starts; specialised tools; layered architecture and next steps | System Studies keeps the complete tool inventory, selection/portability/licensing contracts, worked adapter comparison, and a cross-tool reproduction exercise. Quick-start commands remain in the source because the book teaches contracts rather than duplicating change-prone vendor syntax. |
| Interview question bank | Research taxonomy/counts; ranked core questions; 13-theme bank; evaluation architecture; whiteboards; benchmark/tool map | Thirteen Part I homes plus Interview & Design Drills, answer contract, counterprompts, whiteboards, senior scenarios, and source/reference maps. |
| Deep Research evaluation report | Identification method; first-party corpus; HLE/GAIA/BrowseComp constructs; validity trajectory; live-web fragility; safety; external research network; timeline/source map | RAG & Research Evals, Benchmark Reproducibility, Robustness, primary reference map, temporal manifests, browsing budgets, authority/citation/completeness and indirect-injection controls. |
| Courses and YouTube report | Assessment method; ranked resources; learning paths; eight practical projects; tool stack; requested-framework map; paper spine; human/statistical gaps and next steps | Courses & Learning Paths, Part II project table, System Studies inventory, References, Human Evaluation, Metrics, and judge-calibration exercises. Commercial rankings and stale star counts are not repeated as architectural evidence. |
| Eval-Driven AI Programming | EDD discipline; resource routes; typed cases/results; deterministic/reference/model/human graders; calibration; failure analysis/intervention ladder; observability/CI; curriculum/capstone; first-session 80/20 | Foundations through Release Gates, executable CX lab and mutants, prompt experiment, living dataset, evidence pyramid, courses, and staged roadmap. |
| Evals, Observability and Release Gates | Definitions/KPIs; architecture/tooling; methods/risk profiles/gate template; observability/incidents/governance/ownership/economics; operational cases; roadmap/resources/risks | Foundations, seven surfaces, Production, Release Gates, governance roles, programme economics/roadmap, System Studies case patterns, and synthetic gate/canary artifacts. |
| Evaluating LLM-Based AI Systems | Fourteen 2025–26 developments; five-layer/six-family taxonomy; ranked research map; production blueprint; demo ideas; proposed book structure | Research-to-Practice Evidence supplies the dated maturity rubric and primary-source proof matrix; Metrics covers rare events; Judge covers evaluator qualification and correction; RAG covers stateful personalization; Robustness covers auditing/monitorability; System Studies covers dynamic generation and realtime modalities. Research-only claims remain explicitly non-gating. |

Excluding a volatile ranking, price, star count, or copied quick-start is intentional: the durable concept and verification method are retained, while the live claim must be rechecked at use time.

## Recent capability addendum

The supplied reports remain the coverage baseline. This dated addendum captures capabilities and failure modes that became more prominent after parts of that corpus were written.

| Emerging capability or risk | Portal treatment | Qualification boundary |
| --- | --- | --- |
| Scorer and evaluator isolation | Agent & System Evals separates model-action sandboxing from trusted task/scorer code and fresh scoring state | A sandbox flag does not establish host isolation; review the actual runtime and dependency boundary |
| Evaluation integrity and awareness | Benchmark Reproducibility threat-models answer keys, task identity, harness tampering, denominators, traces, and release identity | Suspicious retrieval can be a security finding without remaining a valid capability score |
| Generated dynamic behavioral evals | System Studies compares Petri, Bloom, and adaptive Giskard multi-turn scenarios | Generated cases amplify discovery; reviewed fixed cases and calibrated graders retain gate authority |
| Adaptive simulated users | Agent & System Evals and System Studies cover changing user turns, shared trace, termination, and non-collusion | Simulator behavior must be checked against held-out human sessions and is not a traffic distribution |
| Tool ownership and lifecycle | System Studies records the 2026 Petri transfer and the AgentKit lifecycle change | Reverify current owners, releases, licenses, data path, and exportability at adoption time |
| Research-to-practice maturity | Research-to-Practice Evidence separates production controls, field evidence, operational tools, and research/benchmarks | A repository or paper is never promoted to “production-proven” without a named operational use and first-party receipt |
| Extreme-tail reliability | Research-to-Practice Evidence and Metrics qualify Five-Nines/CEM importance sampling | Reproduce proposal support, weight stability, and offline-to-live validity before any local gate authority |
| Stateful personalization and memory | Research-to-Practice Evidence and RAG & Research Evals define reset/persist, counter-user, and preference-update arms | Field evidence proves an offline gap, not a universal production evaluation recipe |
| Evaluator-of-evaluators and judge correction | Research-to-Practice Evidence and LLM as a Judge cover AgentRewardBench and bias-corrected reporting | Meta-benchmarks screen candidates; representative local human evidence qualifies them |
| Monitorability and realtime voice | Research-to-Practice Evidence and Robustness/System Studies record disclosed operational use and its limits | Operational use is scoped to the named system, control, and source; it does not establish a complete safety or quality stack |

This addendum does not replace the source-by-source audit. It extends the book while keeping the same rule: an emerging technique becomes operational evidence only after its construct, data, evaluator, environment, and authority are qualified.

## Interview-taxonomy coverage

### Fundamentals & evaluation metrics

| Concepts | Book home | Example/artifact |
| --- | --- | --- |
| Product objective, failure cost, evaluation contract, unit, task/case/trial/trace/outcome | Foundations | CX refund contract and vocabulary table |
| Deterministic, reference, semantic, executable, human, and online evidence | Foundations; Metrics | Evidence hierarchy and metric selection examples |
| BLEU, ROUGE, semantic similarity, task and operational metrics | Metrics | Text-metric limitations and executable-state counterexample |
| Seven independent evaluation surfaces | Agent & System Evals; Build Lab | Timeout-after-commit surface table |

### Benchmarks & contamination

| Concepts | Book home | Example/artifact |
| --- | --- | --- |
| MMLU, BIG-bench, GPQA, GSM8K, HumanEval, SWE-bench, HELM | Benchmark Reproducibility | Benchmark construct map |
| Saturation, prompt sensitivity, answer extraction, harness effects | Benchmark Reproducibility | Four-item two-harness worked example |
| Leakage, semantic overlap, evaluation awareness, private and temporal sets | Dataset Design; Benchmark Reproducibility | Contamination controls and task-detail probes |
| Reproducible manifests and comparable budgets | Benchmark Reproducibility | Run manifest and cross-harness exercise |

### Human evaluation & annotation

| Concepts | Book home | Example/artifact |
| --- | --- | --- |
| Reviewer selection, training, qualification, blinding | Human Evaluation | Annotation protocol |
| Categorical, ordinal, pairwise, ranking, tie, both-unacceptable | Human Evaluation | Response-format design table |
| Inter-rater reliability, disagreement, label noise, ambiguity | Human Evaluation | Eight-conversation pilot |
| Adjudication, protocol drift, sampling bias, power | Human Evaluation; Metrics | Adjudication record and repair exercise |

### LLM-as-a-judge

| Concepts | Book home | Example/artifact |
| --- | --- | --- |
| Pointwise, pairwise, ordinal, reference-guided, claim-level judging | LLM as a Judge | Grounded-status rubric |
| Position, verbosity, identity, self-preference, anchoring, correlated failure | LLM as a Judge | Bias-control suite |
| Human qualification, confusion matrix, false pass/block, abstention | LLM as a Judge | 120-case synthetic calibration report |
| Versioning, shadow comparison, authority and requalification | LLM as a Judge | Criterion/slice authority decision |

### Robustness & adversarial evaluation

| Concepts | Book home | Example/artifact |
| --- | --- | --- |
| Behavioral testing, CheckList-style capabilities, perturbations | Robustness, Safety & Fairness | Six-case transformation suite |
| Metamorphic relations and semantic-preserving validation | Robustness, Safety & Fairness | Paraphrase-invariance code |
| Prompt injection, indirect injection, jailbreaks, adaptive threats | Robustness, Safety & Fairness | Threat manifest and crossed attack suite |
| Long context, missing/stale evidence, tool faults | Robustness; RAG; Agents | Perturbation and timeout examples |

### Bias & fairness

| Concepts | Book home | Example/artifact |
| --- | --- | --- |
| Language, segment, dialect, accessibility, and workflow slices | Robustness, Safety & Fairness | English/Turkish crossed design |
| BBQ, StereoSet, RealToxicityPrompts and benchmark limitations | Robustness; Benchmark Reproducibility | Safety/fairness benchmark map |
| Disparity, support, uncertainty, case mix, intersectionality | Robustness; Metrics | Crossed-slice reporting checklist |
| Privacy and governance of attributes | Robustness; Production | Governed sampling guidance |

### Calibration & uncertainty

| Concepts | Book home | Example/artifact |
| --- | --- | --- |
| Accuracy versus confidence, reliability curves, ECE, Brier, NLL | Metrics | Probability-calibration section |
| Semantic uncertainty and repeated generation | Metrics; Agent Evals | Repeatability and pass@k/pass^k |
| Judge-to-human calibration and threshold sensitivity | LLM as a Judge | Calibration report |
| Selective prediction, abstention, escalation, risk–coverage | LLM as a Judge | Cascade and authority example |
| Simulator and offline-to-production calibration | Agent Evals; Production | Simulator checklist and predictive-validity metrics |

### Prompt evaluation & dataset curation

| Concepts | Book home | Example/artifact |
| --- | --- | --- |
| Error analysis before generic grader creation | Dataset Design | Trace clustering workflow |
| Golden, optimization, regression, adversarial, calibration, sealed, shadow roles | Dataset Design | Canonical seven-role table |
| Synthetic generation, provenance, review, deduplication | Dataset Design | Generation manifest |
| Failure mining, promotion, versioning, supersession, retirement | Dataset Design; Production | Incident-to-regression worked example |
| Dataset health, coverage, freshness, disagreement, contamination | Dataset Design | Health report and coverage ledger |

### Reproducibility & statistics

| Concepts | Book home | Example/artifact |
| --- | --- | --- |
| Estimands, denominators, units, pairing, clustered repeats | Metrics | Experiment estimand and paired bootstrap |
| Confidence intervals, rare events, power, MDE | Metrics | Rule-of-three explanation and design checklist |
| Non-inferiority, superiority, equivalence, inconclusive | Metrics; Release Gates | Candidate/baseline decision example |
| Multiplicity and exploratory versus confirmatory slices | Metrics | Reporting rules |
| Manifests, prompts, extractors, inference settings, exclusions | Benchmark Reproducibility | Reproducibility manifest |

### Tooling, MLOps & continuous evaluation

| Concepts | Book home | Example/artifact |
| --- | --- | --- |
| Promptfoo, DeepEval, Inspect, LM Evaluation Harness, LightEval | System Studies; Benchmark Reproducibility | Tool-selection and cross-harness exercises |
| Phoenix, Langfuse, Opik, MLflow, Weave, OpenTelemetry | System Studies; Production | Portable trace/adapter contract |
| Trace → dataset → evaluator → experiment → gate | Production; Build Lab | Production sample and release packet |
| CI test pyramid and cost-aware cascade | Release Gates; Judge Calibration | Gate policy and course transfer tasks |
| Licensing, self-hosting, maintenance, export, vendor lifecycle | System Studies | Portability checklist |

### RAG, agents & system evaluation

| Concepts | Book home | Example/artifact |
| --- | --- | --- |
| Retrieval recall/precision/ranking and evidence-set completeness | RAG & Research Evals | Versioned retrieval case |
| Answer correctness, groundedness, atomic facts, citations | RAG & Research Evals | Claim-to-evidence table |
| Tool selection/arguments, trajectory, partial orders, state | Agent & System Evals | Timeout trace and trajectory policy |
| Multi-turn memory, commitments, simulator, termination | Agent & System Evals | Session/simulator specification |
| Environment, harness, scaffolding, budgets, recovery | Agent & System Evals; Benchmark Reproducibility | System manifest and mutant validation |

### Interpretability

| Concepts | Book home | Example/artifact |
| --- | --- | --- |
| Explanation plausibility versus causal faithfulness | Robustness, Safety & Fairness | Rationale counterexample |
| Evidence removal, tool-result intervention, counterfactual testing | Robustness; RAG | Causal intervention checklist |
| Limits of free-form rationales and chain-of-thought as evidence | Robustness | Explicit non-privileged-output rule |
| Mechanistic method evaluation: toy ground truth, necessity/sufficiency, causal completeness, predictive intervention, stability, coverage, false discoveries | Robustness, Safety & Fairness; References | Known-mechanism refund example and method-evaluation table |

### Safety, RLHF & alignment

| Concepts | Book home | Example/artifact |
| --- | --- | --- |
| Harmful compliance, false refusal, unsafe partial compliance | Robustness, Safety & Fairness | Crossed benign/adversarial suite |
| HarmBench, JailbreakBench, StrongREJECT, XSTest | Robustness; Benchmark Reproducibility | Benchmark map and caveats |
| Preference data, reward models, Constitutional AI concepts | Robustness, Safety & Fairness | Preference/reward evaluation section |
| Reward overoptimization, Goodhart, specification gaming | Robustness; Agent Evals | Proxy-failure examples |
| Red teaming, permission boundaries, irreversible actions | Robustness; Release Gates | Threat manifest and hard invariants |

## Deep Research evaluation

| Concepts | Book home | Example/artifact |
| --- | --- | --- |
| HLE, GAIA, BrowseComp and different capability constructs | RAG & Research Evals; Benchmark Reproducibility | Research benchmark map |
| HLE dataset revision changes and GAIA answer leakage | RAG & Research Evals | Version-bound comparison and retrieval-integrity controls |
| PersonQA stale references and evaluator correction | RAG & Research Evals | Dated adjudication and scorer-version replay |
| Long-output adaptation; deployed versus capability-eliciting configurations | RAG & Research Evals | Separate report protocol and configuration claims |
| Short-answer reliability versus open-report validity | RAG & Research Evals | Completeness map |
| Source authority, diversity, contradiction, and synthesis | RAG & Research Evals | Source metadata and coverage table |
| Citation entailment, completeness, correctness, and quality | RAG & Research Evals | Atomic-claim grading example |
| Live-web fragility, stale truth, timestamps, content fingerprints | RAG & Research Evals | Research-run manifest |
| Search/test-time compute, pass@k, cost, latency, abstention | RAG; Metrics | Budget and risk–coverage sections |
| Browsing prompt injection and safety | Robustness; RAG | Indirect-injection controls |

## Observability and release gates

| Concepts | Book home | Example/artifact |
| --- | --- | --- |
| Evals, observability, and gates as one closed loop | Foundations; Production; Release Gates | Four planes and incident loop |
| Leading/lagging signals, SLOs, cost per success | Production; Metrics | Signal contract |
| Trace lineage across data, retrieval, model, tools, policy, outcome | Production | Portable trace |
| Shadow, canary, A/B, progressive rollout, hysteresis, rollback | Production; Release Gates | Release manifest |
| Delayed outcomes, drift, sampling, asynchronous judging | Production | Production sample and sampling exercise |
| Incident response and production-to-regression promotion | Production; Dataset Design | Canary regression story |
| Governance, owner roles, privacy, retention, exception handling | Release Gates; Production | Exception record and release packet |
| Economics and evaluator cascade | Metrics; Judge; Release Gates | Cost-aware cascade |

## Course and project practice

The research corpus recommends one evolving lab rather than unrelated notebooks. The book implements that through the CX Eval Lab and these projects:

| Project | Book home | Proof |
| --- | --- | --- |
| Failure-analysis lab | Dataset Design | Actionable taxonomy and promoted cases |
| Golden-dataset lab | Dataset Design | Version, roles, access, health report |
| Human-evaluation lab | Human Evaluation | Protocol, labels, agreement, adjudication |
| Judge-calibration lab | LLM as a Judge | Confusion, slices, abstention, authority |
| RAG evaluation lab | RAG & Research Evals | Retrieval and claim attribution |
| Agent evaluation lab | Agent Evals; Build Lab | Seven-surface trace and state report |
| Red-team lab | Robustness, Safety & Fairness | Threat-linked crossed suite |
| Benchmark reproduction lab | Benchmark Reproducibility; System Studies | Cross-harness manifest and differences |
| Production gate lab | Production; Release Gates | Shadow/canary simulation and incident receipt |

The [Courses & Learning Paths](courses.md) page adds the requested DeepLearning.AI courses and requires an artifact receipt for each.

The [Interview & Design Drills](interview-drills.md) page retains the full thirteen-theme taxonomy and converts the source bank into answer contracts, counterprompts, all eight whiteboard patterns, senior scenarios, and evidence receipts. The source report remains the exhaustive 118-question collection; the portal supplies the structured practice and full teaching chapters rather than duplicating every wording variant.

## Machine-readable synthetic examples

The prose examples also have repository-local JSON companions. They are synthetic teaching data, never production evidence:

| Artifact | Path | What its test proves |
| --- | --- | --- |
| Human annotation pilot | `evals/cx-support/examples/human-annotations-v1.json` | Eight unique items, planned reviewer overlap, and explicit adjudication |
| Judge qualification summary | `evals/cx-support/examples/judge-calibration-v1.json` | The six confusion cells total 120 and the false-pass calculation matches the report |
| Evolving dataset change | `evals/cx-support/examples/dataset-change-v1.1.json` | Version lineage, regression role, incident source, and approval are present |
| RAG atomic claims | `evals/cx-support/examples/rag-claims-v1.json` | Correctness, evidence support, and unverifiable current truth remain separate fields |
| Production canary | `evals/cx-support/examples/production-canary-v1.json` | A duplicate-refund hard invariant forces rollback despite better averages |
| Probability calibration | `evals/cx-support/examples/probability-calibration-v1.json` | Row-level predictions recompute Brier, NLL, binned ECE, and selective thresholds |
| Research-to-practice evidence | `evals/cx-support/examples/practice-evidence-v1.json` | Every maturity claim retains primary sources, an explicit non-claim, local adoption rule, and bounded authority |

`tests/test_book_examples.py` validates these internal relations. The artifacts make the examples inspectable; they do not turn a synthetic study into an empirical result.

## Coverage status and remaining proof

| Layer | Status | What remains before the complete system claim |
| --- | --- | --- |
| Concept explanation | Covered across Part I | Maintain the source audit as the field evolves |
| Bite-sized synthetic examples | Covered in each deep chapter | Maintain visual/readability checks |
| Templates and inspectable artifacts | Covered in Markdown plus seven tested JSON companions | Promote more examples only when they add teaching value |
| Existing deterministic CX slice | Running | Preserve and reverify |
| Human annotation and judge calibration execution | Full design plus consistency-tested synthetic artifacts | Real reviewers/model runs are required before an empirical claim |
| RAG and multi-turn agent execution | Full treatment plus a tested atomic-claim artifact | Extend the running runtime before claiming executable RAG/multi-turn coverage |
| Shadow/canary production control | Full design plus a tested synthetic rollback artifact | Implement a controller before claiming operational deployment capability |

This ledger distinguishes a comprehensive book from a fully implemented production platform. The book can explain and demonstrate synthetic artifacts before every platform feature is executable, but it must state that boundary honestly.

## Maintenance rule

When a new research document is added:

1. extract its substantive topics;
2. map each topic to an existing chapter or create an explicit new home;
3. add an example, counterexample, artifact, or exercise where useful;
4. add primary sources to the claim ledger;
5. record temporal or vendor-lifecycle caveats;
6. update this page before claiming complete coverage.
