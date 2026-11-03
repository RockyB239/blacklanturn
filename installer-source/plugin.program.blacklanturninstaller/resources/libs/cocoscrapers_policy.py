"""Exact reviewed CocoScrapers concurrency source; no runtime repatching."""
import json
from pathlib import Path
from resources.libs import managed_addons as managed

ID='script.module.cocoscrapers'
POLICY='parallel-airdate-1'
def manifest():
    return json.loads((Path(__file__).parents[1]/'managed-cocoscrapers.json').read_text())

def verify_archive(archive):
    prefix='addons/'+ID+'/'
    actual={name[len(prefix):]:managed._digest(ID,name[len(prefix):],archive.read(name)) for name in archive.namelist() if name.startswith(prefix) and not name.endswith('/')}
    if actual!=manifest()['files']:
        raise managed.ProtectionError('The CocoScrapers package is missing or unreviewed. Update BlackLanturn Installer and retry. Your current build has been kept.')

def verify_installed(home):
    addon=Path(home)/'addons'/ID
    if not addon.exists() and not addon.is_symlink():return
    message='Installed CocoScrapers has unreviewed source or version. Your current build has been kept; update compatibility support before installing.'
    actual=managed._source_files(addon,message)
    if managed._tree_digest(actual) not in manifest()['installed_tree_sha256']:
        raise managed.ProtectionError(message)

def verify_kept(home,kept):
    if ID not in kept:return
    message='CocoScrapers in your whitelist does not match this build. Remove it from My Whitelist and retry; your current build has been kept.'
    if managed._source_files(Path(home)/'addons'/ID,message)!=manifest()['files']:
        raise managed.ProtectionError(message)

def prepare(marker,archive,home):
    key='addons/'+ID+'/addon.xml'
    revision=marker.get('cocoscrapers_policy')
    if key not in archive.namelist():
        if revision is None:return
        raise managed.ProtectionError('The CocoScrapers package is missing. Your current build has been kept.')
    raw=archive.read(key)
    protected=managed._versions.normalize_metadata(ID,raw)!=raw
    if revision is None and not protected:return
    shutdown=marker.get('shutdown_patch')
    minimum='1.0.51' if shutdown=='retained-monitor-1' else '1.0.48'
    reliability=marker.get('reliability_patch')
    if reliability=='navigation-focus-1' and shutdown=='retained-monitor-1':minimum='1.0.52'
    if marker.get('browse_patch') is not None:
        try:minimum=managed._versions.browse_minimum(marker,minimum)
        except ValueError as exc:raise managed.ProtectionError(str(exc)) from exc
    if (reliability is not None and (reliability!='navigation-focus-1' or shutdown!='retained-monitor-1')) or shutdown not in (None,'retained-monitor-1') or revision!=POLICY or marker.get('installer_min_version')!=minimum or not protected:
        raise managed.ProtectionError('Update BlackLanturn Installer before installing this CocoScrapers source policy.')
    verify_archive(archive)
    if home is None:raise managed.ProtectionError('CocoScrapers source verification needs the current profile.')
    verify_installed(home)

def protect(db_path):
    managed.protect(db_path,cocoscrapers=True)
