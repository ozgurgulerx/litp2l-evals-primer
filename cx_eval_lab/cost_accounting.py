"""Selected per-packet agent/judge estimates; not a billing reconciliation."""

import json

from cx_eval_lab.artifacts import replay_packet
from cx_eval_lab.campaign_budget import usd_to_micro


def summarize_packet_costs(packet, *, trusted_calibration_hashes=frozenset()):
    """Validate retained grades first; do not change application cost gate inputs.

Denied judge invocations incur no NEW dispatch in this packet. Prior attempts
may still cost money: inspect their campaign ledger rather than summing packets
across retries. Provider reports and caller trust remain external assumptions.
"""
    replay_packet(packet, trusted_calibration_hashes=trusted_calibration_hashes)
    agent_costs, judge_costs = [], []
    not_dispatched = 0
    for artifact in packet['trial_artifacts']:
        payload = artifact['payload']
        agent_costs.append(usd_to_micro(payload['cost_usd']))
        stage = payload.get('semantic_stage') or {}
        judgment = stage.get('judgment')
        campaign = json.loads(judgment['campaign_audit_json']) \
            if judgment and judgment.get('campaign_audit_json') else {}
        denied = (campaign.get('reason') == 'campaign_admission_error'
                  or campaign.get('admission', {}).get('admitted') is False)
        if judgment is None or denied:
            not_dispatched += 1
            continue
        runtime = judgment.get('runtime_evidence') or {}
        judge_costs.append(usd_to_micro(runtime.get('cost_usd')))
    known_agent = sum(value for value in agent_costs if value is not None)
    known_judge = sum(value for value in judge_costs if value is not None)
    unknown = sum(value is None for value in (*agent_costs, *judge_costs))
    return {'agent_known_micro_usd': known_agent, 'judge_known_micro_usd': known_judge,
            'known_subtotal_micro_usd': known_agent + known_judge,
            'unknown_component_count': unknown, 'judge_not_dispatched_trials': not_dispatched,
            'complete_selected_estimate_micro_usd': None if unknown else known_agent + known_judge,
            'measurement_kind': packet['manifest']['measurement_kind'],
            'scope': 'new agent/judge dispatch estimates in this packet; excludes prior attempts, '
                     'tool/hosting/storage/human costs and invoice reconciliation',
            'deployment_authorized': False}
