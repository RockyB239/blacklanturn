"""Temporary cross-script update activity; never a saved user preference."""
import json,math,time
KEY='BlackLanturn.UpdateActivity'
LEASE_SECONDS=10

def _window():
    import xbmcgui
    return xbmcgui.Window(10000)

def active(window=None,clock=time.time):
    try:
        value=json.loads((window or _window()).getProperty(KEY))
        until=value['until'];now=clock()
        return (isinstance(value['owner'],str) and bool(value['owner']) and type(until) in (int,float)
                and math.isfinite(until) and now<until<=now+LEASE_SECONDS+1)
    except (ImportError,AttributeError,RuntimeError,ValueError,TypeError,KeyError):return False


def wait_for_idle(aborted=None):
    if aborted is None:
        try:
            import xbmc
            aborted=xbmc.Monitor().abortRequested
        except (ImportError,AttributeError):aborted=lambda:False
    while active():
        if aborted():return False
        time.sleep(.2)
    return not aborted()
