# RAG & Research Evals

A retrieval-augmented system can produce a correct answer for the wrong reason, retrieve excellent evidence and ignore it, or cite authoritative material that does not support its claim. End-to-end accuracy alone cannot distinguish these failures.

Research agents add time, browsing strategy, source authority, synthesis, and search-budget questions. Evaluate the pipeline and the final product.

## Decompose the system

Use a causal map before selecting metrics:

```text
user need
→ query interpretation
→ retrieval/search
→ ranking and filtering
→ context construction
→ answer generation
→ claim and citation attachment
→ user-facing synthesis
→ verified task outcome
```

| Layer | Core question | Evidence |
| --- | --- | --- |
| Query | Did the system search for the right thing? | Search queries and filters |
| Retrieval | Did it find the necessary material? | Ranked documents and relevance labels |
| Context | Was useful evidence included without destructive noise? | Prompt context and token allocation |
| Generation | Does the response answer the question? | Response and reference criteria |
| Grounding | Are material claims supported by supplied evidence? | Claim-to-evidence links |
| Citation | Does each citation point to the right source and passage? | URLs, document IDs, spans, timestamps |
| Research quality | Are sources authoritative, diverse, current, and synthesized correctly? | Source metadata and report structure |
| Outcome | Did the user’s real task succeed? | Downstream decision or verified state |

## Build a retrieval test collection

A retrieval case needs more than a query and one preferred document.

```yaml
case_id: rag-refund-timeout-001
query: "Was my refund completed after the app timed out?"
relevant_evidence:
  required:
    - doc_id: refund-ledger-order-817
      passage_id: transaction-state
    - doc_id: refund-policy-v3
      passage_id: timeout-after-commit
  useful:
    - doc_id: customer-message-guide-v2
      passage_id: pending-language
  prohibited_or_stale:
    - doc_id: refund-policy-v1
      reason: superseded
as_of: 2026-09-01T00:00:00Z
```

Some questions have several sufficient evidence sets. Labeling only one document as relevant can punish a valid retrieval path.

## Retrieval metrics

Let \(R\) be the relevant documents and \(K\) the first \(k\) retrieved documents.

**Recall@k** asks how much required evidence was found:

\[
\text{Recall@k} = \frac{|R \cap K|}{|R|}
\]

**Precision@k** asks how much of the retrieved set was relevant:

\[
\text{Precision@k} = \frac{|R \cap K|}{k}
\]

Use **MRR** when one early decisive result matters. Use **nDCG** when graded relevance and ordering matter. These metrics require defensible relevance labels and do not prove that generation used the evidence.

Also measure:

- evidence-set completeness;
- stale-source retrieval;
- source-authority distribution;
- retrieval diversity when corroboration is required;
- query and filter correctness;
- latency and cost;
- sensitivity to chunking, index, embeddings, reranker, and top-k.

## Evaluate context construction

High recall can still damage generation when the context contains contradictions, duplicated chunks, stale policies, or irrelevant distractors. Record:

- selected document and passage IDs;
- document versions and effective dates;
- ordering;
- token counts and truncation;
- duplicate content;
- trust level and instruction/data boundary;
- material evidence omitted during context packing.

Test context perturbations: remove the decisive passage, add a plausible stale policy, reorder evidence, or insert irrelevant instructions. The answer should change only when the evidence or correct decision changes.

## Decompose answers into atomic claims

A long answer can mix supported and unsupported statements. Split it into the smallest independently verifiable propositions.

Example answer:

> Your refund was completed yesterday and should reach your bank within three days.

Atomic claims:

1. A refund transaction was completed.
2. Completion occurred yesterday.
3. The funds should reach the bank within three days.

For each atomic claim record:

- materiality;
- cited source and passage;
- `supported`, `contradicted`, `unsupported`, or `not_verifiable`;
- whether the claim was necessary;
- temporal scope;
- reviewer or grader version.

Useful summaries include claim precision, material-claim support, contradiction rate, and citation coverage. Keep the claim table visible; one aggregate groundedness number is diagnostic shorthand.

## Separate correctness from groundedness

| Answer state | Correct? | Grounded in supplied evidence? | Interpretation |
| --- | ---: | ---: | --- |
| Correct and supported | yes | yes | Desired |
| Correct by luck | yes | no | Retrieval or attribution failure |
| Faithfully repeats stale evidence | no | yes | Data freshness or source-selection failure |
| Unsupported and wrong | no | no | Combined failure |

Groundedness cannot replace truth when the evidence store is wrong. Truth cannot replace grounding when the application promises traceable answers.

## Evaluate citations as links, not decoration

Citation quality has at least four dimensions:

1. **Entailment:** the cited passage supports the associated claim.
2. **Completeness:** material verifiable claims have citations.
3. **Correctness:** the citation resolves to the intended document and passage.
4. **Quality:** the source is appropriate for the claim.

A report with many citations can have low completeness if the uncited claims carry the decision. A citation to a real source can still fail entailment.

## Source authority and diversity

Authority depends on the question. Prefer primary law for legal requirements, official product documentation for API behavior, and original papers for research claims. A vendor comparison is not independent evidence about the vendor.

Record source attributes:

```json
{
  "source_id": "refund-policy-v3",
  "publisher": "synthetic-bank-policy-owner",
  "source_type": "first_party_policy",
  "effective_from": "2026-08-01",
  "retrieved_at": "2026-09-06T10:15:00Z",
  "authority": "authoritative_for_refund_rules",
  "supersedes": "refund-policy-v2"
}
```

Source diversity matters when independent corroboration is part of the task. Repeating five articles derived from one press release is not five independent sources.

## Temporal validity and live-web fragility

Live sources change, disappear, or become inaccessible. A research-agent run must record the `as_of` time, retrieved content fingerprint, and access outcome. Separate:

- answer was correct at evaluation time;
- citation still resolves now;
- underlying fact remains current;
- benchmark reference is stale;
- source changed after the run.

For reproducible regression tests, use a frozen document collection. For current-information capability, use live evaluation with time-bounded reference construction and review. Do not present the two as the same claim.

## Research benchmark map and validity lessons

Research-agent benchmarks isolate different constructs. A high score on one does not stand in for a complete, current, well-cited report.

| Evaluation | Primary construct | What it does not establish | Integrity or maintenance lesson |
| --- | --- | --- | --- |
| [Humanity’s Last Exam (HLE)](https://agi.safe.ai/) | Frontier expert knowledge and reasoning across many subjects | Open-ended research process, source quality, or citation completeness | Launch-era descriptions and the later official project used different item counts after curation; bind every historical score to the exact dataset revision |
| [GAIA](https://huggingface.co/gaia-benchmark) | Tool-using assistant tasks combining reasoning, browsing, files, and multimodality | Long-report coverage and synthesis quality | OpenAI reported that some answer material had leaked online and blocked known sites during its evaluation |
| [BrowseComp](https://openai.com/index/browsecomp/) | Persistent browsing for obscure facts with short, verifiable answers | Normal user-query ecology or long-form research validity | Keep answer material non-crawlable, use canaries/access controls, and audit suspicious retrieval paths |
| Frozen-web research tasks | Reproducible search and synthesis against a captured corpus | Current-information behavior on today’s changing web | Content hashes and corpus version improve reproduction but narrow temporal validity |
| Long-form report evaluation | Decomposition, source authority, citations, synthesis, uncertainty, and completeness | Cheap deterministic scoring | Requires adapted rubrics, claim-level evidence, calibrated judges, and targeted human review |

### Historical configuration snapshot—not a current ranking

The supplied research corpus preserves this launch-era evidence from OpenAI's first-party Deep Research publications. It belongs here as a protocol example, not as a 2026 model leaderboard:

| Publication/evaluation | Historical evaluated configuration | Historical result | What the number means |
| --- | --- | ---: | --- |
| February 2025 launch · HLE | Deep Research with browsing and Python | 26.6% accuracy | Correct answers on that HLE revision under that tool configuration |
| February 2025 launch · GAIA Level 1/2/3 | Deep Research, pass@1 | 74.29% / 69.06% / 47.6% | Single-trial success by difficulty level |
| February 2025 launch · GAIA aggregate | Same publication | 67.36% pass@1; 72.57% cons@64 | One run versus an aggregation procedure over up to 64 samples; not deployed single-run reliability |
| April 2025 BrowseComp | Early Deep Research browsing agent | 51.5% accuracy on 1,266 questions | Short-answer obscure-fact retrieval under the published browsing protocol |
| April 2025 BrowseComp comparison | GPT-4o with browsing in the same publication | 1.9% | Historical within-publication comparator, not a general product ranking |

Record model/checkpoint, agent scaffold, tools, browsing policy, prompt, maximum tool calls, sample count, aggregation, data revision, scorer, and date beside every result. Without them, even a correctly copied percentage is not reproducible.

### HLE version change

The January 2025 HLE paper described roughly 3,000 questions, while the subsequently curated official project described 2,500. This does not invalidate either artifact. It means “HLE score” is incomplete without the task version, split, prompting, tools, answer extraction, budget, and evaluation date. Never compare a historical launch score with a current run by name alone.

A minimum HLE comparison record therefore contains both the content identity and the execution identity:

```yaml
benchmark: hle
dataset_revision: exact_commit_or_release
item_count: 2500_or_3000_as_applicable
split_hash: sha256:...
prompt_and_extractor: versioned
tools: [browser, python]
sampling_and_aggregation: declared
result_date: YYYY-MM-DD
```

If the old item set cannot be reconstructed, retain the historical number as historical evidence and decline a direct delta claim.

### GAIA answer-key leakage

In its Deep Research launch material, OpenAI said GAIA ground-truth answers had leaked widely online and that known sites or URLs were blocked during evaluation. A browsing agent that retrieves an answer key has demonstrated search behavior but has not necessarily solved the intended task. Capture retrieval logs, separate evaluator credentials, probe for task-detail reproduction, and keep attempted/compromised denominators visible.

Two trials can return the same correct string but have different validity:

| Trial | Trace | Outcome label | Capability inference |
| --- | --- | --- | --- |
| A | Finds primary evidence, calculates the answer, cites the derivation | correct and clean | Supports the registered task claim |
| B | Searches the benchmark wording, opens an answer mirror, copies the label | correct but compromised | Security/eval-awareness finding; does not support problem-solving accuracy |

Blocking known URLs is one control, not proof of clean evaluation: mirrors, snippets, model memory, or new pages may remain. Combine sealed tasks, egress/access logging, canaries, task-detail probes, and post-run investigation.

### PersonQA and stale references

The Deep Research system card describes PersonQA cases initially counted as hallucinations where the live-web answer was current and the reference had become stale. This is the inverse of ordinary hallucination: the measuring instrument is wrong. Send reference–evidence conflicts to dated adjudication, retain the original label, issue a versioned correction, and replay historical outputs under both scorer versions before changing a trend.

```yaml
label_correction_receipt:
  case_id: personqa-example
  original_reference: value_A
  candidate_answer: value_B
  current_primary_evidence: source_id_and_as_of_time
  adjudication: reference_stale
  old_scorer_result: fail
  new_scorer_result: pass
  history_policy: preserve_both_and_restate_trend
```

The correction process needs reviewer authority and evidence dates. Otherwise teams can relabel inconvenient failures after seeing the candidate.

### Long-output adaptation

Long reports cannot be evaluated by dropping them into short-answer exact match. Adapt the protocol through subquestion coverage, atomic claims, citation entailment/completeness, source quality, contradiction handling, and calibrated report-level review. Preserve which parts were evaluated automatically and which required humans; a single report score hides too many causal stages.

#### Worked example: a long report passes the short answer and fails the report

Synthetic task: *Explain how a refund agent should recover from a timeout after commit, including evidence, customer wording, and rollout implications.* The report contains the short target “inspect the ledger before retrying,” so a short-answer grader passes it. The complete review finds:

| Report criterion | Result | Evidence |
| --- | ---: | --- |
| Short target present | pass | Correct recovery phrase appears |
| Required subquestions covered | 2/5 | Omits idempotency, customer claim boundary, and release follow-up |
| Material atomic claims supported | 3/5 | Two operational claims have no source |
| Current authoritative sources | 1/2 | One cited policy is superseded |
| Contradictions addressed | 0/1 | Current and stale retry policies are not reconciled |
| Citation entailment | 3/5 | Two citations resolve but do not support the attached claim |
| Decision | fail | Correct short answer is insufficient for the report contract |

```yaml
long_report_evaluation:
  unit: report
  deterministic:
    required_sections_present: false
    citations_resolve: 5/5
  claim_level:
    supported_material_claims: 3/5
    entailing_claim_citation_links: 3/5
  research_process:
    required_subquestions_covered: 2/5
    stale_authoritative_sources: 1
    contradictions_unresolved: 1
  human_or_qualified_judge:
    synthesis: weak
    uncertainty_handling: fail
  decision: fail
```

This artifact reveals why “the answer was in the report” and “the report was trustworthy” are different claims.

### Safety and uncertainty methodology

The Deep Research system card broadens capability evaluation to prompt injection, disallowed content, StrongReject-style jailbreak testing, risky-advice comparisons, personal-data policy, BBQ bias, PersonQA factuality, cybersecurity, CBRN, persuasion, and model autonomy. It also reports pass@1 with 95% bootstrap confidence intervals for relevant evaluations rather than only point estimates.

Historical findings must retain their scope. The card reported post-mitigation attack success of 0% on several tested text attacks while one tested multimodal random-location attack remained at 2.63%; that is evidence about those attacks, not proof of zero prompt-injection risk. It also reported 95% correctness for answerable BBQ questions and 63% on an ambiguous split, where reluctance to answer `Unknown` mattered. The operational lesson is to report harmful compliance and false refusal/over-answering separately, with attack family, modality, denominator, interval, and residual limitation.

For long reports, uncertainty evaluation should include:

- whether the system qualifies claims when sources conflict;
- whether confidence tracks claim correctness, not merely fluent tone;
- whether missing evidence triggers scoped abstention rather than a blank refusal;
- class-conditional errors on harmful and benign cases;
- slices for modality, language, source freshness, and attack family;
- the exact configuration used for ordinary deployment and for risk elicitation.

### Deployed versus capability-eliciting evaluation

The Deep Research system card distinguishes evaluation of the deployed system from capability-eliciting configurations used for risk assessment. Both can be valid, but they answer different questions:

- **deployed-system evaluation** estimates behavior under actual prompts, tools, safeguards, budgets, and policies;
- **capability-eliciting evaluation** deliberately relaxes or optimizes scaffolding to ask what the underlying system could do under stronger elicitation.

Report the configuration and inference separately. Do not advertise an elicited maximum as deployed reliability, and do not infer absence of latent capability from a constrained production configuration.

#### Worked example: deployed and capability-eliciting configurations

Run the same ten synthetic research tasks under two manifests:

| Configuration | Prompt/tools/budget | Success | Severe policy failures | Valid claim |
| --- | --- | ---: | ---: | --- |
| Deployed | Production prompt, allow-listed browser, safeguards on, 8-page budget | 6/10 | 0/10 observed | 60% on this deployed synthetic protocol |
| Capability-eliciting | Researcher scaffold, broader tools, safeguards deliberately varied, 40-page budget, four attempts | 9/10 | Report by elicitation condition | Latent capability under stronger elicitation; not production reliability |

The comparison is intentionally synthetic. It teaches the inference boundary: changing tools, attempts, safety controls, and budget changes the system under test. The eliciting run is valuable for preparedness and upper-bound discovery; the deployed run is authoritative for the shipped configuration.

## Artifact: Deep Research evaluation claim record

```yaml
claim_id: dr-historical-gaia-aggregate-2025-02
claim: launch-era Deep Research achieved 67.36% GAIA pass@1
evidence_type: first_party_historical_result
source: OpenAI Introducing Deep Research
source_date: 2025-02-02
evaluated_object:
  model_and_agent: launch-era Deep Research configuration
  tools: [browser, python]
  dataset: GAIA revision used by publication
metric:
  name: pass@1
  result: 0.6736
comparison_only:
  cons_at_64: 0.7257
integrity_caveat: OpenAI reported public answer leakage and URL blocking
does_not_establish:
  - current-model ranking
  - long-form report quality
  - deployed single-run reliability of 72.57%
revalidate_when:
  - dataset_or_answer_environment_changes
  - model_scaffold_tools_or_budget_changes
```

The same shape works for HLE, BrowseComp, safety, or a local research suite: one scoped claim, exact evaluated object, metric, result, validity caveat, and explicit non-claims.

## Exercise: audit a research-agent claim

A stakeholder says: “The agent scored 51.5% on BrowseComp and 72.57% on GAIA cons@64, so it will produce trustworthy long reports at least 72% of the time in production.” Rewrite this as the strongest defensible claims and design the missing evaluation.

??? success "Answer"
    Preserve both as historical protocol-specific results: 51.5% short-answer accuracy on the published 1,266-item BrowseComp evaluation and 72.57% GAIA consistency/aggregation result over up to 64 samples in the launch publication. Neither is a production single-run long-report rate. For the product claim, sample representative and risk-enriched research tasks; pin the deployed prompt, tools, web access, and budgets; evaluate decomposition, evidence coverage, atomic correctness/support, citation entailment/quality, freshness, contradictions, uncertainty, safety, cost, and latency; use qualified human/judge review; report denominators, slices, intervals, abstentions, compromised trials, and offline-to-live validation. Compare any eliciting configuration separately.

## Evaluate research completeness

Short-answer benchmarks reward finding a specific fact. A research report additionally needs:

- question decomposition;
- coverage of material subquestions;
- source selection and authority;
- evidence-to-claim support;
- treatment of disagreement and uncertainty;
- temporal scope;
- synthesis rather than source concatenation;
- calibrated abstention;
- cost, latency, and search budget.

Create an explicit coverage map:

| Required subquestion | Evidence found? | Addressed in report? | Status |
| --- | ---: | ---: | --- |
| Current refund eligibility rule | yes | yes | covered |
| State after timeout | yes | yes | covered |
| Bank settlement timing | no | no | correctly abstained |
| Customer next step | yes | yes | covered |

## Search budget and test-time compute

More search steps can improve recall while increasing cost and latency. Plot task success or evidence coverage against:

- searches;
- pages opened;
- tool calls;
- tokens;
- elapsed time;
- monetary cost.

Compare agents at equivalent budgets when making efficiency claims. `pass@k` can show whether repeated attempts reveal capability; it does not show that the deployed single-run policy is reliable or affordable.

## Appropriate abstention

An agent should abstain or qualify a claim when required evidence is missing, contradictory, stale beyond policy, or outside its authority. Evaluate both:

- unsupported answers that should have abstained;
- excessive abstentions where sufficient evidence existed.

This produces a risk–coverage trade-off: higher coverage is not better if unsupported material claims increase faster.

## Worked example: refund status RAG

Synthetic evidence store:

```text
[policy-v3 §4.2] If a write times out, inspect the ledger before retrying.
[ledger order-817] refund_id=r-91, state=submitted, submitted_at=10:02Z
[guide-v2 §2] Describe submitted refunds as pending; do not promise settlement time.
[policy-v1 §4.2] Retry once after any timeout.  (superseded)
```

Candidate response:

> Your refund completed at 10:02 and will reach your bank in three days [ledger order-817].

Claim grading:

| Claim | Evidence | Verdict | Failure owner |
| --- | --- | --- | --- |
| The refund completed. | Ledger says submitted | contradicted | generation |
| A refund event occurred at 10:02Z. | `submitted_at=10:02Z` | supported as a submission event, not completion | generation/wording |
| The funds will reach the bank within three days. | No settlement evidence | unsupported; current truth not verified | generation |
| Citation identifies ledger | Correct document | resolves; entails the submission-time subclaim but not completion or bank timing | citation grader |

Retrieval found the decisive current evidence, so retrieval recall is not the root cause. The agent misread state and invented timing. The correct repair targets generation/rubric behavior, not the index.

## Artifact: research-evaluation record

```yaml
run_id: research-refund-817-rc2
question: "Did my refund complete and when will it arrive?"
as_of: 2026-09-06T10:10:00Z
budget:
  max_searches: 4
  max_pages: 8
  max_elapsed_ms: 10000
retrieval:
  index_version: policy-index-v5
  required_evidence_recall_at_5: 1.0
  stale_sources_retrieved: 1
answer:
  atomic_claims: 3
  supported: 1
  contradicted: 1
  unsupported: 1
citations:
  resolving: 1
  atomic_claim_links: 3
  entailing: 1
  unsupported_or_contradicted: 2
decision: fail
failure_stage: generation
```

The numbers are synthetic and illustrative. The artifact shape is the lesson.

## Failure modes

| Failure mode | Misleading conclusion | Repair |
| --- | --- | --- |
| End-to-end score only | “RAG is bad” | Grade query, retrieval, context, claims, and outcome separately |
| One reference document | Valid alternative evidence is marked wrong | Label sufficient evidence sets |
| Grounded means true | Stale evidence produces confident errors | Evaluate freshness and authority |
| Citation count | Decorative links look rigorous | Check claim-level entailment and completeness |
| Live web without snapshots | Result cannot be reproduced | Record time, content fingerprints, and access state |
| Unlimited browsing | Accuracy gain hides cost | Compare within registered budgets |
| One binary hallucination label | Mixed long answers lose diagnosis | Decompose material atomic claims |
| No abstention check | Agent guesses or refuses everything | Measure both unsupported answers and excess abstention |

## Exercise: localize the failure

The retriever returns the current policy at rank 1 and a stale policy at rank 2. The context builder truncates rank 1 and includes all of rank 2. The model follows the stale retry instruction and creates a duplicate refund.

Name the first causal failure, downstream symptoms, and minimum regression coverage.

??? success "Answer"
    Retrieval found the required current source, so raw recall is not the first failure. Context construction truncated the decisive current passage and privileged stale evidence. The downstream trajectory and outcome failures are an unsafe retry and duplicate transaction. Add a context-packing test that preserves required passages, a stale-source handling case, a trajectory rule requiring ledger inspection after timeout, and a final-state duplicate-refund invariant. Keep all four because each localizes a different layer.

## Verification checklist

- [ ] Retrieval and generation are scored separately.
- [ ] Required evidence sets allow valid alternatives.
- [ ] Index, documents, passages, and effective dates are versioned.
- [ ] Material claims are decomposed and linked to evidence.
- [ ] Citations are checked for resolution, entailment, completeness, and quality.
- [ ] Current-information runs record time and content fingerprints.
- [ ] Search quality is compared within a registered budget.
- [ ] Abstention and excess abstention are both measured.
- [ ] The first causal failure is separated from downstream symptoms.

## Primary reading

!!! note "Research-to-practice boundary: personalization and memory"
    [Research-to-Practice Evidence](research-to-practice.md#personalization-and-persistent-memory)
    adds real-user field evidence, reset-versus-persist comparison, counter-user
    controls, preference-update cases, and the limits of long-memory benchmarks.

- [FActScore: Fine-grained Atomic Evaluation of Factual Precision](https://arxiv.org/abs/2305.14251)
- [RAGAS: Automated Evaluation of Retrieval Augmented Generation](https://arxiv.org/abs/2309.15217)
- [GAIA: a benchmark for General AI Assistants](https://arxiv.org/abs/2311.12983)
- [BrowseComp: a benchmark for browsing agents](https://openai.com/index/browsecomp/)
- [OpenAI Deep Research system card](https://openai.com/index/deep-research-system-card/)
- [OpenAI — Introducing Deep Research](https://openai.com/index/introducing-deep-research/)
- [Humanity’s Last Exam](https://agi.safe.ai/)
- [GAIA benchmark](https://huggingface.co/gaia-benchmark)
