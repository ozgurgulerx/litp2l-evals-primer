<div class="evals-hero" markdown>

# Evals Primer

A practical field guide to knowing whether an AI system is good enough—and keeping it that way in production.

</div>

## One system, four parts

This primer will use one running example: a customer-support agent that begins with a small refund workflow and gradually becomes more capable. Its evaluation system grows beside it. Every important idea should eventually point to a case, trace, grader, experiment, release rule, or production-learning artifact that we can inspect.

The reading order and building order are intentionally different. Readers meet the ideas before the implementation details. We build a thin working slice early and distinguish recorded executions, illustrative exercises, and outstanding evidence throughout the chapters.

If you are arriving with a decision to make, use three questions:

- **What must I measure?** Start with [Foundations](foundations.md), [Metrics](metrics.md), and the relevant task-family chapter.
- **What evidence do I have?** Inspect the [Evidence Spine](evidence-spine.md), [executed studies](system-studies.md), and [Source Coverage Ledger](source-coverage.md).
- **What does it justify?** Use [Release Gates](checklist.md) for application exposure and [Frontier Risk Decisions](frontier-risk-decisions.md) for the wider claim–evidence–safeguard argument.

The four-part reading order remains below. The [micro-katas](micro-katas.md) offer worked practice; the [delivery map](primer-delivery-map.md) distinguishes implemented material from remaining work.

<div class="chapter-grid" markdown>

<a class="chapter-card" href="foundations/"><strong>Part I · Evaluation foundations</strong>Understand how product promises become evidence, thresholds, release decisions, and learning loops.</a>

<a class="chapter-card" href="build-the-system/"><strong>Part II · Build the CX evaluation system</strong>Grow a mock refund agent toward a production-shaped system with traces, graders, calibration, evidence receipts, and staged release controls.</a>

<a class="chapter-card" href="references/"><strong>Part III · Reference library</strong>Follow the primary sources behind each claim and see which artifact each source informs.</a>

<a class="chapter-card" href="system-studies/"><strong>Part IV · Comparative system studies</strong>Compare how agent runtimes, benchmarks, and evaluation platforms solve the same problems.</a>

</div>

The shared learning loop is:

`concept → CX requirement → executable artifact → observed result or declared evidence gap → source comparison → revised design`

## Part I · Evaluation foundations

### A learning route with evidence checkpoints

Finish the route with [Capstone: defend the release](capstone.md): submit a decision memo and inspectable evidence index, then defend the result under revoked qualification, missing traces and completed side effects. The worked answer distinguishes three local studies from a qualified production system.

Carry one customer workflow through this route. At each checkpoint, produce the named artifact before reading the solution. Record two separate fields: **evidence origin/status** (for example, constructed example, executed local mock, or live study) and **authorized use** (for example, lab-only, unqualified, or qualified for a named use). A live study is not automatically qualified, and an executed result may still use synthetic data. A later chapter does not upgrade an earlier artifact's authority.

| Checkpoint | Read and practice | What you should be able to produce and defend |
| --- | --- | --- |
| **1. Specify the promise** | [Foundations worked checkpoint](foundations.md#worked-checkpoint-seven-surfaces-one-failed-refund-conversation), then [Katas 01–03](micro-katas.md) | A seven-surface contract separating failures, unknowns, runtime prevention and grading. Explain why a correct enum and successful API call can coexist with a failed task. |
| **2. Build and improve the data** | [Dataset Design](dataset-design.md), [Human Evaluation](human-evaluation.md), [Katas 18–20](semantic-grading-lab.md#kata-18-reconstruct-calibration-from-the-labels) | An incident-to-regression record, group-aware split policy and adjudication record. Identify which labels may tune the system and which must remain independent. |
| **3. Qualify the measurement** | [LLM as a Judge](llm-as-a-judge.md), [Semantic Grading Lab](semantic-grading-lab.md) | A rubric, criterion-specific error table, abstention policy and scoped qualification decision. Explain why synthetic annotation rows do not establish human agreement or live judge accuracy. |
| **4. Inspect the execution** | [CX Eval Lab](build-the-system.md), [Kata 04](micro-katas.md#kata-04-recompute-a-grade-not-just-an-average), [Order Resolution](order-resolution-study.md), [Process Recovery](process-recovery-study.md) | A retained trace and authoritative state diff, plus an independently reconstructed grade. Distinguish re-grading, re-execution and provenance verification. |
| **5. Defend the comparison** | [Metrics](metrics.md), [Statistical Method Study](statistical-method-study.md), [Sequential Decisions](sequential-decisions-lab.md) | A registered contrast, independent sampling unit, stopping rule and justified verdict. Reproduce a false-promotion counterexample and state where its assumptions fail. |
| **6. Control exposure** | [Release Gates](checklist.md), [CI Gate Lab](ci-gate-lab.md), [Exposure Control Lab](exposure-control-lab.md) | Separate software conformance from candidate qualification and deployment authority. Demonstrate a hold, restriction and rollback; account for actions already completed before containment. |
| **7. Test transfer and risk** | [Modern Architectures](modern-agent-architectures.md), [Eval Integrity](eval-operations-integrity.md), [Frontier Risk Decisions](frontier-risk-decisions.md) | A study protocol connecting actual execution to outcomes, and a claim–evidence–safeguard argument. Identify what needs human evidence or remains an unresolved research question. |

For interview preparation, close the solution and defend each artifact against a changed assumption: a stale approval, correlated customer sessions, a revoked judge, missing outcomes or an interrupted write. Use [Interview & Design Drills](interview-drills.md) for broader prompts. Completing the route is practice, not an automatic certification; the [delivery map](primer-delivery-map.md) lists the still-missing live and operational evidence.

**Follow one complete local evidence path:** [Katas 58–59](cx-evidence-walkthrough.md) connect checkpoints 4–6 using one retained multi-order CX packet. Inspect the request, clarification, ledger, semantic receipt and paired result, then explain the [current release hold](cx-evidence-walkthrough.md#kata-59-all-trials-passwhat-may-we-release). The walkthrough distinguishes first-grader exercises, SDK mock-transport integration and still-required empirical model qualification.

The order is deliberate: establish why the evaluation exists, decide what evidence it measures, learn how to read the scores, build human evidence, calibrate model graders, test robustness and safety, evaluate retrieval and agents, reproduce benchmarks, watch the system live, and finally enforce the release decision.

<div class="chapter-grid" markdown>

<a class="chapter-card" href="foundations/"><strong>01 · Foundations</strong>Turn a product promise into observable behavior.</a>

<a class="chapter-card" href="dataset-design/"><strong>02 · Dataset design</strong>Build a suite that represents reality and its sharp edges.</a>

<a class="chapter-card" href="metrics/"><strong>03 · Metrics</strong>Interpret scores through slices, uncertainty, and repeatability.</a>

<a class="chapter-card" href="human-evaluation/"><strong>04 · Human evaluation</strong>Design rubrics, annotation studies, adjudication, and trustworthy human evidence.</a>

<a class="chapter-card" href="llm-as-a-judge/"><strong>05 · LLM as a judge</strong>Qualify model-based graders against frozen human evidence.</a>

<a class="chapter-card" href="robustness-safety/"><strong>06 · Robustness, safety & fairness</strong>Probe perturbations, attacks, harmful compliance, false refusal, and crossed slices.</a>

<a class="chapter-card" href="rag-research-evals/"><strong>07 · RAG & research evals</strong>Separate retrieval, claims, citations, source authority, completeness, and temporal validity.</a>

<a class="chapter-card" href="agent-evals/"><strong>08 · Agent & system evals</strong>Evaluate tools, trajectories, state, recovery, multi-turn sessions, and harness validity.</a>

<a class="chapter-card" href="benchmark-reproducibility/"><strong>09 · Benchmark reproducibility</strong>Understand constructs, contamination, prompt sensitivity, harness effects, and result manifests.</a>

<a class="chapter-card" href="production-evals/"><strong>10 · Production</strong>Watch live quality and localize failures from traces.</a>

<a class="chapter-card" href="checklist/"><strong>11 · Release gates & shipping</strong>Enforce the decision contract, control exposure, and roll back safely.</a>

</div>

## Part II · Build the CX evaluation system

Use the [Micro-katas](micro-katas.md) to predict, reproduce and repair small evaluation failures. Each includes runnable checks, a solution, the key interview explanation, and the limits of its evidence. The [delivery map](primer-delivery-map.md) tracks the remaining work toward the complete practitioner curriculum.

The first runnable slice now exists locally. It includes five synthetic refund cases, a resettable mock world, a safe reference agent, deliberately broken agents, deterministic graders, and a release gate that treats safety, quality, protected slices, latency, and cost as separate rules. [Open the CX Eval Lab →](build-the-system.md)

The [Evidence Spine](evidence-spine.md) continues the build from isolated cases to versioned manifests, repeated paired trials, minimum evidence, confidence-bound decisions, and immutable authority receipts.

## Part III · Reference library

The reference library is maintained as part of the work, not attached as a bibliography at the end. Sources are verified, dated, and connected to the claim or design choice they support. [Open the reference library →](references.md)

The [Courses & Learning Paths](courses.md) page maps selected external courses to exact chapters, lab artifacts, and follow-up exercises. A watched course is not treated as evidence of mastery; the artifact produced after it is.

The [Interview & Design Drills](interview-drills.md) page turns the supplied 118-question bank into a thirteen-theme practice map, senior scenarios, whiteboard patterns, answer checks, and evidence receipts.

The [Source Coverage Ledger](source-coverage.md) maps every substantive theme from the supplied research corpus to a chapter, example, artifact, and remaining implementation evidence. It is the completeness control for this living book.

## Part IV · Comparative system studies

Each study asks the same questions of a paper, platform, or codebase, then records what the CX lab should adopt, adapt, or reject. This keeps comparison practical and stops the section from becoming a vendor catalogue. [Open the study programme →](system-studies.md)

<div class="chapter-grid" markdown>

<a class="chapter-card" href="long-running-serving/"><strong>Long-running & serving failures</strong>Build scorer contracts for compaction, restart, approvals, ambiguous commits, fallback, and human workload; trace-producing trials remain pending.</a>

<a class="chapter-card" href="modern-agent-architectures/"><strong>Modern agent architectures</strong>Define typed scoring protocols for knowledge-to-action systems, skill selection, voice timelines, and multi-agent coordination; live comparisons remain pending.</a>

<a class="chapter-card" href="eval-operations-integrity/"><strong>Eval operations & integrity</strong>Exercise fragment merging, model-versus-harness attribution, integrity checks, and simulator scoring; a distributed evaluation service remains pending.</a>

</div>

## Five operating families

| Family | Primary home | What it answers |
| --- | --- | --- |
| **CALIBRATE** | 4 · Human Evaluation and 5 · LLM as a Judge | Is the scoring instrument trustworthy enough for its assigned authority? |
| **BUILD** | 2 · Dataset Design and 3 · Metrics | Is the golden set an executable specification, and can the runner produce defensible evidence? |
| **GATE** | 11 · Release Gates & Shipping | What evidence changes exposure, blocks release, or triggers rollback? |
| **WATCH** | 10 · Production Evals | Is the live system still behaving inside its operating contract? |
| **LOCALIZE** | 1 · Foundations, 7 · RAG, 8 · Agents, and 10 · Production | Did the failure occur at the step, trajectory, or outcome level, and what should fix it? |

!!! important "Dataset boundaries are intentional"
    Sealed acceptance data and label access control live in chapter 2. The frozen calibration set used to validate a judge lives in chapter 5. Keeping them separate prevents evaluation freshness from becoming label leakage.

!!! note "A living book"
    The chapters, code, datasets, and reference map will develop together. When a real failure reveals a missing boundary, we review it, add the smallest useful case, and preserve it in the living regression set.
