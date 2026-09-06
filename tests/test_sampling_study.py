"""Design-based sampling tests use independent finite-ID enumeration."""

import copy
import itertools
import json
import math
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path


class SamplingStudyTests(unittest.TestCase):
    def test_worked_weighted_disagreement_is_uncertainty_hold(self):
        from cx_eval_lab.sampling_study import run_study
        report = run_study()
        estimate = report['worked_example']['estimate']
        self.assertEqual(.375, estimate['raw_failure_rate'])
        self.assertEqual(.1875, estimate['ht_failure_rate'])
        self.assertEqual(.1875, estimate['stratum_weighted_failure_rate'])
        self.assertEqual((.1875, .5625), (estimate['interval']['lower'], estimate['interval']['upper']))
        self.assertEqual({'raw_point': 'illustrative_block', 'weighted_point': 'illustrative_clear',
                          'interval': 'hold'}, estimate['decisions'])
        self.assertFalse(report['deployment_authorized'])

    def test_full_id_enumeration_confirms_cells_inclusion_and_expectations(self):
        from cx_eval_lab.sampling_study import example_inputs, run_study
        inputs = example_inputs()
        report = run_study()
        for name, allocation in inputs['allocations'].items():
            strata = sorted(allocation)
            groups = {h: [r['unit_id'] for r in inputs['frame'] if r['stratum'] == h] for h in strata}
            combinations = [list(itertools.combinations(groups[h], allocation[h])) for h in strata]
            counts, inclusions, raw_total, weighted_total = Counter(), Counter(), 0., 0.
            for selection in itertools.product(*combinations):
                failures = tuple(sum(inputs['outcomes'][i] for i in selected) for selected in selection)
                counts[failures] += 1
                for selected in selection:
                    inclusions.update(selected)
                raw_total += sum(failures) / sum(allocation.values())
                weighted_total += sum(len(groups[h]) * failures[j] / allocation[h] for j, h in enumerate(strata)) / 16
            design = report['designs'][name]
            total = sum(counts.values())
            self.assertEqual(5544 if name == 'proportional' else 495, total)
            self.assertEqual(total, design['sample_set_count'])
            actual = {tuple(cell['failures'][h] for h in strata): cell['multiplicity'] for cell in design['cells']}
            self.assertEqual(dict(counts), actual)
            for h in strata:
                for unit in groups[h]:
                    self.assertAlmostEqual(allocation[h] / len(groups[h]), inclusions[unit] / total)
            self.assertAlmostEqual(.25, weighted_total / total)
            self.assertAlmostEqual(.25 if name == 'proportional' else 5 / 12, raw_total / total)
            self.assertAlmostEqual(raw_total / total, design['summary']['expected_raw_failure_rate'])
            self.assertAlmostEqual(weighted_total / total, design['summary']['expected_ht_failure_rate'])

    def test_independent_65_population_interval_coverage(self):
        from cx_eval_lab.sampling_study import count_interval, run_study
        for name, n0, n1 in (('proportional', 6, 2), ('enriched', 4, 4)):
            minimum = 1.
            for m0, m1 in itertools.product(range(13), range(5)):
                covered = 0
                total = math.comb(12, n0) * math.comb(4, n1)
                for x0, x1 in itertools.product(range(n0 + 1), range(n1 + 1)):
                    def choose(n, k):
                        return math.comb(n, k) if 0 <= k <= n else 0
                    multiplicity = choose(m0, x0) * choose(12 - m0, n0 - x0) * choose(m1, x1) * choose(4 - m1, n1 - x1)
                    interval = count_interval({'routine': 12, 'risk': 4}, {'routine': n0, 'risk': n1},
                                              {'routine': x0, 'risk': x1}, .05)
                    if interval['lower'] <= (m0 + m1) / 16 <= interval['upper']:
                        covered += multiplicity
                minimum = min(minimum, covered / total)
            self.assertGreaterEqual(minimum, .95)
            qualification = run_study()['designs'][name]['qualification']
            self.assertEqual(65, qualification['population_count'])
            self.assertAlmostEqual(minimum, qualification['minimum_coverage'])

    def test_estimator_has_only_selected_labels_and_strict_membership_probabilities(self):
        from cx_eval_lab.sampling_study import estimate_sample, example_inputs, run_study
        inputs = example_inputs()
        rows = run_study()['worked_example']['rows']
        allocation = inputs['allocations']['enriched']
        for mode in ('missing-pi', 'wrong-pi', 'zero-pi', 'bool-pi', 'nan-pi', 'none-label', 'int-label',
                     'duplicate', 'wrong-stratum', 'unknown-id', 'missing-row', 'zero-support', 'missing-stratum', 'truth-leak'):
            sample, plan, frame = copy.deepcopy(rows), dict(allocation), copy.deepcopy(inputs['frame'])
            if mode == 'missing-pi':
                del sample[0]['pi']
            elif mode in ('wrong-pi', 'zero-pi', 'bool-pi', 'nan-pi'):
                sample[0]['pi'] = {'wrong-pi': .9, 'zero-pi': 0, 'bool-pi': True, 'nan-pi': float('nan')}[mode]
            elif mode in ('none-label', 'int-label'):
                sample[0]['failure'] = None if mode == 'none-label' else 1
            elif mode == 'duplicate':
                sample[0] = sample[1]
            elif mode == 'wrong-stratum':
                sample[0]['stratum'] = 'routine' if sample[0]['stratum'] == 'risk' else 'risk'
            elif mode == 'unknown-id':
                sample[0]['unit_id'] = 'not-in-frame'
            elif mode == 'missing-row':
                sample.pop()
            elif mode == 'zero-support':
                plan['routine'] = 0
            elif mode == 'missing-stratum':
                del plan['routine']
            else:
                frame[0]['failure'] = False
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                estimate_sample(frame, plan, sample)

    def test_census_and_extreme_labels_are_not_zero_uncertainty_shortcuts(self):
        from cx_eval_lab.sampling_study import estimate_sample
        frame = [{'unit_id': f'u{i}', 'stratum': 'one'} for i in range(4)]
        for failure in (False, True):
            rows = [{'unit_id': r['unit_id'], 'stratum': 'one', 'failure': failure, 'pi': 1.} for r in frame]
            full = estimate_sample(frame, {'one': 4}, rows)
            self.assertEqual(float(failure), full['interval']['lower'])
            self.assertEqual(float(failure), full['interval']['upper'])
            partial = estimate_sample(frame, {'one': 1}, [{**rows[0], 'pi': .25}])
            self.assertLess(partial['interval']['lower'], partial['interval']['upper'])

    def test_replay_rejects_coherent_result_tampering_and_preserves_inputs(self):
        from cx_eval_lab.evidence import canonical_hash
        from cx_eval_lab.sampling_study import example_inputs, replay_study, run_study
        inputs = example_inputs()
        before = copy.deepcopy(inputs)
        report = run_study(inputs)
        self.assertEqual(before, inputs)
        self.assertEqual(report, replay_study(report))
        report['designs']['enriched']['summary']['expected_ht_failure_rate'] = .1
        report['report_hash'] = canonical_hash({k: v for k, v in report.items() if k != 'report_hash'})
        with self.assertRaises(ValueError):
            replay_study(report)

    def test_cli_exclusive_output(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'study.json'
            cmd = [sys.executable, '-m', 'cx_eval_lab.sampling_study', '--output', str(target)]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            self.assertEqual(0, result.returncode, result.stderr)
            before = target.read_bytes()
            self.assertEqual('finite-stratified-sampling-v1', json.loads(before)['schema'])
            self.assertNotEqual(0, subprocess.run(cmd, capture_output=True, check=False).returncode)
            self.assertEqual(before, target.read_bytes())

    def test_exact_interval_boundary_does_not_round_unsafe_rate_down_to_threshold(self):
        from cx_eval_lab.sampling_study import estimate_sample
        frame = [{'unit_id': f'u{i}', 'stratum': 'only'} for i in range(3)]
        rows = [{**r, 'failure': i == 0, 'pi': 1} for i, r in enumerate(frame)]
        result = estimate_sample(frame, {'only': 3}, rows, threshold=.3333333333333333)
        self.assertEqual('block', result['decisions']['interval'])

    def test_retained_artifact_matches_complete_reexecution(self):
        from cx_eval_lab.sampling_study import replay_study, run_study
        path = Path(__file__).resolve().parents[1] / 'docs/assets/sampling-study-v1.json'
        artifact = json.loads(path.read_text())
        self.assertEqual(run_study(), artifact)
        self.assertEqual(artifact, replay_study(artifact))
