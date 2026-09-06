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

Default replay rejects changed artifact hashes, missing or duplicated evidence, incorrect identity links, inconsistent summaries, missing paired repetitions, and population membership that differs from the manifest. It returns `lab_only` even when every grade matches. Without the source-verification option below, it does not enforce the local code revision or verify source files against manifest hashes. Neither mode authenticates execution provenance or qualifies the statistical method. Old summary-only packets remain useful for aggregate exercises but cannot pass full replay. See [Kata 04](micro-katas.md#kata-04-recompute-a-grade-not-just-an-average) for the worked solution and mutation tests.

### Source-checked replay: labels, files and actual case inputs

The [retained source-verification packet](assets/source-verified-replay-v1.json) was generated locally with a deterministic reference agent in both arms. The source/input check verified **30 files and five complete dataset cases**, then reproduced **20 trial grades**. Its `lab_pass` is still a small synthetic exercise, not statistically qualified deployment evidence.

New `experiment` CLI packets record raw-byte SHA-256 hashes for all package Python files, `pyproject.toml`, `uv.lock`, the dataset and the release policy. The CLI records the local Git revision by default; an explicit `CXLAB_CODE_REVISION` override remains possible, but is checked rather than trusted in strict replay. Capturing dirty-file hashes does not make those files part of the recorded commit.

The optional source check requires three independently retained operator inputs: the experiment packet digest, the full expected commit ID and the expected evaluator version. Dataset and policy paths come from explicit operator options or documented defaults, never from paths invented by the packet.

For the retained example, use a controlled checkout at commit `256f52ce755bb59f0fdfa5f1a843ad7ae5d212a0`. Save the linked packet separately as `artifacts/source-verified-replay-v1.json`; the packet was added alongside this chapter after that source commit. Install the locked development environment in that checkout, then run:

```bash
uv run python -m cx_eval_lab replay \
  --input artifacts/source-verified-replay-v1.json \
  --verify-source \
  --expected-code-revision 256f52ce755bb59f0fdfa5f1a843ad7ae5d212a0 \
  --expected-evaluator-version refund-evaluators-v1 \
  --trusted-packet-hash sha256:afed7ba26f2200e135e5be2cdfe15d5abf81de901a6def301893ca4a66561158
```

Observed output:

```text
source/input consistency verified: 30 files; 5 dataset cases; not execution attestation
replayed 20 trials; authority: lab_only; no model calls
```

These identities are published teaching references, not a signed independent attestation. In an operating service, the producer records the packet digest outside the candidate's write scope; the verifier receives it through a trusted channel. Calculating a digest from an untrusted packet and immediately declaring that value trusted establishes no provenance.

The verifier checks that the manifest revision, operator revision and checkout HEAD agree; source inventory is complete; source bytes match both the manifest and original committed Git objects; and every non-source input has an operator-supplied file mapping and matching raw bytes. Git replacement refs are disabled. Source-tree symlinks and symlinks in supplied input paths are rejected. Files are limited to 64 MiB each. A later checkout—even one with only documentation commits—must not masquerade as the recorded revision: use the exact source checkout or create a new experiment.

After file verification, every retained case must match the supplied dataset in full, not merely in case ID, customer and slices. The check also compares the original agent input and complete case membership. This catches an altered refund amount or eligibility flag that would survive an IDs-only population check. Trial repetition/arm completeness and grading are then checked by replay.

Keep four boundaries explicit:

- **File consistency is not proof of execution.** A fabricated trace can use genuine source and input files. This check does not attest to loaded bytecode, installed dependency equivalence, model-provider execution or a remotely observed backend state. Use a controlled, non-mutating checkout; this is not a race-proof hostile-filesystem sandbox.
- **A lockfile hash is not an environment attestation.** It records the declared dependency solution, not what the interpreter actually imported. Environment verification remains additional work.
- **Policy-file consistency is not release-decision replay.** The outer decision is not recomputed here. The manifest's `refund-gate-v1` release policy is distinct from a trial's `refund-policy-v1` semantic/domain policy; the two version strings must not be compared as though they name the same object.
- **Source verification is not current judge qualification.** The CLI still lacks the current-registry assessment performed by the separate API in [Katas 32–33](micro-katas.md#kata-32-reproduce-yesterday-without-approving-today). Legacy packets without source hashes remain historically replayable but cannot pass the strict source check.

For executable mutation exercises and interview answer criteria, continue with [Katas 34–35](micro-katas.md#kata-34-the-version-label-did-not-change).

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

The [executed statistical study](statistical-method-study.md) now provides a concrete counterexample: with thirty independent customers and true degradation of four points, this normal rule passes 29.39% of the time despite a three-point margin. A zero-discordance sample yields zero estimated variance. The minimum-count check does not qualify the method; do not promote its `lab_only` result to production authority.

| Evidence | Correct result |
| --- | --- |
| Lower bound `−0.020`, margin `0.030` | Non-inferior under the registered inclusive rule; not superior if the interval includes zero |
| Lower bound `−0.031`, margin `0.030` | Non-inferiority not established |
| Twelve independent customers when thirty were required | `inconclusive`, even if every observed pair ties |

The scalar point-floor check in the first five-case demo remains useful for testing gate plumbing, but it is named `illustrative_point_floor:task_success`. It is not the statistical decision described here.

## Sample size and sequential looks

The [Sequential Decisions Lab](sequential-decisions-lab.md) now executes this distinction: ten repeated fixed-sample tests falsely promote 11.08% of runs at its registered null boundary, versus 2.40% for the worked likelihood-ratio rule on the same look schedule. Katas 28–31 expose the iid Bernoulli assumptions, power trade-offs, label/dependence failures and campaign-level multiplicity. These results do not qualify the general clustered comparison implemented elsewhere in this chapter.

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

`build_evidence_receipt` accepts the full paired experiment and content-addressed test/prerequisite receipts. It does **not** accept a caller-supplied comparison, hard-failure count, or raw-artifact hash. It verifies every trial's manifest hash, recomputes the paired comparison using the registered plan, counts candidate trials with failed checks, and hashes the raw experiment itself. The field named `hard_failure_count` currently includes any candidate failed check, including missing semantic qualification; it is not a count restricted to harmful side effects. Its decisions are deliberately asymmetric:

- missing or unqualified prerequisites → `locked` and `block`;
- failed deterministic checks → `buildable` and `block`;
- insufficient independent evidence → `hold`;
- statistical failure or any candidate failed-check trial → `block`;
- a passing result under the current teaching method → `lab_pass`, authority `lab_only`, whether its runtime fields are synthetic or measured.

The current registry contains no method capable of returning `canary_eligible`. Adding one requires a separately qualified statistical implementation, trusted qualification provenance, a production transfer study, a blast limit, monitoring, rollback, mature outcomes, and accountable permission to expose real traffic.

`resolve_evidence_authority` compares the receipt with current component hashes and its validity window. A dataset, policy, or population mismatch—or passing the expiry time—returns `expired`, `block`, and authority `none`. Re-running the resolver with unchanged inputs is idempotent.

Content addressing detects mutation and binds components; it does not authenticate who produced a receipt. A production service should verify issuer identity or signatures and store receipts in an access-controlled append-only system. The local lab therefore never promotes its content-addressed receipts above `lab_only`.

## Campaign evidence in the release decision

The [retained campaign/release controls](assets/campaign-release-conformance-v1.json) join campaign snapshots to actual deterministic mock-world trials and then call the existing release-receipt builder. They execute three synthetic studies plus one post-capture snapshot mutation. Prices, judge verdicts, calibration and prerequisite receipts are explicit teaching fixtures; none qualifies a real service.

| Control | Campaign assessment | Other evidence | Combined action |
| --- | --- | --- | --- |
| Four known judge estimates, within the registered allowance | `clear` | One independent customer, below the registered minimum of thirty | `hold` |
| One unknown judge estimate and two denied judge invocations | `hold` | Candidate judgments are unqualified, producing failed checks | `block` |
| Observed judge estimate exceeds its per-call reservation | `block` | Later judge admissions are denied | `block` |
| Snapshot changed after the simulated operator captured its hash | `block` | The original all-known execution packet remains unchanged | `block` |

The first row is the important positive control: clearing the budget component does not make the experiment statistically sufficient. The second keeps both explanations visible instead of relabeling an unqualified judgment as a demonstrated harmful action.

```bash
uv run --extra openai python -m unittest \
  tests.test_campaign_gate tests.test_campaign_release tests.test_campaign_conformance -v
uv run python -m cx_eval_lab.campaign_conformance \
  --output /tmp/primer-campaign-release-my-first-run.json
```

Use a fresh output path each time. The CI workflow now includes this command and retains the report beside the other conformance evidence. This chapter records local execution; it does not assert that a GitHub workflow or production deployment has run.

### Kata 41: matching hashes, wrong evidence

The snapshot says 1,440 micro-USD, four finalized invocations, and no unknown costs. All packet and snapshot hashes match the references supplied to the checker. Is that enough to clear the campaign?

**Task:** make each of these changes in a copied fixture, then recompute its internal hashes as if an upstream exporter had consistently produced the wrong evidence:

1. Change the judge's authoritative eligibility fact without changing the executed case.
2. Change the retained judge verdict to `fail` while keeping the semantic receipt's `passed=True`.
3. Change the qualification record's class count without changing its independently trusted calibration receipt.
4. Change a recorded admission's reason from `reserved` to `estimated_budget_exhausted`.

??? success "Solution: join the meaning-bearing fields, not just their digests"
    All four mutations block. `assess_campaign` first checks independently supplied packet/snapshot anchors and the operator's registered campaign policy. It then replays grades, recomputes snapshot totals from invocation rows, and joins the packet to those rows.

    It reconstructs the judge request from the retained case, customer input, output, tool events, final state and policy. The ledger request hash covers `{"criterion": CRITERION, "evidence": request}`; the stage's request hash covers the request alone. They are different contracts, not interchangeable IDs.

    Each invocation ID must derive from manifest, case, repetition and arm. Qualification must match the caller-trusted calibration hash; a declared `judge-config` must match the joined configuration. The semantic receipt's pass/abstention flags must match the actual retained verdict. A recorded admission must say it reserved capacity. Finally, the packet's inner judgment and campaign receipt must match the ledger's retained versions. The ledger hashes the inner judgment before the wrapper adds its campaign audit, so that field is reset to null for comparison.

    Tests also reject false totals, duplicate or omitted records, foreign invocations, changed costs and mismatched operator policy. Unknown/pending costs, denied admissions and missing campaign judgments hold. Overruns and established deadline/clock violations block. The supported scope is a dedicated campaign for one packet; extra unrelated rows cannot be silently discarded to make totals fit.

**Boundary:** the tests that recompute anchors deliberately simulate a coherent upstream bug. They do not prove resistance to an attacker who controls all authoritative inputs. Production anchor storage and issuer identity must be outside candidate write access. A snapshot hash also says nothing about whether later ledger changes exist. These snapshots lack an observation timestamp and event sequence sufficient to reconstruct every historical admission decision; this is a pinned consistency check, not freshness or historical enforcement attestation.

**Interview answer:** “A hash proves identity relative to an anchor, not that the record describes the right execution. I join request, case, judge configuration, verdict, receipt and cost, and I separately establish who controls the anchors.”

### Kata 42: a clean component cannot promote a weak experiment

The campaign is `clear`, software tests pass, and the agent has no failed checks. The packet contains two repetitions per arm for one customer. The statistical plan requires thirty independent customers.

**Task:** choose the combined action. Then omit campaign evidence from a manifest declaring `campaign-policy`. Finally supply a campaign assessment for a different packet.

??? success "Solution: restrict, never promote"
    The combined action is `hold`, with authority `none`: repetition does not supply thirty independent customers. Campaign `clear` leaves the existing statistical/prerequisite/test decision unchanged. Campaign `hold` restricts an otherwise passing action, but cannot downgrade an existing block. Campaign `block` forces a block. The precedence is `block > hold > existing action`.

    Missing assessment for a declared campaign, or for artifacts containing campaign audit evidence, holds rather than silently skipping the check. A separate regression starts with thirty hand-authored passing pairs under the teaching method and still obtains a hold when its declared campaign assessment is absent. That isolates the missing-evidence rule from statistical insufficiency; it is not new empirical model evidence.

    A supplied assessment must bind this exact experiment packet and its registered policy. A different packet or policy is rejected. The receipt records the campaign assessment and includes its content hash among decision components, so changing that component invalidates the old identity. Legacy examples with no campaign use explicitly report `not_checked`, not `clear`; their previous lab behavior remains available.

**Trust boundary:** `build_evidence_receipt` consumes a trusted evaluator-produced `CampaignAssessment`; it does not rerun the snapshot checker or authenticate an uploaded assessment. The evaluation service should call `assess_campaign` with operator-controlled anchors, then pass the returned object directly. Never deserialize a candidate-provided `{"status":"clear"}` into this trusted input. Current calibration eligibility, source/environment verification and authenticated admission to the registry remain separate checks; this component does not replace them.

**Interview answer:** “Independent gates combine by restriction. Budget clearance cannot buy statistical confidence, human-reviewed calibration or deployment authority. I retain component decisions and their evidence so a reviewer can distinguish a hold for uncertainty from a block for contradictory or failed checks.”

### Remaining production work

These controls now feed the lab's actual release-receipt implementation. They still cannot authorize a canary. The next integration must join authenticated and fresh evidence, current evaluator qualification, qualified statistics and explicit application exposure authority. Agent/tool costs, invoice reconciliation and provider cancellation also remain outside this judge-only control. Keep the original studies and grades when adding reassessment; do not overwrite historical evidence with a newer verdict.

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

## Kata 49: matching a hash is not validating an input

A dataset file contains `{ "limit": 2 }` followed by a newline. A native experiment registers the JSON value `{"limit":2}`. Both represent the same data, but their byte hashes differ. A second input contains `NaN`, and its producer supplies a matching hash. Does that make the input valid?

**Task:** verify file bytes and structured values without conflating them. Then change both a non-finite value and its registered hash: the validator must still reject it. Finally use an input label resembling a relative path and explain why it must not select a file by itself.

```python
import hashlib
import json
from cx_eval_lab.evidence import canonical_hash

raw = b'{ "limit": 2 }\n'
byte_hash = 'sha256:' + hashlib.sha256(raw).hexdigest()
value_hash = canonical_hash(json.loads(raw))
assert byte_hash != value_hash
```

??? success "Solution: separate representation, validity and trusted selection"
    `verify_sources` now accepts two explicit operator maps. `input_files` maps registered names to operator-selected paths and hashes their exact bytes. `input_values` maps names to finite JSON-compatible values and hashes their canonical representation. The maps must be disjoint; together they must cover exactly the registered non-source inputs. Neither may override a `source:` entry. Missing, extra or conflicting mappings fail.

    Source verification still checks the full Python/package-input inventory, the expected local Git revision, registered bytes and committed bytes. An added untracked Python module, changed source, symlink or mismatched evaluator identity cannot be hidden by updating the manifest alone. File paths come from the operator map, never from manifest labels. A label such as `../../outside/example` remains an opaque identifier if explicitly supplied as a value name; it is not a request to traverse directories.

    Validity must be checked independently of the digest. The existing canonical hash helper can represent non-standard non-finite values, so the new verifier explicitly performs strict JSON serialization with `allow_nan=False` before hashing. `test_nonfinite_values_reject_even_when_the_registered_hash_matches` caught a real implementation gap: earlier tests rejected an altered value because its hash differed, without proving that a coherently registered invalid value would fail.

    For a native provider run, the operator supplies full case values, the experiment design, semantic registration, campaign-policy hash preimage and judge configuration identity. `asdict(JudgeConfig)` is not the complete judge identity: the hash also binds the output schema, adapter, endpoint, retry setting and native format name. Use the adapter's fresh `configuration_identity` object; a copied digest string is not a substitute for those inputs.

**Extend:** preserve the original file hash when recording a parsed representation. Decide which identity supports exact reproduction and which supports semantic comparison. Do not silently canonicalize an original signed or byte-sensitive artifact and call it unchanged.

**Interview answer:** “A hash establishes equality to an anchor, not schema validity or trusted origin. I distinguish exact bytes from canonical values, validate independently, and let the operator—not an uploaded manifest—select filesystem paths and expected identities.”

## Kata 50: successful replay is not permission for a new release

An old packet replays all sixteen trials successfully. The same calibration has since been revoked. A source label still names the right evaluator, but the local code has changed. Another packet claims its judgment completed at 14:00 while a proposed release decision is dated 12:00.

**Task:** preserve the historical evidence while rejecting a new decision that depends on revoked qualification, changed source or future evidence. Do not accept a prebuilt `passed=True` source or calibration assessment as a replacement for recomputation.

```bash
uv run --extra openai python -m unittest tests.test_release_now tests.test_source_values -v
uv run --extra openai python -m cx_eval_lab.current_release_study \
  --output /tmp/primer-current-release-my-first-run.json
```

Run from a controlled checkout with committed package source and locked project inputs; use a fresh output filename. The study pins the current revision before execution, rather than relabeling an older packet after the fact. Its provider transport, prices, annotation labels, clock advances and prerequisite controls are synthetic. No network model call or application deployment is performed.

??? success "Solution: recompute a point-in-time decision from raw evidence"
    `assess_release_now` receives the packet plus separately selected operator inputs: packet anchor, historical calibration trust, current registry, aware clock, source root, expected revision/evaluator, file/value maps, test/prerequisite receipts and campaign policy/snapshot anchor. It does not accept cached source, replay or campaign assessments as authority.

    It first verifies the packet identity and committed source/input identities. It then replays the unchanged trials and checks current calibration. Campaign assessment and the existing release builder are recomputed from their inputs. Each resulting check is retained and hashed in a new composed decision. Missing or contradictory evidence can restrict the result; no component grants deployment authority.

    Revocation changes the new current-calibration result, not the old grade. Likewise, expiry can leave an old judgment historically interpretable while making its qualification unusable now. An out-of-window manifest cannot receive a new base receipt. If source verification fails, the function blocks before historical re-grading instead of claiming the changed implementation reproduced the original experiment.

    Chronology is another independent check. The decision cannot predate available native judgment start/completion times or campaign admission/completion times. Tests reproduce the previously accepted future-evidence case and now block it. This checks known timestamps only: missing legacy timestamps are not invented, and a consistent timestamp does not authenticate a clock.

    A current synthetic qualification check is still diagnostic. Even with explicit positive prerequisite fixtures, the four constructed cases share one customer and cannot satisfy the registered independent-cluster minimum. The base decision holds. Revocation or contradictory source inputs can then turn that hold into a block; neither path grants traffic authority. Using genuinely unqualified application prerequisites also blocks.

**Limits:** the caller owns the registry snapshot, clock, expected revision, input selection and prerequisite provenance. The function does not authenticate those inputs, prove loaded bytecode matches files, verify installed dependencies from a lockfile alone, or prevent a subsequent revocation/source change. Recompute at use time. A serialized result is not a reusable deployment permit, and atomic handoff to an authorized exposure controller remains separate work.

### Executed current-release controls

The [retained study packet](assets/current-release-study-v1.json) was generated against committed source revision `fc981a6959f8bb8d25fdf3838e8e12ac62313a67`. Unlike the orchestration unit tests, this run used the real source verifier against the repository's committed bytes. It retained one sixteen-trial paired packet, sixteen mocked SDK requests, and four separate calibration executions/requests. The seven assessments reuse that packet; they are not seven independent experiments.

| Operator condition | Observed new decision | Interpretation |
| --- | --- | --- |
| Current synthetic diagnostic, positive prerequisite fixtures | `hold` | Source and replay checks succeed, but one customer is insufficient independent evidence |
| Calibration revoked | `block` | Historical failed-trial count remains zero; present qualification is withdrawn |
| Calibration expired | `block` | Historical grades remain reproducible; calibration is not current |
| Synthetic qualification disallowed | `block` | Diagnostic labels cannot satisfy normal qualification |
| Wrong expected revision | `block` | Source identity check fails before replay |
| Changed operator case values | `block` | Registered experiment inputs no longer match |
| Unqualified application prerequisites | `block` | Current source and calibration cannot replace application qualification |

All seven records retain `authority_ceiling="none"` and `deployment_authorized=false`. The study CLI exits successfully only when the expected controls reproduce; it retains the failed report and exits nonzero otherwise. The CI workflow now invokes this command, but a workflow definition is not evidence of an observed cloud run. These controls demonstrate local composition, not authenticated provenance, real semantic accuracy or live exposure control.

**Counterexample: a hold for the wrong reason.** Independent review found that the first study checker would accept a current-control `hold` even if accounting had changed to `hold` and the statistical comparison had changed to `pass`. The outer action matched, but the teaching claim no longer did. Six failing mutation probes reproduced that weakness. The repaired checker requires clear accounting, all 64 available timestamps checked without future evidence, an inconclusive one-cluster comparison, and no deployment authority in any control. A [second committed-source execution](assets/current-release-study-v2.json), after fix `96c76da`, reproduced the same seven outcomes under the stronger checker. The original packet remains available; the fix does not relabel its source revision.

**Extend:** change a component decision while preserving the outer action. Which assertion should fail? A conformance suite must test the reason for an expected rejection, not reward an implementation that blocks everything.

**Interview answer:** “I keep historical reproducibility separate from present eligibility. I recompute source, current qualification and accounting against independent operator inputs, reject chronology contradictions, and let each check restrict the decision. A valid old result cannot authorize new exposure after its assumptions change.”
