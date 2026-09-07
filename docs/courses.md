# Courses & Learning Paths

Courses can accelerate practice, but they do not define the book’s evaluation method. This page maps each course to a concrete chapter and artifact so “completed” means more than watching videos.

!!! info "Verification status"
    Course metadata below was **Verified 6 September 2026** against the official DeepLearning.AI course pages. Availability, pricing, lesson counts, and access conditions can change. Follow the live page rather than treating this snapshot as a permanent commercial claim.

[Browse DeepLearning.AI’s current short-course catalogue filtered for evals](https://www.deeplearning.ai/courses?q=evals&types=short_course){ .md-button }

## Requested DeepLearning.AI courses

### Evaluating AI Agents

[Open the official course](https://www.deeplearning.ai/courses/evaluating-ai-agents){ .md-button }

| Field | Verified value |
| --- | --- |
| Level | Beginner |
| Duration | 2h16m |
| Format | 15 video lessons, 6 code examples, 1 graded assignment shown on the official page |
| Instructors | John Gilhuly and Aman Khan |
| Partner | Arize AI |

The course covers agent decomposition, tracing, router and skill evaluation, trajectory evaluation, experiment structure, LLM-judge improvement, convergence, and production monitoring.

#### Use it with this book

Read [Agent & System Evals](agent-evals.md) first, then use the course to compare its router/skill/trajectory model with the CX lab’s step/trajectory/outcome model.

Produce this receipt:

```yaml
course: evaluating-ai-agents
book_case: cx-refund-timeout-after-commit
artifacts:
  - normalized-trace.json
  - tool-trajectory-grade.json
  - convergence-analysis.md
comparison:
  adopted: component and trajectory decomposition
  adapted: convergence is diagnostic, not a release score
  rejected: none without an observed reason
```

The follow-up exercise is to grade two safe but different trajectories. This prevents exact-path matching from becoming the accidental definition of agent quality.

### Building and Evaluating Data Agents

[Open the official course](https://www.deeplearning.ai/courses/building-and-evaluating-data-agents){ .md-button }

| Field | Verified value |
| --- | --- |
| Level | Intermediate |
| Duration | 1h59m |
| Format | 8 video lessons, 5 code examples, 1 graded assignment shown on the official page |
| Instructors | Anupam Datta and Josh Reini |
| Partner | Snowflake |

The course builds a planner, plan executor, and specialised data sub-agents; evaluates final answers and goal/plan/action alignment; and introduces inline evaluation that can influence runtime replanning.

#### Use it with this book

Pair it with [RAG & Research Evals](rag-research-evals.md) and [Agent & System Evals](agent-evals.md). The book adds controls the course mapping must make explicit: authoritative database state, read/write permissions, query validity, final-answer grounding, plan faithfulness, and the distinction between an inline runtime critic and an independent release evaluator.

Synthetic transfer task:

> A data agent reports that Turkish refund volume rose 18%. Its SQL selected submitted refunds rather than settled refunds and silently excluded one region. Evaluate query execution, dataset coverage, factual claims, citations to query results, and final decision usefulness separately.

Required receipt: a query-result fixture, goal/plan/action trace, deterministic SQL assertions, atomic-claim table, and one corrected regression case.

### Automated Testing for LLMOps

[Open the official course](https://www.deeplearning.ai/short-courses/automated-testing-llmops){ .md-button }

| Field | Verified value |
| --- | --- |
| Level | Intermediate |
| Duration | 52m |
| Format | 6 video lessons, 4 code examples, 1 graded assignment shown on the official page |
| Instructor | Rob Zuber |
| Partner | CircleCI |

The course covers rule-based evaluation, model-graded evaluation, and CI orchestration for LLM applications.

#### Use it with this book

Complete [Metrics](metrics.md), [LLM as a Judge](llm-as-a-judge.md), and [Release Gates & Shipping](checklist.md) alongside it. Translate the course’s tests into the book’s evaluation pyramid:

1. deterministic schema, permission, and state checks on every change;
2. a small semantic regression subset on protected changes;
3. repeated, adversarial, and expensive suites before promotion;
4. human qualification before a model judge receives blocking authority.

Required receipt: a CI policy that fails on the `policy-bypass` mutant and reports exactly which independent rule blocked the release. A single weighted score is not accepted.

### Evaluating and Debugging Generative AI

[Open the official course](https://www.deeplearning.ai/courses/evaluating-debugging-generative-ai){ .md-button }

| Field | Verified value |
| --- | --- |
| Level | Intermediate |
| Duration | 50m |
| Format | 7 video lessons, 5 code examples, 1 graded assignment shown on the official page |
| Instructor | Carey Phelps |
| Partner | Weights & Biases |

The course covers experiment instrumentation, configuration and metric logging, dataset/model artifacts, generative-image evaluation, and LLM tracing.

#### Use it with this book

Pair it with [Production Evals](production-evals.md) and [Benchmark Reproducibility](benchmark-reproducibility.md). Recreate the relevant ideas through the local provider-neutral manifest rather than making a hosted platform the source of truth.

Required receipt:

```json
{
  "run_id": "cx-rc3-2026-09-06",
  "candidate": "rc3",
  "baseline": "shipping-v2",
  "dataset_version": "refund-v1",
  "rubric_version": "interaction-v2",
  "judge_version": "judge-v1",
  "policy_version": "refund-gate-v1",
  "trace_schema_version": "cx-trace-v1"
}
```

The artifact must remain reproducible even if the external experiment platform is later replaced.

## Broader learning path from the research corpus

The supplied course-and-resource survey also identified the following learning surfaces. They are retained here because each teaches a different part of the evaluation system. This is a **dated study map**, not an endorsement, ranking, or promise of current pricing. Verify availability and syllabus on the linked official page before enrolling.

| Resource | Best use | Pair with | Evidence receipt |
| --- | --- | --- | --- |
| [AI Evals for Engineers & PMs](https://maven.com/parlance-labs/evals) · Hamel Husain and Shreya Shankar | Error-analysis-led eval design, datasets, graders, and organisational practice | Foundations; Dataset Design; Human Evaluation | Failure taxonomy, 30-case seed set, and one reviewed dataset change |
| [LLM Evaluation for Builders](https://www.evidentlyai.com/llm-evaluation-course-practice) · Evidently AI | Practical evaluation workflow and monitoring concepts | Metrics; Production Evals | Versioned experiment report plus one offline-to-live comparison |
| [Intro to LangSmith](https://academy.langchain.com/courses/intro-to-langsmith) · LangChain Academy | Tracing, datasets, experiments, and feedback in one platform | Agent Evals; System Studies | Exported provider-neutral trace and manifest, not only a dashboard screenshot |
| [Hugging Face LLM Course: Evaluation](https://huggingface.co/learn/llm-course/en/chapter11/5) | Benchmark and model-evaluation foundations | Metrics; Benchmark Reproducibility | Reproduced score with task, revision, prompt, few-shot, extractor, and environment manifest |
| [Arize AI courses and certifications](https://arize.com/ai-courses-and-certifications/) | Observability, RAG/agent evaluation, and production diagnosis | RAG & Research; Agent Evals; Production Evals | Trace-localised failure promoted into a regression case |
| [AI Evals & Analytics Playbook](https://maven.com/ai-evals-and-analytics/ai-evals-analytics-playbook) | Evaluation programme and analytics practice | Foundations; Release Gates | Evaluation contract, gate policy, and decision packet |
| [Free AI Evaluation Course](https://maven.com/dataneighbor/o/739503) · AI Analyst Lab | Additional structured practice | Use the chapter matching the live syllabus | One artifact that passes the same review rubric as the main curriculum |

The book deliberately maps platform-specific instruction back to portable objects: case, trial, trace, outcome, grader, dataset release, experiment manifest, calibration report, and gate decision. A course is useful when it improves one of those objects or the decision made from it.

### Workshop and video companions

Use shorter videos for orientation or a targeted second explanation, then produce the same evidence as a course exercise:

- [Evidently AI: LLM evaluation](https://www.youtube.com/watch?v=rHs0sP7b5fM) — map the workflow to an evaluation contract and dataset role.
- [Hamel Husain: AI evals](https://www.youtube.com/watch?v=uiza7wp1KrE) — convert an observed failure into an explicit taxonomy and regression candidate.
- [Arize AI: agent evaluation workshop](https://www.youtube.com/watch?v=Xfl50508LZM) — compare step, trajectory, outcome, and convergence evidence.
- [Braintrust: evals workshop](https://www.youtube.com/watch?v=9iN-cPnp7xg) — reproduce one experiment with a provider-neutral export.

Video completion alone is not evidence. A short resource can still earn a place if its Evidence receipt is inspectable, reproducible, and connected to a decision.

## Choose by missing capability

| If the gap is… | Start with… | Do not skip… |
| --- | --- | --- |
| “We have no reliable cases” | AI Evals for Engineers & PMs plus Dataset Design | Error analysis, role separation, provenance, and sealed evidence |
| “Our scores do not drive releases” | Automated Testing for LLMOps plus Release Gates | Independent rules, uncertainty, exceptions, and rollback |
| “Agent failures are opaque” | Evaluating AI Agents plus Agent Evals | State, tool, trajectory, and outcome evidence |
| “Our RAG score hides citation failures” | Building and Evaluating Data Agents plus RAG & Research Evals | Atomic claims, authority, temporal validity, and abstention |
| “The dashboard cannot reproduce a run” | Evaluating and Debugging Generative AI plus Benchmark Reproducibility | Complete manifests and exportable evidence |
| “Production looks unlike offline” | Evidently/Arize material plus Production Evals | Representative sampling, matured outcomes, and predictive validity |

This routing avoids treating a catalogue as a linear curriculum. Start with the decision failure the team actually has.

## Recommended sequence

| Order | Course | Why now | Book proof after completion |
| ---: | --- | --- | --- |
| 1 | Automated Testing for LLMOps | Establish test and CI mechanics | Mutants blocked by independent gate rules |
| 2 | Evaluating and Debugging Generative AI | Connect runs, versions, traces, and artifacts | Reproducible local experiment manifest |
| 3 | Evaluating AI Agents | Deepen component and trajectory evaluation | Two valid paths graded without exact-match brittleness |
| 4 | Building and Evaluating Data Agents | Extend to planning, data evidence, and multi-agent work | SQL/state/claim evaluation with a promoted regression |

This order is based on dependency, not a claim that one course is universally better than another.

## What the courses do not replace

The book still owns the deeper treatment of:

- human annotation design and inter-rater disagreement;
- judge qualification, false-pass risk, abstention, and requalification;
- paired and clustered uncertainty, power, and inconclusive decisions;
- dataset access, contamination, temporal holdouts, and change control;
- adversarial safety, false refusal, fairness slices, and hard invariants;
- source authority, atomic claims, citation completeness, and live-web validity;
- shadow/canary control, delayed outcomes, rollback, and incident-to-regression evidence.

## Course-completion template

## The supplied report's eight-lab completion path

The supplied *Best Courses and YouTube Resources for Learning LLM Evaluation* report proposes eight projects in one progressively developed repository. Use the existing book exercises below as preparation, then keep each lab's receipt in the same experiment history. The report's sample counts are practice targets, not statistical qualification thresholds.

| Source lab | Existing worked practice | Receipt required from the learner |
| --- | --- | --- |
| Failure analysis | [Mixed-trace workshop, Katas 66–67](dataset-design.md#mixed-trace-workshop-observations-before-causes) | Cluster the proposed 200 outputs/traces; retain raw observations, taxonomy revisions and ambiguous assignments. Explain why an enriched failure sample cannot establish prevalence. |
| Golden dataset | [Incident-to-regression, Katas 60–61](dataset-design.md#from-incident-evidence-to-a-versioned-regression) | Version 50–100 representative failures plus normal controls; record provenance, development/holdout roles, deduplication and access history. Reject a renamed exposed case as a fresh holdout. |
| Human evaluation | [Human Evaluation](human-evaluation.md) | Obtain 2–3 independent annotations for approximately 100 outputs, preserve pre-adjudication labels, calculate agreement and retain disagreement reasons. Authored labels do not satisfy independent annotation. |
| Judge calibration | [Decision workshop, Katas 90–92](calibration-decision-workshop.md) and [LLM judges](llm-as-a-judge.md) | Compare pointwise and pairwise judgments with independent human labels; report false passes, false fails, ties, abstentions and slice support. Qualify each intended use rather than transferring one agreement score to every criterion. |
| RAG evaluation | [Knowledge-to-action, Katas 51–53](knowledge-action-study.md) | Compare retrieval, oracle-document and full-context arms; inspect retrieved evidence, generated claims and final state separately. Explain why fixing retrieval need not fix action selection. |
| Agent evaluation | [Integrated CX walkthrough, Katas 58–59](cx-evidence-walkthrough.md) | Retain outcome, tool/trajectory violations, message evidence, latency and cost provenance. Keep unfinished attempts in the denominator; distinguish synthetic measurements from observed usage. |
| Red teaming | [Robustness and Safety](robustness-safety.md), [Cross-run Isolation](cross-run-isolation-study.md) and [CI Gate Lab](ci-gate-lab.md) | Use harmless synthetic secrets and permitted mock tools to exercise injection, exfiltration and unsafe-action controls. Retain successful attacks and benign controls; demonstrate the CI verdict without claiming population safety. |
| Benchmark reproducibility | [Cross-tool reproduction exercise](benchmark-reproducibility.md#reproduction-exercise-across-tools) | Run the report's LM Evaluation Harness/LightEval comparison on identical pinned tasks and model settings. Compare per-item rendered input, extraction and scoring before aggregate scores. A local illustrative harness comparison is preparation, not proof that these two frameworks were run. |

**Completion defense:** “All eight chapters exist, so all eight labs are complete.” Reject this claim. Chapter presence establishes navigation. Worked solutions teach the method. A learner's retained execution and annotation receipts establish what that learner actually performed. In particular, scripted reviewers cannot close the human lab, local built-in agents cannot establish model quality, and a configured workflow is not a successful hosted CI run. Missing receipts remain explicitly unfinished; they do not invalidate the methods already taught.

### Record a completed course

For any new course, add a record only after verifying its official page.

```yaml
title: Exact course title
official_url: https://...
verified_on: YYYY-MM-DD
book_chapters:
  - chapter.md
concepts:
  - concept
artifact_receipt:
  - path-or-description
observed_limitations:
  - limitation
adopt_adapt_reject:
  adopted: []
  adapted: []
  rejected: []
```

The course earns a place in the maintained learning path by producing reusable evidence, not by popularity, star count, or vendor marketing.
