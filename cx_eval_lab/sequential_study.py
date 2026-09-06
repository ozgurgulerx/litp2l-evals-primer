"""Exact finite-horizon stopping probabilities for a Bernoulli loss experiment.

The tested null is p >= margin; promotion requires evidence p < margin.
This special case assumes a perfect baseline and independent, truthful labels.
"""

import argparse
from functools import lru_cache
import json
import math
from pathlib import Path

from cx_eval_lab.evidence import canonical_hash
from cx_eval_lab.statistical_study import _counts, _probability


METHODS = ('fixed_final', 'repeated_fixed', 'bonferroni', 'likelihood_ratio')
LOOKS = tuple(range(50, 501, 50))


def _design(method, looks, margin, alternative, alpha):
    if method not in METHODS:
        raise ValueError('unregistered stopping method')
    if not isinstance(looks, (tuple, list)) or not looks:
        raise ValueError('pre-registered look schedule is required')
    for n in looks:
        _counts(0, n)
    if tuple(sorted(set(looks))) != tuple(looks):
        raise ValueError('looks must be strictly increasing and unique')
    for name, value in (('margin', margin), ('alternative', alternative), ('alpha', alpha)):
        _probability(value, name)
    if not 0 < alternative < margin < 1 or not 0 < alpha < 1:
        raise ValueError('require 0 < alternative < margin < 1 and 0 < alpha < 1')


def log_evidence(k, n, *, margin=0.03, alternative=0.01):
    """Log of a fixed-alternative Bernoulli likelihood-ratio test martingale."""
    _counts(k, n)
    _design('likelihood_ratio', (n,), margin, alternative, 0.05)
    return k * (math.log(alternative) - math.log(margin)) + (n-k) * (
        math.log1p(-alternative) - math.log1p(-margin))


@lru_cache(maxsize=1024)
def _null_masses(n, margin):
    return tuple(math.comb(n, j) * margin**j * (1-margin)**(n-j) for j in range(n+1))


def should_stop(method, k, n, *, looks=LOOKS, margin=0.03, alternative=0.01, alpha=0.05):
    _design(method, looks, margin, alternative, alpha)
    _counts(k, n)
    if n not in looks or (method == 'fixed_final' and n != looks[-1]):
        return False
    if method == 'likelihood_ratio':
        return log_evidence(k, n, margin=margin, alternative=alternative) >= -math.log(alpha)
    tail_probability = math.fsum(_null_masses(n, margin)[:k+1])
    threshold = alpha / len(looks) if method == 'bonferroni' else alpha
    return tail_probability <= threshold


def enumerate_stopping(*, method='likelihood_ratio', looks=LOOKS, true_loss=0.03,
                       margin=0.03, alternative=0.01, alpha=0.05, hidden_loss_probability=0.0):
    """Propagate only not-yet-promoted paths; no Monte Carlo sampling error."""
    _design(method, looks, margin, alternative, alpha)
    _probability(true_loss, 'true loss')
    _probability(hidden_loss_probability, 'hidden loss probability')
    observed_loss = true_loss * (1-hidden_loss_probability)
    alive = (1.0,)
    crossings = []
    for n in range(1, looks[-1]+1):
        next_mass = tuple(math.fsum((alive[k] * (1-observed_loss) if k < len(alive) else 0.0,
                                     alive[k-1] * observed_loss if k else 0.0)) for k in range(n+1))
        if n in looks:
            stops = tuple(should_stop(method, k, n, looks=looks, margin=margin,
                                     alternative=alternative, alpha=alpha) for k in range(n+1))
            crossed = math.fsum(mass for mass, stop in zip(next_mass, stops) if stop)
            crossings.append({'n': n, 'first_promotion_probability': crossed,
                              'largest_promoting_loss_count': max((k for k, stop in enumerate(stops)
                                                                  if stop), default=None)})
            alive = tuple(0.0 if stop else mass for mass, stop in zip(next_mass, stops))
        else:
            alive = next_mass
    promotion = math.fsum(row['first_promotion_probability'] for row in crossings)
    remaining = math.fsum(alive)
    return {'method': method, 'looks': list(looks), 'true_loss': true_loss,
            'observed_loss': observed_loss, 'hidden_loss_probability': hidden_loss_probability,
            'margin': margin, 'alternative': alternative, 'alpha': alpha,
            'null_true': true_loss >= margin,
            'promotion_probability': promotion, 'no_promotion_probability': remaining,
            'false_promotion_probability': promotion if true_loss >= margin else 0.0,
            'expected_observations_until_stop_or_horizon': math.fsum(
                [row['n'] * row['first_promotion_probability'] for row in crossings]
                + [looks[-1] * remaining]),
            'first_crossings': crossings, 'unpromoted_final_loss_masses': list(alive),
            'authority': 'lab_only'}


def dependent_counterexample():
    """One latent Bernoulli outcome copied to all 500 rows; marginal p is unchanged."""
    p = 0.03
    good_path_promotes = any(should_stop('likelihood_ratio', 0, n) for n in LOOKS)
    bad_path_promotes = any(should_stop('likelihood_ratio', n, n) for n in LOOKS)
    return {'marginal_loss': p, 'independent_units': 1, 'duplicated_rows': 500,
            'false_promotion_probability': (1-p)*good_path_promotes + p*bad_path_promotes,
            'mechanism': 'one Bernoulli variable copied across every observation; independence is violated'}


def study_report():
    return {'schema': 'sequential-study-v1', 'evidence_kind': 'exact_synthetic_path_enumeration',
            'deployment_authorized': False,
            'source_hash': canonical_hash(Path(__file__).read_text()),
            'studies': [enumerate_stopping(method=method, true_loss=p)
                        for p in (0.01, 0.03, 0.04) for method in METHODS],
            'biased_labels': enumerate_stopping(true_loss=0.1, hidden_loss_probability=1.0),
            'dependent_labels': dependent_counterexample()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.exit(2, 'Choose a new output path; previous evidence is retained.\n')
    report = study_report()
    with args.output.open('x') as handle:
        handle.write(json.dumps(report, indent=2, allow_nan=False) + '\n')


if __name__ == '__main__':
    main()
