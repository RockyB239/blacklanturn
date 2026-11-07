"""Fail-closed read-only early Home preparation, before native view import."""
from pathlib import Path
def prepare_home(root,store,*,use_fast=True):
    """No provider request. Reuse requires the same native account and policies."""
    try:
        import xbmc,xbmcaddon,xbmcvfs
        STORE=Path(store)
        if use_fast and xbmc.getCondVisibility('System.Platform.Android'):
            from light_home_fast import fingerprint,load_cache,projected_rows
            cached=load_cache(STORE,lambda schema:fingerprint(STORE,schema))
            if cached:
                from live_runtime import read_controller_config
                from title_preferences import TitlePreferences
                try:
                    record,projection=cached
                    preferences=TitlePreferences(STORE/'title-preferences.json')
                    if not preferences.error:
                        return {'record':record,'config':read_controller_config(STORE/'rows.json'),
                                'preferences':preferences,'cards':projected_rows(record,projection,preferences)}
                except (OSError,ValueError,TypeError,AttributeError,IndexError,KeyError):
                    pass
        from live_runtime import read_controller_config
        from public_rows import helper_settings_identity
        from home_rows import home_scope
        from light_home_model import display_scope,validated_record
        config=read_controller_config(STORE/'rows.json')
        helper=xbmcaddon.Addon('plugin.video.themoviedb.helper');schema=xbmcvfs.File(helper.getAddonInfo('path')+'/resources/settings.xml')
        try:identity=helper_settings_identity(schema.read(),helper.getSetting)
        finally:schema.close()
        private=home_scope(config,identity,helper.getSetting('trakt_token'))
        record=validated_record(STORE/'home-display.json',display_scope(STORE,private))
        if not record:return None
        from title_preferences import TitlePreferences
        preferences=TitlePreferences(STORE/'title-preferences.json')
        if preferences.error or any(not preferences.apply(row['items']) for row in record['rows']):return None
        # A changed config cannot use the record. Layout membership/order was
        # already validated by its complete byte identity in display_scope.
        return {'record':record,'config':config,'preferences':preferences}
    except Exception:return None

