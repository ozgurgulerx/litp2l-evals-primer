"""Source checks use operator paths and verify bytes, not version labels alone."""

import hashlib
import subprocess
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from tests.test_evidence_spine import make_manifest


def digest(content):
    return 'sha256:' + hashlib.sha256(content).hexdigest()


class SourceProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name).resolve()
        (self.root / 'cx_eval_lab').mkdir()
        for name, value in (('cx_eval_lab/__init__.py', '# fixture\n'),
                            ('cx_eval_lab/evaluators.py', 'VERSION = 1\n'),
                            ('pyproject.toml', '# fixture\n'), ('uv.lock', '# fixture\n'),
                            ('dataset.json', '[]\n'), ('policy.json', '{}\n')):
            (self.root / name).write_text(value)
        self.git('init', '-q')
        self.git('add', '.')
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                 '-c', 'commit.gpgsign=false', 'commit', '-qm', 'fixture')
        self.revision = self.git('rev-parse', 'HEAD').strip()
        self.inputs = {'dataset': self.root / 'dataset.json', 'policy': self.root / 'policy.json'}

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.root), *args], check=True,
                              text=True, capture_output=True).stdout

    def manifest(self):
        from cx_eval_lab.source_provenance import capture_source_inputs
        return replace(make_manifest(), code_revision=self.revision,
                       input_hashes=(*capture_source_inputs(self.root),
                           *((name, digest(path.read_bytes())) for name, path in self.inputs.items())))

    def verify(self, manifest=None, **changes):
        from cx_eval_lab.source_provenance import verify_sources
        return verify_sources(manifest or self.manifest(), root=self.root,
                              input_files=changes.pop('input_files', self.inputs),
                              expected_revision=changes.pop('expected_revision', self.revision),
                              expected_evaluator_version=changes.pop(
                                  'expected_evaluator_version', 'refund-evaluators-v1'))

    def test_complete_source_and_inputs_match_committed_revision(self):
        result = self.verify()
        self.assertEqual(self.revision, result.code_revision)
        self.assertEqual(6, len(result.verified_hashes))
        self.assertFalse(result.deployment_authorized)

    def test_changed_source_bytes_and_changed_inputs_reject(self):
        manifest = self.manifest()
        for name in ('cx_eval_lab/evaluators.py', 'dataset.json'):
            path = self.root / name
            old = path.read_bytes()
            path.write_bytes(old + b'changed')
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.verify(manifest)
            path.write_bytes(old)

    def test_recording_dirty_source_hash_does_not_make_it_committed(self):
        (self.root / 'cx_eval_lab/evaluators.py').write_text('VERSION = 2\n')
        with self.assertRaisesRegex(ValueError, 'committed'):
            self.verify(self.manifest())

    def test_extra_or_missing_python_file_rejects(self):
        manifest = self.manifest()
        path = self.root / 'cx_eval_lab/extra.py'
        path.write_text('# injected\n')
        with self.assertRaisesRegex(ValueError, 'source inventory'):
            self.verify(manifest)
        with self.assertRaisesRegex(ValueError, 'source inventory'):
            self.verify(self.manifest())
        path.unlink()
        (self.root / 'cx_eval_lab/evaluators.py').unlink()
        with self.assertRaises(ValueError):
            self.verify(manifest)

    def test_legacy_manifest_and_unknown_input_names_fail_closed(self):
        with self.assertRaisesRegex(ValueError, 'source inventory'):
            self.verify(replace(make_manifest(), code_revision=self.revision))
        manifest = self.manifest()
        with self.assertRaisesRegex(ValueError, 'input mapping'):
            self.verify(replace(manifest, input_hashes=(*manifest.input_hashes,
                         ('../../private', digest(b'secret')))))
        with self.assertRaisesRegex(ValueError, 'input mapping'):
            self.verify(manifest, input_files={'dataset': self.inputs['dataset']})

    def test_wrong_revision_and_evaluator_label_reject(self):
        for changes in ({'expected_revision': '0' * 40},
                        {'expected_revision': 'working-tree-unpinned'},
                        {'expected_evaluator_version': 'different'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.verify(**changes)

    def test_unrelated_document_edits_do_not_dirty_registered_code(self):
        (self.root / 'notes.md').write_text('unrelated local documentation')
        self.assertFalse(self.verify().deployment_authorized)

    def test_git_replacement_refs_cannot_change_the_expected_revision_tree(self):
        (self.root / 'cx_eval_lab/evaluators.py').write_text('VERSION = 2\n')
        self.git('add', '.')
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                 '-c', 'commit.gpgsign=false', 'commit', '-qm', 'different source')
        replacement = self.git('rev-parse', 'HEAD').strip()
        # Only this disposable fixture repository is changed.
        self.git('update-ref', 'HEAD', self.revision)
        self.git('replace', self.revision, replacement)
        with self.assertRaisesRegex(ValueError, 'committed'):
            self.verify(self.manifest())

    def test_source_and_input_symlinks_are_rejected(self):
        manifest = self.manifest()
        target = self.root / 'cx_eval_lab/evaluators.py'
        target.unlink()
        target.symlink_to(self.root / 'dataset.json')
        with self.assertRaises(ValueError):
            self.verify(manifest)
        target.unlink()
        target.write_text('VERSION = 1\n')
        link = self.root / 'link.json'
        link.symlink_to(self.root / 'dataset.json')
        with self.assertRaises(ValueError):
            self.verify(manifest, input_files={**self.inputs, 'dataset': link})

    def test_operator_input_with_symlinked_parent_is_rejected(self):
        alias = self.root / 'alias'
        alias.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.verify(input_files={**self.inputs, 'dataset': alias / 'dataset.json'})


if __name__ == '__main__':
    unittest.main()
