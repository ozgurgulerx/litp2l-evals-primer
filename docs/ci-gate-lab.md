# CI gate lab: test the gate, not just the candidate

A release check can fail in two directions: it can reject a good candidate, or it can accept evidence that should have blocked the release. CI must exercise both. A workflow that only runs a passing reference example does not demonstrate that rejection works.

**Implemented:** an offline conformance command, a reusable GitHub Actions workflow, and a dependency that makes book publication wait for conformance. **Verified locally:** all three expected decision paths and their full replayable packets. **Not yet evidenced:** execution of this new workflow on GitHub, required branch-protection checks, or an application deployment governed by it. These are different completion claims.

## What runs, and what it authorizes

The workflow `.github/workflows/eval-conformance.yml` runs on pull requests, manual dispatch, or a reusable-workflow call. The existing Pages workflow calls it before publishing the **book**. The conformance job has read-only repository permissions, no model credentials, bounded runtime, SHA-pinned actions, and credential persistence disabled during checkout. It installs the locked dependencies, runs tests with an 80% production-code coverage threshold, exercises the decision controls, builds the documentation, and attempts to upload available evidence even after failure.

The security choices follow [GitHub's secure-use guidance](https://docs.github.com/en/actions/reference/security/secure-use). Workflow artifacts provide a retained inspection surface, subject to configured retention and access—not permanent or independently authenticated evidence. See [GitHub's artifact documentation](https://docs.github.com/en/actions/tutorials/store-and-share-data).

The new command is:

```bash
uv sync --frozen --group dev
uv run python -m cx_eval_lab.ci_conformance \
  --output-dir artifacts/runs/ci-check-01 \
  --code-revision YOUR_CHECKED_OUT_REVISION
```

Use the actual checkout revision; the command records the supplied identity rather than attesting to a clean worktree. GitHub supplies `github.sha` through an environment variable in the configured job. Use a fresh output directory on each run. No command in this lab changes application traffic or credentials.

## The retained local run

The [conformance summary](assets/ci-conformance-v1/conformance.json) records a local run of the command at implementation revision `1797a1c`. It is not a GitHub Actions run receipt. Each control executed two repetitions of five cases per arm and then independently replayed twenty retained grades.

| Control | Expected CLI exit | Expected action | Authority | Full packet |
| --- | ---: | --- | --- | --- |
| Reference, five-cluster teaching minimum | 0 | `lab_pass` | `lab_only` | [Reference](assets/ci-conformance-v1/reference.json) |
| Reference, thirty-cluster minimum | 3 | `hold` | `none` | [Insufficient evidence](assets/ci-conformance-v1/insufficient-evidence.json) |
| Policy-bypass candidate | 2 | `block` | `none` | [Negative control](assets/ci-conformance-v1/policy-bypass.json) |

The conformance command checks the expected process exit, action, authority ceiling, recorded revision, receipt digest, experiment reference, comparison consistency, and replayed results. It does not treat a parsed `allowed=true` or a successful process exit as sufficient evidence.

Every full packet and command result is retained alongside the summary. `deployment_authorized` is always false: success means that the software behaved as expected for these controls. It does not mean that the policy-bypass candidate, the underpowered reference study, or even the passing synthetic reference may be deployed.

## Kata 16: an expected rejection makes the test pass

**Know:** the candidate verdict and the test verdict are different variables.

**Predict:** the policy-bypass candidate exits with code 2 and has a `block` receipt. Should the conformance job fail? What if the same candidate unexpectedly exits zero with `lab_pass`?

```bash
uv run python -m unittest tests.test_ci_conformance -v
```

??? success "Solution: assert the expected failure"
    The first behavior is correct: a known-bad candidate was blocked. The conformance check passes because the observed rejection matches its registered expectation. An unexpected exit zero or changed receipt action makes conformance fail.

    `run_conformance` uses an explicit table of expected exits and actions. It preserves each command's output, then validates its packet through `verify_packet` and `replay_packet`. The underpowered control similarly requires `hold`; it cannot be silently treated as a successful release.

    Do not write `command || true` around a release gate. That loses the distinction between an expected negative-control result and an unexpected infrastructure, parsing, or policy failure. This implementation checks the exact expected exit and then inspects the evidence.

**Extend:** remove one trial artifact from a copied packet. Then change the receipt authority to `production`, leaving its candidate score untouched. The mutation test rejects both. Explain why a matching checksum still requires an external trust boundary if someone can rewrite both data and checksum.

**Interview answer:** “CI tests the decision mechanism with known-good, insufficient-evidence, and known-bad controls. Expected rejection is a test success, not release permission. Unexpected exits, missing artifacts, and authority escalation fail closed.”

## Kata 17: why a green job must not start a canary

**Situation:** every unit test passes, coverage exceeds 80%, and the conformance command exits zero. The final summary still says `deployment_authorized: false`.

**Task:** identify which evidence is still required before a state-changing application can enter a canary. Do not answer with another aggregate quality score.

??? success "Solution: keep three decisions separate"
    **Software conformance:** do the runner, graders, invariants, and gate behave correctly on their tests? This workflow exercises that question.

    **Candidate qualification:** does current, sufficiently representative evidence support this exact model/prompt/tool/policy configuration and action scope? The current lab-only statistical method, synthetic measurements, and incomplete live semantic qualification cannot establish this.

    **Deployment execution:** are the approved artifact, traffic cohort, permissions, monitoring, delayed-outcome observation, rollback target, and decision owner wired to a controlled rollout? This repository does not yet demonstrate an application deployment satisfying that contract.

    The Pages `needs: eval-conformance` dependency governs publication of the educational book. It is not a canary controller for the refund application. Never promote the meaning of the upstream green job beyond its evidence.

**Extend:** design a trusted release job that consumes an immutable candidate artifact and independently validates current deployment authority. Keep untrusted PR code away from deployment credentials. Specify expiry, component drift, missing-outcome handling, cancellation, and the exact rollback target before adding a traffic-changing step.

**Interview answer:** “I separate tests of the evaluator, qualification of the candidate, and authorization of the deployment. CI green establishes only what the job actually tested. The deployment job must validate scoped, current authority rather than infer it from a generic success status.”

## Kata 85: a timeout is not a candidate BLOCK

**Know:** a control can be expected to reject a candidate, while the experiment that should produce that rejection can fail to finish. Those are different observations. A timeout does not establish that the candidate violated the contract, and an earlier successful control does not finish the remaining experiment.

**Predict:** the reference and insufficient-evidence controls finish and validate. The policy-bypass control times out before returning a packet. What should the overall command return? Which evidence may be retained? May the third action be filled in as `block` because that is its expected answer?

The failed-run path writes `conformance-failure.json`, distinct from the successful `conformance.json`. It preserves only fully verified prior controls, identifies the failed control and phase, and leaves `deployment_authorized` false. A timeout command record uses a null return code rather than inventing zero or the expected candidate exit. Partial process output is diagnostic text, not a completed decision receipt.

These command logs belong to a synthetic, credential-free lab. Capturing stdout/stderr is not a privacy filter: do not apply the same unrestricted capture to customer conversations or secret-bearing production processes. Define redaction, access and retention before exporting such logs. A local exclusive-create write also does not establish durable storage across crashes or disk failure.

| Observed event | Candidate conclusion | Conformance conclusion | Operator action |
| --- | --- | --- | --- |
| Known-bad control exits 2 with replayable BLOCK evidence | This local control was blocked | Pass this control's expected rejection | Continue the remaining software checks |
| Expected HOLD exits 3 with valid underpowered evidence | Insufficient evidence for promotion | Pass this control's expected hold | Do not turn test success into release clearance |
| Child times out or cannot start | No completed candidate verdict from this attempt | Fail the conformance run | Preserve partial diagnostics; investigate execution |
| Exit is expected but the packet is missing, malformed or fails replay | No verified verdict from this attempt | Fail the conformance run | Investigate the evidence path; do not trust exit alone |

**Run:** this example executes the first two actual local conformance controls, then substitutes a deliberately slow Python child for the third command. That child is not an agent run. The timeout is real; it is not a declared failure label passed into a scorer. The temporary directory is deleted when the example exits; remove that context manager only if you intentionally choose a fresh persistent output location.

```python
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch
from cx_eval_lab.ci_conformance import run_conformance

native_run = subprocess.run

def timeout_third(command, **kwargs):
    if "policy-bypass" in command:
        return native_run(
            [sys.executable, "-c",
             "import time; print('started timeout control', flush=True); time.sleep(5)"],
            capture_output=True, text=True, timeout=0.5, check=False,
        )
    return native_run(command, **kwargs)

with tempfile.TemporaryDirectory() as scratch:
    output = Path(scratch) / "conformance"
    with patch("cx_eval_lab.ci_conformance.subprocess.run", side_effect=timeout_third):
        try:
            run_conformance(output, "authored-timeout-exercise")
        except subprocess.TimeoutExpired:
            pass  # Expected injected fault; the assertions below decide success.
        else:
            raise AssertionError("The injected timeout was not raised")
    failure = json.loads((output / "conformance-failure.json").read_text())
    command_record = json.loads((output / "policy-bypass-command.json").read_text())
    assert failure["failed_control"] == "policy-bypass"
    assert failure["status"] == "timeout"
    assert [row["action"] for row in failure["checks"]] == ["lab_pass", "hold"]
    assert failure["deployment_authorized"] is False
    assert command_record["returncode"] is None
    assert not (output / "conformance.json").exists()
    print("2 verified controls; third timed out; no completed run or release authority")
```

The revision string here is an explicit teaching label, not source attestation. This snippet also deliberately catches the injected timeout so it can inspect diagnostics. Do not copy that catch into a deployment workflow and ignore the assertions or the failed conformance result.

??? success "Solution: keep completed evidence without inventing completion"
    The failed run retains two verified checks, not three. The third control's expected action remains part of the test design; it is not an observed candidate decision. No successful final summary is emitted. The normal CLI fails rather than returning a successful conformance result.

    Read the exit code in the context of the command that emitted it. The inner `experiment` command uses 2 for its BLOCK result; the outer `ci_conformance` command's argument/error handler also exits 2 on a conformance failure. The same integer cannot identify both meanings without the command, phase and verified evidence. Do not build a workflow that interprets every exit 2 as a successfully blocked candidate.

    A matching expected process exit is only the first condition. Packet parsing, artifact replay, revision checks, comparison consistency and authority checks must also succeed before the control enters the completed-check list. A malformed or missing packet therefore cannot borrow the previous control's success.

    For this controlled offline lab, investigate and rerun in a new output directory, preserving the failed run for comparison. For state-changing application experiments, first reconcile side effects and pending usage: rerunning a process is not evidence that replaying its business actions is safe. The runner intentionally does not retry this failure automatically.

**Boundary:** Python's `subprocess.run(timeout=...)` kills and waits for its child before raising `TimeoutExpired`; process creation itself may delay that exception. Captured timeout output can be bytes even with `text=True`. These are reasons to preserve a distinct timeout record and decode diagnostic bytes explicitly. They are not proof of descendant-process containment or external side-effect reversal. [Python subprocess documentation](https://docs.python.org/3/library/subprocess.html#subprocess.run)

## Kata 86: the upload step is not a durable experiment ledger

**Situation:** the conformance job has a 15-minute timeout and an artifact-upload step with `if: always()`. An engineer concludes that every interrupted experiment must therefore have a complete evidence packet in GitHub.

**Task:** distinguish a caught child timeout, an unexpected exit, a terminated Python parent, a cancelled job, and a lost runner. State what you would inspect before rerunning or allowing downstream publication.

??? success "Solution: separate local persistence, upload eligibility and confirmed storage"
    A caught child timeout can produce the local failed-run diagnostics while the Python parent and filesystem remain available. An unexpected exit can retain its command output, but only validated packets enter the completed-check list. The failure file is diagnostic evidence, not a model-performance observation or an authenticated release receipt.

    Terminating the parent can prevent any failure handler from running. Disk-full or permission failures can prevent local writes. A lost runner can make local files inaccessible. None of these missing records is evidence of a pass, a candidate block, or a successful rollback.

    Exclusive-create writes prevent replacement of an existing file but are not atomic or crash-durable. An interrupted write can leave truncated JSON, including the final summary. Parse and validate its expected contents and referenced artifacts; filename existence is not completion. If writing the diagnostic itself fails, the original failure still propagates, and no durable failed-run record is guaranteed.

    `always()` changes when the upload step is eligible to run; it does not reconstruct files that were never written. Inspect the workflow run and attempt, step conclusions, uploaded artifact identity, file inventory and expected control coverage. If no confirmed complete run exists, leave conformance incomplete and do not authorize the dependent publication or any application exposure.

    Rerun software conformance under a new attempt/output identity after diagnosis. Do not merge an old partial run and a new result into one complete experiment unless the manifest, registered trial identities and retry policy explicitly permit that composition. Preserve both attempts. A durable distributed evaluation service additionally needs external task accounting and storage acknowledgements; this local JSON failure path does not implement them.

GitHub documents `always()` as true even on cancellation and separately defines job timeout cancellation. These are workflow semantics, not evidence that this repository's upload succeeded. Verify the actual run before making that claim. [Status-check functions](https://docs.github.com/en/actions/reference/workflows-and-actions/expressions#status-check-functions), [workflow timeouts](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idtimeout-minutes).

**Interview answer:** “A failed experiment is not a failed candidate. I retain partial evidence with explicit completion state, validate every claimed completed control, and require confirmed artifact availability. A green upstream test or an `always()` upload condition cannot manufacture deployment authority.”

## Full local verification commands

```bash
uv sync --frozen --group dev --extra openai --extra telemetry
uv run --extra openai --extra telemetry coverage run --branch --source=cx_eval_lab -m unittest discover -s tests
uv run --extra openai --extra telemetry coverage report --fail-under=80
uv run mkdocs build --strict
```

The test suite includes actual child-process recovery and fresh-process CLI checks. Coverage is scoped to application code, not inflated by counting test files as covered production code. Some subprocess execution is not included in the parent coverage counters; executed behavior and instrumented coverage remain distinct evidence.

The book also treats missing Markdown link anchors as warnings, so `--strict` fails when a worked-solution heading disappears. `tests/test_link_validation.py` builds isolated tiny sites using the repository's actual validation settings: a valid exercise link succeeds, while a missing page or anchor fails. This checks reader navigation, not lesson correctness, remote source availability or application release authority. Raw HTML links and rendered assets still need separate inspection; do not describe the Markdown validation setting as a complete web crawler.

The statistical artifact regression compares numerical results to twelve decimal places to allow platform-level floating-point rounding, while preserving exact structure, counts, and decisions. This is not permission to tolerate a changed release verdict.

## What remains before calling this an operated release pipeline

- Observe successful and deliberately failing runs of this workflow on GitHub after publication of the changes.
- Configure and verify required status checks through repository governance; the workflow file alone does not enforce branch protection.
- Supply actual model, dataset, calibration, and deployment evidence with appropriate statistical qualification.
- Transfer the [implemented local exposure controller](exposure-control-lab.md) to an authorized application environment and exercise shadow, canary, expansion, restriction and rollback there. The existing simulation is not a demonstrated production rollout.
- Verify artifact provenance, retention, permissions, secrets isolation, and the behavior of cancelled or partially completed jobs in the operating environment.

The [release chapter](checklist.md) retains the full decision contract, and the [delivery map](primer-delivery-map.md) tracks these remaining requirements. Do not describe configured-but-unobserved cloud behavior as already deployed practice.
