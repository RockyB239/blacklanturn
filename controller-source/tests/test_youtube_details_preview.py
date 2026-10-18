"""YouTube details and preview focus use the controls visible to the user."""
import copy
import re
import threading
import unittest
from types import MethodType, SimpleNamespace
from xml.etree import ElementTree as E

from test_window_lifecycle import ROOT, extract
from live_core import (show_identity, title_details_params, episode_heading,
                       title_presentation, rating_badges, watch_state)
from episode_ui import episode_card
from search_ui import discovery_result, entity_kind, search_caption

VIDEO = {'file': 'plugin://plugin.video.youtube/play/?video_id=Abc_123-Xyz',
         'filetype': 'file', 'title': 'A video', 'label': 'A video',
         'studio': ['A channel'], 'plot': 'Video description', 'art': {'thumb': 'video.jpg'}}


class Control:
    def __init__(self, ident):
        self.ident = ident
        self.links = {}
        self.items = []
        self.label = ''
    def controlUp(self, other): self.links['up'] = other.ident
    def controlDown(self, other): self.links['down'] = other.ident
    def controlLeft(self, other): self.links['left'] = other.ident
    def controlRight(self, other): self.links['right'] = other.ident
    def reset(self): self.items = []
    def addItems(self, items): self.items.extend(items)
    def setLabel(self, label): self.label = label
    def setHeight(self, height): pass


def visible(node, props):
    """Evaluate the narrow Kodi visibility grammar used by these controls."""
    condition = node.findtext('visible', 'True')
    condition = re.sub(r'String.IsEqual\(Window.Property\((\w+)\),([^)]*)\)',
                       lambda m: str(props.get(m[1], '') == m[2]), condition)
    condition = condition.replace('[', '(').replace(']', ')').replace('+', ' and ').replace('|', ' or ').replace('!', ' not ')
    return eval(condition, {'__builtins__': {}})


class YouTubeDetailsPreview(unittest.TestCase):
    def state(self, mode='home', movie='auto', active='manual', ready='true'):
        props = {'page': mode, 'previewMode': active, 'previewsReady': ready,
                 'hasSelection': 'true', 'input': 'mouse', 'youtubeBrowser': 'true'}
        controls = {}
        jobs = []
        class Thread:
            def __init__(self, target, **kwargs): self.target = target
            def start(self): jobs.append(self.target)
        namespace = dict(show_identity=show_identity, title_details_params=title_details_params,
                         discovery_result=discovery_result, episode_heading=episode_heading,
                         title_presentation=title_presentation, episode_card=episode_card,
                         rating_badges=rating_badges, watch_state=watch_state,
                         entity_kind=entity_kind, search_caption=search_caption,
                         event=lambda *a, **k: None, threading=SimpleNamespace(Thread=Thread))
        window = SimpleNamespace(mode=mode, section='YouTube', preview_mode=movie, previews_ready=False,
            config={'PreviewMode': movie, 'YouTubePreviews': active == 'auto', 'Saved': []},
            selected=copy.deepcopy(VIDEO), episode_browser_context=None, row_offset=0,
            rows=[[VIDEO], []], window_ready=[True, True], browse_sources=[], alive=True,
            preview_dispatch_lock=threading.RLock(), rating_cache={}, nav=False,
            actions_open=False, person_context=None, search_state=None, discovery_stack=[],
            last_row=0, return_focus=901,
            setProperty=lambda k, v: props.__setitem__(k, v), getProperty=lambda k: props.get(k, ''),
            getControl=lambda cid: controls.setdefault(cid, Control(cid)),
            stop_preview=lambda: None, getFocusId=lambda: 901,
            setFocusId=lambda cid: setattr(window, 'focus', cid),
            rating_identity=lambda item: None, display_ratings=lambda ratings: None,
            save=lambda: None)
        for name in ('update', 'details', 'row_navigation', 'run_setting', 'onAction', 'arrow'):
            setattr(window, name, MethodType(extract(ROOT/'live_review.py', name, namespace, 'LiveReview'), window))
        return window, props, controls, jobs

    def test_youtube_details_keep_supported_content_without_movie_metadata_job(self):
        w, props, controls, jobs = self.state()
        w.details(copy.deepcopy(VIDEO))
        self.assertEqual(jobs, [], 'YouTube details must not start a movie metadata worker')
        self.assertEqual((props['title'], props['meta'], props['plot']), ('A video', 'A channel', 'Video description'))
        self.assertEqual(controls[101].links['right'], 105)
        self.assertEqual(controls[101].links['down'], 101, 'Down must not target a hidden movie list')
        self.assertEqual(w.return_focus, 901)

    def test_saved_youtube_details_do_not_focus_a_preview_hidden_by_current_section(self):
        root = E.parse(ROOT/'resources/skins/Default/1080i/LiveReview.xml').getroot()
        preview = root.find('.//control[@id="105"]')
        for ready, right, left in [('false', 103, 101), ('true', 105, 105)]:
            with self.subTest(ready=ready):
                w, props, controls, jobs = self.state(ready=ready)
                w.section = 'My Stuff'
                w.previews_ready = ready == 'true'
                props['youtubeBrowser'] = 'false'
                w.details(copy.deepcopy(VIDEO))
                self.assertEqual(visible(preview, props), ready == 'true')
                self.assertEqual(controls[101].links['right'], right)
                self.assertEqual(controls[103].links['left'], left)

    def test_youtube_details_hide_movie_sections_and_their_scroll_arrows(self):
        w, props, controls, jobs = self.state()
        w.details(copy.deepcopy(VIDEO))
        root = E.parse(ROOT/'resources/skins/Default/1080i/LiveReview.xml').getroot()
        for node in root.iter('control'):
            if node.get('id') in ('3000', '3100', '700', '701', '712', '713', '720', '721') or node.findtext('label') in ('Cast', 'More like this'):
                with self.subTest(control=node.get('id') or node.findtext('label')):
                    self.assertFalse(visible(node, props))
                    self.assertTrue(visible(node, {**props, 'youtubeDetails': 'false'}), 'Movie details must retain their sections')

    def test_home_preview_focus_matches_active_visibility_for_both_independent_modes(self):
        root = E.parse(ROOT/'resources/skins/Default/1080i/LiveReview.xml').getroot()
        preview = root.find('.//control[@id="105"]')
        for movie, active, ready, target in [('auto', 'manual', 'true', 105), ('manual', 'auto', 'true', 103), ('auto', 'manual', 'false', 103)]:
            with self.subTest(movie=movie, active=active, ready=ready):
                w, props, controls, jobs = self.state(movie=movie, active=active, ready=ready)
                if ready == 'false':
                    w.section = 'Movies'
                    w.previews_ready = False
                w.row_navigation()
                self.assertEqual(controls[103].links['right'], target)
                self.assertEqual(visible(preview, props), target == 105)
                w.update(copy.deepcopy(VIDEO))
                self.assertEqual(controls[103].links['right'], target)

    def test_movie_preview_setup_refresh_keeps_youtube_video_preview_available(self):
        from pathlib import Path
        from preview_setup import configured
        w, props, controls, jobs = self.state()
        namespace = dict(xbmcaddon=SimpleNamespace(Addon=lambda _: SimpleNamespace(getSetting=lambda _: '')),
                         rpc=lambda *a: {}, PROFILE=Path('/nonexistent-blacklanturn-test'),
                         preview_configured=configured)
        extract(ROOT/'live_review.py', 'refresh_preview_setup', namespace, 'LiveReview')(w)
        self.assertFalse(w.previews_ready, 'Missing movie API setup must still be recorded')
        self.assertEqual(props['previewsReady'], 'true', 'Connected YouTube video preview does not require movie trailer API setup')
        w.row_navigation()
        self.assertEqual(controls[103].links['right'], 105)

    def test_movie_preference_change_preserves_active_youtube_mode(self):
        for active in ('manual', 'auto'):
            with self.subTest(active=active):
                w, props, controls, jobs = self.state(movie='manual', active=active)
                w.run_setting('preview_mode')
                self.assertEqual(w.config['PreviewMode'], 'auto')
                self.assertEqual(props['previewMode'], active)
                self.assertEqual(w.config['YouTubePreviews'], active == 'auto')

    def test_youtube_setting_updates_focus_without_changing_movie_preference(self):
        w, props, controls, jobs = self.state(movie='auto', active='auto')
        w.row_navigation()
        w.run_setting('youtube_previews')
        self.assertEqual(props['previewMode'], 'manual')
        self.assertEqual(w.preview_mode, 'auto')
        self.assertEqual(controls[103].links['right'], 105)

    def test_back_from_youtube_details_retains_captions_and_original_row_focus(self):
        w, props, controls, jobs = self.state()
        w.details(copy.deepcopy(VIDEO))
        w.onAction(SimpleNamespace(getId=lambda: 92))
        self.assertEqual(w.mode, 'home')
        self.assertEqual(w.focus, 901)
        self.assertEqual(props['captionRows'], 'true')

    def test_back_restores_row_focus_after_caption_layout_rebuild(self):
        w, props, controls, jobs = self.state()
        w.details(copy.deepcopy(VIDEO))
        set_property = w.setProperty
        def rebuild_layout(key, value):
            set_property(key, value)
            if key == 'captionRows':
                # Kodi discards focus on the row while its caption layout changes.
                w.focus = None
        w.setProperty = rebuild_layout
        w.onAction(SimpleNamespace(getId=lambda: 92))
        self.assertEqual(w.focus, 901, 'Back must restore the row after rebuilding its caption layout')
        self.assertEqual(props['captionRows'], 'true')

    def test_mouse_scroll_cannot_leave_youtube_details_for_hidden_movie_rows(self):
        w, props, controls, jobs = self.state()
        w.details(copy.deepcopy(VIDEO))
        w.arrow(701)
        self.assertEqual(props['scroll'], 'top')


if __name__ == '__main__': unittest.main()
