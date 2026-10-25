"""Bounded missing-preview lookup through the installed YouTube provider.

The normal TMDb list and public-title verifier must run first. Only an empty
approved list may query YouTube's existing incognito search route. No credentials,
account tables, arbitrary HTTP endpoints, or title-specific videos are used.
The search is only a candidate source: public oEmbed identity approval remains
mandatory. Exact title matching does not prove publisher authenticity or remake
identity. TV search and ranking prefer season one over later-season spoilers.

One provider page is requested; at most 30 returned entries are inspected and six
unique video candidates verified by the caller's existing two-worker verifier.
Provider requests already in flight cannot be interrupted; provider socket/API
limits apply, so this is a request-count bound, not a hard wall-time deadline.
Cancellation discards results and prevents queued work. All caches are memory
only, bounded, and short lived, including provider or title-evidence failures.
"""
from collections import OrderedDict
from itertools import islice
import re
import threading
import time
from urllib.parse import urlencode

from live_core import preview_candidates
from youtube_core import video_id


class SecondaryPreviewLookup:
    def __init__(self, clock=None):
        self._clock = clock or time.monotonic
        self._cache = OrderedDict()
        self._lock = threading.Lock()
        # Shared by all selections: canceled work cannot create unbounded searches.
        self._network_slot = threading.BoundedSemaphore(1)

    def _cached(self, key):
        with self._lock:
            entry = self._cache.get(key)
            if entry and self._clock() < entry[0]:
                self._cache.move_to_end(key)
                return list(entry[1])
            self._cache.pop(key, None)
        return None

    def _store(self, key, candidates, seconds):
        with self._lock:
            self._cache[key] = (self._clock() + seconds, tuple(candidates))
            self._cache.move_to_end(key)
            while len(self._cache) > 128:
                self._cache.popitem(last=False)

    def lookup(self, approved, identity, titles, load, verifier,
               preferred_language='en', year=None, valid=lambda: True):
        """Return normal approvals unchanged or identity-screened secondary URLs.

        ``load`` is the existing Kodi directory loader and may raise on failure.
        ``verifier`` is the existing shared Preview TitleVerifier instance.
        Unknown/absent public evidence never approves a preview. A current Kodi
        provider can still silently return an empty list on error; that receives
        the same brief 30-second cache as an ordinary empty search.
        """
        if not valid():
            return []
        if approved:
            return list(approved)
        if (not isinstance(identity, (tuple, list)) or len(identity) != 2
                or identity[0] not in ('movie', 'tv')
                or not re.fullmatch(r'[1-9]\d{0,11}', str(identity[1]))):
            return []
        aliases = tuple(dict.fromkeys(t.strip() for t in
                        ([titles] if isinstance(titles, str) else titles or ())
                        if isinstance(t, str) and t.strip() and len(t) <= 160
                        and not any(ord(c) < 32 for c in t)))
        if not aliases:
            return []
        title = aliases[0].replace('"', ' ').strip()
        if not title:
            return []
        release_year = str(year) if re.fullmatch(r'(?:18|19|20|21)\d{2}', str(year)) else ''
        kind = identity[0]
        query = '"' + title + '"' + (' season 1' if kind == 'tv' else ' ' + release_year if release_year else '') + ' official trailer'
        path = 'plugin://plugin.video.youtube/kodion/search/query/?' + urlencode({
            'q': query, 'search_type': 'video', 'incognito': 'true',
            'hide_folders': 'true', 'maxResults': '12',
        })
        key = (kind, str(identity[1]), aliases, preferred_language, release_year)
        cached = self._cached(key)
        if cached is not None:
            return cached if valid() else []
        while not self._network_slot.acquire(timeout=.1):
            if not valid():
                return []
        try:
            if not valid():
                return []
            # Another selection may have completed this same lookup while we waited.
            cached = self._cached(key)
            if cached is not None:
                return cached if valid() else []
            try:
                rows = load(path)
                if not valid():
                    return []
                if not isinstance(rows, (tuple, list)):
                    raise ValueError('Unavailable search directory')
                records = []
                seen = set()
                for item in islice(rows, 30):
                    if not isinstance(item, dict):
                        continue
                    try:
                        ident = video_id(item)
                    except (ValueError, TypeError):
                        continue
                    if not ident or ident in seen:
                        continue
                    seen.add(ident)
                    # Keep a safe provider play route, without search-result actions.
                    record = dict(item, file='plugin://plugin.video.youtube/play/?video_id=' + ident)
                    records.append(record)
                if kind == 'tv':
                    def season_rank(item):
                        name = str(item.get('label') or item.get('title') or '').casefold()
                        number = re.search(r'\b(?:season|installment)\s*0*(\d+)\b', name)
                        return 0 if number and int(number[1]) == 1 else 2 if number else 1
                ranked = preview_candidates('', records, preferred_language=preferred_language)
                if kind == 'tv':
                    season_scores = {item['file']: season_rank(item) for item in records}
                    ranked.sort(key=lambda url: season_scores[url])
                ranked = ranked[:6]
                candidates = verifier.filter(ranked, aliases, valid=valid, media_type=kind, expected_year=release_year or None)
            except Exception:
                if valid():
                    self._store(key, [], 15)
                return []
            if not valid():
                return []
            self._store(key, candidates, 300 if candidates else 30)
            return list(candidates)
        finally:
            self._network_slot.release()
