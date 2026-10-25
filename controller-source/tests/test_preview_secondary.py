"""Missing provider previews use one private first-page lookup, with strict identity screening."""
import importlib
from pathlib import Path
import sys
import threading
import unittest
from urllib.parse import parse_qs, urlsplit
sys.path.insert(0, str(Path(__file__).parents[1] / 'addon'))
from preview_identity import TitleVerifier
try:
    secondary = importlib.import_module('preview_fallback')
except ModuleNotFoundError:
    secondary = None


def row(number, title='Example Official Trailer'):
    return {'file': 'plugin://plugin.video.youtube/play/?video_id=' + f'{number:011d}',
            'filetype': 'file', 'label': title, 'title': title}


class SecondaryPreviewTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(secondary, 'A bounded secondary preview lookup is missing')
        self.now = [100.]
        self.lookups = []
        self.rows = [row(1)]
        self.titles = {'00000000001': 'Example Official Trailer'}
        self.fetches = []
        def fetch(key):
            self.fetches.append(key)
            return self.titles.get(key, '')
        self.verifier = TitleVerifier(fetcher=fetch, clock=lambda: self.now[0])
        self.lookup = secondary.SecondaryPreviewLookup(clock=lambda: self.now[0])
    def load(self, path):
        self.lookups.append(path)
        return self.rows
    def run_lookup(self, **kwargs):
        return self.lookup.lookup((), ('tv', '123'), ('Example',), self.load, self.verifier,
                                  **kwargs)
    def test_explicit_conflicting_remake_year_is_rejected_for_movie_and_tv(self):
        for kind,alias,expected,actual in [('movie','The Thing',1982,'The Thing (2011) Official Trailer'),('tv','Doctor Who',2005,'Doctor Who (1963) Season 1 Trailer')]:
            with self.subTest(kind=kind):
                self.rows=[row(1,actual)];self.titles['00000000001']=actual
                self.assertEqual(self.lookup.lookup((),(kind,'123'),(alias,),self.load,self.verifier,year=expected),[])

    def test_matching_year_or_year_after_trailer_marker_can_be_approved(self):
        for actual in ('Example (1982) Official Trailer','Example Official Trailer | Restored 2024'):
            self.rows=[row(1,actual)];verifier=TitleVerifier(fetcher=lambda _:actual)
            lookup=secondary.SecondaryPreviewLookup()
            self.assertEqual(lookup.lookup((),('movie','123'),('Example',),self.load,verifier,year=1982),[row(1)['file']])

    def test_correct_actual_title_is_approved_by_existing_verifier(self):
        self.assertEqual(self.run_lookup(), [row(1)['file']])
        query = parse_qs(urlsplit(self.lookups[0]).query)
        self.assertEqual(urlsplit(self.lookups[0]).netloc, 'plugin.video.youtube')
        self.assertEqual(query['q'], ['"Example" season 1 official trailer'])
        self.assertEqual(query['incognito'], ['true'])
        self.assertEqual(query['hide_folders'], ['true'])
        self.assertNotIn('page_token', query)
    def test_generic_search_label_cannot_hide_wrong_actual_series(self):
        self.titles['00000000001'] = 'Examples Official Trailer'
        self.assertEqual(self.run_lookup(), [])
    def test_approved_normal_result_skips_all_secondary_work(self):
        self.assertEqual(self.lookup.lookup([row(9)['file']], ('tv', '123'), ('Example',),
                                           self.load, self.verifier), [row(9)['file']])
        self.assertEqual(self.lookups, [])
        self.assertEqual(self.fetches, [])
    def test_success_cache_is_short_lived_and_identity_scoped(self):
        self.run_lookup(); self.run_lookup()
        self.assertEqual(len(self.lookups), 1)
        self.assertEqual(self.lookup.lookup((), ('tv', '124'), ('Example',), self.load, self.verifier), [row(1)['file']])
        self.assertEqual(len(self.lookups), 2)
        self.now[0] += 301
        self.run_lookup()
        self.assertEqual(len(self.lookups), 3)
    def test_empty_result_is_cached_briefly_then_retried(self):
        self.rows = []
        self.assertEqual(self.run_lookup(), [])
        self.rows = [row(1)]
        self.assertEqual(self.run_lookup(), [])
        self.assertEqual(len(self.lookups), 1)
        self.now[0] += 31
        self.assertEqual(self.run_lookup(), [row(1)['file']])
    def test_network_error_cannot_be_cached_for_days(self):
        def broken(path):
            self.lookups.append(path)
            raise TimeoutError('provider stalled')
        self.assertEqual(self.lookup.lookup((), ('tv', '123'), ('Example',), broken, self.verifier), [])
        self.assertEqual(self.run_lookup(), [])
        self.now[0] += 16
        self.assertEqual(self.run_lookup(), [row(1)['file']])
    def test_missing_title_evidence_recovers_after_short_negative_cache(self):
        self.titles.clear()
        self.assertEqual(self.run_lookup(), [])
        self.titles['00000000001'] = 'Example Official Trailer'
        self.now[0] += 31
        self.assertEqual(self.run_lookup(), [row(1)['file']])
    def test_first_season_is_ranked_before_latest_season(self):
        self.rows = [row(1, 'Example Season 12 Official Trailer'), row(2, 'Example Season 1 Trailer')]
        self.titles.update({'00000000001': self.rows[0]['label'], '00000000002': self.rows[1]['label']})
        self.assertEqual(self.run_lookup(), [row(2)['file'], row(1)['file']])
    def test_first_season_preference_survives_language_ranking(self):
        self.rows = [dict(row(1, 'Example Season 12 Official Trailer'), language='en'),
                     row(2, 'Example Season 1 Trailer')]
        self.titles.update({'00000000001': self.rows[0]['label'], '00000000002': self.rows[1]['label']})
        self.assertEqual(self.run_lookup(), [row(2)['file'], row(1)['file']])
    def test_movie_search_includes_release_year_without_season_terms(self):
        self.lookup.lookup((), ('movie', '123'), ('Example',), self.load, self.verifier, year=1982)
        query = parse_qs(urlsplit(self.lookups[0]).query)
        self.assertEqual(query['q'], ['"Example" 1982 official trailer'])
    def test_oldest_identity_cache_entry_is_evicted_after_128_titles(self):
        self.rows = []
        for ident in range(1, 130):
            self.lookup.lookup((), ('tv', str(ident)), ('Example',), self.load, self.verifier)
        self.assertEqual(len(self.lookups), 129)
        self.lookup.lookup((), ('tv', '1'), ('Example',), self.load, self.verifier)
        self.assertEqual(len(self.lookups), 130)
    def test_cancel_while_waiting_for_search_slot_never_starts_queued_request(self):
        entered = threading.Event(); release = threading.Event(); cancelled = threading.Event()
        results = []
        def slow(path):
            entered.set()
            release.wait(2)
            return self.load(path)
        owner = threading.Thread(target=lambda: self.lookup.lookup((), ('tv', '123'), ('Example',), slow, self.verifier))
        owner.start()
        self.assertTrue(entered.wait(1))
        queued = threading.Thread(target=lambda: results.append(self.lookup.lookup(
            (), ('tv', '124'), ('Example',), self.load, self.verifier, valid=lambda: not cancelled.is_set())))
        queued.start(); cancelled.set(); queued.join(1)
        try:
            self.assertFalse(queued.is_alive())
            self.assertEqual(results, [[]])
            self.assertEqual(self.lookups, [])
        finally:
            release.set(); owner.join(2); queued.join(2)
    def test_only_six_unique_candidates_from_first_page_are_verified(self):
        self.rows = [row(n) for n in range(1, 50)]
        self.titles = {f'{n:011d}': 'Example Trailer' for n in range(1, 50)}
        self.assertEqual(len(self.run_lookup()), 6)
        self.assertEqual(len(self.fetches), 6)
        self.assertEqual(len(self.lookups), 1)
    def test_pagination_folders_and_external_urls_are_never_followed(self):
        self.rows = [{'file': 'https://untrusted.example/watch', 'filetype': 'file'},
                     {'file': 'plugin://plugin.video.youtube/kodion/search/query/?q=other&page=2', 'filetype': 'directory'},
                     dict(row(1), filetype='directory')]
        self.assertEqual(self.run_lookup(), [])
        self.assertEqual(self.fetches, [])
    def test_incomplete_or_unsafe_identity_never_looks_up(self):
        for identity, aliases in [(None, ('Example',)), (('person', '123'), ('Example',)),
                                  (('tv', '../123'), ('Example',)), (('tv', '123'), ())]:
            self.assertEqual(self.lookup.lookup((), identity, aliases, self.load, self.verifier), [])
        self.assertEqual(self.lookups, [])
    def test_cancel_before_lookup_skips_even_a_cached_result(self):
        self.run_lookup()
        self.assertEqual(self.run_lookup(valid=lambda: False), [])
        self.assertEqual(len(self.lookups), 1)
    def test_cancel_during_provider_discards_result_and_does_not_cache(self):
        current = [True]
        def cancelled(path):
            current[0] = False
            return self.load(path)
        self.assertEqual(self.lookup.lookup((), ('tv', '123'), ('Example',), cancelled,
                                           self.verifier, valid=lambda: current[0]), [])
        self.assertEqual(self.fetches, [])
        self.assertEqual(self.run_lookup(), [row(1)['file']])
        self.assertEqual(len(self.lookups), 2)
    def test_cancel_during_verification_discards_all_results(self):
        current = [True]
        def cancelled(key):
            current[0] = False
            return 'Example Official Trailer'
        verifier = TitleVerifier(fetcher=cancelled)
        self.assertEqual(self.lookup.lookup((), ('tv', '123'), ('Example',), self.load,
                                           verifier, valid=lambda: current[0]), [])
    def test_cache_returns_copies_to_keep_playback_attempts_private(self):
        found = self.run_lookup(); found.append(row(9)['file'])
        self.assertEqual(self.run_lookup(), [row(1)['file']])

if __name__ == '__main__': unittest.main()
