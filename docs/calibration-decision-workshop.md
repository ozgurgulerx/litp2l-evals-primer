# Calibration decision workshop: 95% agreement is not the release rule

A judge agrees with reference labels on 190 of 200 examples. It also passes five of the twenty unsafe examples. Another judge passes none of them, but sometimes abstains. Which one can qualify for automatic acceptance, and how much human review would it create?

This is an **authored numerical exercise**, not a human annotation study or measured model comparison. All counts, the traffic mix, the target and the staffing assumptions below are supplied teaching inputs. The code recomputes their consequences. For actual runner integration and qualification records, use the [Semantic Grading Lab](semantic-grading-lab.md).

**Timebox:** 25 minutes to compute and draft a decision; 10 minutes to defend it. Submit a metric table, a qualification decision, a data-collection plan and a review-capacity calculation. Do not infer a production authorization from the exercise's labels.

## Supplied contract and observations

The criterion is whether a customer-facing response is compliant with its supplied policy and transaction evidence. Reference labels are `safe` or `unsafe`. A judge returns `pass`, `fail` or `abstain`. These are criterion labels, not evidence that a refund occurred or that a customer was satisfied.

The proposed workflow would automatically accept `pass` responses and send both `fail` and `abstain` to human review. The illustrative qualification target is a **one-sided 95% upper bound of at most 1% on the probability that an unsafe response receives `pass`**. This target is chosen for the exercise, not recommended as a universal safety threshold.

| Authored judge | Reference label | Judge pass | Judge fail | Judge abstain |
| --- | --- | ---: | ---: | ---: |
| A: always passes | Unsafe | 20 | 0 | 0 |
| A: always passes | Safe | 180 | 0 | 0 |
| B: binary judge | Unsafe | 5 | 15 | 0 |
| B: binary judge | Safe | 175 | 5 | 0 |
| C: selective judge | Unsafe | 0 | 15 | 5 |
| C: selective judge | Safe | 170 | 5 | 5 |

Each judge is described on the same 200 example identities, but the table supplies only **marginal counts**, not the item-level joint predictions. You can compute each judge's metrics. You cannot reconstruct which individual predictions changed or a paired uncertainty interval from these margins alone.

For the statistical calculation, temporarily assume the twenty unsafe examples are independently sampled from a fixed target unsafe-response population with reliable labels. You must later challenge that assumption; the aggregate table cannot verify it.

## Kata 90: choose the denominator before choosing the winner

**Predict:** compare overall agreement, unsafe false-pass rate, safe false-alarm rate, abstention and automatic acceptance. Is C's agreement directly comparable to B's when abstentions are excluded?

```python
judges = {
    "A": {"unsafe": (20, 0, 0), "safe": (180, 0, 0)},
    "B": {"unsafe": (5, 15, 0), "safe": (175, 5, 0)},
    "C": {"unsafe": (0, 15, 5), "safe": (170, 5, 5)},
}
for name, rows in judges.items():
    unsafe, safe = rows["unsafe"], rows["safe"]
    total = sum(unsafe) + sum(safe)
    abstained = unsafe[2] + safe[2]
    classified = total - abstained
    agreement = (unsafe[1] + safe[0]) / classified
    false_pass = unsafe[0] / sum(unsafe)
    false_alarm = safe[1] / sum(safe)
    accepted = (unsafe[0] + safe[0]) / total
    review = (unsafe[1] + unsafe[2] + safe[1] + safe[2]) / total
    print(name, f"agreement={agreement:.2%}", f"unsafe-pass={false_pass:.2%}",
          f"safe-fail={false_alarm:.2%}", f"accept={accepted:.2%}",
          f"review={review:.2%}", f"abstain={abstained / total:.2%}")
```

??? success "Solution: accuracy hides the dangerous conditional error"
    A has 90% agreement but passes every unsafe response. B has 95% agreement, an unsafe false-pass rate of `5/20 = 25%` and a safe false-alarm rate of `5/180 ≈ 2.78%`. Five of B's 180 pass decisions are unsafe; that `5/180` denominator answers a different question from `5/20`.

    C's agreement among nonabstained labels is `185/190 ≈ 97.37%`. Its classification coverage is 95%, automatic acceptance is `170/200 = 85%`, and the review queue is `30/200 = 15%`. The queue includes twenty fail labels and ten abstentions. Do not call the 95% classification coverage a 95% automatic-acceptance rate.

    C's observed unsafe-pass event rate is `0/20`. That includes all twenty reference-unsafe inputs, including five abstentions, because the registered event is receiving `pass`. If instead you ask about errors conditional on a nonabstained unsafe classification, the denominator is fifteen. Those are different estimands.

    C's higher conditional agreement is not proof of superiority: it excludes ten cases and the table lacks item-level paired predictions. Inspect risk–coverage trade-offs on matched cases rather than celebrating a selective metric alone.

**Known terminology trap:** this is criterion-specific judge qualification. It is not probability calibration of a confidence score. A claim such as “predictions assigned confidence 0.8 are correct about 80% of the time” requires confidence/outcome observations and its own analysis; none are supplied here.

## Kata 91: zero false passes is not evidence of a 1% ceiling

**Predict:** C passes zero of twenty unsafe examples. Does that meet the illustrative target? If every additional independent unsafe example also yields no false pass, how many are needed for the fixed-sample zero-event upper bound to reach 1%?

For zero events in `n` independent Bernoulli trials, the probability of observing zero at event rate `p` is `(1-p)^n`. Inverting the one-sided tail at `alpha` gives `upper = 1 - alpha**(1/n)`. This is the zero-event case of exact binomial inversion; it is not the zero-width normal interval. [NIST binomial confidence-interval guidance](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm)

```python
import math

alpha, target = 0.05, 0.01
observed_unsafe = 20
upper = 1 - alpha ** (1 / observed_unsafe)
required = math.ceil(math.log(alpha) / math.log(1 - target))
assert required == 299
assert 1 - alpha ** (1 / required) <= target
assert 1 - alpha ** (1 / (required - 1)) > target
print(f"0/{observed_unsafe}: one-sided upper={upper:.2%}")
print(f"Fixed sample required if zero events: {required} independent unsafe examples")
```

??? success "Solution: HOLD qualification, and register the next study"
    The upper bound is about 13.91%, not 1%. The supplied evidence does not meet the target. With zero events throughout a **fixed-sample** study, 299 independent unsafe examples reach an upper bound below 1%; 299 total mixed examples are not enough unless all are eligible unsafe trials for this conditional event.

    This is a planning calculation, not permission to keep collecting until a convenient fixed-sample interval clears. If the team repeatedly checks the bound and stops on success, register a valid sequential method instead. A false pass changes the calculation; do not keep using the zero-event formula. The confidence procedure concerns repeated-sampling coverage, not a 95% posterior probability that this particular judge is safe.

    Twenty paraphrases of one incident do not establish twenty independent task draws. Repeated judge calls share case difficulty and can also share reviewer errors. Preserve customer/session/source groups and register the sampling unit. A count minimum cannot repair dependence, mislabeled references, task leakage or a shifted population.

    Enrich the unsafe class to obtain enough relevant examples, but distinguish that from hand-selecting only hard cases within the class. The population bound needs a justified sampling design for the target unsafe-response population. A convenience stress set is useful for finding failures; difficulty targeting does not make its unweighted binomial bound representative. Unequal inclusion or weighting requires an analysis qualified for that design. Keep cases used to tune prompts or abstention rules separate from untouched acceptance evidence. Use blinded independent labels and adjudication for consequential disagreements. The authored table demonstrates none of those collection safeguards.

**Pressure question:** “Can we disable abstention to reduce the queue?” Not on this evidence. That changes the decision policy and can turn the five abstained unsafe cases into false passes. Re-evaluate the changed policy rather than carrying over C's observed zero-event result.

## Kata 92: transport the error rates, not the headline accuracy

Assume a hypothetical day has 10,000 responses: 100 unsafe and 9,900 safe. For this calculation only, assume B and C retain exactly the class-conditional behavior in the authored table. Treat the resulting counts as **expected frequencies under that assumption**, not observations or forecasts validated against production.

Human review takes two minutes per queued item. Four reviewers each have six productive review hours that day. Both fail and abstain decisions enter the queue. No other work, absence, rework or service-time variation is included.

**Predict:** what are the expected unsafe pass counts, review volumes and nominal staffing loads? Does fitting inside mean daily capacity establish a response-time SLA?

```python
from fractions import Fraction

population = {"unsafe": 100, "safe": 9900}
rates = {
    "B": {"unsafe": (5, 15, 0), "safe": (175, 5, 0)},
    "C": {"unsafe": (0, 15, 5), "safe": (170, 5, 5)},
}
capacity_minutes = 4 * 6 * 60
for name, rows in rates.items():
    projected = {
        label: tuple(population[label] * Fraction(count, sum(counts)) for count in counts)
        for label, counts in rows.items()
    }
    unsafe_pass = projected["unsafe"][0]
    fail_queue = sum(values[1] for values in projected.values())
    abstain_queue = sum(values[2] for values in projected.values())
    queue = fail_queue + abstain_queue
    minutes = queue * 2
    print(name, "unsafe-pass=", unsafe_pass, "fail-review=", fail_queue,
          "abstain-review=", abstain_queue, "total-review=", queue,
          f"nominal-load={float(minutes / capacity_minutes):.2%}")
```

??? success "Solution: the queue and the risk both need their own evidence"
    B projects 25 unsafe pass decisions, 350 fail-review items and no abstentions. Of those 350 flagged responses, only 75 are unsafe: `75/350 ≈ 21.43%` precision, compared with `15/20 = 75%` in the risk-enriched teaching set. Prevalence changed; the class-conditional false-pass rate remains 25% under the stipulated assumption.

    C projects zero unsafe pass decisions, 350 fail-review items and 300 abstentions: 650 reviews. Its 1,300 review minutes use about 90.28% of the supplied 1,440-minute capacity. B uses 700 minutes, or 48.61%. These are planning figures, not evidence that C's true unsafe-pass probability is zero or that the reviewers will finish on time.

    Average capacity does not establish tail latency. Arrival bursts, service-time variation, repeat reviews, absences and other queues can create backlog. Nor is a human reviewer automatically correct. Measure queue age, completion, adjudication quality and recovery effort before relying on review as an operational control.

    The transport assumption may fail: the unsafe mix, languages, policy changes and task difficulty can shift within each reference class. Validate it on representative traffic. Do not import the enriched set's overall accuracy or flagged-response precision unchanged into production.

## Worked senior decision and must-hit rubric

**Decision:** hold automatic-acceptance qualification. A fails the criterion by design; B's observed conditional error is unacceptable for the supplied target; C has promising control behavior but insufficient independent evidence to establish the specified ceiling. Continue a bounded, already-authorized calibration/shadow study with no increase in application authority. Do not claim a production rollout from this classroom example.

The evaluation owner must register the criterion, sampling groups, target population, stopping rule, error bound and policy version; the annotation owner must supply independent labels and disagreement handling; the operations owner must validate the review queue and human outcomes. The release owner needs a current compatible packet before changing exposure. Those are proposed owner roles, not approvals obtained here.

| Must hit | Evidence in a satisfactory answer |
| --- | --- |
| Separate meanings of calibration | Judge error qualification distinguished from confidence-score calibration |
| Name denominators | `5/20`, `5/180`, `185/190` and `170/200` interpreted correctly |
| Respect abstention | Classification coverage, automatic acceptance and review load kept separate |
| Quantify uncertainty | 13.91% bound and 299 **unsafe independent** examples, with fixed-sample assumptions |
| Improve the data | Group separation, independent labels, tuning/acceptance boundaries and targeted sampling specified |
| Challenge transport | Production prevalence separated from within-class distribution stability |
| Connect to operations | Review capacity and reviewer quality treated as measured controls, not free perfect fallbacks |
| Bound the decision | No claimed model superiority, human validation, live deployment or production authority |

Passing this authored exercise is learning evidence, not certification of interview readiness. Continue with the [release capstone](capstone.md) to attach a decision memo to retained execution artifacts, and the [statistical method study](statistical-method-study.md) to investigate when a seemingly adequate sample count still yields a bad decision rule.
