"""Runtime boundary for the installed private preview; no provider mutations."""
from pathlib import Path
import time

REQUIRED=('plugin.video.themoviedb.helper','plugin.video.umbrella','plugin.video.youtube')

class SkinStartupGate:
 """Allow Kodi's timed confirmation to finish before opening a modal Home."""
 def __init__(self,started):self.started=started
 def tick(self,skin,confirmation_visible,now):
  if skin!='skin.blacklanturn.preview' or now-self.started>30:return 'cancel'
  if now-self.started<1 or confirmation_visible:return 'wait'
  return 'ready'

def validate_paths(home,profile,addon):
 home,profile,addon=(Path(p).resolve() for p in (home,profile,addon))
 if addon != home/'addons/script.blacklanturn.preview':
  raise ValueError('Controller must be installed in the active Kodi home')
 if profile != home/'userdata' and home/'userdata/profiles' not in profile.parents:
  raise ValueError('Unexpected active Kodi profile')
 return profile

def check_dependencies(rpc,wait_for_abort=None,timeout=0,clock=None):
 clock=clock or time.monotonic
 deadline=clock()+max(0,timeout)
 while True:
  unavailable=[]
  for addon in REQUIRED:
   result=rpc('Addons.GetAddonDetails',{'addonid':addon,'properties':['enabled','version']})
   if not result.get('result',{}).get('addon',{}).get('enabled',False):unavailable.append(addon)
  remaining=deadline-clock()
  if not unavailable or wait_for_abort is None or remaining<=0:return unavailable
  if wait_for_abort(min(.25,remaining)):return unavailable
