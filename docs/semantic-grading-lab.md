# Semantic grading lab: qualification before interpretation

The runner now has an evaluator-owned semantic stage. A `SemanticJudge` receives a frozen evidence request and returns `pass`, `fail`, or `abstain` with a rationale and optional usage evidence. The stage—not the agent or judge—checks qualification and issues the context-bound receipt consumed by the grader.

**Implemented:** scoped registry checks, class-conditional calibration bounds, abstention limits, expiry/revocation controls, single-run and paired-run integration, retained request/judgment evidence, and offline replay with externally supplied trust.

**Not demonstrated:** a live model judge's accuracy, human-reviewed calibration, representative slice coverage, or qualification for production. The executable exercises use a clearly labeled fixture judge and synthetic calibration counts. A fixture that returns `pass` proves wiring, not that prose is true. A paid adapter and an independently reviewed calibration study remain delivery requirements.

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

The registry is trusted operator configuration, not proof that reviewers actually performed their work. Its label-artifact hash must resolve to real evidence outside this interface. The current implementation consumes reviewed counts; it does not yet ingest annotation rows, independently verify reviewer provenance, or infer qualification scopes from raw calibration data. Never change `synthetic` to `human_reviewed` to make a run pass.

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

The [judge chapter](llm-as-a-judge.md) explains rubric design, human calibration, bias, and risk–coverage trade-offs. The [delivery map](primer-delivery-map.md) tracks the remaining adapter, reviewed-data ingestion, live-study, and deployment-control work.
