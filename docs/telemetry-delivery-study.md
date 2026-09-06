# Telemetry delivery: measure the evidence channel

A missing trace is not a successful request. Nor does it necessarily mean the application outcome is unknown: a separate application ledger may already know what happened. This study compares those two views while exercising actual local telemetry delivery.

## Protocol and authority

The workshop uses a private OpenTelemetry Python SDK provider and its native OTLP/HTTP exporter. A loopback-only test receiver decodes the protobuf payloads. Each request has a root span and one child spanning the evaluation call. These are not individual tool or model spans, and their timings do not localize each internal step.

Four registered synthetic CX requests run through the existing deterministic evaluation code. An application-owned, in-memory SQLite ledger records the request inventory independently of the collector. The collector controls delivery, not the business action. The study compares normal delivery, a receiver capacity limit, terminal rejection, and acceptance followed by a retryable response that causes duplicate delivery.

The SQLite table holds request and span identities; business results are retained separately in the report. “Independent” here means a separate accounting path from export, not a separate trusted machine, authenticated witness or durable audit service.

The receiver stores a validated span before acknowledging it. Its retained log distinguishes transport attempts from unique span identities. It has no external authentication service or durable storage; an acknowledgment means acceptance into this local process, not replication or survival after a crash. This is real loopback OTLP transport to a deliberately small test receiver—not a deployed OpenTelemetry Collector or operated production monitoring service.

Application outcomes, example customers and feedback labels are synthetic. There are no model calls, hosted collector uploads or real refunds. SDK instrumentation and HTTP exchange are real. A replay checks the retained experiment's consistency; it does not independently attest execution or authenticate reviewers.

## Executed comparison

The normal, capacity-limited and rejected arms each make eight HTTP attempts, one per ended span. The retry arm makes nine: the receiver accepts the first span but returns 503, then receives exactly the same protobuf payload again. Deduplication retains eight unique spans rather than nine. All four controls return `True` from provider flushing; receiver inventories still differ.

| Receiver control | HTTP attempts | Unique retained spans | Observed request roots | Passing roots / observed roots | Missing roots | Complete business ledger |
| --- | ---: | ---: | ---: | --- | ---: | --- |
| Normal | 8 | 8 | 4 | 2/4 = 50% | 0 | 2 pass, 2 fail |
| Capacity limit | 8 | 4 | 2 | 2/2 = 100% | 2 | 2 pass, 2 fail |
| Terminal rejection | 8 | 0 | 0 | Undefined, not zero or 100% | 4 | 2 pass, 2 fail |
| Accept, retry, deduplicate | 9 | 8 | 4 | 2/4 = 50% | 0 | 2 pass, 2 fail |

The capacity control deliberately retains the first two requests, which are the passing reference cases, and loses both mutant traces. It illustrates selective loss; it does not estimate how often a real collector loses failures. The complete application outcome is still 2/4 in every arm. `unknown_requests` in the artifact means unknown in the **receiver's trace view**, not unknown to the independent business ledger.

### Reproduce and inspect

```bash
uv sync --frozen --group dev --extra openai --extra telemetry
uv run --extra telemetry python -m cx_eval_lab.telemetry_study \
  --output /tmp/my-telemetry-study.json
uv run --extra telemetry python -m unittest tests.test_telemetry_study -v
```

Choose a new output path; the CLI refuses to overwrite one. Exporter logs for HTTP 400 and a transient 503 are expected in the negative controls. Judge conformance by the registered outcomes and verifier, not by the absence of the word “error” in logs. The [retained artifact](assets/telemetry-study-v1.json) includes raw protobuf payloads encoded as base64, their hashes, HTTP outcomes, unique stored spans, ledger identities, export results and feedback joins. The base64 payloads are inspectable evidence, not encryption. Their content has passed the study's narrow export allowlist; do not apply that publication policy to arbitrary real customer traces.

Trace IDs and timestamps vary across fresh runs. Compare `stable_projection(report)` for registered outcomes and counts; do not pretend different wall-clock traces are byte-identical. `verify_study(report)` validates retained transport consistency and reexecutes the four deterministic business controls for each arm in fresh mock worlds. Thus the CLI performs sixteen measured business executions and sixteen additional verification executions. Those verification calls are not delivery retries and are not live payments or model calls.

The selected runtime manifest records the observed Python and package versions plus hashes of the two telemetry source modules. It is not the complete imported CX source or dependency closure. These hashes identify recorded bytes; they are not signatures or proof that those bytes ran. The verifier checks the registered package contract and metadata shape, not the authenticity of the machine or a historical execution. Historical source hashes need not match a future checkout.

Inspect the retained evidence from the repository root without sending HTTP:

```python
import json
from pathlib import Path
from cx_eval_lab.telemetry_study import verify_study

report = verify_study(json.loads(Path("docs/assets/telemetry-study-v1.json").read_text()))
arms = {arm["mode"]: arm for arm in report["arms"]}
capacity = arms["capacity"]["summary"]
assert capacity["observed_pass_rate"] == 1.0
assert capacity["ledger_passes"] / capacity["registered_requests"] == 0.5
assert arms["reject"]["summary"]["observed_pass_rate"] is None
assert arms["retry-dedup"]["summary"]["duplicate_deliveries"] == 1
assert arms["capacity"]["feedback"]["pending_feedback"] == 1
assert not report["deployment_authorized"]
```

This inspection performs another sixteen mock business-control executions through `verify_study`; it does not re-send the stored telemetry.

## Kata 83: flush succeeded, evidence disappeared

**Know:** transport health, application correctness and decision authority need separate evidence.

**Task:** inspect the capacity arm. A dashboard reports 100% success and flushing returns `True`. Explain why that does not justify expanding exposure. Then compare the retry arm: what proves the extra POST did not create an extra request or inflate trace coverage?

??? success "Worked solution: restore the denominator and separate retries"
    The capacity arm has four independently registered requests, but only two request roots. Both surviving roots pass, so 100% describes the observed subset. The business ledger still records two failures and four invocations. Missing trace evidence cannot remove those failures. If the separate ledger were unavailable, the observed roots alone would bound success in this four-request cohort between 2/4 and 4/4; that range is not a confidence interval.

    The rejection arm makes the same distinction stark: no root is observed, so the trace-only rate is undefined. Its independent business ledger still knows two passes and two failures. Zero telemetry cannot support a positive release claim, and it should not be mislabeled as four application failures either.

    In the retry arm, the first two attempts have matching payload hashes and the same trace/span identity. Their responses are 503 and 200. The receiver stores the span before the first response and treats the second delivery as a duplicate. There are nine HTTP attempts, eight unique spans and four business invocations within the measured arm. Business results match the normal arm; the transport retry does not invoke the refund workflow again.

    Replaying the receiver policy explains the recorded deduplication. It does not authenticate the historical log or prove durable storage. The local request ledger, test receiver and verifier remain trusted workshop components. A real service needs independent persistence and integrity controls.

**Extend:** change the bytes under a previously stored trace/span identity. Reject the conflict instead of treating it as an idempotent retry. Then model an asynchronous queue: register its capacity, eviction policy, admission behavior, retry budget and shutdown deadline. This synchronous study does not qualify those backpressure rules.

**Interview answer:** “I join receiver records to an independent attempted-work inventory. Flush success is not a receipt. I deduplicate delivery, keep conflicting duplicates visible, and never repeat the business action to repair telemetry.”

## Kata 84: feedback arrives before its trace

**Task:** the input has two distinct feedback annotations plus one exact retry of the first annotation. In the capacity arm, the second annotation's request root is missing. Count unique opinions and pending joins. Then try changing a rating under the original feedback ID, or joining a root with the right request ID but a different trace ID.

??? success "Worked solution: preserve identity, disagreement and pending work"
    There are three delivered annotation rows, two unique annotations, one delivery duplicate, and two requests with feedback. Normal and retry-dedup arms have no pending annotations. Capacity has one pending annotation; rejection has two. A missing trace does not remove the independently registered request, so preserve its annotation as pending.

    The exact duplicate contributes no new opinion. A changed rating or target under that same annotation identity is a conflict, not a retry. A legitimate independent second review needs a distinct annotation identity; a revision needs its own explicit history. Never resolve disagreement by overwriting the first row.

    A trace join checks request identity, trace identity, root identity and evaluation version. A matching request label alone is insufficient. A missing root stays pending; a supplied but inconsistent root is rejected. These checks establish referential consistency, not the reviewer's identity or independence.

    The capacity arm retains the positive annotation's trace while the negative annotation remains pending. Reporting only joined feedback can therefore create a favorable view without changing either opinion. Keep annotation coverage and pending age visible, and do not equate these authored ratings with authoritative task success.

**Interview answer:** “I deduplicate feedback transport, not human disagreement. I preserve pending joins and exact execution/evaluation identity, and I report selection and missingness before interpreting a feedback rate.”

The workshop has one output per registered execution. A product supporting edited or regenerated answers also needs explicit output-version binding and a feedback-revision protocol; these controls are not supplied by a request ID alone.

## What must remain independent

| Inventory | Unit | Reason to retain it |
| --- | --- | --- |
| Application ledger | Registered request | Export loss cannot remove attempted work from the denominator |
| Business outcome | Evaluated request and its effects | A telemetry failure must not rerun a refund |
| HTTP attempt log | Export attempt | Retries and failures must remain visible |
| Receiver store | Unique trace/span identity | Duplicate delivery must not inflate coverage |
| Feedback log | Annotation identity and exact target | Delivery retries must not manufacture additional opinions |

The request and evaluation versions are part of the join. Parent links distinguish a request root from its evaluation child. Counting eight arbitrary spans is not proof that four complete request traces arrived. An orphan, duplicated or incorrectly parented span cannot fill a missing slot merely because it increases the count.

## Privacy boundary

Spans contain only registered opaque request identifiers, fixed version/role metadata and bounded evaluation booleans or counts. The workshop does not attach prompts, customer-facing text, tool arguments or exception descriptions. Resource metadata is explicit rather than populated from ambient host information. The HTTP session must not inherit proxy settings, netrc credentials or arbitrary exporter headers.

The receiver validates the original protobuf bytes, including resource, scope, span, event and status fields, before retaining them. Testing only a sanitized JSON projection would miss a leak that had already crossed the network boundary. Deliberately planted private strings are test inputs, not real personal data; their absence is a bounded regression check, not a universal guarantee against every sensitive representation or covert channel.

Keep the application evidence and identity mappings outside general telemetry export. An opaque ID is useful for joining approved records; it does not make all linked records anonymous.

## Read the delivery contract, not the method name

In the pinned SDK, `SimpleSpanProcessor.force_flush()` returning `True` does not establish that the receiver accepted anything. The processor's export handling can also isolate telemetry failures from application execution. Inspect expected and received identities, HTTP results and retry history instead of treating a flush Boolean as an acknowledgment. [OpenTelemetry Python 1.44.0 processor implementation](https://github.com/open-telemetry/opentelemetry-python/blob/v1.44.0/opentelemetry-sdk/src/opentelemetry/sdk/trace/export/__init__.py)

The SDK and OTLP exporter are pinned at 1.44.0 in the optional `telemetry` dependency group. These are the versions selected for this experiment, not a promise about future API behavior. [SDK package](https://pypi.org/project/opentelemetry-sdk/1.44.0/), [HTTP exporter package](https://pypi.org/project/opentelemetry-exporter-otlp-proto-http/1.44.0/)

## What this does not qualify

The synchronous processor is chosen to make each delivery boundary inspectable. Ending the child span can block while its export completes, so the enclosing root's duration includes that telemetry work. Do not call the root duration pure model latency or compare it with the runner's synthetic measurement profile. This implementation does not demonstrate asynchronous, low-overhead production instrumentation; that requires a separate queue, timeout and loss experiment.

**Adopt:** independent request accounting, explicit local provider ownership, content-minimized spans, exact joins and conflict-aware deduplication. **Adapt:** replace the in-memory receiver and synchronous export path with governed durable infrastructure, then repeat the failure tests. **Reject:** treating a successful flush, a favorable surviving subset or joined feedback alone as authority to expand exposure.

Real application rollout still needs representative traffic, governed raw evidence, durable delivery and retention, authenticated feedback, access controls, alert ownership, asynchronous backpressure, and an explicitly authorized exposure controller. Sampling and export loss require separate treatment: a designed sample has a known inclusion mechanism; an overloaded receiver may selectively lose the hardest requests.

The [Production chapter](production-evals.md) supplies the signal and denominator contracts. The [Exposure Control Lab](exposure-control-lab.md) exercises a separate simulated routing controller. Neither should be described as connected to a real customer deployment merely because this local telemetry experiment succeeds.
