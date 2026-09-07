# Process recovery study: the missing acknowledgement

**Question:** after a process dies, does the resumed workflow reconcile the payment ledger or infer payment state from its own checkpoint?

**Status:** executed local process experiment, not a supplied-observation fixture. The parent launches a worker, waits for a registered boundary marker, kills that child, verifies its exit, and starts a new process against the same durable mock ledger. No model, customer account, or real payment service is involved.

The complete [21-trial artifact](assets/process-recovery-study-v1.json) includes source hashes, Python/SQLite/platform versions, process IDs, return codes, interruption and final ledger snapshots, recovery results, and elapsed time. It was generated at revision `919461d`. The recorded environment was macOS, Python 3.12.7, SQLite 3.45.3. The runner uses POSIX pipe selection and is intended for macOS/Linux.

## What actually executes

`cx_eval_lab/recovery_worker.py` has two separate durable commits:

1. A mock payment service checks order/amount/currency approval and commits a payment keyed by an idempotency key.
2. The workflow writes its own completion checkpoint.

The payment boundary runs under a SQLite transaction. Repeating the same key with the same action returns the original committed result; changing the action under that key is rejected. A new key is a new payment request and can create another effect. The reference therefore reuses its operation key after restart. The mutant treats a missing checkpoint as proof that no payment happened and retries with a new key.

SQLite's atomic-commit mechanisms depend on filesystem and hardware assumptions; this study does not test power failure or damaged storage. The process harness uses `Popen.kill()` on a child it owns, which sends SIGKILL on POSIX. These implementation details follow the [SQLite atomic-commit documentation](https://www.sqlite.org/atomiccommit.html) and [Python subprocess documentation](https://docs.python.org/3/library/subprocess.html). Our observed results below come from the retained local executions.

## Registered interventions and observed results

Each row ran three times in a newly initialized database. The worker's payment amount was 4,000 cents in USD, approved for one synthetic order. These repetitions exercise deterministic execution paths; they are not independent customer samples or a live-agent reliability estimate.

| Intervention | Resume behavior | Final payments, each run | Contract result |
| --- | --- | ---: | --- |
| Uninterrupted control | Commit, then checkpoint | 1 | 3/3 pass |
| Kill before payment | Revalidate approval, commit, checkpoint | 1 | 3/3 pass |
| Kill after payment, before checkpoint | Reconcile the existing key, checkpoint | 1 | 3/3 pass |
| Kill after checkpoint | Reconcile the existing key | 1 | 3/3 pass |
| Kill after payment; mutant retries with new key | Make a second payment | 2 | 3/3 mutant failures detected |
| Kill before payment; revoke approval before restart | Deny the new action | 0 | 3/3 safety-contract pass |
| Kill after payment; revoke approval before restart | Report the already committed payment without another effect | 1 | 3/3 pass |

A safety-contract pass in the denial row does **not** mean the customer's refund was completed. It means the resumed worker correctly refused an action whose approval had been revoked. Record task resolution and policy adherence separately in an application report.

The interrupted workers returned `−9` in this run; the parent then observed new process IDs on resume. The mutant resumed with exit code zero despite leaving two payments. A successful process exit is therefore not a successful application outcome. The grader detects the failure from durable rows, not from the mutant announcing that it duplicated a payment.

## Kata 11: kill after commit, before checkpoint

**Know:** the effect ledger and the workflow checkpoint answer different questions. A missing checkpoint means the workflow has not recorded completion; it does not establish that the external action failed.

**Predict:** the worker commits a payment, then dies before writing its checkpoint or returning a final response. What evidence should the new process inspect before doing anything state-changing?

```bash
uv run python -m unittest tests.test_process_recovery -v
uv run python -m cx_eval_lab.recovery_study \
  --repetitions 3 \
  --output artifacts/runs/process-recovery-study.json
```

Use a new filename for another run. Output is never overwritten. The runner creates only owned temporary databases and child processes; it retains their relevant snapshots in JSON before removing the temporary databases. Worker waits and resumed calls have five-second timeouts. The study accepts at most twenty repetitions.

??? success "Solution: preserve operation identity, then reconcile"
    `issue_payment` checks the existing idempotency key inside the transaction. If the order, amount, and currency match, it returns `already_committed` rather than inserting another payment. The workflow can then finish its own checkpoint.

    In the interrupted snapshot, inspect `payments` and `checkpoints`: after the payment boundary, there is one payment and no checkpoint. In the reference final snapshot there is still one payment and a complete checkpoint. In the mutant final snapshot there are two payments with distinct keys.

    `test_new_key_retry_duplicates_a_committed_effect` launches the real worker and reproduces that difference. `test_reference_recovers_at_each_crash_boundary_without_duplicate_effects` checks the three registered crash points. `test_timeout_cleans_up_only_its_owned_worker` checks harness cleanup if a boundary is not observed.

**Extend:** add a notification side effect after the payment checkpoint. Give it its own durable identity and state. Explain why “payment complete” must not mean “customer notified,” and inject a crash between notification commit and acknowledgement. That second-side-effect protocol is not implemented by this study.

**Interview answer:** “I do not infer external state from a missing local checkpoint. I preserve operation identity, query or retry through an idempotent service boundary, verify the authoritative result, and resume unfinished work. I test the commit-to-acknowledgement gap with real process interruption.”

## Kata 12: revoked authority versus historical fact

**Know:** permission to perform a new action and evidence that an action already happened are different objects.

**Task:** compare revocation before the payment with revocation after the payment but before workflow completion. Then reuse the original idempotency key with a changed currency or amount.

??? success "Solution: check authority for new effects and identity for reconciliation"
    Before commit, no historical payment exists. The resumed transaction sees revoked approval and returns a structured `PermissionError`; it writes no payment or completion checkpoint.

    After commit, the existing key identifies an action already performed. Returning that historical result creates no new effect and does not restore approval. A fresh payment key remains subject to current approval. Tests exercise both cases and verify the durable payment count.

    `test_idempotency_key_cannot_change_amount_or_currency` checks that a retained key cannot be repurposed for a different order, amount, or currency. The service rejects that conflict instead of quietly returning a misleading success or changing the original payment.

**Extend:** give approval an expiry and policy version, then change each independently across restart. For historical reconciliation, decide which evidence must be retained to explain the old action. For new effects, require current authorization. The current mock approval schema covers only object, amount, currency, and revocation—not the full production approval contract.

**Interview answer:** “Revocation prevents future effects; it cannot erase a completed effect. I distinguish historical reconciliation from new authorization and bind idempotency to the exact action parameters.”

## Kata 99: the process died, but the allowance did not reset

**Know:** a workflow checkpoint is not a payment ledger or a budget ledger. The optional budget extension now stores a fixed count/per-currency policy in the same database as payments. Existing unbudgeted trials and their retained artifact remain unchanged.

Run the process-level regression checks:

```sh
uv run python -m unittest tests.test_recovery_budget tests.test_process_recovery -v
```

Then inspect one bounded payment and its exact replay:

```python
# kata99-start: local mock payments only
from pathlib import Path
from tempfile import TemporaryDirectory
from cx_eval_lab.recovery_worker import initialize, issue_payment, budget_snapshot

with TemporaryDirectory() as directory:
    database = Path(directory) / "payments.sqlite"
    initialize(database, max_actions=1, currency_caps={"USD": 4000})
    assert issue_payment(database, "original") == "committed"
    assert issue_payment(database, "original") == "already_committed"
    try:
        issue_payment(database, "new-key")
    except PermissionError as error:
        assert str(error) == "budget_action_limit"
    else:
        raise AssertionError("new effect exceeded campaign capacity")
    state = budget_snapshot(database)
    assert state["charged_actions"] == 1
    assert state["charged_cents"] == {"USD": 4000}
    assert state["remaining_actions"] == 0
    assert state["deployment_authorized"] is False
    print(state)
# kata99-end
```

**Predict:** what should remain after killing the worker just after payment insertion but before commit? What changes when it dies after commit but before its checkpoint? Why must the competing-process test inspect the final ledger rather than count successful process exits?

??? success "Solution: consumption follows committed effects"
    Before transaction commit, the inserted row is not a completed payment. The controlled kill-and-reopen test finds no committed payment and no consumed allowance; a new worker can perform the authorized action. After commit, the payment remains even without a workflow checkpoint. Restarting with the exact action key returns `already_committed`, with one payment and one consumed unit—not a replenished budget.

    Two spawned processes synchronize before requesting different keys against the last available unit. One commits and the other is denied. Both consult persisted policy and payment consumption inside their write transactions; no caller-supplied campaign identifier or optional payment-call budget can bypass the configured database policy. Currency caps remain separate; zero is a valid cap, Boolean and out-of-range values are not.

    Historical replay is checked before current approval and capacity because it creates no new effect. A changed action under the same key is a conflict. A fresh key still needs current approval and remaining capacity. The tests preserve the legacy mutant that duplicates payments without a cap; configuring a cap changes the permitted effects, not the meaning of idempotency.

**Evidence limit:** these are executed regression tests against owned temporary databases, not a new retained multi-window budget packet or a live-agent evaluation. The earlier exposure campaign still uses its in-memory boundary. Integrating this durable service with that campaign, retaining a full process-level packet, and enforcing authenticated ownership remain separate work. Direct database access is trusted; this code is not a hostile-agent sandbox. No real money moves.

### Durable budget contract: put the allowance beside the effect

The historical experiment above has no campaign cap: its new-key mutant can create a second payment. Preserve that result. The extension joins an optional fixed policy to the existing database before any payment, rather than trusting each caller to supply an allowance.

The intended transaction order is **historical replay → current approval for a new action → campaign capacity → payment insertion → commit**. Consumption is derived from committed payment rows; there is no separately persisted counter to reconcile. A workflow checkpoint remains a different transaction. Resetting or losing that checkpoint must not reset the allowance.

| Failure boundary | Required payment state after reopening the database | Required allowance behavior |
| --- | --- | --- |
| Worker dies before payment transaction commits | No new committed payment | No consumption from the uncommitted row |
| Worker dies after payment commit, before checkpoint | Original payment remains | Original effect still consumes capacity; exact replay consumes nothing more |
| Two processes compete for the last effect | At most one new payment | The second transaction observes committed consumption and refuses a new effect |
| Approval revoked after an earlier payment | Earlier payment remains | Historical reconciliation is allowed; new effects still require approval |

These acceptance conditions are now exercised by the extension's process-level regressions; they are not additional results in the historical 21-trial artifact. Inspect the database, not just process exit codes.

SQLite allows one simultaneous write transaction, and `BEGIN IMMEDIATE` requests that transaction before reading the allowance. Contention can fail with a busy error; failure must not switch to an uncapped path. This is a single-database ordering boundary, not a distributed payment guarantee. [SQLite transaction documentation](https://www.sqlite.org/lang_transaction.html).

The atomic-commit guarantee also has filesystem and hardware assumptions. Killing an owned worker tests process interruption, not power-loss behavior, damaged storage or a remote payment provider. If the real effect lives outside this transaction, a separate reconciliation protocol is required; a successful local budget update does not make a remote charge atomic. [SQLite atomic-commit documentation](https://www.sqlite.org/atomiccommit.html).

## Evidence boundary and next experiment

**Adopt:** process-level fault injection, authoritative-state grading, stable operation identity, and separate workflow/effect records. **Reject:** new-key retry based only on absent workflow completion.

This worker is a deterministic harness component, not a persistent LLM agent. It uses a local database rather than a distributed payment API and pauses at selected boundaries rather than randomly corrupting execution. The historical study does not establish correctness for context compaction, long conversations, concurrent workers, eventual consistency, approval expiry, code-version drift, provider failover, power loss, or customer notification. Kata 99 adds a bounded competing-process budget test; the other transfer claims and broader concurrency behavior remain separate experiments.

The next transfer step is to route an actual agent's tool calls through a durable boundary and repeat the same interventions with retained trajectories. The broader [long-running systems chapter](long-running-serving.md) and [delivery map](primer-delivery-map.md) preserve those requirements. No result here grants production or canary authority.
