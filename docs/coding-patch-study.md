# Coding patch evaluation: what did the tests actually prove?

A patch can pass every visible example and still mishandle missing outcomes. Another can return the right numbers while changing its caller's input. A third can try to replace the acceptance tests. These failures require different evidence; “the tests were green” is not a sufficient diagnosis.

This study evaluates five **hand-authored patch controls** for a small Python project. The runner creates temporary working copies, executes fixed test harnesses in real child processes and retains code, diffs, test evidence and file-integrity checks. It does not call a model, record an agent editing trajectory or measure coding-agent capability. Its purpose is to make a second domain's outcome evidence concrete alongside the refund lab.

## Register the coding task before writing the grader

Implement `summarize_trials(rows)` for a list of dictionaries containing an `outcome` of `pass`, `fail` or `unknown`.

- Preserve the number of registered rows and separate counts for all three outcomes.
- Define `known_pass_rate = pass / (pass + fail)`; return `None` when no outcome is known.
- Define `completion = (pass + fail) / registered`; return `None` for an empty input.
- Reject a missing or invalid outcome with `ValueError`.
- Do not mutate the caller's list or its dictionaries.

Counts are non-boolean integers. Rates are finite numbers (not booleans), or `None` where specified; numerically equal `1` and `1.0` are both valid rates. This semantic output contract differs from exact artifact-byte identity. A serialization change may change an artifact hash without making a function's mathematical answer wrong.

Unknown is a measurement state, not another spelling of failure. A rate conditional on known outcomes and a completeness fraction answer different questions. This task does not define a production release threshold or say that missing outcomes are acceptable.

The patch contract permits changing the candidate implementation, not the harness or test definitions. Two visible cases provide development feedback; eight separate acceptance cases check additional behavior. **All cases are public teaching fixtures.** Their separate file and execution do not make them sealed, uncontaminated or independently authored evaluation data.

## What runs and what is retained

Run from the repository root after installing the book's locked environment:

```bash
uv run python -m unittest tests.test_coding_patch_study -v
uv run python -m cx_eval_lab.coding_patch_study \
  --output artifacts/runs/coding-patches-my-first-run.json
```

Choose a new output filename on each run. The CLI refuses to overwrite evidence. The [retained local study](assets/coding-patch-study-v1.json) is available for inspection without running its stored text as code.

### Observed control results

The retained artifact was produced from the implementation committed in `feab2cd`. Each ordinary control runs two fresh child processes, one for each suite; the protected-test edit runs neither. One study therefore executes eight child processes and forty registered case checks. Each verifier call executes another eight child processes. No model calls are made.

| Authored control | Visible cases passed | Acceptance cases passed | Result and evidence |
| --- | ---: | ---: | --- |
| Original denominator | 2/2 | 6/8 | Rejected: `all-unknown` and `missing-evidence` expose the wrong known-outcome denominator |
| Visible overfit | 2/2 | 0/8 | Rejected: literal matches to development examples do not implement the contract |
| Correct | 2/2 | 8/8 | Accepted for this local task and published suite only |
| Input-mutating | 0/2 | 3/8 | Rejected: output agreement cannot compensate for caller-state changes; empty and two error cases pass |
| Protected-test edit | Not run | Not run | Integrity blocked: proposed `acceptance.json` replacement detected before execution |

This table is a control comparison, not an estimated coding-agent success rate. The eight acceptance fixtures include empty, unknown-only, mixed missing evidence, reordered rows, all failures, preserved metadata, invalid labels and missing labels. They do not exhaust every invalid container type or arbitrary Python object behavior.

In the report, `protected_before` is the registered baseline inventory and `protected_after` is the observed protected-file inventory. Each executed suite also retains its observed `files_before` and `files_after`. For the pre-execution test-edit block, the changed proposal is observed without running a suite; these snapshots are not a captured editing trajectory.

| Evidence | Question answered | Important limit |
| --- | --- | --- |
| Candidate sources and diffs | What implementation changed relative to the starting version? | An authored patch is not a captured agent edit history |
| Protected-file hashes | Did the visible/acceptance definitions or harness change? | Local integrity checking is not authenticated provenance |
| Fresh child-process suite results | Which registered checks actually completed? | This is not an OS security sandbox or realistic large-repository environment |
| Per-case outcomes and mutation checks | Was a wrong value, rejected input or changed caller state observed? | The assertions can themselves be incomplete or incorrect |
| Replay against built-in controls | Do retained claims agree with a new execution of the registered local code? | Repetition is not independent model sampling or human validation |

Only registered built-in candidate sources are executed. The verifier must check the registered inventory and rerun local built-ins; it must never execute arbitrary source strings taken from the artifact. The study is not an upload endpoint for untrusted patches.

Replay is a same-source reproducibility check, not independent confirmation of the test definitions or authenticated proof of a historical execution. The retained artifact binds the interpreter and source inventory; if your local version differs, inspect the old artifact as history and generate a separate fresh run. Do not rewrite its inventory to make verification appear successful.

The child uses isolated Python startup and no inherited environment credentials. Those settings reduce accidental interpreter/environment coupling; they do **not** restrict OS filesystem or network access. Do not substitute unknown model-generated code into this runner and assume it is contained. A real coding-agent service needs separately designed isolation, resource limits, credential boundaries and restricted test visibility.

## Kata 87: two passing examples, an incomplete repair

**Predict:** the original denominator bug and an implementation tailored to the visible cases both pass the two visible cases. What new evidence would distinguish a real repair from an implementation that merely reproduces those examples?

**Inspect:** compare `original-denominator`, `visible-overfit` and `correct` in the retained report. Locate the exact acceptance failures, not just the overall status. Then inspect the relevant input, expected outcome, candidate source and diff. State which line of the task contract each failing assertion represents.

For the executable replay below, use the fresh output from the preceding CLI command. This avoids treating a different machine's retained interpreter as your current runtime. The published artifact remains historical evidence with its own inventory.

```python
import json
from pathlib import Path
from cx_eval_lab.coding_patch_study import verify_study

report = json.loads(Path("artifacts/runs/coding-patches-my-first-run.json").read_text())
assert verify_study(report) is True  # Executes registered local built-ins again.
controls = {row["name"]: row for row in report["controls"]}
for name in ("original-denominator", "visible-overfit", "correct"):
    control = controls[name]
    visible, acceptance = control["suites"]
    print(name, visible["passed"], acceptance["passed"], control["status"])
assert controls["correct"]["status"] == "accepted"
assert report["deployment_authorized"] is False
```

??? success "Solution: qualify the claim made by each suite"
    The visible cases show agreement with two examples. They do not establish the full contract. A denominator bug may remain invisible until `unknown` appears; a literal-case implementation may reproduce familiar outputs while failing a different mix of rows. Locate those distinctions in the acceptance records rather than attributing every rejection to the same cause.

    A correct repair counts the categories independently, computes each rate from its registered denominator, handles empty/unknown-only inputs and preserves caller state. It rejects invalid labels rather than silently treating them as failures or dropping them. The accepted control demonstrates this behavior on the published tests, not on every possible Python input or future application integration.

    Do not call the five authored controls five independent model trials. They were chosen to expose specific failure modes. Comparing their pass counts teaches the grader's discrimination, not the probability that an agent will produce a correct patch.

**Interview defense:** “I separate task satisfaction from agreement with development examples. I retain the patch and exact failing tests, then check whether each assertion is justified by the contract. Acceptance data must have a separate change and access policy; a different filename alone does not provide that boundary.”

## Kata 88: right answer, wrong side effect—or changed examiner?

**Predict:** one candidate computes a plausible result but mutates its input. Another proposes a change to the acceptance test file. Should either be called accepted? Should the test-edit control receive a zero correctness score if execution never started?

Inspect the `input-mutating` control's per-case `input_unchanged` fields and the `protected-test-edit` control's protected-file evidence. The latter is blocked before candidate execution; an empty suite list is not a completed test suite with zero failures.

??? success "Solution: keep correctness, integrity and nonexecution separate"
    The task expressly prohibits changing caller data. A numerically correct output cannot compensate for that contract violation. The mutation check compares before/after input state rather than relying on the candidate's own claim that it is pure.

    The protected-test edit violates the allowed patch surface. Its `integrity_blocked` status explains why grading did not proceed. It is not evidence about how that implementation would perform against valid acceptance tests. Do not merge nonexecution into the denominator of ordinary completed correctness cases without declaring the reporting policy.

    Check protected files before and after execution, including missing files. Also require the exact registered result inventory: an exit zero with missing or fabricated case results must not be promoted to success. Passing the test runner's software regressions establishes those local checks for the authored controls, not resistance to an arbitrary malicious program on the same machine.

    Conformance must verify the intended failure evidence. If the original buggy control times out, a grader merely labeling it `rejected` would not be sufficient. The implemented runner records `incomplete`: its registered suites did not complete and demonstrate the expected defect. That is a failed study, not successful detection of the bug.

    Repair the implementation under the original test contract. If a test itself is defective, propose that as a separate reviewed change with a counterexample and versioned regrading—not as an unreviewed edit inside the candidate patch.

**Transfer to CX:** a refund agent cannot grade itself by editing the ledger or refund policy. A coding patch cannot grade itself by replacing the examiner. The authoritative objects differ, but the separation of candidate behavior and evaluation evidence is the same.

## Kata 89: when the acceptance test is wrong

**Authored counterexample:** the input is one `pass` and one `unknown`. A reviewer proposes an acceptance assertion requiring `known_pass_rate == 0.5`, claiming that it is “more conservative.” The implementation returns `known_pass_rate == 1.0` and `completion == 0.5`.

**Task:** identify whether the defect is in the implementation, the task specification or the proposed assertion. Explain what should happen to historical grades if that assertion had already been used. Do not change the function until you have resolved the definition.

??? success "Solution: conservatism cannot silently redefine the metric"
    There is one known result and it passes, so the registered known-outcome rate is `1/1 = 1.0`. One of two registered outcomes is known, so completion is `1/2 = 0.5`. The proposed assertion uses the wrong denominator for its named metric. A separate all-request known-pass fraction could be useful, but it is not the specified field.

    Preserve the incorrect assertion, its version and any grades it produced. Attach the explicit two-row counterexample and the relevant task clause. Independently review the correction, create a new test-suite version and rerun affected patches under both versions. Report verdict changes as measurement corrections, not model improvements. Do not discard only inconvenient failures or retrofit an unstated task requirement to match a gold patch.

    This counterexample is authored, not a discovered error in an external benchmark or a second human annotation campaign. It demonstrates how to reason about test validity alongside the executed patch controls.

    Apply the same discipline to types. `True` is not a valid count or rate here, even though Python compares it equal to `1`. Conversely, rejecting numeric `1` solely because the reference rate is `1.0` would impose an unnecessary representation requirement. Validate the declared semantic schema; reserve strict byte/type comparisons for the evidence identities and state-preservation checks that actually require them.

## How frontier methodology changes this design

Anthropic's agent-evaluation guidance combines executable outcome checks with additional review of code quality and agent/tool behavior. This lab supplies the first of those evidence types; it has no model-generated edit trajectory to score. A future agent study must retain the task interaction and tool history instead of inferring them from the final patch. [Anthropic agent-evaluation guidance](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)

Read the [dated benchmark corrections](benchmark-reproducibility.md#dated-coding-benchmark-corrections-tests-are-evidence-not-infallible-truth) before adopting a public suite as ground truth. The task specification, tests and environment are parts of the measuring instrument. A current benchmark name or a passing test command does not establish their validity.

## What would establish an actual coding-agent result?

| Decision | Engineering consequence |
| --- | --- |
| Adopt | Keep explicit task clauses, per-case observed outputs, caller-state checks and protected-file inventories in the evidence packet |
| Adapt | Move acceptance execution and artifact storage into a reviewed isolation and access-control design before admitting arbitrary agent-generated patches |
| Reject | Do not treat a zero exit, a changed test suite or success on these authored controls as a coding-agent capability or production-release claim |

Keep the same artifact discipline, then add a separately authorized execution environment and agent run:

1. Pin the repository revision, issue/task, permitted information access, dependency image and allowed patch surface.
2. Freeze development and acceptance roles; validate task/test alignment with reviewers who can identify both false passes and false failures.
3. Record the actual model, prompt, tool traces, patch attempts, test feedback, token usage, time and resource limits.
4. Grade in a clean evaluator-controlled environment, preserving regression tests and distinguishing infrastructure errors, unresolved work and rejected actions.
5. Compare registered repeated trials under matched budgets and disclose exclusions, interventions and uncertainty.

Do not automatically give a patch production authority because this local study accepted it. Integrating a change into an application additionally requires review, security and compatibility checks and the [release evidence contract](checklist.md). The [capstone](capstone.md) explains how to defend that boundary.
