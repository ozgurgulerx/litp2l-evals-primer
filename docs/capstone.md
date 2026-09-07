# Capstone: defend the release, not the dashboard

The retained release study passes conformance and still says **hold**. A telemetry arm reports **100% observed success** while its complete business record contains two passes and two failures. A simulated controller rolls back only after four wrong-order commits. Your task is to explain what these results justify without combining three different systems into an imaginary qualified deployment.

This is an authored classroom exercise using existing local artifacts, not a real customer release or an interview question reported by an employer. It connects the [seven learning checkpoints](index.md#a-learning-route-with-evidence-checkpoints). Completing it is practice, not certification of interview readiness or deployment competence.

## Supplied evidence and requested decision

**Timebox:** 45 minutes for inspection and a memo; 15 minutes for an oral defense. You may use the book. No API key, network call or new model run is required to inspect these retained files.

**Stakeholder request:** “The local conformance run is green, telemetry says 100%, and the rollout controller can expand. Approve 25% production exposure for the refund agent.” No production candidate identity, independent human qualification, or signed release authority is supplied.

| Evidence | What actually ran | What this artifact cannot establish |
| --- | --- | --- |
| [Current release packet v2](assets/current-release-study-v2.json) | Native multi-order agent/semantic integration through SDK mock transport and current-state assessment controls | Actual model quality, independent human calibration, or representative production performance |
| [Telemetry delivery study](assets/telemetry-study-v1.json) | Actual local OTLP HTTP delivery around legacy synthetic business controls | Durable authenticated production telemetry or performance of the native release candidate |
| [Exposure control study](assets/exposure-control-v1.json) | A separate simulated routing/controller sequence with disposable mock ledgers | Permission to route real traffic, atomic interruption of an in-flight action, or reversal of a completed refund |

Use the [completed evidence index](assets/capstone-evidence-index-v1.json) after drafting your own. It records exact file-byte hashes and JSON pointers, including control names alongside positional array entries. A hash freezes the referenced bytes and ordering; it does not authenticate who produced them or whether their judgments are valid.

The native study's historical revision is retained inside its artifact. Do not represent a successful inspection today as a fresh execution against today's source, models, registry or policy. For a separate fresh source-checked run, follow the [CX walkthrough](cx-evidence-walkthrough.md); keep its output separate from this historical exercise.

## Submission contract

Submit a decision memo of at most 700 words plus a JSON evidence index. The memo must include:

1. **Requested action and verdict:** distinguish holding a requested production expansion from continuing a bounded local diagnostic.
2. **Evidence table:** claim, artifact, exact field, denominator, scope and limitation. At least one claim from each artifact must be independently locatable.
3. **Compatibility check:** identify missing joins for candidate/model, prompt/harness, dataset/population, policy, time and authority. Explain why shared terminology does not create these joins.
4. **Three failure explanations:** green conformance with insufficient evidence; selective trace loss; rollback after completed side effects.
5. **Reopening conditions:** owner roles, next evidence artifacts, and what decision each could change. Do not invent completed approvals or name people who have not accepted responsibility.

The index is a review aid, not an executable release policy. Your verdict requires the argument in the memo; matching the reference values alone is insufficient.

## Inspect the reference index

Run this from the repository root in a normal Python interpreter. It checks the supplied index against local bytes and values; it does not rerun the agents, independently regrade messages, verify artifact provenance, or grant authority. The snippet is for these trusted repository files, not an upload validator for untrusted JSON.

```python
import hashlib
import json
from pathlib import Path

root = Path("docs/assets")
index = json.loads((root / "capstone-evidence-index-v1.json").read_text())

def pointer_value(document, pointer):
    value = document
    for segment in pointer.split("/")[1:]:
        key = segment.replace("~1", "/").replace("~0", "~")
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value

checked = 0
for item in index["artifacts"]:
    raw = (root / item["file"]).read_bytes()
    if hashlib.sha256(raw).hexdigest() != item["sha256"]:
        raise ValueError(f"Changed artifact: {item['file']}")
    document = json.loads(raw)
    for pointer, expected in item["expected"].items():
        actual = pointer_value(document, pointer)
        if type(actual) is not type(expected) or actual != expected:
            raise ValueError(f"Mismatch: {item['file']} {pointer}")
        checked += 1
print(f"Inspected {len(index['artifacts'])} retained files and {checked} fields; no release authorized.")
```

Expected: `Inspected 3 retained files and 29 fields; no release authorized.` A mismatch means stop and investigate the version difference. Do not silently replace the expected hash to make the example pass. Preserve the previous index and explain any intentional successor.

## Worked decision memo

??? success "Solution: HOLD the requested production expansion"
    **Decision:** do not approve 25% production exposure on this packet. Continue only already-authorized local diagnostic work. No evidence here establishes a production authorization.

    | Claim and artifact | Exact evidence | Denominator, scope and limitation |
    | --- | --- | --- |
    | Native comparison is inconclusive (`current-release-study-v2.json`) | `/assessments/0/assessment/checks/base_receipt/comparison/status` = `inconclusive` | Eight pairs, one synthetic customer cluster; not production reliability |
    | Telemetry is incomplete (`telemetry-study-v1.json`) | `/arms/1/summary/unknown_requests` = `2` | Two of four registered requests lack roots; observed success is conditional on delivery |
    | Side effects precede rollback (`exposure-control-v1.json`) | `/windows/5/artifacts/{1,2,18,35}/candidate/wrong_order_commits` = `1` each | Four served candidate requests in this simulated window; not four real customer refunds |

    The brace notation abbreviates four exact pointers listed separately in the index; it is not a JSON-pointer wildcard.

    **Native comparison:** `current-release-study-v2.json` records `conformance_passed=true`, while `assessments[0]`, named `current-diagnostic`, has action `hold` and authority ceiling `none`. Its base comparison contains eight pairs but one independent customer cluster and status `inconclusive`. Repeated successes for that synthetic customer do not establish reliability across customers. Conformance means the expected control behavior occurred, including expected holds and blocks; it is not a promotion verdict. Meeting a larger cluster-count minimum alone would also not qualify the statistical method.

    **Observability:** the telemetry `capacity` arm has two observed roots, both passing, hence observed success of 2/2. The independent complete business record contains two passes across four registered requests. Two requests have missing roots and one feedback item remains pending. The 100% dashboard is therefore a selected denominator, not evidence of four successful requests. Without that complete business record, missing outcomes would be unknown rather than automatically failed. This control diagnoses an accounting failure mode, not its prevalence in production.

    **Containment:** exposure `window-6` serves four candidate requests and ends `rolled_back`, at zero percent, for `hard_violation`. The underlying execution artifacts contain four wrong-order commits before batch assessment. Reducing future exposure does not undo these commits. The simulation neither shows immediate prevention of the first violation nor grants permission for real refunds.

    **Compatibility:** these are a native SDK mock-transport study, legacy telemetry controls, and a separate simulated exposure candidate. They do not share a verified production candidate/model, prompt/harness, population, policy, validity time or authorization. I cannot multiply their successes or concatenate their receipts into an end-to-end production safety claim.

    **Reopen:** the evaluation owner must supply representative paired evidence and independently qualified semantic judgments for the exact proposed candidate; the instrumentation owner must reconcile durable authenticated request/trace/feedback records; the application owner must demonstrate prevention, interruption and recovery at the actual write boundary; the release owner must review these compatible, current artifacts and approve a bounded exposure policy. These are required roles, not approvals already obtained. None of these obligations can be waived by relabeling the current synthetic evidence.

## Pressure variants: revise only what changed

Answer each before opening its solution. Keep the original memo and record the changed claim, affected evidence and new decision.

??? question "Variant A: the semantic qualification has been revoked"
    The native artifact already contains a separate control named `revoked` at `assessments[1]`. What changes? Should historical passing judgments be deleted?

??? success "Solution A"
    The revoked assessment is `block`, not the diagnostic `hold`. Preserve historical grades and their original qualification context; they explain what was assessed then. Current authorization must reject the revoked qualification. Do not rewrite the earlier result or describe every other study as invalid merely because this control changed. A new authorized calibration/registry assessment is required before reconsideration.

??? question "Variant B: only the observed telemetry dashboard is available"
    Remove access to the complete business-outcome record from your reasoning, not from the stored artifact. You still know four requests were registered and only two passing roots arrived. What can you claim?

??? success "Solution B"
    Two outcomes are known passing; two are unknown. Full-population success could range from 2/4 to 4/4 on these four requests. Neither 100% overall success nor two proven failures follows from the dashboard. Hold any decision requiring complete outcomes, investigate missing delivery, and retain pending feedback instead of joining it to a convenient different trace. The teaching artifact's independent business record resolves this uncertainty only for the local control.

??? question "Variant C: the controller successfully stopped future candidate routing"
    A stakeholder says the successful rollback cancels the four severe outcomes. Which evidence would you require before agreeing?

??? success "Solution C"
    Refuse the premise: routing rollback cannot erase a completed side effect. Require an authoritative ledger reconciliation, separately authorized compensation where possible, customer-impact assessment and evidence that the repaired precommit boundary prevents recurrence. Stopping future routing and recovering prior effects are different controls. No compensation run or customer recovery is demonstrated by this study.

## Advanced defense: budget, replay and consequential risk

Keep the original three-artifact submission and its reference index unchanged. This separate **30-minute extension** uses the [budgeted campaign packet](assets/budgeted-exposure-v1.json), [CI replay exercise](exposure-control-lab.md#kata-97-the-packet-exists-but-did-ci-verify-it) and [risk-dependence counterexample](frontier-risk-decisions.md#kata-98-identical-component-scores-one-hundred-times-the-failures). Do not join the newer campaign to the original native candidate merely because both concern refunds.

Submit an addendum of at most 400 words and a separate evidence index. For the budget artifact, record its file-byte hash and inspect at least these fields. These are lookup targets, not an independent regrading result:

| Exact JSON pointer | Retained value | Interpretation to defend |
| --- | --- | --- |
| `/windows/1/served_candidate` | `4` | Selected candidate requests in the canary window |
| `/windows/1/summary/candidate_completed` | `2` | Delivered completions, not all selected requests |
| `/windows/1/summary/candidate_budget_denials` | `2` | Unfinished work caused by the capped policy |
| `/windows/2/summary/candidate_completed` | `0` | Restriction did not restore allowance |
| `/windows/2/summary/candidate_budget_denials` | `4` | Four further denied attempts in the restricted window |
| `/final_budget/charged_actions` | `2` | New served-candidate effects charged across windows |
| `/final_budget/charged_cents/EUR` | `9000` | €90 charged, not a global multi-currency amount |
| `/deployment_authorized` | `false` | No production permission supplied by this local study |

Use the pointer-reading pattern above on a new index of your own. Inspect the underlying tool events, order ledgers and budget snapshots before defending a summary. [Kata 96](exposure-control-lab.md#kata-96-a-hash-is-not-a-replay) explains complete fixed-program replay and its exact-source/interpreter requirement. A historical pointer lookup does not establish that replay passed today.

??? question "Variant D: the budget worked, so exclude denied requests"
    A stakeholder reports 100% completion among the two allowed refunds, discards the two denials, and proposes resetting the budget after restriction. What should the addendum report?

??? success "Solution D: retain unfinished work and campaign identity"
    Canary completion is 2/4 selected requests, not 2/2 after exclusions. The two denials demonstrate enforcement and unfinished service simultaneously. The next restricted window completes 0/4 because the same campaign allowance remains exhausted. Distinguish a policy-constrained delivered outcome from an intrinsic model-quality estimate; neither deleting denials nor renewing allowance silently repairs the service.

    The two charged effects total EUR 9,000 cents across served candidate execution. Isolated baseline and shadow effects are different accounting scopes; their successes cannot increase delivered candidate completion. A new budget or campaign would require an explicit policy decision and preserved linkage to prior effects, not a reset that erases consumption. This packet demonstrates in-memory mock enforcement, not durable protection after process loss or authorization for a real campaign renewal.

??? question "Variant E: a hash and an uploaded artifact prove the run passed"
    The packet hash matches. A colleague supplies the workflow YAML and says an upload step proves the verifier ran successfully. Can you approve the requested expansion?

??? success "Solution E: separate configuration, execution and authority"
    No. Matching bytes do not authenticate execution or validate a judgment. Inspect the actual run revision, generation/replay step results, job conclusion and retained artifact. An always-run upload can retain evidence from a failed job. Workflow configuration alone establishes neither an observed cloud run nor a required branch-protection check.

    Fresh fixed-program replay uses matching source and interpreter identities and compares complete normalized evidence; timing is explicitly excluded from semantic replay. That provides bounded consistency evidence, not signed provenance, calibrated model quality or production authority. A historical artifact from another interpreter may correctly fail exact replay. Keep it intact and produce a separate fresh packet; do not rewrite its identity to manufacture agreement.

??? question "Variant F: two 1% rates justify a tiny residual risk"
    A proposal multiplies a 1% attempt rate by a 1% safeguard-failure marginal and claims one consequential failure per 10,000 opportunities. The illustrative policy allows at most ten. What is missing?

??? success "Solution F: defend the conditional pathway, not the product"
    Under Kata 98's compatible synthetic population assumptions, the same marginals permit zero to one hundred joint failures. The aligned arrangement violates the ten-case policy. The correct factorization needs safeguard failure conditional on attempts; substituting the marginal requires justified independence. Different source populations would create an additional transport problem before that calculation even begins.

    Hold expansion on this evidence. Specify the relevant joint attempt/control/effect observations and consequential pathways, or separately justified enforceable limits. Do not call logical bounds confidence intervals or extrapolate the authored populations into an empirical frontier-model risk estimate. Capability, safeguard effectiveness, exposure and consequences remain distinct claims.

### Advanced assessment checks

??? question "Variant G: every durable component passed, so the campaign can resume"
    The refund ledger, completion journal, window registry and controller receipt tests all pass. One worker died after a wrong-order refund without persisting its response. Another controller committed its decision but lost its acknowledgement. Explain which operations may be repeated, what evidence remains missing and whether those component results establish a recoverable application.

??? success "Solution G: recover each record without inventing the missing joins"
    Inspect the [joined window evidence](exposure-control-lab.md#kata-104-do-not-lose-the-request-when-completion-is-missing) without executing an agent. Keep all registered members and the served-candidate denominator. The observed wrong-order effect remains a violation while the missing response label stays unknown. An absent journal record is not proof that no other execution path acted. Baseline/shadow records are outside this diagnostic's retained-evidence scope, so it cannot establish a paired release comparison.

    Reopen a completed request's exact bound evidence without issuing another refund. Do not restart an incomplete agent as though its prior attempt never happened. Request resumption needs an explicit continuation policy and ownership fencing at the consequential-action boundary; a receipt read or expired timeout does not stop an old worker. Repeating the exposure driver may rerun baseline controls while reusing completed candidate evidence, which is neither an independent trial nor a complete window resume.

    For the controller acknowledgement, replay the same decision identity and exact inputs through [Kata 105's receipt store](exposure-control-lab.md#kata-105-the-controller-committed-but-its-acknowledgement-was-lost). It returns the accepted historical decision without advancing state again. A changed request conflicts, and a new decision must match the full current predecessor, including pending-cohort state. This local receipt transaction does not atomically join the request, effect and evidence databases or authenticate the supplied observations.

    Therefore withhold the claim of end-to-end recoverability. The remaining demonstration must connect registered membership, qualified observations, fenced attempt recovery and controller acceptance in one versioned process study, including crash boundaries and unfinished outcomes. Component test success is necessary evidence for that build, not a substitute for the integrated experiment. Neither the original wrong refund nor an already delivered message is undone by replaying a receipt.

Every row must be satisfied independently. Passing the original rubric does not waive these checks, and passing either rubric does not authorize deployment.

| Must demonstrate | Passing addendum | Revision trigger |
| --- | --- | --- |
| Budget and service outcomes | Both enforcement success and 2/4 delivered completion, with 0/4 after restriction | Denials excluded, allowance silently reset, or shadow success counted as served work |
| Inspectable evidence | Separate artifact identity, exact pointers and underlying events/ledgers | New summaries merged into the old candidate's release receipt |
| Replay versus CI evidence | Exact-environment replay limits plus actual-run evidence requirements | Hash, workflow configuration or upload existence treated as proof of a passing deployment gate |
| Consequential-risk inference | Conditional rate, dependence bounds and explicit causal/population assumptions | Unrelated marginals multiplied into a risk certificate |
| Recovery boundaries | Distinguish effect inspection, completed-evidence retrieval, incomplete-attempt continuation and controller acknowledgement replay | Components composed into an untested end-to-end guarantee, or a receipt read treated as worker fencing |
| Bounded next action | Required evidence and responsible roles, with current authorization withheld | A higher task score used to waive unresolved control or evidence obligations |

## Review rubric and interview defense

Use a noncompensatory rubric: polished prose cannot offset an unsupported deployment claim. Each row must pass; a failed row means revise the submission, not that the learner has failed an employment assessment.

| Must demonstrate | Pass evidence | Revision trigger |
| --- | --- | --- |
| Traceable claims | Correct file, control name, pointer/value and denominator | A headline score with no inspectable supporting field |
| Measurement limits | One cluster distinguished from eight pairs; synthetic qualification identified | More repetitions presented as new customers or independent human calibration |
| Missingness reasoning | 2/2 observed separated from 2/4 complete; unknowns handled explicitly | Missing traces counted as passes or necessarily failures |
| Evidence compatibility | Missing candidate/population/policy/time/authority joins named | Three unrelated local greens composed into production authority |
| Control consequences | Four completed commits distinguished from future routing restriction | Rollback described as undoing money movement |
| Change control | Historical and current validity separated; targeted updates for all three variants | Revocation hidden, history erased, or unrelated results discarded |
| Actionable next work | Named owner roles and concrete evidence needed to reopen | “Gather more data” without sampling, qualification or operational scope |

For an oral defense, answer: **Which one field most directly contradicts the requested permission?** The native assessment's authority ceiling is `none`; then explain why that result is appropriate rather than treating the field as unquestionable authority. **What if all three artifact hashes match?** You have byte consistency, not authenticated execution or valid inference. **What evidence would change your mind?** A compatible current packet satisfying the registered measurement and operational obligations, reviewed by the actual release authority—not merely a higher score.

Continue with [Release Gates](checklist.md) for the full release-packet contract, [Statistical Method Study](statistical-method-study.md) for method qualification, and [Frontier Risk Decisions](frontier-risk-decisions.md) to extend the argument from application correctness to exposure, safeguards and unresolved consequential risk.
