"""A recreated WindowXML must reject its previous setup/monitor workers.

These tests reproduce Python lifecycle ownership only, not a native Kodi crash.
The broken behavior is an old session loading Home or updating recreated controls.
"""
import ast
import copy
import hashlib
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import MethodType, SimpleNamespace
from urllib.parse import parse_qs, urlsplit


SOURCE = Path(__file__).parents[1] / 'addon' / 'live_review.py'
sys.path.insert(0, str(SOURCE.parent))
from live_core import PageHistory, valid_source, PreviewAttempts, title_details_params, merge_title_details, person_identity, show_identity
from live_runtime import read_controller_config
from row_feedback import RowResultCache, provider_page_label, row_message
from filtered_pages import provider_path
from preview_identity import TitleVerifier
from youtube_core import preview_path,video_id,automatic_preview,is_youtube,resume_allowed


class ExperimentLifecycle(unittest.TestCase):
    def state(self, folder, initialize=None, dialog_factory=None):
        queued = []
        effects = []

        class QueuedThread:
            def __init__(self, target, name=None, daemon=None, args=(), kwargs=None):
                self.target = target
                self.name = name
                self.args = args
                self.kwargs = kwargs or {}

            def start(self):
                queued.append(self)

            def run(self):
                self.target(*self.args, **self.kwargs)

        namespace = {
            'threading': SimpleNamespace(Thread=QueuedThread, RLock=threading.RLock,
                                         Lock=threading.Lock),
            'read_controller_config': read_controller_config,
            'time': time, 'copy': copy,'youtube_preview_path':preview_path,'youtube_video_id':video_id,'automatic_preview':automatic_preview,'is_youtube':is_youtube,'youtube_resume_allowed':resume_allowed,
            'json': __import__('json'),
            'xbmc': SimpleNamespace(getSkinDir=lambda: 'skin.blacklanturn.preview',
                                    getCondVisibility=lambda condition: False,
                                    Monitor=lambda: SimpleNamespace(abortRequested=lambda: False)),
            'STORE': Path(folder), 'PROFILE': Path(folder), 'rpc': lambda *a, **k: {},
            'event': lambda *a, **k: None,
            'tmdb': lambda info, kind='movie', **params: 'plugin://helper/' + info + '/' + kind,
            'migrate_navigation': lambda config: config,
            'migrate_pages': lambda config: config,
            'initialize_addons': initialize or (lambda: effects.append('initialize')),
            'BackendSettings': dialog_factory,
            'HomeUpdates':lambda *a:SimpleNamespace(tick=lambda:None),
            'ROOT': Path(folder),
            'parse_qs': parse_qs, 'urlsplit': urlsplit,
            'valid_source': valid_source, 'provider_page_label': provider_page_label,
            'provider_path': provider_path, 'row_message': row_message,
            'page_ahead_eligible': lambda path: False,
            'get_list': lambda path: [{'file': path + '/title'}],
            'PreviewAttempts': PreviewAttempts,
            'TitleVerifier': TitleVerifier,
            'cached_title_aliases':lambda *a:[],
            'xbmcvfs':SimpleNamespace(translatePath=lambda _:folder),
            'Path':Path,
            'preview_candidates': lambda trailer, videos, **kwargs: [trailer],
            'discovery_result': lambda item: None, 'show_identity': show_identity,
            'title_details_params': title_details_params, 'merge_title_details': merge_title_details,
            'person_identity': person_identity, 'rating_line': lambda item: '',
            'media_item': lambda item: item,
        }
        for name in ('PageAhead', 'PreviewRendererGuard', 'PreviewPlayer', 'HoverScroll',
                     'PageHistory', 'AnimeMetadata', 'PreviewFramingCache', 'RowResultCache'):
            namespace[name] = lambda *a, **k: SimpleNamespace()
        namespace.update(PageHistory=PageHistory, RowResultCache=RowResultCache)
        namespace['gui_labels']=lambda keys:{key:namespace['xbmc'].getInfoLabel(key) for key in keys}
        cls = next(node for node in ast.parse(SOURCE.read_text()).body
                   if isinstance(node, ast.ClassDef) and node.name == 'LiveReview')
        methods = [node for node in cls.body if isinstance(node, ast.FunctionDef)
                   and node.name in ('onInit', 'start', 'monitor', 'resume_settings', 'settings', 'load_path', 'preview', 'details', 'restore_browse')]
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(SOURCE), 'exec'), namespace)
        props = {}
        window = SimpleNamespace(
            setProperty=lambda key, value: props.__setitem__(key, value),
            getProperty=lambda key: props.get(key, ''),
            restore_preview_renderer=lambda: None, refresh_preview_setup=lambda: None,
            refresh_youtube_connection=lambda **k:None,
            configure_row_snapshots=lambda: False,
            refresh_navigation=lambda: effects.append('recreate_navigation'),
            apply_status=lambda: None, initialize_startup_focus=lambda: None,
            load_section=lambda: effects.append('load_home'),
            finish_loading=lambda reason: effects.append('setup_failed'),
            set_nav=lambda *a, **k: effects.append('set_nav'),
            setFocusId=lambda control: effects.append(('focus', control)),
            run_setting=lambda action: effects.append(('setting', action)),
            finish=lambda: effects.append('finish_current'),
            getControl=lambda control: SimpleNamespace(getSelectedPosition=lambda: 0,
                controlDown=lambda *a: None, controlRight=lambda *a: None, controlLeft=lambda *a: None,
                reset=lambda: None, addItems=lambda items: effects.append(('add_items', items))),
            getFocusId=lambda: 900,
            stop_preview=lambda: None,
            apply_row=lambda row, files, *a, **k: effects.append(('apply', files)),
            rating_identity=lambda item: None,
            play_preview_candidate=lambda url, *a: effects.append(('preview', url)),
        )
        window.update = lambda item: (setattr(window, 'selected', item), effects.append(('update', item)))
        for name in ('onInit', 'start', 'monitor', 'resume_settings', 'settings', 'load_path', 'preview', 'details', 'restore_browse'):
            setattr(window, name, MethodType(namespace[name], window))
        return window, queued, effects

    def test_old_queued_setup_cannot_load_recreated_window(self):
        with tempfile.TemporaryDirectory() as folder:
            window, queue, effects = self.state(folder)
            window.onInit()
            old_setup = next(t for t in queue if t.name == 'BlackLanturnLiveSetup')
            queue.clear()
            window.onInit()
            self.assertEqual(effects.count('recreate_navigation'), 2,
                             'Every onInit must initialize its recreated controls')
            effects.clear()
            old_setup.run()
            self.assertEqual(effects, [], 'Obsolete setup must not initialize or reload Home')
            next(t for t in queue if t.name == 'BlackLanturnLiveSetup').run()
            self.assertEqual(effects, ['initialize', 'load_home'])

    def test_running_setup_rechecks_owner_after_integration_wait(self):
        entered = threading.Event()
        release = threading.Event()
        finished = threading.Event()

        def initialize():
            entered.set()
            if not release.wait(2):
                raise RuntimeError('Test integration wait timed out')

        with tempfile.TemporaryDirectory() as folder:
            window, queue, effects = self.state(folder, initialize)
            window.onInit()
            old_setup = next(t for t in queue if t.name == 'BlackLanturnLiveSetup')

            def run():
                try:
                    old_setup.run()
                finally:
                    finished.set()

            worker = threading.Thread(target=run)
            worker.start()
            try:
                self.assertTrue(entered.wait(1))
                window.onInit()
                effects.clear()
            finally:
                release.set()
                worker.join(2)
            self.assertTrue(finished.is_set())
            self.assertEqual(effects, [], 'An old integration response must not reload new Home')

    def test_old_queued_monitor_cannot_update_recreated_controls(self):
        with tempfile.TemporaryDirectory() as folder:
            window, queue, effects = self.state(folder)
            window.onInit()
            old_monitor = next(t for t in queue if t.name == 'BlackLanturnLiveFocus')
            window.onInit()
            effects.clear()

            def update_width():
                effects.append('native_nav_width')
                window.alive = False  # End this one monitor turn after observing its effect.

            window.apply_nav_width = update_width
            old_monitor.run()
            self.assertEqual(effects, [], 'Old monitor must not touch the new control lifetime')

    def test_stale_setup_error_does_not_clear_new_loading_state(self):
        with tempfile.TemporaryDirectory() as folder:
            def initialize():
                window.onInit()
                effects.clear()
                raise RuntimeError('Old integration failed after window recreation')

            window, queue, effects = self.state(folder, initialize)
            window.onInit()
            next(t for t in queue if t.name == 'BlackLanturnLiveSetup').run()
            self.assertEqual(effects, [], 'A stale setup exception belongs to the old lifetime')
            self.assertEqual(window.getProperty('notice'), 'Loading live add-on lists…')

    def test_running_monitor_stops_after_recreation_during_idle_wait(self):
        with tempfile.TemporaryDirectory() as folder:
            window, queue, effects = self.state(folder)
            window.onInit()
            old_monitor = next(t for t in queue if t.name == 'BlackLanturnLiveFocus')
            window.settings_open = True
            sleeps = []

            def sleep(seconds):
                sleeps.append(seconds)
                if len(sleeps) == 1:
                    window.onInit()
                    effects.clear()

            def update_width():
                effects.append('native_nav_width')
                window.alive = False

            window.apply_nav_width = update_width
            window.monitor.__func__.__globals__['time'] = SimpleNamespace(
                monotonic=time.monotonic, sleep=sleep)
            old_monitor.run()
            self.assertEqual(effects, [], 'Old monitor must stop when its idle wait returns')
            self.assertEqual(len(sleeps), 1)

    def test_old_settings_return_worker_does_not_open_new_dialog(self):
        with tempfile.TemporaryDirectory() as folder:
            window, queue, effects = self.state(folder)
            window.resume_backend = {'section': 'Home', 'category': 0, 'row': 0}
            window.onInit()
            old_settings = next(t for t in queue if t.name == 'BlackLanturnSettingsReturn')
            window.onInit()
            window.settings = lambda *a: effects.append('open_settings')
            effects.clear()
            old_settings.run()
            self.assertEqual(effects, [], 'Old settings return must not open or refocus new controls')

    def test_old_modal_result_cannot_close_or_clear_new_settings_owner(self):
        with tempfile.TemporaryDirectory() as folder:
            dialog = SimpleNamespace(result='kodi:videos', category=9, row=9)

            def returned_after_recreation():
                window.onInit()
                window.settings_open = True
                effects.clear()
                dialog.handler('preview_mode')

            dialog.doModal = returned_after_recreation
            window, queue, effects = self.state(folder, dialog_factory=lambda *a: dialog)
            window.onInit()
            window.settings()
            self.assertEqual(effects, [], 'Old modal results must not act on recreated controls')
            self.assertTrue(window.settings_open, 'Old finally must not clear a newer settings owner')

    def test_old_page_request_cannot_reclaim_recreated_row_token(self):
        with tempfile.TemporaryDirectory() as folder:
            window, queue, effects = self.state(folder)

            def ready_home():
                # Home navigation advances once in load_section and once in
                # show_row_window; seed its visible row without provider I/O.
                window.generation += 2
                window.anime_metadata = None
                window.paths[0] = 'plugin://plugin.video.example/origin'
                window.rows[0] = [{'file': 'original'}]

            window.onInit()
            ready_home()
            window.load_path(0, 'plugin://plugin.video.example/old', 'Old')
            old_page = next(t for t in queue if t.name == 'BlackLanturnLivePage')
            queue.clear()
            window.onInit()
            ready_home()
            window.load_path(0, 'plugin://plugin.video.example/new', 'New')
            new_page = next(t for t in queue if t.name == 'BlackLanturnLivePage')
            effects.clear()
            old_page.run()
            self.assertEqual(effects, [], 'Reset counters must not revive an old page owner')
            new_page.run()
            self.assertEqual(window.paths[0], 'plugin://plugin.video.example/new')
            self.assertEqual([effect[0] for effect in effects], ['apply', 'focus'])

    def test_old_preview_lookup_cannot_dispatch_after_counter_reuse(self):
        with tempfile.TemporaryDirectory() as folder:
            window, queue, effects = self.state(folder)

            def select_title():
                window.player.isPlaying = lambda: False
                window.selected = {'file': 'same-title', 'trailer': 'plugin://plugin.video.youtube/play/?video_id=old'}
                window.stop_preview = lambda: setattr(window, 'preview_generation', window.preview_generation + 1)

            window.onInit()
            select_title()
            window.preview()
            old_preview = next(t for t in queue if t.name == 'BlackLanturnPreviewCandidates')
            queue.clear()
            window.onInit()
            select_title()
            window.preview()
            effects.clear()
            old_preview.run()
            self.assertEqual(effects, [], 'An old lookup must not take a new preview owner')
            next(t for t in queue if t.name == 'BlackLanturnPreviewCandidates').run()
            self.assertEqual([effect[0] for effect in effects], ['preview'])

    def test_old_details_cast_response_cannot_build_native_items_after_recreation(self):
        with tempfile.TemporaryDirectory() as folder:
            window, queue, effects = self.state(folder)
            item = {'file': 'plugin://plugin.video.themoviedb.helper/?info=details&tmdb_type=movie&tmdb_id=42', 'title': 'Same title'}
            window.onInit()
            window.details(item)
            old_details = next(t for t in queue if t.name == 'BlackLanturnLiveDetails')
            namespace = window.details.__func__.__globals__

            def provider(path):
                if '/cast/' not in path:
                    return [dict(item)]
                window.onInit()
                window.details(item)
                effects.clear()
                return [{'file': 'plugin://plugin.video.themoviedb.helper/?info=details&tmdb_type=person&tmdb_id=7', 'title': 'Actor'}]

            def native_item(**kwargs):
                effects.append('native_cast_created')
                return SimpleNamespace(setArt=lambda art: effects.append('native_cast_art'))

            namespace['get_list'] = provider
            namespace['xbmcgui'] = SimpleNamespace(ListItem=native_item)
            old_details.run()
            self.assertEqual(effects, [], 'Stale cast responses must stop before native ListItem creation')

    def test_monitor_rechecks_after_native_screen_read(self):
        with tempfile.TemporaryDirectory() as folder:
            window, queue, effects = self.state(folder)
            window.onInit()
            old_monitor = next(t for t in queue if t.name == 'BlackLanturnLiveFocus')
            window.setProperty('loading', 'false')
            window.apply_nav_width = lambda: None
            namespace = window.monitor.__func__.__globals__
            namespace['caption_fit_step'] = lambda width, height: 0
            original_set = window.setProperty

            def record(key, value):
                original_set(key, value)
                if key == 'captionFitStep':
                    effects.append(('stale_caption_write', value))

            def labels(key):
                if key == 'System.ScreenWidth':
                    window.onInit()
                    effects.clear()
                return '1920' if key.endswith('Width') else '1080'

            def stop_iteration():
                raise RuntimeError('Stop after observing any stale caption write')

            window.setProperty = record
            namespace['xbmc'].getInfoLabel = labels
            window.getFocusId = stop_iteration
            old_monitor.run()
            self.assertEqual(effects, [], 'Native screen reads may return in a new lifetime')

    def test_restore_stops_if_navigation_recreates_window(self):
        with tempfile.TemporaryDirectory() as folder:
            window, queue, effects = self.state(folder)
            state = {'mode': 'home', 'section': 'Home', 'active_page': None,
                'episode_browser_context': None, 'search_state': None,
                'properties': {'captionRows': 'false', 'row0': 'Old A', 'row1': 'Old B'},
                'rows': [[{'file': 'old-card'}], []], 'positions': [0, 0],
                'selected': None, 'focus': 900, 'last_row': 0, 'row_offset': 0}
            window.resume_backend = {'section': 'Home', 'category': 0, 'row': 0, 'browse_state': state}
            window.onInit()
            old_setup = next(t for t in queue if t.name == 'BlackLanturnLiveSetup')
            triggered = []

            def navigate():
                if not triggered:
                    triggered.append(True)
                    window.onInit()
                    effects.clear()

            window.refresh_navigation = navigate
            window.load_browse_sources = lambda: None
            window.restart_pending_rows = lambda: None
            window.getControl = lambda cid: SimpleNamespace(setHeight=lambda height: None,
                                                            getSelectedPosition=lambda: 0)
            old_setup.run()
            self.assertEqual(effects, [], 'An old restore must stop before applying old rows or focus')


class PrefetchEvidence(unittest.TestCase):
    def test_completion_identifies_exact_prepared_page_and_owner(self):
        target = 'plugin://plugin.video.themoviedb.helper/?info=popular&tmdb_type=movie&page=2'
        events = []
        fetched = []
        cls = next(node for node in ast.parse(SOURCE.read_text()).body
                   if isinstance(node, ast.ClassDef) and node.name == 'LiveReview')
        method = next(node for node in cls.body if isinstance(node, ast.FunctionDef)
                      and node.name == 'prefetch_next_page')
        namespace = {
            'time': SimpleNamespace(monotonic=lambda: 1.), 'hashlib': hashlib,
            'page_ahead_eligible': lambda path: path == target,
            'xbmcgui': SimpleNamespace(getCurrentWindowDialogId=lambda: 0),
            'event': lambda name, **fields: events.append((name, fields)),
        }
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(SOURCE), 'exec'), namespace)
        window = SimpleNamespace(
            page_ahead=SimpleNamespace(start=lambda key, fetch, current: fetch()),
            alive=True, mode='home', window_ready=[True, True], nav=False,
            settings_open=False, actions_open=False, owned_preview=False,
            player=SimpleNamespace(isPlaying=lambda: False),
            getProperty=lambda key: '', getFocusId=lambda: 900,
            dwell=0., rows=[[{'_page_control': 'next', 'file': target}], []],
            paths=['origin', ''], generation=7, result_cache=SimpleNamespace(revision=4),
            getControl=lambda cid: SimpleNamespace(getSelectedPosition=lambda: 0),
            page_files=lambda path, current, revision: fetched.append(path),
        )
        namespace['prefetch_next_page'](window)
        self.assertEqual(fetched, [target])
        self.assertEqual(events, [('next_page_prepared', {
            'seconds': 0., 'generation': 7, 'revision': 4,
            'target_sha256': hashlib.sha256(target.encode()).hexdigest(),
        })])


if __name__ == '__main__':
    unittest.main()
