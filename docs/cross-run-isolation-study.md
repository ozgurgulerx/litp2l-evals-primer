# Cross-run isolation: what may one evaluation learn from another?

Run A caches a synthetic answer. Run B asks the same question and receives A's private marker. Both runs may appear successful if the grader checks only response shape. The experiment is nevertheless invalid under a contract that requires independent private state.

This study tests a local cache boundary with actual reads and writes. It distinguishes forbidden private-state reuse from useful same-run caching and explicitly permitted shared policy access. The workers are cooperative application code, not hostile programs contained by an operating-system sandbox.

## Register the sharing contract

“Isolated” is incomplete without naming what may be shared.

| Resource | Run A | Run B | Required boundary |
| --- | --- | --- | --- |
| A's private answer cache | Read and write | No access | Run identity participates in lookup authority |
| B's private answer cache | No access | Read and write | Same query text does not confer cross-run access |
| Shared policy | Read only | Read only | Both runs see the approved policy; neither can replace it |
| Evaluation record | Captured by the harness | Captured by the harness | Candidate output cannot redefine the allowed-sharing contract |

The last row is a required trust boundary, not proof of tamper-resistant logging in this Python exercise. A hostile program with the same filesystem or interpreter privileges could bypass the application API. Hashing the resulting record does not remove that limitation.

METR's independent incident investigation describes unintended communication between agents that were meant to be isolated, alongside integrity failures and important limitations in the available evidence and analysis. That motivates testing indirect shared surfaces. Our cache experiment does not reproduce the incident, evaluate the implicated models, or estimate its prevalence. [METR investigation](https://metr.org/blog/2026-08-26-openai-hugging-face-incident-investigation/) (checked 7 September 2026).

## Cross the key strategy with worker lifetime

The buggy strategy uses the query as the private-cache key. The scoped strategy includes an operator-issued run context. Both use a distinct namespace for shared policy data.

Test each strategy under three execution contexts:

- **Fresh workers:** each run gets a new worker object, but the cache service persists. A fresh worker is not a fresh environment.
- **Reused worker:** the operator rebinds one worker to another run. Check that an earlier run's identity does not remain attached to the lookup.
- **Concurrent workers:** two threads are alive together. Explicit barriers order A's write before B's read so the cross-run probe is reproducible.

The concurrent arm is a controlled overlapping schedule, not thread-interleaving fuzzing or a distributed-systems reliability claim. The sequential arms make the same A-before-B relationship visible without concurrency. If query-only keys leak in all three, restarting the worker alone does not repair the cache contract.

## Run and inspect the experiment

From the repository root, with the locked environment installed:

```bash
uv sync --locked
uv run python -m unittest tests.test_isolation_study tests.test_isolation_artifact -v
uv run python -m cx_eval_lab.isolation_study \
  --output /tmp/primer-isolation-my-first-run.json
```

Choose a new output filename for each run; the command refuses to overwrite evidence. It creates temporary SQLite stores and executes all six comparisons without model calls or external data. The registration fixes the sharing contract, A/B/A phases, worker assignments and schedules before execution. Concurrent thread identifiers will differ between executions; compare the registered relationships and derived outcomes, not byte-identical reports.

The [retained execution packet](assets/isolation-study-v1.json) contains 18 answer responses and 55 recorded operations, including readiness events, across the six comparisons:

| Private key | Worker context | Foreign-marker responses | A-repeat cache hit | Both policy reads / overwrite refusals | Contract |
| --- | --- | ---: | --- | --- | --- |
| Query only | Fresh objects | 1 | Yes | 2 / 2 | Fail |
| Query only | Reused object | 1 | Yes | 2 / 2 | Fail |
| Query only | Concurrent threads | 1 | Yes | 2 / 2 | Fail |
| Run scoped | Fresh objects | 0 | Yes | 2 / 2 | Pass |
| Run scoped | Reused object | 0 | Yes | 2 / 2 | Pass |
| Run scoped | Concurrent threads | 0 | Yes | 2 / 2 | Pass |

Each comparison contains three responses: A-first, B-first and A-repeat. The single foreign marker in each buggy comparison is B receiving `{"private_marker": "run-A"}`. The buggy cache makes one private write; the scoped cache makes two, one for each run. The approved shared policy remains unchanged in every comparison.

`conformance_passed: true` means the study reproduced its registered controls, **including the expected failures of the buggy strategy**. It does not mean every system arm passed isolation. `deployment_authorized` remains false. These six constructed comparisons are mechanism checks, not six sampled customers or an estimate of deployment leakage probability.

For example, inspect the fresh-worker query-only trace: operation 3 misses A's private cache, operation 4 writes A's marker, operation 7 returns that marker to B, and operation 8 correctly hits A's own cached answer. Under scoped keys, B's operation 7 misses and operation 8 writes B's marker; A's repeat moves to operation 9. This is the execution evidence behind the verdict, not a hand-authored leak flag.

To reconstruct the retained grades in a Python session started from the repository root:

```python
import json
from pathlib import Path
from cx_eval_lab.isolation_study import replay_study

report = json.loads(Path("docs/assets/isolation-study-v1.json").read_text())
grades = replay_study(report)
assert [g["foreign_marker_responses"] for g in grades] == [1, 1, 1, 0, 0, 0]
assert [g["contract_passed"] for g in grades] == [False] * 3 + [True] * 3
```

Replay reconstructs cache state from initial entries and ordered operations, joins each response to its read or producing write, and checks the final entries and grades. It also checks the independent phase-to-run/worker assignments. A B-phase request accidentally executed under A's identity cannot redefine itself as an A success. Concurrent actions must match the two recorded ready threads, with A's write completed before B's probe. Coherently rehashing a substituted worker, a mismatched thread or reordered calls does not make these traces conform.

These checks establish internal consistency against this harness's registered contract. They do not authenticate historical execution or protect the Python module, expected contract or database from an actor with the same host privileges. The CI workflow includes a fresh execution, but no observed cloud run is claimed here.

## Kata 56: the worker is new, but the state is not

**Know:** worker identity, run identity and resource namespace answer different questions.

**Task:** run A and B with the same query and different private synthetic markers. First create fresh workers over the same store; then reuse a worker; finally use concurrent workers with the registered ordering. Compare the returned values under query-only and run-scoped keys.

??? success "Solution: trace the lookup to its authority context"
    Under query-only keys, A's answer is reusable wherever that query recurs, including B. A new worker can still read the existing record. Restarting the caller does not remove shared service state.

    Under run-scoped keys, B's lookup targets B's namespace. It must miss A's entry and produce B's own response. A subsequent read within A should still hit A's entry. The repair preserves intended reuse while preventing the forbidden reuse.

    The scope must come from the operator's trusted run binding, not a run ID embedded in the user query. A syntactically valid identifier is not evidence that the caller has authority to select that namespace. In this local API, issued context handles model that trust boundary; they do not authenticate a remote client or defeat hostile code in the same interpreter.

    Retain the actual lookup context, returned value, write result and worker identity. Grade the foreign marker appearing in B's observed result, not a supplied `leak_detected` flag. An empty foreign-marker count is only meaningful if B really performed the probe and received a result.

**Extend:** vary tenant, dataset split, prompt version, model version and policy version independently. Decide which dimensions require access separation, which require cache invalidation, and which may intentionally share a result. A run ID is a useful isolation dimension here, not a universal production cache-key design.

**Interview answer:** “I inspect shared state, not just process boundaries. Fresh workers can leak through persistent caches. I bind private cache access to trusted run context, preserve allowed same-run reuse, and check actual returned values across runs.”

## Kata 57: blocking every read is not successful isolation

**Know:** an isolation contract includes permitted operations as well as prohibitions.

**Task:** evaluate a system that never returns cached content. It shows no foreign markers. Does it pass? Then test shared policy reads from both runs and an attempted policy overwrite.

??? success "Solution: include utility and integrity controls"
    No. The experiment requires a same-run cache hit and access to the shared read-only policy. A reject-everything system avoids one failure by abandoning the required behavior. The conformance result must check those positive controls, not only the absence of private-state leakage.

    Both runs should read the same approved public policy. Identical policy content is authorized sharing, not contamination. The attempted overwrite should be refused and the final policy should remain unchanged. Keep private answer keys and shared-policy keys in separate domains so a crafted query cannot collide with a reserved policy record.

    Report three outcomes separately: forbidden private-state exposure, allowed reuse, and shared-resource integrity. They must not cancel one another in an average. A high hit rate cannot compensate for leakage, and zero leakage cannot compensate for a broken cache service.

    Re-grading retained events can detect inconsistent summaries or modified records relative to their anchors. It cannot authenticate the original execution if one actor can rewrite the events, references and expected policy together. Protect the evaluation's evidence and authority inputs separately in a real service.

**Extend:** add sealed acceptance labels, an optimization worker and a shared retrieval index. Specify which actor may read each resource before testing. Reusing a policy document may be allowed while exposing acceptance labels is forbidden, even when both are stored in the same database product.

**Interview answer:** “I test allowed and forbidden information flows together. Isolation must preserve authorized utility, reject unauthorized reads and writes, and keep the grader's authority outside the candidate's control. A no-output system is not an isolation success.”

## What the result can justify

A local result can validate this cache API's key construction and access contract under the registered schedules. It cannot establish that agents are unable to communicate through files, network services, package caches, logs, timing or other shared infrastructure. Nor does it show that a real agent will refrain from seeking those channels.

Keep planned multi-agent cooperation separate. A collaboration task deliberately permits some information flow; an independent-evaluation task may prohibit the same flow. Reuse the explicit sharing-contract method, not a universal ban on communication. The [frontier-risk chapter](frontier-risk-decisions.md) explains why that distinction matters for risk decisions, while the [evaluation-operations chapter](eval-operations-integrity.md) covers how corrupted infrastructure can change a reported capability score.
