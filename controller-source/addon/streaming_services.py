"""Regional service catalog ordering and profile-local pins."""
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import tempfile
from threading import Lock
import unicodedata
from urllib.parse import parse_qs, urlsplit

PAGE_SIZE = 18
_PIN_KEY = re.compile(r'[A-Z]{2}:[1-9][0-9]{0,8}')
_MAX_PIN_BYTES = 32 * 1024
_PIN_LOCK = Lock()

# JustWatch U.S. SVOD engagement, January–September 2025.
# https://www.justwatch.com/us/press/netflix-paramount-warner-bros
# Prime Video, Netflix, Disney+, HBO Max, Hulu, Apple TV, Paramount+,
# Peacock Premium, and Starz. The Paramount+ brand maps to Essential when
# available, otherwise Premium. The report supplies no separate tier rankings.
_US_INTEREST_KEYS = (
    ('US:9',), ('US:8',), ('US:337',), ('US:1899',), ('US:15',),
    ('US:350',), ('US:2616', 'US:2303'), ('US:386',), ('US:43',),
)


@dataclass(frozen=True)
class Service:
    key: str
    name: str
    region: str
    card: dict


def service_key(card):
    if not card:
        return None
    route = urlsplit(card.get('file') or '')
    if (route.scheme, route.netloc, route.path) != ('plugin', 'plugin.video.themoviedb.helper', '/'):
        return None
    query = parse_qs(route.query)
    if query.get('info') != ['discover'] or query.get('tmdb_type') not in (['movie'], ['tv']):
        return None
    regions = query.get('watch_region', [])
    providers = query.get('with_watch_providers', [])
    if len(regions) != 1 or len(providers) != 1:
        return None
    key = f'{regions[0]}:{providers[0]}'
    return key if _PIN_KEY.fullmatch(key) else None


def _alphabetical_name(service):
    name = unicodedata.normalize('NFKD', service.name.casefold())
    return ''.join(character for character in name if not unicodedata.combining(character))


class ServiceCatalog:
    def __init__(self, cards):
        self.services = {}
        for card in cards:
            key = service_key(card)
            if not key or key in self.services:
                continue
            region = key.split(':')[0]
            label = card.get('title') or card.get('label') or key
            suffix = f' · {region}'
            name = label[:-len(suffix)] if label.endswith(suffix) else label
            self.services[key] = Service(key, name.strip(), region, card)
        self.alphabetical = sorted(self.services.values(), key=_alphabetical_name)
        ranked = {}
        for aliases in _US_INTEREST_KEYS:
            key = next((key for key in aliases if key in self.services), None)
            if key:
                ranked[key] = self.services[key]
        # Keep Helper display priority for any services outside the measured ranking.
        unranked = (service for key, service in self.services.items() if key not in ranked)
        self.featured = (list(ranked.values()) + list(unranked))[:PAGE_SIZE]
        self.featured_source = (
            'JustWatch US interest (Jan–Sep 2025) · then Helper order'
            if ranked else 'TMDb / JustWatch display order'
        )

    def entries(self, tab, pin_keys):
        if tab == 'all':
            return self.alphabetical
        pins = [self.services[key] for key in pin_keys if key in self.services]
        if tab == 'pinned':
            return pins
        return pins + [service for service in self.featured if service.key not in pin_keys]


class ServicePins:
    def __init__(self, profile):
        self.path = Path(profile) / 'addon_data/script.blacklanturn.preview/streaming-service-pins.json'
        try:
            self.keys = self._read()
        except (OSError, ValueError):
            self.keys = ()

    def _read(self):
        try:
            with self.path.open('rb') as stream:
                raw = stream.read(_MAX_PIN_BYTES + 1)
        except FileNotFoundError:
            return ()
        if len(raw) > _MAX_PIN_BYTES:
            raise ValueError('Saved pins exceed the storage limit')
        data = json.loads(raw)
        keys = data.get('pins') if isinstance(data, dict) and data.get('version') == 1 else None
        if not isinstance(keys, list) or any(not isinstance(key, str) or not _PIN_KEY.fullmatch(key)
                                              for key in keys) or len(set(keys)) != len(keys):
            raise ValueError('Saved pins could not be read')
        return tuple(keys)

    def toggle(self, key):
        if not _PIN_KEY.fullmatch(key):
            raise ValueError('Invalid service')
        with _PIN_LOCK:
            keys = self._read()
            pinned = key not in keys
            updated = keys + (key,) if pinned else tuple(saved for saved in keys if saved != key)
            raw = json.dumps({'version': 1, 'pins': updated}).encode('utf-8')
            if len(raw) > _MAX_PIN_BYTES:
                raise ValueError('Saved pins exceed the storage limit')
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, temporary = tempfile.mkstemp(prefix=self.path.name + '.', dir=self.path.parent)
            try:
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(raw)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, self.path)
            finally:
                Path(temporary).unlink(missing_ok=True)
            self.keys = updated
        return pinned
