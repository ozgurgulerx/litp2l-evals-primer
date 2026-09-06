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

## Evidence boundary and next experiment

**Adopt:** process-level fault injection, authoritative-state grading, stable operation identity, and separate workflow/effect records. **Reject:** new-key retry based only on absent workflow completion.

This worker is a deterministic harness component, not a persistent LLM agent. It uses a local database rather than a distributed payment API and pauses at selected boundaries rather than randomly corrupting execution. It does not establish correctness for context compaction, long conversations, concurrent workers, eventual consistency, approval expiry, code-version drift, provider failover, power loss, or customer notification. Those remain separate experiments.

The next transfer step is to route an actual agent's tool calls through a durable boundary and repeat the same interventions with retained trajectories. The broader [long-running systems chapter](long-running-serving.md) and [delivery map](primer-delivery-map.md) preserve those requirements. No result here grants production or canary authority.
