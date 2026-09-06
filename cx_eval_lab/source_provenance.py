"""Local source/input consistency, not signed provenance or execution attestation."""

import hashlib
import re
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path


MAX_FILE_BYTES = 64 * 1024 * 1024
FIXED_INPUTS = ('pyproject.toml', 'uv.lock')


def _hash(content):
    return 'sha256:' + hashlib.sha256(content).hexdigest()


def _read(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('registered input must be a regular non-symlink file')
    with path.open('rb') as stream:
        content = stream.read(MAX_FILE_BYTES + 1)
    if len(content) > MAX_FILE_BYTES:
        raise ValueError('registered input exceeds verification size limit')
    return content


def _git(root, *arguments):
    try:
        return subprocess.run(['git', '--no-replace-objects', '-C', str(root), *arguments], check=True,
                              capture_output=True, timeout=15).stdout
    except (OSError, subprocess.SubprocessError) as error:
        raise ValueError('cannot verify local git source identity') from error


def local_revision(root):
    root = Path(root).resolve()
    top = Path(_git(root, 'rev-parse', '--show-toplevel').decode().strip()).resolve()
    if top != root:
        raise ValueError('source root must be the repository root')
    return _git(root, 'rev-parse', '--verify', 'HEAD').decode().strip()


def _source_names(root):
    package = root / 'cx_eval_lab'
    if package.is_symlink() or not package.is_dir():
        raise ValueError('source inventory requires a local package directory')
    paths = tuple(package.rglob('*'))
    if any(path.is_symlink() for path in paths):
        raise ValueError('source inventory cannot contain symlinks')
    names = tuple(sorted(path.relative_to(root).as_posix() for path in paths
                         if path.is_file() and path.suffix == '.py'))
    if 'cx_eval_lab/__init__.py' not in names:
        raise ValueError('source inventory requires package initialization')
    return tuple(sorted((*names, *FIXED_INPUTS)))


def capture_source_inputs(root):
    """Record current bytes, including dirty files; verification checks commitment."""
    root = Path(root).resolve()
    return tuple((f'source:{name}', _hash(_read(root / name))) for name in _source_names(root))


@dataclass(frozen=True)
class SourceVerification:
    code_revision: str
    evaluator_version: str
    verified_hashes: tuple[tuple[str, str], ...]
    deployment_authorized: bool = field(default=False, init=False)


def verify_sources(manifest, *, root, input_files, expected_revision, expected_evaluator_version):
    """Check all registered files against operator paths and committed source bytes.

    Caller controls root, expected identities and input_files. Manifest labels
    never become filesystem paths. Run in a controlled, non-mutating checkout.
    This does not inspect loaded bytecode or installed third-party dependencies.
    """
    root = Path(root).resolve()
    if (not isinstance(expected_revision, str)
            or not re.fullmatch(r'(?:[0-9a-f]{40}|[0-9a-f]{64})', expected_revision)
            or manifest.code_revision != expected_revision
            or local_revision(root) != expected_revision):
        raise ValueError('code revision does not match operator identity and checkout')
    if not expected_evaluator_version or manifest.evaluator_version != expected_evaluator_version:
        raise ValueError('evaluator version differs from operator identity')
    current = dict(capture_source_inputs(root))
    registered = dict(manifest.input_hashes)
    if {key for key in registered if key.startswith('source:')} != set(current):
        raise ValueError('registered source inventory differs from local source inventory')
    tracked = _git(root, 'ls-tree', '-r', '--name-only', '-z', expected_revision,
                   '--', 'cx_eval_lab', *FIXED_INPUTS).decode().split('\0')
    expected_names = {f'source:{name}' for name in tracked
                      if name in FIXED_INPUTS or name.endswith('.py')}
    if expected_names != set(current):
        raise ValueError('committed source inventory differs from local source inventory')
    if set(input_files) != set(registered) - set(current):
        raise ValueError('operator input mapping must cover exactly the registered inputs')
    for key, actual in current.items():
        if registered[key] != actual:
            raise ValueError('registered source hash differs from local bytes')
        name = key.removeprefix('source:')
        if _hash(_git(root, 'show', f'{expected_revision}:{name}')) != actual:
            raise ValueError('source bytes differ from committed revision')
    observed_inputs = tuple((name, _hash(_read(path))) for name, path in input_files.items())
    if any(registered[name] != digest for name, digest in observed_inputs):
        raise ValueError('registered input hash differs from operator file bytes')
    return SourceVerification(expected_revision, expected_evaluator_version,
                              tuple(sorted((*current.items(), *observed_inputs))))


def verify_packet_inputs(packet, *, dataset_path, policy_path):
    """Bind complete case and agent input records; call after file-hash verification.

    This is not reconstruction of an outer release decision or executed state.
    """
    from cx_eval_lab.dataset import load_refund_cases
    from cx_eval_lab.evidence import canonical_hash
    from cx_eval_lab.gate import load_gate_policy
    cases = {case.case_id: case for case in load_refund_cases(dataset_path)}
    if not cases or packet['manifest']['dataset_version'] != next(iter(cases.values())).dataset_version:
        raise ValueError('dataset version differs from manifest')
    if packet['manifest']['policy_version'] != load_gate_policy(policy_path).policy_version:
        raise ValueError('release policy version differs from manifest')
    seen = set()
    for artifact in packet['trial_artifacts']:
        payload = artifact['payload']
        case_id = payload['case']['case_id']
        if case_id not in cases or canonical_hash(payload['case']) != canonical_hash(cases[case_id].to_dict()):
            raise ValueError('retained dataset case differs from operator dataset')
        if canonical_hash(payload['agent_input']) != canonical_hash(asdict(cases[case_id].agent_input)):
            raise ValueError('retained agent input differs from operator dataset')
        seen.add(case_id)
    if seen != set(cases):
        raise ValueError('retained case membership differs from operator dataset')
    return len(cases)
