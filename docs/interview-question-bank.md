# Complete supplied interview question bank

All 118 canonical IDs, question variants, difficulty labels and answer outlines from the supplied research bank are retained below. These are source outlines, not newly validated model results or complete worked solutions. Use [Interview & Design Drills](interview-drills.md) for the answer contract and [the capstone](capstone.md) for evidence-backed release decisions. The [source ledger](source-coverage.md#input-identity-check-7-september-2026) identifies the exact input version.

Close each outline, answer aloud, then provide a concrete case or artifact and a limitation. A memorized outline alone does not satisfy the book's learning contract. Theme links lead to deeper methods, examples and exercises; source reference abbreviations are retained as provenance labels, with the book's [reference library](references.md) providing usable primary-source links.

## Fundamentals and metrics

Study: [Fundamentals and metrics](metrics.md).

### F1

**What does it mean to evaluate an LLM?** Variant: “How is LLM evaluation different from training loss?”

*Junior · Conceptual*

??? success "Source answer outline"
    Evaluation estimates behaviour on intended tasks and risks; training loss measures optimisation objective. Define target population, task and success criteria.

Source families: EV.

### F2

**What is perplexity, and when is it useful?** Variant: “Is lower perplexity always a better assistant?”

*Junior · Technical*

??? success "Source answer outline"
    `PPL = exp(mean NLL)` for next-token prediction. Useful for language modelling; weak proxy for helpfulness, safety and downstream task success.

Source families: EV.

### F3

**Explain precision, recall and F1.** Variant: “When would accuracy be misleading?”

*Junior · Technical*

??? success "Source answer outline"
    Precision controls false positives; recall controls false negatives; F1 harmonic mean. Choose according to failure cost and class balance.

Source families: MET.

### F4

**How do BLEU and ROUGE differ?** Variant: “Why can two good answers receive poor overlap scores?”

*Mid · Technical*

??? success "Source answer outline"
    BLEU emphasises n-gram precision with brevity handling; ROUGE family emphasises reference overlap/recall. Validity drops when many semantically valid phrasings exist.

Source families: MET.

### F5

**What does BERTScore add over lexical overlap?** Variant: “Would embeddings solve the metric problem?”

*Mid · Technical*

??? success "Source answer outline"
    Contextual-token similarity handles paraphrases better than exact n-grams, but semantic similarity still does not guarantee factuality, instruction following or safety.

Source families: MET.

### F6

**How would you evaluate summarisation quality?** Variant: “What dimensions matter beyond ROUGE?”

*Mid · Case*

??? success "Source answer outline"
    Score factual consistency, coverage, relevance, coherence/style and task-specific constraints; combine automatic metrics with calibrated human/judge evaluation.

Source families: MET, JDG.

### F7

**Whiteboard an evaluator for classification-like LLM outputs.** Variant: “Implement exact match/F1 robustly.”

*Mid · Coding*

??? success "Source answer outline"
    Normalise only justified surface differences; preserve semantic distinctions; compute per-example results; aggregate by slices; expose raw failures.

Source families: EV.

### F8

**How would you construct a single score from many quality dimensions?**

*Senior · Technical*

??? success "Source answer outline"
    Prefer dashboard/Pareto frontier. Aggregate only when decision weights are explicit; normalise scales; treat hard safety constraints separately.

Source families: EV.

### F9

**Tell me about a time a metric improved while product quality got worse. How would you investigate?**

*Senior · Behavioural*

??? success "Source answer outline"
    Test construct mismatch, distribution shift and gaming; inspect examples; compare with human/online outcomes; modify metric/eval dataset rather than defend proxy.

Source families: EV.

### F10

**What makes an evaluation metric scientifically valid?** Variant: “How do you validate an evaluator?”

*Research · Conceptual*

??? success "Source answer outline"
    Reliability plus construct/content/criterion validity; sensitivity to meaningful changes; invariance to irrelevant changes; external human/outcome validation.

Source families: EV, JDG.

## Benchmarks and contamination

Study: [Benchmarks and contamination](benchmark-reproducibility.md).

### B1

**What is MMLU?** Variant: “What does an MMLU score tell you?”

*Junior · Conceptual*

??? success "Source answer outline"
    Broad multiple-choice knowledge/reasoning benchmark across 57 subjects; useful capability signal, not a universal measure of assistant quality.

Source families: BEN.

### B2

**What are GSM8K and HumanEval designed to test?**

*Junior · Conceptual*

??? success "Source answer outline"
    GSM8K: multi-step maths word problems. HumanEval: program synthesis judged through executable functional tests.

Source families: BEN.

### B3

**How should benchmark scores be interpreted?**

*Mid · Conceptual*

??? success "Source answer outline"
    State task distribution, prompt/scoring protocol, chance level, uncertainty, contamination risk and distance from deployment workload.

Source families: BEN, DATA.

### B4

**Why might a model improve on MMLU but not your application?**

*Mid · Case*

??? success "Source answer outline"
    Benchmark/product distribution mismatch; benchmark may omit tool use, conversation, domain constraints, latency, safety and real error costs.

Source families: BEN, EV.

### B5

**What is benchmark contamination? How would you detect or mitigate it?**

*Mid · Technical*

??? success "Source answer outline"
    Training exposure can inflate results. Track provenance, n-gram/search overlap where possible, use temporal/private/live sets and fresh generated tasks.

Source families: DATA.

### B6

**How would you design a benchmark that resists saturation?**

*Senior · Design*

??? success "Source answer outline"
    Dynamic/fresh data, harder discriminative tasks, hidden/private subsets, adversarially mined failures, regular refreshes and stable anchors for longitudinal comparison.

Source families: BEN, DATA.

### B7

**Explain or derive pass@k for code evaluation.** Variant: “Why isn't pass@1 enough?”

*Senior · Whiteboard*

??? success "Source answer outline"
    Generate multiple candidates and estimate probability at least one passes all tests; use the unbiased estimator when sampling finite `n`; report k and sampling policy.

Source families: BEN.

### B8

**How can we distinguish genuine generalisation from benchmark memorisation in black-box models?**

*Research · Research design*

??? success "Source answer outline"
    Use canary/novel transformations, temporal tests, paraphrased structure, contamination probes and generalisation to newly generated instances; no single test proves absence.

Source families: DATA.

## Human evaluation

Study: [Human evaluation](human-evaluation.md).

### H1

**When do you need human evaluation?**

*Junior · Conceptual*

??? success "Source answer outline"
    When quality is subjective/open-ended, automatic metrics are insufficient or high-stakes validation is needed; reserve humans strategically because of cost/variance.

Source families: HUM.

### H2

**How would you design a human evaluation study?**

*Mid · Design*

??? success "Source answer outline"
    Define construct/rubric; sample representative outputs; blind/randomise; train raters; collect repeat judgements; measure agreement and uncertainty.

Source families: HUM.

### H3

**Pairwise comparison or Likert rating?**

*Mid · Conceptual*

??? success "Source answer outline"
    Pairwise often simplifies relative preference; Likert gives absolute scale but anchoring/scale interpretation varies. Match method to decision.

Source families: HUM.

### H4

**What is inter-annotator agreement and why does it matter?**

*Mid · Technical*

??? success "Source answer outline"
    Measures consistency beyond raw averages; low agreement can signal unclear rubric, inherently subjective construct or insufficient rater expertise.

Source families: HUM.

### H5

**Your annotators disagree on 40% of examples. What do you do?**

*Senior · Case*

??? success "Source answer outline"
    Examine disagreement slices; clarify rubric/anchors; train raters; separate legitimate ambiguity from errors; adjudicate; preserve uncertainty.

Source families: HUM.

### H6

**How many human ratings do you need?**

*Senior · Technical*

??? success "Source answer outline"
    Depends on expected effect, between-example/rater variance and desired precision. Power/design analysis beats a universal fixed sample count.

Source families: HUM.

### H7

**A domain expert and ordinary users disagree. Whose label is correct?**

*Senior · Behavioural*

??? success "Source answer outline"
    Depends on construct: factual/legal correctness may need expert authority; preference/usability may need target users. Model label hierarchy explicitly.

Source families: HUM.

### H8

**How would you model rater effects rather than averaging them away?**

*Research · Technical*

??? success "Source answer outline"
    Hierarchical/mixed-effects or probabilistic annotator models; estimate item and rater variation; model systematic biases and uncertainty.

Source families: HUM.

## LLM judges

Study: [LLM judges](llm-as-a-judge.md).

### J1

**What is LLM-as-a-judge?**

*Junior · Conceptual*

??? success "Source answer outline"
    A model grades, ranks or classifies outputs under a rubric, enabling scalable semantic evaluation where deterministic checks are insufficient.

Source families: JDG.

### J2

**What are the major failure modes of an LLM judge?**

*Mid · Technical*

??? success "Source answer outline"
    Position/order, verbosity/length, style, self-preference, rubric ambiguity, domain weakness, prompt sensitivity and correlated errors.

Source families: JDG.

### J3

**Pairwise judging versus scoring 1–5: which would you choose?**

*Mid · Design*

??? success "Source answer outline"
    Pairwise often easier for relative discrimination; absolute scoring fits stable criterion thresholds. Validate whichever format against humans.

Source families: JDG.

### J4

**How do you calibrate an LLM judge to human evaluators?**

*Mid · Technical*

??? success "Source answer outline"
    Build held-out expert-labelled set; compare agreement/confusion/rank correlation; tune rubric; inspect disagreements by slice; avoid evaluating calibration data.

Source families: JDG, HUM.

### J5

**Whiteboard an experiment for position bias in a judge.**

*Senior · Coding/design*

??? success "Source answer outline"
    Judge `(A,B)` and `(B,A)`, randomise identities, measure preference flips/order coefficient; repeat enough items; optionally average symmetric judgements.

Source families: JDG.

### J6

**Your judge says model B is better but expert reviewers strongly prefer A. What next?**

*Senior · Behavioural*

??? success "Source answer outline"
    Stop treating judge as ground truth; error-slice disagreements, audit rubric/bias, recalibrate, potentially replace or ensemble judge.

Source families: JDG, HUM.

### J7

**How would you measure whether judge errors are correlated with the evaluated model's errors?**

*Research · Research*

??? success "Source answer outline"
    Human-labelled stratified set, error covariance/conditional analysis across model families, cross-family judges, adversarial disagreement sets.

Source families: JDG.

### J8

**Can an LLM judge replace human evaluation entirely?**

*Research · Conceptual*

??? success "Source answer outline"
    No general guarantee. Best viewed as a calibrated proxy whose validity is bounded by domain, task and judge capabilities; retain human audits.

Source families: JDG, HUM.

## Robustness and adversarial evaluation

Study: [Robustness and adversarial evaluation](robustness-safety.md).

### R1

**What is robustness in LLM evaluation?**

*Junior · Conceptual*

??? success "Source answer outline"
    Stable desired behaviour under irrelevant or expected variation, distribution shift, noise and—in security settings—adversarial inputs.

Source families: ROB.

### R2

**How would you test prompt robustness?**

*Mid · Technical*

??? success "Source answer outline"
    Generate meaning-preserving paraphrases, spelling noise, formatting/order variations; compare mean/worst-case performance and failure consistency.

Source families: ROB.

### R3

**What is behavioural testing for language models?**

*Mid · Conceptual*

??? success "Source answer outline"
    Test specific capabilities/invariances and directional expectations rather than only averaging accuracy over a natural dataset.

Source families: ROB.

### R4

**How do adversarial tests differ from normal edge cases?**

*Mid · Conceptual*

??? success "Source answer outline"
    Adversarial tests are constructed to provoke failure under an explicit attacker objective/capability; edge cases need not involve an attacker.

Source families: ROB, SAFE.

### R5

**Design a robustness suite for a customer-support assistant.**

*Senior · Case*

??? success "Source answer outline"
    Paraphrase/noise/language/style shifts; conflicting instructions; long context; malformed data; domain tails; injection attempts; consistent business rules.

Source families: ROB, SAFE.

### R6

**Write pseudocode for a metamorphic/perturbation evaluator.**

*Senior · Coding*

??? success "Source answer outline"
    Base examples → semantically valid transformations → paired inference → invariant property check → degradation metrics → save counterexamples.

Source families: ROB.

### R7

**How would you measure worst-case rather than average robustness?**

*Senior · Technical*

??? success "Source answer outline"
    Define perturbation set/threat model; report lower-tail/worst-group performance and attack success, not only mean score.

Source families: ROB, SAFE.

### R8

**A red team finds a rare catastrophic failure one day before launch. What do you do?**

*Senior · Behavioural*

??? success "Source answer outline"
    Severity × exploitability × exposure; reproduce; create regression; mitigate/contain; make explicit risk-based release decision rather than average it away.

Source families: SAFE.

### R9

**How do you know your red-team benchmark itself is representative of realistic attackers?**

*Research · Research*

??? success "Source answer outline"
    Threat modelling, diverse attack families, adaptive attacks, held-out attacks, external red teams and real incident feedback.

Source families: SAFE.

### R10

**How would you evaluate adaptive adversaries rather than static jailbreak strings?**

*Research · Research*

??? success "Source answer outline"
    Allow iterative attacker feedback/query budget; measure success versus cost; prevent benchmark leakage; evaluate defences under adaptation.

Source families: SAFE.

## Bias and fairness

Study: [Bias and fairness](robustness-safety.md).

### BF1

**What does fairness mean for a generative model?**

*Junior · Conceptual*

??? success "Source answer outline"
    No universal definition: specify affected population, outcome, protected dimensions and harm before choosing a metric.

Source families: FAIR.

### BF2

**How would you test stereotypical bias?**

*Mid · Technical*

??? success "Source answer outline"
    Controlled/counterfactual prompts varying protected attribute while holding task-relevant context constant; measure response differences and stereotypes.

Source families: FAIR.

### BF3

**What are BBQ and StereoSet used for?**

*Mid · Conceptual*

??? success "Source answer outline"
    Benchmark social bias/stereotypical behaviour under structured prompts; they measure particular constructs, not complete real-world fairness.

Source families: FAIR.

### BF4

**How do you evaluate toxicity?**

*Mid · Technical*

??? success "Source answer outline"
    Representative and adversarial prompts, group-conditioned slices, severity/type labels; validate toxicity classifier/judge against humans.

Source families: FAIR.

### BF5

**A model passes gender and race tests separately but fails for Black women. What happened?**

*Senior · Case*

??? success "Source answer outline"
    Intersectional effects are hidden by marginal aggregates; evaluate crossed subgroups with adequate samples and uncertainty.

Source families: FAIR.

### BF6

**How do you decide whether a fairness gap is practically significant?**

*Senior · Technical*

??? success "Source answer outline"
    Effect size, uncertainty, harm severity, baseline rates and application context—not p-value alone.

Source families: FAIR.

### BF7

**Product leadership wants to remove a fairness slice because it lowers the headline score. How do you respond?**

*Senior · Behavioural*

??? success "Source answer outline"
    Preserve decision-relevant slices; explain aggregation masking; establish explicit governance/release constraints.

Source families: FAIR.

### BF8

**How would you evaluate fairness for free-form generation where there is no obvious positive label?**

*Research · Research*

??? success "Source answer outline"
    Operationalise harms such as allocation, representation, stereotyping, toxicity or quality-of-service; combine counterfactual, distributional and human measures.

Source families: FAIR.

## Calibration and uncertainty

Study: [Calibration and uncertainty](calibration-decision-workshop.md).

### C1

**What is calibration?** Variant: “What does 80% confidence mean?”

*Junior · Conceptual*

??? success "Source answer outline"
    Among predictions assigned about 0.8 confidence, roughly 80% should be correct under the evaluated distribution.

Source families: CAL.

### C2

**Can a highly accurate model be poorly calibrated?**

*Junior · Conceptual*

??? success "Source answer outline"
    Yes. Accuracy measures correctness frequency; calibration measures reliability of confidence estimates.

Source families: CAL.

### C3

**Explain ECE, Brier score and NLL.**

*Mid · Technical*

??? success "Source answer outline"
    ECE bins confidence versus empirical accuracy; Brier scores probabilistic squared error; NLL rewards proper probability assignment strongly.

Source families: CAL.

### C4

**How would you use uncertainty in a production LLM?**

*Mid · Case*

??? success "Source answer outline"
    Abstention/escalation/retrieval/verification based on confidence; optimise risk–coverage trade-off rather than always answering.

Source families: CAL.

### C5

**Whiteboard a reliability diagram and calibration test.**

*Senior · Coding*

??? success "Source answer outline"
    Collect `(confidence, correctness)`; bin or smooth; plot mean confidence against accuracy; report ECE/proper score with uncertainty.

Source families: CAL.

### C6

**Why is token probability a problematic confidence measure for free-form answers?**

*Senior · Technical*

??? success "Source answer outline"
    Probability is distributed across many semantically equivalent strings; sequence length/tokenisation also distort comparisons.

Source families: CAL.

### C7

**What is semantic entropy?**

*Research · Technical*

??? success "Source answer outline"
    Sample completions, cluster equivalent meanings, aggregate probability/mass by semantic answer, calculate uncertainty over semantic classes.

Source families: CAL.

### C8

**Can perfect calibration eliminate hallucination?**

*Research · Conceptual*

??? success "Source answer outline"
    No. Calibration concerns frequency-reliability, not guaranteed truth on every instance; theoretical work even identifies settings where calibrated models must sometimes err/hallucinate.

Source families: CAL.

## Prompts and datasets

Study: [Prompts and datasets](dataset-design.md).

### P1

**What is a golden eval set?**

*Junior · Conceptual*

??? success "Source answer outline"
    Versioned examples with trusted expected labels/rubrics used for repeatable comparison and regression detection.

Source families: EV.

### P2

**Why should prompts be versioned?**

*Junior · Conceptual*

??? success "Source answer outline"
    Prompt changes alter system behaviour and therefore experimental conditions; reproducibility requires exact templates/instructions.

Source families: DATA.

### P3

**How would you compare two prompt templates?**

*Mid · Technical*

??? success "Source answer outline"
    Same examples/models/settings; paired evaluation; quality + safety + latency/token-cost; repeated runs if stochastic.

Source families: EV, DATA.

### P4

**How do you evaluate few-shot example selection?**

*Mid · Case*

??? success "Source answer outline"
    Hold evaluation data separate; vary exemplars/order; test multiple slices; detect overfitting to particular examples.

Source families: ROB.

### P5

**What should be in an LLM eval dataset?**

*Mid · Design*

??? success "Source answer outline"
    Representative normal cases, important slices, tails, high-risk cases, adversarial inputs and previously observed failures.

Source families: EV.

### P6

**How do you use synthetic data for evaluation safely?**

*Mid · Design*

??? success "Source answer outline"
    Use it to expand coverage, not unquestioned ground truth; constrain generation; deduplicate; validate samples; maintain human/real-data anchors.

Source families: EV.

### P7

**How would you build an eval set from millions of production traces?**

*Senior · Design*

??? success "Source answer outline"
    Stratify by intents/outcomes/slices; enrich failures; sample temporal tails; deduplicate clusters; protect privacy; maintain untouched holdout.

Source families: DATA.

### P8

**Whiteboard a stratified sampling strategy for eval-set construction.**

*Senior · Coding/design*

??? success "Source answer outline"
    Estimate production strata; sample with minimum representation for rare critical groups; attach weights for population-level estimates.

Source families: DATA.

### P9

**You optimised a prompt for weeks and benchmark scores rose, but production did not. Explain.**

*Senior · Behavioural*

??? success "Source answer outline"
    Benchmark overfitting/test reuse, distribution mismatch, proxy metric gaming or interaction effects; refresh holdout and production-derived eval.

Source families: DATA.

### P10

**How would you quantify prompt overfitting from repeated eval-set reuse?**

*Research · Research*

??? success "Source answer outline"
    Separate development/test evals, track number of adaptive decisions, refresh hidden sets, use temporal/external replication; recognise adaptive holdout problem.

Source families: DATA.

## Reproducibility and statistics

Study: [Reproducibility and statistics](metrics.md).

### S1

**Why can the same model get different benchmark scores in two implementations?**

*Junior · Conceptual*

??? success "Source answer outline"
    Prompt/template, tokenizer, few-shot selection, decoding, model revision, scorer and dataset-version differences.

Source families: DATA.

### S2

**What do you log for reproducible LLM evaluation?**

*Mid · Technical*

??? success "Source answer outline"
    Model/provider/version; prompt; dataset hash; scorer version; decoding; seed; dependencies; timestamp; raw outputs; cost/latency.

Source families: DATA.

### S3

**Why are paired comparisons preferable when evaluating A vs B on the same test set?**

*Mid · Technical*

??? success "Source answer outline"
    Per-example pairing removes much item-difficulty variation and lets you estimate the distribution of differences directly.

Source families: DATA.

### S4

**Implement/whiteboard a paired bootstrap confidence interval.**

*Mid · Coding*

??? success "Source answer outline"
    Store per-example A/B outcomes; repeatedly resample item indices with replacement; recompute delta; percentile/appropriate bootstrap CI.

Source families: DATA.

### S5

**Model B beats A by 0.7 percentage points. Do you ship?**

*Senior · Case*

??? success "Source answer outline"
    Need CI/effect size, slice regressions, business significance, risk thresholds, cost/latency and experimental power.

Source families: DATA.

### S6

**How do you handle multiple comparisons across many prompts and models?**

*Senior · Statistics*

??? success "Source answer outline"
    Pre-register primary comparisons where possible; correct/control multiplicity or use hierarchical modelling; avoid cherry-picked maxima.

Source families: DATA.

### S7

**An external team cannot reproduce your reported eval. How do you debug it?**

*Senior · Behavioural*

??? success "Source answer outline"
    Diff artefacts end-to-end: data hash, prompts, harness commit, model endpoint revision, decoding and evaluator; provide raw examples.

Source families: DATA.

### S8

**How should benchmark uncertainty be modelled when both examples and model outputs are stochastic?**

*Research · Statistics*

??? success "Source answer outline"
    Hierarchical/resampling design accounting for item and generation variance; repeated generations; avoid treating correlated samples as independent.

Source families: DATA.

## Tooling and continuous evaluation

Study: [Tooling and continuous evaluation](production-evals.md).

### M1

**What is evaluation-driven development?**

*Junior · Conceptual*

??? success "Source answer outline"
    Write measurable behaviour tests before/alongside prompt/model changes; iterate against stable evals rather than eyeballing demos.

Source families: OPS.

### M2

**Where do evals fit in CI/CD?**

*Mid · Design*

??? success "Source answer outline"
    Cheap deterministic/regression tests every change; larger suites pre-merge/release; costly human/red-team audits periodically.

Source families: OPS.

### M3

**What should an LLM observability trace contain?**

*Mid · Technical*

??? success "Source answer outline"
    User input, prompt/context, retrieval, tool calls, model outputs, timing, tokens/cost, errors, evaluator feedback and version metadata.

Source families: OPS.

### M4

**What would you monitor after deployment?**

*Mid · Design*

??? success "Source answer outline"
    Task/business outcomes, quality samples, safety events, refusal/fallback, input shifts, latency, cost and failure slices.

Source families: OPS.

### M5

**Write a release-gate design for an eval pipeline.**

*Mid · Coding/design*

??? success "Source answer outline"
    Baseline/candidate → suite → scorer → CIs → hard constraints + non-regression thresholds → artefact report → pass/fail.

Source families: OPS.

### M6

**How do you implement continuous evaluation without grading every production request?**

*Senior · Design*

??? success "Source answer outline"
    Risk/stratified sampling, automated cheap scorers, trigger-based deep evaluation, periodic human audits.

Source families: OPS.

### M7

**How do you detect drift when labels arrive slowly?**

*Senior · Technical*

??? success "Source answer outline"
    Proxy signals/input embeddings/intent distribution, disagreement/uncertainty, sampled judge scores; verify with delayed human/business labels.

Source families: OPS.

### M8

**How would you choose among evaluation frameworks?**

*Senior · Architecture*

??? success "Source answer outline"
    Evaluate required model providers, agents/tools, custom scorers, reproducibility, trace support, CI, distributed execution and governance—not popularity.

Source families: OPS.

### M9

**A production incident passed every offline eval. What do you change?**

*Senior · Behavioural*

??? success "Source answer outline"
    Convert incident to regression; identify missing slice/threat; mine related cases; change sampling/gate; examine why offline distribution missed it.

Source families: OPS.

### M10

**Design an eval platform serving many teams and models.**

*Senior · System design*

??? success "Source answer outline"
    Versioned datasets/rubrics/scorers, immutable runs, cached model outputs, distributed workers, access controls, experiment comparison, trace/error analysis.

Source families: OPS.

## RAG and agents

Study: [RAG and agents](agent-evals.md).

### A1

**Why is evaluating a RAG application different from evaluating the LLM alone?**

*Junior · Conceptual*

??? success "Source answer outline"
    Errors can arise in query processing, retrieval, ranking/context construction or generation; evaluate components and end-to-end interaction.

Source families: RAG.

### A2

**What retrieval metrics would you use?**

*Mid · Technical*

??? success "Source answer outline"
    Recall@k/Hit@k for evidence coverage; precision@k for noise; MRR for first relevant rank; nDCG for graded relevance.

Source families: RAG.

### A3

**What are faithfulness, answer relevance and context relevance?**

*Mid · Conceptual*

??? success "Source answer outline"
    Faithfulness: supported by context; answer relevance: addresses query; context relevance: retrieved material helps answer. Keep constructs distinct.

Source families: RAG.

### A4

**How would you evaluate citations in a RAG answer?**

*Mid · Technical*

??? success "Source answer outline"
    Citation completeness, correctness/entailment, source quality and whether cited span actually supports nearby claim.

Source families: RAG, FACT.

### A5

**Whiteboard a RAG evaluation harness.**

*Mid · Coding/design*

??? success "Source answer outline"
    Query + expected evidence → retrieval → retrieval metrics → generation → claim-level grounding/answer score → latency/cost → slice report.

Source families: RAG.

### A6

**Retrieval recall is high but answer quality is poor. How do you debug it?**

*Senior · Case*

??? success "Source answer outline"
    Inspect ranking/noise/context placement; run generation on oracle contexts; test prompt/context utilisation; isolate generator from retriever.

Source families: RAG.

### A7

**How would you evaluate an agent rather than a chatbot?**

*Senior · Design*

??? success "Source answer outline"
    Task success, tool choice, arguments, trajectory, retries/recovery, environmental side effects, safety, latency, tokens/cost.

Source families: AGT.

### A8

**Design a trajectory scorer for a tool-using agent.**

*Senior · Coding/design*

??? success "Source answer outline"
    Verify final state and each action's validity; distinguish outcome success from efficient/appropriate path; penalise unsafe/unnecessary operations.

Source families: AGT.

### A9

**How do you evaluate multi-turn agents that can recover from mistakes?**

*Senior · Technical*

??? success "Source answer outline"
    Do not fail on every intermediate error; score final goal, recovery ability, accumulated cost and irreversible side effects.

Source families: AGT.

### A10

**An agent achieved 95% task success but caused damaging side effects in 1%. Would you launch?**

*Senior · Behavioural*

??? success "Source answer outline"
    Separate hard-risk constraints from average success; severity-weight catastrophic side effects; require sandbox/approval/mitigation before release.

Source families: AGT, SAFE.

### A11

**How do you compare two agents when successful trajectories can be radically different?**

*Research · Research*

??? success "Source answer outline"
    Outcome/state-based scoring plus action-level constraints; trajectory equivalence classes; cost/risk Pareto analysis rather than one reference path.

Source families: AGT.

### A12

**How would you evaluate emergent tool-use capability without leaking the task into scaffolding?**

*Research · Research*

??? success "Source answer outline"
    Standardise harness/scaffolding; disclose tools; vary task instances; ablate orchestration; measure model versus system contribution separately.

Source families: AGT.

## Interpretability

Study: [Interpretability](robustness-safety.md).

### I1

**What is the difference between interpretability and explainability?**

*Junior · Conceptual*

??? success "Source answer outline"
    Terms vary, but distinguish understanding internal mechanism from producing understandable explanations of behaviour; state definition explicitly.

Source families: INTP.

### I2

**Why isn't chain-of-thought automatically a faithful explanation?**

*Mid · Conceptual*

??? success "Source answer outline"
    Generated rationale may be post-hoc or omit causal mechanisms; behavioural coherence does not prove causal dependence.

Source families: INTP.

### I3

**How would you test whether an explanation is faithful?**

*Senior · Technical*

??? success "Source answer outline"
    Intervention/counterfactual tests: change purported causal factor and measure resulting behaviour; compare against plausible-but-noncausal explanations.

Source families: INTP.

### I4

**Whiteboard a causal intervention experiment for an interpretability method.**

*Senior · Coding/design*

??? success "Source answer outline"
    Identify mechanism/feature → intervene/ablate → predicted behavioural change → controls → effect estimate across examples.

Source families: INTP.

### I5

**How do you evaluate a mechanistic interpretability method itself?**

*Research · Research*

??? success "Source answer outline"
    Ground-truth toy mechanisms, causal completeness/sufficiency, predictive interventions, stability, coverage and false discoveries.

Source families: INTP.

### I6

**Can interpretability evidence be incorporated into safety evaluation?**

*Research · Research*

??? success "Source answer outline"
    Potentially as complementary evidence for hidden mechanisms/deception, but validate causal reliability; don't substitute unvalidated interpretations for behavioural tests.

Source families: INTP, SAFE.

## Safety and alignment

Study: [Safety and alignment](robustness-safety.md).

### L1

**What is RLHF?**

*Junior · Conceptual*

??? success "Source answer outline"
    Collect human preference/demonstration signal, fit/aligned policy via supervised and preference/reward optimisation stages; evaluate held-out behaviour independently.

Source families: RLHF.

### L2

**What is red teaming?**

*Mid · Conceptual*

??? success "Source answer outline"
    Systematic adversarial probing to discover harmful/security failures under explicit threat models before and after deployment.

Source families: SAFE.

### L3

**How do you evaluate a safety refusal policy?**

*Mid · Technical*

??? success "Source answer outline"
    Measure harmful compliance and benign false-refusal separately, stratified by harm category/severity.

Source families: SAFE.

### L4

**How do you evaluate the quality of RLHF preference data?**

*Mid · Technical*

??? success "Source answer outline"
    Agreement, rater expertise, instruction compliance, consistency, difficult/ambiguous cases, demographic/rater bias and held-out predictive validity.

Source families: RLHF, HUM.

### L5

**RLAIF versus RLHF—how would evaluation differ?**

*Mid · Conceptual*

??? success "Source answer outline"
    AI-generated feedback adds evaluator-model failure/bias risk; validate AI preferences against independent humans/standards and adversarial cases.

Source families: RLHF.

### L6

**How do you know a reward model is good?**

*Senior · Technical*

??? success "Source answer outline"
    Held-out pairwise accuracy/ranking, calibration, slice performance, OOD robustness and relationship with independent human evaluation.

Source families: RLHF.

### L7

**What is reward hacking or overoptimisation?**

*Senior · Conceptual*

??? success "Source answer outline"
    Policy exploits imperfections in proxy reward; proxy score may rise after true human quality peaks. Use independent evaluation and conservative optimisation.

Source families: RLHF.

### L8

**Design an evaluation for a newly RLHF-trained assistant.**

*Senior · Design*

??? success "Source answer outline"
    Held-out preferences, core capabilities, factuality, safety/refusal, bias, robustness, production-like tasks; compare SFT/base and analyse regressions.

Source families: RLHF, SAFE.

### L9

**Safety wants a higher refusal rate; product wants fewer refusals. How do you resolve the dispute?**

*Senior · Behavioural*

??? success "Source answer outline"
    Build harmful-compliance/false-refusal frontier by risk class, assign costs/constraints explicitly, improve classifier/policy rather than optimise one aggregate rate.

Source families: SAFE.

### L10

**How do you evaluate safety against adaptive jailbreaking?**

*Research · Research*

??? success "Source answer outline"
    Adaptive attacker with budget and feedback; diverse attack algorithms; hidden behaviours; human validation; measure success, severity and false positives.

Source families: SAFE.

### L11

**Can preference-model accuracy predict aligned behaviour after optimisation?**

*Research · Research*

??? success "Source answer outline"
    Only partially; distribution shifts as policy exploits reward model. Evaluate post-optimisation policy independently and monitor Goodhart effects.

Source families: RLHF.

### L12

**How would you evaluate Constitutional AI or another AI-feedback alignment method?**

*Research · Research*

??? success "Source answer outline"
    Validate principle adherence, harmlessness/helpfulness, evaluator bias, over-refusal, capability regression and generalisation beyond training critiques/preferences.

Source families: RLHF, SAFE.

