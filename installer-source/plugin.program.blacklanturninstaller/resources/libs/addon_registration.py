"""Register newly bundled code through Kodi, preserving existing disabled addons."""
import json
REPAIR34=frozenset(('script.module.tmdbhelper.sync.trakt','script.module.tmdbhelper.sync.mdblist'))
class RegistrationError(ValueError):pass

def rpc(kodi,method,params):
 value=json.loads(kodi.executeJSONRPC(json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params})))
 if 'error' in value:raise RegistrationError('Kodi could not finish enabling a new bundled add-on. Retry Update BlackLanturn.')
 return value['result']

def restore(state,kodi=None):
 entries=state.get('registration',{})
 if not entries:return
 allowed={aid for aid,entry in state.get('addons',{}).items() if entry.get('before') is None}|REPAIR34
 if not isinstance(entries,dict) or not set(entries)<=allowed:raise RegistrationError('Invalid add-on registration recovery targets.')
 for entry in entries.values():
  if not isinstance(entry,dict) or any(type(entry.get(key)) is not bool for key in ('enabled_before','existed_before','started')):raise RegistrationError('Invalid add-on registration recovery state.')
 if kodi is None:import xbmc as kodi
 for aid,entry in entries.items():
  if not entry.get('started'):continue
  try:rpc(kodi,'Addons.SetAddonEnabled',{'addonid':aid,'enabled':entry['enabled_before']})
  except RegistrationError:
   # A newly introduced addon may already be absent after an interrupted rollback.
   if entry['existed_before']:raise

class Registrar:
 def __init__(self,kodi):self.kodi=kodi
 def snapshot(self,plan):
  targets={aid:plan['chosen'][aid] for aid,entry in plan['state']['addons'].items() if entry['before'] is None}
  if plan.get('base_version')=='1.1.34':
   targets.update({aid:plan['chosen'][aid] for aid in REPAIR34 if aid in plan['chosen'] and plan['chosen'][aid]=='1.1.0'})
  entries={}
  for aid,version in targets.items():
   existed=aid not in plan.get('new_addons',())
   if existed:
    item=rpc(self.kodi,'Addons.GetAddonDetails',{'addonid':aid,'properties':['enabled','version']})['addon']
    if type(item.get('enabled')) is not bool:raise RegistrationError('Kodi add-on state is unavailable. Your setup has been kept.')
    enabled=item['enabled']
   else:enabled=False
   entries[aid]={'version':version,'enabled_before':enabled,'existed_before':existed,'started':False}
  plan['state']['registration']=entries;plan['_registration_kodi']=self.kodi
 def apply(self,plan,journal):
  if not plan['state'].get('registration'):return
  self.kodi.executebuiltin('UpdateLocalAddons',wait=True)
  for aid,entry in plan['state']['registration'].items():
   item=rpc(self.kodi,'Addons.GetAddonDetails',{'addonid':aid,'properties':['enabled','version']})['addon']
   if item.get('version')!=entry['version']:raise RegistrationError('Kodi registered a different bundled add-on version. Your previous build will be restored.')
   if item.get('enabled') is not True:
    entry['started']=True;journal(plan,plan['state'])
    rpc(self.kodi,'Addons.SetAddonEnabled',{'addonid':aid,'enabled':True})
   item=rpc(self.kodi,'Addons.GetAddonDetails',{'addonid':aid,'properties':['enabled','version']})['addon']
   if item.get('enabled') is not True or item.get('version')!=entry['version']:raise RegistrationError('A new bundled add-on is not ready. Your previous build will be restored.')
