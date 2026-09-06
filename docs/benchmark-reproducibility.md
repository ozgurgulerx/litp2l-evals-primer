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

### Find the first divergent boundary

Two matching aggregate scores can hide different wrong answers. Two different scores can come from identical model outputs. Compare per-item records before interpreting the headline, and locate the earliest boundary at which the two executions disagree:

| Boundary | Retained comparison | What a mismatch suggests |
| --- | --- | --- |
| Task | Item IDs, input/target bytes, split and inclusion rules | Different experiments despite the same task name |
| Prompt | Fully rendered text, demonstrations and chat-role serialization | Prompt construction or few-shot selection changed |
| Tokenization | Token IDs, special tokens, context/continuation boundary | The model did not receive the same token sequence |
| Inference | Model files, dtype, backend, generation settings and raw outputs or likelihoods | Numerical, serving, caching or inference differences |
| Extraction | Raw output, selected answer and parse/abstention status | The scoring input changed after inference |
| Scoring | Per-item metric inputs, formula and decision | Normalization, tie-breaking or metric semantics differ |
| Aggregation | Included IDs, weights and task grouping | Exclusions or weighting changed the summary |

A file hash proves identity only for the bytes actually included. Pinning a model's weight file but omitting its tokenizer or chat template does not freeze the model input. An equal prompt string does not prove equal tokenization, and equal token IDs do not prove equal numerical execution. State which boundaries were compared and which were merely assumed.

Use explicit tolerances for floating-point scores when exact equality is inappropriate. Register them before seeing the discrepancy. A small log-likelihood difference can still change an argmax when choices are nearly tied, so report both numerical error and decision agreement. Do not hide a changed prediction by rounding the scores until they look equal.

### Raw and normalized likelihood answer different questions

For a fixed prompt and a candidate continuation containing tokens \(t_1,\ldots,t_n\), summed conditional log-likelihood is:

\[
L = \sum_{i=1}^{n} \log p(t_i \mid \text{prompt},t_{<i}).
\]

The sum ranks the probability of the whole sequence. Dividing by continuation token count ranks average token log-probability; dividing by character count is a different normalization again. These transformations can reverse the preferred answer. None is a universal correction for length bias: the appropriate score depends on the registered task and answer representation.

For example, suppose two continuations have summed log-likelihoods −3 and −4, with one and four tokens respectively. The raw sum favors the first; token normalization gives −3 versus −1 and favors the second. This arithmetic example does not describe either framework's default. Inspect the installed task and metric implementation before labeling a difference a default mismatch.

Retain the continuation text and token count used by each scorer. Check whether leading whitespace belongs to the prompt or continuation, whether a beginning-of-sequence token is inserted, whether termination tokens are scored, and what happens when a continuation token merges across the prompt boundary. “Same answer text” is not sufficient to establish the same likelihood event.

Generation exact match is a different protocol from choosing the most likely supplied answer. In the former, the model must produce an answer under a generation budget. In the latter, the evaluator supplies the alternatives and scores them. Reporting one as the other changes the capability claim even when both metrics are named accuracy.

### Separate replay from rerunning the model

A lightweight replay can recompute extraction, metric decisions and aggregates from retained outputs. It should detect missing items, duplicated IDs, malformed outputs and contradictory derived scores. It cannot establish that the stored outputs were generated by the claimed framework or model.

A model rerun additionally requires the pinned executable environment, model and tokenizer files, task inputs, inference configuration and resource assumptions. Keep dependency-heavy reruns separate from offline artifact inspection so readers can inspect results without silently downloading a model. A successful replay is evidence about reporting consistency; a successful rerun supplies stronger reproduction evidence, still bounded by execution provenance and the observed platform.

Record failed runs too. If a backend is unsupported on the test machine or an optional dependency is missing, that is an execution limitation—not a zero capability score and not permission to substitute stored answers while calling the result a fresh model run.

## Kata 81: equal accuracy, different evidence

**Know:** aggregate agreement does not establish per-item agreement, numerical parity, or equivalent measurement. Join by registered item identity before comparing records.

These are invented diagnostic records, not model executions:

| Item | Target | Harness X prediction | Harness Y prediction |
| --- | --- | --- | --- |
| J01 | A | A | B |
| J02 | B | A | B |
| J03 | A | A | A |
| J04 | B | B | B |

**Task:** calculate both accuracies, prediction agreement, and the two directions of paired correctness disagreement. Can you identify the cause? Would reordering Y's records justify comparing them by row position?

??? success "Worked solution and executable diagnostic"
    Both accuracies are 3/4, but predictions agree on only 2/4 items. X alone is correct on J01; Y alone is correct on J02. The net accuracy difference is zero despite two discordant pairs. This does not establish statistical equivalence or identify whether prompts, inference or extraction caused the differences.

    ```python
    targets = {"J01": "A", "J02": "B", "J03": "A", "J04": "B"}
    x_rows = [("J01", "A"), ("J02", "A"), ("J03", "A"), ("J04", "B")]
    y_rows = [("J04", "B"), ("J02", "B"), ("J01", "B"), ("J03", "A")]

    def join_registered(rows, registered):
        ids = [item_id for item_id, _ in rows]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate item identity")
        if set(ids) != set(registered):
            raise ValueError("missing or unexpected item identity")
        return dict(rows)

    x = join_registered(x_rows, targets)
    y = join_registered(y_rows, targets)
    x_ok = {key: x[key] == target for key, target in targets.items()}
    y_ok = {key: y[key] == target for key, target in targets.items()}
    assert sum(x_ok.values()) == sum(y_ok.values()) == 3
    assert sum(x[key] == y[key] for key in targets) == 2
    assert [key for key in targets if x_ok[key] and not y_ok[key]] == ["J01"]
    assert [key for key in targets if y_ok[key] and not x_ok[key]] == ["J02"]
    for malformed in (y_rows[:-1], y_rows + [y_rows[0]]):
        try:
            join_registered(malformed, targets)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid item inventory was accepted")
    ```

    Row order is irrelevant after this identity join. Equal IDs alone are not enough for a real reproduction: verify their input and target bytes too. This helper checks inventory only, not the provenance or schema of arbitrary artifacts.

**Extend:** suppose exact prompts agree but continuation token IDs differ. Locate the first observed divergence at tokenization, retain both token sequences, and investigate special tokens and boundary splitting. Do not attribute all downstream differences to that boundary until a targeted intervention tests it. Equal tokens with different likelihoods instead move the investigation to inference settings and numerical execution.

**Interview answer:** “I compare registered per-item evidence and locate the first divergent boundary. Equal headline accuracy can conceal different failures. A shared scorer diagnoses reporting differences but does not replace native metrics. I preserve original results and report what a controlled reconciliation actually repairs.”

This exercise validates comparison arithmetic and identity joining only. It does not complete the two-framework execution exercise above or qualify any deployment decision.

### A reproducible environment is not necessarily a safe environment

Pinning dependencies preserves old behavior, including known vulnerabilities. Audit the isolated rerun environment before recommending its installation. Record audit scope, date, unresolved advisories and whether a patched compatible combination exists. Do not claim that a failed audit demonstrates exploitation, or that safetensors alone makes the dependency stack safe.

If upgrades alter tokenizer or framework behavior, retain the old experiment as historical evidence and register the patched environment as a new arm. Do not silently overwrite the original version while presenting its scores as reproduced. Offline artifact inspection should remain available without requiring readers to install the historical stack.

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
