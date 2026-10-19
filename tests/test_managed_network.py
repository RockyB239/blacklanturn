"""Managed common dependency protection uses the existing installer boundaries."""
import hashlib
import inspect
import json
from pathlib import Path
import sqlite3
import unittest
import zipfile
import test_managed_umbrella as umbrella_fixture

ROOT = Path(__file__).resolve().parents[1]
ADDON = 'script.module.jurialmunkey'
PREFIX = 'addons/' + ADDON + '/'


class ManagedNetworkTests(unittest.TestCase):
    def setUp(self):
        self.fixture = umbrella_fixture.ManagedUmbrellaTests(); self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.m = self.fixture.m
        with zipfile.ZipFile(ROOT/'compatibility/shared-requests/upstream-general-0.2.35.zip') as z:
            self.files = {n.removeprefix(ADDON+'/'): z.read(n) for n in z.namelist()}
        self.files['resources/modules/jurialmunkey/reqapi.py'] = (ROOT/'compatibility/shared-requests/reqapi.py').read_bytes()
        manifest = {'addon_id': ADDON, 'version': '0.2.35', 'patch': 'request-reliability-privacy-1',
                    'installed_request_hashes': [hashlib.sha256((ROOT/'compatibility/shared-requests'/name).read_bytes()).hexdigest() for name in ('general-before.py','reqapi.py')],
                    'files': {n: hashlib.sha256(b).hexdigest() for n,b in self.files.items()}}
        (self.fixture.resources/'managed-network.json').write_text(json.dumps(manifest))

    def archive(self, change=None):
        with zipfile.ZipFile(self.fixture.archive()) as z:
            data = {n:z.read(n) for n in z.namelist()}
        data.update({PREFIX+n:b for n,b in self.files.items()})
        if change: change(data)
        path = self.fixture.root/'network-build.zip'
        with zipfile.ZipFile(path, 'w') as z:
            for n,b in data.items(): z.writestr(n,b)
        return path

    def invoke(self, method, *args, **kwargs):
        for key in kwargs:
            self.assertIn(key, inspect.signature(method).parameters, 'Missing managed network protection')
        return method(*args, **kwargs)

    def test_exact_complete_shared_tree_passes(self):
        with zipfile.ZipFile(self.archive()) as z:
            self.invoke(self.m.verify_archive, z, umbrella=True, network=True)

    def test_old_missing_foreign_and_future_dependency_fail_before_cleanup(self):
        for mode in ('old', 'missing', 'extra', 'future'):
            def change(data):
                path = PREFIX+'resources/modules/jurialmunkey/reqapi.py'
                if mode == 'old': data[path] = (ROOT/'compatibility/shared-requests/general-before.py').read_bytes()
                if mode == 'missing': del data[path]
                if mode == 'extra': data[PREFIX+'foreign.py'] = b'pass'
                if mode == 'future': data[PREFIX+'addon.xml'] = data[PREFIX+'addon.xml'].replace(b'0.2.35', b'0.2.36')
            with self.subTest(mode=mode), zipfile.ZipFile(self.archive(change)) as z:
                self.assertIn('network', inspect.signature(self.m.verify_archive).parameters)
                with self.assertRaises(self.m.ProtectionError): self.m.verify_archive(z, umbrella=True, network=True)

    def test_shared_rule_is_idempotent_and_preserves_all_unrelated_rules(self):
        db = self.fixture.registry(); before = self.fixture.rules(db)
        self.invoke(self.m.protect, db, umbrella=True, network=True)
        self.invoke(self.m.protect, db, umbrella=True, network=True)
        self.assertEqual(self.fixture.rules(db), before + [('plugin.video.themoviedb.helper',1), ('plugin.video.umbrella',1), (ADDON,1)])

    def test_shared_rule_failure_rolls_back_other_new_rules(self):
        db = self.fixture.registry(); before = self.fixture.rules(db)
        with sqlite3.connect(db) as c:
            c.execute("CREATE TRIGGER reject_network BEFORE INSERT ON update_rules WHEN NEW.addonID='script.module.jurialmunkey' AND NEW.updateRule=1 BEGIN SELECT RAISE(ABORT,'fixture'); END")
        self.assertIn('network', inspect.signature(self.m.protect).parameters)
        with self.assertRaises(self.m.ProtectionError): self.m.protect(db, umbrella=True, network=True)
        self.assertEqual(self.fixture.rules(db), before)

    def test_whitelist_cannot_keep_old_shared_request_source(self):
        home = self.fixture.root/'home'
        for n,b in self.files.items():
            path = home/'addons'/ADDON/n; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(b)
        self.invoke(self.m.verify_kept, home, {ADDON}, network=True)
        path = home/'addons'/ADDON/'resources/modules/jurialmunkey/reqapi.py'
        path.write_bytes((ROOT/'compatibility/shared-requests/general-before.py').read_bytes())
        with self.assertRaises(self.m.ProtectionError): self.m.verify_kept(home, {ADDON}, network=True)

    def test_installed_known_sources_pass_but_unknown_newer_code_is_not_overwritten(self):
        home = self.fixture.root/'home'
        for n,b in self.files.items():
            path=home/'addons'/ADDON/n;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b)
        self.assertIn('network', inspect.signature(self.m.verify_installed).parameters)
        self.m.verify_installed(home, network=True)
        path=home/'addons'/ADDON/'resources/modules/jurialmunkey/reqapi.py'
        path.write_bytes((ROOT/'compatibility/shared-requests/general-before.py').read_bytes())
        self.m.verify_installed(home, network=True)
        path.write_bytes(b'foreign newer implementation')
        with self.assertRaises(self.m.ProtectionError):self.m.verify_installed(home, network=True)
        self.assertEqual(path.read_bytes(),b'foreign newer implementation')


if __name__ == '__main__': unittest.main()
