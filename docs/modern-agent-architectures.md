# Modern agent architectures: skills, knowledge, voice, and teams

Agent architecture changes what can fail. A retrieval system can find the correct policy and still execute the wrong action; a voice system can finish the task after acting before the customer finished speaking; a multi-agent system can cover more work while duplicating a side effect. Evaluate each architecture with evidence that matches its causal structure.

This chapter contributes completed synthetic protocol comparisons through `cx_eval_lab/advanced.py` and `evals/cx-support/examples/advanced-protocols-v1.json`. The examples validate measurement logic. They are not model leaderboards or deployment proof.

## Knowledge-to-action systems

Evaluate knowledge access and state-changing behavior in the same task while keeping their stages separate:

`knowledge available → retrieval → reasoning → action arguments → external state → customer explanation`

Run at least four interfaces on identical cases:

| Interface | What it isolates |
| --- | --- |
| Normal retrieval | Actual search, ranking, context assembly, and downstream use |
| Oracle documents | Removes search failure while retaining reasoning and action risk |
| Full context | Tests whether retrieval itself is the limiting factor |
| Alternative search interface | Tests whether query/tool affordances change downstream performance |

Sierra's [τ³ discussion](https://sierra.ai/blog/bench-advancing-agent-benchmarking-to-knowledge-and-voice) motivates this separation: correct documents do not guarantee correct reasoning or action. Locally, the oracle-document mutant retrieves the required evidence and reasons correctly, then changes the wrong state. Its failure stage is `action`, not `retrieval`.

### Required metrics

- required-knowledge availability;
- retrieval recall and ranking at the action-relevant unit;
- correct policy interpretation;
- tool selection and argument accuracy;
- authorization and final-state correctness;
- grounded explanation;
- latency and cost by interface.

Do not call an end-to-end failure a RAG failure until the trace localizes it.

## Skills and capability selection

A reusable skill or procedure creates two independent questions:

1. Did the system select and load the right capability?
2. Did it execute that capability correctly under the current context?

Build a selection matrix:

| Condition | Expected behavior |
| --- | --- |
| Explicit request | Activate the named compatible skill |
| Implicit semantic match | Activate only when the trigger contract is satisfied |
| Context-dependent request | Use preceding state without allowing stale context to force activation |
| Competing skills | Select the narrowest applicable procedure or request bounded clarification |
| Incorrect activation | Detect irrelevant or prohibited selection |
| Stale instructions | Refuse authority or re-load the current version |
| Correct selection, bad execution | Label `execution_error`, not selection failure |

OpenAI's [skill-evaluation guidance](https://developers.openai.com/blog/eval-skills) provides a useful first-party framing. The local protocol records `selection_error`, `stale_instruction_error`, and `execution_error` separately so improving one rate cannot hide another.

### Skill-specific mutants

- Generic-support skill wins over the required refund-policy skill.
- Both skills load and issue conflicting instructions.
- Correct skill loads an expired policy version.
- Correct skill is selected but tool arguments are wrong.
- Skill selection succeeds only when its name appears verbatim.
- A prohibited skill activates from untrusted retrieved text.

Measure selection precision/recall, abstention, instruction version, execution success, tool-side effects, and incremental token/latency cost.

## Voice and multimodal workflows

Text transcripts erase timing. A voice evaluation record needs an audio-event timeline:

```yaml
task_id: voice-refund-817
events:
  - {at_ms: 0, type: user_speech_start}
  - {at_ms: 2100, type: identifier_partial, value: "order eight one..."}
  - {at_ms: 3300, type: user_correction, value: "eight one seven"}
  - {at_ms: 3900, type: tool_action_start}
  - {at_ms: 4200, type: user_speech_end}
decision: fail_premature_action
```

The transcript may contain the correct final identifier and a successful refund, yet the action is unsafe because it began 300 ms before the customer finished correcting the order number.

### Voice test matrix

- barge-in before confirmation;
- user correction after a partial identifier;
- silence and end-of-turn uncertainty;
- packet loss and jitter;
- accent, language, code-switching, and background noise;
- partial confirmations such as “yes, but…”;
- tool action before speech completion;
- recovery after interruption;
- matched text-versus-voice tasks.

Report task completion, identifier accuracy, premature-action rate, interruption recovery, false end-of-turn rate, time to first useful response, end-to-end completion time, tail latency, and human correction burden. Audio safety classifiers and task-quality evaluation are complementary, not interchangeable.

## Multi-agent evaluation

Compare multi-agent and single-agent systems under matched total budgets, not equal per-agent budgets. Otherwise additional inference can masquerade as architectural superiority.

### Coordination contract

For each trial, record:

- required subtasks;
- delegation decision and assigned owner;
- information included at each handoff;
- completed subtask evidence;
- shared-state reads and writes;
- merge inputs and conflicts;
- external side-effect identities;
- total tokens, latency, and cost.

Measure:

| Dimension | Failure example |
| --- | --- |
| Delegation correctness | Policy analysis sent to an agent without policy access |
| Coverage | Customer-explanation subtask never assigned |
| Duplicate work | Two agents independently repeat the same search |
| Information preservation | Refund limit disappears at handoff |
| Shared-state contention | One agent invalidates another's approval |
| Merge correctness | Conflicting findings are concatenated rather than resolved |
| Effect safety | Two agents issue the same refund |
| Efficiency | Higher success comes only from exceeding the matched budget |

Anthropic's [multi-agent research-system account](https://www.anthropic.com/engineering/multi-agent-research-system) offers concrete production-oriented coordination patterns. The local synthetic mutant assigns policy twice, omits the customer message, loses one fact, produces a merge conflict, repeats a refund, and exceeds the matched single-agent budget. Each failure remains visible instead of collapsing into one “agent score.”

## Agent-family-specific evidence

The refund workflow cannot carry the whole field. Reuse the evidence spine, but change the authoritative outcome source:

| Agent family | Authoritative outcome | Architecture-specific evidence |
| --- | --- | --- |
| Coding | clean checkout, tests, static analysis, diff | repository state, command logs, hidden tests, patch minimality, forbidden-file access |
| Browser/computer use | DOM/app state plus screenshots where necessary | action sequence, target identity, confirmation timing, page transitions, recovery |
| Professional artifact | parsed workbook/document plus rendered output and reviewer task success | formulas, structure, visual legibility, provenance, editability, requirement coverage |
| Research | claim ledger and primary sources | search coverage, citation entailment, temporal validity, unsupported claims |
| Stateful CX | backend transaction and approval ledgers | identity, policy, amount, currency, idempotency, settlement wording |

Google DeepMind's [FACTS suite](https://deepmind.google/blog/facts-benchmark-suite-systematically-evaluating-the-factuality-of-large-language-models/) is useful when separating parametric, search, grounding, and visual factuality. It does not replace executable outcome checks for systems that modify code, records, or files.

## Evidence added in this chapter

- **Executable evaluators:** knowledge-to-action, skill, voice-timeline, and multi-agent protocols.
- **Observed synthetic results:** oracle knowledge can still fail at action; a correct voice outcome can fail timing; a multi-agent run can lose coverage and duplicate effects.
- **Artifacts:** row-level protocol inputs and derived summaries in `advanced-protocols-v1.json`.
- **Limitations:** no live audio, model, skill-loader, browser, or distributed-agent run was executed.
- **Authority:** `lab_only`.

## Exercise: matched-budget comparison

A four-agent research system completes 88% of tasks for $1.20 per task. A single agent completes 82% for $0.40. When the single agent receives a $1.20 inference budget, it completes 90%. What can be attributed to orchestration?

??? success "Answer"
    The unmatched comparison cannot establish an orchestration advantage. Under the matched budget, the single agent is two points higher, subject to paired uncertainty and the rest of the evaluation vector. Inspect delegation, coverage, merge quality, latency, and failure slices before concluding that one architecture dominates. The result concerns these harnesses and tasks, not all single- or multi-agent systems.
