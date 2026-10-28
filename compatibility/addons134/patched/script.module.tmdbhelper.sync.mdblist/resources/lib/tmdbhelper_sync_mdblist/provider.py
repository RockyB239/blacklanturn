from jurialmunkey.ftools import cached_property
from tmdbhelper.lib.sync.providers.base import SyncProvider
from tmdbhelper_sync_mdblist.sync import synctype, datasync
from tmdbhelper_sync_mdblist.actions import basic
from tmdbhelper_sync_mdblist.actions.progress import ItemProgress
from tmdbhelper_sync_mdblist.scrobbler import ProviderScrobbler


class Provider(SyncProvider):
    interface_version = 3
    provider_id = 'mdblist'
    display_name = 'MDbList'
    sync_classes = {
        'SyncWatched': synctype.SyncWatched,
        'SyncPlayback': synctype.SyncPlayback,
        'SyncNextEpisodes': synctype.SyncNextEpisodes,
        'SyncAllNextEpisodes': synctype.SyncAllNextEpisodes,
        'SyncWatchlist': synctype.SyncWatchlist,
        'SyncCollection': synctype.SyncCollection,
        'SyncHiddenDropped': synctype.SyncHiddenDropped,
        'SyncAiredEpisodes': synctype.SyncNextEpisodes,
    }
    action_classes = {
        'watched': basic.ItemWatched,
        'unwatched': basic.ItemUnwatched,
        'watchlist': basic.ItemWatchlist,
        'collection': basic.ItemCollection,
        'dropped': basic.ItemDropped,
        'progress': ItemProgress,
    }
    getter_classes = {
        'movies_to_watch': datasync.MDbListSyncDataGetterAllUnHiddenMoviesToWatch,
        'shows_to_watch': datasync.MDbListSyncDataGetterAllUnHiddenShowsToWatch,
        'shows_in_progress': datasync.MDbListSyncDataGetterAllUnHiddenShowsInProgress,
    }
    scrobbler_class = ProviderScrobbler

    @cached_property
    def api(self):
        return self.get_api()

    def get_api(self):
        from tmdbhelper.lib.api.mdblist.api import MDbListAPI
        return MDbListAPI()

    def is_authorized(self):
        return self.api is not None

    def get_last_activities(self):
        data = self.api.get_response_json('sync/last_activities')
        if data is None:
            return
        return {
            item_type: {
                'watchlisted_at': data.get('watchlisted_at'),
                'collected_at': data.get('collected_at'),
                'paused_at': data.get('episode_paused_at' if item_type == 'episodes' else 'paused_at'),
                'watched_at': data.get('watched_at' if item_type == 'movies' else 'episode_watched_at'),
                'dropped_at': data.get('dropped_at'),
            } for item_type in ('movies', 'shows', 'seasons', 'episodes')
        }
