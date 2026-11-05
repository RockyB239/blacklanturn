"""One fresh regional service row, requested only after settled tile focus."""
import time
from genre_lookahead import GenreLookahead
from streaming_cache import _query, streaming_route


class StreamingLookahead(GenreLookahead):
    def __init__(self, fetch, cached=lambda path:False, clock=time.monotonic):
        self.completed_at = None
        def timed_fetch(path):
            items = fetch(path)
            self.completed_at = clock()
            return items
        super().__init__({}, timed_fetch, cached=cached, clock=clock)

    def observe(self, path):
        # Only the original unfiltered first page of a validated catalog card.
        fields = _query(path)
        if streaming_route(path) != 'titles' or fields.keys() & {'with_genres', 'sort_by'}:
            path = ''
        if path:
            self.paths[path] = path
        super().observe(path)

    def take(self, path, current):
        items = super().take(path, current)
        return items if self.completed_at is not None and self.clock()-self.completed_at < 120 else None
