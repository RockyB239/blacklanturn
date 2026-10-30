"""One bounded public metadata request through the installed Helper's API client.

No Kodi plugin invocation: a slow lookup cannot become a playback handoff gate.
Uses Helper's supported exposed TMDb API, without copying keys into preferences.
"""
import json,sys
from pathlib import Path
from urllib.request import urlopen,Request

def load_show_package(ident):
    if not str(ident).isdigit():return {}
    import xbmcaddon
    helper=Path(xbmcaddon.Addon('plugin.video.themoviedb.helper').getAddonInfo('path'))
    root=str(helper/'resources')
    if root not in sys.path:sys.path.insert(0,root)
    from tmdbhelper.lib.api.tmdb.api import TMDbAPI
    api=TMDbAPI()
    if api.req_api_url not in ('https://api.themoviedb.org/3','https://api.tmdb.org/3'):return {}
    url=api.get_request_url('tv',ident,append_to_response='recommendations,similar',language=api.req_language)
    with urlopen(Request(url,headers={'Accept':'application/json'}),timeout=4) as response:
        raw=response.read(1024*1024+1)
    if len(raw)>1024*1024:return {}
    value=json.loads(raw)
    return value if isinstance(value,dict) else {}
