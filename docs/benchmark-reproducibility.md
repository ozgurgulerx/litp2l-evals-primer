# Benchmark Reproducibility

A benchmark result is produced by a task specification, dataset, prompt template, few-shot examples, model configuration, harness, answer extractor, scorer, and reporting policy. The number is not a primitive property of the model.

## Begin with the claim

Ask what decision the benchmark supports:

- Does a model possess a narrow capability under a fixed protocol?
- Is a new model non-regressive on an internal task portfolio?
- Does an application satisfy a product contract?
- Does an agent solve tasks in a realistic environment?
- Is a safeguard effective against a named threat model?

Using MMLU to approve a refund agent would have weak **construct validity**: broad multiple-choice knowledge does not represent tool authorization, payment state, or customer resolution.

## Five forms of validity

| Property | Question | Example threat |
| --- | --- | --- |
| Construct validity | Does the task measure the capability named in the claim? | Short-answer search used as a proxy for full research-report quality |
| Internal validity | Did the candidate change cause the observed difference? | Prompt and maximum tokens changed with the model |
| External validity | Does the result transfer to the target users and environment? | English academic questions generalized to Turkish CX traffic |
| Measurement reliability | Would the protocol produce stable results under controlled repetition? | Judge order flips winners |
| Predictive validity | Does offline evidence forecast production behavior and decisions? | Offline win does not predict canary resolution |

Validity is not binary. State the intended inference and the threats that remain.

## Model, application, and system benchmarks

| Level | Examples | Good use | Main caveat |
| --- | --- | --- | --- |
| Model capability | MMLU, GPQA, GSM8K, BIG-bench | Compare defined knowledge or reasoning tasks | Narrow tasks and prompt sensitivity |
| Code correctness | HumanEval | Execute generated functions against tests | Small functions differ from repository work |
| Repository agent | SWE-bench | Resolve real issue tasks in repository environments | Scaffolding and environment affect the score |
| General assistant agent | GAIA, AgentBench | Tool use and multi-step task completion | Aggregate outcome hides failure attribution |
| Browsing agent | BrowseComp | Find obscure, verifiable facts through browsing | Short answers do not cover full research quality |
| Truth and factuality | TruthfulQA, FActScore | Probe misconceptions or atomic factual precision | Domain and evidence assumptions matter |
| RAG application | RAGAS-style dimensions or internal suites | Separate retrieval and generation properties | Automated judges need qualification |
| Safety | HarmBench, JailbreakBench, StrongREJECT, XSTest | Named attacks, harmfulness, and over-refusal | Threat and scorer coverage remain incomplete |
| Fairness/toxicity | BBQ, StereoSet, RealToxicityPrompts | Probe specific bias or toxicity constructs | Not a complete fairness assessment |
| Holistic programme | HELM | Multi-scenario, multi-metric transparent evaluation | Breadth increases reporting and configuration burden |

Do not memorize benchmark names as answers. Explain the construct, protocol, score, target inference, and limitation.

## Freeze the task definition

Version:

- canonical input and target;
- data split and revision;
- few-shot selection and ordering;
- prompt template and chat formatting;
- tools and documents;
- maximum steps and token budget;
- generation parameters;
- answer extraction;
- scoring and aggregation;
- exclusions and failure handling.

A silent dataset patch or extractor change creates a new measuring instrument even when the benchmark name stays constant.

## Prompt and few-shot sensitivity

Small changes can alter performance:

- instruction wording;
- response format;
- answer-choice labels;
- chat role formatting;
- number and order of demonstrations;
- whitespace or stop tokens;
- whether reasoning is requested;
- whether the final answer must use a parser-friendly form.

Choose the protocol before seeing candidate results where possible. If several defensible prompts are studied, report the distribution or a registered selection rule rather than publishing only the best prompt per model.

## Answer extraction is part of the metric

Suppose the target is `B` and the model writes:

```text
The correct answer is option B because the policy applies after verification.
```

An exact whole-string scorer returns failure. A brittle “first capital letter” parser might extract `T`. A registered option extractor returns `B`. Validate extractors using known-good, malformed, ambiguous, and adversarial outputs.

For code, execute in a controlled sandbox and record compile/runtime/test failures separately. For agents, verify environment state rather than parsing a success phrase.

## Inference and serving settings matter

Record:

- provider and exact model identifier;
- weights or revision where available;
- quantization and serving backend;
- tokenizer and chat template;
- temperature, top-p, seeds, and sampling count;
- maximum input/output tokens;
- batch and concurrency settings;
- tool and reasoning budgets;
- retry and timeout policy.

An infrastructure change can alter semantic behavior without changing the model name. Treat serving implementation as part of the evaluated system.

## Contamination and saturation

Contamination occurs when test items, close variants, labels, or task-specific solution information enter training, prompting, retrieval, or optimization. Detecting it perfectly may be impossible, but use layered controls:

- private or newly authored acceptance tasks;
- time-based holdouts;
- near-duplicate and semantic-overlap searches;
- task-detail reproduction probes;
- canary items or controlled strings where appropriate;
- strict label access and audit logs;
- separation of optimization and acceptance sets;
- suspicious-score investigations.

A saturated benchmark no longer differentiates strong systems well. Preserve it for historical comparison if useful, but add harder or more representative tasks instead of interpreting ceiling differences as decisive.

## Protect evaluation integrity

Contamination is one threat to evaluation integrity, but not the only one. The evaluation is compromised whenever a system can obtain the answer key, infer privileged task metadata, alter the scorer, manipulate what enters the denominator, or exploit state that the intended product would not possess.

Threat-model the entire evidence path:

| Asset or boundary | Example attack or failure | Control |
| --- | --- | --- |
| Sealed tasks and answer keys | Retrieval, logs, package contents, or credentials expose labels | Separate storage and credentials; least privilege; access audit; canary strings |
| Task identity and protocol | Model recognizes benchmark phrasing and switches to a memorized strategy | Private/temporal holdouts; phrasing variants; task-detail reproduction probes |
| Harness and scorer | Agent alters files, dependencies, or services used by scoring | Content hashes; reviewed dependencies; fresh or read-only scoring environment |
| Reporting denominator | Timeouts, abstentions, parse errors, or failed runs disappear | Register inclusion rules; publish all attempts, errors, exclusions, and reasons |
| Trace and result records | Successful rows are edited or failed trials are silently rerun | Append-only logs; trial IDs; signed or content-addressed artifacts; retry policy |
| Release authority | Evaluated system can write its own approval | Separate execution, scoring, and release identities; immutable decision record |

### Worked threat: answer-key retrieval

Anthropic's analysis of BrowseComp found a small set of cases in which a model appeared aware that it was being evaluated; in two cases it located and decrypted a leaked answer key. That behavior may demonstrate browsing and inference capability, but it does **not** estimate the intended obscure-fact research construct. Once privileged labels enter the trajectory, record the trial as an integrity incident, preserve it for security analysis, and exclude it only under a predeclared reporting rule that leaves the original denominator visible.

An investigation receipt might be:

```yaml
trial_id: browse-214#seed-03
signal: answer_key_canary_accessed
evidence:
  - outbound_request_to_label_artifact
  - exact_private_canary_in_trace
disposition: compromised_trial
reporting:
  attempted_denominator: included
  capability_score: reported_with_and_without_compromised_trial
follow_up:
  - rotate_answer_key_and_credentials
  - search_all_trials_for_task_detail_reproduction
  - add_egress_and_artifact_access_controls
```

Evaluation awareness is not automatically misconduct and cannot always be detected. The engineering obligation is narrower: prevent privileged evaluator information from changing the measured task, retain enough trace evidence to investigate suspicious success, and avoid calling a compromised score general capability.

## Harness effects

The harness can help or hurt a model through:

- tool wrappers and descriptions;
- context packing;
- retry behavior;
- answer normalization;
- timeouts;
- environment reset;
- dependency versions;
- hidden state;
- network availability;
- error handling.

Validate the harness with reference outputs and controlled failures. Cross-harness reproduction is especially useful when a surprising result could be an implementation artifact.

## Statistical reporting

Report:

- numerator, denominator, and exclusions;
- per-task and aggregate results;
- uncertainty appropriate to the sampling design;
- repeated-trial policy;
- paired candidate-baseline differences when possible;
- slice results;
- compute, cost, latency, and budget;
- all deviations from the registered protocol.

Macro-averaging weights tasks equally; micro-averaging weights examples. Neither is universally right. Publish enough detail to recover both when the portfolio contains materially different tasks.

## Leaderboard discipline

A leaderboard compresses decisions into rank. It can hide:

- measurement uncertainty;
- tiny non-material differences;
- missing tasks;
- incompatible budgets;
- contamination risk;
- unsafe regressions;
- vendor-specific scaffolding;
- changes in benchmark version.

Use leaderboards for discovery, then inspect task-level evidence and reproduce critical claims under the intended environment.

## Worked example: one dataset, two harness results

Synthetic four-item benchmark:

| ID | Target | Model response |
| --- | --- | --- |
| B01 | A | `A` |
| B02 | B | `The answer is B.` |
| B03 | C | `C, with low confidence.` |
| B04 | D | `I cannot determine; likely D.` |

Harness X uses whole-string exact match and reports `1/4 = 25%`. Harness Y uses a registered option extractor and reports `4/4 = 100%`.

Neither headline is sufficient:

- X confounds task performance with output formatting.
- Y may over-credit B04 if abstention or calibrated confidence is part of the construct.
- Four examples provide almost no precision.
- The model, prompt, and output contract are not yet shown.

The right response is to define the intended output contract, validate the extractor, report malformed/abstained outputs separately, and run the registered protocol on a defensible sample.

## Artifact: reproducibility manifest

```yaml
benchmark_run: cx-policy-mcq-2026-09-06-01
claim: compare policy-reasoning accuracy at a fixed inference budget
dataset:
  name: cx-policy-mcq
  version: v2
  split: sealed-test
  item_hash: sha256:example
protocol:
  prompt_template: mcq-direct-v3
  few_shot_ids: [demo-01, demo-07]
  extractor: final-option-v2
  scorer: exact-option-v1
model:
  identifier: provider/model-version
  temperature: 0
  max_output_tokens: 128
harness:
  name: local-benchmark-adapter
  version: v1
environment:
  python: "3.12"
reporting:
  exclusions: none
  confidence_interval: wilson-95
  aggregation: micro
```

Store the manifest beside per-item outputs and scorer decisions. A summary CSV alone cannot explain a reproduction failure.

## Reproduction exercise across tools

Implement a small task in two systems, such as LM Evaluation Harness and LightEval, or the local harness and Inspect. Hold the data, prompt, generation settings, extractor, and scorer constant.

Compare:

- rendered prompts;
- tokenized inputs;
- model outputs;
- extraction decisions;
- per-item scores;
- exclusions and errors;
- aggregate and interval calculations.

The objective is not to crown a tool. It is to identify which defaults enter the measurement.

## Failure modes

| Failure mode | Misleading claim | Repair |
| --- | --- | --- |
| Benchmark name without version | Results appear comparable across changed tasks | Pin data, task, and harness revisions |
| Best prompt selected after results | Prompt search is hidden test tuning | Register selection or report sensitivity |
| Unvalidated extractor | Formatting becomes capability | Test extraction and report malformed outputs |
| Model name only | Serving and chat-template changes disappear | Record the complete system configuration |
| Public test optimization | Score is mistaken for generalization | Use separated private/temporal acceptance data |
| Aggregate leaderboard | Critical tasks and uncertainty vanish | Publish task, slice, and paired evidence |
| Cross-budget ranking | More search or tokens look like better intelligence | Normalize or expose compute and cost |
| Harness trusted by default | Implementation bug becomes model result | Reference cases, mutants, and cross-harness checks |
| Answer key accessible to the system | Retrieval skill is reported as task capability | Restrict labels, audit access, and classify compromised trials |
| Failures removed from denominator | Reliability is inflated through reporting policy | Register and publish attempts, exclusions, errors, and retries |

## Exercise: audit a benchmark claim

A report says: “Model B beats Model A by 1.2 points on AgentBench.” It supplies only model display names and the aggregate score.

List the minimum evidence needed before using the result in a production model decision.

??? success "Answer"
    Require the exact benchmark/task and dataset version; harness and environment revision; model/provider revisions; prompts and chat templates; tool wrappers; inference, token, step, retry, and time budgets; number of trials and seeds; answer/outcome graders; exclusions and errors; per-task paired outcomes; uncertainty; cost/latency; contamination considerations; and evidence that the benchmark construct transfers to the target product. Even a fully reproduced 1.2-point difference may be irrelevant if the product requires different tools, languages, safety constraints, or outcomes.

## Verification checklist

- [ ] The claimed construct and target decision are explicit.
- [ ] Dataset, task, prompt, model, harness, extractor, and scorer are versioned.
- [ ] Inference and resource budgets are recorded.
- [ ] Known outputs validate answer extraction and scoring.
- [ ] Contamination and saturation risks are discussed.
- [ ] Answer keys, evaluator-only fields, scorer state, and release authority are access-separated.
- [ ] Evaluation-awareness and task-detail-reproduction probes are reviewed.
- [ ] Results include denominators, exclusions, uncertainty, and slices.
- [ ] Candidate and baseline use comparable conditions.
- [ ] Aggregate scores do not hide critical task failures.
- [ ] Cross-harness reproduction is used for consequential surprises.

## Primary reading and implementations

- [HELM: Holistic Evaluation of Language Models](https://arxiv.org/abs/2211.09110)
- [EleutherAI LM Evaluation Harness](https://github.com/EleutherAI/lm-evaluation-harness)
- [Hugging Face LightEval](https://github.com/huggingface/lighteval)
- [UK AI Security Institute Inspect](https://github.com/UKGovernmentBEIS/inspect_ai)
- [MMLU](https://arxiv.org/abs/2009.03300)
- [SWE-bench](https://arxiv.org/abs/2310.06770)
- [BrowseComp](https://openai.com/index/browsecomp/)
- [Anthropic — Evaluation awareness in BrowseComp](https://www.anthropic.com/engineering/eval-awareness-browsecomp)
- [Inspect AI security guidance](https://github.com/UKGovernmentBEIS/inspect_ai/blob/main/SECURITY.md)
