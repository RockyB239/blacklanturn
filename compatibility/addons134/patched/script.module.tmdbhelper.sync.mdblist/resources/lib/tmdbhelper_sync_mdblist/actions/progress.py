from jurialmunkey.parser import try_int
from tmdbhelper_sync_mdblist.actions.item import ItemSync
from tmdbhelper.lib.script.sync.progress import ItemProgress as BasicItemProgress


class ItemProgress(ItemSync, BasicItemProgress):

    def get_post_response_args(self):
        return ('scrobble/clear', )

    def get_post_response_data(self):
        item = {'ids': {'tmdb': try_int(self.tmdb_id)}}
        if self.item_type == 'episode':
            item.update({'season': try_int(self.season), 'episode': try_int(self.episode)})
        return {self.base_item_type: item}
