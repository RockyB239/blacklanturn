"""Browse a provider's catalog using the active media type and region."""
from collections import Counter
from urllib.parse import urlencode

from adaptive_services import candidate_filters, preview_ids, qualify_preview
from streaming_cache import _query, streaming_route
from browse_controls import is_next_page

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


MOVIE_GENRES = (
    ('Adventure', '12'), ('Fantasy', '14'), ('History', '36'), ('Horror', '27'),
    ('Music', '10402'), ('Mystery', '9648'), ('Romance', '10749'),
    ('Thriller', '53'), ('War', '10752'), ('Western', '37'),
)
SHOW_GENRES = (
    ('Kids', '10762'), ('Mystery', '9648'), ('News', '10763'), ('Reality', '10764'),
    ('Soap', '10766'), ('Talk', '10767'), ('War & Politics', '10768'), ('Western', '37'),
)


class StreamingShelfLayout:
    def __init__(self, path, specialty_count):
        self.path = path
        self.specialty_count = specialty_count
        self.baseline = None
        self.baseline_ids = frozenset()
        self.compact = False
        self.empty = False
        self.candidates = set()
        self.rejected = set()
        self.accepted = {}
        self.movie_card = None
        self.alternate_checked = False

    def available(self, path):
        if path == self.path or path in self.accepted:
            return True
        return (self.baseline is not None and not self.compact
                and path in self.candidates and path not in self.rejected)

    def reject(self, path):
        self.accepted.pop(path, None)
        self.rejected.add(path)

    def filter(self, path, files):
        if not files or (path != self.path and path not in self.candidates):
            return files
        if path == self.path:
            if self.baseline is None:
                self.baseline = list(files)
                self.baseline_ids = preview_ids(files)
                self.compact = len(files) <= 8 and not any(is_next_page(item, path) for item in files)
            return files
        if path in self.accepted:
            return files
        candidate = preview_ids(files)
        if self.available(path) and qualify_preview(candidate, self.baseline_ids, self.accepted.values()):
            self.accepted[path] = candidate
            return files
        self.reject(path)
        return []

    def order(self, rows):
        if self.compact or self.baseline is None:
            return
        counts = Counter()
        aliases = {'Action & Adventure': 'Action', 'Science Fiction': 'Sci-Fi', 'Sci-Fi & Fantasy': 'Sci-Fi'}
        for item in self.baseline:
            genres = item.get('genre') or ()
            if isinstance(genres, str):
                genres = (genres,)
            counts.update(aliases.get(name, name) for name in genres)
        start = 1 + self.specialty_count
        rows[start:] = sorted(rows[start:], key=lambda row: -counts[row['label']])


def service_shelves(name, path, *, adaptive=False, region_name=None):
    if streaming_route(path) != 'titles':
        return None
    fields = _query(path)
    movie = fields['tmdb_type'] == 'movie'
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
    if adaptive:
        specialties = [row(label, **filters) for label, filters in
                       candidate_filters(fields['tmdb_type'], fields['with_watch_providers'])]
        extra_genres = MOVIE_GENRES if movie else SHOW_GENRES
        rows.extend(row(label, with_genres=genre_id) for label, genre_id in extra_genres)
        unique = {}
        for entry in specialties + rows[1:]:
            unique.setdefault(entry['path'], entry)
        rows[1:] = unique.values()
        layout = StreamingShelfLayout(path, len(specialties))
        rows[0].update(label='Browse All Movies' if movie else 'Browse All Shows', _streaming_layout=layout)
        layout.candidates = {entry['path'] for entry in rows[1:]}
        country = fields['watch_region']
        name = name.removesuffix(' · ' + country)
        name += ' · ' + (region_name or country)
    return {'heading': name + ' / TMDB & JUSTWATCH', 'button': 'Browse titles', 'rows': rows, 'hide_captions': True}
