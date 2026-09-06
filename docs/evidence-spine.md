# Evidence spine: from run to release authority

An evaluation result earns authority only when another person can reconstruct what ran, recompute the result from raw records, and see which decision rule was applied. This chapter turns that principle into an executable chain:

`case → isolated trial → paired experiment → statistical comparison → evidence receipt → release action`

The implementation lives in `cx_eval_lab/evidence.py`, `cx_eval_lab/statistics.py`, and `cx_eval_lab/runner.py`. The code is intentionally small enough to inspect. It is a teaching implementation, not a claim that a local synthetic run predicts production.

## The prerequisite graph

Evidence moves through five states:

| State | Meaning | Maximum action |
| --- | --- | --- |
| `locked` | A prerequisite contract or control is absent | Do not run for authority |
| `buildable` | The protocol is specified, but evidence is incomplete | Engineering only |
| `evidence_ready` | Raw artifacts and checks exist, but evidence is synthetic, inconclusive, or not transfer-qualified | `lab_pass`, `hold`, or `block` |
| `qualified` | An externally governed method and every prerequisite support bounded transfer | Reserved; no current local method emits this state |
| `expired` | A relevant component or population changed | Requalify before reuse |

This is not learner gamification. It is an authority state machine. Reading a chapter or running a command does not unlock deployment authority.

## Manifest before measurement

`ExperimentManifest` pins the experimental identity before candidate results are interpreted:

```python
manifest = ExperimentManifest(
    experiment_id="cx-rc4-vs-shipping-v3",
    created_at="2026-09-06T12:00:00Z",
    valid_until="2026-10-06T12:00:00Z",
    code_revision="<git revision>",
    model_id="<resolved model or deterministic implementation>",
    prompt_version="refund-system-v6",
    tool_version="typed-refund-tools-v1",
    dataset_version="refund-v1",
    evaluator_version="refund-evaluators-v1",
    policy_version="refund-gate-v1",
    environment_version="python-3.12-container-v4",
    population_hash="sha256:" + "a" * 64,
    repetitions=3,
    measurement_kind="synthetic",
    estimand="candidate_minus_baseline_verified_task_success",
    statistical_method="clustered_normal_interval",
    non_inferiority_margin=0.03,
    confidence_level=0.95,
    minimum_independent_clusters=30,
    sequential_policy="fixed_sample_no_interim_looks",
    input_hashes=(
        ("dataset", "sha256:" + "b" * 64),
        ("policy", "sha256:" + "c" * 64),
    ),
    invalidation_rules=(
        "model_or_prompt_change",
        "tool_or_evaluator_change",
        "dataset_or_policy_change",
    ),
)
```

The canonical JSON content hash identifies this exact manifest. The estimand, method, margin, confidence level, minimum independent clusters, stopping policy, population, and validity window are decision inputs—not post-run arguments. Changing a relevant prompt, model, tool, dataset, evaluator, policy, population, or statistical plan changes the hash. A friendly experiment name never substitutes for a reconstruction record. Measured evidence also requires a pinned code revision; `working-tree-unpinned` is rejected.

## Independent replay of retained executions

Paired summaries now reference complete, content-addressed trial artifacts. These preserve the original case, agent input, initial/final state, tool events, output, available runtime usage, measurement provenance, execution error, semantic receipt slot, and original grading result. `cx_eval_lab/artifacts.py` reconstructs the deterministic evaluation instead of trusting its saved pass/fail label.

After generating an experiment packet, run:

```bash
uv run python -m cx_eval_lab replay --input artifacts/runs/paired-reference.json
```

Replay rejects changed artifact hashes, missing or duplicated evidence, incorrect identity links, inconsistent summaries, missing paired repetitions, and population membership that differs from the manifest. It returns `lab_only` even when every grade matches. It does not authenticate execution provenance, enforce the installed code revision, verify source files against all manifest hashes, or qualify the statistical method. Old summary-only packets remain useful for aggregate exercises but cannot pass full replay. See [Kata 04](micro-katas.md#kata-04-recompute-a-grade-not-just-an-average) for the worked solution and mutation tests.

## Repeated trials are not new cases

`run_paired_experiment` resets the world for every candidate and baseline trial and emits stable keys `(case_id, trial_index)`. Repeating one customer situation measures stochastic reliability; it does not create more independent customer situations. Each trial therefore also carries `cluster_id`, normally the customer or session sampled from the target population.

```python
experiment = run_paired_experiment(
    baseline_agent=baseline,
    candidate_agent=candidate,
    cases=cases,
    manifest=manifest,
    baseline_measurement_profile=baseline_profile,
    candidate_measurement_profile=candidate_profile,
)
```

The runner fails closed when the manifest dataset or measurement kind disagrees with the supplied cases or profiles. Missing, duplicated, or mismatched trial keys are rejected by the statistical comparison rather than silently dropped.

Run the complete deterministic evidence path with:

```bash
uv run python -m cx_eval_lab experiment \
  --baseline-agent reference \
  --candidate-agent reference \
  --minimum-independent-clusters 30 \
  --output artifacts/runs/paired-reference.json
```

The default five-case dataset produces ten records per arm because the registered default is two repetitions. With a thirty-cluster minimum, the command exits with `hold`: ten repeated trials still represent only five independent customer clusters. Passing `--minimum-independent-clusters 5` exercises a synthetic `lab_pass` for teaching, but it does not turn five customers into adequate production evidence. The output packet contains the manifest and its hash, every raw trial, the recomputed comparison, raw-artifact hash, content-addressed prerequisite and test receipts, component hashes, issue/expiry times, invalidation rules, and the receipt's own content hash. The command refuses to overwrite an existing packet path.

## Statistical non-inferiority

For paired binary outcomes, define (d_i=y_{candidate,i}-y_{baseline,i}). A registered non-inferiority claim with margin \(\Delta\) is supported when the lower confidence bound for the candidate-minus-baseline contrast satisfies:

\[
L \ge -\Delta
\]

The executable implementation first averages repeated differences within each independent cluster, then forms a normal interval over cluster means. It reports the point difference, both bounds, pair count, independent-cluster count, method, confidence level, and minimum evidence.

!!! warning "Method limitation"
    The clustered normal interval is a transparent teaching implementation. Rare events, small samples, unequal clusters, adaptive stopping, and heavy dependence can require exact, bootstrap, randomisation, Bayesian, or hierarchical methods. Pre-register the method that matches the estimand and sampling process; do not choose it after seeing the result.

### Three different decisions

| Evidence | Correct result |
| --- | --- |
| Lower bound `−0.020`, margin `0.030` | Non-inferior under the registered inclusive rule; not superior if the interval includes zero |
| Lower bound `−0.031`, margin `0.030` | Non-inferiority not established |
| Twelve independent customers when thirty were required | `inconclusive`, even if every observed pair ties |

The scalar point-floor check in the first five-case demo remains useful for testing gate plumbing, but it is named `illustrative_point_floor:task_success`. It is not the statistical decision described here.

## Sample size and sequential looks

Choose sample size from the smallest decision-relevant degradation, baseline rate, target power, confidence level, clustering, expected missingness, and protected-slice requirements. “Thirty” in the executable example is a minimum-evidence fixture, not a universal sample-size recommendation.

If results are inspected repeatedly, register the look schedule and error-control method. A safe sequential record includes:

```yaml
looks: [250, 500, 1000]
stopping_rule: registered_alpha_spending_or_bayesian_rule
early_stop_for_harm: hard_invariant_or_safety_boundary
early_stop_for_success: only_when_registered_boundary_is_crossed
all_looks_retained: true
```

Stopping when a favourable interval first appears inflates the error rate. Operational harm rules may still stop exposure immediately; statistical evidence and safety containment are different controls.

## Noisy labels and judge-error propagation

When a model judge supplies the binary outcome, the interval measures variation in judge-labelled outcomes—not automatically variation in customer truth. Report:

- raw judge estimate;
- sensitivity and specificity on a representative frozen human set;
- corrected estimate when assumptions justify it;
- uncertainty from both sampling and judge calibration;
- slice-specific false-pass rates and abstention;
- the requalification trigger for judge, prompt, rubric, parser, or population change.

A judge-qualified interval cannot override an executable side-effect contradiction. Use deterministic external state for transactions, schema validity, permissions, and exact calculations; reserve judges for criteria that genuinely require semantic interpretation.

## Repeated holdout use

A sealed set becomes optimisation data once results repeatedly shape development. The receipt should count accesses, record which outputs were exposed, and expire the set according to policy. Use nested or rolling holdouts, refresh from independently reviewed traffic, and distinguish confirmatory analyses from exploratory slice discovery.

## Evidence receipt and authority ceiling

`build_evidence_receipt` accepts the full paired experiment and content-addressed test/prerequisite receipts. It does **not** accept a caller-supplied comparison, hard-failure count, or raw-artifact hash. It verifies every trial's manifest hash, recomputes the paired comparison using the registered plan, counts candidate hard failures, and hashes the raw experiment itself. Its decisions are deliberately asymmetric:

- missing or unqualified prerequisites → `locked` and `block`;
- failed deterministic checks → `buildable` and `block`;
- insufficient independent evidence → `hold`;
- statistical failure or any hard failure → `block`;
- a passing result under the current teaching method → `lab_pass`, authority `lab_only`, whether its runtime fields are synthetic or measured.

The current registry contains no method capable of returning `canary_eligible`. Adding one requires a separately qualified statistical implementation, trusted qualification provenance, a production transfer study, a blast limit, monitoring, rollback, mature outcomes, and accountable permission to expose real traffic.

`resolve_evidence_authority` compares the receipt with current component hashes and its validity window. A dataset, policy, or population mismatch—or passing the expiry time—returns `expired`, `block`, and authority `none`. Re-running the resolver with unchanged inputs is idempotent.

Content addressing detects mutation and binds components; it does not authenticate who produced a receipt. A production service should verify issuer identity or signatures and store receipts in an access-controlled append-only system. The local lab therefore never promotes its content-addressed receipts above `lab_only`.

## Artifact: paired evidence receipt

The inspectable fixture `evals/cx-support/examples/paired-evidence-receipt-v1.json` is a compact summary of thirty paired independent synthetic cases with a zero difference. The runnable CLI emits the complete row-level packet and recomputes its aggregate. Both remain `lab_only` despite passing the teaching rule.

## Failure-injection checklist

Before trusting the spine, prove it rejects:

- a missing baseline or candidate pair;
- a duplicated trial key;
- an omitted failure row;
- a manifest hash changed after execution;
- fabricated cost provenance;
- too few independent clusters disguised as many repeated trials;
- a hard failure hidden by a favourable average;
- synthetic or measured runs attempting to obtain canary authority from the teaching method;
- forged caller-supplied comparisons, hard-failure counts, or raw hashes;
- expired receipts and current-component drift;
- test receipts from a different code revision.

## Exercise: diagnose the receipt

A system has 300 paired trials created from ten customers, a favourable point estimate, no observed authorization failures, and a measured latency field copied from a synthetic profile. The registered minimum is thirty independent customers.

??? success "Answer"
    The decision is `inconclusive` or `block`, not canary eligibility. There are only ten independent clusters, and the latency provenance is falsely labelled. Repetition improves knowledge about stochastic behaviour on those ten customers but does not satisfy the population-evidence minimum. Correct the provenance, sample the required independent units, retain exact trial pairs, and rerun the registered comparison.
