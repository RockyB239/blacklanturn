"""Persistent typed navigation; independent of Kodi UI and private account data."""
from copy import deepcopy
from urllib.parse import urlsplit
import re
from live_core import valid_source

ICON_CHOICES=[('home', 'Home'), ('tv', 'Shows'), ('movies', 'Movies'), ('bookmark', 'My Stuff'), ('search', 'Search'), ('settings', 'Settings'), ('blacklanturn-lantern', 'Lantern'), ('action', 'Action'), ('action-lightning', 'Action — lightning'), ('addons', 'Add-ons'), ('adventure', 'Adventure'), ('animation', 'Animation'), ('anime', 'Anime'), ('biography', 'Biography'), ('collections', 'Collections'), ('comedy', 'Comedy'), ('concerts', 'Concerts'), ('continue-watching', 'Continue watching'), ('documentary', 'Documentary'), ('downloads', 'Downloads'), ('drama', 'Drama'), ('family', 'Family'), ('fantasy', 'Fantasy'), ('favourites', 'Favourites'), ('files', 'Files'), ('games', 'Games'), ('history', 'History'), ('horror', 'Horror'), ('international', 'International'), ('kids', 'Kids'), ('live-tv', 'Live TV'), ('music', 'Music'), ('music-addons', 'Music add-ons'), ('my-stuff', 'My Stuff'), ('mystery', 'Mystery'), ('new-releases', 'New releases'), ('news', 'News'), ('picture-addons', 'Picture add-ons'), ('pictures', 'Pictures'), ('playlist', 'Playlists'), ('podcasts', 'Podcasts'), ('popular', 'Popular'), ('program-addons', 'Program add-ons'), ('radio', 'Radio'), ('reality', 'Reality'), ('recordings', 'Recordings'), ('romance', 'Romance'), ('science-fiction', 'Science fiction'), ('science-fiction-orbit', 'Science fiction — orbit'), ('services', 'Services'), ('sports', 'Sports'), ('talk', 'Talk shows'), ('thriller', 'Thriller'), ('tools', 'Tools'), ('top-rated', 'Top rated'), ('trending', 'Trending'), ('guide', 'TV guide'), ('video-addons', 'Video add-ons'), ('war', 'War'), ('weather', 'Weather'), ('western', 'Western'), ('youtube', 'YouTube'), ('adventure-backpack', 'Adventure — backpack'), ('adventure-mountains', 'Adventure — mountains'), ('crime-lights', 'Crime — police lights'), ('documentary-graduate', 'Documentary — graduate'), ('drama-mask', 'Drama — mask'), ('stand-up', 'Stand-up'), ('warning', 'Warning'), ('creature-features', 'Creature Features')]
RETIRED_ICONS={'crime','western-horse','western-tumbleweed'}
ICON_CHOICES += [('crime-handcuffs','Crime — handcuffs'),('slashers','Slashers')]
KODI_DESTINATIONS=[('tvchannels','Live TV'),('tvguide','TV guide'),('tvrecordings','TV recordings'),('radiochannels','Radio'),('music','Music'),('pictures','Pictures'),('games','Games'),('favouritesbrowser','Kodi favourites'),('addonbrowser','Add-ons'),('weather','Weather'),('filemanager','File manager')]
SECTIONS=('Home','Shows','Movies','My Stuff','Add-ons','YouTube')

def sidebar_items(config,youtube_connected=False):
    return [{'id':'search','label':'Search','icon':'search','fixed_action':'search'}]+visible_navigation(config,youtube_connected)+[{'id':'settings','label':'Settings','icon':'settings','fixed_action':'settings'}]

def sidebar_layout(count):
    total=count+2;row_height=96 if total<=9 else 80
    return {'top':190,'height':min(864,total*row_height),'row_height':row_height,'settings_top':190+(total-1)*row_height}

def default_icon(label,destination):
    kind=destination.get('kind')
    if kind=='kodi':
        return {'tvchannels':'live-tv','tvguide':'guide','tvrecordings':'recordings','radiochannels':'radio','music':'music','pictures':'pictures','games':'games','favouritesbrowser':'favourites','addonbrowser':'addons','weather':'weather','filemanager':'files'}.get(destination.get('window'),'bookmark')
    if kind=='addon':
        return 'youtube' if urlsplit(destination.get('path','')).netloc=='plugin.video.youtube' else 'video-addons'
    slug=re.sub(r'[^a-z0-9]+','-',label.lower()).strip('-')
    slug={'shows':'tv','my-stuff':'bookmark','sci-fi':'science-fiction','scifi':'science-fiction','documentaries':'documentary','crime':'crime-handcuffs'}.get(slug,slug)
    return slug if slug in dict(ICON_CHOICES) else 'collections'

def status_settings(config):
    values=config.get('StatusDisplay',{})
    return {key:values.get(key,default) is True for key,default in [('clock',True),('date',False),('weather',False)]}

def migrate_navigation(config):
    result=deepcopy(config)
    if 'Sidebar' not in result:
        result['Sidebar']=[{'id':i,'label':s,'icon':icon,'enabled':True,'destination':{'kind':'section','section':s}} for i,s,icon in [('home','Home','home'),('shows','Shows','tv'),('movies','Movies','movies'),('saved','My Stuff','bookmark')]]
    result.setdefault('StatusDisplay',status_settings(result))
    result['NavigationSchema']=1
    return result

def visible_navigation(config,youtube_connected=False):
    items=[]
    for entry in config.get('Sidebar',[]):
        if not isinstance(entry,dict) or not entry.get('enabled',True):continue
        if entry.get('destination',{}).get('section')=='YouTube' and not youtube_connected:continue
        item=deepcopy(entry)
        if item.get('icon') not in dict(ICON_CHOICES) and item.get('icon') not in RETIRED_ICONS:item['icon']='bookmark'
        items.append(item)
    if youtube_connected and not any(x.get('destination',{}).get('section')=='YouTube' for x in config.get('Sidebar',[]) if isinstance(x,dict)):
        items.append({'id':'youtube','label':'YouTube','icon':'youtube','enabled':True,'destination':{'kind':'section','section':'YouTube'}})
    return items

def resolve_destination(destination,config,section='Movies'):
    if not isinstance(destination,dict):return None
    kind=destination.get('kind')
    if kind=='section' and destination.get('section') in SECTIONS:return {'kind':kind,'section':destination['section']}
    if kind=='kodi' and destination.get('window') in dict(KODI_DESTINATIONS):return {'kind':kind,'window':destination['window']}
    if kind=='addon':
        path=destination.get('path','')
        if not isinstance(path,str) or any(ord(c)<32 or c in '\"' for c in path):return None
        addon=urlsplit(path).netloc
        if valid_source(path) and re.fullmatch(r'[a-z0-9_.-]+',addon):return {'kind':kind,'path':path,'addon':addon}
    if kind=='page':
        page=next((p for group in ('Genres','Categories') for p in config.get(group,[]) if p.get('id')==destination.get('page_id')),None)
        if not page:return None
        placement=page.get('section','Both');target=placement if placement in ('Movies','Shows') else section if section in ('Movies','Shows') else 'Movies'
        return {'kind':kind,'page_id':page['id'],'label':page['label'],'section':target,'rows':[deepcopy(r) for r in page.get('rows',[]) if r.get('enabled',True) and valid_source(r.get('path',''))]}
    return None

def edit_navigation(config,entry_id,action,value=None):
    result=deepcopy(config);items=result.setdefault('Sidebar',[])
    if action=='add':
        if not isinstance(value,dict) or not value.get('id') or value['id'] in {e.get('id') for e in items}|{'search','settings'}:raise ValueError('Duplicate or missing entry ID')
        if not value.get('label','').strip() or not resolve_destination(value.get('destination'),result):raise ValueError('Invalid destination')
        items.append(deepcopy(value));return result
    index=next((n for n,e in enumerate(items) if e.get('id')==entry_id),None)
    if index is None:raise ValueError('Entry no longer exists')
    item=items[index]
    if action=='rename' and isinstance(value,str) and value.strip():item['label']=value.strip()
    elif action=='icon' and value in dict(ICON_CHOICES):item['icon']=value
    elif action=='destination':
        if not resolve_destination(value,result):raise ValueError('Invalid destination')
        item['destination']=deepcopy(value)
    elif action in ('up','down'):
        target=index+(-1 if action=='up' else 1)
        if 0<=target<len(items):items[index],items[target]=items[target],items[index]
    elif action=='toggle':item['enabled']=not item.get('enabled',True)
    elif action=='remove':items.pop(index)
    return result
