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
        self.assertEqual({'baseline'}, {route(initial, f'user-{i}') for i in range(100)})
        canary = transition(initial, window(initial), now=10).state
        self.assertEqual(('canary', 5), (canary.stage, canary.percent))
        expanded = transition(canary, window(canary, 'w2', 10, 20, mature_at=20), now=20).state
        self.assertEqual(('expanded', 25), (expanded.stage, expanded.percent))
        low = {i for i in range(1000) if route(canary, f'user-{i}') == 'candidate'}
        high = {i for i in range(1000) if route(expanded, f'user-{i}') == 'candidate'}
        self.assertTrue(low and low < high)
        self.assertEqual(low, {i for i in range(1000) if route(canary, f'user-{i}') == 'candidate'})

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
        self.assertEqual('baseline', route(decision.state, 'customer'))
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


if __name__ == '__main__':
    unittest.main()
