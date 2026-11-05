from tmdbhelper.lib.addon.plugin import get_setting, set_setting
from tmdbhelper.lib.sync.providers.features import FEATURE_LABELS


class SyncProviderSetting:
    never_value = 'never'

    def __init__(self, capability):
        self.capability = capability

    @property
    def setting(self):
        return f'sync_provider_{self.capability}'

    @property
    def value(self):
        value = get_setting(self.setting, 'str')
        if value:
            return value
        # Preserve saved pre-provider choices without rewriting account/settings data.
        if self.capability == 'scrobbling':
            if get_setting('trakt_scrobbling') and get_setting('trakt_token', 'str'):
                return 'trakt'
            if get_setting('mdblist_scrobbling') and get_setting('mdblist_apikey', 'str'):
                return 'mdblist'
            return self.never_value
        # Only these capabilities had settings before provider selection.
        if self.capability not in ('watched', 'watchlist', 'collection'):
            return ''
        previous = get_setting('sync_source_' + self.capability, 'str')
        return {'Trakt': 'trakt', 'MDbList': 'mdblist'}.get(previous, '')

    @property
    def is_unconfigured(self):
        return not self.value

    @property
    def is_never(self):
        return self.value == self.never_value

    @property
    def provider_id(self):
        value = self.value
        return '' if value == self.never_value else value

    @property
    def provider_ids(self):
        return (self.provider_id,) if self.provider_id else ()

    def add_provider(self, provider_id):
        self.save(provider_id)

    def remove_provider(self, provider_id):
        if provider_id in self.provider_ids:
            self.save(self.never_value)

    def save(self, provider_id):
        if provider_id == get_setting(self.setting, 'str'):
            return
        if self.capability != 'scrobbling':
            from tmdbhelper.lib.sync.invalidator import SyncInvalidator
            invalidator = SyncInvalidator(self.capability)
            invalidator.notification = False
            invalidator.invalidate()
        set_setting(self.setting, provider_id, 'str')

    def disable(self):
        self.save(self.never_value)

    @classmethod
    def clear_provider(cls, provider_id):
        for capability in FEATURE_LABELS:
            SyncProviderSettingFactory(capability).remove_provider(provider_id)


def SyncProviderSettingFactory(capability):
    if capability == 'scrobbling':
        from tmdbhelper.lib.sync.providers.scrobbling_settings import ScrobblingProviderSetting
        return ScrobblingProviderSetting(capability)
    return SyncProviderSetting(capability)
