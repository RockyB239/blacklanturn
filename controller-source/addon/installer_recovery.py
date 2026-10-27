"""Independent entrypoint for an interrupted update of the Installer itself.

Normal startup does one journal existence check. Only a pending self update can
load the fixed recovery module from the active Installer or its complete backup.
Saved settings, databases and unrelated add-ons stay under the existing updater's
preservation contract.
"""
import importlib.util
import json
import os
import tempfile
from pathlib import Path
import re
import xml.etree.ElementTree as ET

SELF='plugin.program.blacklanturninstaller'

class RecoveryError(ValueError):
    pass

def _plain(path):
    for part in (path,*path.parents):
        if part.is_symlink():
            raise RecoveryError('Installer recovery contains a linked path. Keep the recovery folder.')

def _save_registration(path,enabled):
    descriptor,temporary=tempfile.mkstemp(prefix='.blacklanturn-registration-',dir=str(path.parent))
    try:
        with os.fdopen(descriptor,'w') as stream:
            json.dump({'schema':1,'addon':SELF,'enabled':enabled},stream)
            stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
        parent=os.open(str(path.parent),os.O_RDONLY)
        try:os.fsync(parent)
        finally:os.close(parent)
    finally:
        if os.path.exists(temporary):os.unlink(temporary)

def _register(path,home,kodi,addon_factory):
    _plain(path)
    if path.stat().st_size>1024:raise ValueError('Invalid Installer registration recovery')
    wanted=json.loads(path.read_bytes())
    if set(wanted)!={'schema','addon','enabled'} or wanted['schema']!=1 or wanted['addon']!=SELF or type(wanted['enabled'])is not bool:
        raise ValueError('Invalid Installer registration recovery')
    meta=home/'addons'/SELF/'addon.xml';_plain(meta)
    node=ET.fromstring(meta.read_bytes());version=node.get('version')
    if node.get('id')!=SELF or not version:raise ValueError('Installer identity is unavailable')
    kodi.executebuiltin('UpdateLocalAddons',wait=True)
    def rpc(method,params):
        reply=json.loads(kodi.executeJSONRPC(json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params})))
        if 'error'in reply or 'result'not in reply:raise ValueError('Kodi could not register the recovered Installer')
        return reply['result']
    rpc('Addons.SetAddonEnabled',{'addonid':SELF,'enabled':wanted['enabled']})
    details=rpc('Addons.GetAddonDetails',{'addonid':SELF,'properties':['enabled','version']}).get('addon',{})
    if details.get('enabled')is not wanted['enabled'] or details.get('version')!=version:
        raise ValueError('Recovered Installer registration could not be verified')
    if wanted['enabled'] and addon_factory is not None and addon_factory(SELF).getAddonInfo('version')!=version:
        raise ValueError('Recovered Installer could not be opened')
    path.unlink()

def _core(root):
    _plain(root)
    meta=root/'addon.xml';core=root/'resources/libs/inplace_update.py'
    if not meta.is_file() or not core.is_file():return None
    _plain(meta);_plain(core)
    if meta.stat().st_size>65536:raise ValueError('Invalid Installer identity')
    node=ET.fromstring(meta.read_bytes())
    match=re.fullmatch(r'(\d+)\.(\d+)\.(\d+)(?:[~+][A-Za-z0-9._-]+)?',node.get('version',''))
    if node.get('id')!=SELF or not match or tuple(map(int,match.groups()))<(1,0,32):return None
    for name in ('standard_addons.py','archive_paths.py','portable_lock.py','component_update.py'):_plain(core.with_name(name))
    if tuple(map(int,match.groups()))>=(1,0,36):_plain(core.with_name('stream_io.py'))
    spec=importlib.util.spec_from_file_location('_blacklanturn_installer_recovery',core)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    if not hasattr(module,'UpdateBusy'):raise ValueError('Installer recovery protocol is unavailable')
    return module

def recover_installer(home,kodi=None,addon_factory=None):
    home=Path(home).resolve()
    work=home/'addons/.blacklanturn-update';journal=work/'journal.json'
    pending=home/'addons/.blacklanturn-installer-registration.json'
    _plain(work);_plain(pending)
    if not work.exists() and not pending.exists():
        return False
    try:
        if not journal.exists():
            recovered=False
            if work.exists():
                module=_core(home/'addons'/SELF)
                if module is None:raise ValueError('The Installer recovery entrypoint is missing')
                try:recovered=module.recover(home)
                except module.UpdateBusy:return False
            if pending.exists():
                if kodi is not None:_register(pending,home,kodi,addon_factory)
                return True
            return recovered
        _plain(journal)
        if not journal.is_file() or journal.stat().st_size>1024*1024:
            raise ValueError('Invalid update journal')
        state=json.loads(journal.read_bytes())
        if not isinstance(state,dict) or not isinstance(state.get('addons'),dict):
            raise ValueError('Invalid update journal')
        if SELF not in state['addons']:
            return False
        enabled=state['addons'][SELF].get('enabled_before')
        if type(enabled)is not bool:raise ValueError('Installer enabled-state recovery is unavailable')
        for root in (home/'addons'/SELF,work/'old'/SELF):
            module=_core(root)
            if module is None:continue
            try:
                recovered=module.recover(home,before_recover=lambda:_save_registration(pending,enabled))
                if recovered and kodi is not None:_register(pending,home,kodi,addon_factory)
                return recovered
            except module.UpdateBusy:
                return False
        raise ValueError('The Installer recovery entrypoint is missing')
    except RecoveryError:
        raise
    except (OSError,ValueError,KeyError,TypeError,ImportError,AttributeError,RuntimeError,SyntaxError,ET.ParseError) as exc:
        raise RecoveryError('An interrupted BlackLanturn update needs recovery. Keep the recovery folder and retry. '+str(exc)) from exc
