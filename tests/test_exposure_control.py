"""Simulation routing must respect evidence identity, maturity and stop rules."""

from dataclasses import replace
import unittest


def window(state, identity='w1', start=0, end=10, failures=0, violation=False, mature_at=10):
    from cx_eval_lab.exposure_control import Observation, ExposureWindow
    rows = tuple(Observation(f'user-{i}', True, i >= failures, violation and i == 0,
                             mature_at, f'artifact-{identity}-{i}') for i in range(10))
    return ExposureWindow(identity, state.candidate, state.baseline, state.revision, start, end, rows)


class ExposureControlTests(unittest.TestCase):
    def test_shadow_canary_expansion_and_stable_nested_cohorts(self):
        from cx_eval_lab.exposure_control import ExposureState, transition, route
        initial = ExposureState('candidate-v1', 'baseline-v1')
        self.assertEqual({'baseline'}, {route(initial, f'user-{i}', now=0) for i in range(100)})
        canary = transition(initial, window(initial), now=10).state
        self.assertEqual(('canary', 5), (canary.stage, canary.percent))
        expanded = transition(canary, window(canary, 'w2', 10, 20, mature_at=20), now=20).state
        self.assertEqual(('expanded', 25), (expanded.stage, expanded.percent))
        low = {i for i in range(1000) if route(canary, f'user-{i}', now=20) == 'candidate'}
        high = {i for i in range(1000) if route(expanded, f'user-{i}', now=20) == 'candidate'}
        self.assertTrue(low and low < high)
        self.assertEqual(low, {i for i in range(1000) if route(canary, f'user-{i}', now=20) == 'candidate'})

    def test_immature_and_small_windows_do_not_expand(self):
        from cx_eval_lab.exposure_control import ExposureState, transition
        state = ExposureState('candidate-v1', 'baseline-v1')
        self.assertEqual(state.stage, transition(state, window(state, mature_at=20), now=10).state.stage)
        small = replace(window(state), observations=window(state).observations[:1])
        self.assertEqual('insufficient_mature_evidence', transition(state, small, now=10).reason)

    def test_hard_violation_rolls_back_without_waiting_for_label_maturity(self):
        from cx_eval_lab.exposure_control import ExposureState, transition, route
        state = ExposureState('candidate-v1', 'baseline-v1', stage='canary', percent=5)
        decision = transition(state, window(state, violation=True, mature_at=100), now=10)
        self.assertEqual(('rolled_back', 0), (decision.state.stage, decision.state.percent))
        self.assertEqual('baseline', route(decision.state, 'customer', now=10))
        self.assertFalse(decision.deployment_authorized)

    def test_quality_restriction_needs_two_new_healthy_windows_and_explicit_resume(self):
        from cx_eval_lab.exposure_control import ExposureState, transition
        state = ExposureState('candidate-v1', 'baseline-v1', stage='expanded', percent=25)
        restricted = transition(state, window(state, failures=3), now=10).state
        self.assertEqual(('restricted', 5), (restricted.stage, restricted.percent))
        first = transition(restricted, window(restricted, 'w2', 10, 20, mature_at=20), now=20).state
        self.assertEqual('restricted', first.stage)
        second = transition(first, window(first, 'w3', 20, 30, mature_at=30), now=30).state
        self.assertEqual('restricted', second.stage)
        resumed = transition(second, window(second, 'w4', 30, 40, mature_at=40), now=40,
                             resume=True).state
        self.assertEqual('canary', resumed.stage)

    def test_replay_overlap_and_changed_revision_cannot_create_new_evidence(self):
        from cx_eval_lab.exposure_control import ExposureState, transition
        state = ExposureState('candidate-v1', 'baseline-v1')
        used = window(state)
        state = transition(state, used, now=10).state
        self.assertEqual('replayed_window', transition(state, used, now=10).reason)
        stale_revision = replace(used, window_id='renamed')
        self.assertEqual('wrong_exposure_revision', transition(state, stale_revision, now=10).reason)
        overlap = window(state, 'overlap', 5, 15, mature_at=15)
        self.assertEqual('overlapping_window', transition(state, overlap, now=15).reason)

    def test_candidate_drift_and_stale_telemetry_stop_exposure(self):
        from cx_eval_lab.exposure_control import ExposureState, transition
        state = ExposureState('candidate-v1', 'baseline-v1', stage='canary', percent=5)
        drift = replace(window(state), candidate='different-candidate')
        self.assertEqual('rolled_back', transition(state, drift, now=10).state.stage)
        self.assertEqual('stale_telemetry', transition(state, window(state), now=1000).reason)

    def test_rolled_back_state_cannot_be_reactivated_by_green_results(self):
        from cx_eval_lab.exposure_control import ExposureState, transition
        state = ExposureState('candidate-v1', 'baseline-v1', stage='rolled_back', percent=0)
        self.assertEqual(state, transition(state, window(state), now=10, resume=True).state)

    def test_router_deadline_stops_candidate_without_a_new_window(self):
        from cx_eval_lab.exposure_control import ExposureState, route
        state = ExposureState('candidate-v1', 'baseline-v1', stage='canary', percent=5, last_end=10)
        self.assertEqual({'baseline'}, {route(state, f'user-{i}', now=41) for i in range(1000)})
        with self.assertRaises(TypeError):
            route(state, 'customer')

    def test_pending_cohort_cannot_drop_missing_labels_or_be_skipped(self):
        from cx_eval_lab.exposure_control import ExposureState, transition
        state = ExposureState('candidate-v1', 'baseline-v1')
        original = window(state)
        pending = replace(original, observations=(*original.observations[:-1],
                          replace(original.observations[-1], candidate_pass=None)))
        held = transition(state, pending, now=10).state
        truncated = replace(pending, observations=pending.observations[:-1])
        self.assertEqual('pending_cohort_mismatch', transition(held, truncated, now=10).reason)
        self.assertEqual('pending_cohort_mismatch', transition(held, window(held, 'new', 10, 20), now=20).reason)
        self.assertEqual('canary', transition(held, original, now=10).state.stage)

    def test_simulation_decision_cannot_claim_deployment_authority(self):
        from cx_eval_lab.exposure_control import ExposureState, ExposureDecision
        with self.assertRaises(TypeError):
            ExposureDecision(ExposureState('c', 'b'), 'test', deployment_authorized=True)

    def test_executed_study_routes_cloned_worlds_and_reaches_all_stages(self):
        from cx_eval_lab.exposure_study import run_study
        study = run_study()
        self.assertEqual(['canary', 'expanded', 'restricted', 'restricted', 'canary',
                          'rolled_back', 'rolled_back'],
                         [window['decision']['state']['stage'] for window in study['windows']])
        self.assertFalse(study['deployment_authorized'])
        self.assertEqual(0, study['windows'][0]['served_candidate'])
        self.assertGreater(study['windows'][1]['served_candidate'], 0)
        self.assertEqual(0, study['windows'][-1]['served_candidate'])
        for window in study['windows']:
            for artifact in window['artifacts']:
                self.assertIn('orders', artifact['baseline'])
                if artifact['candidate'] is not None:
                    self.assertIn('orders', artifact['candidate'])

    def test_equally_bad_arms_do_not_earn_expansion(self):
        from cx_eval_lab.exposure_control import ExposureState, transition
        state = ExposureState('candidate-v1', 'baseline-v1', stage='canary', percent=5)
        sample = window(state, failures=10)
        sample = replace(sample, observations=tuple(replace(row, baseline_pass=False)
                                                    for row in sample.observations))
        self.assertEqual('restricted', transition(state, sample, now=10).state.stage)


if __name__ == '__main__':
    unittest.main()
