"""Optional YouTube and library work must stay outside idle browser startup."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ADDON = Path(__file__).resolve().parents[1] / 'addon'


class OptionalFeatureImports(unittest.TestCase):
    def probe(self, code):
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run(
                [sys.executable, '-I', '-S', '-c',
                 'import sys\nsys.path.insert(0,sys.argv[1])\n' + code,
                 str(ADDON), folder], capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_youtube_browser_import_does_not_initialize_provider_or_history_reader(self):
        self.probe('''
import threading
before = set(threading.enumerate())
import youtube_browser
assert not {'youtube_provider', 'sqlite3', 'pickle'} & sys.modules.keys(), 'Idle browser loaded provider/history work'
assert set(threading.enumerate()) == before
# First provider use still observes its cancellation contract.
assert youtube_browser.load_home_rows(lambda: False, refresh=True, resolved_items=[{'id': 'unchanged'}]) == []
assert 'youtube_provider' in sys.modules
import youtube_rows, youtube_saved_runtime
for load in (youtube_rows.load_shelf_page, youtube_rows.load_related_page):
    try:
        load({}, lambda: False)
    except RuntimeError as exc:
        assert str(exc) == 'YouTube request retired'
    else:
        raise AssertionError('Retired page request was accepted')
original = [{'file': 'unrelated', 'playcount': 3}]
fresh = youtube_saved_runtime.provider_watch(original)
assert fresh == original and fresh is not original and fresh[0] is not original[0]
''')

    def test_saved_display_reads_leave_history_dependencies_unloaded(self):
        self.probe('''
from pathlib import Path
import youtube_saved
path = Path(sys.argv[2]) / 'display.json'
path.write_text('{"version":1,"scope":"test","rows":[]}')
before = path.read_bytes()
assert youtube_saved.SavedRows(path, 'test').get() == []
assert path.read_bytes() == before
assert not {'sqlite3', 'pickle'} & sys.modules.keys(), 'Display-only read loaded SQL/pickle'
# First history use keeps missing/disabled history behavior and input ownership.
item = {'file':'plugin://plugin.video.youtube/play/?video_id=00000000001', 'playcount':8, 'runtime':100}
fresh = youtube_saved.current_watch([item], path.with_suffix('.sqlite'), enabled=False)
assert fresh[0]['playcount'] == 0 and fresh[0]['resume'] == {'position':0,'total':100}
assert item['playcount'] == 8
assert not path.with_suffix('.sqlite').exists()
''')

    def test_library_import_and_context_actions_do_not_load_collection_storage(self):
        self.probe('''
import library_ui
window = library_ui.LibraryActions()
window.section = 'Home'
window.config = {}
assert window.library_context_actions() == []
assert 'personal_library' not in sys.modules, 'Idle browser loaded collection storage'
assert window.personal_rows() == []
assert 'personal_library' in sys.modules
''')


if __name__ == '__main__':
    unittest.main()
