# Long-report evaluation: inspect what the scorer missed

A report can receive a higher factual-support score without changing a word: its claim extractor can simply stop returning the unsupported assertions. The numerator may stay fixed while the denominator shrinks. A release review that sees only the final percentage can mistake an evaluator regression for an application improvement.

This study extends [Katas 76–77](rag-research-evals.md#executed-report-and-citation-workshop). Those exercises make a compact report, citations and reference correction inspectable. Here the problem is the report-level evaluation pipeline: atomic decomposition, extraction omissions, conflicting evidence, task coverage and synthesis. The local experiment uses authored reports and semantic annotations with deterministic extraction controls. It does not claim to reproduce a model-based factuality evaluator or to establish professional-report quality from parser tests.

## Read the report before the answer key

Start with the [casebook](long-report-casebook.md). Read the baseline report and frozen sources before inspecting its annotations or the repaired report. Write down:

- each material assertion, including both sides of compound sentences;
- which source passages support, contradict or leave it unresolved;
- required questions that the report never answers;
- conclusions that require more than repeating individual facts;
- recommendations whose justification depends on an untested assumption.

Then compare your list with the retained annotation inventory. A disagreement is useful evidence to investigate, not an instruction to make your answer match a program. The supplied inventory is an authored teaching key, not independently qualified human ground truth. Its purpose is to expose the checks required before trusting an automatically produced inventory.

## The local experiment's boundary

The authored reports distinguish marked `Finding:` paragraphs from surrounding analysis. Three deterministic controls operate on those paragraphs: a sentence-window control, a semicolon-clause control, and a cited-clause-only control. Their input is the report text, not the gold labels or expected claim IDs. This is a **format-bound extraction experiment**. Its recall denominator is the registered finding inventory, not every possible factual assertion in the surrounding prose.

The controls answer different questions. A sentence window may retain the words of two claims without separating them. A clause splitter can recover the registered atomic units because the casebook deliberately uses a semicolon convention. A cited-only filter can miss an assertion precisely because that assertion lacks evidence. None establishes reliable extraction on arbitrary professional writing, and none reads semantic truth from the source text.

The broader methods below describe what a production evaluation would need. Where the local implementation uses authored support, question or synthesis judgments, treat those judgments as inspectable inputs, not a demonstrated capability of the extractor. The casebook's narrative analysis remains subject to review outside the finding-parser score.

### What to inspect in the Aster memo

The original memo and its repair use the same nine-document packet. The evidence includes a committed transaction followed by a timeout, current and archived recovery procedures, a narrow explanation pilot, channel exclusions, review-capacity assumptions and a conditional pilot policy. The report must connect those records without treating every kind of success as equivalent.

| Defect in the original findings | Evidence to inspect | What the repair must do |
| --- | --- | --- |
| Timeout described as proof of no financial effect | The incident ledger records the committed transaction before the response timeout | Distinguish transport failure from recorded state |
| September recovery justified by an August retry instruction | The two procedures' effective periods and conflicting action rules | Use the applicable rule and explain why the archived instruction does not govern |
| Bank arrival promised within 24 hours | Estimated processing guidance and the unknown settlement field | Distinguish a general estimate from account-specific confirmation |
| Narrow explanation results extended to transaction reliability, Turkish and voice readiness | Pilot scope and explicit channel exclusions | State what was measured and what the packet cannot decide |
| A 52-review forecast described as fitting 40 daily slots | Capacity and demand in the same planning unit | Derive the 12-case shortfall while preserving the forecast assumptions |
| Zero operating cost asserted without cost evidence | The packet's explicit cost-evidence gap | State that cost is undetermined, rather than equating missing measurement with zero |
| Expansion recommended without the owner and pause conditions | The conditional supervised-pilot contract | Identify the owner, stop conditions and prerequisites without pretending they are already satisfied |

The 52-minus-40 calculation is a planning implication of invented inputs, not a measured queueing result. The repaired recommendation is conditional; it does not authorize the fictional pilot to start, much less an actual deployment. Accurate statements of missing evidence should count as supported assertions when the sources warrant them. Whether the underlying arrival time or operating cost remains unanswered is a separate dimension.

## Reproduce and inspect

The [frozen inputs](assets/long-report-inputs-v1.json) retain the reports, corpus and authored review records. The [study packet](assets/long-report-study-v1.json) retains the executed extraction results and derived comparison. The [casebook](long-report-casebook.md) is the readable entry point; use the JSON when checking exact offsets and identities.

```bash
uv run python -m unittest tests.test_long_report -v
uv run python -m cx_eval_lab.long_report --output /tmp/long-report-study.json
```

Choose a fresh output path for each run. These commands execute local extraction and grading mechanics; they do not browse, call a model, commission human judgments or change application exposure. Replay can check the retained computations against the current implementation. It is not execution attestation or proof that the authored judgments are valid.

### Executed results

The original memo has 878 words and 18 registered atomic findings; the repaired memo has 1,020 words and 20. Each has two compound finding paragraphs. The nine frozen source documents contain 638 words. These are two authored outputs for one task, not independent samples of research-agent performance.

| Report / extraction control | Returned units | Exactly recovered atoms | Unmatched coarse units | Support among matched atoms | Support over full authored inventory |
| --- | --- | --- | --- | --- | --- |
| Original / sentence | 16 | 14/18 | 2 | 4/14 | 8/18 |
| Original / clause | 18 | 18/18 | 0 | 8/18 | 8/18 |
| Original / cited-only | 17 | 17/18 | 0 | 8/17 | 8/18 |
| Repaired / sentence | 18 | 16/20 | 2 | 16/16 | 20/20 |
| Repaired / clause | 20 | 20/20 | 0 | 20/20 | 20/20 |
| Repaired / cited-only | 20 | 20/20 | 0 | 20/20 | 20/20 |

On the original, cited-only filtering omits C16's unsupported zero-cost assertion. Observed support rises from 8/18 to 8/17 while recovery falls: the report has not improved. The sentence control fails to split the two compound paragraphs, leaving C04/C05 and C13/C14 unrecovered as atomic units. Their text remains inside two coarse spans. On the repaired report, 16/16 observed support still coexists with only 16/20 atomic recovery; a perfect conditional score does not qualify the extractor.

The clause control's perfect recovery is a result on the deliberately registered semicolon format. It is not a general extraction benchmark. All repaired findings carry citations, so cited-only and clause results coincide there; this does not repair the filtering rule on reports with uncited assertions.

Under the authored review, the original has eight supported, six contradicted and four unsupported assertions. Two of its supported assertions explicitly leave an underlying outcome unknown. The repair has twenty supported assertions and four unknown withheld targets. **Supported uncertainty statements count as supported statements.** These counts neither supply the missing arrival/cost/channel answer nor establish that a production judge would recognize the distinction.

The fixed task has six questions: the original has one answered, four partially answered and one omitted; the repair has all six answered under the authored coverage rubric, which allows appropriately explained uncertainty. Four synthesis obligations are registered independently of the submitted reports. The original's reviews contain one supported, two contradicted and one unsupported synthesis judgment; all four are supported in the repair. These semantic decisions remain inspectable review inputs, not conclusions discovered by the parser.

```python
import json
from pathlib import Path
from cx_eval_lab.long_report import replay_study

packet = replay_study(json.loads(Path("docs/assets/long-report-study-v1.json").read_text()))
original, repaired = packet["reports"]
assert original["shared_context_hash"] == repaired["shared_context_hash"]
full = original["controls"]["clause"]
selected = original["controls"]["cited-only"]
assert selected["observed_support"]["rate"] > full["observed_support"]["rate"]
assert selected["full_inventory_support"] == full["full_inventory_support"]
assert selected["omitted_claim_ids"] == ["C16"]
assert repaired["gold_status_counts"]["supported"] == 20
assert repaired["underlying_unknown_count"] == 4
assert not packet["deployment_authorized"]
print("Unchanged original inventory:", full["full_inventory_support"])
print("Cited-only omission:", selected["omitted_claim_ids"])
```

## Kata 78: the missing claims are part of the result

**Predict:** keep the report unchanged and switch from all registered clauses to only clauses carrying citations. If the uncited clauses are the unsupported or unverified ones, what happens to observed support? Has the report improved?

Run the extraction controls and retain their actual returned spans. Join each prediction to the reviewed finding inventory. List exact matches, missing findings and predictions that do not match an atomic finding. Compute support among matched returned claims, but also report recovery against the full registered inventory and the omitted claims' statuses. Do not silently score an unmatched coarse span as true or drop it without reporting it.

??? success "Solution: a favorable subset is not a better report"
    Filtering to cited clauses changes the evaluation's selection mechanism. It does not change the report. A higher support fraction among those clauses can coexist with lower finding recovery. The user still receives the uncited unsupported assertion, even if the scorer no longer inspects it.

    Keep the full-inventory support result beside extracted-only support and publish the omitted IDs and text. In this workshop the full inventory is authored in advance. In production, a reviewed sample is needed to estimate extraction errors; the real inventory cannot be assumed complete because a parser returned some claims.

    Zero predictions produce no observed-support estimate, not perfect factuality. Duplicate predictions do not create new recovered claims. An unmatched whole-report span is neither an atomic claim nor evidence that every contained claim was evaluated. These cases belong in the extractor's regression suite.

**Interview answer criteria:** name the selection bias, retain both denominators, identify missing severe claims, separate unmatched predictions from false claims, and explain why the same report cannot become better through selective measurement.

## Kata 79: covering the words is not splitting the claims

**Predict:** each of the two compound finding paragraphs contains two separately supported clauses. Compare one coarse extraction with two atomic extractions. Should the coarse span count as two recovered atomic claims? As a further hypothetical variation, what would change if one conjunct were unsupported?

Inspect the control's actual offsets, then compare them with each authored atomic span. Keep the coarse span's relationship to both claims visible for diagnosis. The exact-atomic metric should not award two successful decompositions for a single unresolved compound unit. Likewise, counting the compound as one claim and marking it supported when either part is supported is too lenient.

??? success "Solution: diagnose the coarse unit without rewarding it"
    Report that the words were retained but the atomic decomposition failed. Under exact-span matching, the coarse unit is unmatched and the constituent atoms are not recovered as separate units. That is a declared evaluation choice, not proof the extractor ignored the text. A text-coverage metric can be reported separately but must not be called atomic recall.

    If the downstream grader genuinely evaluates a compound unit, it must assess every material conjunct and preserve uncertainty in any unresolved part. It should not import the first clause's supporting citation as evidence for the second. A single binary verdict can still obscure which claim needs correction, so retain component judgments where the contract requires them.

    The semicolon control works for this authored format. A general extractor needs independently reviewed sentence structures and a matching method that handles valid paraphrases without rewarding missing qualifiers. Run the same examples after punctuation changes; do not infer general decomposition capability from the registered delimiter alone.

**Interview answer criteria:** distinguish exact atomic recovery from text coverage, explain partial compound support, retain one-to-many matches, and identify the limits of punctuation-based extraction.

## Kata 80: true premises can lead to an unsupported recommendation

**Predict:** the original accurately quotes capacity of 40 reviews and forecast demand of 52, then concludes that the batch fits. The repair derives a 12-case shortfall and makes its recommendation conditional. Can correct premise citations alone establish that the conclusion follows?

Read the baseline and repaired conclusions with their supporting passages. Trace each recommendation to the task's requested decision, the relevant premises, contrary evidence and unstated assumptions. Compare question coverage, explicit abstentions and synthesis judgments under the same frozen rubric. Preserve the original report even when the repair is plainly better under the teaching key.

??? success "Solution: grade the inference and its unresolved premises"
    In the executed workload example, both numerical premises are supported but the original's “fits” conclusion is contradicted by their comparison. The repair correctly derives a conditional planning shortfall. The code retains authored judgments about that inference; it is not discovering arithmetic implications from unrestricted prose. This is distinct from the original's pilot-count defect, which also misstates a premise: its 24/24 assertion contradicts the source's 21/24 result.

    A correct pilot statistic establishes only what was measured under that pilot's conditions. Broader deployment may require additional evidence about workload, severity, slices, reliability and operational authority. The conclusion must either establish those premises or state the restriction they impose. Repeating accurate facts does not close the gap.

    Read the authored synthesis rationale and challenge it against its cited premises. The local program validates bindings and aggregates review records; it does not discover logical validity by itself. If a rationale says a conflict is resolved, locate the exact report text that resolves it. If the conclusion depends on missing evidence, a qualified recommendation or justified abstention may be better than an unsupported definitive answer.

    The repair is a new report under the same task and corpus, not a new reference applied to an unchanged report as in Kata 77. Its claim count and wording can change. Report both denominators, newly addressed questions and remaining uncertainty. Do not describe a hand-authored repair as a measured improvement in the research agent.

**Interview answer criteria:** separate facts from inference, identify unstated premises, compare fixed task/rubric conditions, preserve both outputs and distinguish a teaching repair from a causal model experiment.

## Define the unit before calculating the score

Consider the invented sentence: “The refund request was accepted, and the bank has received the funds.” The first clause might be supported by an API receipt while the second is unverified. A sentence-level verdict that finds one supporting passage and calls the whole sentence supported creates a false pass. Splitting every occurrence of `and` is not a general solution: “between Monday and Friday” is not two independent assertions, and qualifiers can govern several clauses together.

Use an atomicity convention that retains the subject, predicate, scope, negation, quantities and temporal qualifiers needed to judge each assertion. Record both the original sentence span and the component claim spans. Evaluate decomposition against independently annotated examples of conjunction, anaphora, attribution, comparisons, numerical ranges and exceptions. A fluent paraphrase can accidentally remove the very qualifier that made a claim false.

Three inventories have different jobs:

| Inventory | What it counts | Failure if omitted |
| --- | --- | --- |
| Report assertions | Material claims actually made in the report | Unsupported assertions can disappear from factuality scoring |
| Required task questions | Information the user asked the report to provide | A report can avoid difficult questions and still look perfectly factual |
| Synthesis obligations | Relationships and decisions the report must justify | Correct isolated facts can conceal an invalid overall conclusion |

Do not put an omitted task requirement into the report-claim denominator as if the report asserted a false fact. Keep the completeness failure separately. Conversely, do not remove an unsupported assertion merely because the user did not explicitly request it: extra claims can still mislead the reader.

## Measure the extractor as well as the extracted claims

For a reviewed report inventory, report the fraction of gold material claims recovered, the fraction of extracted claims that match material assertions, duplicate matches, compound sentences left unsplit and claims missed by severity or section. An extractor that returns the entire report as one span has high text coverage but has not produced an atomic inventory. An extractor that returns only easy cited sentences can have high observed factual support while omitting the most consequential claims.

Match by retained text and spans under a declared rule, not by silently copying gold claim identifiers into extractor inputs. When a heuristic produces a coarse sentence containing two gold claims, preserve that one-to-many relation. Distinguish “the text was covered” from “the atomic claims were recovered.” In a real paraphrasing extractor, exact-span matching may be inappropriate; independently validate the matching method and its disagreement rate before treating it as the oracle.

Always publish the missing-claim list beside observed support. Compare these quantities:

- support among claims the extractor returned;
- recovery of all reviewed material claims;
- support over the complete reviewed inventory;
- unresolved, contradicted and unknown claims that were missed.

These are not interchangeable estimates. On an unreviewed production report the complete inventory is unknown; you cannot fix that uncertainty by dividing by a guessed total. Use a reviewed sample to qualify extraction and keep unverified reports visibly provisional.

## Conflicting sources require an adjudication, not a vote

Two sources can disagree because they describe different dates, populations, products, regions or outcome definitions. Before calling a claim contradicted, align those conditions. Before accepting a newer source, establish its authority and applicability. Three reposts of one obsolete rule are not three independent confirmations.

A useful conflict record retains both source passages, their dates and scopes, the precise disputed assertion, the controlling rule and the remaining uncertainty. If the report resolves the disagreement, point to the sentence doing that work. If it merely cites both documents without explaining which applies, citation presence has not established conflict handling.

Unknown and false must remain distinct. “The source corpus does not establish bank arrival time” is different from “the funds have not arrived.” A correct abstention names the unanswered question and the evidence limitation; a silent omission does not. Neither is an excuse to ignore readily available decisive evidence.

## Synthesis is an additional claim

“The observed error rate is lower” and “the system is ready for unrestricted rollout” are not the same claim. The second depends on additional premises: representative sampling, uncertainty, severity, affected slices, operational readiness and release authority. A report can cite every descriptive fact accurately and still make an unsupported deployment recommendation.

For each consequential conclusion, retain:

1. the conclusion span;
2. the premises and their source spans;
3. the inference being made;
4. assumptions or scope restrictions not established by those premises;
5. contradictory evidence the report must address;
6. the review judgment and its rationale.

A program can verify the existence and identity of these records and recompute a registered rubric. It cannot establish the inference's validity merely because the fields are populated. Qualification needs examples where the facts are all true but the inference fails, alongside valid conclusions and legitimate uncertainty. Keep recommendations distinguishable from factual assertions without exempting them from evidential review.

## Compare the repaired report fairly

Freeze the task, source corpus, information-access cutoff, claim-definition policy and review rubric before comparing report versions. Preserve both full texts and annotate newly added, removed and modified material claims. The repaired report need not have the same number of claims: appropriate qualifications and newly addressed questions can change the denominator. Report that change rather than forcing a one-to-one claim match that does not exist.

The comparison should explain which defects were repaired, which remain, and whether the recommendation changed for a defensible reason. A hand-authored repair demonstrates the target behavior and grading mechanics. It is not a measured improvement from prompt tuning, retrieval changes or a new model. To make that attribution, actually execute the competing systems under matched registered conditions and preserve unsuccessful trials too.

## Research connection and evidence boundary

[FActScore](https://arxiv.org/abs/2305.14251) motivates decomposing long-form output into atomic facts and assessing support against reliable evidence. Its published model results do not qualify this local extractor. [ALCE](https://arxiv.org/abs/2305.14627) separates correctness and citation quality and studies end-to-end citation-bearing answers; this workshop is not an ALCE benchmark reproduction.

The local contribution is an inspectable teaching experiment. The remaining empirical work is to sample actual research outputs, obtain independent annotations, qualify extraction and semantic review, test source conflicts and synthesis across representative tasks, and measure end-to-end utility under realistic browsing budgets. No single authored report supplies a population accuracy rate, a confidence interval for general research capability or permission to expand production exposure.
