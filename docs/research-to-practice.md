# Research-to-Practice Evidence

This chapter answers a narrower question than “does the technique exist?”:
**is it demonstrably used in a real evaluation or deployment process?** The
answer is dated **6 September 2026**. Public evidence can establish disclosed
practice, but it cannot reveal controls, failures, or outcomes that an
organization has not published.

!!! abstract "Short answer"
    Some of the frontier methods are in operational use. Deployment replay,
    Petri-style automated alignment auditing, chain-of-thought monitoring, and
    audio safety evaluation all have first-party evidence tied to actual model
    assessment or deployed systems. Rare-failure importance sampling,
    evaluator-of-evaluators benchmarks, judge bias correction, long-memory
    benchmarks, and hidden-objective audit games remain primarily research
    methods. Personalization has field evidence showing why stateless offline
    evaluation can fail, but not a publicly validated production recipe.

The practical rule is simple: **a paper, leaderboard, repository, or vendor
feature is not by itself production proof**. A portal claim must name the
organization, use, date, evidence source, limitations, and local authority.

## Evidence maturity rubric

Use [Frontier Risk Decisions](frontier-risk-decisions.md) for the next step: turn these method receipts into a bounded safety case. Its worked examples separate capability, practical uplift, harmful propensity, safeguards, internal deployment, participant outcomes, and residual uncertainty. Numerical exercises are explicitly illustrative; they are not additional company deployment evidence.

| Level | Minimum public evidence | What may be claimed | What may not be claimed |
| --- | --- | --- | --- |
| **Production control** | A first party says the method informed pre-deployment assessment, deployment decisions, live monitoring, or an operational safeguard | “Disclosed as used in this named operational context” | Universal effectiveness, causal impact, or suitability for our gate |
| **Field evidence** | Data from real users, production traffic, or post-release outcomes tests a hypothesis | “The failure or relationship was observed in the field” | That a complete evaluation control was deployed or fixed the problem |
| **Operational tool** | Maintained code is usable and may have named adopters, but release authority or deployment outcomes are not established | “Implemented and used for exploration/testing” | “Production-proven” or “validated release gate” |
| **Research or benchmark** | A paper, controlled experiment, synthetic model organism, dataset, or leaderboard | “Demonstrated under the reported experimental conditions” | Real-world deployment effectiveness |

These levels describe evidence, not intrinsic quality. A production control can
still be weak; a research method can be excellent and simply not yet validated
in operations.

## Deployment proof matrix

| Capability from the research review | Ledger ID | Evidence level | Practical proof | Portal decision |
| --- | --- | --- | --- | --- |
| Deployment-like replay and rate calibration | `deployment_simulation` | **Production control** | OpenAI reports using Deployment Simulation in pre-deployment safety review and model development, analyzing about 1.3 million de-identified conversations and comparing predictions with post-release rates | Adopt the pattern when consent, privacy, recency, tool fidelity, and post-release calibration can be proved locally |
| Dynamic behavioral auditing with Petri | `petri_dynamic_auditing` | **Production control** | Anthropic states Petri has been part of every Claude alignment assessment since Sonnet 4.5; UK AISI also used it for sabotage-propensity evaluation | Use for broad discovery and pre-release assessment; human validation and fixed regression cases retain gate authority |
| Targeted suite generation with Bloom | `bloom_suite_generation` | **Operational tool** | Anthropic released a working framework and reports agreement with hand labels and separation of baseline from intentionally misaligned models | Use in sandbox/shadow to generate candidate cases; qualify realism, diversity, and judges before gating |
| Chain-of-thought monitoring | `chain_of_thought_monitoring` | **Production control**, narrowly scoped | OpenAI reports monitoring internal coding agents/frontier workloads and later deploying additional monitoring for high-risk models; its evaluation suite measures monitor and agent together | Treat as defense in depth for systems that expose suitable reasoning signals; never as a sole safety case |
| Realtime voice safety evaluation and monitoring | `realtime_voice_evaluation` | **Production control**, partial | OpenAI’s GPT-4o system card documents pre-deployment audio evals; the generally available Realtime API documents active session classifiers and layered safeguards | Adopt modality-specific safety, voice-diversity, interruption, noise, and live-monitor tests; the sources do not prove a complete voice-quality EvalOps stack |
| Personalization and persistent state | `personalized_stateful_evaluation` | **Field evidence** | A study with 800 real ChatGPT and Gemini users found that identical prompts can behave differently in stateless and personalized sessions | Add reset-versus-persist and consented replay slices; validate on our traffic before assigning release authority |
| Extreme-tail reliability with Five-Nines/CEM | `rare_failure_estimation` | **Research or benchmark** | The paper reports sample-efficient importance sampling on three models and parameterized GSM8K templates, with up to 156.22× fewer inferences than naive sampling | Reproduce locally in shadow; no public deployment proof found |
| Evaluator-of-evaluators with AgentRewardBench | `evaluator_of_evaluators` | **Research or benchmark** | Expert-reviewed trajectories expose disagreement among twelve LLM judges and undercounting by some rule graders | Benchmark candidate evaluators, then qualify them on local human/deterministic evidence; no public deployment proof found |
| Bias-corrected LLM-judge reporting | `judge_bias_correction` | **Research or benchmark** | The method models a judge as an imperfect diagnostic and propagates calibration-set uncertainty into corrected estimates and intervals | Prototype beside raw confusion matrices; no public deployment proof found |
| Adaptive/IRT evaluation | `adaptive_irt_evaluation` | **Research or benchmark** | Published studies reduce benchmark item counts using item-response models, while later stress tests show unreliable item and rank estimates in small or non-normal model populations | Use for cost-saving experiments only after model-fit, item-bank, rank-stability, and mandatory safety-core checks; no public production proof found |
| Adaptive security testing | `adaptive_security_testing` | **Research or benchmark** | A peer-reviewed study optimized attacks against eight indirect prompt-injection defenses | Red-team the exact deployed system and keep external enforcement; attack evidence is not deployment proof |
| Hidden-objective auditing | `hidden_objective_auditing` | **Research or benchmark** | Blind teams audited a deliberately trained model with a hidden objective; three of four teams uncovered it | Use as an audit-training pattern, not evidence that hidden objectives are reliably detectable in deployed frontier systems |
| Long-memory and long-horizon benchmarks | `long_memory_and_horizon_benchmarks` | **Research or benchmark** | LongMemEval, NoLiMa, and Long-Horizon-Terminal-Bench provide reproducible stress instruments | Use to probe constructs, then add product histories, latency, privacy, and outcome evidence; benchmark use is not deployment proof |

!!! warning "Current local authority: none"
    Every row is currently `not_gating` in this portal's local evidence ledger.
    “Production control” describes a named external disclosure; it does not
    inherit authority into the CX lab. The separate
    `eligible_authority_after_qualification` field records only the maximum
    local role worth considering after the required validation is completed.

## The research review's fourteen headline developments

The supplied review makes fourteen executive claims. This table preserves all
fourteen and adds the operational verdict that a research summary alone cannot
provide.

| # | Development | Practice verdict as of 6 September 2026 |
| ---: | --- | --- |
| 1 | Evaluation expanded from model to system | **Deployed practice.** System cards, agent assessments, and deployment replay record model, scaffold, tools, environment, budget, and graders; local manifests still need to reproduce that tuple. |
| 2 | Judge validity is local | **Strong research and practitioner practice.** Task- and criterion-specific qualification is well supported, but public evidence rarely identifies which product release was decided by a calibrated judge. |
| 3 | Solver ability bounds objective judging | **Research evidence.** JudgeBench and No Free Labels support verified references and executable truth; they do not prove a universal ceiling for every subjective criterion. |
| 4 | Human judgment is a distribution | **Established evaluation practice.** Overlap, expertise, disagreement, and adjudication are used in serious studies; TASTE demonstrates discussion/confidence filtering on 92 expert preference pairs, not a production product gate. |
| 5 | Pairwise is not always superior to scalar scoring | **Research evidence.** Protocol performance varies by criterion and judge; run a local format ablation instead of adopting a universal rule. |
| 6 | More rubric/context is not monotonically better | **Research evidence.** Fixation, overlap, overload, and reference mimicry are measured failure modes; no public production outcome study identifies one optimal rubric length. |
| 7 | Static benchmarks lose authority as they saturate or leak | **Operationally acted upon.** Labs use refreshed, held-out, and private evaluations and audit benchmark health, but freshness does not itself establish product validity. |
| 8 | Benchmarks themselves require evaluation | **Deployed decision support.** OpenAI reports auditing coding evals because they inform deployment and safety decisions; task validity, oracle replay, grader coverage, and environment health remain separate checks. |
| 9 | Agent reliability decays with horizon | **Benchmark evidence.** Long task suites expose compounding failure, but public results are scaffold-, budget-, and environment-dependent rather than universal reliability laws. |
| 10 | Outcome and trajectory evidence are complementary | **Deployed practice.** Automated audits and agent system cards examine traces and behaviors while state/outcome checks establish success; exact canonical-path matching is still usually too rigid. |
| 11 | RAG evaluation is decompositional | **Operational tools and benchmark evidence.** Claim, retrieval, citation, context, and memory diagnostics exist; a public tool release does not prove causal product improvement. |
| 12 | Average accuracy is giving way to tail reliability | **Research evidence.** Five-Nines and rare-behavior forecasting target the tail; neither supplies public proof of a production release gate. |
| 13 | Safety is adaptive and system-level | **Mixed.** Adaptive-attack research shows static-defense weakness, while deployed systems disclose external enforcement and monitoring; the specific adaptive attacks are not production controls. |
| 14 | Offline evaluation cannot close the loop alone | **Production and field evidence.** Deployment Simulation backtests pre-release forecasts, and the 800-user personalization study demonstrates state-dependent field behavior. |

For the detailed evidence receipts and adoption boundaries, use the sections
below and the machine-readable ledger rather than the shorthand verdict alone.

## Production controls with public receipts

### Deployment Simulation: replay, predict, verify

[OpenAI’s Deployment Simulation report](https://openai.com/index/deployment-simulation/)
is the strongest example here of closing the offline-to-live loop. It reports:

- recent, privacy-filtered production prefixes replayed against a candidate;
- pre-registered predictions for 20 undesirable-behavior categories for one
  release;
- post-release checks of taxonomy coverage, direction, and rate calibration;
- approximately 1.3 million analyzed conversations across several deployments;
- a median multiplicative prediction error of 1.5×, with much larger tail errors;
- an agentic extension using 120,000 internal employee trajectories and tool
  simulation.

This is operational proof that the method was used, not proof that replay is an
unbiased copy of future traffic. The report says rare events can be missed,
historical prefixes can drift, and most experiments simulate one assistant
response. A local implementation therefore needs a consent and privacy record,
traffic-window manifest, state/tool simulator checks, forecast registration,
and post-release backtest.

### Petri: automated auditing before release

[Anthropic’s 2026 Petri update](https://www.anthropic.com/research/donating-open-source-petri)
states that Petri has participated in every Claude alignment assessment since
Sonnet 4.5 and that UK AISI used it in sabotage-risk evaluation. The
[original release](https://www.anthropic.com/research/petri-open-source-auditing)
also documents simulated users and tools, an auditor agent, a judge, and system
card usage.

That is practical assessment evidence. It does not show that an automated
Petri score alone approved or blocked a release. Petri’s own authors call the
metrics provisional and emphasize human review. Eval awareness and simulator
realism remain active problems. The correct local pattern is:

```text
broad generated audit
→ human review of surfaced traces
→ reproduce the behavior with controlled seeds
→ promote confirmed failures into a fixed regression set
→ qualify any grader before it gains gate authority
```

[Bloom](https://www.anthropic.com/research/bloom) complements this by generating
a deeper suite for one named behavior. Its published experiments are useful
validation, but public evidence does not establish Bloom itself as a routine
release gate. Keep generated cases exploratory until their construct, realism,
diversity, and scorer are qualified.

### Chain-of-thought monitoring: operational but not sufficient

OpenAI’s [monitorability evaluation framework](https://openai.com/index/evaluating-chain-of-thought-monitorability/)
separates three archetypes: intervention, process, and outcome-property
evaluations. OpenAI also publicly describes
[monitoring internal high-risk workloads](https://openai.com/index/pacing-model-development-cyber-capabilities/)
and says chain-of-thought monitoring has been used for internal coding agents
and long-running sessions.

The proof is narrow. Monitorability is a two-sided property of the agent and
monitor; some behaviors are poorly observable; training pressure can cause
intent to become less legible; benchmark results may not transfer to live
misbehavior. A sound control keeps separate measures for:

1. whether the behavior actually occurred;
2. whether actions/outputs reveal it;
3. whether the reasoning signal reveals it;
4. the monitor’s true- and false-positive rates by behavior and model;
5. the operational response to a flag.

Do not expose private reasoning to end users or treat it as a faithful causal
explanation. Where the reasoning trace is unavailable, actions, outputs,
tool-state invariants, and independent monitors remain the control surface.

### Realtime voice: deployed safety evidence, incomplete quality evidence

The [GPT-4o system card](https://openai.com/index/gpt-4o-system-card/) reports
audio-specific pre-deployment work: diverse voice inputs, transferred safety
tests, unauthorized-voice controls, human red teaming, and observed robustness
problems under noise, echo, and interruption. The
[generally available Realtime API](https://openai.com/index/introducing-gpt-realtime/)
documents active classifiers that can halt policy-violating sessions.

This proves deployed audio safeguards and evaluation, not a universal end-to-end
voice scorecard. A product evaluation must still measure:

- speech recognition and semantic task success by language/accent;
- time to first audio, interruption response, barge-in recovery, and turn
  completion;
- background noise, echo, packet loss, truncation, and overlapping speech;
- unsafe audio and false refusal independently;
- tool latency, confirmation before irreversible actions, and recovery;
- conversation-level resolution rather than transcript quality alone.

## Field evidence that changes evaluation design

### Personalization and persistent memory

[The Inadequacy of Offline LLM Evaluations](https://arxiv.org/abs/2509.19364)
compared offline behavior with questions posed by 800 real users through
ChatGPT and Gemini interfaces. It provides field evidence that user state can
change answers to nominally identical prompts. It does not publish a generally
validated production gate for memory or personalization.

The practical response is a paired protocol:

| Arm | State | Question answered |
| --- | --- | --- |
| Reset | No prior user history | Does the base system satisfy the contract? |
| Persist | Consented, versioned history | Does personalization help without violating current intent, privacy, or policy? |
| Counter-user | A different synthetic or consented history | Is behavior improperly leaking or overgeneralizing preferences? |
| Update | Old preference followed by a newer correction | Does the system respect recency and explicit override? |

Slice by memory age, history length, language, preference type, user cohort,
and conflict with the current instruction. Report task success, incorrect
personalization, privacy leakage, stale-memory use, abstention, latency, and
cost. [LongMemEval](https://github.com/xiaowu0162/longmemeval) and
[NoLiMa](https://proceedings.mlr.press/v267/modarressi25a.html) are useful
stress instruments, but only local or consented histories establish product
validity.

## Promising methods without deployment proof

### Rare-failure estimation

[Five-Nines](https://arxiv.org/abs/2605.11209) learns a proposal distribution
concentrated on failure-prone inputs using the cross-entropy method, then uses
importance weights to estimate the original-distribution failure rate. The
reported efficiency gains are experimental results on parameterized math
templates, not public proof of a production reliability control.

Before operational use, verify that the parameterized generator represents the
target population, the proposal retains support wherever failures can occur,
importance weights do not collapse to a few samples, estimates recover known
synthetic rates, and confidence intervals include adaptation uncertainty. Keep
hard prevention and incident monitoring: a statistical estimator cannot make
an irreversible action safe.

### Evaluating evaluators

[AgentRewardBench](https://arxiv.org/abs/2504.08942) contains 1,302
expert-reviewed trajectories drawn from five web-agent benchmarks. It found no
single LLM judge best across all benchmarks and found that common rule-based
graders can undercount success. This is strong evidence that graders need their
own benchmark; it is not proof that the top leaderboard judge transfers to a
specific product.

For each candidate evaluator, report human agreement, false-pass and
false-block rates, precision/recall on failures, rank fidelity between systems,
side-effect detection, repeatability, cost, and behavior under distribution
shift. The winner still enters local qualification and shadow comparison.

### Corrected judge estimates

[How to Correctly Report LLM-as-a-Judge Evaluations](https://arxiv.org/abs/2511.21140)
treats judge outputs like a noisy diagnostic. If sensitivity and specificity
are learned on a representative human-labeled calibration set, a raw judge
pass rate can be corrected and its interval can propagate uncertainty from
both datasets.

The assumptions are load-bearing: the error rates must transfer from the
calibration set to the evaluated population; labels must be trustworthy; and
the judge cannot have unmodeled slice- or severity-dependent errors. Until
those are demonstrated locally, show the corrected estimate beside—not in
place of—the raw confusion matrix and slice report.

### Adaptive and IRT-based evaluation

[Computerized adaptive testing for LLM medical benchmarking](https://www.nature.com/articles/s41746-026-02671-w)
reports near-full-bank rank agreement across 38 models while using a small
fraction of a calibrated knowledge bank. That is a peer-reviewed benchmark
study, not deployment evidence, and the authors explicitly separate it from
clinical validation and prospective safety evaluation.

A later [IRT reliability study](https://arxiv.org/abs/2607.15190) tests 18,000
simulated conditions and finds that small, skewed, clustered, or multimodal
model populations can make item parameters and ranks unreliable. Practical use
therefore requires model-fit diagnostics, a stable item bank, exposure and
contamination controls, rank-stability checks, and a mandatory non-adaptive
safety/regression core. Adaptive selection may reduce cost; it must not route
around rare, protected-slice, or hard-invariant cases. No public production
deployment proof was found for adaptive/IRT LLM release gating.

#### Micro-kata: the most informative item is not the whole release suite

For an authored one-parameter logistic teaching model, assume item difficulty `b` is already calibrated and candidate ability is currently estimated as `theta = 0`. Define success probability as `p = 1 / (1 + exp(b - theta))`. With unit discrimination and the model's local-independence assumption, item information about ability is `p * (1 - p)`.

**Exercise:** compare difficulties -2, 0 and 2. Which unused item is most informative at the current estimate? May the runner omit a mandatory authorization scenario with low information?

```python
from math import exp
theta = 0
information = {}
for b in [-2, 0, 2]:
    p = 1 / (1 + exp(b - theta))
    information[b] = p * (1 - p)
assert max(information, key=information.get) == 0
print([round(information[b], 6) for b in [-2, 0, 2]])
# [0.104994, 0.25, 0.104994]
```

**Solution:** choose difficulty 0 among these optional items; its modeled success probability is 0.5. After observing a response, update the ability estimate under a registered fitting procedure and select again from unused eligible items. Stop under a registered precision/budget rule, not when a favorable answer arrives. An exhausted budget with inadequate precision remains inconclusive.

The authorization scenario still runs: information about this modeled ability is not information about every safety property. This calculation assumes item parameters rather than estimating them, supplies no fitted uncertainty interval and does not qualify an adaptive evaluator. Before using one, test item-bank fit, parameter uncertainty, correlated tasks, population shift and rank stability against full-bank held-out results. Preserve the independent mandatory regression/safety suite.

### Adaptive security testing

[Adaptive attacks on indirect prompt-injection defenses](https://aclanthology.org/2025.findings-naacl.395/)
show why a static attack suite can overstate security. This is peer-reviewed
attack evidence, not proof of a deployed defense. A release programme should
red-team the exact prompt, retriever, tools, permissions, and detectors; keep a
held-out attack budget; record attacker knowledge; and require external
authorization and effect-boundary controls even when model-level defenses look
strong.

### Hidden objectives and long-horizon behavior

[Auditing language models for hidden objectives](https://arxiv.org/abs/2503.10965)
is a controlled audit game using a deliberately trained model organism. Three
of four blind teams found its hidden objective with a mixture of behavioral,
interpretability, and training-data methods. This validates an audit exercise,
not reliable detection of unknown objectives in deployed models.

Long-horizon benchmarks similarly provide useful instruments. They must be
augmented with real task state, irreversible-action controls, compaction and
memory behavior, latency/cost budgets, evaluator isolation, and post-release
incident evidence before they support deployment claims.

## What the evidence does not prove

Across all rows, public disclosure does **not** automatically establish:

- causal improvement in incidents or user outcomes;
- coverage of undisclosed failure modes, languages, users, or environments;
- independence of auditors, simulators, judges, and target models;
- suitability for a different product, model, scaffold, or risk tolerance;
- that the method alone had release authority;
- that a reported absence of failures means zero risk.

Use the strongest precise wording: “used in Anthropic’s disclosed alignment
assessment” is better than “industry proven”; “observed across 800 users” is
better than “production-ready personalization eval.”

## Worked example: qualifying a research method

A team reproduces Five-Nines on its refund assistant and obtains an estimated
unauthorized-refund rate of 8 per million with a narrow interval. Can the metric
block or approve release?

**Not yet.** The reproduction establishes that code ran and produced an
estimate. It does not establish target-population coverage or unbiased tail
sampling. The team should:

1. recover known failure rates in a synthetic world with complete enumeration;
2. compare the estimator with naive sampling where both are feasible;
3. inspect proposal support, weight concentration, and effective sample size;
4. validate generator slices against consented production inputs and incidents;
5. run the estimator in shadow through several release cycles;
6. compare predictions with canary and post-release outcomes;
7. register the scope, interval, hard controls, and escalation rule.

Only then may a review board grant narrow local authority. Even after
qualification, zero-tolerance transaction invariants remain deterministic and
non-compensable.

## Artifact: practice-evidence ledger

The inspectable companion is
`evals/cx-support/examples/practice-evidence-v1.json`. Each claim records:

```json
{
  "topic_id": "rare_failure_estimation",
  "evidence_level": "research_or_benchmark",
  "observed_use": "CEM importance sampling evaluated on parameterized GSM8K templates",
  "not_proven": "No public production deployment or release-gate evidence found",
  "current_local_authority": "not_gating",
  "eligible_authority_after_qualification": "shadow_only"
}
```

The test suite rejects missing sources, missing non-claims, unknown evidence
levels, and accidental gate authority. “No public deployment proof found” is a
dated evidence statement—not proof that no private deployment exists.

## Adoption contract

For any emerging technique:

```yaml
claim:
  wording: precise, scoped statement
  as_of: YYYY-MM-DD
  evidence_level: production_control | field_evidence | operational_tool | research_or_benchmark
proof:
  primary_sources: []
  named_organization_and_use: required_for_production_control
  observed_outcome: null
limits:
  not_proven: []
local_validation:
  construct: required
  dataset_and_slices: required
  evaluator: required
  environment: required
  offline_to_live_check: required_for_gate
authority:
  current_local_authority: not_gating
  eligible_authority_after_qualification: shadow_only | qualified_local_only
revalidate_on: [model, scaffold, data, evaluator, traffic_shift, material_incident]
```

External production use earns attention, not inherited authority. Authority is
always local, versioned, bounded to a claim and slice, and revocable.

## Exercise: make three defensible claims

Classify each statement and rewrite it as a claim the evidence supports:

1. “Petri is production-proven for all alignment failures.”
2. “A Five-Nines reproduction proves our agent is 99.999% reliable.”
3. “GPT-4o’s system card proves voice evaluation is deployed.”

??? success "Answer outline"
    1. **Production control, narrow:** Anthropic discloses Petri use in Claude
       alignment assessments since Sonnet 4.5; this does not prove exhaustive
       coverage or sole gate authority.
    2. **Research/local experiment:** the reproduction supports only the
       registered generator, proposal, estimator, and environment; production
       reliability requires population validation and offline-to-live checks.
    3. **Production control, partial:** the card documents audio-specific
       pre-deployment safety evaluation and mitigations. It does not establish
       a complete voice quality, latency, interruption, and business-outcome
       system.

## Primary reading

- [OpenAI — Predicting model behavior before release by simulating deployment](https://openai.com/index/deployment-simulation/)
- [Anthropic — Donating our open-source alignment tool](https://www.anthropic.com/research/donating-open-source-petri)
- [OpenAI — Evaluating chain-of-thought monitorability](https://openai.com/index/evaluating-chain-of-thought-monitorability/)
- [OpenAI — GPT-4o System Card](https://openai.com/index/gpt-4o-system-card/)
- [Wang, Ho, and Koyejo — The Inadequacy of Offline LLM Evaluations](https://arxiv.org/abs/2509.19364)
- [Kim et al. — Measuring Five-Nines Reliability](https://arxiv.org/abs/2605.11209)
- [Lù et al. — AgentRewardBench](https://arxiv.org/abs/2504.08942)
- [Lee et al. — How to Correctly Report LLM-as-a-Judge Evaluations](https://arxiv.org/abs/2511.21140)
- [Zheng et al. — Computerized adaptive testing for LLM medical benchmarking](https://www.nature.com/articles/s41746-026-02671-w)
- [Jiang et al. — Can We Trust Item Response Theory for AI Evaluation?](https://arxiv.org/abs/2607.15190)
- [Zhan et al. — Adaptive Attacks Break Indirect Prompt Injection Defenses](https://aclanthology.org/2025.findings-naacl.395/)
- [Marks et al. — Auditing language models for hidden objectives](https://arxiv.org/abs/2503.10965)
