"""Watch metadata shared by new cards and stable visible-card hydration."""
from live_core import watch_state

def refreshed_display_metadata(item,replacement):
    """Enrich one matched title while retaining displayed identity/art/layout."""
    value={key:data for key,data in item.items() if key not in ('playcount','resume')}
    for key in ('plot','year','rating','votes','genre','country','runtime','mpaa','cast','director','studio','trailer','premiered','writer','set','_series_status','_rating_source','playcount','resume'):
        if key in replacement:value[key]=replacement[key]
    return value


def hydrate_watch_metadata(item,data,info=None,properties=None,initial=False):
    state=watch_state(data)
    merged=dict(info or {});merged['playcount']=data.get('playcount',0)
    item.setInfo('video',merged)
    props=dict(properties or {})
    props.update({key:str(value) for key,value in [('watchState',state['state']),('watchLabel',state['label']),('watchPercent',state['percent'])]})
    # Fresh native items already have empty properties and a zero resume point.
    # Displayed refreshes must still write empties/zero to clear prior state.
    item.setProperties({key:value for key,value in props.items() if value!=''} if initial else props)
    resume=data.get('resume') if state['state']=='progress' else None
    if resume or not initial:
        item.getVideoInfoTag().setResumePoint(float(resume['position']) if resume else 0.,float(resume['total']) if resume else 0.)
