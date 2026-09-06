"""Execute only fixed local coding controls in temporary workspaces; no model calls."""

import argparse
import difflib
import hashlib
import json
import math
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from cx_eval_lab.coding_patch_cases import (
    ACCEPTANCE,
    BUILTINS,
    CONTRACT,
    HARNESS,
    ORIGINAL,
    VISIBLE,
    output_matches,
)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def _sha(source):
    return hashlib.sha256(source).hexdigest()


def _protected():
    return {'harness.py': HARNESS, 'visible.json': json.dumps(VISIBLE, sort_keys=True),
            'acceptance.json': json.dumps(ACCEPTANCE, sort_keys=True)}


def _inventory():
    return {'contract': digest(CONTRACT), 'candidates': {name: _sha(code.encode()) for name, code in BUILTINS.items()},
            'protected': {name: _sha(source.encode()) for name, source in _protected().items()},
            'inputs': digest([VISIBLE, ACCEPTANCE]),
            'engine': {name: _sha(Path(__file__).with_name(name).read_bytes())
                       for name in ('coding_patch_study.py', 'coding_patch_cases.py')},
            'interpreter': {'sha256': _sha(Path(sys.executable).resolve().read_bytes()), 'version': sys.version}}


def _prepare(root, name):
    for filename, source in {**_protected(), 'candidate.py': BUILTINS[name]}.items():
        (root / filename).write_text(source, encoding='utf-8')
    if name == 'protected-test-edit':
        (root / 'acceptance.json').write_text('[]', encoding='utf-8')


def _files(root):
    return {str(path.relative_to(root)): {'source': path.read_text(encoding='utf-8'),
                                        'sha256': _sha(path.read_bytes())}
            for path in sorted(root.rglob('*')) if path.is_file()}


def _hashes(files):
    return {name: row['sha256'] for name, row in files.items()}


def _streams(value):
    return value.decode('utf-8', errors='replace') if isinstance(value, bytes) else value or ''


def _suite(root, name, cases):
    command = [sys.executable, '-I', '-S', 'harness.py', f'{name}.json']
    started = time.monotonic()
    try:
        done = subprocess.run(command, cwd=root, env={}, capture_output=True, text=True,
                              timeout=2, check=False)
        code, stdout, stderr, status = done.returncode, done.stdout, done.stderr, 'completed'
    except (subprocess.TimeoutExpired, OSError) as error:
        code, stdout, stderr = None, _streams(getattr(error, 'stdout', None)), _streams(getattr(error, 'stderr', None))
        status = 'timeout' if isinstance(error, subprocess.TimeoutExpired) else 'launch_error'
    results = []
    if status == 'completed':
        try:
            parsed = json.loads(stdout)
            valid = (isinstance(parsed, list) and len(parsed) == len(cases)
                     and all(isinstance(row, dict) and set(row) == {'name', 'output_passed', 'input_unchanged', 'passed',
                                                                   'actual', 'error_type', 'input_before', 'input_after'}
                             and row['name'] == case['name']
                             and all(type(row[key]) is bool for key in ('output_passed', 'input_unchanged', 'passed'))
                             and (row['error_type'] is None or isinstance(row['error_type'], str))
                             and digest(row['input_before']) == digest(case['rows'])
                             and row['output_passed'] == (
                                 row['error_type'] == case['raises'] if 'raises' in case else
                                 row['error_type'] is None and output_matches(row['actual'], case['expected']))
                             and row['input_unchanged'] == (digest(row['input_after']) == digest(case['rows']))
                             and row['passed'] == (row['output_passed'] and row['input_unchanged'])
                             for row, case in zip(parsed, cases, strict=True)))
            if not valid or code != (0 if all(row['passed'] for row in parsed) else 1):
                raise ValueError('invalid suite results')
            results = parsed
        except (ValueError, TypeError, KeyError):
            status = 'invalid_results'
    return {'name': name, 'status': status, 'registered': len(cases),
            'passed': sum(row['passed'] for row in results), 'results': results,
            'returncode': code, 'stdout': stdout, 'stderr': stderr,
            'command': ['<current-python>', *command[1:]], 'duration_seconds': time.monotonic() - started}


def _control(name):
    expected = {**{key: _sha(value.encode()) for key, value in _protected().items()},
                'candidate.py': _sha(BUILTINS[name].encode())}
    suites, files, after = [], {}, {}
    for suite, cases in (('visible', VISIBLE), ('acceptance', ACCEPTANCE)):
        # Each suite gets a fresh workspace as well as a fresh interpreter.
        with tempfile.TemporaryDirectory(prefix='coding-patch-') as directory:
            root = Path(directory)
            _prepare(root, name)
            files = _files(root)
            before = _hashes(files)
            if before != expected:
                after = before
                break
            result = _suite(root, suite, cases)
            after = _hashes(_files(root))
            suites = [*suites, {**result, 'files_before': before, 'files_after': after}]
            if after != expected:
                break
    integrity = before == expected and after == expected
    accepted = integrity and len(suites) == 2 and all(
        row['status'] == 'completed' and row['passed'] == row['registered'] for row in suites)
    completed = len(suites) == 2 and all(row['status'] == 'completed' for row in suites)
    baseline = {**_protected(), 'candidate.py': ORIGINAL}
    diff = ''.join(''.join(difflib.unified_diff(baseline[key].splitlines(True), value['source'].splitlines(True),
                                             fromfile=f'before/{key}', tofile=f'after/{key}'))
                   for key, value in files.items() if key in baseline)
    status = 'integrity_blocked' if not integrity else 'incomplete' if not completed else 'accepted' if accepted else 'rejected'
    return {'name': name, 'status': status,
            'files': files, 'diff': diff, 'protected_before': {key: expected[key] for key in _protected()},
            'protected_after': {key: after.get(key) for key in _protected()}, 'suites': suites}


def _conforms(controls):
    if [row['status'] for row in controls] != ['rejected', 'rejected', 'accepted', 'rejected', 'integrity_blocked']:
        return False
    patterns = ((True, False, False, True, True, True, True, True), (False,) * 8,
                (True,) * 8, (True, False, False, False, False, False, True, True))
    for control, acceptance in zip(controls[:4], patterns, strict=True):
        visible = (False, False) if control['name'] == 'input-mutating' else (True, True)
        if len(control['suites']) != 2 or any(
            suite['status'] != 'completed' or tuple(row['passed'] for row in suite['results']) != pattern
            or suite['files_before'] != suite['files_after']
            for suite, pattern in zip(control['suites'], (visible, acceptance), strict=True)):
            return False
    blocked = controls[4]
    expected_after = {**blocked['protected_before'], 'acceptance.json': _sha(b'[]')}
    return (blocked['status'] == 'integrity_blocked' and blocked['suites'] == []
            and blocked['protected_after'] == expected_after
            and _hashes(blocked['files']) == {**expected_after, 'candidate.py': _sha(BUILTINS[blocked['name']].encode())})


def run_study():
    inventory = _inventory()
    controls = [_control(name) for name in BUILTINS]
    report = {'schema': 'coding-patch-study-v1', 'contract': CONTRACT,
              'evidence_kind': 'executed_fixed_hand_authored_python_patches',
              'source_inventory': inventory, 'controls': controls,
              'conformance_passed': _conforms(controls),
              'deployment_authorized': False,
              'limitations': 'Public teaching fixtures, not hidden tests or independent acceptance. '
              'Fixed hand-authored controls, not coding-agent or model performance. Temporary workspaces '
              'and isolated Python flags are not an OS sandbox; never run untrusted code with this harness. '
              'Hashes detect consistency, not authenticated provenance. Durations are observed, not stability guarantees. '
              'The eight acceptance fixtures do not cover every invalid input container shape.'}
    return {**report, 'report_hash': digest(report)}


def _normalized(value):
    return {**{key: item for key, item in value.items() if key != 'report_hash'},
            'controls': [{**control, 'suites': [
                {key: item for key, item in suite.items() if key != 'duration_seconds'}
                for suite in control['suites']]} for control in value['controls']]}


def verify_study(report):
    if not isinstance(report, dict) or digest(report.get('source_inventory')) != digest(_inventory()):
        raise ValueError('source inventory differs from current builtins/interpreter')
    if report.get('report_hash') != digest({key: value for key, value in report.items() if key != 'report_hash'}):
        raise ValueError('report hash mismatch')
    try:
        durations = [suite['duration_seconds'] for control in report['controls'] for suite in control['suites']]
        if any(type(value) not in (int, float) or not math.isfinite(value) or value < 0 for value in durations):
            raise ValueError('invalid recorded duration')
        normalized = _normalized(report)
    except (KeyError, TypeError) as error:
        raise ValueError('malformed report') from error
    # Never execute any source, command, path, or case supplied in the report.
    if digest(normalized) != digest(_normalized(run_study())):
        raise ValueError('builtin replay differs from retained report')
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('choose a new output path')
    report = run_study()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as destination:
        json.dump(report, destination, indent=2, allow_nan=False)
        destination.write('\n')
    return 0 if report['conformance_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
