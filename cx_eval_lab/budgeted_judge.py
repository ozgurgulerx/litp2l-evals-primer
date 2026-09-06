"""Optional judge admission wrapper. It does not budget agent executions."""

import json
from dataclasses import asdict, dataclass, replace

from cx_eval_lab.campaign_budget import CampaignLedger, usd_to_micro
from cx_eval_lab.evidence import canonical_hash
from cx_eval_lab.semantic import SemanticJudge, SemanticJudgment, SemanticRequest


@dataclass(frozen=True)
class BudgetedSemanticJudge:
    inner: SemanticJudge
    ledger: CampaignLedger

    @property
    def evaluator_version(self):
        return self.inner.evaluator_version

    @property
    def configuration_hash(self):
        # Admission policy is recorded separately; it does not alter the rubric.
        return self.inner.configuration_hash

    def _abstain(self, reason, audit, judgment=None):
        return SemanticJudgment('abstain', reason,
            None if judgment is None else judgment.runtime_evidence,
            None if judgment is None else judgment.provider_audit_json,
            json.dumps({'status': 'held', 'reason': reason,
                        'campaign_policy_hash': self.ledger.policy.content_hash, **audit},
                       sort_keys=True, allow_nan=False))

    def evaluate(self, request):
        try:
            if not isinstance(request, SemanticRequest) or not request.invocation_id:
                raise ValueError('evaluator-owned invocation ID required')
            request_hash = canonical_hash({'criterion': request.criterion_id,
                                           'evidence': json.loads(request.evidence_json)})
            admission = self.ledger.reserve(request.invocation_id, request_hash, self.configuration_hash)
        except Exception as error:
            return self._abstain('campaign_admission_error', {'error_type': type(error).__name__})
        if not admission.admitted:
            return self._abstain(admission.reason, {'admission': asdict(admission)})
        try:
            # Arm/trial identity is for the ledger, never provider-visible evidence.
            judgment = self.inner.evaluate(replace(request, invocation_id=None))
            if not isinstance(judgment, SemanticJudgment):
                raise TypeError('judge returned invalid contract')
        except Exception as error:
            judgment = SemanticJudgment('abstain', f'judge_error:{type(error).__name__}')
        try:
            runtime = judgment.runtime_evidence
            estimate = usd_to_micro(None if runtime is None else runtime.cost_usd)
            receipt = self.ledger.finalize(request.invocation_id, estimate,
                json.dumps(asdict(judgment), sort_keys=True, allow_nan=False))
        except Exception as error:
            return self._abstain('campaign_finalization_error', {
                'admission': asdict(admission), 'error_type': type(error).__name__,
                'uncommitted_judgment': asdict(judgment)}, judgment)
        return replace(judgment, campaign_audit_json=json.dumps({
            'status': 'recorded', 'admission': asdict(admission), 'receipt': receipt}, sort_keys=True))
