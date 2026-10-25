"""Public video titles must agree with the selected title before playback."""
import importlib
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
import threading
import time
import unittest
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).parents[1] / 'addon'))
from live_core import preview_candidates
try:
    identity = importlib.import_module('preview_identity')
except ModuleNotFoundError:
    identity = None


def video(number):
    return 'plugin://plugin.video.youtube/play/?video_id=' + f'{number:011d}'


class Response:
    def __init__(self, raw):
        self.raw = raw
        self.read_sizes = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size):
        self.read_sizes.append(size)
        return self.raw[:size]


class PreviewIdentity(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(identity, 'Preview identity verification is missing')

    def current_filter(self, verifier, urls, titles, valid):
        try:
            return verifier.filter(urls, titles, valid=valid)
        except TypeError as exc:
            self.fail('Cancellation-aware preview verification is missing: ' + str(exc))

    def test_already_cancelled_filter_never_fetches(self):
        calls = []
        verifier = identity.TitleVerifier(fetcher=lambda key: calls.append(key) or 'Example Trailer')
        self.assertEqual(self.current_filter(verifier, [video(1)], ['Example'], lambda: False), [])
        self.assertEqual(calls, [])

    def test_cancelled_while_waiting_for_shared_slot_never_fetches(self):
        calls = []
        both_started = threading.Event()
        waiting = threading.Event()
        release = threading.Event()
        cancelled = threading.Event()
        lock = threading.Lock()

        class ObservableSlots:
            def __init__(self):
                self.slots = threading.BoundedSemaphore(2)
                self.active = 0

            def __enter__(self):
                with lock:
                    if self.active == 2:
                        waiting.set()
                self.slots.acquire()
                with lock:
                    self.active += 1

            def __exit__(self, *args):
                with lock:
                    self.active -= 1
                self.slots.release()

        def fetch(key):
            with lock:
                calls.append(key)
                if len(calls) == 2:
                    both_started.set()
            release.wait(2)
            return 'Example Trailer'

        verifier = identity.TitleVerifier(fetcher=fetch)
        self.assertEqual(self.current_filter(verifier, [], [], lambda: True), [])
        verifier._network_slots = ObservableSlots()
        with ThreadPoolExecutor(max_workers=2) as callers:
            owner = callers.submit(verifier.filter, [video(1), video(2)], ['Example'])
            try:
                self.assertTrue(both_started.wait(1), 'Two owner requests did not start')
                stale = callers.submit(self.current_filter, verifier, [video(3)], ['Example'], lambda: not cancelled.is_set())
                self.assertTrue(waiting.wait(1), 'The stale request never waited for an occupied slot')
                cancelled.set()
            finally:
                release.set()
            self.assertEqual(owner.result(2), [video(1), video(2)])
            self.assertEqual(stale.result(2), [])
        self.assertEqual(set(calls), {'00000000001', '00000000002'})

    def test_cancellation_during_fetch_discards_otherwise_matching_result(self):
        cancelled = threading.Event()
        def fetch(key):
            cancelled.set()
            return 'Example Trailer'
        verifier = identity.TitleVerifier(fetcher=fetch)
        self.assertEqual(self.current_filter(verifier, [video(1)], ['Example'], lambda: not cancelled.is_set()), [])

    def test_generic_provider_label_cannot_hide_wrong_actual_series_title(self):
        verifier = identity.TitleVerifier(fetcher=lambda key: 'American Horror Stories Season 1 Trailer | Rotten Tomatoes TV')
        url = 'plugin://plugin.video.youtube/play/?video_id=nLJR2twdK00'
        # Recorded provider association for tv.1413; generic label hides the error.
        ranked = preview_candidates('', [{'file': url, 'label': 'Season 1 Trailer'}])
        self.assertEqual(ranked, [url])
        self.assertEqual(verifier.filter(ranked, ['American Horror Story']), [])

    def test_story_and_stories_are_rejected_in_both_directions(self):
        for selected, actual in [('American Horror Story', 'American Horror Stories Trailer'),
                                 ('American Horror Stories', 'American Horror Story Trailer')]:
            with self.subTest(selected=selected):
                verifier = identity.TitleVerifier(fetcher=lambda key: actual)
                self.assertEqual(verifier.filter([video(1)], [selected]), [])

    def test_series_title_matches_season_trailer(self):
        verifier = identity.TitleVerifier(fetcher=lambda key: 'American Horror Story | Season 12 Official Trailer')
        self.assertEqual(verifier.filter([video(1)], ['American Horror Story']), [video(1)])

    def test_installment_number_is_season_metadata_after_the_exact_series_title(self):
        # FX uses "Installment" for American Horror Story's numbered seasons.
        verifier = identity.TitleVerifier(fetcher=lambda key: 'American Horror Story | Installment 13 Official Teaser | FX')
        self.assertEqual(verifier.filter([video(1)], ['American Horror Story'], media_type='tv'), [video(1)])
        self.assertEqual(verifier.filter([video(1)], ['American Horror Stories'], media_type='tv'), [])

    def test_installment_number_is_not_identity_evidence_without_a_tv_type(self):
        verifier = identity.TitleVerifier(fetcher=lambda key: 'It Installment 2 Official Trailer')
        self.assertEqual(verifier.filter([video(1)], ['It']), [])
        for media_type in (None, 'movie', 'unknown'):
            with self.subTest(media_type=media_type):
                self.assertEqual(verifier.filter([video(1)], ['It'], media_type=media_type), [])

    def test_final_and_red_band_trailer_labels_preserve_the_exact_title(self):
        # Public studio title fixtures: Paramount nRwLyKIBNU8; Sony rze8QYwWGMs.
        for selected, actual in [
                ('Scream', 'Scream (2022) - Final Trailer - Paramount Pictures'),
                ('Scream', 'Scream - Official Final Trailer (2022)'),
                ('Kraven the Hunter', 'KRAVEN THE HUNTER – Official Red Band Trailer (HD)')]:
            with self.subTest(actual=actual):
                verifier = identity.TitleVerifier(fetcher=lambda key: actual)
                self.assertEqual(verifier.filter([video(1)], [selected]), [video(1)])

    def test_trailer_modifiers_cannot_hide_title_extensions(self):
        for selected, actual in [
                ('It', 'It Ends With Us Final Trailer'),
                ('Dune', 'Dune Part Two Official Red Band Trailer'),
                ('Dune', 'Dune Final Cut Official Trailer'),
                ('American Horror Story', 'American Horror Stories Installment 3 Official Teaser'),
                ('American Horror Story', 'American Horror Story Installment Unknown Official Teaser')]:
            with self.subTest(actual=actual):
                verifier = identity.TitleVerifier(fetcher=lambda key: actual)
                self.assertEqual(verifier.filter([video(1)], [selected]), [])

    def test_short_titles_cannot_match_inside_another_title(self):
        for selected, actual in [('Up', "DON'T LOOK UP | Official Trailer"),
                                 ('It', 'It Ends With Us | Official Trailer')]:
            with self.subTest(selected=selected):
                verifier = identity.TitleVerifier(fetcher=lambda key: actual)
                self.assertEqual(verifier.filter([video(1)], [selected]), [])

    def test_franchise_prefix_cannot_approve_a_different_sequel_or_series(self):
        for selected, actual in [('Dune', 'Dune: Part Two | Official Trailer'),
                                 ('CSI', 'CSI: Miami | Official Trailer'),
                                 ('Star Trek', 'Star Trek: Picard | Official Trailer'),
                                 ('Up', 'Up 2 | Official Trailer'),
                                 ('It', 'IT Chapter Two | Official Trailer')]:
            with self.subTest(selected=selected):
                verifier = identity.TitleVerifier(fetcher=lambda key: actual)
                self.assertEqual(verifier.filter([video(1)], [selected]), [])

    def test_specific_season_subtitle_requires_an_explicit_full_alias(self):
        verifier = identity.TitleVerifier(fetcher=lambda key: 'American Horror Story: Delicate | Season 12 Official Trailer')
        self.assertEqual(verifier.filter([video(1)], ['American Horror Story']), [])
        self.assertEqual(verifier.filter([video(1)], ['American Horror Story', 'American Horror Story: Delicate']), [video(1)])

    def test_exact_title_allows_only_recognized_trailer_year_and_quality_suffixes(self):
        for selected, actual in [('Up', 'UP (2009) Official Trailer'),
                                 ('It', 'IT Trailer'),
                                 ('Dune: Part Two', 'Dune: Part Two | Official Trailer'),
                                 ('Dune', 'Dune Official Trailer #1 (2021) 4K UHD'),
                                 ('Up', 'UP (2009)'),
                                 ('Up', 'Up (2009) | Official Trailer | Pixar'),
                                 ('The Haunting of Hill House', 'The Haunting of Hill House | Official Trailer [HD] | Netflix'),
                                 ('American Horror Story', 'American Horror Story Season 12 Teaser Trailer')]:
            with self.subTest(actual=actual):
                verifier = identity.TitleVerifier(fetcher=lambda key: actual)
                self.assertEqual(verifier.filter([video(1)], [selected]), [video(1)])

    def test_clearly_delimited_official_trailer_prefix_does_not_break_title_anchor(self):
        for actual in ['Official Trailer: UP (2009)', 'Official Trailer | UP (2009)', 'Official Teaser - UP (2009)']:
            with self.subTest(actual=actual):
                verifier = identity.TitleVerifier(fetcher=lambda key: actual)
                self.assertEqual(verifier.filter([video(1)], ['Up']), [video(1)])

    def test_delimiters_cannot_hide_unknown_title_extensions_before_trailer_marker(self):
        for selected, actual in [('It', 'It - Ends With Us Official Trailer'),
                                 ('Dune', 'Dune | Part Two Official Trailer'),
                                 ('It', 'Official Trailer | It Ends With Us')]:
            with self.subTest(selected=selected):
                verifier = identity.TitleVerifier(fetcher=lambda key: actual)
                self.assertEqual(verifier.filter([video(1)], [selected]), [])

    def test_unicode_punctuation_and_localized_aliases_match(self):
        for titles, actual in [(['Amélie'], 'AMELIE — Official Trailer'),
                               (['Spider-Man'], 'Spider Man: Official Trailer'),
                               (['La casa de papel', 'Money Heist'], 'Money Heist | Official Trailer'),
                               (['進撃の巨人'], '進撃の巨人 Official Trailer')]:
            with self.subTest(titles=titles):
                verifier = identity.TitleVerifier(fetcher=lambda key: actual)
                self.assertEqual(verifier.filter([video(1)], titles), [video(1)])

    def test_partial_words_noncontiguous_words_and_reordered_words_do_not_match(self):
        for actual in ['American Horror Storytelling Trailer', 'American New Horror Story Trailer', 'Horror American Story Trailer']:
            with self.subTest(actual=actual):
                verifier = identity.TitleVerifier(fetcher=lambda key: actual)
                self.assertEqual(verifier.filter([video(1)], ['American Horror Story']), [])

    def test_empty_titles_do_not_fetch_or_approve(self):
        calls = []
        verifier = identity.TitleVerifier(fetcher=lambda key: calls.append(key) or 'Trailer')
        for titles in [[], [''], [' - '], None]:
            self.assertEqual(verifier.filter([video(1)], titles), [])
        self.assertEqual(calls, [])

    def test_invalid_video_urls_never_reach_fetcher(self):
        calls = []
        verifier = identity.TitleVerifier(fetcher=lambda key: calls.append(key) or 'Example Trailer')
        invalid = ['https://www.youtube.com/watch?v=00000000001',
                   'plugin://evil.example/play/?video_id=00000000001',
                   'plugin://plugin.video.youtube/play/?video_id=short',
                   'plugin://plugin.video.youtube/play/?video_id=000000000001',
                   'plugin://plugin.video.youtube/play/?video_id=0000000000!',
                   'plugin://plugin.video.youtube/play/?video_id=00000000001&video_id=00000000002',
                   'plugin://plugin.video.youtube/play/?video_id=https%3A%2F%2Fevil.example',
                   None, '']
        self.assertEqual(verifier.filter(invalid, ['Example']), [])
        self.assertEqual(calls, [])

    def test_approval_preserves_rank_order_and_deduplicates_video_ids(self):
        def fetch(key):
            if key == '00000000001':
                time.sleep(.02)
            return 'Wrong Show Trailer' if key == '00000000002' else 'Example Trailer'
        verifier = identity.TitleVerifier(fetcher=fetch)
        self.assertEqual(verifier.filter([video(1), video(2), video(3), video(1) + '&x=1'], ['Example']), [video(1), video(3)])

    def test_only_first_six_valid_distinct_candidates_are_checked(self):
        calls = []
        verifier = identity.TitleVerifier(fetcher=lambda key: calls.append(key) or 'Example Trailer')
        urls = [video(n) for n in range(1, 8)]
        self.assertEqual(verifier.filter(['invalid', urls[0], urls[0]] + urls[1:], ['Example']), urls[:6])
        self.assertEqual(set(calls), {f'{n:011d}' for n in range(1, 7)})

    def test_at_most_two_concurrent_network_workers(self):
        lock = threading.Lock()
        counts = {'active': 0, 'peak': 0}
        def fetch(key):
            with lock:
                counts['active'] += 1
                counts['peak'] = max(counts['peak'], counts['active'])
            time.sleep(.02)
            with lock:
                counts['active'] -= 1
            return 'Example Trailer'
        verifier = identity.TitleVerifier(fetcher=fetch)
        self.assertEqual(verifier.filter([video(n) for n in range(6)], ['Example']), [video(n) for n in range(6)])
        self.assertEqual(counts['peak'], 2)

    def test_fetch_errors_and_non_title_results_fail_closed(self):
        def unavailable(key):
            raise OSError('network unavailable')
        for fetcher in [unavailable, lambda key: None, lambda key: {}, lambda key: '', lambda key: '   ']:
            with self.subTest(fetcher=fetcher):
                self.assertEqual(identity.TitleVerifier(fetcher=fetcher).filter([video(1)], ['Example']), [])

    def test_success_cache_expires_after_six_hours_and_rechecks_actual_title(self):
        now = [0]
        calls = []
        verifier = identity.TitleVerifier(fetcher=lambda key: calls.append(key) or ('Example Trailer' if len(calls) == 1 else 'Wrong Trailer'), clock=lambda: now[0])
        self.assertEqual(verifier.filter([video(1)], ['Example']), [video(1)])
        now[0] = 21599
        self.assertEqual(verifier.filter([video(1)], ['Example']), [video(1)])
        self.assertEqual(len(calls), 1)
        now[0] = 21600
        self.assertEqual(verifier.filter([video(1)], ['Example']), [])
        self.assertEqual(len(calls), 2)

    def test_cached_public_title_is_recompared_for_each_selected_identity(self):
        verifier = identity.TitleVerifier(fetcher=lambda key: 'American Horror Stories Trailer')
        self.assertEqual(verifier.filter([video(1)], ['American Horror Stories']), [video(1)])
        self.assertEqual(verifier.filter([video(1)], ['American Horror Story']), [])

    def test_failure_cache_retries_after_fifteen_seconds(self):
        now = [0]
        calls = []
        def fetch(key):
            calls.append(key)
            if len(calls) == 1:
                raise TimeoutError('unavailable')
            return 'Example Trailer'
        verifier = identity.TitleVerifier(fetcher=fetch, clock=lambda: now[0])
        self.assertEqual(verifier.filter([video(1)], ['Example']), [])
        now[0] = 14
        self.assertEqual(verifier.filter([video(1)], ['Example']), [])
        self.assertEqual(len(calls), 1)
        now[0] = 15
        self.assertEqual(verifier.filter([video(1)], ['Example']), [video(1)])
        self.assertEqual(len(calls), 2)

    def test_cache_evicts_oldest_entry_after_256_public_titles(self):
        calls = []
        verifier = identity.TitleVerifier(fetcher=lambda key: calls.append(key) or 'Example Trailer')
        for n in range(257):
            self.assertEqual(verifier.filter([video(n)], ['Example']), [video(n)])
        self.assertEqual(verifier.filter([video(256)], ['Example']), [video(256)])
        self.assertEqual(len(calls), 257)
        self.assertEqual(verifier.filter([video(0)], ['Example']), [video(0)])
        self.assertEqual(len(calls), 258)

    def test_public_fetcher_uses_fixed_official_endpoint_and_two_second_timeout(self):
        seen = []
        response = Response(json.dumps({'title': 'Example Trailer', 'author_name': 'Example Channel', 'type': 'video'}).encode())
        def opener(request, timeout):
            seen.append((request.full_url, timeout))
            return response
        self.assertEqual(identity.fetch_public_title('00000000001', opener=opener), 'Example Trailer')
        endpoint, timeout = seen[0]
        self.assertEqual(urlsplit(endpoint).scheme, 'https')
        self.assertEqual(urlsplit(endpoint).netloc, 'www.youtube.com')
        self.assertEqual(urlsplit(endpoint).path, '/oembed')
        self.assertEqual(parse_qs(urlsplit(endpoint).query), {'url': ['https://www.youtube.com/watch?v=00000000001'], 'format': ['json']})
        self.assertEqual(timeout, 2)
        self.assertEqual(response.read_sizes, [65537])

    def test_public_fetcher_validates_id_before_http(self):
        calls = []
        self.assertEqual(identity.fetch_public_title('https://evil.example', opener=lambda *a, **k: calls.append(a)), '')
        self.assertEqual(calls, [])

    def test_public_fetcher_rejects_oversize_and_malformed_responses(self):
        for payload in [b'x' * 65537, b'not-json', b'[]', b'null', b'{"title": 12}', b'{"title":""}', b'{"title":"   "}', b'\xff']:
            with self.subTest(payload=payload[:30]):
                self.assertEqual(identity.fetch_public_title('00000000001', opener=lambda *a, **k: Response(payload)), '')

    def test_public_fetcher_rejects_read_timeout(self):
        class TimeoutResponse(Response):
            def read(self, size):
                raise TimeoutError('read timed out')
        self.assertEqual(identity.fetch_public_title('00000000001', opener=lambda *a, **k: TimeoutResponse(b'')), '')

    def test_public_fetcher_rejects_http_errors(self):
        def unavailable(*args, **kwargs):
            raise OSError('unavailable')
        self.assertEqual(identity.fetch_public_title('00000000001', opener=unavailable), '')


if __name__ == '__main__':
    unittest.main()
