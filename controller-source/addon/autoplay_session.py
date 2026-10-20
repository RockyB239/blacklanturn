"""Read the runtime Umbrella choice without importing its account/settings code."""
import json,math,time
from live_core import episode_identity

PROPERTY='BlackLanturn.SourceSession.v1'
PREPARED='umbrella.preResolved_sourceSession'
URL='umbrella.preResolved_nextUrl'

def label(item,raw,now=None):
    try:
        identity=episode_identity(item)
        policy=json.loads(raw or '{}')
        if not identity or not isinstance(policy,dict) or policy.get('version')!=1:return ''
        show,season=policy['scope']
        if show!='tmdb:'+identity['tmdb_id']:return ''
        if (identity['season'],identity['episode'])<(int(season),int(policy['episode'])):return ''
        if not 0<=(time.time() if now is None else now)-float(policy['created'])<21600:return ''
        ceiling=float(policy['ceiling']);provider=policy['debrid']
        if not math.isfinite(ceiling) or ceiling<=0 or not isinstance(provider,str) or not provider:return ''
        # Retain the real cap; rounding up could imply a larger source is allowed.
        return 'Following your selection: %s · up to %s GB'%(provider,format(ceiling,'.8g'))
    except (KeyError,TypeError,ValueError):return ''

def clear(window):
    for key in (PROPERTY,PREPARED,URL):window.clearProperty(key)
