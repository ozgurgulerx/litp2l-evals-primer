# RAG & Research Evals

A retrieval-augmented system can produce a correct answer for the wrong reason, retrieve excellent evidence and ignore it, or cite authoritative material that does not support its claim. End-to-end accuracy alone cannot distinguish these failures.

Research agents add time, browsing strategy, source authority, synthesis, and search-budget questions. Evaluate the pipeline and the final product.

For state-changing tasks, follow this chapter with the [Knowledge-to-Action Study](knowledge-action-study.md): Katas 51–53 connect corpus coverage and supplied evidence to actual policy decisions, attempted tool arguments and mock ledger outcomes. A retrieval repair is not automatically an action repair.

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

### Executed study: retrieved evidence that never reaches the agent

The retriever finds both current policy facts, but the agent receives neither. A recent promotional passage occupies the context budget before the policy passages are considered.

The [retained context-packing study](assets/context-packing-v1.json) separates four stages: lexical ranking, candidate selection, context packing and final action. Its five-passage corpus contains a current refund-window rule, an exact duplicate of that passage, a current maximum-refund rule, a stale rule and a long recent promotion. The two current rules are separate required **evidence units**. Two copies of the window rule still supply only one unit.

The deterministic policy control requires the complete two-fact bundle before deciding. It parses structured fields in the actual packed JSON body; it does not understand natural-language policy prose. Missing or conflicting facts cause abstention. The bundle requirement is this exercise's registered contract, not a theorem that every denial needs both facts: a different contract might permit a justified short-circuit denial, which would need its own evidence rules.

Three constructed requests exercise an allowed refund, a purchase outside the refund window and an amount above the permitted maximum. Every trial starts with an empty mock ledger. The backend independently enforces both limits; neither a favorable retrieval score nor the agent's intended action can alter those checks.

Four arms times two controls times three cases produce **24 deterministic local executions**. The three customer IDs are constructed examples, not a sampled customer population. The promotion uses deliberate multibyte padding to make byte accounting observable; this is not a natural-language relevance benchmark.

### Kata 68: why did increasing top-k reduce packed evidence?

**Predict:** a fixed lexical ranking is used in both arms. Top-2 returns two copies of the window passage; top-5 additionally returns the limit, stale rule and promotion. Can packed evidence get worse if the packer processes the original ranking in order? What changes when it first sorts selected passages by recency?

```bash
uv run python -m cx_eval_lab.context_packing --output /tmp/context-packing-study.json
uv run python -m unittest tests.test_context_packing -v
```

Use a new output path for a subsequent run. Inspect the rankings, selected candidates, packing decisions, exact serialized body and final ledger—not just the grade. This study makes no model calls, uses no production traffic and reports no inference-cost or service-latency result.

| Arm | Retrieved current evidence units | Packed current evidence units | Correct-control contracts |
| --- | --- | --- | --- |
| Top-2, recency-first packing | 1/2 | 1/2 | 0/3 |
| Top-5, same recency-first packing | 2/2 | 0/2 | 0/3 |
| Top-5, metadata filtering and exact deduplication | 2/2 | 2/2 | 3/3 |
| Oracle evidence, same context budget | 2/2 | 2/2 | 3/3 |

These are evidence-unit recalls within this constructed corpus, not document-level Recall@k estimates for a retrieval service. The oracle row describes supplied reference evidence rather than the quality of an operational search algorithm.

The shared body budget is **240 UTF-8 bytes**. Top-2 packs `window-copy` and `window` in 141 bytes; top-5 packs only `promo` in 191 bytes. The repair and oracle each pack `limit` and `window` in 136 bytes. After packing the promotion, adding the limit would require 256 bytes; adding a window passage would require 261 bytes. The exclusion is visible in the packing trace rather than inferred from the final answer.

```python
import json
from pathlib import Path
from cx_eval_lab.context_packing import pack_passages, rank_passages, replay_study

study = json.loads(Path("docs/assets/context-packing-v1.json").read_text())
assert len(replay_study(study)) == 24
trials = {t["payload"]["arm"]: t["payload"] for t in study["trials"]
          if t["payload"]["agent"] == "policy-control" and t["payload"]["case_id"] == "eligible"}
for arm in ("top2", "top5", "filtered-top5", "oracle"):
    trial = trials[arm]
    body_bytes = len(trial["agent_input"]["context_body"].encode("utf-8"))
    assert body_bytes == trial["packed_bytes"] <= study["inputs"]["budget_bytes"]
    print(arm, trial["packed_ids"], body_bytes, trial["decision"]["action"])
assert trials["top5"]["grade"]["retrieved_evidence_unit_recall"] == 1
assert trials["top5"]["grade"]["packed_evidence_unit_recall"] == 0

# Component-level counterfactual: preserve the original ranking instead of reordering.
inputs = study["inputs"]
lookup = {p["passage_id"]: p for p in inputs["passages"]}
ranked = [lookup[r["passage_id"]] for r in rank_passages(inputs["query"], inputs["passages"])]
short, _, _ = pack_passages(ranked[:2], inputs["budget_bytes"], recency_first=False)
long, _, _ = pack_passages(ranked[:5], inputs["budget_bytes"], recency_first=False)
assert {p["passage_id"] for p in short}.issubset({p["passage_id"] for p in long})
```

The last check is a packing-component counterfactual, not a fifth registered end-to-end arm. It changes ordering alone to test the proposed explanation; it does not collect an additional model observation.

??? success "Solution: identify the packing interaction, not an inevitable top-k penalty"
    Under a fixed ranking and an append-only packer with the same budget, extending the candidate prefix cannot evict a passage already accepted from the earlier prefix. It may add nothing, but previously packed evidence stays packed. An observed loss therefore needs an explanation: reordering, changed chunk allocation, truncation, a different filter, or some other change to context construction.

    Here the policy is explicitly **recency-first after retrieval**. The top-5 candidate set introduces a long promotional passage with the highest recency. It is processed first and fits. Remaining space cannot hold the other whole passages. The top-2 candidate set does not contain that promotion, so its window passages survive. Increasing k improves retrieved-unit recall from one-half to one while reducing packed-unit recall from one-half to zero **under this packing policy**. Neither incomplete context earns a successful policy decision.

    The duplicate passage inflates a document count without adding a distinct policy condition. The stale rule cannot substitute for the current window unit, even if its wording overlaps the query. Record source identity, content identity, version and the reference evidence unit separately. Otherwise duplication and stale evidence can make “coverage” look better while leaving the task unsupported.

    The budget measures UTF-8 bytes of the serialized document body, including structured fields and JSON syntax. It is not a model-token budget or a total prompt budget; request text and any outer prompt wrapper are outside this quantity. The retained body lets a reader recompute it. A real model experiment must account for the provider's actual input format and tokenizer, plus request, tool definitions and other context.

**Interview answer criteria:** distinguish retrieved from packed evidence; explain the prefix-monotonicity condition; identify recency reordering as the interaction; define what the budget includes; avoid counting an exact duplicate as new evidence.

### Kata 69: repair packing without giving the retriever the answers

**Predict:** how can the non-oracle repair retain both policy units under the same budget? Once both facts are present, must the final action be correct?

The repair uses configured source metadata: the active policy version and authoritative source kind. It excludes stale and promotional material, then deduplicates identical content before packing. These are harness inputs that must be maintained and trusted; they are not an automatic discovery of authority. The repair does not use the evaluator's reference evidence units or expected decisions. The oracle arm does use reference evidence and is labelled as a diagnostic intervention.

??? success "Solution: distinguish an evidence repair from an action repair"
    First check the rejection trace. Stale-version and non-authoritative-source exclusions should be attributable to registered metadata rules. A repeated content body should be marked as a duplicate, not counted as an additional policy unit. Then verify the remaining serialized context fits the same budget and actually contains both facts. A report that lists the right passage IDs while omitting their content does not establish that the agent received them.

    Metadata filtering and deduplication repair this constructed packing failure. The correct control then refunds the eligible request and denies the two ineligible ones. Its success is supported by observed decision and final state, not by the mere presence of the reference passages.

    The ignore-limit mutant receives the same complete context but ignores the maximum-refund condition. Its excessive request is blocked by the independent backend. That is successful boundary enforcement and a failed agent contract—not a successful refund or proof that evidence packing failed. Oracle evidence cannot repair a downstream control that ignores a supplied condition.

    Both repaired and oracle contexts therefore require action-level evaluation. Keep missing evidence, conflicting evidence, an incorrect decision, a rejected attempt and an incorrect final state distinct. An unchanged ledger may mean a correct denial, a cautious abstention or a blocked invalid attempt; the trajectory determines which happened.

    This repair combines metadata filtering and exact deduplication. Its result does not identify the separate effect of each component. For attribution, add matched filter-only and dedup-only arms, keep the corpus, case, budget and downstream control fixed, and compare the extracted packing and action outcomes. Do not quietly replace these operational filters with gold relevance labels and call the result a better retriever.

**Extend:** introduce two different sufficient evidence sets, a partial passage that cuts off a decisive qualifier, or a wrongly labelled source version. Specify how admissible evidence changes before evaluating the result. Replace the byte budget with a measured model-token budget only when the complete serialized request and tokenizer are available. A model-backed study must separately test whether the model interprets and uses the packed text correctly.

**Evidence boundary:** this is an executed local ranking/packing/structured-decision experiment with mock state changes. Its synthetic cases and supplied metadata do not qualify real retrieval relevance, natural-language reasoning, authority discovery or production reliability. Replay checks the retained inputs, packing decisions, outputs and effects against local re-execution; it does not authenticate historical execution. The earlier [knowledge-to-action study](knowledge-action-study.md) remains the simpler retrieval/oracle/full-context introduction.

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

### Executed report-and-citation workshop

For the next level, use the [Long-Report Evaluation Study](long-report-study.md): it separates extraction recovery, compound claims, conflicting evidence and synthesis from the compact citation mechanics below. The original example remains the starting point.

The earlier refund-report table remains an illustrative scoring example. This separate [retained workshop](assets/report-citations-v1.json) freezes a complete **compact** classroom report, four invented source documents, five material claim annotations, four attempted citations and five required subquestions. It makes the joins and reassessment inspectable; it does not yet demonstrate automated extraction or synthesis evaluation on a long professional report.

Here is the entire evaluated report, including its deliberate mistakes:

```text
# Northport parcel-policy brief

As-of: 2026-09-07. Invented classroom report.

## Returns
The return window is 30 days. [L1] Opened items are always refundable. [L3]

## Refund timing
Refunds settle within 5 business days. [L2]

## Shipping
Return shipping is free. [L4]

## Scope
The policy covers Northport purchases.
```

The task additionally asks for the warranty period; the report omits it. The old policy says 30 days and stops applying on 1 September. The current policy says 14 days, excludes opened items and establishes Northport scope. Separate payment and shipping sources support the timing and shipping sentences. All policies, dates and review authority labels are invented for this exercise—not consumer advice or evidence of actual human review.

### Kata 76: four citations do not establish five claims

**Predict:** L1 quotes the obsolete policy accurately. L2 cites the payment source. L3 attaches that same payment source to the opened-item claim. L4 has an explicitly unresolved locator, even though a shipping document in the frozen corpus supports the sentence. The scope claim is true under the supplied reference but has no citation. Which failures belong to resolution, entailment, current support and task completeness?

```bash
uv run python -m cx_eval_lab.report_citations --output /tmp/report-citations.json
uv run python -m unittest tests.test_report_citations -v
```

Choose a fresh output path on subsequent runs. Inspect the retained report and source text alongside the exact claim, citation-marker and source-passage spans. The annotations use Python string indices—Unicode code points with an exclusive end offset. Entailment and truth judgments are explicitly authored and bound to the evidence they describe; the program validates and aggregates them rather than inferring meaning from prose.

| Computed measure | Result | Interpretation |
| --- | --- | --- |
| Resolving citation links | 3/4 | The broken shipping citation stays in the denominator |
| Entailing links among all attempted links | 2/4 | Old-window and timing passages entail their attached claims |
| Entailing links among resolving links | 2/3 | This conditional rate excludes the broken link; show both denominators |
| Claims with at least one resolving citation | 3/5 | Resolution includes the irrelevant citation |
| Claims supported by their supplied citations | 2/5 | Uncited truth and corpus evidence not actually cited do not count |
| Claims supported by current applicable citations | 1/5 | Only the timing claim has current cited support |
| Required questions addressed | 4/5 | Warranty is missing; this is not abstention |
| Required questions correctly answered after correction | 3/5 | The combined return-rule question fails; warranty remains unanswered |

??? success "Solution: keep the join and the denominator visible"
    L1 resolves and entails the 30-day sentence, but its policy is obsolete at the report date. L3 resolves to a real payment passage that says nothing supporting opened-item eligibility. L4 is unresolved; a supporting document elsewhere in the corpus does not repair the citation the report supplied. The scope sentence is true under the authored reference but uncited. These outcomes cannot be represented faithfully by one citation-count score.

    The returns subquestion asks for both the window and the opened-item rule. A partial mention cannot establish a correct answer to the whole question. Warranty contributes to the required-question denominator even though it contributes no extracted claim. If evaluation considers only assertions the report chose to make, omissions disappear and concise but incomplete reports can look perfect.

    Repair the specific defect: update the window and its source; correct the opened-item assertion and cite the applicable policy; repair the shipping locator; cite the scope evidence; address warranty with evidence or an explicit, justified uncertainty statement. These are proposed report repairs, not measured improvements from a newly executed research agent.

### Kata 77: correct a false pass without rewriting history

**Predict:** the original reference mistakenly accepts the 30-day window for this September report. A dated correction uses the already-frozen current policy and marks that claim wrong. What changes if the report, corpus and citation annotations stay identical?

The original factual grade is 4/5. Reassessment is 3/5, with only C1's factual label changed. This is a correction exposing a **false pass**, not the false failure in the PersonQA example above. Both directions matter: correcting the measuring instrument is not an optimization that must raise the score. Citation results stay unchanged because their text, links and applicability evidence did not change.

```python
import json
from pathlib import Path
from cx_eval_lab.report_citations import replay_study

packet = replay_study(json.loads(Path("docs/assets/report-citations-v1.json").read_text()))
old, new = packet["original_grade"], packet["reassessed_grade"]
assert old["context_hash"] == new["context_hash"]
assert old["factual_correctness"]["numerator"] == 4
assert new["factual_correctness"]["numerator"] == 3
assert packet["correction"]["changed_claim_ids"] == ["C1"]
assert packet["deployment_authorized"] is False
print("Original and reassessed correctness:",
      old["factual_correctness"]["rate"], new["factual_correctness"]["rate"])
```

??? success "Solution: a changed grade is not a changed model"
    Retain the original reference and its original grade. Link a new reference to the previous reference hash, bind the same report/corpus context, record the correction evidence and declared affected claims, and compute a new grade. Do not overwrite a stored pass flag and erase the reason it changed. The example's next-day review is a fictional timeline, not a claim that an independent review occurred.

    Hashes and allowed review authority labels provide local consistency checks, not reviewer authentication or proof of independent adjudication. A person with authority to rewrite all inputs and their hashes could manufacture a different evidence story. Real reassessment needs controlled annotation provenance, authorized corrections and retention outside the candidate's write scope.

    Replay here checks spans, joins, temporal applicability, annotation bindings and derived results. It does not prove that the authored semantic judgments are correct or exhaustive. To extend this to long reports, independently label omitted and compound claims, validate extraction, retain disagreements, score contradiction handling and synthesis, and compare actual research-agent outputs under a registered task and browsing budget.

**Interview answer criteria:** distinguish resolved citations from entailment and present applicability; retain uncited claims and missing subquestions in their proper denominators; preserve old/new evidence; separate reference repair from model improvement; identify the independent annotation and access controls that the local example does not establish.

#### Keep the report, not only its score

A reviewer cannot reconstruct the table above from five percentages. For an inspectable evaluation, freeze the complete report, the task and its required subquestions, the source corpus, and the reference version. Attach each material claim to its exact location in the report. Attach each citation to both the claim it is offered to support and the quoted passage in the frozen source. Record how the claim and support judgments were obtained: authored teaching annotations, independent human review or a qualified evaluator are different evidence.

Do not let a valid link substitute for a valid conclusion:

| Question | Unit and denominator | What a positive result does not prove |
| --- | --- | --- |
| Does the citation resolve? | Resolved links / all attempted citation links | That the passage entails the claim |
| Does the cited passage entail the claim? | Entailing links / attempted links; also report the resolved-only denominator | That the source is current, authoritative or correct |
| Does this material claim have supporting citations? | Claims with support / all material claims, including uncited claims | That every conjunct of a compound claim is supported |
| Is that support applicable at the requested time? | Claims with authoritative, in-scope, temporally applicable support / all material claims | That the corpus is complete or uncontested |
| Is the claim factually correct under the reference? | Correct claims / all material claims, with unknowns explicit | That the reference is itself valid or that the citation supports the claim |
| Did the report answer the task? | Required subquestions addressed, correctly answered and appropriately abstained, reported separately | That a polished heading or a sentence mentioning the topic supplies an answer |

An uncited true claim can improve factual correctness without improving citation support. An obsolete policy can entail a false present-tense claim. A broken citation can accompany a true claim. These are different repairs: add evidence, update the source, fix the link or correct the assertion. Changing the retriever is not the universal response.

**Span contract:** declare whether offsets count UTF-8 bytes, Unicode code points or another unit, and whether the end offset is exclusive. Validate `document[start:end] == quoted_text` against the frozen document. Reject negative, empty, reversed and out-of-range spans; do not silently truncate them. Repeated wording needs an explicit location, not an unconstrained first-string match. A report rewrite changes its identity and may invalidate every following offset.

Span validation proves that the annotation points at the intended text. It does not prove semantic entailment or that the annotator extracted every material claim. Measure extraction omissions and compound-claim splitting against independently reviewed reports before using the resulting claim count as a trustworthy denominator. Otherwise an extractor can improve the score simply by ignoring the difficult assertions.

#### Two clocks and two kinds of correction

“Newer source” is not a sufficient adjudication rule. A page's publication or capture date is different from the period during which its policy applies. A report requested **as of 1 August** may correctly cite a policy superseded on 1 September. Conversely, a current report can be wrong while quoting an old source exactly. Record report-as-of time, source publication/capture time, effective interval, jurisdiction or product scope, and authority separately.

Also register the information-access cutoff. A retrospective question about what was true on 1 August may permit a later correction that establishes the historical fact. A simulation of what an operator could decide on 1 August must exclude evidence unavailable then. Both tasks can share the same fact date while permitting different source sets. Do not let hindsight improve a historical decision simulation unnoticed.

Distinguish these changes:

- **Reference error at a fixed task date:** the expected answer was already wrong for the report's requested date. Keep the report and task fixed, issue a reviewed reference correction, and re-grade the same output. Either a false failure or a false pass may be exposed.
- **A genuinely changed task date:** a previously correct answer becomes obsolete because the world changes. Evaluate a new dated task; do not call the old historical answer a hallucination merely because it is no longer current.
- **An improved report:** the candidate changes its text or evidence. This is a new output, not merely a correction to the measuring instrument.

A correction record should bind the original reference, replacement reference, report/task identity, affected claims, dated supporting sources, reviewer authority, rationale and resulting grades. The reviewer must not be able to alter an unrelated field unnoticed. Preserve old grades for audit; publish corrected comparisons with an explanation of which labels changed. Reassess all affected stored candidates under the same corrected reference before interpreting a model-to-model delta. Candidate-specific relabeling can manufacture an improvement.

The [Deep Research system card](https://deploymentsafety.openai.com/deep-research) motivates both longer-answer evaluation and scrutiny of changing factual references. The local record design here is a teaching protocol, not a reproduction of OpenAI's internal grader or an assertion that the reference-correction problem is solved.

??? question "Interview drill: a better score after correcting the answer key"
    A frozen report scores 8/10 factual claims under reference v1 and 9/10 under reference v2. No model was rerun. Two citations still fail to support their attached claims, and the report omits one required subquestion. What improved, what can you release, and what do you retain?

??? success "Solution: correct the measurement before claiming an improvement"
    The measured factuality changed by one claim after a reference revision. The model and output did not improve in this experiment. Verify that v2 corrects the answer for the original task date and scope, rather than importing a later policy or accommodating this candidate. Retain the frozen report, both references, dated adjudication evidence, claim-level diff, both grades and the unchanged citation/completeness findings.

    Recompute affected baseline and candidate reports under v2 before comparing systems. A change to a single answer key can alter their relative ranking; reporting only the candidate's corrected score is not a fair comparison. If adjudication is uncertain, retain that uncertainty rather than forcing a favorable reference value.

    Neither 9/10 nor a one-point gain resolves unsupported citations or the omitted question. Apply the registered report contract and any material-error vetoes. In the absence of qualified, representative evidence and an authorized release policy, no production expansion follows. This example supplies ten claims in one report, not ten independent deployment tasks.

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
| Bank settlement timing | no | yes: explicitly says timing is unverified | appropriately abstained, subject to review of evidence sufficiency |
| Customer next step | yes | yes | covered |

Omission is not abstention. A report that silently skips bank timing has left a required subquestion unanswered. A report that explains the evidence gap has addressed the question without providing a verified arrival date; keep those outcomes separate from both correctness and factual-answer coverage.

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
