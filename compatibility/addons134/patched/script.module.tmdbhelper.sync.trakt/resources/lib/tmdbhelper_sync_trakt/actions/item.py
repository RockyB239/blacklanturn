from tmdbhelper.lib.script.actions.trakt.item import ItemAction
from tmdbhelper.lib.script.sync.provider import ItemSync as ProviderItemSync


class ItemSync(ProviderItemSync, ItemAction):
    def get_trakt_api(self):
        return self.sync_provider.api
