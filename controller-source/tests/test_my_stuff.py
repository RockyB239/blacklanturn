import ast, os, sys, unittest
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit, urlencode
sys.path.insert(0, str(Path(__file__).parents[1] / 'addon'))
import live_core
from contextlib import nullcontext

ROOT = Path(__file__).parents[1]
def method(name, extra):
    source = Path(os.environ.get('BL_CONTROLLER_SOURCE', str(ROOT / 'addon/live_review.py')))
    cls = next(n for n in ast.parse(source.read_text()).body if isinstance(n, ast.ClassDef) and n.name == 'LiveReview')
    node = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == name)
    ns = dict(extra)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), 'exec'), ns)
    return ns[name]

def tmdb(info, kind='movie'):
    return 'plugin://plugin.video.themoviedb.helper/?' + urlencode(dict(info=info, tmdb_type=kind, nextpage='true', widget='true'))

class MyStuff(unittest.TestCase):
    def rows(self, saved):
        fn = getattr(live_core, 'my_stuff_rows', None)
        self.assertIsNotNone(fn, 'My Stuff has no Trakt row definitions')
        return fn(saved, tmdb)

    def test_two_account_watchlists_and_device_saves_remain_distinct(self):
        saved = [{'file': 'local-title'}]
        rows = self.rows(saved)
        self.assertEqual([r['label'] for r in rows], ['Saved on this device', 'Trakt Watchlist · Movies', 'Trakt Watchlist · Shows'])
        for row, kind in zip(rows[1:], ('movie', 'tv')):
            q = parse_qs(urlsplit(row['path']).query)
            self.assertEqual(q['info'], ['trakt_watchlist'])
            self.assertEqual(q['tmdb_type'], [kind])
            self.assertEqual(q['nextpage'], ['true'])
            self.assertNotIn('user', q)
        self.assertEqual(rows[0]['local_items'], saved)
        self.assertEqual(rows[0]['path'], '')

    def test_device_saves_never_request_a_provider_or_mutate_saved_metadata(self):
        fn = getattr(live_core, 'row_items', None)
        self.assertIsNotNone(fn, 'Local saved rows cannot use the common row loader')
        saved = [{'file': 'local-title', 'art': {'poster': 'original'}}]
        items = fn(self.rows(saved)[0], lambda path: self.fail('Local saves invoked a provider'))
        items[0]['art']['poster'] = 'changed'
        self.assertEqual(saved[0]['art']['poster'], 'original')

    def test_watchlist_uses_exact_provider_path_and_propagates_failure(self):
        fn = getattr(live_core, 'row_items', None)
        self.assertIsNotNone(fn, 'Row loader is missing')
        row = self.rows([])[1]
        def provider(path):
            self.assertEqual(path, row['path'])
            raise ValueError('Unavailable')
        with self.assertRaisesRegex(ValueError, 'Unavailable'):
            fn(row, provider)

    def test_my_stuff_enters_common_scrollable_row_flow(self):
        calls = []
        state = SimpleNamespace(section='My Stuff', config={'Saved': []}, generation=0,
            setProperty=lambda *args: None, getControl=lambda cid: SimpleNamespace(setHeight=lambda height: None),
            load_browse_sources=lambda: None, set_rows=lambda rows: calls.append(rows),
            apply_row=lambda *args: self.fail('Legacy one-row My Stuff flow used'))
        fn = method('load_section', {'PageHistory': live_core.PageHistory, 'my_stuff_rows': getattr(live_core, 'my_stuff_rows', lambda saved, maker: []), 'tmdb': tmdb})
        fn(state)
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(calls[0]), 3)

    def test_common_row_worker_loads_local_items_without_provider(self):
        source = Path(os.environ.get('BL_CONTROLLER_SOURCE', str(ROOT / 'addon/live_review.py'))).read_text()
        cls = next(n for n in ast.parse(source).body if isinstance(n, ast.ClassDef) and n.name == 'LiveReview')
        outer = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'request_row_loads')
        calls = []
        state = SimpleNamespace(alive=True, generation=1, list_lock=nullcontext(),paths=['',''],path_tokens={},
            apply_row=lambda slot, items, label, position=0: calls.append(items),
            setProperty=lambda *args: None, failed_paths={}, row_states={})
        ns = {'self': state, 'generation': 1, 'pending': [(0, {'path': '', 'label': 'Saved on this device', 'local_items': [{'file': 'saved'}]})],
            'revision':0, 'focus_slot': None, 'get_list': lambda path: (_ for _ in ()).throw(ValueError('Local saves cannot invoke the provider')),
            'row_items': getattr(live_core, 'row_items', None), 'row_message': lambda *args: '', 'event': lambda *args, **kwargs: None}
        ns['threading']=SimpleNamespace(Thread=lambda target,**kwargs:SimpleNamespace(start=target))
        ns['submit_latest']=lambda owner,work:work()
        exec(compile(ast.Module(body=[outer], type_ignores=[]), str(ROOT), 'exec'), ns)
        from cache_fixture import bind
        bind(state,ns)
        ns['request_row_loads'](state,ns['pending'])
        self.assertEqual(calls, [[{'file': 'saved'}]])

if __name__ == '__main__': unittest.main()
