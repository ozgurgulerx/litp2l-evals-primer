# Semantic grading lab: qualification before interpretation

The runner now has an evaluator-owned semantic stage. A `SemanticJudge` receives a frozen evidence request and returns `pass`, `fail`, or `abstain` with a rationale and optional usage evidence. The stage—not the agent or judge—checks qualification and issues the context-bound receipt consumed by the grader.

**Implemented:** scoped registry checks, class-conditional calibration bounds, abstention limits, expiry/revocation controls, single-run and paired-run integration, retained request/judgment evidence, and offline replay with externally supplied trust.

**Not demonstrated:** a live model judge's accuracy, human-reviewed calibration, representative slice coverage, or qualification for production. The executable exercises use a clearly labeled fixture judge and synthetic calibration counts. A fixture that returns `pass` proves wiring, not that prose is true. An optional provider adapter is now implemented and exercised offline in Katas 36–37 below; a metered live study and independently reviewed calibration remain delivery requirements.

## The execution contract

1. Execute the agent against the resettable world and freeze its output, tool events, and final state.
2. Resolve an operator-selected calibration hash in the trusted registry. Reject missing or revoked entries.
3. Check criterion, evaluator version, configuration hash, dataset, domain policy, exact joint slice, validity window, class counts, error bounds, and abstention rate.
4. Give the judge customer input, output claims, tool evidence, final state, and authoritative order/policy facts. Omit the expected outcome label, injected fault settings, and experimental arm.
5. Retain the judge's result, rationale, usage, and elapsed time; check qualification again after the call in case it expired.
6. Have the evaluator issue the receipt and combine semantic evidence with independent transaction and policy checks.

`SemanticStage` in `cx_eval_lab/semantic.py` implements this path. Both `evaluate_agent(..., semantic_stage=stage)` and `run_paired_experiment(..., semantic_stage=stage)` support it. No judge runs unless a stage is supplied. The current command-line agent runner does not configure a live judge automatically.

## What a calibration record means

| Field or rule | Why it matters |
| --- | --- |
| Criterion and evaluator version | Qualification for truth does not grant authority over tone or policy compliance |
| Configuration hash | Bind the resolved judge model, rubric/prompt, parser, and settings; a friendly version name is insufficient |
| Label-artifact hash | Identify the independently retained calibration judgments and reviewed labels |
| One joint slice scope per record | Aggregate English and Turkish accuracy cannot establish each slice separately |
| Truthful and false example counts | Expose the denominators behind false blocks and false passes |
| Class-conditional upper bounds | Zero observed errors is not evidence of zero population error |
| Abstention count and limit | A judge cannot qualify for useful automation merely by declining difficult cases |
| Issue, expiry, revocation | Qualification is time-limited and can be withdrawn |
| Evidence kind | Synthetic records may exercise lab plumbing but cannot qualify measured runs |

The registry is trusted operator configuration, not proof that reviewers actually performed their work. Its label-artifact hash must resolve to real evidence outside this interface. Direct construction of `CalibrationRecord` still accepts operator-supplied counts; the new `compile_calibration` ingestion path derives those counts from retained annotation rows and checks their declared scope. Neither path independently authenticates reviewers or establishes that sampling was representative. Never change `synthetic` to `human_reviewed` to make a run pass.

Counts are limited to 500 examples per class in this teaching implementation because its exact-binomial helper is deliberately bounded. Errors are evaluated with one-sided 95% upper bounds, obtained from the upper endpoint of a two-sided 90% exact interval. Each error bound is marginal: the two simultaneous claims are not automatically a joint 95% guarantee. Correlated or repeatedly reused calibration examples require a different analysis.

For truthful examples, `false_blocks` counts all non-pass outcomes, including abstentions. For false examples, `false_passes` counts erroneous passes; abstentions are not false passes but remain in the separate abstention count. The configured numerical limits are policy inputs to register before qualification, not universal production defaults.

## Kata 08: zero errors, insufficient qualification

**Know:** calibration sample size and tolerated false-pass risk determine whether zero observed errors is convincing.

**Situation:** the judge makes zero false passes among thirty independently reviewed false statements. The registered maximum false-pass upper bound is 5%. It also meets a minimum-count rule of thirty examples per class.

**Predict:** should the registry accept it? What changes with one hundred false statements and zero false passes?

```bash
uv run python -m unittest tests.test_semantic_stage -v
```

??? success "Solution and calculation"
    With no errors among `n` independent class examples, the one-sided 95% upper error bound is `1 − 0.05**(1/n)`.

    At thirty examples it is about 9.50%, which exceeds the 5% policy limit. Passing the minimum count does not establish qualification. At one hundred examples it is about 2.95%; that class clears the bound, subject to the other class, abstention, scope, configuration, and provenance requirements.

    `CalibrationRecord.error_bounds` performs the calculation. `test_expiry_scope_version_and_small_sample_block_qualification` verifies that both insufficient count and excessive uncertainty prevent even calling the judge.

**Extend:** add one false pass and recompute the bound. Then change the rubric but leave the calibration counts unchanged. The new configuration hash must invalidate the old qualification, regardless of the attractive counts.

**Interview answer:** “I qualify a judge against class-conditional error bounds for a registered criterion and population, not one agreement score. Zero observed false passes can still be too uncertain to grant the required authority.”

## Kata 09: false, unknown, and unqualified are different

**Know:** the measurement instrument's qualification is separate from its answer.

| Stage outcome for free-form prose | Report interpretation |
| --- | --- |
| Current, scoped qualification; judge returns `pass` | Semantic check can pass; other invariants still apply |
| Current, scoped qualification; judge returns `fail` | Count a false-message finding, not missing qualification |
| Judge returns `abstain` or raises an error | Abstention and unqualified message; do not treat as success |
| Missing, revoked, expired, changed, or out-of-scope qualification | Unqualified message; judge is not called |
| Qualification expires while judging | Retain the judgment but withhold its qualifying receipt |

**Task:** run a free-form reference response through each state. Then give a passing semantic judgment to a response whose structured claims promise settled money even though the world only proves a committed payment instruction.

??? success "Solution and inspection"
    `tests/test_semantic_stage.py` executes these cases. `FixtureJudge` is a control double, not a semantic model. The runner creates a receipt after checking its configuration; the judge cannot submit a receipt or choose a calibration hash through its output contract.

    `test_qualified_negative_judgment_is_a_false_claim_not_missing_qualification` verifies the negative-grade distinction. `test_semantic_pass_cannot_override_an_impossible_settlement_claim` verifies that a semantic pass cannot buy away a deterministic contradiction. Revocation and expiry tests exercise qualification both before and after judging.

**Extend:** make a judge return an invalid schema, then raise a timeout containing sensitive details. The stage abstains and retains the error type rather than the raw exception message. The adapter must impose its own finite request timeout: this synchronous stage catches returned timeout errors but cannot forcibly stop an indefinitely hung adapter.

**Interview answer:** “I separate invalid instrumentation, abstention, and negative findings. They may all block exposure, but they need different repairs. A judge's semantic pass does not override authoritative transaction evidence.”

## Kata 10: preserve the judge's evidence without changing the customer metric

**Know:** customer response latency, evaluator latency, application spend, and evaluation spend answer different questions.

**Situation:** the synthetic agent profile costs $0.08 per case. The fixture judge supplies $0.001 of separately labeled usage evidence. Where should those numbers appear?

??? success "Solution and retained fields"
    The case's application cost remains $0.08. The judge's $0.001 is retained under `semantic_stage.judgment.runtime_evidence.cost_usd`, with its provider/model identity, response identifiers, and token counts when available. Judge elapsed time appears as `semantic_stage.judge_latency_ms`; it does not retroactively increase the measured customer-response latency.

    `test_single_run_preserves_semantic_audit_and_usage_separately` verifies the separation. Single-run reports and paired trial artifacts retain the qualification record, bounds, supplied evidence, request hash, judgment, rationale, and judge timing. Do not call either cost field “total operational cost”: tools, storage, reviewers, and other costs remain separate or unknown.

    Paired replay reconstructs the deterministic grade from the retained semantic receipt without rerunning the judge. It requires independently supplied trusted calibration hashes; listing a hash inside the packet cannot self-authorize it. See [Kata 04](micro-katas.md#kata-04-recompute-a-grade-not-just-an-average).

**Extend:** distinguish historical replay from current requalification. A receipt can explain what a previously qualified judge decided, while expiry or revocation prevents that judgment from authorizing a new deployment. The current replay CLI does not load a qualification registry; semantic replay with explicit external trust uses the Python API.

**Interview answer:** “I preserve the evidence supplied to the judge and its versioned decision, not just the final score. I account for evaluator spend and latency separately, and I distinguish reproducing a historical grade from renewing its authority.”

## From this lab to a genuine qualified judge

The next deliverable is not a larger fixture set. It is a frozen, independently reviewed calibration artifact for a resolved model/rubric configuration, with class and slice denominators, disagreements, abstentions, error bounds, held-out checks, and explicit limits. The runner can now consume a judge through the protocol, but no live semantic study or production qualification is claimed here.

The [judge chapter](llm-as-a-judge.md) explains rubric design, human calibration, bias, and risk–coverage trade-offs. The [delivery map](primer-delivery-map.md) tracks the remaining adapter, authenticated reviewed-data provenance, live-study, and deployment-control work.

## Kata 18: reconstruct calibration from the labels

The [retained compilation packet](assets/calibration-compiled-v1.json) contains four synthetic examples. The people-like reviewer identifiers and judge verdicts are teaching fixtures, not real annotations or model calls.

| Customer explanation and supplied state | Final reference label | Fixture judge | Contribution |
| --- | --- | --- | --- |
| “Identity was not verified”; `verified=true` | False | Pass | One false pass |
| “The order is ineligible”; `eligible=false` | Truthful | Fail | One false block |
| “The money has settled”; committed but not settled | False, after adjudication | Abstain | One abstention, no false pass |
| “The instruction was recorded”; committed | Truthful | Pass | Correct pass |

**Know:** a class error rate needs its own denominator. A false pass is a pass on a false statement, not the fraction of all rows that happen to be wrong. On truthful statements, this lab counts both failure and abstention as blocking useful automation.

**Task:** compute the counts before running the compiler. Does successfully generating a record mean the judge is qualified?

```bash
uv run python -m cx_eval_lab.calibration_data \
  --input evals/cx-support/examples/calibration-annotations-v1.json \
  --config evals/cx-support/examples/calibration-policy-v1.json \
  --output /tmp/primer-calibration-my-first-run.json
uv run python -m unittest tests.test_calibration_data -v
```

Choose a fresh output path on subsequent runs. The CLI refuses to overwrite an existing artifact. It makes no network or model calls.

??? success "Solution: compilation is not qualification"
    The denominators are two truthful and two false examples. There is one false pass, one false block and one abstention. Both class error estimates are 50%; the overall abstention rate is 25%. The configured minimum is thirty per class, the class upper-bound limits are 5%, and the abstention limit is 20%.

    Compilation succeeds because the evidence is structurally consistent and the counts can be computed. Qualification fails. Even in synthetic test mode it fails the minimum-count rule; measured runs also reject synthetic evidence. The other limits are not waived just because an earlier check already rejects the record.

    `compile_calibration` in `cx_eval_lab/calibration_data.py` derives every count. Its policy input cannot override `false_passes`, `false_blocks`, denominators or the label-artifact hash. The output retains the complete input, operator configuration, computed record and error bounds. `deployment_authorized` stays false.

**Extend:** change the truthful rejected example's fixture verdict from `fail` to `abstain`. False blocks remain one; abstentions rise to two. Change only its message without updating the judgment evidence binding: compilation must reject it, because that verdict refers to different evidence.

**Interview answer:** “I retain row-level reference labels and judge outcomes so qualification statistics can be recomputed. Producing a valid record does not mean it clears registered error limits, has authentic provenance, or authorizes deployment.”

## Kata 19: disagreement cannot disappear into an aggregate

In the settlement example, reviewer A labels the statement false and reviewer B labels it truthful. A third reviewer resolves it as false because a recorded payment instruction does not establish settlement. All three identifiers are explicitly synthetic in this artifact.

**Task:** remove the adjudication, then let reviewer A adjudicate their own disagreement. Finally restore the third reviewer but remove the rationale. Predict each result.

??? success "Solution: retain the conflict and its resolution"
    All three mutations fail. This teaching ingestion contract requires two distinct allowed reviewers, resolved binary labels, and—for disagreement—a third allowed reviewer with a nonempty reason and a resolved label. It retains the original disagreement rather than replacing both original labels with the adjudicated answer.

    An agreed pair cannot be silently overridden by adding an adjudication. A label correction needs a new reviewed artifact, with the prior version retained through the operator's versioning process. The compiler does not implement an annotation-service audit log.

    The local tests also reject unknown reviewer IDs, duplicated reviewer identities and unresolved labels. “Uncertain” is not forced into either truth class: the packet is held for resolution or an explicitly revised study protocol. Do not silently drop hard rows to improve apparent agreement.

**Operational extension:** before collecting actual labels, freeze the rubric and judge configuration, blind reviewers to the judge verdict and experimental arm, pilot on development data, then collect independent calibration annotations. Record reviewer training, disagreement categories and adjudication. The compiler checks declared identities against an operator allowlist; it cannot verify blinding, independence, human participation or the truth of the reference label. An annotation service or reviewed export must establish those facts.

**Interview answer:** “Agreement is not truth, and adjudication is not a reason to erase disagreement. I preserve original labels, the resolution and its evidence; difficult unresolved examples remain visible in the study accounting.”

## Kata 20: improve the dataset without contaminating qualification

You discover the same customer session in development and calibration. Its text differs slightly after redaction. A message-only duplicate check misses it.

**Task:** put that session's `group_id` in the operator configuration's `excluded_group_ids`. Then try copying a calibration row under a new row ID but keeping its evidence unchanged. Finally change one row's judge configuration or policy scope.

??? success "Solution: reject leakage, dependence and mixed instruments"
    The compiler rejects all these cases. It accepts only the calibration split, one declared dataset/policy/joint-slice scope and one judge configuration. It checks unique row IDs, group IDs and exact evidence hashes, plus externally supplied excluded groups and hashes. Judgment evidence hashes must match the retained evidence.

    One row per declared group is a deliberate restriction of this simple exact-binomial teaching path. It does not solve correlated annotation statistics or prove independent sampling. If several examples from one customer/session are required, retain them in a separate study using an appropriate clustered method rather than renaming the groups to satisfy this compiler.

    Populate the exclusion inventories from development and sealed-set manifests maintained outside the candidate's authority. The example uses empty inventories because it has no real development or sealed corpus; that is not a verified absence of leakage. Exact hashing cannot detect paraphrases or semantic near-duplicates. Group lineage and an independently reviewed similarity audit remain necessary.

**Dataset-improvement loop:** classify an observed production failure; redact and review it; preserve incident provenance; add it to development/regression data; revise the rubric or agent; freeze the changed versions; collect independent calibration evidence; evaluate on an untouched sealed set. Do not move the optimized-on incident into calibration and call its passing score independent validation. If a sealed case is exposed during debugging, record that exposure and retire it from future untouched-holdout claims.

**Interview answer:** “Dataset improvement and evaluator qualification use different data roles. I promote incidents into reviewed regression examples, preserve lineage, and requalify changed judges on independent evidence rather than repeatedly optimizing the acceptance set.”

### What this addition proves—and leaves open

The compiler and CLI are executed local implementations, and the four-row artifact can be reconstructed from its retained labels. They close the manual-count reproducibility gap for this ingestion path. They do not authenticate reviewer identities, enforce pre-registration timestamps, validate reference-label accuracy, discover hidden lineage, or supply a live judge study. Existing direct construction of operator-trusted records remains supported; production registry admission must require independently verified artifacts rather than treat either a content hash or a caller's `human_reviewed` string as proof.

## Kata 36: a passing JSON verdict is not a usable judgment

A provider response contains `{"verdict":"pass","explanation":"supported"}`. Its envelope says `incomplete`. Another returns the same JSON from an unregistered model. A third includes a refusal alongside the JSON. Which judgments may the evaluator use?

**Know:** inspect the provider envelope before interpreting the verdict. Parsing JSON establishes a data shape, not a completed request, the identity of the instrument, or factual accuracy.

The optional `OpenAIResponsesJudge` in `cx_eval_lab/openai_judge.py` implements `SemanticJudge`. Its configuration requires an explicit model. The adapter sends one non-streaming request with a strict verdict schema, no tools, disabled input truncation, an output-token limit, and SDK retries set to zero. It rechecks the effective client endpoint before sending. These are inspectable implementation choices, not a recommendation to use an unspecified model.

**Run offline:** install the optional SDK to exercise its actual serialization through an in-memory HTTP transport. The test supplies a clearly synthetic credential to that transport; it neither reads a real key for the request nor sends network traffic to a model.

```bash
uv sync --frozen --group dev --extra openai
uv run --extra openai python -m unittest tests.test_openai_judge -v
```

**Task:** predict the result for each envelope above. Then try missing usage, duplicate `verdict` JSON keys, and a changed client endpoint after constructing the judge. Does any transport test establish the truth of “the refund has settled”?

??? success "Solution: retain the response, abstain on an unusable instrument result"
    Incomplete responses, refusals, model mismatch, malformed verdicts and invalid usage abstain. A changed effective endpoint blocks before sending. No provider `pass` becomes a qualifying receipt directly: the evaluator-owned stage must separately check the operator-selected calibration record and bind the judgment to case evidence.

    Where a usable response envelope exists, the adapter retains its full serialized body in `provider_audit_json`, alongside configuration identity and a cost-unknown flag. Missing or oversized envelopes are explicitly marked `response_not_retained`; they do not acquire a pass. An oversized serializable response retains a content hash, not a replayable replacement for its missing body.

    The integration test runs two repetitions for each of two arms: four synthetic provider calls, four retained trial artifacts, and four replayed grades. Its registry and verdicts are synthetic. That proves stage/runner/artifact plumbing, not semantic accuracy, independent human review, or authenticated execution provenance.

**Extend:** change the rubric, model or timeout while keeping the old registry record. The configuration hash changes. The stage must reject that old qualification before calling the newly configured judge. In a real study, pin the approved model identity; a returned identity mismatch deliberately abstains rather than silently treating an alias change as equivalent.

**Interview answer:** “I distinguish a syntactically valid verdict, a usable provider response, and a currently qualified judgment. I retain rejected evidence, and I do not turn infrastructure uncertainty into either a factual pass or a factual failure.”

## Kata 37: timeout does not mean free—and token cost is not total cost

The fixture reports 100 input tokens and 20 output tokens. For arithmetic only, the test supplies invented rates of $2 and $8 per million tokens. A second request times out before returning usage. A third claims `10**400` input tokens.

**Task:** compute the first estimate. Should the timeout contribute zero dollars? Should malformed metering crash the whole experiment or discard the response that exposed it?

??? success "Solution: compute the known estimate and preserve missingness"
    The first estimate is `(100 × 2 + 20 × 8) / 1,000,000 = $0.00036`. These are fixture prices, not current provider prices. The result is an operator-supplied, undiscounted token-cost estimate; cache discounts, service-tier differences and operational costs are excluded.

    The timeout abstains, records the exception type without copying potentially sensitive exception text, and marks cost unknown. The adapter performs no retry. The provider might still have processed the request; absence of returned usage does not prove zero expenditure or server cancellation.

    The extreme integer response abstains while preserving its raw usage in the audit. Parsed token fields and cost remain unknown. A defensive one-billion-token envelope bound prevents malformed metering arithmetic; it is not a model context limit, a pricing rule, or a campaign budget. Unrepresentable numeric configuration is rejected before a request.

    The paired runner's `cost_usd` currently represents agent cost. Judge cost and elapsed time remain separate in semantic audit. Summing them for a complete experiment budget, handling unknown-cost requests, and enforcing a campaign reservation/stop policy remain implementation work. Do not describe the current packet's agent-cost column as total spend.

**Limits to know:** `max_input_bytes` bounds the supplied evidence JSON, not the rubric/schema/full request. `max_response_bytes` checks retention after SDK download and deserialization; it is not a network-memory limit. A transport timeout is not a hard experiment deadline. The SDK/client and operator registry remain trusted dependencies; endpoint checking is not network attestation. `store=False` is a request setting, not proof of zero provider retention. Full provider bodies can contain sensitive customer material: protect real artifacts, and publish only reviewed synthetic or appropriately redacted examples.

**Before a live run:** select an approved agent and judge model, freeze the configuration and dataset, obtain a total spend cap, establish independent calibration evidence, and configure an operator-owned stage with synthetic admission disabled. The existing Python runner accepts that stage; the CLI does not silently create one. These offline exercises require none of those paid calls and do not stand in for them.

**Interview answer:** “I account separately for application cost, evaluation overhead, and unknown expenditure. A timeout cannot clear a spend gate merely because its response is missing. Likewise, a valid cost estimate cannot qualify the judge's factual accuracy.”
