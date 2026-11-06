"""Check that the provider bridge completes only authoritative empty shelves."""
import ast
import re
from pathlib import Path
from types import SimpleNamespace
import unittest

SOURCE = (Path(__file__).parents[2] /
          'compatibility/streaming-shelves188/helper/lists_discover.py')
EMPTY = {'page': 1, 'results': [], 'total_pages': 0, 'total_results': 0}


class ListStandardProperties:
    cache_name_tuple = ('original',)

    def get_uncached_items(self):
        items = self.get_page_items(self.page, self.response)
        return {'items': items, 'pages': 0, 'count': 0}

    def get_page_items(self, page, response):
        return []


class ListStandard:
    def get_directory_items(self):
        return self.items


class ProviderShelfEmpty(unittest.TestCase):
    def state(self, response=EMPTY, items=None, handle=1, **params):
        names = {'ListDiscover', 'ListDiscoverStandardProperties', 'provider_shelf_route'}
        nodes = [node for node in ast.parse(SOURCE.read_text()).body
                 if getattr(node, 'name', '') in names]
        ns = {'ListStandard': ListStandard, 'ListDiscoverProperties': object,
              'ListStandardProperties': ListStandardProperties, 'cached_property': property, 're': re}
        for node in nodes:
            if getattr(node, 'name', '') == 'ListDiscoverStandardProperties':
                node.bases = node.bases[1:]
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE), 'exec'), ns)
        discover = ns['ListDiscover']()
        calls = []
        discover.items = items
        discover.handle = handle
        discover.is_localonly = False
        discover.params = {'tmdb_type': 'tv', 'widget': 'false', 'with_id': 'true', 'nextpage': 'true',
                           'with_watch_providers': '11',
                           'watch_region': 'US', 'with_genres': '10759', **params}
        properties = discover.list_properties = ns['ListDiscoverStandardProperties']()
        properties.discover_params = discover.params
        properties.page = 1
        properties.response = response
        discover.sync_playdata = SimpleNamespace(pre_sync_join=lambda: calls.append('join'))
        discover.finish_container = lambda: calls.append('finish')
        return discover, calls

    def test_successful_empty_directory_completes_after_sync(self):
        discover, calls = self.state()
        discover.list_properties.unconfigured_item_data = discover.list_properties.get_uncached_items()
        self.assertIsNone(discover.get_directory_items())
        self.assertEqual(calls, ['join', 'finish'])

    def test_unverified_responses_do_not_complete_directory(self):
        for response in (None, {}, dict(EMPTY, success=False), dict(EMPTY, page=2),
                         dict(EMPTY, total_pages=False), dict(EMPTY, total_results=4),
                         dict(EMPTY, results=[{'id': 7}])):
            with self.subTest(response=response):
                discover, calls = self.state(response)
                with self.assertRaises(RuntimeError):
                    discover.list_properties.get_uncached_items()
                self.assertNotIn('finish', calls)

    def test_unverified_cached_empty_does_not_complete(self):
        discover, calls = self.state()
        discover.list_properties.unconfigured_item_data = {'items': [], 'pages': 0, 'count': 0}
        with self.assertRaises(RuntimeError):
            discover.get_directory_items()
        self.assertEqual(calls, [])

    def test_populated_provider_keeps_original_items_without_an_extra_request(self):
        items = [{'title': 'Title', 'file': 'title'}]
        discover, calls = self.state(items=items)
        self.assertIs(discover.get_directory_items(), items)
        self.assertEqual(calls, [])

    def test_other_discover_and_internal_routes_do_not_complete_early(self):
        for options in ({'handle': -1}, {'with_watch_providers': ''}, {'with_watch_providers': '11|8'},
                        {'widget': 'true'}, {'nextpage': 'false'}, {'with_id': ''},
                        {'watch_region': 'USA'}, {'page': '2'}):
            with self.subTest(options=options):
                discover, calls = self.state(**options)
                self.assertIsNone(discover.get_directory_items())
                self.assertEqual(calls, [])
                if options.get('handle') != -1:
                    self.assertEqual(discover.list_properties.cache_name_tuple, ('original',))
