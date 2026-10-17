from pathlib import Path
import json,xbmc,xbmcgui,xbmcvfs,xbmcaddon
def return_to_previous_skin():
    store=Path(xbmcvfs.translatePath(xbmcaddon.Addon('script.blacklanturn.preview').getAddonInfo('profile')))
    try:previous=(store/'previous-skin.txt').read_text().strip()
    except FileNotFoundError:previous='skin.estuary'
    if not previous.startswith('skin.') or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789._-' for c in previous):previous='skin.estuary'
    result=json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc':'2.0','id':1,'method':'Settings.SetSettingValue','params':{'setting':'lookandfeel.skin','value':previous}})))
    if not result.get('result'):xbmcgui.Dialog().ok('BlackLanturn','Open Kodi Settings → Interface → Skin to select your previous skin.')
