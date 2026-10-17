"""Validate portable build payloads and retain Kodi-managed native components."""
import json
from pathlib import PurePosixPath
import re
import stat
import zipfile
import xml.etree.ElementTree as E

NATIVE_ADDONS = ('inputstream.adaptive', 'script.module.pil')
POLICY_PATH = 'userdata/blacklanturn-build.json'

class CompatibilityError(Exception):
    pass

def _rpc(kodi, method, params):
    response = json.loads(kodi.executeJSONRPC(json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params})))
    return response.get('result')

def _version(value):
    return tuple(int(x) for x in re.findall(r'\d+',str(value))[:3])

def _details(kodi, aid):
    result = _rpc(kodi, 'Addons.GetAddonDetails', {'addonid':aid,'properties':['enabled','version','path']})
    return (result or {}).get('addon')

def _compatible(aid, details):
    if not details or not details.get('enabled'): return False
    version = _version(details.get('version',''))
    if not version: return False
    return version[0] == 21 if aid == 'inputstream.adaptive' else version >= (1,1,7)

def prepare(path, kodi):
    """Called after download, before OpenWizard performs any profile cleanup."""
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if not names or len(set(names)) != len(names):
                raise CompatibilityError('The download is incomplete. Your current build has been kept.')
            for item in archive.infolist():
                name = item.filename
                p = PurePosixPath(name)
                if p.is_absolute() or '..' in p.parts or '\\' in name or not p.parts or p.parts[0] not in ('addons','userdata') or stat.S_ISLNK(item.external_attr >> 16):
                    raise CompatibilityError('The download is not a valid build package. Your current build has been kept.')
            if archive.testzip() is not None:
                raise CompatibilityError('The download is damaged. Your current build has been kept.')
            addon_ids = sorted({PurePosixPath(n).parts[1] for n in names if n.startswith('addons/') and len(PurePosixPath(n).parts)==3 and n.endswith('/addon.xml')})
            if not addon_ids:
                raise CompatibilityError('The download has no add-ons. Your current build has been kept.')
            native_needed = set()
            for aid in addon_ids:
                meta = E.fromstring(archive.read('addons/'+aid+'/addon.xml'))
                if meta.get('id') != aid:
                    raise CompatibilityError('The package add-on information is invalid.')
                native_needed.update(dep.get('addon') for dep in meta.findall('./requires/import') if dep.get('addon') in NATIVE_ADDONS)
                if aid in NATIVE_ADDONS: native_needed.add(aid)
            policy = None
            if POLICY_PATH in names:
                if archive.getinfo(POLICY_PATH).file_size > 32768:
                    raise CompatibilityError('The package compatibility information is invalid.')
                policy = json.loads(archive.read(POLICY_PATH))
                if not isinstance(policy,dict) or policy.get('schema') != 1 or policy.get('kodi_major') != 21 or policy.get('edition') not in ('apple','general'):
                    raise CompatibilityError('This build package is not supported by this installer.')
                for name in names:
                    parts=PurePosixPath(name).parts
                    if (len(parts)>1 and parts[0]=='addons' and parts[1] in NATIVE_ADDONS) or (len(parts)>2 and parts[:2]==('userdata','addon_data') and parts[2] in NATIVE_ADDONS) or (parts[:2]==('userdata','Database') and parts[-1].startswith('Addons') and parts[-1].endswith('.db')) or name.endswith(('.so','.dylib','.dll')):
                        raise CompatibilityError('The package contains device-specific components. Your current build has been kept.')
    except CompatibilityError:
        raise
    except (OSError,ValueError,zipfile.BadZipFile,RuntimeError,KeyError,E.ParseError):
        raise CompatibilityError('The download is incomplete or damaged. Your current build has been kept.') from None
    if policy is None and not native_needed:
        return {'addon_ids':addon_ids,'policy':None}
    if _version(kodi.getInfoLabel('System.BuildVersion'))[:1] != (21,) or _version(kodi.getInfoLabel('System.BuildVersion')) < (21,3):
        raise CompatibilityError('This build requires Kodi 21.3 Omega. Your current build has been kept.')
    apple = any(kodi.getCondVisibility(x) for x in ('System.Platform.Darwin','System.Platform.OSX','System.Platform.IOS'))
    android = kodi.getCondVisibility('System.Platform.Android')
    if policy and ((policy['edition']=='apple' and not apple) or (policy['edition']=='general' and not android)):
        raise CompatibilityError('This build is for a different device. Your current build has been kept.')
    try:
        for aid in NATIVE_ADDONS if policy else sorted(native_needed):
            if kodi.Monitor().abortRequested():
                raise CompatibilityError('Installation cancelled. Your current build has been kept.')
            details = _details(kodi,aid)
            if details and not details.get('enabled'):
                _rpc(kodi,'Addons.SetAddonEnabled',{'addonid':aid,'enabled':True})
                details = _details(kodi,aid)
            if _compatible(aid,details): continue
            if details:
                raise CompatibilityError('Update '+aid+' through Kodi’s official repository, then retry. Your current build has been kept.')
            repo = _details(kodi,'repository.xbmc.org')
            origin = _rpc(kodi,'Settings.GetSettingValue',{'setting':'addons.updatemode'})
            if not repo or not repo.get('enabled') or not origin or origin.get('value') != 0:
                raise CompatibilityError('Install '+aid+' from the official Kodi repository, then retry. Your current build has been kept.')
            kodi.executebuiltin('InstallAddon('+aid+')',wait=True)
            if not _compatible(aid,_details(kodi,aid)):
                raise CompatibilityError('Playback setup was cancelled or unavailable. Your current build has been kept.')
    except CompatibilityError:
        raise
    except (RuntimeError,ValueError,TypeError,KeyError):
        raise CompatibilityError('Playback setup could not be verified. Your current build has been kept.') from None
    return {'addon_ids':addon_ids,'policy':policy}
