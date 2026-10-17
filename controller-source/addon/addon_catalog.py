"""Installed add-on shelves; consumes Kodi's content-filtered read-only catalogue."""
import re

CATALOGUE='script.blacklanturn.preview'

def catalogue_items(addons,category):
    if category not in ('video','program'):raise ValueError('Unknown add-on category')
    result=[]
    for addon in addons:
        identity=addon.get('addonid','')
        if not addon.get('enabled') or identity==CATALOGUE or not re.fullmatch(r'[a-z0-9_.-]+',identity):continue
        name=addon.get('name') or addon.get('label') or identity
        icon=addon.get('thumbnail') or 'DefaultAddon.png'
        script=addon.get('type')=='xbmc.python.script' or identity.startswith('script.')
        result.append({'addonid':identity,'launch_kind':'script' if script else 'plugin','addon_category':category,
            'title':name,'label':name,'file':'plugin://'+identity+'/','filetype':'directory','type':'addon',
            'plot':addon.get('description') or addon.get('summary',''),'genre':['Video add-on' if category=='video' else 'Program add-on'],
            'art':{'square':icon,'icon':icon,'fanart':addon.get('fanart','')}})
    return sorted(result,key=lambda item:re.sub(r'\[/?[^]]+\]','',item['title']).casefold())

def catalogue_category(path):
    from urllib.parse import urlsplit,parse_qs
    parsed=urlsplit(path);query=parse_qs(parsed.query)
    if parsed.scheme!='plugin' or parsed.netloc!=CATALOGUE or query.get('info')!=['installed_addons']:return None
    category=query.get('category',[''])[0]
    if category not in ('video','program'):raise ValueError('Unknown add-on category')
    return category

def launch_destination(item):
    identity=item.get('addonid','')
    if item.get('type')!='addon' or not re.fullmatch(r'[a-z0-9_.-]+',identity) or identity==CATALOGUE:return None
    if item.get('launch_kind')=='script':
        return {'window':'programs','parameters':['addons://sources/executable/','return'],'script':identity}
    return {'window':'programs' if item.get('addon_category')=='program' else 'videos','parameters':['plugin://'+identity+'/','return']}
