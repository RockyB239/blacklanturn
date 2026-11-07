"""Watch refresh retires workers while keeping only scoped neutral display rows."""
import copy
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parents[1] / 'addon'))
from cache_fixture import bind
from filtered_pages import PageCancelled
from home_rows import HomeRowSnapshots
from playback_core import restored_position, refreshed_watch_item, item_key, trakt_command
from public_rows import PublicRowSnapshots
from live_core import title_details_params, watch_state
from test_public_row_snapshots import P, ITEM
from test_watch_refresh import InlineThread
from test_window_lifecycle import extract, ROOT

H = P.replace('info=popular', 'info=trakt_recommendations')


class WatchRefreshCache(unittest.TestCase):
    def state(self, folder, provider=None, clock=lambda:1000):
        calls = []
        fresh = dict(ITEM, playcount=0, resume={'position':75, 'total':100})
        def load(path):
            calls.append(path)
            return provider(path) if provider is not None else [dict(ITEM, file=ITEM['file'].replace('42', '43')), fresh]
        props = {}
        state = SimpleNamespace(actions_open=False, stop_preview=lambda:None, generation=2, alive=True,
            section='Movies', getFocusId=lambda:900, setFocusId=lambda cid:props.__setitem__('focus', cid),
            list_lock=threading.Lock(), selected=copy.deepcopy(ITEM), paths=[P, H],
            rows=[[copy.deepcopy(ITEM)], [copy.deepcopy(ITEM)]], row_cache={8:'hydrated'}, failed_paths={},
            getControl=lambda cid:SimpleNamespace(getSelectedPosition=lambda:0),
            setProperty=lambda key,value:props.__setitem__(key,value), getProperty=lambda key:'Row')
        state.apply_row=lambda n,files,label,position,**kw:(state.rows.__setitem__(n,files), props.__setitem__('position'+str(n),position))
        state.update=lambda item:setattr(state, 'selected', item)
        ns = {'threading':SimpleNamespace(Thread=InlineThread), 'time':time, 'get_list':load,
            'restored_position':restored_position, 'refreshed_watch_item':refreshed_watch_item,
            'item_key':item_key, 'trakt_command':trakt_command, 'title_details_params':title_details_params,
            'event':lambda *a,**kw:None}
        bind(state, ns)
        state.snapshot_cache=PublicRowSnapshots(Path(folder)/'public.json', 'public-account-a', clock=clock, archive=True)
        state.home_snapshot_cache=HomeRowSnapshots(Path(folder)/'home.json', 'home-account-a', clock=clock)
        self.assertTrue(state.snapshot_cache.put(P, [ITEM]))
        self.assertTrue(state.home_snapshot_cache.put(H, [ITEM]))
        state.result_cache.put(P, [ITEM])
        state.result_cache.put('filtered-v1:'+P, [ITEM])
        refresh=extract(ROOT/'live_review.py', 'refresh_watch_status', ns, 'LiveReview')
        return state, props, calls, lambda:refresh(state)

    def test_refresh_preserves_disk_rows_but_reloads_visible_status_and_focus(self):
        with tempfile.TemporaryDirectory() as folder:
            state,props,calls,refresh=self.state(folder)
            stores=(state.snapshot_cache,state.home_snapshot_cache)
            before=[store.path.read_bytes() for store in stores]
            revisions=[store.revision for store in stores]
            refresh()
            self.assertEqual(calls,[P,H])
            self.assertEqual(state.selected['resume']['position'],75)
            self.assertEqual(props['position0'],1)
            self.assertEqual(props['focus'],900)
            self.assertFalse(state.actions_open)
            self.assertEqual(state.row_cache,{})
            self.assertIsNone(state.result_cache.get(P))
            self.assertIsNone(state.result_cache.get('filtered-v1:'+P))
            for store,path,raw,revision in zip(stores,(P,H),before,revisions):
                with self.subTest(path=path):
                    self.assertTrue(store.path.exists(), 'Watch refresh must retain the neutral disk display')
                    self.assertEqual(store.path.read_bytes(),raw)
                    self.assertEqual(store.revision,revision+1)
                    self.assertEqual(watch_state(store.get(path)[0])['state'],'unknown')
                    self.assertFalse(store.put(path,[dict(ITEM,title='Late')],revision=revision))
                    reopened=type(store)(store.path,store.scope,clock=lambda:1000)
                    self.assertEqual(reopened.get(path)[0]['title'],ITEM['title'])
            # Ordinary new-generation loads can republish freshly sanitized
            # displays and retain hydrated status only in the session cache.
            loaded=state.cached_row_items({'path':P})
            self.assertEqual(loaded[1]['resume']['position'],75)
            self.assertEqual(state.result_cache.get(P)[1]['resume']['position'],75)
            self.assertNotIn('resume',state.snapshot_cache.get(P)[1])

    def test_failed_provider_refresh_keeps_saved_neutral_rows_and_current_status(self):
        def offline(path):raise OSError('offline')
        with tempfile.TemporaryDirectory() as folder:
            state,props,calls,refresh=self.state(folder,offline)
            refresh()
            self.assertEqual(calls,[P,H])
            self.assertEqual(state.selected['resume']['position'],ITEM['resume']['position'])
            self.assertIn('could not refresh',props['notice'])
            self.assertIsNotNone(state.snapshot_cache.get(P), 'Watch refresh must retain public display rows')
            self.assertEqual(state.snapshot_cache.get(P)[0]['title'],ITEM['title'])
            self.assertEqual(state.home_snapshot_cache.get(H)[0]['title'],ITEM['title'])

    def test_refresh_keeps_original_age_and_account_scope_for_resident_and_archive(self):
        now=[1000]
        with tempfile.TemporaryDirectory() as folder:
            state,props,calls,refresh=self.state(folder,clock=lambda:now[0])
            public,home=state.snapshot_cache,state.home_snapshot_cache
            for page in range(2,public.max_rows+3):public.put(P+'&page='+str(page),[ITEM])
            self.assertNotIn(P,public.rows)
            archive=public._archive_store().path
            before=(public.path.read_bytes(),home.path.read_bytes(),archive.read_bytes())
            now[0]=87400
            refresh()
            self.assertTrue(public.path.exists(), 'Watch refresh must retain resident public rows')
            self.assertTrue(home.path.exists(), 'Watch refresh must retain owned Home rows')
            self.assertTrue(archive.exists(), 'Watch refresh must retain public visited history')
            self.assertEqual(before,(public.path.read_bytes(),home.path.read_bytes(),archive.read_bytes()))
            self.assertIsNotNone(public.get(P))
            self.assertIsNotNone(public.get(P+'&page='+str(public.max_rows+2)))
            self.assertIsNotNone(home.get(H))
            self.assertIsNotNone(PublicRowSnapshots(public.path,public.scope,clock=lambda:now[0],archive=True).get(P))
            self.assertIsNone(PublicRowSnapshots(public.path,'other-account',clock=lambda:now[0],archive=True).get(P))
            self.assertIsNone(HomeRowSnapshots(home.path,'other-account',clock=lambda:now[0]).get(H))
            self.assertFalse(home.archive_enabled)
            now[0]+=1
            self.assertIsNone(home.get(H))
            self.assertIsNotNone(public.get(P))
            now[0]=1000+30*86400+1
            self.assertIsNone(public.get(P))
            self.assertIsNone(public.get(P+'&page='+str(public.max_rows+2)))

    def test_running_and_queued_pre_refresh_workers_cannot_repopulate_caches(self):
        with tempfile.TemporaryDirectory() as folder:
            first=[True]
            def provider(path):
                if first[0]:
                    first[0]=False
                    refresh()
                    return [dict(ITEM,title='Retired worker')]
                return [ITEM]
            state,props,calls,refresh=self.state(folder,provider)
            state.result_cache.clear()
            revision=state.result_cache.revision
            with self.assertRaises(PageCancelled):state.cached_row_items({'path':P},expected_revision=revision)
            self.assertEqual(calls,[P,P,H])
            self.assertIsNone(state.result_cache.get(P))
            self.assertIsNotNone(state.snapshot_cache.get(P), 'Watch refresh must retain public display rows')
            self.assertEqual(state.snapshot_cache.get(P)[0]['title'],ITEM['title'])
            self.assertEqual(state.home_snapshot_cache.get(H)[0]['title'],ITEM['title'])
            self.assertEqual(state.cached_row_items({'path':P},expected_revision=revision),[])
            self.assertEqual(calls,[P,P,H])

    def test_default_invalidation_still_deletes_displays_and_public_history(self):
        with tempfile.TemporaryDirectory() as folder:
            state,props,calls,refresh=self.state(folder)
            public,home=state.snapshot_cache,state.home_snapshot_cache
            for page in range(2,public.max_rows+3):public.put(P+'&page='+str(page),[ITEM])
            self.assertIsNotNone(public.get(P))
            state.invalidate_row_results()
            self.assertIsNone(public.get(P))
            self.assertIsNone(home.get(H))
            self.assertFalse(public.path.exists())
            self.assertFalse(home.path.exists())
            self.assertFalse(public._archive_store().path.exists())
            self.assertIsNone(state.result_cache.get(P))

    def test_keep_home_scope_transition_still_clears_memory_but_keeps_owned_disk(self):
        with tempfile.TemporaryDirectory() as folder:
            state,props,calls,refresh=self.state(folder)
            home=state.home_snapshot_cache
            before=home.path.read_bytes()
            state.invalidate_row_results(keep_home=True)
            self.assertIsNone(home.get(H))
            self.assertEqual(home.path.read_bytes(),before)
            self.assertIsNotNone(HomeRowSnapshots(home.path,home.scope,clock=lambda:1000).get(H))
            self.assertFalse(state.snapshot_cache.path.exists())


if __name__=='__main__':unittest.main()
