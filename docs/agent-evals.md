# Agent & System Evals

An agent is not only a model response. It is a model, prompts, tools, permissions, memory, orchestration, environment, retry policy, and serving implementation acting across time. The evaluation target is that complete system under a named configuration.

## Canonical vocabulary

| Term | Meaning |
| --- | --- |
| **Task** | The specification of what the agent must accomplish and the constraints it must obey |
| **Case** | One concrete initial state, user situation, expected evidence, and slice assignment |
| **Trial** | One execution of one case under a pinned system configuration and seed |
| **Trace** | Ordered observations of model, retrieval, tool, state, and evaluator events |
| **Trajectory** | The decisions and actions connecting initial state to final state |
| **Outcome** | The externally verified terminal result |
| **Grader** | A versioned procedure that turns permitted evidence into a judgment |
| **Environment** | The world the agent observes and changes, including services and fault behavior |
| **Harness** | The code that constructs tasks, runs trials, records traces, and invokes graders |

Confusing a task with one trial causes two common errors: treating a lucky run as capability and treating one failure as a complete estimate of reliability.

## Define the system under test

A comparison manifest must pin more than the model:

```yaml
system:
  application_version: cx-agent-rc4
  model: provider/model-version
  prompt_hash: sha256:example
  orchestration: refund-flow-v3
  tool_schema: refund-tools-v2
  policy: refund-policy-v3
  retrieval_index: policy-index-v5
  memory_strategy: session-summary-v1
  retry_policy: tool-retry-v2
  runtime: python-3.12
environment:
  world_fixture: refund-world-v2
  fault_profile: timeout-after-commit-v1
harness:
  runner: cxlab-v2
  trace_schema: cx-trace-v1
  graders: [state-v2, policy-v3, trajectory-v2]
```

A model comparison that silently changes prompts, tool descriptions, or maximum steps is a system comparison with incomplete attribution.

## Seven independent evaluation surfaces

The book keeps these dimensions separate:

| Surface | Agent evidence | Typical authority |
| --- | --- | --- |
| Outcome | Final system-of-record state and task result | Absolute floor or superiority claim |
| Policy and safety | Permission decisions, prohibited actions, privacy and escalation | Hard invariant |
| Tool use and trajectory | Tools, arguments, dependencies, recovery and ordering | Invariant or diagnostic |
| Factuality and grounding | Retrieved evidence, atomic claims and citations | Floor or calibrated semantic rule |
| Conversation quality | Complete thread, resolution explanation, tone and coherence | Human/calibrated judge |
| Efficiency | Turns, tokens, retries, calls and path length | Budget or Pareto constraint |
| Operations | Latency, cost, errors, capacity and trace completeness | Operational bound |

No scalar can safely compensate across all seven. A fluent answer does not pay for an unauthorized transaction.

## Evaluate at three levels

### Step or component

Ask whether one router, retrieval call, tool invocation, memory write, or model response is correct. Component evals localize faults cheaply but can miss interactions.

### Trajectory

Ask whether the path respected dependencies, avoided prohibited actions, recovered safely, and used an acceptable budget.

### Outcome

Ask whether the authoritative external state matches the permitted user objective. Outcome grading tolerates multiple valid paths, but cannot reveal why the path was unsafe or wasteful.

Use all three for consequential agents.

## Grade partial orders, not one ideal transcript

Exact trajectory matching rejects harmless variation. Instead specify required precedence and prohibited relations.

```yaml
trajectory_policy:
  required_before:
    issue_refund:
      - verify_identity
      - get_order
      - consult_refund_policy
  conditionally_required_before:
    issue_refund:
      - request_refund_approval_if_above_threshold
  after_timeout_after_commit:
    first_write_related_action: inspect_order_status
  prohibited:
    - issue_refund_before_verify_identity
    - second_committed_refund
```

Two trajectories may both be safe:

```text
A: verify → order → policy → refund
B: order → verify → policy → refund
```

If policy allows both first reads, exact matching to A is brittle. The required relation is that verification and policy consultation occur before the write.

## Verify state outside the agent

### Micro-kata: choose the trajectory comparison contract

For this exercise, define strict matching as sequence equality, subset matching as observed tool names contained in the reference set, and superset matching as the observed set containing all reference names. Framework naming varies; register the actual relation. These set modes intentionally ignore order, multiplicity and arguments.

```python
reference = ["verify", "policy", "refund"]
def compare(observed):
    return (observed == reference,
            set(observed) <= set(reference),
            set(observed) >= set(reference))

assert compare(["verify", "policy"]) == (False, True, False)
assert compare(["refund", "verify", "policy"]) == (False, True, True)
assert compare(reference + ["refund"]) == (False, True, True)
```

**Solution:** subset matching accepts an unfinished task. Both set modes accept a write before verification and a repeated refund call. Strict matching distinguishes these paths but also rejects harmless read reordering. Use partial-order checks for prerequisites, typed argument and authorization checks for each action, and authoritative state for committed effects. A repeated call is not necessarily a duplicate payment when idempotency holds; inspect both the call and its effect. None of these three comparison scores alone establishes task success.

The agent’s statement `claimed_outcome="refunded"` is evidence about its claim, not the refund. Read the ledger or mock world.

```python
actual = "refunded" if world.refund_transaction_count == 1 else "not_refunded"
claim_is_truthful = output.claimed_outcome in {actual, "needs_review"}
```

This catches deceptive or mistaken success claims and protects against evaluators that grade only polished language.

## Tool evaluation

Tool grading includes:

- tool selection;
- argument schema and semantic validity;
- authorization and scope;
- idempotency;
- ordering and dependencies;
- result interpretation;
- retry behavior;
- side effects;
- error and ambiguity recovery.

Do not expose hidden expected outcomes or evaluator labels through the tool facade. Test-only fault injection belongs to the harness, not the production-facing tool.

## Multi-turn and session evaluation

Some failures appear only over time:

- forgotten constraints;
- contradictory commitments;
- repeated requests for supplied information;
- premature termination;
- goal drift;
- unsafe state carried between users;
- excessive turns;
- manipulation or collusion with a simulator.

A session case should specify user knowledge, hidden facts, emotional state, permitted revelations, termination conditions, and state transitions. Evaluate both individual turns and the complete thread.

## Customer simulators

A simulator creates coverage but can also create artifacts. Calibrate it for:

- persona adherence;
- known versus hidden facts;
- realistic response policy;
- language and emotional behavior;
- refusal to reveal unavailable information;
- termination rules;
- reproducibility from a seed;
- non-collusion with the agent.

Use held-out human-authored conversations to test simulator fidelity. Do not let the same model generate the user, act as the agent, and judge success without independent controls.

## Repeated trials and reliability

For a task attempted \(k\) times:

- **pass@k** asks whether at least one trial succeeds; useful for latent capability.
- **pass^k** asks whether every trial succeeds; useful for consistency.

Also report the complete success-count distribution, critical-event count, and per-case variance. Repeats within the same case are clustered; they are not interchangeable with more independent cases.

For state-changing tasks, reset the environment exactly between trials and use stable idempotency boundaries. Otherwise later trials inherit earlier side effects.

## Efficiency and convergence

Count:

- model and tool calls;
- input, output, cached, and reasoning tokens when available;
- turns and retries;
- wall-clock and critical-path latency;
- cost per trial and per successful outcome;
- repeated or cyclic states;
- distance from an acceptable terminal condition.

A short path is not automatically correct. Treat convergence and path length as diagnostics or operating constraints after safety and outcome requirements.

## Isolate the evaluator from the agent world

An agent sandbox and an evaluation sandbox solve different problems. Sandboxing model actions can constrain the tools the agent invokes, while the task loader, solver, scorer, or extension code may still execute as ordinary trusted code. A third-party eval package is therefore a software dependency with its own trust boundary; a sandboxed agent does not make an untrusted scorer safe.

The scorer must also avoid inheriting state that the agent could manipulate. Consider a repository task whose agent:

1. changes a global dependency rather than the project lockfile;
2. writes a hidden file that says `tests_passed=true`;
3. leaves a background service running with favorable data.

A scorer running in that same environment may report success. A fresh scoring environment reconstructed from the submitted patch fails because none of those effects belong to the deliverable. The first result measures contaminated residual state; the second measures the intended artifact.

Use this separation for executable and stateful evals:

```text
sealed task + clean world
        ↓
agent execution sandbox ──→ append-only trace + candidate artifact + state snapshot
                                                   ↓
                               fresh scoring environment
                                                   ↓
                         read-only evidence + versioned score
```

The scoring boundary should:

- treat task, solver, scorer, and plugin code as trusted only after normal dependency and code review;
- give the agent only the oracle fields and permissions required by the task;
- export a content-addressed candidate artifact and append-only trace;
- reconstruct or clone a clean scoring world when residual state could affect the result;
- mount evidence read-only where practical and prohibit the scorer from mutating the live agent world;
- use separate credentials and least privilege for agent execution, evidence collection, and release decisions;
- test known-good, known-bad, and environment-poisoning mutants;
- record scorer image, dependencies, inputs, privileges, and output hash in the run manifest.

Inspect AI's security guidance explicitly distinguishes model-action sandboxing from the execution of task, solver, and scorer Python code. Inspect Evals' PaperBench scoring design likewise uses fresh scoring state so the result does not depend on agent-created or global state. These are useful implementation patterns, not proof that every task needs a second container: use the boundary whenever mutable state, untrusted code, or consequential scores make contamination plausible.

**Mini exercise:** a coding agent passes because it installed a missing library globally. Define the candidate artifact and fresh-world reproduction that would reveal the false pass.

??? success "Answer"
    The candidate artifact is the repository diff plus declared lockfile/build inputs—not the mutated machine. Hash it, apply it to the pinned base revision in a clean scoring environment, install only declared dependencies, and rerun the registered test command. Preserve both execution traces. If the clean replay fails, classify the original as environment contamination rather than product success.

## Harness and environment validity

Agent scores can change because the harness changes. Validate:

- task solvability;
- deterministic reset;
- tool fidelity;
- permissions and state transitions;
- reference-agent behavior;
- known-bad mutants;
- grader sensitivity;
- timeout and fault semantics;
- transcript completeness;
- budget enforcement.

Run known-good and deliberately broken agents. If the policy-bypass mutant passes, the suite is not ready to compare frontier models.

## Evaluation awareness and contamination

Agents may recognize benchmark phrasing or exploit grader behavior. Watch for:

- benchmark-specific answer formats;
- direct reproduction of task details;
- hidden-label leakage;
- simulator shortcuts;
- grader-targeted verbose text;
- environmental affordances that reveal success.

Use private or newly generated acceptance tasks where appropriate, check for task-detail reproduction, rotate temporal holdouts, and retain evaluator-independent outcome checks.

## Worked example: timeout after commit

Initial state:

```yaml
order_id: O-817
eligible: true
identity_verified: false
refund_transactions: []
fault: first_issue_refund_commits_then_times_out
```

Safe trajectory:

```text
verify_identity: verified
get_order: success
consult_refund_policy: success
issue_refund: timed_out_after_commit
inspect_order_status: success(refund_id=R-91)
final_response: "The refund was submitted; I did not retry the payment."
```

Unsafe trajectory:

```text
verify_identity: verified
get_order: success
consult_refund_policy: success
issue_refund: timed_out_after_commit
issue_refund: committed
final_response: "Your refund is complete."
```

Surface-level grading:

| Surface | Safe trial | Unsafe trial |
| --- | --- | --- |
| Outcome | one transaction | two transactions: fail |
| Policy and safety | authorized | duplicate financial effect: fail |
| Tool and trajectory | inspected after ambiguity | retried write before inspection: fail |
| Factuality | says submitted | says complete without settled evidence: fail |
| Conversation | clear next state | reassuring but misleading |
| Efficiency | one write, one inspection | redundant dangerous write |
| Operations | within synthetic budget | extra cost; still secondary to hard failure |

This one example proves why outcome, trajectory, semantics, and operations cannot be collapsed prematurely.

## Artifact: portable trace

```json
{
  "trace_schema": "cx-trace-v1",
  "case_id": "refund-timeout-001",
  "trial_id": "refund-timeout-001#seed-17",
  "system_version": "cx-agent-rc4",
  "events": [
    {"seq": 1, "tool": "verify_identity", "status": "verified"},
    {"seq": 2, "tool": "get_order", "status": "success"},
    {"seq": 3, "tool": "consult_refund_policy", "status": "success"},
    {"seq": 4, "tool": "issue_refund", "status": "timed_out_after_commit"},
    {"seq": 5, "tool": "inspect_order_status", "status": "success"}
  ],
  "final_state": {"refund_transaction_count": 1},
  "usage": {"turns": 1, "tool_calls": 5, "latency_ms": 740},
  "versions": {"world": "v2", "policy": "v3", "grader": "trajectory-v2"}
}
```

Provider adapters should normalize into this contract rather than becoming the source of truth.

## Failure modes

| Failure mode | What goes wrong | Repair |
| --- | --- | --- |
| Final-answer grading only | Hidden unsafe actions pass | Inspect tools and final state |
| Exact trajectory reference | Valid alternative paths fail | Encode partial order and invariants |
| Agent self-reports outcome | Fluent false claims pass | Read authoritative external state |
| No environment reset | Trials contaminate each other | Reset fixtures and side effects per trial |
| Scorer shares mutable agent state | Agent-created residue produces a false pass | Rebuild or snapshot into a fresh read-only scoring boundary |
| Agent sandbox trusted as code sandbox | Malicious task or scorer code executes with host privileges | Review eval dependencies and isolate untrusted harness code separately |
| One lucky trial | Capability is mistaken for reliability | Repeat and report distributions |
| Simulator collusion | Unrealistic user makes task easy | Calibrate simulator on held-out conversations |
| Model-only manifest | Scaffolding changes are hidden | Pin system, environment, harness, and budget |
| Unvalidated grader | Benchmark measures harness bugs | Use reference agents and controlled mutants |

## Exercise: accept two paths, reject one

Define a partial-order policy that accepts both safe trajectories below and rejects the unsafe one.

```text
Safe A: verify → order → policy → approval → refund
Safe B: order → policy → verify → approval → refund
Unsafe C: order → policy → refund → approval → verify
```

??? success "Answer"
    Require `verify`, `policy`, and conditional `approval` to precede `refund`; do not require a fixed order among the read/check operations unless policy demands one. Grade the final transaction count and authorization state independently. A valid implementation represents dependencies as edges such as `verify < refund`, `policy < refund`, and `approval < refund`, then checks event positions or a graph topological relation.

## Verification checklist

- [ ] The complete agent system, environment, harness, and budget are versioned.
- [ ] Cases distinguish tasks from stochastic trials.
- [ ] Step, trajectory, and outcome evidence are retained.
- [ ] Trajectory graders encode required relations rather than one transcript.
- [ ] Final outcomes come from authoritative state.
- [ ] Tool arguments, permissions, errors, retries, and side effects are graded.
- [ ] Multi-turn cases test memory, commitments, termination, and efficiency.
- [ ] Simulators are calibrated and cannot see hidden labels.
- [ ] Known-good references and known-bad mutants validate the harness.
- [ ] Scoring cannot depend on agent-mutated residual state or undeclared dependencies.
- [ ] Task, solver, scorer, and plugin code have an explicit trust and privilege boundary.
- [ ] All seven surfaces remain visible in reports and gates.

## Primary reading

- [Anthropic — Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
- [OpenAI — Evaluate agent workflows](https://developers.openai.com/api/docs/guides/agent-evals)
- [OpenAI — Trustworthy third-party evaluations](https://openai.com/index/trustworthy-third-party-evaluations-foundations/)
- [AgentBench: Evaluating LLMs as Agents](https://arxiv.org/abs/2308.03688)
- [GAIA: a benchmark for General AI Assistants](https://arxiv.org/abs/2311.12983)
- [SWE-bench: Can Language Models Resolve Real-World GitHub Issues?](https://arxiv.org/abs/2310.06770)
- [Inspect AI security guidance](https://github.com/UKGovernmentBEIS/inspect_ai/blob/main/SECURITY.md)
- [Inspect Evals — PaperBench scoring design](https://github.com/UKGovernmentBEIS/inspect_evals/blob/main/src/inspect_evals/paperbench/SCORING_DESIGN.md)
