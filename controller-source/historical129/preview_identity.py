"""Conservative preview approval using public YouTube titles, never search.

Provider video labels can be generic or incorrectly associated with a series.
Require a selected-title/alias at the actual title's start, followed by known
preview metadata. Unknown title extensions do not prove the selected identity.
Unavailable evidence leaves the preview unapproved. This is a title check, not
proof of publisher authenticity, spoken language, or season-specific accuracy.
"""
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
import json
import re
import threading
import time
import unicodedata
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


_VIDEO_ID = re.compile(r'[A-Za-z0-9_-]{11}\Z')
_MAX_RESPONSE = 64 * 1024
_OFFICIAL_PREFIX = re.compile(r'^\s*official\s+(?:trailer|teaser)(?:\s*#?\d+)?\s*[:|\-–—]\s*', re.IGNORECASE)
_YEAR = re.compile(r'(?:18|19|20|21)\d{2}\Z')
_QUALITY = re.compile(r'(?:hd|uhd|[248]k|(?:360|480|720|1080|1440|2160|4320)p)\Z')
_TRAILER_LABELS = (('trailer',), ('teaser',), ('final', 'trailer'), ('red', 'band', 'trailer'))


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # A candidate never grants authority to fetch any other URL.
        return None


def fetch_public_title(video_id, opener=None):
    """Read at most 64 KiB from the fixed official oEmbed endpoint, no API key.

    The two-second timeout applies to socket operations. DNS and a slowly
    trickling response can exceed two seconds of total wall time.
    """
    if not isinstance(video_id, str) or not _VIDEO_ID.fullmatch(video_id):
        return ''
    endpoint = 'https://www.youtube.com/oembed?' + urlencode({
        'url': 'https://www.youtube.com/watch?v=' + video_id,
        'format': 'json',
    })
    request = Request(endpoint, headers={'Accept': 'application/json'})
    try:
        open_url = opener or build_opener(_NoRedirect()).open
        with open_url(request, timeout=2) as response:
            raw = response.read(_MAX_RESPONSE + 1)
        if len(raw) > _MAX_RESPONSE:
            return ''
        data = json.loads(raw.decode('utf-8'))
        title = data.get('title') if isinstance(data, dict) else None
        return title.strip() if isinstance(title, str) else ''
    except Exception:
        # Network errors and response contents can contain URLs; do not log them.
        return ''


def _video_id(url):
    if not isinstance(url, str):
        return None
    try:
        source = urlsplit(url)
        if source.scheme != 'plugin' or source.netloc != 'plugin.video.youtube':
            return None
        keys = parse_qs(source.query, keep_blank_values=True).get('video_id', [])
        return keys[0] if len(keys) == 1 and _VIDEO_ID.fullmatch(keys[0]) else None
    except ValueError:
        return None


def _tokens(title):
    if not isinstance(title, str):
        return ()
    normalized = unicodedata.normalize('NFKD', title.casefold())
    normalized = ''.join(c for c in normalized if not unicodedata.combining(c))
    return tuple(re.findall(r'[^\W_]+', normalized))


def _preview_suffix(tokens, media_type=None, expected_year=None):
    """Recognize metadata before the trailer marker, never sequel/subseries names.

    A trailer/teaser marker establishes the end of the title; publisher and other
    marketing text can follow. A delimiter alone never establishes that boundary.
    """
    index = 0
    while index < len(tokens):
        token = tokens[index]
        # Modifiers are accepted only as a complete trailer label. They cannot
        # consume unknown title words such as "Dune: Final Cut".
        marker = index + 1 if token == 'official' else index
        if any(tokens[marker:marker + len(label)] == label for label in _TRAILER_LABELS):
            return True
        if token == 'official':
            return marker == len(tokens)
        if token == 'season' or token == 'installment' and media_type == 'tv':
            if index + 1 >= len(tokens) or not re.fullmatch(r'\d{1,2}', tokens[index + 1]):
                return False
            index += 2
            continue
        if _YEAR.fullmatch(token) and expected_year and token != str(expected_year):
            return False
        if token == 'series' or _YEAR.fullmatch(token) or _QUALITY.fullmatch(token):
            index += 1
            continue
        return False
    return True


def _matches(actual, aliases, media_type=None, expected_year=None):
    tokens = _tokens(_OFFICIAL_PREFIX.sub('', actual))
    return any(tokens[:len(alias)] == alias and _preview_suffix(tokens[len(alias):], media_type=media_type, expected_year=expected_year)
               for alias in aliases)


class TitleVerifier:
    """Bounded, reusable public-title cache; selected-title approval is not cached.

    ``fetcher(video_id)`` returns a public title string. ``clock()`` returns
    monotonic seconds. No private account settings, persistence, or API keys.
    """
    def __init__(self, fetcher=None, clock=None):
        self._fetcher = fetcher or fetch_public_title
        self._clock = clock or time.monotonic
        self._cache = OrderedDict()
        self._cache_lock = threading.Lock()
        self._network_slots = threading.BoundedSemaphore(2)

    def _title(self, key, valid):
        if not valid():
            return None
        with self._cache_lock:
            cached = self._cache.get(key)
            if cached and self._clock() < cached[0]:
                self._cache.move_to_end(key)
                return cached[1]
            self._cache.pop(key, None)
        with self._network_slots:
            # A newer selection can cancel this job while all slots are busy.
            if not valid():
                return None
            try:
                title = self._fetcher(key)
                title = title.strip() if isinstance(title, str) else ''
            except Exception:
                title = ''
        with self._cache_lock:
            self._cache[key] = (self._clock() + (21600 if title else 15), title)
            self._cache.move_to_end(key)
            while len(self._cache) > 256:
                self._cache.popitem(last=False)
        return title

    def filter(self, urls, titles, valid=lambda: True, media_type=None, expected_year=None):
        """Approve six rank-ordered candidates while the selection remains current.

        Numbered installment labels require an explicit TV media type.
        Cancellation prevents queued network work and discards the whole result.
        An HTTP read already in progress finishes under its normal socket timeout.
        """
        if not valid():
            return []
        aliases = [_tokens(title) for title in ([titles] if isinstance(titles, str) else titles or ())]
        aliases = [alias for alias in aliases if alias]
        if not aliases:
            return []
        candidates = []
        seen = set()
        for url in urls or ():
            key = _video_id(url)
            if key is None or key in seen:
                continue
            seen.add(key)
            candidates.append((url, key))
            if len(candidates) == 6:
                break
        if not candidates:
            return []
        with ThreadPoolExecutor(max_workers=2, thread_name_prefix='BlackLanturnTitle') as workers:
            futures = []
            for _, key in candidates:
                if not valid():
                    break
                futures.append(workers.submit(self._title, key, valid))
            actual_titles = [future.result() for future in futures]
        if len(actual_titles) != len(candidates) or any(title is None for title in actual_titles) or not valid():
            return []
        return [url for (url, _), actual in zip(candidates, actual_titles) if _matches(actual, aliases, media_type=media_type, expected_year=expected_year)]
