"""Local integration contracts; synthetic manifests are never native receipts."""
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import xml.etree.ElementTree as E

import test_managed_helper as helper_fixture

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'installer-source').is_dir())
LIB=ROOT/'installer-source/plugin.program.blacklanturninstaller/resources/libs'
SOURCE=ROOT/'compatibility/umbrella-progress/upstream-6.7.92.zip'
UMBRELLA='plugin.video.umbrella'
PREFIX='addons/'+UMBRELLA+'/'
HELPER='plugin.video.themoviedb.helper'

class ManagedUmbrellaTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.spec=importlib.util.spec_from_file_location('managed_umbrella_under_test',LIB/'managed_addons.py')
        self.m=importlib.util.module_from_spec(self.spec);self.spec.loader.exec_module(self.m)
        self.provider=helper_fixture.current_data(UMBRELLA)
        self.version=E.fromstring(self.provider['addon.xml']).get('version')
        self.resources=self.root/'installer/resources';(self.resources/'libs').mkdir(parents=True)
        self.m.__file__=str(self.resources/'libs/managed_addons.py')
        shutil.copyfile(LIB.parent/'managed-helper.json',self.resources/'managed-helper.json')
        # Hash-only contract fixture deliberately uses upstream code. It is not
        # a claim that upstream player.py is an accepted production candidate.
        self.manifest={'addon_id':UMBRELLA,'version':self.version,'playback_patch':'event-progress-3',
            'files':{n:hashlib.sha256(b).hexdigest()for n,b in self.provider.items()},
            'installed_player_hashes':{self.version:[hashlib.sha256(self.provider['resources/lib/modules/player.py']).hexdigest()]},'legacy_files':{}}
        (self.resources/'managed-umbrella.json').write_text(json.dumps(self.manifest))

    def invoke(self,method,*args,**kwargs):
        for key in kwargs:
            self.assertIn(key,inspect.signature(method).parameters,'Optional managed provider support is missing: '+key)
        return method(*args,**kwargs)

    def archive(self,change=None):
        helper=helper_fixture.ManagedTests();helper.root=self.root
        with zipfile.ZipFile(helper.archive()) as source:data={n:source.read(n)for n in source.namelist()}
        data.update({PREFIX+n:b for n,b in self.provider.items()})
        if change:change(data)
        path=self.root/'managed-build.zip'
        with zipfile.ZipFile(path,'w')as archive:
            for name,raw in data.items():archive.writestr(name,raw)
        return path

    def installed(self,version=None,change=None):
        home=self.root/'home';addon=home/'addons'/UMBRELLA
        for name,raw in self.provider.items():
            path=addon/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        if version:(addon/'addon.xml').write_bytes(self.provider['addon.xml'].replace(('version="'+self.version+'"').encode(),('version="'+version+'"').encode(),1))
        if change:change(addon)
        return home

    def guard(self,home):
        method=getattr(self.m,'verify_installed',None);self.assertTrue(callable(method),'Missing pre-cleanup source guard')
        return method(home)

    def registry(self,trigger=False):
        path=self.root/'Addons33.db'
        with sqlite3.connect(path)as db:
            db.execute('CREATE TABLE update_rules(id INTEGER PRIMARY KEY,addonID TEXT,updateRule INTEGER)')
            db.executemany('INSERT INTO update_rules VALUES(?,?,?)',[(1,'repository.keep',2),(2,HELPER,3),(3,UMBRELLA,2)])
            if trigger:db.execute("CREATE TRIGGER reject_umbrella BEFORE INSERT ON update_rules WHEN NEW.addonID='plugin.video.umbrella' AND NEW.updateRule=1 BEGIN SELECT RAISE(ABORT,'fixture transaction failure'); END")
        return path

    def rules(self,path):
        with sqlite3.connect(path)as db:return list(db.execute('SELECT addonID,updateRule FROM update_rules ORDER BY id'))

    def test_legacy692_source_archive_and_full_manifest_have_exact_official_provenance(self):
        provenance=json.loads((ROOT/'compatibility/umbrella-progress/upstream-provenance.json').read_text())
        self.assertEqual(provenance['archive_sha256'],'8dc3b19e70d0e02deb32d06579441288dbe1911ecaec2628d298590e1333853f')
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(),provenance['archive_sha256'])
        manifest=json.loads((ROOT/'compatibility/umbrella-progress/upstream-6.7.92-manifest.json').read_text())
        self.assertEqual(len(manifest['files']),1682)
        with zipfile.ZipFile(SOURCE) as z:legacy={n.removeprefix(UMBRELLA+'/'):hashlib.sha256(z.read(n)).hexdigest()for n in z.namelist()if not n.endswith('/')}
        self.assertEqual(manifest['files'],legacy)

    def test_legacy692_archive_is_not_current_approved_target(self):
        def legacy(data):
            for name in list(data):
                if name.startswith(PREFIX):del data[name]
            with zipfile.ZipFile(SOURCE) as archive:
                data.update({PREFIX+n.removeprefix(UMBRELLA+'/'):archive.read(n) for n in archive.namelist() if not n.endswith('/')})
        with zipfile.ZipFile(self.archive(legacy)) as archive,self.assertRaises(self.m.ProtectionError):
            self.m.verify_archive(archive,umbrella=True)

    def test_current_pinned_complete_tree_passes_actual_production_install_guard(self):
        self.m.__file__=str(LIB/'managed_addons.py')
        self.assertEqual(self.guard(self.installed()),UMBRELLA)

    def test_optional_full_provider_archive_verification_accepts_exact_tree(self):
        with zipfile.ZipFile(self.archive())as archive:self.assertEqual(self.invoke(self.m.verify_archive,archive,umbrella=True),HELPER)

    def test_optional_full_tree_rejects_reverted_missing_and_added_provider_features(self):
        for mode in ('reverted','missing','added','future'):
            with self.subTest(mode=mode):
                def change(data):
                    if mode=='reverted':data[PREFIX+'resources/lib/modules/trakt.py']=b'foreign provider source'
                    elif mode=='missing':del data[PREFIX+'resources/lib/modules/trakt.py']
                    elif mode=='added':data[PREFIX+'foreign.py']=b'pass'
                    else:data[PREFIX+'addon.xml']=data[PREFIX+'addon.xml'].replace(('version="'+self.version+'"').encode(),b'version="999.0.0"',1)
                with zipfile.ZipFile(self.archive(change))as archive:
                    self.assertIn('umbrella',inspect.signature(self.m.verify_archive).parameters,'Optional provider verification missing')
                    with self.assertRaises(self.m.ProtectionError):self.m.verify_archive(archive,umbrella=True)

    def test_legacy_helper_only_verification_ignores_unmanaged_provider(self):
        with zipfile.ZipFile(self.archive(lambda data:data.__setitem__(PREFIX+'addon.xml',b'legacy unreviewed provider')))as archive:
            self.assertEqual(self.m.verify_archive(archive),HELPER)

    def test_standalone_managed_api_rejects_raw_casefold_unicode_and_directory_aliases(self):
        for addon,relative in ((UMBRELLA,'resources/lib/modules/player.py'),(HELPER,'resources/tmdbhelper/lib/monitor/player.py')):
            canonical='addons/'+addon+'/'+relative
            aliases=('addons/./'+addon+'/'+relative,'addons//'+addon+'/'+relative,
                     'addons/'+addon.upper()+'/'+relative,
                     'addons/'+addon.upper()+'/unreviewed-extra.py')
            for alias in aliases:
                with self.subTest(addon=addon,alias=alias):
                    with zipfile.ZipFile(self.archive(lambda data:data.__setitem__(alias,b'unvalidated overwrite')))as archive:
                        with self.assertRaises(self.m.ProtectionError):self.m.verify_archive(archive,umbrella=addon==UMBRELLA)
        for names in (('userdata/caf\u00e9/settings.xml','userdata/cafe\u0301/settings.xml'),
                      ('addons/fixture/Directory/a.py','addons/fixture/directory/b.py'),
                      ('addons/fixture/same','addons/fixture/same/child.py')):
            with self.subTest(names=names):
                def change(data):data.update({n:b'alias'for n in names})
                with zipfile.ZipFile(self.archive(change))as archive:
                    with self.assertRaises(self.m.ProtectionError):self.m.verify_archive(archive,umbrella=True)

    def test_real_zip_extractor_overwrites_validated_player_through_dot_alias(self):
        alias='addons/./'+UMBRELLA+'/resources/lib/modules/player.py'
        path=self.archive(lambda data:data.__setitem__(alias,b'unvalidated overwrite'))
        # Establish the actual source-to-destination discrepancy at Python's
        # unchanged production ZIP boundary, rather than predicting normalization.
        with zipfile.ZipFile(path)as archive:
            archive.extractall(self.root/'unsafe-demonstration')
            self.assertEqual((self.root/'unsafe-demonstration'/PREFIX/'resources/lib/modules/player.py').read_bytes(),b'unvalidated overwrite')
            with self.assertRaises(self.m.ProtectionError):self.m.verify_archive(archive,umbrella=True)

    def test_standalone_managed_module_loads_without_kodi_or_resources_package(self):
        code="import importlib.util,sys,zipfile;spec=importlib.util.spec_from_file_location('standalone_managed',sys.argv[1]);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);z=zipfile.ZipFile(sys.argv[2]);assert m.verify_archive(z)=='plugin.video.themoviedb.helper'"
        result=subprocess.run([sys.executable,'-I','-B','-c',code,str(LIB/'managed_addons.py'),str(self.archive())],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_known_installed_tree_and_reviewed_player_variant_pass(self):
        home=self.installed();self.assertEqual(self.guard(home),UMBRELLA)
        path=home/'addons'/UMBRELLA/'resources/lib/modules/player.py';path.write_bytes(b'# known alternate fixture\n')
        self.manifest['installed_player_hashes'][self.version].append(hashlib.sha256(path.read_bytes()).hexdigest())
        (self.resources/'managed-umbrella.json').write_text(json.dumps(self.manifest))
        self.assertEqual(self.guard(home),UMBRELLA)

    def full_tree_digest(self, files):
        return hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

    def test_actual_installer_manifest_accepts_published_and_tested_complete_source(self):
        self.m.__file__=str(LIB/'managed_addons.py')
        for variant in ('published','tested'):
            with self.subTest(variant=variant):
                home=self.root/'home';addon=home/'addons'/UMBRELLA
                with zipfile.ZipFile(SOURCE) as archive:
                    for name in archive.namelist():
                        if name.endswith('/'):continue
                        target=addon/name.removeprefix(UMBRELLA+'/');target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(archive.read(name))
                if variant=='published':
                    (addon/'resources/lib/modules/player.py').write_bytes((ROOT/'compatibility/umbrella-progress/duration-candidate/6.7.92/player.py').read_bytes())
                else:
                    candidate=ROOT/'compatibility/autoplay-size/candidate'
                    for path in candidate.rglob('*.py'):(addon/path.relative_to(candidate)).write_bytes(path.read_bytes())
                self.assertEqual(self.guard(home),UMBRELLA)
                shutil.rmtree(home)

    def test_complete_tree_policy_accepts_exact_reviewed_predecessor(self):
        home=self.installed();addon=home/'addons'/UMBRELLA
        old=dict(self.manifest['files'])
        self.manifest['files']=dict(old, **{'resources/lib/modules/sources.py':'0'*64})
        self.manifest['installed_tree_sha256']={self.version:[self.full_tree_digest(old)]}
        (self.resources/'managed-umbrella.json').write_text(json.dumps(self.manifest))
        self.assertEqual(self.guard(home),UMBRELLA)

    def test_complete_tree_policy_rejects_mixed_individually_reviewed_modules(self):
        home=self.installed();addon=home/'addons'/UMBRELLA
        old=dict(self.manifest['files']);new=dict(old)
        alternate=b'# reviewed alternate player\n';new['resources/lib/modules/player.py']=hashlib.sha256(alternate).hexdigest()
        new['resources/lib/modules/sources.py']='0'*64
        self.manifest['installed_tree_sha256']={self.version:[self.full_tree_digest(old),self.full_tree_digest(new)]}
        self.manifest['installed_player_hashes'][self.version].append(new['resources/lib/modules/player.py'])
        (self.resources/'managed-umbrella.json').write_text(json.dumps(self.manifest))
        (addon/'resources/lib/modules/player.py').write_bytes(alternate)
        before={p.relative_to(home):p.read_bytes() for p in home.rglob('*') if p.is_file()}
        with self.assertRaises(self.m.ProtectionError):self.guard(home)
        self.assertEqual(before,{p.relative_to(home):p.read_bytes() for p in home.rglob('*') if p.is_file()})

    def test_future_version_fails_before_any_existing_files_change(self):
        home=self.installed(version='6.8.0');before={p.relative_to(home):p.read_bytes()for p in home.rglob('*')if p.is_file()}
        method=getattr(self.m,'verify_installed',None);self.assertTrue(callable(method),'Missing source guard')
        with self.assertRaises(self.m.ProtectionError):method(home)
        self.assertEqual(before,{p.relative_to(home):p.read_bytes()for p in home.rglob('*')if p.is_file()})

    def test_foreign_player_and_foreign_provider_module_are_rejected(self):
        for relative in ('resources/lib/modules/player.py','resources/lib/modules/trakt.py','foreign.py'):
            with self.subTest(relative=relative):
                home=self.installed(change=lambda addon:(addon/relative).write_bytes(b'foreign'))
                method=getattr(self.m,'verify_installed',None);self.assertTrue(callable(method),'Missing source guard')
                with self.assertRaises(self.m.ProtectionError):method(home)
                shutil.rmtree(home)

    def test_known_legacy_version_requires_its_entire_reviewed_tree(self):
        legacy=dict(self.provider);legacy['addon.xml']=legacy['addon.xml'].replace(('version="'+self.version+'"').encode(),b'version="6.7.90"',1)
        self.manifest['legacy_files']['6.7.90']={n:hashlib.sha256(raw).hexdigest()for n,raw in legacy.items()}
        self.manifest['installed_player_hashes']['6.7.90']=[hashlib.sha256(legacy['resources/lib/modules/player.py']).hexdigest()]
        (self.resources/'managed-umbrella.json').write_text(json.dumps(self.manifest))
        home=self.installed(version='6.7.90');self.assertEqual(self.guard(home),UMBRELLA)
        (home/'addons'/UMBRELLA/'resources/lib/modules/trakt.py').write_bytes(b'foreign90source')
        with self.assertRaises(self.m.ProtectionError):self.guard(home)

    def test_runtime_bytecode_is_ignored_but_source_links_are_rejected(self):
        home=self.installed();addon=home/'addons'/UMBRELLA
        cache=addon/'resources/lib/modules/__pycache__';cache.mkdir()
        (cache/'player.pyc').write_bytes(b'generated runtime bytecode')
        self.assertEqual(self.guard(home),UMBRELLA)
        foreign=self.root/'foreign';foreign.write_bytes(b'foreign source')
        (addon/'foreign.py').symlink_to(foreign)
        with self.assertRaises(self.m.ProtectionError):self.guard(home)

    def test_absent_provider_is_allowed_for_clean_install(self):
        self.assertIsNone(self.guard(self.root/'new-home'))

    def test_both_rules_are_idempotent_and_retain_all_existing_rules(self):
        db=self.registry();before=self.rules(db)
        self.invoke(self.m.protect,db,umbrella=True);self.invoke(self.m.protect,db,umbrella=True)
        self.assertEqual(self.rules(db),before+[(HELPER,1),(UMBRELLA,1)])

    def test_second_rule_failure_rolls_back_first_rule(self):
        db=self.registry(trigger=True);before=self.rules(db)
        self.assertIn('umbrella',inspect.signature(self.m.protect).parameters,'Optional provider rule missing')
        with self.assertRaises(self.m.ProtectionError):self.m.protect(db,umbrella=True)
        self.assertEqual(self.rules(db),before)

if __name__=='__main__':unittest.main()
