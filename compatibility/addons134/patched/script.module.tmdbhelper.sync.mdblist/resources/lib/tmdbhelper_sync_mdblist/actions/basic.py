from tmdbhelper_sync_mdblist.actions.item import ItemSync
from tmdbhelper.lib.script.sync.actions import (
    ItemWatched as BasicItemWatched,
    ItemUnwatched as BasicItemUnwatched,
    ItemWatchlist as BasicItemWatchlist,
    ItemCollection as BasicItemCollection,
    ItemDropped as BasicItemDropped,
)


class ItemWatched(ItemSync, BasicItemWatched):
    sync_url = 'sync/watched'


class ItemUnwatched(ItemWatched, BasicItemUnwatched):
    pass


class ItemWatchlist(ItemSync, BasicItemWatchlist):
    sync_url = 'watchlist/items'

    def get_method(self):
        return f'{self.sync_url}/{"remove" if self.remove else "add"}'

    def get_sync_item(self):
        return super().get_sync_item()['ids']


class ItemCollection(ItemSync, BasicItemCollection):
    sync_url = 'sync/collection'

    def get_sync_value(self):
        """ Episode collection status is synced separately from the parent show. """
        return self.syncdata.get_value(
            self.tmdb_type,
            self.tmdb_id,
            self.season,
            self.episode,
            key=self.sync_key,
            item_type=self.item_type
        )


class ItemDropped(ItemSync, BasicItemDropped):
    sync_url = 'sync/dropped'
