import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from light_home_fast import CACHE, load_cache, save_cache, projected_rows

class StartupCache(unittest.TestCase):
    def test_proof_rejects_changed_account_and_damaged_file(self):
        with TemporaryDirectory() as folder:
            store = Path(folder)
            original = {'time': 1000, 'rows': [{'items':[{'file':'a'}]}, {'items':[{'file':'b'}]}]}
            rows = [[['a',{}]], [['b',{}]]]
            schema = {'hash':'test-schema', 'keys':['trakt_token']}
            self.assertTrue(save_cache(store, schema, 'unchanged', original, rows))
            self.assertEqual(load_cache(store, lambda _: 'unchanged', now=1010), (original, rows))
            self.assertIsNone(load_cache(store, lambda _: 'other-account', now=1010))
            self.assertIsNone(load_cache(store, lambda _: 'unchanged', now=200000))
            path = store/CACHE
            body = json.loads(path.read_bytes())
            body['payload'] += ' '
            path.write_text(json.dumps(body))
            self.assertIsNone(load_cache(store, lambda _: 'unchanged', now=1010))

    def test_current_session_controls_hidden_titles_order_and_paging(self):
        first, second, next_page = ({'file':s} for s in ('a','b','page-2'))
        record = {'rows':[{'items':[first,next_page,second]}]}
        prepared = [[
            [first, {'label':'A'}],
            [dict(next_page,_page_control='next'), {'label':'Next'}],
            [second, {'label':'B'}],
        ]]
        prefs = SimpleNamespace(apply=lambda _: [second,next_page])
        models, cards = projected_rows(record, prepared, prefs)[0]
        self.assertEqual([item['file'] for item in models], ['b','page-2'])
        self.assertEqual([card['label'] for card in cards], ['B','Next'])

if __name__=='__main__':
    unittest.main()
