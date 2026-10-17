"""Curated playback choices over TMDb Helper's existing player definitions."""
from urllib.parse import urlsplit,parse_qsl,urlencode,urlunsplit
MODES=(('umbrella.select.json','Umbrella · Source Select'),('umbrella.autoplay.json','Umbrella · Auto Play'),('umbrella.rescrape.json','Umbrella · Rescrape'))
def default_setting(kind):
    return {'episode':'default_player_episodes','movie':'default_player_movies'}[kind]
def player_choices(definitions,enabled,kind):
    if not enabled or kind not in ('episode','movie'):return []
    action='play_'+kind
    return [{'file':filename,'label':label,'setting':filename+' '+action} for filename,label in MODES
        if definitions.get(filename,{}).get('plugin')=='plugin.video.umbrella'
        and urlsplit(definitions.get(filename,{}).get(action,'')).netloc=='plugin.video.umbrella']
def player_path(item,filename):
    if filename not in {f for f,_ in MODES} or item.get('filetype')=='directory':return None
    source=urlsplit(item.get('file',''));pairs=parse_qsl(source.query,keep_blank_values=True)
    if source.netloc!='plugin.video.themoviedb.helper' or dict(pairs).get('info')!='play':return None
    pairs=[p for p in pairs if p[0] not in ('player','mode','ignore_default')]
    return urlunsplit((source.scheme,source.netloc,source.path,urlencode(pairs+[('player',filename),('mode','play'),('ignore_default','true')]),source.fragment))
