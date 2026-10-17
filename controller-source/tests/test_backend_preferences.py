"""Exercise settings callbacks and labels without a native Kodi window."""
import ast
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import MethodType, SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).parents[1] / 'addon'
sys.path.insert(0, str(ROOT))
from backend_core import SETTINGS_GROUPS


def method(filename, class_name, name, namespace):
    tree = ast.parse((ROOT / filename).read_text(encoding='utf-8'))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name)
    node = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), filename, 'exec'), namespace)
    return namespace[name]


class ListControl:
    def __init__(self, position=0):
        self.position = position
        self.items = []

    def reset(self):
        self.items = []

    def addItems(self, items):
        self.items.extend(items)

    def getSelectedPosition(self):
        return self.position

    def selectItem(self, position):
        self.position = position


class BackendPreferences(unittest.TestCase):
    def hub(self, config, handler=lambda action: None):
        category = next(i for i, group in enumerate(SETTINGS_GROUPS) if group[0] == 'Previews')
        category_control = ListControl(category)
        rows = ListControl(2)
        hub = SimpleNamespace(config=config, preview_mode='manual', loaded_category=-1,
                              category=category, row=2, handler=handler,
                              getControl=lambda cid: category_control if cid == 100 else rows,
                              setProperty=lambda *args: None, setFocusId=lambda cid: None)
        ns = {'SETTINGS_GROUPS': SETTINGS_GROUPS,
              'xbmcgui': SimpleNamespace(ListItem=lambda **kwargs: SimpleNamespace(**kwargs))}
        for name in ('populate', 'onClick'):
            setattr(hub, name, MethodType(method('backend_ui.py', 'BackendSettings', name, ns), hub))
        hub.populate(category)
        return hub, rows

    def test_default_and_saved_english_preference_describe_current_selection(self):
        for config in ({}, {'PreviewLanguage': 'en'}):
            with self.subTest(config=config):
                _, rows = self.hub(config)
                self.assertEqual(rows.items[2].label2, 'Current preference: English first, other languages as fallback')

    def test_provider_order_preference_describes_current_selection(self):
        _, rows = self.hub({'PreviewLanguage': ''})
        self.assertEqual(rows.items[2].label2, 'Current preference: Provider order')

    def test_chooser_persists_each_selection_and_refreshes_visible_label(self):
        for previous, choice, expected, description in (
                ('en', 1, '', 'Provider order'),
                ('', 0, 'en', 'English first, other languages as fallback')):
            with self.subTest(choice=choice), tempfile.TemporaryDirectory() as temp:
                config = {'PreviewLanguage': previous}
                selected = []
                stopped = []
                ns = {'json': json, 'STORE': Path(temp), 'event': lambda *args, **kwargs: None,
                      'xbmcgui': SimpleNamespace(Dialog=lambda: SimpleNamespace(
                          select=lambda *args, **kwargs: selected.append(kwargs['preselect']) or choice))}
                save = method('live_review.py', 'LiveReview', 'save', ns)
                run = method('live_review.py', 'LiveReview', 'run_setting', ns)
                owner = SimpleNamespace(config=config, preview_cache={'old': ['candidate']},
                                        stop_preview=lambda: stopped.append(True))
                owner.save = lambda: save(owner, invalidate=False)
                hub, rows = self.hub(config, lambda action: run(owner, action))
                hub.onClick(200)
                self.assertEqual(config['PreviewLanguage'], expected)
                self.assertEqual(json.loads((Path(temp) / 'rows.json').read_text())['PreviewLanguage'], expected)
                self.assertEqual(rows.items[2].label2, 'Current preference: ' + description)
                self.assertEqual(selected, [0 if previous == 'en' else 1])
                self.assertEqual(stopped, [True])
                self.assertEqual(owner.preview_cache, {})
                self.assertEqual((hub.row, rows.position), (2, 2))

    def test_cancel_preserves_preference_and_does_not_save_or_stop_preview(self):
        config = {'PreviewLanguage': ''}
        ns = {'event': lambda *args, **kwargs: None,
              'xbmcgui': SimpleNamespace(Dialog=lambda: SimpleNamespace(select=lambda *args, **kwargs: -1))}
        run = method('live_review.py', 'LiveReview', 'run_setting', ns)
        forbidden = lambda: self.fail('Cancel must not save or stop the preview')
        owner = SimpleNamespace(config=config, preview_cache={'old': ['candidate']}, save=forbidden,
                                stop_preview=forbidden)
        hub, rows = self.hub(config, lambda action: run(owner, action))
        hub.onClick(200)
        self.assertEqual(config, {'PreviewLanguage': ''})
        self.assertEqual(owner.preview_cache, {'old': ['candidate']})
        self.assertEqual(rows.items[2].label2, 'Current preference: Provider order')

    def test_help_reads_utf8_when_device_default_encoding_is_ascii(self):
        shown = []
        ns = {'ROOT': ROOT, 'event': lambda *args, **kwargs: None,
              'xbmcgui': SimpleNamespace(Dialog=lambda: SimpleNamespace(textviewer=lambda *args: shown.append(args)))}
        run = method('live_review.py', 'LiveReview', 'run_setting', ns)
        original_read = Path.read_text

        def device_read(path, encoding=None, errors=None):
            return original_read(path, encoding=encoding or 'ascii', errors=errors)

        with patch.object(Path, 'read_text', device_read):
            try:
                run(SimpleNamespace(), 'help')
            except UnicodeDecodeError as error:
                self.fail('Help must decode its UTF-8 file independently of the device locale: ' + str(error))
        self.assertEqual(shown, [('BlackLanturn · Help', original_read(ROOT / 'HELP.txt', encoding='utf-8'))])


if __name__ == '__main__':
    unittest.main()
