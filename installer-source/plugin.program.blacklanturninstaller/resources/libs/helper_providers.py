"""Exact reviewed Helper sync providers, conditional on their build policy."""
import json
from pathlib import Path
from resources.libs import managed_addons as managed

IDS=frozenset(('script.module.tmdbhelper.sync.trakt','script.module.tmdbhelper.sync.mdblist','script.module.tmdbhelper.sync.kodi'))
def manifest():
    return json.loads((Path(__file__).parents[1]/'managed-helper-providers.json').read_text())

def verify_archive(archive):
    records=manifest()['addons']
    for aid in IDS:
        prefix='addons/'+aid+'/'
        actual={name[len(prefix):]:managed._digest(aid,name[len(prefix):],archive.read(name)) for name in archive.namelist() if name.startswith(prefix) and not name.endswith('/')}
        if actual!=records[aid]['files']:
            raise managed.ProtectionError('The Helper sync provider package is missing or unreviewed. Update BlackLanturn Installer and retry. Your current build has been kept.')

def verify_installed(home):
    records=manifest()['addons']
    for aid in IDS:
        addon=Path(home)/'addons'/aid
        if not addon.exists() and not addon.is_symlink():continue
        message='Installed Helper sync provider has unreviewed source or version. Your current build has been kept; update compatibility support before installing.'
        actual=managed._source_files(addon,message)
        if managed._tree_digest(actual) not in records[aid]['installed_tree_sha256']:
            raise managed.ProtectionError(message)

def verify_kept(home,kept):
    records=manifest()['addons']
    for aid in IDS & set(kept):
        message='A Helper sync provider in your whitelist does not match this build. Remove it from My Whitelist and retry; your current build has been kept.'
        if managed._source_files(Path(home)/'addons'/aid,message)!=records[aid]['files']:
            raise managed.ProtectionError(message)

def prepare(marker,archive,home):
    version=managed._versions.upstream_version(managed.HELPER,archive.read(managed.PREFIX+'addon.xml'))
    needs_group=tuple(int(x) for x in version.split('.')[:3])>=(6,19,3)
    revision=marker.get('helper_sync_policy')
    if revision is None and not needs_group:return
    shutdown=marker.get('shutdown_patch')
    minimum='1.0.51' if shutdown=='retained-monitor-1' else '1.0.48' if marker.get('cocoscrapers_policy')=='parallel-airdate-1' else '1.0.47'
    reliability=marker.get('reliability_patch')
    if reliability=='navigation-focus-1' and shutdown=='retained-monitor-1':minimum='1.0.52'
    if marker.get('browse_patch') is not None:
        try:minimum=managed._versions.browse_minimum(marker,minimum)
        except ValueError as exc:raise managed.ProtectionError(str(exc)) from exc
    if (reliability is not None and (reliability!='navigation-focus-1' or shutdown!='retained-monitor-1')) or shutdown not in (None,'retained-monitor-1') or revision!='providers-1' or marker.get('installer_min_version')!=minimum or not needs_group:
        raise managed.ProtectionError('Update BlackLanturn Installer before installing this Helper sync provider group.')
    verify_archive(archive)
    if home is None:raise managed.ProtectionError('Helper sync provider source verification needs the current profile.')
    verify_installed(home)

def protect(db_path):
    managed.protect(db_path,providers=True)
