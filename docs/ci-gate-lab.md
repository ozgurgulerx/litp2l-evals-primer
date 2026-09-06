# CI gate lab: test the gate, not just the candidate

A release check can fail in two directions: it can reject a good candidate, or it can accept evidence that should have blocked the release. CI must exercise both. A workflow that only runs a passing reference example does not demonstrate that rejection works.

**Implemented:** an offline conformance command, a reusable GitHub Actions workflow, and a dependency that makes book publication wait for conformance. **Verified locally:** all three expected decision paths and their full replayable packets. **Not yet evidenced:** execution of this new workflow on GitHub, required branch-protection checks, or an application deployment governed by it. These are different completion claims.

## What runs, and what it authorizes

The workflow `.github/workflows/eval-conformance.yml` runs on pull requests, manual dispatch, or a reusable-workflow call. The existing Pages workflow calls it before publishing the **book**. The conformance job has read-only repository permissions, no model credentials, bounded runtime, SHA-pinned actions, and credential persistence disabled during checkout. It installs the locked dependencies, runs tests with an 80% production-code coverage threshold, exercises the decision controls, builds the documentation, and uploads available evidence even after failure.

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

## Run and inspect the same checks locally

```bash
uv run coverage run --branch --source=cx_eval_lab -m unittest discover -s tests
uv run coverage report --fail-under=80
uv run mkdocs build --strict
```

The test suite includes actual child-process recovery and fresh-process CLI checks. Coverage is scoped to application code, not inflated by counting test files as covered production code. Some subprocess execution is not included in the parent coverage counters; executed behavior and instrumented coverage remain distinct evidence.

The statistical artifact regression compares numerical results to twelve decimal places to allow platform-level floating-point rounding, while preserving exact structure, counts, and decisions. This is not permission to tolerate a changed release verdict.

## What remains before calling this an operated release pipeline

- Observe successful and deliberately failing runs of this workflow on GitHub after publication of the changes.
- Configure and verify required status checks through repository governance; the workflow file alone does not enforce branch protection.
- Supply actual model, dataset, calibration, and deployment evidence with appropriate statistical qualification.
- Implement and exercise the application exposure controller, including shadow, canary, expansion, restriction, and rollback.
- Verify artifact provenance, retention, permissions, secrets isolation, and the behavior of cancelled or partially completed jobs in the operating environment.

The [release chapter](checklist.md) retains the full decision contract, and the [delivery map](primer-delivery-map.md) tracks these remaining requirements. Do not describe configured-but-unobserved cloud behavior as already deployed practice.
