# Foundations

An evaluation is a decision instrument. Before choosing a metric, state the decision it must support and the cost of being wrong.

## Start with the product promise

Write the user-visible behavior in plain language. Then split it into claims that can be observed independently.

| Question | Working note |
| --- | --- |
| Who relies on the system? | _Add the primary user and affected stakeholders._ |
| What must it accomplish? | _Describe the task without naming a metric._ |
| What must never happen? | _List unacceptable harms and failures._ |
| What trade-offs are allowed? | _Record latency, cost, and quality boundaries._ |

## Define the unit of evaluation

A unit might be a single response, a tool call, a conversation, or a completed workflow. Choose the smallest unit that still captures the behavior you need to judge.

## Write the evaluation contract

Use this sentence as a starting point:

> Given **[context]**, when the system **[acts]**, it should **[observable behavior]**, subject to **[constraints]**.

<!-- Continue with your own examples and principles here. -->

