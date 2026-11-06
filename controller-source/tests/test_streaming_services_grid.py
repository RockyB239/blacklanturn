"""Ordering, local pin persistence, and selection in the native service picker."""
import importlib.util
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from xml.etree import ElementTree

ADDON = Path(__file__).resolve().parents[1] / 'addon'
sys.path.insert(0, str(ADDON))
from streaming_services import ServiceCatalog, ServicePins, PAGE_SIZE


def card(number, name, region='US', kind='movie', icon=''):
    return {
        'file': 'plugin://plugin.video.themoviedb.helper/?info=discover'
                f'&tmdb_type={kind}&with_watch_providers={number}&watch_region={region}',
        'label': f'{name} · {region}',
        'art': {'icon': icon},
    }


class ServiceModelTests(unittest.TestCase):
    def test_featured_uses_pins_then_helper_priority_and_all_remains_alphabetical(self):
        beta, zulu, alpha = [card(number, name) for number, name in
                            ((10, 'Beta'), (1, 'Zulu'), (3, 'Álpha'))]
        catalog = ServiceCatalog([beta, zulu, alpha, card(10, 'Duplicate')])
        self.assertEqual([s.card for s in catalog.entries('featured', [])], [beta, zulu, alpha])
        self.assertEqual([s.card for s in catalog.entries('featured', ['US:3', 'CA:1'])],
                         [alpha, beta, zulu])
        self.assertEqual([s.card for s in catalog.entries('all', ['US:3'])], [alpha, beta, zulu])
        self.assertEqual([s.card for s in catalog.entries('pinned', ['US:1', 'US:3'])],
                         [zulu, alpha])

    def test_us_ranked_services_precede_unranked_and_do_not_affect_other_regions(self):
        netflix = card(8, 'Netflix')
        prime = card(9, 'Prime Video')
        free = card(1234, 'Free')
        hulu = card(15, 'Hulu')
        premium = card(2303, 'Paramount Plus Premium')
        essential = card(2616, 'Paramount Plus Essential')
        catalog = ServiceCatalog([free, hulu, netflix, premium, prime, essential])
        self.assertEqual([s.card for s in catalog.entries('featured', ['US:1234'])],
                         [free, prime, netflix, hulu, essential, premium])
        self.assertIn('Jan–Sep 2025', catalog.featured_source)
        self.assertEqual([s.card for s in ServiceCatalog([free, premium, hulu]).entries('featured', [])],
                         [hulu, premium, free])
        ca_netflix = card(8, 'Netflix', region='CA')
        ca_prime = card(9, 'Prime Video', region='CA')
        catalog = ServiceCatalog([ca_netflix, ca_prime])
        self.assertEqual([s.card for s in catalog.entries('featured', [])], [ca_netflix, ca_prime])
        self.assertNotIn('US interest', catalog.featured_source)

    def test_pins_are_persistent_across_media_types_and_isolated_by_profile_and_region(self):
        with TemporaryDirectory() as path:
            primary = Path(path) / 'primary'
            alternate = Path(path) / 'alternate'
            store = ServicePins(primary)
            self.assertFalse(primary.exists())
            self.assertTrue(store.toggle('US:3'))
            self.assertEqual(ServicePins(alternate).keys, ())
            pins = ServicePins(primary)
            self.assertEqual(pins.keys, ('US:3',))
            renamed = card(3, 'New name', kind='tv')
            catalog = ServiceCatalog([card(3, 'Same service', region='CA'), renamed])
            self.assertEqual([s.card for s in catalog.entries('pinned', pins.keys)], [renamed])
            self.assertFalse(pins.toggle('US:3'))
            self.assertEqual(ServicePins(primary).keys, ())

    def test_failed_or_corrupt_pin_storage_preserves_the_file_and_known_state(self):
        with TemporaryDirectory() as path:
            pins = ServicePins(path)
            pins.toggle('US:1')
            old = pins.path.read_bytes()
            with patch('streaming_services.os.replace', side_effect=OSError):
                with self.assertRaises(OSError):
                    pins.toggle('US:2')
            self.assertEqual(pins.keys, ('US:1',))
            self.assertEqual(pins.path.read_bytes(), old)
            self.assertEqual(list(pins.path.parent.iterdir()), [pins.path])
            pins.path.write_bytes(b'invalid')
            with self.assertRaises(ValueError):
                ServicePins(path).toggle('US:2')
            self.assertEqual(pins.path.read_bytes(), b'invalid')

    def test_later_pin_mutation_observes_prior_writer(self):
        with TemporaryDirectory() as path:
            original = ServicePins(path)
            later = ServicePins(path)
            original.toggle('US:1')
            later.toggle('US:2')
            self.assertEqual(ServicePins(path).keys, ('US:1', 'US:2'))


class Panel:
    def reset(self):
        self.items = []
        self.position = -1

    def addItems(self, items):
        self.items.extend(items)

    def selectItem(self, index):
        self.position = index

    def getSelectedPosition(self):
        return self.position


class Item:
    def __init__(self, label):
        self.label = label
        self.properties = {}

    def setArt(self, art):
        self.art = art

    def setProperty(self, key, value):
        self.properties[key] = value


class Dialog:
    def __init__(self, *args):
        self.panel = Panel()
        self.properties = {}
        self.closed = False

    def getControl(self, control):
        return self.panel

    def setProperty(self, key, value):
        self.properties[key] = value

    def setFocusId(self, target):
        self.focus = target

    def getFocusId(self):
        return self.focus

    def close(self):
        self.closed = True


class GridTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('streaming_services_ui_test', ADDON / 'streaming_services_ui.py')
        self.ui = importlib.util.module_from_spec(spec)
        self.commands = []
        fake_gui = SimpleNamespace(WindowXMLDialog=Dialog, ListItem=Item, Dialog=lambda: self)
        with patch.dict(sys.modules, {'xbmcgui': fake_gui}):
            spec.loader.exec_module(self.ui)
        profile = TemporaryDirectory()
        self.addCleanup(profile.cleanup)
        self.dialog = self.ui.StreamingServicesGrid()
        self.dialog.catalog = ServiceCatalog(
            [card(4000 - n, f'Service {n:03}') for n in range(298)])
        self.dialog.pins = ServicePins(profile.name)
        self.dialog.onInit()

    def contextmenu(self, choices):
        self.commands.append(choices)
        return 0

    def notification(self, heading, message):
        self.commands.append((heading, message))

    def test_featured_is_first_and_select_returns_original_provider_in_one_step(self):
        ui, grid = self.ui, self.dialog
        self.assertEqual(grid.focus, ui.GRID)
        self.assertEqual(len(grid.panel.items), PAGE_SIZE)
        self.assertEqual(grid.panel.items[0].label, 'Service 000')
        self.assertTrue(grid.panel.items[0].art['icon'].endswith('/services.png'))
        grid.panel.selectItem(6)
        grid.onClick(ui.GRID)
        self.assertEqual(grid.result, card(3994, 'Service 006'))
        self.assertTrue(grid.closed)

    def test_all_catalog_is_paged_without_materializing_offscreen_tiles(self):
        ui, grid = self.ui, self.dialog
        grid.onClick(ui.ALL)
        for _ in range(16):
            self.assertLessEqual(len(grid.panel.items), PAGE_SIZE)
            grid.onClick(ui.NEXT)
        self.assertEqual(len(grid.panel.items), 10)
        self.assertEqual(grid.panel.items[-1].label, 'Service 297')
        grid.onClick(ui.NEXT)
        self.assertEqual(grid.panel.items[-1].label, 'Service 297')
        grid.onClick(ui.PREVIOUS)
        self.assertEqual(grid.panel.items[0].label, 'Service 270')

    def test_manage_pins_retains_selected_service_when_featured_reorders(self):
        ui, grid = self.ui, self.dialog
        grid.panel.selectItem(10)
        grid.onClick(ui.MANAGE)
        self.assertEqual(grid.panel.position, 10)
        grid.onClick(ui.GRID)
        self.assertFalse(grid.closed)
        self.assertEqual(grid.panel.position, 0)
        self.assertEqual(grid.panel.items[0].label, 'Service 010')
        self.assertEqual(grid.panel.items[0].properties['pinned'], 'true')
        grid.onClick(ui.MANAGE)
        grid.onClick(ui.GRID)
        self.assertEqual(grid.result, card(3990, 'Service 010'))

    def test_reopen_restores_exact_tile_from_full_catalog(self):
        ui, grid = self.ui, self.dialog
        grid.initial_card = card(3780, 'Service 220')
        grid.onInit()
        self.assertEqual(grid.tab, ui.ALL)
        self.assertEqual(grid.page, 12)
        self.assertEqual(grid.panel.items[grid.panel.position].label, 'Service 220')

    def test_context_unpin_last_tile_returns_focus_to_pinned_tab(self):
        ui, grid = self.ui, self.dialog
        grid.onAction(SimpleNamespace(getId=lambda: 117))
        self.assertEqual(self.commands, [['Pin Service 000']])
        grid.onClick(ui.PINNED)
        grid.onAction(SimpleNamespace(getId=lambda: 117))
        self.assertEqual(self.commands[-1], ['Unpin Service 000'])
        self.assertEqual(grid.focus, ui.PINNED)
        self.assertFalse(grid.closed)
        grid.onAction(SimpleNamespace(getId=lambda: 92))
        self.assertTrue(grid.closed)
        self.assertIsNone(grid.result)

    def test_skin_uses_square_native_tiles_and_has_pin_page_and_back_navigation(self):
        ui = self.ui
        skin = ElementTree.parse(ADDON / 'resources/skins/Default/1080i/StreamingServicesGrid.xml')
        panel = skin.find(f".//control[@id='{ui.GRID}']")
        self.assertEqual(panel.get('type'), 'panel')
        for layout in ('itemlayout', 'focusedlayout'):
            tile = panel.find(layout)
            self.assertEqual(tile.get('width'), tile.get('height'))
            self.assertIn('ListItem.Art(icon)', ElementTree.tostring(tile, encoding='unicode'))
        self.assertEqual(panel.findtext('onright'), str(ui.MANAGE))
        for control in (ui.FEATURED, ui.PINNED, ui.ALL, ui.MANAGE, ui.PREVIOUS, ui.NEXT, ui.CANCEL):
            self.assertIsNotNone(skin.find(f".//control[@id='{control}']"))

    def test_failed_country_switch_retains_previous_grid_and_latest_country_wins(self):
        ui, grid = self.ui, self.dialog
        pending, saved = [], []
        grid.region_store = SimpleNamespace(
            cached=lambda kind, region: (None, False),
            select=lambda code: saved.append(code) or True,
            visible=lambda cards, kind, region: cards)
        grid.media_kind = 'movie'
        grid.request_catalog = lambda code, deliver, current: pending.append((code, deliver, current))
        grid.region_names = {'US': 'United States', 'CA': 'Canada', 'GB': 'United Kingdom'}
        grid.catalog_region = grid.requested_region = 'US'
        grid.switch_region('CA')
        self.assertEqual(grid.properties['region'], 'United States')
        grid.switch_region('GB')
        self.assertFalse(pending[0][2]())
        pending[0][1]([card(1, 'Canadian', region='CA')], 'fresh')
        self.assertEqual(grid.catalog_region, 'US')
        pending[1][1](None, 'error')
        self.assertIn('United Kingdom', grid.properties['regionStatus'])
        self.assertEqual(grid.properties['region'], 'United States')
        self.assertEqual(saved, [])
        grid.switch_region('GB')
        pending[-1][1]([], 'fresh')
        self.assertEqual(grid.properties['region'], 'United Kingdom')
        self.assertIn('No streaming services', grid.properties['catalogStatus'])
        self.assertEqual(saved, ['GB'])

    def test_cached_country_is_saved_before_the_user_can_select_a_tile(self):
        grid = self.dialog
        saved = []
        grid.region_store = SimpleNamespace(
            cached=lambda kind, region: ([card(1, 'Canadian', region='CA')], False),
            select=lambda code: saved.append(code) or True,
            selected=lambda default: saved[-1] if saved else default,
            visible=lambda cards, kind, region: cards)
        grid.media_kind = 'movie'
        grid.request_catalog = lambda *args: None
        grid.region_names = {'US': 'United States', 'CA': 'Canada'}
        grid.catalog_region = grid.requested_region = 'US'
        grid.switch_region('CA')
        self.assertEqual(saved, ['CA'])
        self.assertEqual(grid.properties['region'], 'Canada')

    def test_select_ignores_a_tile_from_the_old_rendered_grid(self):
        ui, grid = self.ui, self.dialog
        grid.read_labels = lambda keys: {keys[0]: 'CA:3994'}
        grid.panel.selectItem(6)
        grid.onClick(ui.GRID)
        self.assertIsNone(grid.result)
        self.assertFalse(grid.closed)
        grid.read_labels = lambda keys: {keys[0]: 'US:3994'}
        grid.onClick(ui.GRID)
        self.assertEqual(grid.result, card(3994, 'Service 006'))
