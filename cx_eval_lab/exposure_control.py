"""Simulation-only exposure state machine. Never grants deployment authority.

Quality thresholds exercise control flow; they are not statistical release tests.
An external trusted collector owns observations and candidate/baseline identities.
"""

from dataclasses import dataclass, field, replace
import hashlib
from cx_eval_lab.evidence import canonical_hash


PERCENTAGES = {'shadow': 0, 'canary': 5, 'expanded': 25, 'restricted': 5, 'rolled_back': 0}


def _identifier(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('nonempty identity required')


def _clock(value):
    if type(value) is not int or value < 0:
        raise ValueError('simulation time must be a nonnegative integer')


@dataclass(frozen=True)
class ExposureState:
    candidate: str
    baseline: str
    stage: str = 'shadow'
    percent: int = 0
    revision: int = 0
    healthy_windows: int = 0
    last_end: int = 0
    used_windows: tuple[str, ...] = ()
    used_artifacts: tuple[str, ...] = ()
    pending_window: str | None = None
    expires_at: int = 120

    def __post_init__(self):
        _identifier(self.candidate)
        _identifier(self.baseline)
        if self.candidate == self.baseline:
            raise ValueError('candidate and baseline identities must differ')
        if self.stage not in PERCENTAGES or type(self.percent) is not int or self.percent != PERCENTAGES[self.stage]:
            raise ValueError('exposure percentage must match the registered stage')
        for value in (self.revision, self.healthy_windows, self.last_end, self.expires_at):
            _clock(value)
        if self.pending_window is not None:
            _identifier(self.pending_window)
        for key in ('used_windows', 'used_artifacts'):
            values = tuple(getattr(self, key))
            for value in values:
                _identifier(value)
            if len(values) != len(set(values)):
                raise ValueError('consumed evidence must be unique')
            object.__setattr__(self, key, values)


@dataclass(frozen=True)
class Observation:
    customer_id: str
    baseline_pass: bool | None
    candidate_pass: bool | None
    hard_violation: bool
    mature_at: int
    artifact_id: str

    def __post_init__(self):
        _identifier(self.customer_id)
        _identifier(self.artifact_id)
        _clock(self.mature_at)
        if type(self.hard_violation) is not bool:
            raise ValueError('hard violation must be boolean')
        if any(value is not None and type(value) is not bool
               for value in (self.baseline_pass, self.candidate_pass)):
            raise ValueError('outcomes must be boolean or explicitly missing')


@dataclass(frozen=True)
class ExposureWindow:
    window_id: str
    candidate: str
    baseline: str
    exposure_revision: int
    start: int
    end: int
    observations: tuple[Observation, ...]

    def __post_init__(self):
        for value in (self.window_id, self.candidate, self.baseline):
            _identifier(value)
        for value in (self.start, self.end, self.exposure_revision):
            _clock(value)
        if self.end <= self.start:
            raise ValueError('window must have positive duration')
        object.__setattr__(self, 'observations', tuple(self.observations))
        for key in ('customer_id', 'artifact_id'):
            values = [getattr(row, key) for row in self.observations]
            if len(values) != len(set(values)):
                raise ValueError('window requires distinct customer and artifact identities')


@dataclass(frozen=True)
class ExposureDecision:
    state: ExposureState
    reason: str
    deployment_authorized: bool = field(default=False, init=False)


def route(state, customer_id, *, now):
    """Stable nested customer cohorts for one candidate identity."""
    _identifier(customer_id)
    _clock(now)
    if now >= state.expires_at or now < state.last_end or now - state.last_end > 30:
        return 'baseline'
    digest = hashlib.sha256(f'{state.candidate}\0{customer_id}'.encode()).digest()
    bucket = int.from_bytes(digest[:8], 'big') % 10000
    return 'candidate' if bucket < state.percent * 100 else 'baseline'


def transition(state, window, *, now, resume=False):
    """Advance only from complete fresh windows; safety stops precede maturity."""
    _clock(now)
    if type(resume) is not bool:
        raise ValueError('resume must be an explicit simulation operator choice')
    if state.stage == 'rolled_back':
        return ExposureDecision(state, 'rollback_latched')
    rollback = replace(state, stage='rolled_back', percent=0, revision=state.revision + 1,
                       healthy_windows=0)
    if (window.candidate, window.baseline) != (state.candidate, state.baseline):
        return ExposureDecision(rollback, 'deployment_identity_mismatch')
    # A newly reported severe incident can refer to an older exposure revision.
    if any(row.hard_violation for row in window.observations):
        return ExposureDecision(rollback, 'hard_violation')
    if window.end > now or now - window.end > 30:
        return ExposureDecision(rollback, 'stale_telemetry')
    if now >= state.expires_at:
        return ExposureDecision(rollback, 'campaign_expired')
    if window.window_id in state.used_windows:
        return ExposureDecision(state, 'replayed_window')
    if window.exposure_revision != state.revision:
        return ExposureDecision(state, 'wrong_exposure_revision')
    if window.start < state.last_end:
        return ExposureDecision(state, 'overlapping_window')
    if any(row.artifact_id in state.used_artifacts for row in window.observations):
        return ExposureDecision(state, 'reused_artifact')
    membership = canonical_hash((window.window_id, window.candidate, window.baseline,
        window.exposure_revision, window.start, window.end,
        sorted((row.customer_id, row.mature_at) for row in window.observations)))
    if state.pending_window is not None and state.pending_window != membership:
        return ExposureDecision(state, 'pending_cohort_mismatch')
    held = replace(state, pending_window=membership)
    if any(row.mature_at > now for row in window.observations):
        return ExposureDecision(held, 'waiting_for_maturity')
    if any(row.baseline_pass is None or row.candidate_pass is None for row in window.observations):
        return ExposureDecision(held, 'missing_mature_label')
    if len(window.observations) < 2:
        return ExposureDecision(held, 'insufficient_mature_evidence')
    # Illustrative paired point difference, NOT a non-inferiority confidence bound.
    loss = sum(int(row.baseline_pass) - int(row.candidate_pass)
               for row in window.observations) / len(window.observations)
    candidate_rate = sum(row.candidate_pass for row in window.observations) / len(window.observations)
    updated = replace(state, revision=state.revision + 1, last_end=window.end, pending_window=None,
                      used_windows=(*state.used_windows, window.window_id),
                      used_artifacts=(*state.used_artifacts, *(row.artifact_id for row in window.observations)))
    if loss > 0.10 or candidate_rate < 0.90:
        stage = 'shadow' if state.stage == 'shadow' else 'restricted'
        return ExposureDecision(replace(updated, stage=stage, percent=PERCENTAGES[stage],
                                        healthy_windows=0), 'illustrative_quality_regression')
    if loss > 0:
        return ExposureDecision(replace(updated, healthy_windows=0), 'guard_band_hold')
    healthy = state.healthy_windows + 1
    if state.stage == 'restricted':
        stage = 'canary' if resume and healthy >= 2 else 'restricted'
    else:
        stage = {'shadow': 'canary', 'canary': 'expanded', 'expanded': 'expanded'}[state.stage]
    return ExposureDecision(replace(updated, stage=stage, percent=PERCENTAGES[stage],
                                    healthy_windows=healthy),
                            'simulation_resume' if state.stage == 'restricted' and stage == 'canary'
                            else 'simulation_healthy_window')
