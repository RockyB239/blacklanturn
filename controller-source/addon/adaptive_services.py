"""Audited specialty candidates and preview rules for regional service pages."""
import re
from itertools import chain
from urllib.parse import parse_qs, urlsplit


_FILM_FIRST = (11, 201, 258, 433, 579, 2395, 2135, 2416, 1793, 529, 596, 33, 1891, 349, 28, 2263, 2502)
_HORROR = (99, 204, 2049, 202, 1960, 2367, 2478, 2078)
_DOCUMENTARY = (190, 603, 2060, 551, 100, 520, 524, 510, 584, 2430, 268, 2073, 2057, 411)
_ANIME = (283, 1968, 430, 2390, 446, 295, 2494)
_FAMILY = (175, 2796, 293, 2415, 2452, 2329, 2768)
_LIBRARY = (191, 212, 1972, 463)
_SPORTS = (1718, 1768, 260, 2448, 2383, 1809, 299, 2528)
_BRITISH = (151, 197, 1852, 87, 2034, 196)
_LANGUAGES = (
    ('ko', 'Korean-Language', (344, 464, 2413, 575)),
    ('zh', 'Chinese-Language', (581,)),
    ('bn', 'Bengali-Language', (315, 2176)),
    ('te', 'Telugu-Language', (532,)),
    ('ta', 'Tamil-Language', (309,)),
    ('es', 'Spanish-Language', (457, 1866)),
    ('ar', 'Arabic-Language', (1715,)),
    ('de', 'German-Language', (427,)),
)


def _row(label, **filters):
    return label, filters


def _build_profiles(kind):
    movie = kind == 'movie'
    action, science_fiction = ('28', '878') if movie else ('10759', '10765')
    date = 'primary_release_date.lte' if movie else 'first_air_date.lte'
    cinema = (
        _row('World Cinema', with_origin_country='FR|IT|JP|KR|DE|ES|IN|BR|MX|SE|HK|DK|IR|TW'),
        _row('Classics Before 1990', **{date: '1989-12-31', 'vote_average.gte': '6.5', 'vote_count.gte': '15'}),
        _row('Film Noir', with_keywords='9807'),
    ) if movie else ()
    supernatural = '6152|10224|15001'
    horror = (
        _row('Slashers', with_genres='27', with_keywords='12339'),
        _row('Supernatural Horror', with_genres='27', with_keywords=supernatural),
        _row('Creature Features', with_genres='27', with_keywords='1299|158126|12564'),
    ) if movie else (
        _row('Mystery', with_genres='9648'),
        _row('Supernatural', with_keywords=supernatural),
    )
    documentaries = (
        _row('Space & Science', with_genres='99', with_keywords='9882|160330|287067'),
        _row('Nature & Wildlife', with_genres='99', with_keywords='9902|221355'),
        _row('True Crime', with_genres='99', with_keywords='33722'),
        # A single audited World War II keyword avoids the broader history tag.
        _row('World War II Documentaries', with_genres='99', with_keywords='1956'),
    )
    anime = (
        _row('Anime Action', with_genres=f'16,{action}', with_original_language='ja'),
        _row('Anime Sci-Fi' if movie else 'Anime Sci-Fi & Fantasy',
             with_genres=f'16,{science_fiction}', with_original_language='ja'),
        _row('Classic Anime Before 2000', with_genres='16', with_original_language='ja', **{date: '1999-12-31'}),
    )
    family = (
        _row('Animation', with_genres='16'),
        _row('Family Adventures', with_genres='10751,' + ('12' if movie else action)),
        _row('Learning & Nature', with_keywords='18257|9902|221355'),
    )
    sports = (
        _row('Sports Documentaries', with_genres='99', with_keywords='6075|159290'),
        _row('Combat Sports', with_keywords='384605|331674|209476'),
    )
    groups = (
        (_FILM_FIRST, cinema),
        (_HORROR, horror),
        (_DOCUMENTARY, documentaries),
        (_ANIME, anime),
        (_FAMILY, family),
        (_LIBRARY, (_row('Documentaries', with_genres='99'), *cinema[:2])),
        (_SPORTS, sports),
        (_BRITISH, (
            _row('British Mysteries', with_origin_country='GB', with_genres='9648'),
            _row('British Crime', with_origin_country='GB', with_genres='80'),
        )),
        ((554, 2420), (
            _row('Stage Performances', with_keywords='193537|195729|4344'),
            _row('Ballet & Dance', with_keywords='10551|1346'),
        )),
        ((2266,), (_row('Concerts', with_keywords='6029|11634'),)),
        ((2068, 2047), (
            _row('Cooking', with_keywords='1918|295152'),
            _row('Food & Travel', with_keywords='10637,9935'),
        )),
        ((2164, 2480), (_row('Yoga & Fitness', with_keywords='5828|163412'),)),
        ((264,), (_row('Outdoor Sports', with_keywords='33688|1495'),)),
        ((278, 2433), (_row('Faith & Family', with_genres='10751', with_keywords='253695|6150'),)),
    )
    profiles = {provider: rows for providers, rows in groups for provider in providers}
    for language, label, providers in _LANGUAGES:
        rows = (
            _row(f'{label} Drama', with_original_language=language, with_genres='18'),
            _row(f'{label} Comedy', with_original_language=language, with_genres='35'),
        )
        profiles.update(dict.fromkeys(providers, rows))
    return profiles


_PROFILES = {kind: _build_profiles(kind) for kind in ('movie', 'tv')}


def _provider_id(provider_id):
    if type(provider_id) is int:
        return provider_id
    if isinstance(provider_id, str) and re.fullmatch(r'[1-9][0-9]{0,8}', provider_id):
        return int(provider_id)
    return None


def candidate_filters(kind, provider_id):
    """Return ordered labels and independent, decoded Helper query filters."""
    rows = _PROFILES.get(kind, {}).get(_provider_id(provider_id), ())
    return tuple((label, dict(filters)) for label, filters in rows)


def film_first(provider_id):
    return _provider_id(provider_id) in _FILM_FIRST


def valid_specialty_filters(kind, provider_id, filter_dict):
    """Accept only exact filter dictionaries approved for this provider and media."""
    if not isinstance(filter_dict, dict):
        return False
    rows = _PROFILES.get(kind, {}).get(_provider_id(provider_id), ())
    return any(filter_dict == approved for _, approved in rows)


def _title_id(item):
    if not isinstance(item, dict) or item.get('_page_control'):
        return None
    path = item.get('file')
    query = {}
    if isinstance(path, str):
        try:
            route = urlsplit(path)
        except ValueError:
            return None
        if (route.scheme, route.netloc) == ('plugin', 'plugin.video.themoviedb.helper'):
            query = parse_qs(route.query)
    if 'page' in query or query.get('info') == ['discover']:
        return None
    unique_id = item.get('uniqueid')
    if not isinstance(unique_id, dict):
        unique_id = {}
    kind = query.get('tmdb_type', query.get('type', [item.get('type')]))[0]
    if kind == 'tvshow' or (not kind and 'tvshow.tmdb' in unique_id):
        kind = 'tv'
    if kind not in ('movie', 'tv'):
        return None
    fallback = (unique_id.get('tvshow.tmdb') if kind == 'tv' else None) or unique_id.get('tmdb')
    ident = str(query.get('tmdb_id', [fallback])[0])
    if re.fullmatch(r'[1-9][0-9]*', ident):
        return kind, ident
    return None


def preview_ids(files):
    titles = set()
    for item in files:
        identity = _title_id(item)
        if identity is not None:
            titles.add(identity)
        if len(titles) == 8:
            break
    return frozenset(titles)


def qualify_shelf(baseline_files, existing_files, candidate_files):
    """Require a useful sample and compare each shelf's visible titles separately."""
    return qualify_preview(preview_ids(candidate_files), preview_ids(baseline_files),
                           map(preview_ids, existing_files))


def qualify_preview(candidate, baseline, preceding_shelves):
    return len(candidate) >= 4 and all(
        len(candidate - preceding) * 2 >= len(candidate)
        for preceding in chain((baseline,), preceding_shelves)
    )
