import json,time,traceback
from pathlib import Path
import xbmc,xbmcgui,xbmcaddon,xbmcvfs,sys
BASE=Path(__file__).parent;OUT=BASE/'benchmark.json';MON=xbmc.Monitor();DEADLINE=time.monotonic()+360;UI_WINDOW=None
sys.path.insert(0,str(BASE))
sys.path.insert(0,xbmcaddon.Addon('script.blacklanturn.preview').getAddonInfo('path'))
from row_readiness import media_route,settled as fresh_settled,COMPARE_PROTOCOL
from discovery_core import page_rows
from live_core import my_stuff_rows
from live_review import tmdb
from youtube_core import tab_rows
CONFIG=json.loads((Path(xbmcvfs.translatePath('special://profile/'))/'addon_data/script.blacklanturn.preview/rows.json').read_bytes())
EXPECTED=None
def expected_for(name):
    definitions=(my_stuff_rows(CONFIG['Saved'],tmdb) if name=='My Stuff' else tab_rows('home') if name=='YouTube' else page_rows(CONFIG,name))[:2]
    labels=[d['label'] for d in definitions]
    routes=[None if name=='My Stuff' else {'provider':'plugin.video.youtube'} if name=='YouTube' else media_route(d['path']) for d in definitions]
    return labels,routes

R={'status':'running','row_visits':[],'protocol':COMPARE_PROTOCOL}
def save():
    p = OUT.with_suffix('.pending')
    p.write_text(json.dumps(R, indent=2))
    p.replace(OUT)

def rpc(method, params=None):
    v = json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params or {}})))
    if 'error' in v:
        raise RuntimeError(method + ': ' + v['error'].get('message', 'RPC failure'))
    return v['result']

def info(k):
    return rpc('XBMC.GetInfoLabels',{'labels':[k]}).get(k,'')

def prop(k):
    return info('Window(' + str(xbmcgui.getCurrentWindowId()) + ').Property(' + k + ')')

def focus():
    return int(info('System.CurrentControlId') or 0)

def count(n):
    return int(info('Container(' + str(n) + ').NumItems') or 0)

def label(n):
    return info('Container(' + str(n) + ').ListItem.Label')

def act(name):
    xbmc.executebuiltin('Action(' + name + ')', False)

def wait(test, seconds=12):
    end = min(time.monotonic() + seconds, DEADLINE)
    while not MON.abortRequested() and time.monotonic() < end:
        result = test()
        if result:
            return result
        MON.waitForAbort(0.05)
    raise RuntimeError('Native timeout at ' + R.get('stage','startup'))

def snapshot():
    window=xbmcgui.getCurrentWindowId()
    names=['System.CurrentControlId']+['Window('+str(window)+').Property('+x+')' for x in ('eyebrow','rowState0','rowState1','row0','row1','preview')]+['Container('+str(n)+').'+key for n in (900,901) for key in ('NumItems','ListItem.FileNameAndPath')]
    v=rpc('XBMC.GetInfoLabels',{'labels':names})
    def prop_value(k):return v.get('Window('+str(window)+').Property('+k+')','')
    return {'window':window,'focus':int(v.get(names[0]) or 0),'eyebrow':prop_value('eyebrow'),'states':[prop_value('rowState0'),prop_value('rowState1')],'counts':[int(v.get('Container('+str(n)+').NumItems') or 0) for n in (900,901)],'labels':[prop_value('row0'),prop_value('row1')],'preview':prop_value('preview'),'routes':[media_route(v.get('Container('+str(n)+').ListItem.FileNameAndPath','')) for n in (900,901)]}

def settled(heading=None):
    value=snapshot()
    return value if EXPECTED and fresh_settled(value,heading or value['eyebrow'],*EXPECTED) else None

def sidebar():
    for _ in range(15):
        if focus() == 50:
            MON.waitForAbort(0.35)
            if focus() == 50:
                return
        act('Back')
        MON.waitForAbort(0.35)
    raise RuntimeError('Sidebar inaccessible ' + str(snapshot()))

def select_section(name):
    global EXPECTED
    EXPECTED=expected_for(name)
    sidebar()
    act('FirstPage')
    wait(lambda : label(50) == 'Search', 4)
    for _ in range(10):
        if label(50) == name:
            break
        old = label(50)
        act('Down')
        wait(lambda : label(50) != old, 4)
    else:
        raise RuntimeError('Missing section ' + name)
    t = time.monotonic()
    act('Select')
    MON.waitForAbort(0.12)
    return t

def row_visit(name):
    t = select_section(name)
    s = wait(lambda : settled('YOUTUBE / HOME' if name=='YouTube' else name.upper()), 50)
    MON.waitForAbort(0.12)
    s = wait(lambda : settled('YOUTUBE / HOME' if name=='YouTube' else name.upper()), 10)
    value = {'section': name, 'seconds': round(time.monotonic() - t, 3), 'ui': s}
    R['row_visits'].append(value)
    sidebar()
    save()
try:
 # Wait until the temporary Favourites launcher is closed.
 wait(lambda:bool(prop('eyebrow')),20)
 UI_WINDOW=xbmcgui.getCurrentWindowId()
 if rpc('Player.GetActivePlayers'):raise RuntimeError('Playback active; left untouched')
 for cycle in range(4):
  for name in ('Shows','Movies','Home','YouTube','My Stuff'):
   R['stage']='cycle '+str(cycle+1)+' '+name
   before=len(R['row_visits']);row_visit(name);R['row_visits'][-1]['cycle']=cycle
   if rpc('Player.GetActivePlayers'):
    if prop('preview')=='playing':
     act('Back');wait(lambda:not rpc('Player.GetActivePlayers'),15)
    else:raise RuntimeError('Unexpected full playback; no further navigation')
 R['stage']='finish Home';select_section('Home');wait(lambda:settled('HOME'),25)
 R['passed']=True;R['status']='completed'
except Exception as exc:R['passed']=False;R['status']='failed';R['error']=str(exc);R['trace']=traceback.format_exc()
finally:save()
