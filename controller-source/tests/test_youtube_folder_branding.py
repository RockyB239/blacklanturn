"""Category folders use the selected brand pack; playable media keeps its art."""
import copy
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from xml.etree import ElementTree as E

sys.path.insert(0, str(Path(__file__).parents[1] / 'addon'))
import icon_packs
from youtube_rows import YouTubeRows
from native_list_fixture import media_functions

ROOT = Path(__file__).parents[1] / 'addon'
BASE = 'plugin://plugin.video.youtube'


class YouTubeFolderBranding(unittest.TestCase):
    def setUp(self):
        icon_packs.configure([])
        self.addCleanup(icon_packs.configure, [])

    def test_nested_subscription_folders_use_same_selected_pack_as_short_and_live_categories(self):
        from youtube_folder_artwork import display_items
        for pack in ('sculpted-silver','smoked-glass'):
            for route in ('/special/my_subscriptions','/special/my_subscriptions_filtered/'):
                original={'label':'Localized subscriptions','file':BASE+route+'?category_label=My+Subscriptions','filetype':'directory','art':{'thumb':'special://home/addons/plugin.video.youtube/resources/media/new_uploads.png'}}
                saved=copy.deepcopy(original);item=display_items([original],{'IconPack':pack})[0]
                expected=icon_packs.icon_path(ROOT,'subscriptions',pack)
                self.assertEqual(item['art']['thumb'],expected)
                self.assertEqual(item['_youtube_folder_icon'],expected)
                self.assertEqual(original,saved)

    def state(self, pack='sculpted-silver'):
        path = BASE + '/special/my_subscriptions'
        return SimpleNamespace(section='YouTube', paths=[path, ''],
                               page_definitions=[{'path': path}],
                               config={'IconPack': pack})

    def folder(self, route, image='shorts.png'):
        return {'file': BASE + route, 'filetype': 'directory', 'label': 'Category',
                'art': {'thumb': '/device/addons/plugin.video.youtube/resources/media/' + image,
                        'fanart': 'https://provider.example/generic-youtube-background.jpg'}}

    def prepare(self, state, files):
        return YouTubeRows.prepare_youtube_row(state, 0, files)

    def test_subscription_categories_share_selected_brand_on_card_and_header(self):
        # Omitting display routing restores mismatched provider icons/fanart.
        render = media_functions()['media_item']
        for pack in ('sculpted-silver', 'smoked-glass', 'original'):
            for route, slug in (('/special/my_subscriptions/shorts/', 'youtube'),
                                ('/special/my_subscriptions/live/', 'live-tv')):
                with self.subTest(pack=pack, route=route):
                    state = self.state(pack)
                    source = self.folder(route, 'shorts.png' if slug == 'youtube' else 'live.png')
                    before = copy.deepcopy(source)
                    displayed = self.prepare(state, [source])[0]
                    expected = str(ROOT / ('resources/media/' if pack == 'original' else
                                            'resources/icon-packs/packs/' + pack + '/') / (slug + '.png'))
                    tile = render(displayed)
                    self.assertEqual(tile.art['youtubefolder'], expected)
                    self.assertEqual(displayed['art']['fanart'], expected)
                    self.assertEqual(displayed['art']['landscape'], expected)
                    self.assertTrue(Path(expected).is_file())
                    self.assertEqual(displayed['file'], before['file'])
                    self.assertEqual(source, before)
                    self.assertEqual(state.youtube_pages[state.paths[0]]['items'][0], before)
                    self.assertEqual(state.config, {'IconPack': pack})

    def test_semantic_routes_do_not_depend_on_labels_or_provider_icon_uri_format(self):
        routes = [('/special/my_subscriptions_filtered/shorts/', 'youtube'),
                  ('/channel/UC123/shorts/', 'youtube'),
                  ('/playlist/UUSH123/', 'youtube'),
                  ('/channel/UC123/playlist/UUSH123/', 'youtube'),
                  ('/channel/UC123/live/', 'live-tv'),
                  ('/playlist/UULV123/', 'live-tv'),
                  ('/special/live/', 'live-tv'),
                  ('/special/upcoming_live/', 'live-tv'),
                  ('/special/completed_live/', 'live-tv'),
                  ('/kodion/search/query/?q=space&event_type=live', 'live-tv')]
        for route, slug in routes:
            with self.subTest(route=route):
                source = self.folder(route)
                source['label'] = '[B]Localized category[/B]'
                source['art']['thumb'] = 'image://special%3A%2F%2Fhome%2Faddons%2Fplugin.video.youtube%2Fresources%2Fmedia%2Fshorts.png/'
                displayed = self.prepare(self.state('smoked-glass'), [source])[0]
                self.assertEqual(Path(displayed['art']['thumb']).name, slug + '.png')
                self.assertIn('/smoked-glass/', displayed['art']['thumb'])

    def test_actual_video_and_unrelated_provider_folder_art_stay_genuine(self):
        video = {'file': BASE + '/play/?video_id=Abc_123-Xyz&resume=true',
                 'filetype': 'file', 'label': 'Shorts live video', 'playcount': 1,
                 'resume': {'position': 17, 'total': 60},
                 'art': {'thumb': 'https://i.ytimg.com/vi/Abc_123-Xyz/mqdefault.jpg',
                         'fanart': 'https://provider.example/video.jpg'}}
        playlist = self.folder('/playlist/PL_real/')
        playlist['label'] = 'Shorts'
        playlist['art']['thumb'] = 'https://provider.example/actual-playlist.jpg'
        channel = self.folder('/channel/UC123/')
        other = self.folder('/special/my_subscriptions/live/')
        other['file'] = other['file'].replace('plugin.video.youtube', 'plugin.video.other')
        files = [video, playlist, channel, other]
        before = copy.deepcopy(files)
        self.assertEqual(self.prepare(self.state(), files), before)
        self.assertEqual(files, before)

    def test_reused_page_resolves_new_pack_without_storing_branded_paths(self):
        source = self.folder('/special/my_subscriptions/shorts/')
        state = self.state()
        state.page_definitions[0]['youtube_cursor'] = {'path': state.paths[0] + '?page=2'}
        first = self.prepare(state, [source])
        state.config['IconPack'] = 'smoked-glass'
        second = self.prepare(state, first)
        self.assertIn('/sculpted-silver/', first[0]['art']['thumb'])
        self.assertIn('/smoked-glass/', second[0]['art']['thumb'])
        self.assertEqual(state.youtube_pages[state.paths[0]]['items'], [source])
        self.assertTrue(second[-1]['_youtube_more'])

    def test_pack_missing_category_asset_falls_back_to_valid_existing_media(self):
        state = self.state()
        icon_packs._assets['sculpted-silver'].pop('youtube')
        displayed = self.prepare(state, [self.folder('/special/my_subscriptions/shorts/')])[0]
        self.assertEqual(displayed['art']['thumb'], str(ROOT / 'resources/media/youtube.png'))
        self.assertTrue(Path(displayed['art']['thumb']).is_file())

    def test_selected_category_sets_header_identity_and_video_or_other_folder_clears_it(self):
        from test_youtube_details_preview import YouTubeDetailsPreview, VIDEO
        window, props, _, _ = YouTubeDetailsPreview().state()
        folder = self.prepare(self.state(), [self.folder('/special/my_subscriptions/shorts/')])[0]
        window.update(folder)
        self.assertEqual(props.get('youtubeCategoryFolder'), 'true')
        self.assertEqual(props['hero'], folder['art']['thumb'])
        window.update(copy.deepcopy(VIDEO))
        self.assertEqual(props.get('youtubeCategoryFolder'), 'false')
        window.update(folder)
        window.update(self.folder('/channel/UC123/'))
        self.assertEqual(props.get('youtubeCategoryFolder'), 'false')

    def test_new_section_clears_category_marker_even_for_personal_update_override(self):
        from test_window_lifecycle import extract
        props={'youtubeCategoryFolder':'true'}
        state=SimpleNamespace(setProperty=lambda k,v:props.update({k:v}),show_row_window=lambda *a:None)
        method=extract(ROOT/'live_review.py','set_rows',{},'LiveReview')
        method(state,[{'label':'Fight Zone live','path':'personal'}])
        self.assertEqual(props['youtubeCategoryFolder'],'false')

    def test_folder_header_uses_contained_icon_and_regular_heroes_keep_their_video_shape(self):
        from test_youtube_details_preview import visible
        document = E.parse(ROOT / 'resources/skins/Default/1080i/LiveReview.xml')
        heroes = [node for node in document.iter('control')
                  if node.findtext('texture') == '$INFO[Window.Property(hero)]']
        props = {'page': 'home', 'heroCompact': 'true', 'youtubeCategoryFolder': 'true',
                 'preview': '', 'previewFade': 'true'}
        displayed = [node for node in heroes if visible(node, props)]
        self.assertEqual(len(displayed), 1)
        self.assertEqual(displayed[0].findtext('aspectratio'), 'keep')
        self.assertGreaterEqual(int(displayed[0].findtext('left')), 1200)
        self.assertLessEqual(int(displayed[0].findtext('left')) + int(displayed[0].findtext('width')), 1850)
        for compact in ('true', 'false'):
            regular = [node for node in heroes if visible(node, {**props, 'heroCompact': compact,
                                                                  'youtubeCategoryFolder': 'false',
                                                                  'previewFade': 'false'})]
            self.assertEqual(len(regular), 1)
            self.assertEqual(regular[0].findtext('aspectratio'), 'scale')
        self.assertFalse(any(visible(node, {**props, 'preview': 'playing'}) for node in heroes))
        self.assertFalse(any(visible(node, {**props, 'page': 'settings', 'previewFade': 'false'})
                             for node in heroes if node.findtext('aspectratio') == 'keep'))


if __name__ == '__main__':
    unittest.main()
