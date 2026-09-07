"""Executed local recovery-to-rollback control, never a promotion experiment."""

import argparse
import json
import multiprocessing
import os
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory

from cx_eval_lab.durable_completion import CompletionJournal
from cx_eval_lab.durable_controller import DurableController
from cx_eval_lab.durable_world import DurableCampaign
from cx_eval_lab.evidence import canonical_hash
from cx_eval_lab.exposure_control import ExposureState, ExposureWindow, Observation
from cx_eval_lab.exposure_study import (
    FaultInjectedCandidate,
    build_window_plan,
    case_from_plan,
)
from cx_eval_lab.source_provenance import capture_source_inputs
from cx_eval_lab.window_completion import inspect_window
from cx_eval_lab.window_registration import WindowRegistry

POLICY = {'campaign_id': 'recovery-decision', 'max_actions': 2,
          'currency_caps': {'USD': 90000, 'EUR': 90000}}


def _worker(campaign_path, journal_path, member, manifest, ready, release):
    campaign = DurableCampaign.open(campaign_path, **POLICY)
    journal = CompletionJournal.open(journal_path, campaign)

    class InterruptedCandidate:
        name = FaultInjectedCandidate.name

        def run(self, request, tools):
            result = FaultInjectedCandidate('wrong_order').run(request, tools)
            ready.set()  # Actual tools have returned; no case artifact is persisted.
            release.wait(30)
            return result

    journal.execute(case_from_plan(member['case']), InterruptedCandidate(),
                    namespace=member['candidate_namespace'], manifest_digest=manifest)


def run_study():
    sources = capture_source_inputs(Path(__file__).resolve().parents[1])
    manifest = canonical_hash({'sources': sources, 'fault': 'wrong_order',
                               'interruption': 'after_tools_before_agent_return'})[7:]
    with TemporaryDirectory() as directory:
        root = Path(directory)
        campaign = DurableCampaign.initialize(root / 'effects.sqlite', **POLICY)
        journal = CompletionJournal.initialize(root / 'completion.sqlite', campaign)
        registry = WindowRegistry.initialize(root / 'windows.sqlite', campaign)
        state = ExposureState('candidate', 'baseline', stage='expanded', percent=25)
        controller = DurableController.initialize(root / 'controller.sqlite', state)
        plan = registry.register(build_window_plan(state, 1, 'wrong_order',
            execution_namespace='study', manifest_digest=manifest, effect_backend='durable'))
        member = next(row for row in plan['members'] if row['served'] == 'candidate')
        context = multiprocessing.get_context('spawn')
        ready, release = context.Event(), context.Event()
        child = context.Process(target=_worker, args=(campaign.path, journal.path, member,
                                                      manifest, ready, release))
        child.start()
        try:
            if not ready.wait(15):
                raise RuntimeError('worker did not reach the registered interruption boundary')
            child.kill()
            child.join(10)
            if child.is_alive() or child.exitcode != -9:
                raise RuntimeError('worker termination was not confirmed')
            process = {'supervisor_pid': os.getpid(), 'worker_pid': child.pid,
                       'exitcode': child.exitcode, 'boundary': 'after_tools_before_agent_return'}
        finally:
            if child.is_alive():
                child.kill()
                child.join(10)
        campaign = DurableCampaign.open(campaign.path, **POLICY)
        joined = inspect_window(WindowRegistry.open(registry.path, campaign),
            CompletionJournal.open(journal.path, campaign), 'study', 1, manifest_digest=manifest)
        # This is an incident-only rollback input, NOT a complete window comparison.
        violations = [row for row in joined['members'] if row['observed_wrong_order_violation'] is True]
        if len(violations) != 1 or violations[0]['status'] != 'no_completion':
            raise ValueError('expected one observed violation with missing completion')
        incident = ExposureWindow('incident-window-1', state.candidate, state.baseline,
            state.revision, 0, 10, tuple(Observation(row['customer_id'], None, None, True,
                10, canonical_hash(row)) for row in violations))
        receipt = controller.apply('wrong-order-incident', state, incident, now=10)
        reopened = DurableController.open(controller.path)
        replay = reopened.apply('wrong-order-incident', state, incident, now=10)
        budget = campaign.snapshot()
        passed = (receipt == replay and receipt['decision']['reason'] == 'hard_violation'
                  and reopened.state().stage == 'rolled_back' and reopened.state().revision == 1
                  and budget['charged_actions'] == 1 and len(joined['members']) == 40)
        return {'study': 'recovery-decision-v1', 'evidence_kind': 'executed_local_process_control',
            'sources': sources, 'manifest_digest': manifest, 'process': process,
            'joined': joined, 'budget': budget, 'receipt': receipt, 'reopened_receipt': replay,
            'controller_state': asdict(reopened.state()), 'conformance_passed': passed,
            'decision_scope': 'observed_incident_rollback_only_not_full_window_promotion',
            'deployment_authorized': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('choose a new output path')
    report = run_study()
    with args.output.open('x') as handle:
        json.dump(report, handle, indent=2, allow_nan=False)
        handle.write('\n')
    if not report['conformance_passed']:
        parser.exit(1, 'recovery control failed; inspect retained evidence\n')


if __name__ == '__main__':
    main()
