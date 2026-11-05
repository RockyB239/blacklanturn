"""Browse a provider's catalog using the active media type and region."""
from urllib.parse import urlencode

from streaming_cache import _query, streaming_route

GENRES = (
    ('Action', '28', '10759'),
    ('Comedy', '35', '35'),
    ('Drama', '18', '18'),
    ('Crime', '80', '80'),
    ('Documentary', '99', '99'),
    ('Animation', '16', '16'),
    ('Family', '10751', '10751'),
    ('Sci-Fi', '878', '10765'),
)


def service_shelves(name, path):
    if streaming_route(path) != 'titles':
        return None
    movie = _query(path)['tmdb_type'] == 'movie'
    date = 'primary_release_date' if movie else 'first_air_date'

    def row(label, **filters):
        query = '&' + urlencode(filters) if filters else ''
        return {'label': label, 'path': path + query, '_explicit_streaming': True}

    rows = [
        row('Popular'),
        row('Recent Releases', sort_by=date + '.desc', **{date + '.gte': 't-365', date + '.lte': 't-0'}),
    ]
    rows.extend(row(label, with_genres=movie_id if movie else show_id)
                for label, movie_id, show_id in GENRES)
    return {'heading': name + ' / TMDB & JUSTWATCH', 'button': 'Browse titles', 'rows': rows}
