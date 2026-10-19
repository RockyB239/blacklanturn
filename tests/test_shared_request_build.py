"""The common overlay may change only the reviewed dependency source file."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('request_build', ROOT/'tools/build_release.py')
build = importlib.util.module_from_spec(spec); spec.loader.exec_module(build)
KEY = 'addons/script.module.jurialmunkey/resources/modules/jurialmunkey/reqapi.py'


class SharedRequestBuild(unittest.TestCase):
    def overlay(self, data):
        method = getattr(build, 'apply_shared_requests', None)
        self.assertTrue(callable(method), 'No common request overlay in the reproducible build')
        method(data)

    def test_both_known_bases_receive_exact_same_code_without_changing_settings_or_youtube(self):
        for edition in ('general', 'apple'):
            data = {KEY:(ROOT/f'compatibility/shared-requests/{edition}-before.py').read_bytes(),
                    'userdata/guisettings.xml':b'unchanged playback',
                    'addons/plugin.video.youtube/platform.py':b'unchanged workaround'}
            expected=dict(data);expected[KEY]=(ROOT/'compatibility/shared-requests/reqapi.py').read_bytes()
            self.overlay(data);self.assertEqual(data,expected)

    def test_unknown_base_fails_without_partial_mutation(self):
        data={KEY:b'unknown future dependency', 'userdata/keep':b'original'};before=dict(data)
        self.assertTrue(callable(getattr(build,'apply_shared_requests',None)))
        with self.assertRaisesRegex((AssertionError,ValueError), 'request'):build.apply_shared_requests(data)
        self.assertEqual(data,before)


if __name__ == '__main__':unittest.main()
