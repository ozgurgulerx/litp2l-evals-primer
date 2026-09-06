# Long-report casebook: a refund decision memo

Every organization, incident, policy, reviewer judgment, date, and number in this casebook is invented. The original memo is deliberately flawed. Neither memo authorizes a real refund or deployment.

This is the complete readable counterpart of [the frozen input artifact](assets/long-report-inputs-v1.json). Both reports use the same nine-document corpus, task, date, and rubric. The original has 878 words and 18 registered findings; the repaired memo has 1,020 words and 20. The source documents contain 638 words in total.

## What the workshop audits

The executable extraction contract covers only lines beginning `Finding:`. Two lines in each report contain two atomic clauses separated by a semicolon. Citation markers belong to the preceding clause. All 18 or 20 clauses are registered in the authored inventory; the JSON stores their exact Unicode-code-point spans, source quotes, and source spans.

The surrounding analysis makes the memo usable as a professional document, but it is **not claimed to be exhaustively claim-extracted or semantically audited**. The full-report protocol would require reviewing that prose too. Do not confuse success on the declared format with general natural-language claim extraction.

The source text and spans make citation resolution inspectable. Entailment, factual status, subquestion coverage, and synthesis judgments are explicitly authored teaching annotations. Executing the checks or replaying them does not turn those judgments into independent human evidence or a qualified semantic evaluator.

## Shared task and rubric

As of **2026-09-07**, assess the fictional Aster Goods refund incident and proposed next stage. Answer these questions:

- **Q1:** What happened after the timeout, what recovery is permitted, and which conflicting policy governs the incident date?
- **Q2:** What purchase and amount limits apply, and when must supervisor approval exist?
- **Q3:** What can the customer be told about the refund and bank timing, and what must remain unknown?
- **Q4:** What does the explanation pilot establish, and what can be concluded about other languages, channels, and transaction reliability?
- **Q5:** Does proposed review demand fit the stated capacity, and what is known about incremental operating cost?
- **Q6:** Who owns starting the supervised pilot, and which observed events require it to pause?

All documents, labels, dates, counts and review reasons are invented teaching data. Audit only the registered Finding clauses, not every assertion in the surrounding prose. A material factual finding needs scoped support; an inference must not outrun its premises; a recommendation must respect unresolved dependencies. Claim status judges the literal assertion. An accurate statement that evidence cannot determine an outcome is supported. The separate abstention_target_answerability field is unknown for an explicitly withheld target and null for other findings; null does not assert that an unsupported claim is answerable. Citation entailment, current factual validity, task completeness and synthesis are distinct. An archived passage may entail a quoted instruction while failing to justify its current use. The task is complete only when every registered subquestion is addressed or its evidence gap is explicitly and appropriately resolved as an abstention. Semantic labels and coverage/synthesis reviews are authored, not produced or qualified by a model or human study.

## Frozen source corpus

The documents below are all the evidence available to either memo. “Authority” is a property assigned within this invented case, not an authenticated issuer. The September task date determines which policy applies; the older source remains readable so the conflict can be inspected.

### S01 — Current refund policy

Published: 2026-09-01. Effective from: 2026-09-01. No end date specified in this frozen packet.

Automatic refunds are limited to GBP 50 and purchases made within 30 calendar days. Amounts above GBP 50 require a recorded supervisor approval before a refund action. Following a timeout, inspect the transaction ledger before attempting another refund. If the original transaction exists, reconcile that transaction and reuse its idempotency key for any permitted status reconciliation. Never create a fresh refund key merely because the response timed out. This policy replaces the August retry instruction on 1 September 2026. Eligibility and approval checks must be enforced by the service, not inferred from customer wording.

### S02 — Retired August retry instruction

Published: 2026-08-01. Effective from: 2026-08-01. Effective until (exclusive): 2026-09-01.

After a timeout, retry the refund request using a new request key. This temporary instruction applies to the August integration only. Its effective period ends on 1 September 2026, when the current refund policy replaces it. The document remains in the archive so incident reviewers can understand earlier operator behavior. Archival availability is not permission to use this instruction for September transactions.

### S03 — Incident ledger extract

Published: 2026-09-07. Effective from: 2026-09-07. No end date specified in this frozen packet.

At 09:14 UTC on 7 September 2026, request R17 created transaction T41 for a GBP 42 refund on order O8. The ledger records one committed refund transaction with idempotency key K17. The response channel then timed out. The bank settlement field is unknown. No second refund transaction is recorded in this extract. This extract proves the recorded transaction state, not whether the customer has received money in a bank account.

### S04 — Bank timing guidance

Published: 2026-09-01. Effective from: 2026-09-01. No end date specified in this frozen packet.

The indicative bank processing window is three to five business days after a refund is submitted. This window is an estimate, not a promise about a particular account. The guidance does not guarantee settlement within 24 hours. A settlement claim requires a separate bank confirmation tied to the transaction. Staff should distinguish the merchant transaction being committed from the customer's bank balance changing.

### S05 — Frozen explanation pilot

Published: 2026-09-05. Effective from: 2026-09-05. No end date specified in this frozen packet.

The pilot contains 24 invented English refund conversations. In 21 conversations the explanation accurately distinguishes the recorded transaction status from bank settlement. Three explanations incorrectly say that a pending bank transfer has settled. The pilot is a scripted teaching sample, not production traffic. It does not measure the frequency of duplicate transactions, fraud detection, or customer satisfaction. The counts describe these fixed explanations only, not future reliability.

### S06 — Language and channel inventory

Published: 2026-09-05. Effective from: 2026-09-05. No end date specified in this frozen packet.

Only English text conversations are included in the frozen pilot. No Turkish conversation or voice interaction has been evaluated in this packet. There is no basis here for a Turkish or voice release claim. Missing evaluation does not establish that those channels are unsafe; it establishes that this packet cannot decide their readiness. Additional channel-specific evidence would require its own protocol and observations.

### S07 — Review capacity worksheet

Published: 2026-09-06. Effective from: 2026-09-06. No end date specified in this frozen packet.

The planned review team can complete 40 cases per day under its current staffing assumption. The proposed pilot batch is expected to produce 52 reviews per day. The forecast is a planning assumption, not an observed arrival rate. A capacity decision must compare review demand with available review slots and preserve the assumptions behind both numbers. No extra reviewer or overtime allocation has been approved in this worksheet.

### S08 — Cost evidence boundary

Published: 2026-09-06. Effective from: 2026-09-06. No end date specified in this frozen packet.

The packet contains no supplier invoice, measured token usage, or reviewer labor cost record. Incremental operating cost cannot be calculated from this packet. A future budget must account for model use, review labor, retries, and storage under declared pricing assumptions. Absence of an invoice is not evidence that the service is free. This note records an evidence gap rather than estimating a price.

### S09 — Supervised pilot and rollback contract

Published: 2026-09-07. Effective from: 2026-09-07. No end date specified in this frozen packet.

The next permitted stage is a supervised English text pilot only. The release owner is the fictional role Support Operations Lead. That owner must confirm eligibility and approval enforcement, truthful customer wording, a feasible review allocation, and a cost estimate before starting. One observed duplicate refund or one unsupported settlement promise pauses the pilot and routes the affected case to review. Restart requires owner approval after the failure is reproduced and the repair is checked. This contract is an invented policy for the teaching case, not deployment authorization.

## Original memo — deliberately flawed

Aster Goods refund recovery decision memo — original

This memo assesses the recovery and release proposal against the frozen packet, separating a transaction decision from customer wording and a broader rollout recommendation. Read the findings as the reviewable conclusions; the intervening paragraphs describe how to inspect and use them. The report is intentionally fictional and is not an instruction for handling real customer money.

Finding: Request R17 produced one committed refund before its response channel timed out [L01].

Begin the investigation with the recorded side effect, not the visible error banner. Keep the request, transaction, and idempotency identifiers together so an operator can reconcile the incident without treating an unfamiliar identifier as a new customer instruction.

Finding: The timeout proves that the original request had no financial effect [L02].

For the recovery decision, use a single interpretation of the timeout throughout the handoff. Do not alternate between transport failure and transaction failure merely to make a proposed retry seem consistent with whichever paragraph the reader is currently consulting.

Finding: The September recovery procedure requires a fresh request key and a second refund attempt [L03].

Keep the archived instruction available beside the working procedure during incident review. Explain which instruction governs the transaction date, rather than allowing whichever search result appeared first to determine the operational response.

Finding: Automatic refunds have a GBP 50 limit [L04]; The purchase must fall within the 30 calendar day window [L05].

Apply the amount and purchase-age conditions as separate checks. A clear customer description can help locate an order, but the final decision should use recorded order fields and leave an inspectable reason for any failed eligibility check.

Finding: Refunds above GBP 50 require recorded supervisor approval before the action [L06].

An approval request should identify the exact order, amount, and proposed action. Keep that request separate from a customer's preference or an agent's confidence, and make the resulting approval available to the service that will enforce the decision.

Finding: The refund will reach the customer bank account within 24 hours [L07].

Customer wording deserves its own review rather than inheriting a passing grade from the transaction check. Read the proposed sentence as a commitment a customer might rely on, and identify which record could establish each time-sensitive assertion.

Finding: The supplied ledger cannot establish when the customer bank account will receive the money [L08].

Keep this uncertainty visible in the proposed response. A useful explanation can acknowledge the verified action and distinguish an estimate from confirmation, leaving the unresolved bank event for an appropriate evidence source instead of inventing a reassuring date.

Finding: Every one of the 24 pilot explanations accurately distinguished transaction status from settlement [L09].

Retain the case-level explanation record when presenting the headline result. A reader should be able to inspect the counterexamples and the meaning of the scoring criterion before treating the number as evidence for a broader service decision.

Finding: This explanation pilot establishes that duplicate refunds will not occur [L10].

Do not compress different operational outcomes into an undifferentiated quality label. A transaction incident, an inaccurate explanation, and a delayed review require different evidence and repairs even when they appear within the same customer conversation.

Finding: The packet establishes readiness for Turkish text conversations [L11].

Keep language scope adjacent to any score in the release memo. A reader should not have to infer whether a language was measured, deliberately excluded, or simply absent from a convenient sample that became the headline evaluation.

Finding: Voice readiness cannot be determined from the supplied evaluation packet [L12].

Treat this as an unanswered evidence question. A follow-up evaluation should state the voice task, interruption conditions, action boundaries, and review criteria before asking whether a text result can transfer to that setting.

Finding: The planned team has capacity for 40 reviews per day [L13]; The proposed batch is expected to generate 52 reviews per day [L14].

Present demand and capacity in the same unit and planning window. Keep forecast assumptions available for challenge, and avoid converting a neat spreadsheet result into a claim about how a queue will behave during a changing service day.

Finding: The proposed batch fits within the stated daily review capacity [L15].

Decide what action the workload calculation supports. If the proposal needs a smaller batch or another staffing decision, record that dependency rather than hiding unresolved work behind an average completion score or a general promise to monitor.

Finding: The proposed service has zero incremental operating cost.

Budget review should list the inputs needed for an estimate and identify who will supply them. Keep unknown cost distinct from an observed zero, and avoid letting a quality comparison stand in for an operating expense calculation.

Finding: Both the archived and current policies support unrestricted fresh-key retrying [L16].

Place conflicting passages next to one another in the decision record. Explain whether the disagreement concerns dates, transaction state, or permitted actions, and preserve the losing interpretation so a reviewer can understand why it was not used.

Finding: The combined packet supports immediate expansion to every language and channel [L17].

A recommendation should state the evidence it depends on and the conditions that would change it. Keep the conclusion separate from its supporting observations so a reviewer can reject the proposed action without discarding every valid fact in the report.

### Authored citation and finding ledger

Citation entailment concerns the whole finding, including material dates. Finding status judges the literal assertion under the task’s full evidence and temporal scope. Accurate statements that an outcome cannot be determined are supported; their separate abstention target remains unknown. An uncited finding still belongs in the denominator.

| Finding | Kind | Assertion status | Abstention target | Citation and source | Authored reason |
| --- | --- | --- | --- | --- | --- |
| C01 | factual | supported | Not assessed | L01 → S03 (entails) | The ledger directly distinguishes committed state from response delivery. |
| C02 | inference | contradicted | Not assessed | L02 → S03 (contradicts) | The inference contradicts the explicit committed transaction. |
| C03 | factual | contradicted | Not assessed | L03 → S02 (insufficient) | The archived August instruction does not entail the explicitly September-scoped claim; S01 contradicts its current use. |
| C04 | factual | supported | Not assessed | L04 → S01 (entails) | The current policy specifies the monetary ceiling. |
| C05 | factual | supported | Not assessed | L05 → S01 (entails) | The current policy independently specifies the age window. |
| C06 | factual | supported | Not assessed | L06 → S01 (entails) | The approval requirement precedes action. |
| C07 | factual | unsupported | Not assessed | L07 → S04 (insufficient) | A general indicative window cannot support a transaction-specific promise. |
| C08 | abstention | supported | unknown | L08 → S03 (entails) | A justified abstention: the account-specific settlement event remains unknown. |
| C09 | factual | contradicted | Not assessed | L09 → S05 (contradicts) | The pilot reports 21, not 24, accurate explanations. |
| C10 | inference | unsupported | Not assessed | L10 → S05 (contradicts) | Explanation correctness does not establish transaction reliability. |
| C11 | factual | contradicted | Not assessed | L11 → S06 (contradicts) | There are no Turkish observations in the packet. |
| C12 | abstention | supported | unknown | L12 → S06 (entails) | A justified abstention, not an adverse capability verdict. |
| C13 | factual | supported | Not assessed | L13 → S07 (entails) | This is a staffing assumption, not measured throughput. |
| C14 | factual | supported | Not assessed | L14 → S07 (entails) | This is a planning forecast, not an observed arrival rate. |
| C15 | inference | contradicted | Not assessed | L15 → S07 (contradicts) | Demand 52 exceeds capacity 40 by 12. |
| C16 | factual | unsupported | Not assessed | Uncited | The uncited cost claim is unsupported; S08 lacks the necessary records. |
| C17 | inference | contradicted | Not assessed | L16 → S01 (contradicts) | This synthesis erases the explicit conflict and effective-date boundary. |
| C18 | recommendation | unsupported | Not assessed | L17 → S05 (insufficient) | The recommendation exceeds pilot scope and ignores unresolved constraints. |

### Authored completeness review

| Question | Status | Findings | Reason |
| --- | --- | --- | --- |
| Q1 | partially_answered | C01, C02, C03, C17 | The incident is identified, but the retry recommendation and claimed policy agreement contradict current evidence. |
| Q2 | answered | C04, C05, C06 | Both eligibility limits and the prior-approval requirement are identified. |
| Q3 | partially_answered | C07, C08 | An appropriate abstention conflicts with an unsupported 24-hour promise. |
| Q4 | partially_answered | C09, C10, C11, C12, C18 | The memo misstates the count and extends narrow evidence to duplicate-refund certainty and Turkish readiness. |
| Q5 | partially_answered | C13, C14, C15, C16 | The underlying capacity assumptions are quoted, but their comparison is wrong and zero cost is invented. |
| Q6 | omitted | None | No finding states the accountable role or the pause trigger; a general expansion recommendation does not answer either. |

### Authored synthesis review

These are explicit evidence-to-conclusion judgments, not sentiment ratings or a model-generated summary. The support and conclusion IDs refer to this memo only.

| Review | Conclusion | Premises | Status | Reason |
| --- | --- | --- | --- | --- |
| SY01 | C17 | C01, C03 | contradicted | The sources disagree about fresh-key retries; the memo cannot reconcile them by asserting agreement. |
| SY02 | C15 | C13, C14 | contradicted | The quoted figures show excess demand, not spare capacity. |
| SY03 | C18 | C09, C10, C11, C12, C15, C16 | unsupported | The proposed expansion is stronger than its cited pilot and ignores missing channel and cost evidence and an unresolved workload shortfall. |
| SY04 | C08 | C01 | supported | A committed merchant transaction does not fill the unknown bank-settlement field; the abstention is justified despite an established transaction. |

## Repaired memo — still fictional and conditional

Aster Goods refund recovery decision memo — repaired

This memo assesses the recovery and release proposal against the frozen packet, separating a transaction decision from customer wording and a broader rollout recommendation. Read the findings as the reviewable conclusions; the intervening paragraphs describe how to inspect and use them. The report is intentionally fictional and is not an instruction for handling real customer money.

Finding: Request R17 produced one committed refund before its response channel timed out [L01].

Begin the investigation with the recorded side effect, not the visible error banner. Keep the request, transaction, and idempotency identifiers together so an operator can reconcile the incident without treating an unfamiliar identifier as a new customer instruction.

Finding: The transport timeout does not negate the committed transaction recorded in the ledger [L02].

For the recovery decision, use a single interpretation of the timeout throughout the handoff. Do not alternate between transport failure and transaction failure merely to make a proposed retry seem consistent with whichever paragraph the reader is currently consulting.

Finding: September recovery requires ledger inspection and forbids a fresh refund key merely because the response timed out [L03].

Keep the archived instruction available beside the working procedure during incident review. Explain which instruction governs the transaction date, rather than allowing whichever search result appeared first to determine the operational response.

Finding: Automatic refunds have a GBP 50 limit [L04]; The purchase must fall within the 30 calendar day window [L05].

Apply the amount and purchase-age conditions as separate checks. A clear customer description can help locate an order, but the final decision should use recorded order fields and leave an inspectable reason for any failed eligibility check.

Finding: Refunds above GBP 50 require recorded supervisor approval before the action [L06].

An approval request should identify the exact order, amount, and proposed action. Keep that request separate from a customer's preference or an agent's confidence, and make the resulting approval available to the service that will enforce the decision.

Finding: The bank guidance offers a three to five business day estimate rather than an account-specific settlement promise [L07].

Customer wording deserves its own review rather than inheriting a passing grade from the transaction check. Read the proposed sentence as a commitment a customer might rely on, and identify which record could establish each time-sensitive assertion.

Finding: The supplied ledger cannot establish when the customer bank account will receive the money [L08].

Keep this uncertainty visible in the proposed response. A useful explanation can acknowledge the verified action and distinguish an estimate from confirmation, leaving the unresolved bank event for an appropriate evidence source instead of inventing a reassuring date.

Finding: Twenty-one of the 24 invented English pilot explanations accurately distinguished transaction status from settlement [L09].

Retain the case-level explanation record when presenting the headline result. A reader should be able to inspect the counterexamples and the meaning of the scoring criterion before treating the number as evidence for a broader service decision.

Finding: The explanation pilot cannot establish the future frequency of duplicate refunds [L10].

Do not compress different operational outcomes into an undifferentiated quality label. A transaction incident, an inaccurate explanation, and a delayed review require different evidence and repairs even when they appear within the same customer conversation.

Finding: Turkish text readiness remains undetermined because the packet contains no Turkish evaluation [L11].

Keep language scope adjacent to any score in the release memo. A reader should not have to infer whether a language was measured, deliberately excluded, or simply absent from a convenient sample that became the headline evaluation.

Finding: Voice readiness cannot be determined from the supplied evaluation packet [L12].

Treat this as an unanswered evidence question. A follow-up evaluation should state the voice task, interruption conditions, action boundaries, and review criteria before asking whether a text result can transfer to that setting.

Finding: The planned team has capacity for 40 reviews per day [L13]; The proposed batch is expected to generate 52 reviews per day [L14].

Present demand and capacity in the same unit and planning window. Keep forecast assumptions available for challenge, and avoid converting a neat spreadsheet result into a claim about how a queue will behave during a changing service day.

Finding: Under the stated assumptions the proposed batch exceeds daily review capacity by 12 cases [L15].

Decide what action the workload calculation supports. If the proposal needs a smaller batch or another staffing decision, record that dependency rather than hiding unresolved work behind an average completion score or a general promise to monitor.

Finding: Incremental operating cost cannot be determined from the supplied packet [L16].

Budget review should list the inputs needed for an estimate and identify who will supply them. Keep unknown cost distinct from an observed zero, and avoid letting a quality comparison stand in for an operating expense calculation.

Finding: The September policy supersedes the archived August fresh-key retry instruction for this incident [L17].

Place conflicting passages next to one another in the decision record. Explain whether the disagreement concerns dates, transaction state, or permitted actions, and preserve the losing interpretation so a reviewer can understand why it was not used.

Finding: The next proposed stage should be limited to supervised English text after the stated prerequisites are satisfied [L18].

A recommendation should state the evidence it depends on and the conditions that would change it. Keep the conclusion separate from its supporting observations so a reviewer can reject the proposed action without discarding every valid fact in the report.

Finding: The Support Operations Lead owns the decision to start the supervised pilot [L19].

Name the accountable role in the handoff rather than addressing a generic team. The start decision should remain pending until its evidence is assembled; identifying an owner does not by itself satisfy the prerequisites or approve an expansion.

Finding: One observed duplicate refund or unsupported settlement promise must pause the pilot and route the affected case to review [L20].

Keep the pause decision connected to an inspectable incident and its repair. The escalation record should carry the affected transaction, the explanation, and the evidence needed for the owner to decide whether a restart is warranted.

### Authored citation and finding ledger

Citation entailment concerns the whole finding, including material dates. Finding status judges the literal assertion under the task’s full evidence and temporal scope. Accurate statements that an outcome cannot be determined are supported; their separate abstention target remains unknown. An uncited finding still belongs in the denominator.

| Finding | Kind | Assertion status | Abstention target | Citation and source | Authored reason |
| --- | --- | --- | --- | --- | --- |
| C01 | factual | supported | Not assessed | L01 → S03 (entails) | The ledger directly distinguishes committed state from response delivery. |
| C02 | inference | supported | Not assessed | L02 → S03 (entails) | The transport observation and committed state can both hold; neither erases the other. |
| C03 | factual | supported | Not assessed | L03 → S01 (entails) | Current policy governs recovery; an existing transaction must be reconciled rather than duplicated. |
| C04 | factual | supported | Not assessed | L04 → S01 (entails) | The current policy specifies the monetary ceiling. |
| C05 | factual | supported | Not assessed | L05 → S01 (entails) | The current policy independently specifies the age window. |
| C06 | factual | supported | Not assessed | L06 → S01 (entails) | The approval requirement precedes action. |
| C07 | factual | supported | Not assessed | L07 → S04 (entails) | The statement preserves both the estimate and its limitation. |
| C08 | abstention | supported | unknown | L08 → S03 (entails) | A justified abstention: the account-specific settlement event remains unknown. |
| C09 | factual | supported | Not assessed | L09 → S05 (entails) | The count, language and invented sample scope are retained. |
| C10 | inference | supported | Not assessed | L10 → S05 (entails) | The conclusion respects the difference between explanation scoring and transaction outcomes. |
| C11 | abstention | supported | unknown | L11 → S06 (entails) | Appropriate abstention about readiness, rather than an unsupported release claim. |
| C12 | abstention | supported | unknown | L12 → S06 (entails) | A justified abstention, not an adverse capability verdict. |
| C13 | factual | supported | Not assessed | L13 → S07 (entails) | This is a staffing assumption, not measured throughput. |
| C14 | factual | supported | Not assessed | L14 → S07 (entails) | This is a planning forecast, not an observed arrival rate. |
| C15 | inference | supported | Not assessed | L15 → S07 (entails) | 52 minus 40 is 12; the inference remains conditional on planning assumptions. |
| C16 | abstention | supported | unknown | L16 → S08 (entails) | Missing price and usage evidence cannot establish zero cost. |
| C17 | inference | supported | Not assessed | L17 → S01 (entails) | The incident date is after the explicit replacement date; archival presence does not imply authority. |
| C18 | recommendation | supported | Not assessed | L18 → S09 (entails) | This recommendation stays within the invented contract and does not claim the prerequisites are already satisfied. |
| C19 | factual | supported | Not assessed | L19 → S09 (entails) | The owner is an invented role, not a real authorization. |
| C20 | factual | supported | Not assessed | L20 → S09 (entails) | The pause trigger is explicit and operates on either named failure. |

### Authored completeness review

| Question | Status | Findings | Reason |
| --- | --- | --- | --- |
| Q1 | answered | C01, C02, C03, C17 | The memo reconciles committed state, the transport failure, and the effective-date conflict. |
| Q2 | answered | C04, C05, C06 | Both eligibility limits and the prior-approval requirement are identified. |
| Q3 | answered | C07, C08 | The estimate is qualified and the missing account-specific settlement event is explicitly left unknown. |
| Q4 | answered | C09, C10, C11, C12, C18 | The pilot count and scope are preserved; Turkish and voice readiness are not inferred from English explanations. |
| Q5 | answered | C13, C14, C15, C16 | The conditional shortfall is calculated and cost remains unknown pending evidence. |
| Q6 | answered | C19, C20 | The report identifies the accountable role and the event-based pause condition. |

### Authored synthesis review

These are explicit evidence-to-conclusion judgments, not sentiment ratings or a model-generated summary. The support and conclusion IDs refer to this memo only.

| Review | Conclusion | Premises | Status | Reason |
| --- | --- | --- | --- | --- |
| SY01 | C17 | C01, C03 | supported | The incident date and governing current procedure support superseding the archived retry rule. |
| SY02 | C15 | C13, C14 | supported | The 12-case excess follows from 52 planned arrivals minus 40 available slots; it remains a planning result. |
| SY03 | C18 | C09, C10, C11, C12, C15, C16 | supported | A conditional supervised English-only proposal respects the narrow pilot, unknown channels, staffing shortfall, and missing cost; it is not approval to start. |
| SY04 | C08 | C01 | supported | A committed merchant transaction does not fill the unknown bank-settlement field; the abstention is justified despite an established transaction. |

## What changed—and what did not

The repaired memo changes the conclusions and adds the missing owner/pause findings. It does not change the source corpus, task date, questions, or rubric. In particular:

- The archived passage resolves, but it does not entail the explicitly September-scoped retry claim. A lexical match cannot erase a material date qualifier.
- The baseline cost assertion is uncited and unsupported. A cited-only extractor can hide that finding rather than improve its truth.
- The two eligibility clauses and the two workload clauses are separate propositions even though each pair shares one sentence.
- The workload conclusion must follow the quoted planning numbers; polished reasoning cannot make 52 fit inside 40.
- The repaired recommendation is conditional and limited to the invented supervised English-text contract. It does not assert readiness for immediate execution.
- The bank timing, untested channels, and operating cost remain evidence boundaries rather than inconvenient fields to fill with guesses.

Use [the long-report workshop](long-report-study.md) for the executed extraction and grading comparisons. Keep this casebook and the original report available when inspecting the repaired result; a correction should not erase the evidence that made the original failure understandable.
