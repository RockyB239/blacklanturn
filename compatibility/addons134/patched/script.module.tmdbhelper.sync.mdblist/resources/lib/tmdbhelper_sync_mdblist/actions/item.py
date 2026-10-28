from tmdbhelper.lib.script.actions.mdblist.item import ItemAction
from tmdbhelper.lib.script.sync.provider import ItemSync as ProviderItemSync


class ItemSync(ProviderItemSync, ItemAction):
    def get_mdblist_api(self):
        return self.sync_provider.api
