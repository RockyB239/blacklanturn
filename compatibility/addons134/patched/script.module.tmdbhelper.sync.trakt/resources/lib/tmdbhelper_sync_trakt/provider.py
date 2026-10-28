from jurialmunkey.ftools import cached_property
from tmdbhelper.lib.sync.providers.base import SyncProvider
from tmdbhelper_sync_trakt.sync import synctype, datasync
from tmdbhelper_sync_trakt.actions import basic
from tmdbhelper_sync_trakt.actions.progress import ItemProgress
from tmdbhelper_sync_trakt.scrobbler import ProviderScrobbler


class Provider(SyncProvider):
    interface_version = 3
    provider_id = 'trakt'
    display_name = 'Trakt'
    sync_classes = {
        'SyncWatched': synctype.SyncWatched,
        'SyncPlayback': synctype.SyncPlayback,
        'SyncNextEpisodes': synctype.SyncNextEpisodes,
        'SyncAllNextEpisodes': synctype.SyncAllNextEpisodes,
        'SyncWatchlist': synctype.SyncWatchlist,
        'SyncCollection': synctype.SyncCollection,
        'SyncHiddenDropped': synctype.SyncHiddenDropped,
        'SyncHiddenCalendar': synctype.SyncHiddenCalendar,
        'SyncHiddenProgressWatched': synctype.SyncHiddenProgressWatched,
        'SyncHiddenProgressCollected': synctype.SyncHiddenProgressCollected,
        'SyncAiredEpisodes': synctype.SyncWatched,
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
        'movies_to_watch': datasync.TraktSyncDataGetterAllUnHiddenMoviesToWatch,
        'shows_to_watch': datasync.TraktSyncDataGetterAllUnHiddenShowsToWatch,
        'shows_in_progress': datasync.TraktSyncDataGetterAllUnHiddenShowsInProgress,
    }
    scrobbler_class = ProviderScrobbler

    @cached_property
    def api(self):
        return self.get_api()

    def get_api(self):
        from tmdbhelper.lib.api.trakt.api import TraktAPI
        return TraktAPI()

    def is_authorized(self):
        return self.api is not None and self.api.authenticator.is_authorized

    def get_last_activities(self):
        return self.api.get_response_json('sync/last_activities')
