"""Updates navigation uses installed edition, curated notes and true in-place routes."""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import test_installer_preservation_ui as fixture


class InstallerUpdates(unittest.TestCase):
    def setUp(self):
        self.f = fixture.InstallerPreservationUI()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.home = Path(self.f.config.HOME)
        self.home.joinpath('userdata').mkdir(parents=True, exist_ok=True)
        self.marker = self.home/'userdata/blacklanturn-build.json'
        self.marker.write_text(json.dumps({'schema':3, 'edition':'apple', 'build_version':'1.1.24'}))
        self.context = patch.dict(sys.modules, self.f.modules)
        self.context.start()
        self.addCleanup(self.context.stop)
        self.f.modules['resources.libs'].__path__ = [str(fixture.LIB)]

    def updates(self):
        self.assertTrue((fixture.LIB/'gui/updates_menu.py').is_file(), 'Dedicated Updates page is missing')
        return self.f.load('gui/updates_menu.py')

    def release(self, edition='apple', version='1.1.25'):
        return {'id':'blacklanturn-'+edition+'-'+version, 'edition':edition, 'version':version,
                'revision':0, 'title':'BlackLanturn '+version, 'summary':'Reviewed fixes',
                'sections':[{'heading':'Playback', 'bullets':['Preserve your playback preferences.']}],
                'files':{'addons/test/addon.xml':'a'*64}}

    def catalog(self, module, entries=None):
        catalog={'schema':1,'releases':entries or [self.release()]}
        (self.home/'userdata/blacklanturn-releases.json').write_text(json.dumps(catalog))
        return catalog

    def test_sidebar_opens_updates_page_without_opening_builds_or_install(self):
        nav=self.f.load('gui/navigation.py')
        model=self.f.load('gui/navigation_model.py')
        screen=nav.InstallerNavigation('unused',navigation=model.Navigation(),rows=[])
        screen.onInit()
        labels=[i.label for i in screen.getControl(100).items]
        self.assertIn('Updates', labels)
        self.assertLess(labels.index('Updates'), labels.index('Maintenance'))
        screen.getControl(100).position=labels.index('Updates')
        screen.onClick(100)
        self.assertEqual(screen.pending,('switch',{'mode':'updates'},'Updates'))
        self.assertIsNotNone(nav.producer({'mode':'updates'}))

    def test_opening_page_shows_installed_and_known_latest_without_network_or_reinstall(self):
        m=self.updates();self.catalog(m)
        with patch.object(m.releases,'fetch_catalog',side_effect=AssertionError('page performed network')):
            rows=m.rows(self.home)
        self.assertTrue(any('1.1.24' in r['label'] for r in rows))
        self.assertTrue(any('1.1.25' in r['label'] for r in rows))
        self.assertTrue(any(r['params']=={'mode':'updatescheck'} for r in rows))
        self.assertFalse(any(r['params'].get('action') in ('build','fresh') for r in rows))
        self.assertFalse(self.f.writes)

    def test_check_now_offers_true_update_for_installed_edition_despite_stale_other_buildname(self):
        m=self.updates();cat=self.catalog(m,[self.release(),self.release('general','9.0.0')])
        self.f.config.BUILDNAME='BlackLanturn General'
        calls=[]
        self.f.modules['resources.libs.check'].check_build=lambda name, field:calls.append((name,field)) or '1.1.25'
        with patch.object(m.releases,'fetch_catalog',return_value=cat):m.check_now(self.home,now=1720000000)
        update=next(r for r in m.rows(self.home) if r['label']=='Update BlackLanturn')
        self.assertEqual(update['params'],{'mode':'install','action':'update','name':'BlackLanturn Apple TV & Mac'})
        self.assertEqual(calls,[('BlackLanturn Apple TV & Mac','version')])
        self.assertIn('Keep all',update['description'])
        self.assertEqual(self.f.writes,[])

    def test_general_edition_never_uses_apple_update_route(self):
        m=self.updates();self.marker.write_text(json.dumps({'schema':3,'edition':'general','build_version':'1.1.24'}))
        self.f.modules['resources.libs.check'].check_build=lambda *a:'1.1.25'
        with patch.object(m.releases,'fetch_catalog',return_value=self.catalog(m,[self.release('general')])):m.check_now(self.home,now=1720000000)
        row=next(r for r in m.rows(self.home) if r['label']=='Update BlackLanturn')
        self.assertEqual(row['params']['name'],'BlackLanturn General')

    def test_current_or_newer_installed_build_does_not_offer_downgrade(self):
        m=self.updates();self.f.modules['resources.libs.check'].check_build=lambda *a:'1.1.23'
        with patch.object(m.releases,'fetch_catalog',return_value=self.catalog(m)):m.check_now(self.home,now=1720000000)
        self.assertFalse(any(r['label']=='Update BlackLanturn' for r in m.rows(self.home)))

    def test_failed_catalog_check_keeps_last_success_but_hides_update_and_explains_retry(self):
        m=self.updates();self.f.modules['resources.libs.check'].check_build=lambda *a:'1.1.25'
        with patch.object(m.releases,'fetch_catalog',return_value=self.catalog(m)):m.check_now(self.home,now=1720000000)
        self.f.modules['resources.libs.check'].check_build=lambda *a:False
        with patch.object(m.releases,'fetch_catalog',side_effect=OSError('offline')):m.check_now(self.home,now=1720000500)
        rows=m.rows(self.home)
        self.assertTrue(any('1.1.25' in r['label'] for r in rows))
        self.assertTrue(any('failed' in r['label'].lower() for r in rows))
        self.assertFalse(any(r['label']=='Update BlackLanturn' for r in rows))

    def test_failed_notes_fetch_still_allows_valid_build_update_with_bundled_notes(self):
        m=self.updates();self.catalog(m);self.f.modules['resources.libs.check'].check_build=lambda *a:'1.1.25'
        with patch.object(m.releases,'fetch_catalog',side_effect=OSError('offline')):m.check_now(self.home,now=1720000000)
        self.assertTrue(any(r['label']=='Update BlackLanturn' for r in m.rows(self.home)))
        self.assertTrue(any(r['params']=={'mode':'updatenotes'} for r in m.rows(self.home)))

    def test_notice_toggle_changes_only_existing_curated_notice_preference(self):
        m=self.updates();state=m.releases.empty_state();state['seen']=['never:older'];state['history']=[self.release()]
        path=self.home/'userdata/addon_data/script.blacklanturn.preview/release-notices.json'
        m.releases.write_state(path,state)
        m.toggle_preference(self.home)
        self.assertEqual(m.releases.read_state(path),dict(state,enabled=False))
        self.assertEqual(self.f.writes,[])
        self.assertTrue(any('OFF' in r['label'] and r['params']=={'mode':'updatespref'} for r in m.rows(self.home)))

    def test_notes_available_after_dismissal_uses_curated_same_edition_without_changing_preference(self):
        m=self.updates();self.catalog(m,[self.release(),self.release('general','9.0.0')])
        path=self.home/'userdata/addon_data/script.blacklanturn.preview/release-notices.json'
        state=m.releases.empty_state(False);state['seen']=['never:blacklanturn-apple-1.1.25']
        m.releases.write_state(path,state)
        self.assertTrue(callable(getattr(m,'refresh_notes',None)), 'Notes action must prepare saved curated entries')
        with patch.object(m.releases,'fetch_catalog',side_effect=AssertionError('notes performed network')):
            m.refresh_notes(self.home)
        actual=m.releases.read_state(path)
        self.assertFalse(actual['enabled']);self.assertEqual(actual['seen'],state['seen'])
        self.assertEqual(actual['available']['edition'],'apple')
        self.assertEqual(actual['available']['version'],'1.1.25')
        self.assertEqual(self.f.writes,[])

    def test_update_comparison_uses_numeric_versions(self):
        m=self.updates();self.marker.write_text(json.dumps({'schema':3,'edition':'apple','build_version':'1.1.9'}))
        self.f.modules['resources.libs.check'].check_build=lambda *a:'1.1.10'
        with patch.object(m.releases,'fetch_catalog',return_value=self.catalog(m)):m.check_now(self.home,now=1720000000)
        self.assertTrue(any(r['label']=='Update BlackLanturn' for r in m.rows(self.home)))

    def test_missing_marker_has_no_update_and_never_checks_arbitrary_build(self):
        m=self.updates();self.marker.unlink()
        self.f.modules['resources.libs.check'].check_build=lambda *a:self.fail('checked arbitrary build')
        m.check_now(self.home,now=1720000000)
        self.assertFalse(any(r['label']=='Update BlackLanturn' for r in m.rows(self.home)))

    def test_replaced_installed_edition_invalidates_previous_check(self):
        m=self.updates();self.f.modules['resources.libs.check'].check_build=lambda *a:'1.1.25'
        with patch.object(m.releases,'fetch_catalog',return_value=self.catalog(m)):m.check_now(self.home,now=1720000000)
        self.marker.write_text(json.dumps({'schema':3,'edition':'general','build_version':'1.1.24'}))
        self.assertFalse(any(r['label']=='Update BlackLanturn' for r in m.rows(self.home)))

    def test_malformed_marker_and_check_state_fail_closed_without_inventing_latest(self):
        m=self.updates()
        self.marker.write_text('[]')
        try:
            rows=m.rows(self.home)
        except AttributeError as exc:
            self.fail('Malformed marker crashed the Updates page: '+str(exc))
        self.assertFalse(any(r['label']=='Update BlackLanturn' for r in rows))
        self.marker.write_text(json.dumps({'schema':3,'edition':'apple','build_version':'1.1.24'}))
        path=self.home/'userdata/addon_data/plugin.program.blacklanturninstaller/update-check.json'
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text('[]')
        self.assertFalse(any(r['label']=='Update BlackLanturn' for r in m.rows(self.home)))

    def test_manual_routes_reopen_updates_and_never_dispatch_update_transaction(self):
        m=self.updates();nav=self.f.load('gui/navigation.py');router=self.f.load('common/router.py')
        # Real route code executes; only remote checks and UI refresh are replaced.
        with patch.dict(sys.modules,{'resources.libs.gui.updates_menu':m}),patch.object(m,'check_now') as check,patch.object(m,'toggle_preference') as toggle:
            router.Router().dispatch(1,'mode=updatescheck')
            router.Router().dispatch(1,'mode=updatespref')
            self.assertEqual(check.call_count,1);self.assertEqual(toggle.call_count,1)
        self.assertFalse(any('install' in c.lower() for c in self.f.kodi.commands))

if __name__=='__main__':unittest.main()
