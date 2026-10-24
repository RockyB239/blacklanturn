"""Run once at startup or on demand; never change YouTube or its preferences."""
from pathlib import Path
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
from check import inspect

MESSAGES = {
    'verified': 'The tested YouTube preview fix and playback settings are present.',
    'replaced': 'The tested preview fix has been replaced. Check for a BlackLanturn build update.',
    'review': 'Your YouTube version has changed. Its preview compatibility needs review.',
    'settings': 'Preview playback settings changed. Enable InputStream Adaptive and MPEG-DASH in YouTube Settings.',
    'unavailable': 'Preview configuration could not be checked. Open YouTube and check that its add-on is enabled.',
}

def run(startup=False):
    if startup and xbmc.Monitor().waitForAbort(30):
        return
    try:
        youtube = xbmcaddon.Addon('plugin.video.youtube')
        version = youtube.getAddonInfo('version')
        if version != '7.4.4':
            status = 'review'
        else:
            path = Path(xbmcvfs.translatePath(youtube.getAddonInfo('path')))
            source = (path / 'resources/lib/youtube_plugin/youtube/client/player_client.py').read_bytes()
            isa = youtube.getSettingBool('kodion.video.quality.isa') and xbmc.getCondVisibility('System.HasAddon(inputstream.adaptive)')
            status = inspect(version, source, isa, youtube.getSettingBool('kodion.mpd.videos'))
    except Exception:
        status = 'unavailable'
    xbmc.log('[BlackLanturn Preview Check] status=' + status, xbmc.LOGINFO)
    if startup:
        if status != 'verified':
            xbmcgui.Dialog().notification('BlackLanturn Preview Check', MESSAGES[status], xbmcgui.NOTIFICATION_WARNING, 10000)
    else:
        xbmcgui.Dialog().ok('BlackLanturn Preview Check', MESSAGES[status])

    return status
