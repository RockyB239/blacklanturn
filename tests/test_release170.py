import unittest

import test_reliability_release165


class BrowseReleaseGate(unittest.TestCase):
    def test_browse_requires_new_installer_and_exact_policy(self):
        prior = test_reliability_release165.Release165Gate()
        gate = prior.gate()
        marker = dict(prior.marker(), browse_patch='shelf-tools-1', installer_min_version='1.0.53')
        self.assertEqual(gate.prepare_policy(marker, None), '1.0.53')
        self.assertEqual(gate.prepare_policy(prior.marker(), None), '1.0.52')
        for altered in ({'installer_min_version': '1.0.52'}, {'browse_patch': 'future'}, {'reliability_patch': None}):
            with self.subTest(altered=altered), self.assertRaises(ValueError):
                gate.prepare_policy(dict(marker, **altered), None)
