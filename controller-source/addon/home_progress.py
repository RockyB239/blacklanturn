"""Resolve display-only private progress at the explicit playback boundary."""
import copy
from playback_core import action_identity
from public_rows import _finite_number

PENDING_SCOPE='_home_progress_scope'

class ProgressUnavailable(ValueError):pass

def authoritative_progress(item):
    """An explicit empty/zero resume is current; an absent/invalid value is unknown."""
    point=item.get('resume')
    if not isinstance(point,dict):return False
    if point:
        position=point.get('position');total=point.get('total')
        if not all(_finite_number(value) for value in (position,total)):return False
        if not 0<=position<=total:return False
    count=item.get('playcount',0)
    return _finite_number(count)

def current_home_scope():
    # Use the same schema/native settings proof as configure_row_snapshots.
    import xbmcaddon,xbmcvfs
    from live_review import STORE
    from live_runtime import read_controller_config
    from public_rows import helper_settings_identity
    from home_rows import home_scope
    helper=xbmcaddon.Addon('plugin.video.themoviedb.helper')
    schema=xbmcvfs.File(helper.getAddonInfo('path')+'/resources/settings.xml')
    try:identity=helper_settings_identity(schema.read(),helper.getSetting)
    finally:schema.close()
    return home_scope(read_controller_config(STORE/'rows.json'),identity,helper.getSetting('trakt_token'))

def prepare_home_progress(item):
    """Never open a saved progress title without exact, current-account progress."""
    from live_review import get_list,tmdb
    from home_rows import home_browse_item_path
    from live_core import title_details_params
    try:
        scope=item.get(PENDING_SCOPE)
        if not isinstance(scope,str) or not scope or current_home_scope()!=scope:
            raise ProgressUnavailable('Account or settings changed. Reopen this row before playing.')
        identity=action_identity(item)
        if identity is None or not home_browse_item_path(item.get('file')):
            raise ProgressUnavailable('Current title could not be verified. Reopen the row and try again.')
        params=title_details_params(item);kind=params.pop('tmdb_type')
        files=get_list(tmdb('details',kind,**params))
        if current_home_scope()!=scope:
            raise ProgressUnavailable('Account or settings changed. Reopen this row before playing.')
        matches=[fresh for fresh in files if isinstance(fresh,dict) and home_browse_item_path(fresh.get('file')) and action_identity(fresh)==identity and authoritative_progress(fresh)]
        if len(matches)!=1:raise ProgressUnavailable('Current progress unavailable. Return to the title and try again.')
        fresh=copy.deepcopy(matches[0]);value={**item,**fresh,'file':item['file'],'filetype':item.get('filetype','file')}
        value.pop(PENDING_SCOPE,None)
        return value
    except ProgressUnavailable:raise
    except Exception as exc:
        # Provider/account errors may contain sensitive addresses; keep them out
        # of notifications and never silently play this title from zero.
        raise ProgressUnavailable('Current progress unavailable. Return to the title and try again.') from exc
