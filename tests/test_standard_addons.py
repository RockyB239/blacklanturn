"""Run Standard's actual download, wipe and extraction on disposable trees."""
import importlib.util
from pathlib import Path
import sys
import itertools
import shutil
import subprocess
import tempfile
import types
import unittest
from unittest.mock import patch
import zipfile
import test_compatibility as fixture

LIB = fixture.ROOT

def metadata(aid, version, deps='', platform='all'):
    return ('<addon id="{}" version="{}"><requires><import addon="xbmc.python" version="3.0.0"/>{}</requires>'
            '<extension point="xbmc.python.module" library="lib"/><extension point="xbmc.addon.metadata"><platform>{}</platform></extension></addon>').format(aid, version, deps, platform).encode()

class StandardAddons(unittest.TestCase):
    def setUp(self):
        self.f = fixture.CompatibilityTests(); self.f.setUp(); self.addCleanup(self.f.tearDown)
        self.cfg, self.mods = self.f.install_environment(fixture.Kodi())
        self.mods['xbmc'].LOGERROR = 4
        self.mods['resources.libs.whitelist'] = types.SimpleNamespace(whitelist=lambda mode: [])
        self.mods['resources.libs.common.tools'].convert_size = str
        self.cfg.EXCLUDE_FILES = []
        self.home = Path(self.cfg.HOME)
        self.addon('script.module.certifi', '2.0', {'lib/current.py': b'new complete code'})
        self.data = {'addons/script.module.certifi/addon.xml': metadata('script.module.certifi', '1.0'),
                     'addons/script.module.certifi/lib/obsolete.py': b'old bundled code'}
        marker = self.home/'userdata/preflight.txt'; marker.parent.mkdir(parents=True, exist_ok=True); marker.write_text('original')
    def addon(self, aid, version, files=None, deps='', platform='all'):
        root=self.home/'addons'/aid; root.mkdir(parents=True, exist_ok=True)
        (root/'addon.xml').write_bytes(metadata(aid, version, deps, platform))
        for name, raw in (files or {'lib/main.py': b'complete'}).items():
            p=root/name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(raw)
        return root
    def run_install(self, auth_only=False):
        self.cfg.get_setting=lambda key: 'true' if auth_only and key=='authonlyclean' else 'false'
        self.f.archive(None, self.data)
        with patch.dict(sys.modules, self.mods):
            spec=importlib.util.spec_from_file_location('real_standard_extract',LIB/'extract.py'); ex=importlib.util.module_from_spec(spec); spec.loader.exec_module(ex)
            self.mods['resources.libs.extract'].all=ex.all
            spec=importlib.util.spec_from_file_location('standard_wizard',LIB/'wizard.py'); wizard=importlib.util.module_from_spec(spec); spec.loader.exec_module(wizard)
            wizard.Wizard().build('fixture')
    def test_standard_does_not_downgrade_or_mix_complete_newer_dependency(self):
        self.run_install()
        root=self.home/'addons/script.module.certifi'
        self.assertIn(b'version="2.0"', (root/'addon.xml').read_bytes())
        self.assertTrue((root/'lib/current.py').is_file())
        self.assertFalse((root/'lib/obsolete.py').exists())
        self.assertFalse((self.home/'userdata/preflight.txt').exists(), 'cleanup did not execute')
    def test_actual_running_installer29_survives_older_same_and_newer_bundled_self(self):
        source=LIB.parents[1]
        expected={p.relative_to(source).as_posix():p.read_bytes() for p in source.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
        aid=self.cfg.ADDON_ID
        for version in ('1.0.28','1.0.29','1.0.30'):
            with self.subTest(bundled_version=version):
                root=self.home/'addons'/aid
                for name,raw in expected.items():
                    p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
                self.data['addons/'+aid+'/addon.xml']=metadata(aid,version)
                self.data['addons/'+aid+'/lib/bundle-only.py']=b'must never replace running Installer'
                marker=self.home/'userdata/preflight.txt';marker.parent.mkdir(parents=True,exist_ok=True);marker.write_bytes(b'old')
                self.run_install()
                actual={p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}
                self.assertTrue(actual==expected,'Running Installer changed or disappeared')
                self.assertFalse(marker.exists(),'Standard update did not complete')
    def test_own_repository_upgrade_is_complete_and_newer_repository_stays_whole(self):
        aid='repository.blacklanturn'
        self.cfg.EXCLUDES.append(aid)
        def repo(version):
            return ('<addon id="repository.blacklanturn" version="'+version+'"><extension point="xbmc.addon.repository"><dir><info>https://example.invalid/addons.xml</info><checksum>https://example.invalid/addons.xml.md5</checksum><datadir zip="true">https://example.invalid/</datadir></dir></extension><extension point="xbmc.addon.metadata"><platform>all</platform></extension></addon>').encode()
        for version in ('1.0.5','1.0.6','1.0.7'):
            with self.subTest(installed_repository=version):
                root=self.home/'addons'/aid
                if root.exists():shutil.rmtree(root)
                root.mkdir(parents=True)
                (root/'addon.xml').write_bytes(repo(version));(root/'only-installed.txt').write_bytes(b'original complete repository')
                self.data['addons/'+aid+'/addon.xml']=repo('1.0.6')
                self.data['addons/'+aid+'/only-bundle.txt']=b'current repository asset'
                marker=self.home/'userdata/preflight.txt';marker.parent.mkdir(parents=True,exist_ok=True);marker.write_bytes(b'old')
                self.run_install()
                self.assertFalse(marker.exists(),'repository case did not install')
                if version=='1.0.7':
                    self.assertEqual((root/'addon.xml').read_bytes(),repo('1.0.7'))
                    self.assertTrue((root/'only-installed.txt').is_file());self.assertFalse((root/'only-bundle.txt').exists())
                else:
                    self.assertEqual((root/'addon.xml').read_bytes(),repo('1.0.6'))
                    self.assertTrue((root/'only-bundle.txt').is_file());self.assertFalse((root/'only-installed.txt').exists())

    def test_clean_replaces_own_repository_with_build_defaults_and_keeps_runtime_excludes(self):
        aid='repository.blacklanturn';custom='script.module.system-kept'
        self.cfg.EXCLUDES.extend((aid,custom))
        source=LIB.parents[3]/'repository/repository.blacklanturn'
        expected={p.relative_to(source).as_posix():p.read_bytes() for p in source.rglob('*') if p.is_file()}
        installer_source=LIB.parents[1]
        installer_expected={p.relative_to(installer_source).as_posix():p.read_bytes() for p in installer_source.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
        self.addon(custom,'1',{'lib/main.py':b'protected custom runtime'})
        self.data['addons/'+custom+'/addon.xml']=metadata(custom,'3')
        self.data['addons/'+custom+'/lib/bundle-only.py']=b'not for protected runtime'
        for version in ('1.0.5','1.0.7'):
            with self.subTest(installed_repository=version):
                repository=self.home/'addons'/aid
                if repository.exists():shutil.rmtree(repository)
                for name,raw in expected.items():
                    p=repository/name;p.parent.mkdir(parents=True,exist_ok=True)
                    p.write_bytes(raw.replace(b'version="1.0.6"',('version="'+version+'"').encode()) if name=='addon.xml' else raw)
                    self.data['addons/'+aid+'/'+name]=raw
                (repository/'only-installed.txt').write_bytes(b'obsolete repository file')
                installer=self.home/'addons'/self.cfg.ADDON_ID
                for name,raw in installer_expected.items():
                    p=installer/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
                self.data['addons/'+self.cfg.ADDON_ID+'/addon.xml']=metadata(self.cfg.ADDON_ID,'1.0.30')
                self.f.archive(None,self.data)
                plan=self.module().prepare(self.f.root/'build.zip',self.home,auth_only=True,excluded=self.cfg.EXCLUDES)
                with patch.dict(sys.modules,self.mods):
                    self.mods['resources.libs.install'].wipe(accounts_prepared=True,auth_only=True,standard_plan=plan)
                    spec=importlib.util.spec_from_file_location('clean_repository_extract',LIB/'extract.py');ex=importlib.util.module_from_spec(spec);spec.loader.exec_module(ex)
                    self.assertEqual(ex.all(self.f.root/'build.zip',self.home,standard_plan=plan)[:2],(100,0))
                actual={p.relative_to(repository).as_posix():p.read_bytes() for p in repository.rglob('*') if p.is_file()}
                self.assertTrue(actual==expected,'Clean retained old/newer repository instead of complete build defaults')
                actual_installer={p.relative_to(installer).as_posix():p.read_bytes() for p in installer.rglob('*') if p.is_file()}
                self.assertTrue(actual_installer==installer_expected,'Clean changed running Installer')
                self.assertEqual((self.home/'addons'/custom/'lib/main.py').read_bytes(),b'protected custom runtime')
                self.assertFalse((self.home/'addons'/custom/'lib/bundle-only.py').exists())

    def test_dependency_on_running_installer_uses_actual_not_bundled_version(self):
        aid=self.cfg.ADDON_ID
        self.addon(aid,'1.0.29')
        self.data['addons/'+aid+'/addon.xml']=metadata(aid,'1.0.30')
        self.data['addons/'+aid+'/lib/main.py']=b'bundled self module'
        self.addon('script.module.certifi','2',deps='<import addon="'+aid+'" version="1.0.30"/>')
        self.assert_aborts()
    def test_explicit_excluded_portable_code_survives_wipe_and_extraction(self):
        aid='script.module.system-kept'
        self.cfg.EXCLUDES.append(aid)
        root=self.addon(aid,'1',{'lib/main.py':b'protected original'})
        self.data.update({'addons/'+aid+'/addon.xml':metadata(aid,'3'),'addons/'+aid+'/lib/bundle-only.py':b'bundled'})
        self.run_install()
        self.assertTrue((root/'lib/main.py').is_file(),'Explicitly excluded code tree was deleted')
        self.assertEqual((root/'lib/main.py').read_bytes(),b'protected original')
        self.assertFalse((root/'lib/bundle-only.py').exists())
        self.assertIn(b'version="1"',(root/'addon.xml').read_bytes())

    def test_newer_bundle_replaces_complete_tree_without_foreign_old_files(self):
        self.data['addons/script.module.certifi/addon.xml']=metadata('script.module.certifi','3.0')
        self.run_install()
        root=self.home/'addons/script.module.certifi'
        self.assertFalse((root/'lib/current.py').exists(), 'retained tree mixed with new bundle')
        self.assertIn(b'version="3.0"', (root/'addon.xml').read_bytes())

    def module(self):
        spec=importlib.util.spec_from_file_location('standard_addons_test',LIB/'standard_addons.py')
        module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module
    def prepare(self, **kwargs):
        self.f.archive(None, self.data)
        return self.module().prepare(self.f.root/'build.zip', self.home, **kwargs)
    def assert_aborts(self):
        self.run_install()
        self.assertTrue((self.home/'userdata/preflight.txt').exists(), 'unsafe state reached cleanup')
    def test_malformed_installed_metadata_aborts_before_cleanup(self):
        (self.home/'addons/script.module.certifi/addon.xml').write_bytes(b'<broken>')
        self.assert_aborts()
    def test_wrong_installed_identity_aborts_before_cleanup(self):
        (self.home/'addons/script.module.certifi/addon.xml').write_bytes(metadata('script.module.foreign', '2.0'))
        self.assert_aborts()
    def test_missing_module_code_aborts_before_cleanup(self):
        (self.home/'addons/script.module.certifi/lib/current.py').unlink()
        self.assert_aborts()
    def test_foreign_native_file_aborts_before_cleanup(self):
        (self.home/'addons/script.module.certifi/foreign.so').write_bytes(b'foreign architecture')
        self.assert_aborts()
    def test_foreign_nested_addon_aborts_before_cleanup(self):
        root=self.home/'addons/script.module.certifi/nested'; root.mkdir(); (root/'addon.xml').write_bytes(metadata('nested','1'))
        self.assert_aborts()
    def test_foreign_platform_and_python_api_abort_before_cleanup(self):
        for raw in (metadata('script.module.certifi','2',platform='android'), metadata('script.module.certifi','2').replace(b'3.0.0',b'2.1.0')):
            with self.subTest(raw=raw):
                (self.home/'addons/script.module.certifi/addon.xml').write_bytes(raw); self.assert_aborts()
    def test_linked_tree_aborts_before_cleanup(self):
        p=self.home/'addons/script.module.certifi/lib/linked.py'; p.symlink_to('/etc/hosts')
        self.assert_aborts()
    def test_required_dependency_closure_is_preserved_and_registered(self):
        self.addon('script.module.certifi', '2', deps='<import addon="script.module.extra" version="2"/>')
        self.addon('script.module.extra','2')
        self.run_install()
        self.assertTrue((self.home/'addons/script.module.extra/lib/main.py').is_file())
        self.assertFalse((self.home/'userdata/preflight.txt').exists())
    def test_missing_dependency_aborts_before_cleanup(self):
        self.addon('script.module.certifi','2',deps='<import addon="script.module.missing" version="1"/>')
        self.assert_aborts()
    def test_insufficient_dependency_aborts_before_cleanup(self):
        self.addon('script.module.certifi','2',deps='<import addon="script.module.extra" version="3"/>')
        self.data.update({'addons/script.module.extra/addon.xml':metadata('script.module.extra','2'),'addons/script.module.extra/lib/main.py':b'bundled'})
        self.assert_aborts()
    def test_optional_dependency_does_not_block_retention(self):
        self.addon('script.module.certifi','2',deps='<import addon="script.module.missing" version="100" optional="true"/>')
        self.run_install(); self.assertFalse((self.home/'userdata/preflight.txt').exists())
    def test_all_four_managed_ids_and_native_are_never_retained(self):
        managed=('plugin.video.themoviedb.helper','plugin.video.umbrella','script.module.jurialmunkey','plugin.video.youtube','inputstream.adaptive','script.module.pil')
        for aid in managed:
            self.addon(aid, '99'); self.data['addons/'+aid+'/addon.xml']=metadata(aid,'1')
        plan=self.prepare()
        self.assertEqual(set(plan['preserve']), {'script.module.certifi'})
        self.assertFalse(set(managed) & plan['replace'])
    def test_retained_tree_changed_after_preflight_aborts_actual_wipe(self):
        plan=self.prepare()
        (self.home/'addons/script.module.certifi/lib/current.py').write_bytes(b'changed concurrently')
        with patch.dict(sys.modules,self.mods):
            self.assertIs(self.mods['resources.libs.install'].wipe(standard_plan=plan),False)
        self.assertTrue((self.home/'userdata/preflight.txt').exists())
    def test_post_cleanup_tree_change_reports_partial_install_state_honestly(self):
        plan=self.prepare()
        with patch.dict(sys.modules,self.mods):
            self.mods['resources.libs.install'].wipe(accounts_prepared=True,standard_plan=plan)
            self.assertFalse((self.home/'userdata/preflight.txt').exists())
            (self.home/'addons/script.module.certifi/lib/current.py').write_bytes(b'changed after cleanup')
            spec=importlib.util.spec_from_file_location('post_cleanup_extract',LIB/'extract.py');ex=importlib.util.module_from_spec(spec);spec.loader.exec_module(ex)
            percent,errors,error=ex.all(self.f.root/'build.zip',self.home,standard_plan=plan)
        self.assertEqual((percent,errors),(0,1))
        self.assertNotIn('No cleanup has run',error)
        self.assertIn('cleanup has already run',error)
        self.assertFalse((self.home/'addons/script.module.certifi/lib/obsolete.py').exists())

    def test_account_only_plan_does_not_preserve_ordinary_newer_trees(self):
        plan=self.prepare(auth_only=True)
        self.assertEqual(plan, {'preserve':{},'replace':set(),'state':False,'excluded':frozenset((self.cfg.ADDON_ID,))})
    def test_version_order_epochs_tilde_revision_and_numeric(self):
        module=self.module()
        for older,newer in [('1.9','1.10'),('1.0~beta','1.0'),('1.0-2','1.0-10'),('99.0','1:1.0'),('1:6.18.1+blacklanturn.1','1:6.18.1+blacklanturn.2'),('1.0a','1.0b')]:
            self.assertLess(module.compare(older,newer),0,(older,newer))
        self.assertEqual(module.compare('01.0','1.0'),0)
    def test_python_version_order_matches_unmodified_kodi_omega_comparator(self):
        source=LIB.parents[3]/'compatibility/managed-updates/kodi-omega'
        versions=['0','0.0.0','1','01','1.0','1.0.0','1.9','1.10','1.0~alpha','1.0~beta2','1.0~beta10',
                  '1.0-1','1.0-10','1.0+a','1.0_A','1.0@a','1:0','2:1','1:6.18.1+blacklanturn.1',
                  '1:6.18.1+blacklanturn.2','1.0a','1.0.01','1.0~','9999999999999999999999']
        pairs=list(itertools.product(versions,repeat=2))
        with tempfile.TemporaryDirectory() as directory:
            d=Path(directory); (d/'utils').mkdir()
            (d/'utils/StringUtils.h').write_text('#include <string>\n#include <algorithm>\n#include <cctype>\nstruct StringUtils { static void ToLower(std::string& s) { std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c){return std::tolower(c);}); } static std::string Format(const char*, int n) { return std::to_string(n)+":"; } };')
            (d/'utils/log.h').write_text('enum { LOGERROR }; struct CLog { template<typename... T> static void Log(int,const char*,T...) {} };')
            (d/'main.cpp').write_text('#include "AddonVersion.h"\n#include <iostream>\nint main(int argc,char** argv) { for(int i=1;i<argc;i+=2) { ADDON::CAddonVersion a(argv[i]),b(argv[i+1]); std::cout << (a<b?-1:a==b?0:1) << "\\n"; } }')
            subprocess.run([shutil.which('c++'),'-std=c++17','-I'+str(d),'-I'+str(source),str(source/'AddonVersion.cpp'),str(d/'main.cpp'),'-o',str(d/'compare')],check=True,capture_output=True)
            expected=subprocess.run([str(d/'compare')]+[v for pair in pairs for v in pair],check=True,capture_output=True,text=True).stdout.splitlines()
        module=self.module()
        self.assertEqual([module.compare(a,b) for a,b in pairs],[int(v) for v in expected])

    def test_standard_keeps_kodi_database_and_only_account_history_files(self):
        paths=['userdata/Database/MyVideos131.db','userdata/Database/MyVideos131.db-wal',
               'userdata/addon_data/plugin.video.youtube/0/history.sqlite',
               'userdata/addon_data/plugin.video.youtube/0/history.sqlite-wal',
               'userdata/addon_data/plugin.video.youtube/0/bookmarks.sqlite',
               'userdata/addon_data/plugin.video.youtube/0/bookmarks.sqlite-shm']
        for relative in paths:
            p=self.home/relative; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(b'personal-state')
            self.data[relative]=b'package-must-not-overwrite'
        unrelated=self.home/'userdata/addon_data/plugin.video.youtube/0/other.sqlite'; unrelated.write_bytes(b'not-retained')
        self.run_install()
        for relative in paths: self.assertEqual((self.home/relative).read_bytes(),b'personal-state',relative)
        self.assertFalse(unrelated.exists())
    def test_clean_clears_kodi_database_and_account_history(self):
        self.f.archive(None,self.data)
        p=self.home/'userdata/Database/MyVideos131.db'; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(b'old-library')
        h=self.home/'userdata/addon_data/plugin.video.youtube/0/history.sqlite'; h.parent.mkdir(parents=True,exist_ok=True); h.write_bytes(b'old-history')
        plan=self.module().prepare(self.f.root/'build.zip',self.home,auth_only=True)
        with patch.dict(sys.modules,self.mods): self.mods['resources.libs.install'].wipe(accounts_prepared=True,auth_only=True,standard_plan=plan)
        self.assertFalse(p.exists()); self.assertFalse(h.exists())
    def test_invalid_versions_fail_closed(self):
        module=self.module()
        for value in ('','one:1','1/2','1-','1:','1 2'):
            with self.subTest(value=value),self.assertRaises(module.ProtectionError): module.compare(value,'1')

if __name__=='__main__': unittest.main()
