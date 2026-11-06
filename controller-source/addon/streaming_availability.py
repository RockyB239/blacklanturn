"""On-demand title availability from TMDb and JustWatch."""

from __future__ import annotations

from dataclasses import dataclass
import re


_OFFER_TYPES = (
    ('flatrate', 'Subscription'),
    ('free', 'Free'),
    ('ads', 'With ads'),
    ('rent', 'Rent'),
    ('buy', 'Buy'),
)
_ATTRIBUTION = 'Availability data by JustWatch.'
_ACCESS = 'Access depends on the provider, your account and your library.'
_SERIES = 'Series-level availability. Seasons and episodes may vary.'


@dataclass(frozen=True)
class ProviderAvailability:
    provider_id: int
    name: str
    offers: tuple[str, ...]


@dataclass(frozen=True)
class RegionAvailability:
    link: str = ''
    providers: tuple[ProviderAvailability, ...] = ()


def load_title_availability(kind, tmdb_id):
    """Load one title worldwide. An empty mapping means a successful empty response."""
    ident = str(tmdb_id)
    if kind not in ('movie', 'tv') or not re.fullmatch('[1-9][0-9]{0,9}', ident):
        raise ValueError('A movie or series TMDb ID is required')

    from regional_catalog import fetch_public_tmdb

    payload = fetch_public_tmdb(kind, ident, 'watch', 'providers')
    if not isinstance(payload, dict) or type(payload.get('id')) is not int or payload['id'] != int(ident):
        raise ValueError('Availability response did not match the requested title')
    results = payload.get('results')
    if not isinstance(results, dict):
        raise ValueError('Invalid title availability response')

    regions = {}
    for code, listing in results.items():
        if not re.fullmatch('[A-Z]{2}', code) or not isinstance(listing, dict):
            raise ValueError('Invalid country availability')
        link = listing.get('link', '')
        if not isinstance(link, str):
            raise ValueError('Invalid country availability link')

        providers = {}
        for field, label in _OFFER_TYPES:
            offers = listing.get(field, [])
            if not isinstance(offers, list):
                raise ValueError('Invalid provider offers')
            for row in offers:
                if not isinstance(row, dict):
                    raise ValueError('Invalid provider offer')
                provider_id = row.get('provider_id')
                name = row.get('provider_name')
                if type(provider_id) is not int or provider_id <= 0 or not isinstance(name, str) or not name.strip():
                    raise ValueError('Invalid provider offer')
                _, offer_types = providers.setdefault(provider_id, (name, []))
                if label not in offer_types:
                    offer_types.append(label)

        regions[code] = RegionAvailability(link, tuple(
            ProviderAvailability(provider_id, name, tuple(offers))
            for provider_id, (name, offers) in providers.items()
        ))
    return regions


def _show_region(dialog, region_name, listing, kind, title):
    lines = [title, _ATTRIBUTION]
    if kind == 'tv':
        lines.append(_SERIES)
    if listing.providers:
        lines.extend(('', _ACCESS, ''))
        lines.extend(f"{provider.name} · {', '.join(provider.offers)}" for provider in listing.providers)
    else:
        lines.extend(('', 'No providers listed.'))
    if listing.link:
        lines.extend(('', 'Availability page (TMDb)', listing.link))
    dialog.textviewer(f'Where to Watch · {region_name}', '\n'.join(lines))


def show_where_to_watch(dialog, kind, tmdb_id, title, region, region_names=None):
    """Browse the current country and other countries without repeating the title request."""
    from regional_catalog import helper_region_names

    country_names = helper_region_names()
    country_names.update(region_names or {})
    region = str(region or '').upper()
    local_name = country_names.get(region, region)
    scopes = [local_name, 'All Regions'] if local_name else ['All Regions']
    heading = f'Where to Watch · {title}'
    scope = dialog.select(heading, scopes, preselect=0)
    if scope < 0:
        return

    try:
        availability = load_title_availability(kind, tmdb_id)
    except (OSError, ValueError):
        dialog.ok(heading, 'Could not load streaming availability. Open Where to Watch to try again.')
        return

    countries = sorted((code for code, listing in availability.items() if listing.providers),
                       key=lambda code: country_names.get(code, code).casefold())
    labels = []
    for code in countries:
        count = len(availability[code].providers)
        noun = 'provider' if count == 1 else 'providers'
        labels.append(f'{country_names.get(code, code)} · {count} {noun}')

    while scope >= 0:
        if scopes[scope] != 'All Regions':
            _show_region(dialog, local_name, availability.get(region, RegionAvailability()), kind, title)
        elif not countries:
            _show_region(dialog, 'All Regions', RegionAvailability(), kind, title)
        else:
            selected = 0
            while selected >= 0:
                selected = dialog.select('All Regions · JustWatch', labels, preselect=selected)
                if selected >= 0:
                    code = countries[selected]
                    _show_region(dialog, country_names.get(code, code), availability[code], kind, title)
        scope = dialog.select(heading, scopes, preselect=scope)
