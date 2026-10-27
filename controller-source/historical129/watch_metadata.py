"""Watch metadata shared by new cards and stable visible-card hydration."""
from live_core import watch_state


def hydrate_watch_metadata(item,data):
    state=watch_state(data)
    item.setInfo('video',{'playcount':data.get('playcount',0)})
    for key,value in [('watchState',state['state']),('watchLabel',state['label']),('watchPercent',state['percent'])]:
        item.setProperty(key,str(value))
    resume=data.get('resume') if state['state']=='progress' else None
    item.getVideoInfoTag().setResumePoint(float(resume['position']) if resume else 0.,float(resume['total']) if resume else 0.)
