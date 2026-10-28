from tmdbhelper_sync_trakt.actions.item import ItemSync
from tmdbhelper.lib.script.sync.actions import (
    ItemWatched as BasicItemWatched,
    ItemUnwatched as BasicItemUnwatched,
    ItemWatchlist as BasicItemWatchlist,
    ItemCollection as BasicItemCollection,
    ItemDropped as BasicItemDropped,
)


class ItemWatched(ItemSync, BasicItemWatched):
    sync_url = 'history'


class ItemUnwatched(ItemSync, BasicItemUnwatched):
    sync_url = 'history'


class ItemWatchlist(ItemSync, BasicItemWatchlist):
    sync_url = 'watchlist'


class ItemCollection(ItemSync, BasicItemCollection):
    sync_url = 'collection'


class ItemDropped(ItemSync, BasicItemDropped):
    sync_url = 'hidden/dropped'

    def reset_lastactivities(self):
        super().reset_lastactivities()
        if self.is_successful_sync:
            self.delete_listdata()

    def delete_listdata(self):
        from tmdbhelper.lib.script.method.tmdb import delete_listdata
        delete_listdata(patterns=('ListTraktCalendar%', 'TraktData_calendars%'))

    def get_post_response_args(self):
        return ('users', self.method, )
