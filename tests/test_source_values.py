"""Operator-pinned JSON values are not file paths or self-issued source authority."""

from dataclasses import asdict, replace
import unittest

from cx_eval_lab.evidence import canonical_hash
from cx_eval_lab.source_provenance import verify_sources
from tests import test_source_provenance as fixture


class SourceValueTests(unittest.TestCase):
    setUp = fixture.SourceProvenanceTests.setUp
    git = fixture.SourceProvenanceTests.git

    def manifest(self, values=None):
        base = fixture.SourceProvenanceTests.manifest(self)
        return replace(base, input_hashes=(*base.input_hashes,
            *((name, canonical_hash(value)) for name, value in (values or {}).items())))

    def verify(self, manifest, *, values=None, files=None):
        return verify_sources(manifest, root=self.root,
            input_files=self.inputs if files is None else files, input_values=values,
            expected_revision=self.revision, expected_evaluator_version='refund-evaluators-v1')

    def test_mixed_file_bytes_and_json_values_match_registered_hashes(self):
        values = {'design': {'arms': ['baseline', 'candidate'], 'count': 2, 'active': True},
                  'optional': None}
        result = self.verify(self.manifest(values), values=values)
        self.assertEqual(8, len(result.verified_hashes))
        self.assertEqual(canonical_hash(values['design']), dict(result.verified_hashes)['design'])
        self.assertFalse(result.deployment_authorized)
        self.assertEqual(['baseline', 'candidate'], values['design']['arms'])

    def test_omitted_values_preserve_legacy_file_mapping(self):
        self.assertEqual(6, len(self.verify(self.manifest()).verified_hashes))

    def test_missing_extra_overlapping_or_source_keys_reject(self):
        manifest = self.manifest({'design': {'count': 2}})
        for values, files in ((None, self.inputs), ({}, self.inputs),
                ({'design': {'count': 2}, 'extra': 0}, self.inputs),
                ({'design': {'count': 2}, 'dataset': []}, self.inputs),
                ({'design': {'count': 2}}, {'dataset': self.inputs['dataset']}),
                ({'design': {'count': 2}, 'source:cx_eval_lab/__init__.py': '# fixture'}, self.inputs),
                ({'design': {'count': 2}}, {**self.inputs, 'source:pyproject.toml': self.root / 'pyproject.toml'})):
            with self.subTest(values=values, files=files), self.assertRaises(ValueError):
                self.verify(manifest, values=values, files=files)

    def test_nonfinite_opaque_and_malformed_operator_maps_reject(self):
        manifest = self.manifest({'design': {'count': 2}})
        for value in (float('nan'), float('inf'), {'nested': [float('-inf')]},
                      {'opaque': object()}, b'bytes', {'set'}, {1: 'nonstring key'}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.verify(manifest, values={'design': value})
        for values, files in (([], self.inputs), ('design', self.inputs),
                              ({'design': {}}, [])):
            with self.subTest(values=values, files=files), self.assertRaises(ValueError):
                self.verify(manifest, values=values, files=files)

    def test_changed_values_and_file_json_hash_confusion_reject(self):
        values = {'design': {'count': 2}}
        manifest = self.manifest(values)
        with self.assertRaises(ValueError):
            self.verify(manifest, values={'design': {'count': 3}})
        # File bytes include a newline. Canonical JSON for [] is a different hash.
        with self.assertRaises(ValueError):
            self.verify(self.manifest(), values={'dataset': []}, files={'policy': self.inputs['policy']})

    def test_manifest_input_labels_are_never_interpreted_as_paths(self):
        values = {'../../private/operator-secret': {'safe': 'operator supplied value'}}
        result = self.verify(self.manifest(values), values=values)
        self.assertIn('../../private/operator-secret', dict(result.verified_hashes))

    def test_native_judge_uses_actual_hash_preimage_not_config_only(self):
        from cx_eval_lab.openai_judge import JudgeConfig, OpenAIResponsesJudge, NATIVE_CRITERION, _schema
        from tests.test_openai_judge import FakeClient
        for criterion in ('refund_customer_message_truth_v1', NATIVE_CRITERION):
            judge = OpenAIResponsesJudge(JudgeConfig(model='pinned-fixture-model', criterion_id=criterion),
                                         FakeClient())
            identity = judge.configuration_identity
            self.assertEqual(judge.configuration_hash, canonical_hash(identity))
            self.assertNotEqual(judge.configuration_hash, canonical_hash(asdict(judge.config)))
            values = {'native-judge-config': identity}
            self.assertFalse(self.verify(self.manifest(values), values=values).deployment_authorized)
            with self.assertRaises(ValueError):
                self.verify(self.manifest(values), values={'native-judge-config': asdict(judge.config)})
            identity['config']['model'] = 'external mutation'
            self.assertEqual('pinned-fixture-model', judge.configuration_identity['config']['model'])
            if criterion != NATIVE_CRITERION:
                old_config = {key: value for key, value in asdict(judge.config).items() if key != 'criterion_id'}
                self.assertEqual(judge.configuration_hash, canonical_hash({'config': old_config,
                    'schema': _schema(), 'adapter': judge.evaluator_version,
                    'endpoint': 'https://api.openai.com/v1', 'max_retries': 0}))


if __name__ == '__main__':
    unittest.main()
