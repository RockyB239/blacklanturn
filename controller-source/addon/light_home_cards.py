"""Shared-shape early cards; kept byte-identical to the normal card renderer."""
import xbmcgui
from live_core import episode_heading,card_artwork
from youtube_core import is_youtube,caption as youtube_caption
from episode_ui import episode_card
from search_ui import search_caption
from watch_metadata import hydrate_watch_metadata
def media_item(data,immutable=False):
    headline,episode_line=episode_heading(data)
    # Only the YouTube browser opts in: it replaces whole cards on refresh.
    # TMDb and personal extensions mutate displayed cards and retain GUI locks.
    li=xbmcgui.ListItem(label=episode_line or data.get('title') or data.get('label',''),path=data.get('file',''),offscreen=immutable)
    art=dict(data.get('art',{}))
    selected_art=card_artwork(data)
    art['landscape']=selected_art['image'] if selected_art['kind']=='landscape' else ''
    art['poster']=selected_art['image'] if selected_art['kind']=='portrait' else art.get('poster','')
    if selected_art['kind']=='square':art['square']=selected_art['image']
    if data.get('_page_control') and selected_art['kind']=='text':selected_art['kind']='paging'
    properties={'pageControl':data.get('_page_control','')}
    youtube_folder=(is_youtube(data) and data.get('filetype')=='directory' and not data.get('_page_control')
                    and not selected_art['image'].startswith(('http://','https://')))
    properties['youtubeFolder']='true' if youtube_folder else 'false'
    if youtube_folder:art['youtubefolder']=selected_art['image'] or 'video-addons.png'
    properties['cardArtKind']=selected_art['kind']
    properties['cardEpisodeLabel']='true' if episode_line and not data.get('_page_control') else 'false'
    properties['cardPosterFallback']='true' if selected_art['kind']=='landscape' and selected_art['image'] and selected_art['image'] in {art.get(k) for k in ('poster','season.poster','tvshow.poster') if art.get(k)} else 'false'
    li.setArt(art)
    info={k:data[k] for k in ['title','plot','year','rating','genre','mpaa','director','studio','season','episode','tvshowtitle','playcount'] if k in data}
    if data.get('runtime'):info['duration']=data['runtime']
    if data.get('showtitle'):info['tvshowtitle']=data['showtitle']
    caption={'caption':data.get('title') or data.get('label',''),'meta':youtube_caption(data)} if is_youtube(data) else episode_card(data)
    properties.update(episodeCaption=caption['caption'],episodeMeta=search_caption(data) if data.get('_search_kind') else caption['meta'])
    hydrate_watch_metadata(li,data,info=info,properties=properties,initial=True)
    return li

