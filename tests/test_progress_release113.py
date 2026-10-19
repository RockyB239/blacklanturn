"""A repaired file or a successful local simulation is not device acceptance."""
import copy
import errno
from pathlib import Path
import unittest
from unittest import mock
from tools import verify_release


class ProgressAcceptance(unittest.TestCase):
    def setUp(self):
        self.manifest = {'patch': 'event-progress-3', 'variants': {
            '6.7.90': {'after_sha256': 'a' * 64},
            '6.7.92': {'after_sha256': 'b' * 64}}}
        def device(version):
            return {'version': version,
                    'candidate_sha256': self.manifest['variants'][version]['after_sha256'],
                    'loaded_trace_sha256': 'c' * 64, 'expected_trace_sha256': 'c' * 64,
                    'diagnostics_removed': True, 'other_sources_preserved': True,
                    'settings_authorizations_preserved': True,
                    'watched_history_unchanged': True, 'unrelated_progress_unchanged': True,
                    'ordinary_restart': True, 'quiet_home': True,
                    'cold_seek_stop': {'absolute_callback_ms': 750000,
                        'seconds_after_player': 0.7, 'av_ready': False,
                        'outgoing_progress': 12.5, 'cloud_reads_matched': 2,
                        'cloud_error_seconds': 0.5},
                    'saved_resume': {'native_duration_replaced_fallback': True,
                        'cloud_reads_matched': 2, 'cloud_error_seconds': 0.9},
                    'pause_stop': {'paused_seconds': 4, 'native_drift_seconds': 0,
                        'cloud_reads_matched': 2, 'cloud_error_seconds': 0.01},
                    'zero_seek_stop': {'absolute_callback_ms': 0,
                        'selected_resume_id_matched': True, 'delete_status': 204,
                        'absent_cloud_reads': 2, 'invalid_zero_pause_sent': False}}
        self.receipt = {'patch': 'event-progress-3', 'passed': True,
            'devices': {'fire': device('6.7.92'), 'mac': device('6.7.92'),
                        'apple_tv': device('6.7.92')}}

    def gate(self, receipt=None):
        gate = getattr(verify_release, 'verify_umbrella_progress_acceptance', None)
        self.assertTrue(callable(gate), 'No source-bound native progress acceptance gate')
        gate(self.receipt if receipt is None else receipt, self.manifest)

    def test_accepts_completed_actual_device_contracts(self):
        self.gate()

    def test_release_entrypoint_requires_new_progress_proof_before_artifacts(self):
        target = verify_release.ROOT / "compatibility/umbrella-progress/native-verification.json"
        original_read = Path.read_text

        def missing_receipt(path, *args, **kwargs):
            if path == target:
                raise FileNotFoundError(errno.ENOENT, "Missing native acceptance receipt", str(target))
            return original_read(path, *args, **kwargs)

        with mock.patch.object(Path, 'read_text', missing_receipt), self.assertRaises(FileNotFoundError) as caught:
            verify_release.verify(Path("/nonexistent-blacklanturn-artifacts"))
        self.assertEqual(Path(caught.exception.filename), target)

    def test_missing_apple_proof_cannot_be_called_all_device_acceptance(self):
        receipt = copy.deepcopy(self.receipt); del receipt['devices']['apple_tv']
        with self.assertRaises(AssertionError): self.gate(receipt)

    def test_other_candidate_or_unloaded_trace_cannot_pass(self):
        for key in ('candidate_sha256', 'loaded_trace_sha256'):
            receipt = copy.deepcopy(self.receipt)
            receipt['devices']['mac'][key] = 'd' * 64
            with self.subTest(key=key), self.assertRaises(AssertionError): self.gate(receipt)

    def test_old_variant_cannot_approve_packaged_92_on_any_device(self):
        for name in self.receipt['devices']:
            receipt = copy.deepcopy(self.receipt)
            receipt['devices'][name].update(version='6.7.90', candidate_sha256='a' * 64)
            with self.subTest(device=name), self.assertRaises(AssertionError): self.gate(receipt)

    def test_stale_or_rejected_cold_progress_cannot_pass(self):
        for key, value in [('absolute_callback_ms', 750), ('outgoing_progress', 0),
                           ('cloud_reads_matched', 1), ('cloud_error_seconds', 20),
                           ('cloud_error_seconds', float('nan')), ('seconds_after_player', 6)]:
            receipt = copy.deepcopy(self.receipt)
            receipt['devices']['fire']['cold_seek_stop'][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(AssertionError): self.gate(receipt)

    def test_zero_requires_selected_record_204_and_settled_absence(self):
        for key, value in [('delete_status', 422), ('selected_resume_id_matched', False),
                           ('absent_cloud_reads', 1), ('invalid_zero_pause_sent', True)]:
            receipt = copy.deepcopy(self.receipt)
            receipt['devices']['apple_tv']['zero_seek_stop'][key] = value
            with self.subTest(key=key), self.assertRaises(AssertionError): self.gate(receipt)

    def test_missing_preservation_or_cleanup_blocks_release(self):
        for key in ('diagnostics_removed', 'other_sources_preserved',
                    'settings_authorizations_preserved', 'watched_history_unchanged',
                    'unrelated_progress_unchanged', 'ordinary_restart', 'quiet_home'):
            receipt = copy.deepcopy(self.receipt); receipt['devices']['mac'][key] = False
            with self.subTest(key=key), self.assertRaises(AssertionError): self.gate(receipt)


if __name__ == '__main__': unittest.main()
