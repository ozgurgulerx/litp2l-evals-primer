# Reference library

## Coding-evaluation methodology updates — checked 7 September 2026

- [OpenAI: Separating signal from noise in coding evaluations](https://openai.com/index/separating-signal-from-noise-coding-evaluations/) — July 2026 benchmark-quality audit and changed recommendation; use for task/test validity and independent review, not a blanket replacement-benchmark endorsement.
- [Anthropic: Quantifying infrastructure noise in agentic coding evals](https://www.anthropic.com/engineering/infrastructure-noise) — resource allocation and enforcement as experimental variables.
- [Anthropic: Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) — outcome tests, regression protection and complementary trajectory review. The [local coding study](coding-patch-study.md) implements only a bounded authored-patch exercise.

The primer treats references as part of the evaluation system. A source should tell us more than “where an idea came from.” It should identify the claim it supports, the artifact it changes, how fresh it is, and what would make us revisit it.

## Primary-source rule

Public claims are re-authored from stable primary evidence wherever possible: official documentation, engineering reports, standards, papers, and source repositories. Research reports and private study notes help us find gaps, but they are not copied into the public primer and do not become evidence by themselves.

For every material claim we record:

- the exact claim and its scope;
- the primary source and date checked;
- the chapter and CX artifact it informs;
- whether the statement is documented fact, experimental result, proposal, or inference;
- the owner and review date when freshness matters.

## Claim ledger

The maintained claim ledger will use this shape:

| Field | Purpose |
| --- | --- |
| Claim ID and wording | Prevents a citation from drifting to support a different statement |
| Evidence type | Separates official behavior, empirical evidence, standards, and local design choices |
| Source and checked date | Makes provenance and freshness visible |
| CX artifact | Connects reading to code, data, grader, policy, or experiment |
| Confidence and caveat | Records what the source does not establish |
| Revalidation trigger | Defines when a model, SDK, API, standard, or practice must be checked again |

## Seed reference spine

This is the starting collection, not the finished bibliography.

| Area | Primary reference | What it informs here |
| --- | --- | --- |
| OpenAI agent runtime | [OpenAI Agents SDK for Python](https://openai.github.io/openai-agents-python/) and [Agents SDK quickstart](https://developers.openai.com/api/docs/guides/agents/quickstart) | Agent/runner structure, typed tools, traces, and the optional model-backed runtime |
| OpenAI agent evaluation | [Agent evals](https://developers.openai.com/api/docs/guides/agent-evals) | Reproducible agent-quality measurement and trace-oriented evaluation |
| Anthropic eval design | [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) | Tasks, trials, graders, transcripts, outcomes, and evaluation workflow |
| Anthropic agent design | [Building effective agents](https://www.anthropic.com/research/building-effective-agents) | Choosing workflow complexity and keeping orchestration understandable |
| Long-running agent harnesses | [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) | Checkpoints, progress preservation, restart/resume evaluation, and durable-state limits |
| Multi-agent production architecture | [How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) | Delegation, coordination, shared context, parallel work, synthesis, and matched-budget evaluation |
| Skill evaluation | [OpenAI skill evals](https://developers.openai.com/blog/eval-skills) | Explicit, implicit, competing, stale, and incorrect activation; selection versus execution errors |
| Tool-agent benchmark | [τ-bench](https://arxiv.org/abs/2406.12045) and its [reference implementation](https://github.com/sierra-research/tau-bench) | Stateful tool interaction, policy adherence, and end-state evaluation |
| Multi-turn benchmark | [τ²-bench](https://arxiv.org/abs/2506.07982) | Multi-turn, dual-control interaction and stateful evaluation |
| Knowledge and voice agent benchmarking | [Sierra τ³ and τ-Voice](https://sierra.ai/blog/bench-advancing-agent-benchmarking-to-knowledge-and-voice) | Knowledge-to-action ablations, oracle-context limits, audio timelines, interruptions, and matched text/voice tasks |
| Dynamic broad behavioral auditing | [Anthropic Petri](https://www.anthropic.com/research/petri-open-source-auditing) and its [2026 stewardship update](https://www.anthropic.com/research/donating-open-source-petri) | Simulated users/tools, auditor/judge roles, broad exploration, and lifecycle verification |
| Targeted behavioral suite generation | [Anthropic Bloom](https://www.anthropic.com/research/bloom) | Behavior-to-scenario generation, diverse rollouts, judgment, seeds, and validation limits |
| Adaptive multi-turn application tests | [Giskard multi-turn testing](https://docs.giskard.ai/oss/checks/tutorials/multi-turn) | Dynamic simulated users, shared traces, stateful goals, and simulator caveats |
| LLM judge foundations | [Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena](https://arxiv.org/abs/2306.05685) | Judge agreement, bias, limitations, and the need for calibration |
| Agent benchmark breadth | [AgentBench](https://arxiv.org/abs/2308.03688) | Evaluating agents across interactive environments rather than text alone |
| Trace interoperability | [OpenTelemetry generative AI semantic conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/) | Provider-neutral trace naming and observability boundaries |
| CI enforcement | [GitHub protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches) | Making an eval job a required status check |
| Progressive delivery | [Google SRE: Canarying releases](https://sre.google/workbook/canarying-releases/) | Promotion, hold, and rollback decisions using live evidence |

## How references will grow

New sources enter through a research question or a build decision. They are mapped to one of the nineteen working questions: evaluation units, dataset roles, label hygiene, repeatability, release vectors, offline-to-live validity, harness effects, provider boundaries, evaluator evolution, retrieval, incident promotion, rubric quality, red-teaming, operational bounds, CX outcome definitions, trace localization, multi-turn failure, and overfitting.

## Research spine

The larger study and R/Q collection has been normalized into nineteen public questions. The private question bank remains private; each public answer will be written afresh, supported by primary evidence, and proved with a CX artifact.

| ID | Question the primer must answer | CX proof |
| --- | --- | --- |
| RQ-01 | What is the unit under evaluation? | Grade one run at step, trajectory, conversation, and outcome level |
| RQ-02 | Why do capability, optimisation, regression, adversarial, calibration, sealed, and production-shadow datasets differ? | Versioned manifests, visibility rules, and promotion history |
| RQ-03 | Which facts can code establish, and which need people or calibrated models? | Evaluator-routing table plus known-good and known-bad tests |
| RQ-04 | How do we prevent hidden labels from reaching the agent, simulator, or judge? | Separate agent input and evaluator-only oracle, with leakage tests |
| RQ-05 | How many stochastic trials are enough? | Repeat policy, reliability metrics, and confidence bounds |
| RQ-06 | How does an evidence vector become block, constrain, canary, expand, or rollback? | Versioned policy and reconstructable decision |
| RQ-07 | Do offline evals predict production behavior? | Offline-to-canary predictive-validity report |
| RQ-08 | How much does the harness alter the measured result? | Controlled runtime and resource-limit ablation |
| RQ-09 | What must the product own, and what can a platform provide? | Provider-neutral kernel exercised through two adapters |
| RQ-10 | How does an evaluator change without silently rewriting history? | Shadow comparison, calibration report, and evaluator release record |
| RQ-11 | How do retrieval and answer generation fail independently? | Retrieval-versus-generation diagnostic matrix |
| RQ-12 | How does a production failure become durable regression coverage? | Incident-to-case receipt and coverage-growth metric |
| RQ-13 | What makes a rubric observable and discriminating? | Boundary examples, disagreement review, and rubric tests |
| RQ-14 | How do safety evals test the whole system? | Threat-linked cases for injection, authorization, privacy, unsafe tools, and escalation |
| RQ-15 | How do latency, cost, retries, and tool errors become non-compensable constraints? | Tail-latency, cost-per-success, and gate evidence |
| RQ-16 | How do containment, deflection, verified resolution, adoption, and business value differ? | Explicit denominators and quality-adjusted CX outcomes |
| RQ-17 | How do traces localize the failure and critical-path delay? | Failure taxonomy, parser, and component attribution |
| RQ-18 | What fails only across a session? | Multi-turn, memory, commitment, and perturbation cases |
| RQ-19 | How do criteria, golden cases, prompts, and fixes interact without overfitting? | Criteria-before-prompt experiment with held-out evidence |

A source remains only if it changes the explanation, implementation, experiment, or decision. The library is curated for depth and auditability, not link volume.

## Expanded primary-source map

### Measurement, human evaluation, and judges

| Topic | Primary source | Book use |
| --- | --- | --- |
| Holistic multi-metric evaluation | [HELM](https://arxiv.org/abs/2211.09110) | Scenarios, desiderata, transparency, and limits of one-number evaluation |
| Human pairwise preference | [Chatbot Arena](https://arxiv.org/abs/2403.04132) | Pairwise design, crowdsourced preference, and leaderboard interpretation |
| LLM-judge behavior | [MT-Bench and Chatbot Arena judge study](https://arxiv.org/abs/2306.05685) | Position, verbosity, self-preference, and human comparison |
| Rubric-guided model evaluation | [G-Eval](https://arxiv.org/abs/2303.16634) | Model-based evaluator design and human correlation claims |
| Open rubric evaluator | [Prometheus](https://arxiv.org/abs/2310.08491) | Fine-grained rubric-based grading |
| Selective judge escalation | [Trust or Escalate](https://arxiv.org/abs/2407.18370) | Calibration sets, abstention, coverage, and human escalation |
| Probability calibration | [On Calibration of Modern Neural Networks](https://arxiv.org/abs/1706.04599) | Reliability diagrams, temperature scaling, and calibration error |
| Generative uncertainty | [Semantic Uncertainty](https://arxiv.org/abs/2302.09664) | Meaning-aware uncertainty across generated answers |
| Extreme-tail reliability | [Measuring Five-Nines Reliability](https://arxiv.org/abs/2605.11209) | CEM importance sampling, proposal-support assumptions, estimator efficiency, and the research-to-production boundary |
| Adaptive/IRT evaluation | [Computerized adaptive testing for LLM medical benchmarking](https://www.nature.com/articles/s41746-026-02671-w) and [Can We Trust Item Response Theory for AI Evaluation?](https://arxiv.org/abs/2607.15190) | Cost reduction, calibrated item banks, rank stability, population-regime failures, and non-adaptive safety cores |
| Evaluator meta-evaluation | [AgentRewardBench](https://arxiv.org/abs/2504.08942) | Expert-grounded comparison of rule and LLM evaluators for agent trajectories |
| Corrected judge reporting | [How to Correctly Report LLM-as-a-Judge Evaluations](https://arxiv.org/abs/2511.21140) and [No Free Labels](https://arxiv.org/abs/2503.05061) | Noisy-diagnostic correction, calibration uncertainty, reference quality, and shift assumptions |

### Behavioral testing, safety, fairness, and alignment

| Topic | Primary source | Book use |
| --- | --- | --- |
| Behavioral test design | [CheckList](https://aclanthology.org/2020.acl-main.442/) | Capability, invariance, and directional-expectation tests |
| Automated red teaming | [HarmBench](https://arxiv.org/abs/2402.04249) | Standardized behavior and attack evaluation |
| Jailbreak reproducibility | [JailbreakBench](https://arxiv.org/abs/2404.01318) | Threat, attack, defense, and evaluator separation |
| Over-refusal | [XSTest](https://arxiv.org/abs/2308.01263) | Benign near-neighbors and exaggerated safety behavior |
| Bias in ambiguous QA | [BBQ](https://aclanthology.org/2022.findings-acl.165/) | Ambiguous/disambiguated bias cases and benchmark limits |
| Stereotype measurement | [StereoSet](https://arxiv.org/abs/2004.09456) | Language-model stereotype evaluation |
| Toxic degeneration | [RealToxicityPrompts](https://arxiv.org/abs/2009.11462) | Naturally occurring prompts and classifier-dependent toxicity measurement |
| Preference-based instruction following | [InstructGPT](https://arxiv.org/abs/2203.02155) | Human demonstrations, preference data, reward models, and policy evaluation |
| Constitutional alignment | [Constitutional AI](https://arxiv.org/abs/2212.08073) | Rule-guided feedback and independent safety evaluation |
| Reward overoptimization | [Scaling Laws for Reward Model Overoptimization](https://arxiv.org/abs/2210.10760) | Proxy optimization and Goodhart-style failure |
| Hidden-objective auditing | [Auditing language models for hidden objectives](https://arxiv.org/abs/2503.10965) | Blind audit games, model organisms, mixed audit methods, and transfer limits |
| Chain-of-thought monitorability | [OpenAI monitorability evaluations](https://openai.com/index/evaluating-chain-of-thought-monitorability/) and [internal-workload monitoring disclosure](https://openai.com/index/pacing-model-development-cyber-capabilities/) | Two-sided monitor evaluation, operational use, fragile observability, and defense-in-depth limits |

### Interpretability and explanation evaluation

| Topic | Primary source | Book use |
| --- | --- | --- |
| Faithfulness versus plausibility | [Jacovi and Goldberg — Towards Faithfully Interpretable NLP Systems](https://aclanthology.org/2020.acl-main.386/) | Explicit definitions, graded faithfulness, and causal-evaluation discipline |
| Attribution sanity checks | [Adebayo et al. — Sanity Checks for Saliency Maps](https://proceedings.neurips.cc/paper/2018/hash/294a8ed24b1ad22ec2e7efea049b8737-Abstract.html) | Model/data randomization controls and protection against visually persuasive false explanations |
| Attribution-graph evaluation | [Anthropic — Circuit Tracing methods](https://transformer-circuits.pub/2025/attribution-graphs/methods.html) | Interpretability, intervention validation, sufficiency/completeness, graph scope, and limitations |

### Factuality, retrieval, research, and agents

| Topic | Primary source | Book use |
| --- | --- | --- |
| Truthfulness | [TruthfulQA](https://arxiv.org/abs/2109.07958) | Misconception-focused truth evaluation and scope limits |
| Atomic factual precision | [FActScore](https://arxiv.org/abs/2305.14251) | Claim decomposition and evidence support |
| RAG evaluation | [RAGAS](https://arxiv.org/abs/2309.15217) | Retrieval/generation dimensions and automated-proxy caveats |
| General assistant agents | [GAIA](https://arxiv.org/abs/2311.12983) | Reasoning, tools, browsing, multimodality, and end-to-end outcome |
| Browsing agents | [BrowseComp](https://openai.com/index/browsecomp/) | Obscure fact finding, automatic verification, and narrow-construct caution |
| Benchmark evaluation awareness | [Anthropic's BrowseComp investigation](https://www.anthropic.com/engineering/eval-awareness-browsecomp) | Task recognition, leaked-answer retrieval, integrity investigation, and score caveats |
| Long-form research safety | [Deep Research system card](https://openai.com/index/deep-research-system-card/) | Prompt injection, factuality, safety, and long-output adaptation |
| Stateful policy/tool agents | [τ-bench](https://arxiv.org/abs/2406.12045) | Tools, policy, environment state, and outcomes |
| Multi-turn dual-control agents | [τ²-bench](https://arxiv.org/abs/2506.07982) | Stateful user-agent interaction and session evaluation |
| Interactive agent breadth | [AgentBench](https://arxiv.org/abs/2308.03688) | Multiple agent environments and scaffolding effects |
| Factuality suite by evidence mode | [Google DeepMind FACTS](https://deepmind.google/blog/facts-benchmark-suite-systematically-evaluating-the-factuality-of-large-language-models/) | Parametric, search, grounding, and visual factuality as distinct constructs |
| Repository coding agents | [SWE-bench](https://arxiv.org/abs/2310.06770) | Real repository tasks, executable outcomes, and environment validity |
| Long-term conversational memory | [LongMemEval](https://github.com/xiaowu0162/longmemeval) | Multi-session extraction, updates, temporal reasoning, abstention, and benchmark-to-product limits |
| Long-context retrieval without lexical cues | [NoLiMa](https://proceedings.mlr.press/v267/modarressi25a.html) | Latent-association retrieval under long context and stress-test boundaries |
| Personalization field validity | [The Inadequacy of Offline LLM Evaluations](https://arxiv.org/abs/2509.19364) | Real-user evidence for reset-versus-persist evaluation and the offline-to-field gap |

### Benchmarks and reproducibility

| Benchmark or method | Primary source | Book use |
| --- | --- | --- |
| Broad academic knowledge | [MMLU](https://arxiv.org/abs/2009.03300) | Narrow construct versus application inference |
| Diverse capability collection | [BIG-bench](https://arxiv.org/abs/2206.04615) | Task breadth, aggregation, and saturation |
| Graduate-level expert QA | [GPQA](https://arxiv.org/abs/2311.12022) | Expert-domain question construction and limits |
| Mathematical word problems | [GSM8K](https://arxiv.org/abs/2110.14168) | Multi-step answer accuracy and reasoning caveats |
| Executable code correctness | [HumanEval](https://arxiv.org/abs/2107.03374) | Test execution and pass@k |
| Frontier academic questions | [Humanity’s Last Exam](https://arxiv.org/abs/2501.14249) | Hard-question capability and expert-verification boundaries |
| Reproducible evaluation practice | [Lessons from the Trenches](https://arxiv.org/abs/2405.14782) | Prompt, implementation, and reporting sensitivity |
| Evaluator execution boundary | [Inspect AI security guidance](https://github.com/UKGovernmentBEIS/inspect_ai/blob/main/SECURITY.md) and [PaperBench scoring design](https://github.com/UKGovernmentBEIS/inspect_evals/blob/main/src/inspect_evals/paperbench/SCORING_DESIGN.md) | Model-action sandbox limits, trusted eval code, and fresh scoring state |

### Production, governance, and operations

| Topic | Primary source | Book use |
| --- | --- | --- |
| Deployment-like replay | [OpenAI deployment simulation](https://openai.com/index/deployment-simulation/) | Recent production-like context, pre-release failure mining, and forecast validation |
| Operational automated auditing | [Anthropic Petri operational update](https://www.anthropic.com/research/donating-open-source-petri) | Named pre-deployment/model-assessment use, external adoption, and remaining realism limits |
| Realtime audio deployment | [GPT-4o system card](https://openai.com/index/gpt-4o-system-card/) and [generally available Realtime API](https://openai.com/index/introducing-gpt-realtime/) | Audio-specific pre-deployment evals, live safeguards, and the incomplete end-to-end quality boundary |
| Evaluation-system validity | [OpenAI trustworthy third-party evaluations](https://openai.com/index/trustworthy-third-party-evaluations-foundations/) | Environment, harness, contamination, budget, and claim disclosure |
| Model failover | [Sierra model failover](https://sierra.ai/blog/model-failover) | Prevalidated alternatives, failure injection, switching boundaries, and fallback-path evaluation |
| Online coding-agent evaluation | [CursorBench](https://cursor.com/blog/cursorbench) | Online outcomes, human workload, and failures missed by offline correctness graders |
| Benchmark integrity investigation | [Cursor reward hacking investigation](https://cursor.com/blog/reward-hacking-coding-benchmarks) | Permitted information access, known-fix contamination, and score-integrity controls |
| Deep-agent evaluation operations | [How LangChain builds evals for Deep Agents](https://www.langchain.com/blog/how-we-build-evals-for-deep-agents) | Separating software health from model capability, artifacts, reruns, and operational eval service concerns |
| Trace semantics | [OpenTelemetry GenAI conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/) | Portable telemetry and sensitive-field boundaries |
| Canary control | [Google SRE Workbook: Canarying releases](https://sre.google/workbook/canarying-releases/) | Control-relative rollout, analysis, and rollback |
| AI risk-management profile | [NIST AI 600-1 Generative AI Profile](https://doi.org/10.6028/NIST.AI.600-1) | Risk-to-measurement traceability and lifecycle controls |
| AI management system | [ISO/IEC 42001 overview](https://www.iso.org/standard/81230.html) | Organizational management-system context |
| European AI regulation | [Official EU AI Act portal](https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai) | Starting point for jurisdiction-specific governance review; not legal advice |

## Open-source implementation map

Official repositories are implementation evidence, not proof that a default metric fits this product:

- [Promptfoo](https://github.com/promptfoo/promptfoo)
- [DeepEval](https://github.com/confident-ai/deepeval)
- [Inspect AI](https://github.com/UKGovernmentBEIS/inspect_ai)
- [LM Evaluation Harness](https://github.com/EleutherAI/lm-evaluation-harness)
- [LightEval](https://github.com/huggingface/lighteval)
- [HELM](https://github.com/stanford-crfm/helm)
- [Phoenix](https://github.com/Arize-ai/phoenix)
- [Langfuse](https://github.com/langfuse/langfuse)
- [Opik](https://github.com/comet-ml/opik)
- [Ragas](https://github.com/explodinggradients/ragas)
- [Giskard](https://github.com/Giskard-AI/giskard)
- [Label Studio](https://github.com/HumanSignal/label-studio)

## Source-use rules

- Benchmark scores from old papers illustrate protocols, not current model rankings.
- Course duration, access, APIs, licenses, and platform lifecycle are dated claims and must be reverified.
- Vendor case studies can motivate a pattern but do not establish universal effectiveness.
- Secondary research identifies topics; public claims should link to primary evidence.
- A citation supports only the nearby scoped claim, not an entire chapter.
- Local synthetic results are labeled as synthetic and illustrative.
- Regulatory mappings require qualified legal and compliance review for the actual jurisdiction and use case.
