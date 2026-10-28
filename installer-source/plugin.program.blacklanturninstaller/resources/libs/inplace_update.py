"""Whole-code-tree updates. Never installs payload defaults or cleans a profile.

One writer holds an OS lock across staging and commit. A durable intent journal
retains the previous code until every replacement and release receipt is saved.
An interrupted writer is rolled back before a later update or at Kodi startup.
"""
import errno
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import xml.etree.ElementTree as E
import zipfile

SELF = 'plugin.program.blacklanturninstaller'
MANAGED = frozenset(('plugin.video.themoviedb.helper', 'plugin.video.umbrella', 'script.module.jurialmunkey', 'plugin.video.youtube'))
NATIVE = frozenset(('inputstream.adaptive', 'script.module.pil'))
META = ('blacklanturn-build.json', 'blacklanturn-releases.json', 'blacklanturn-install-complete.json')
ID = re.compile(r'[a-z0-9][a-z0-9_.-]{0,120}')

class UpdateError(ValueError):
    pass

class UpdateBusy(UpdateError):
    """A live writer owns recovery and must be allowed to finish."""
    pass

def _module(name):
    spec = importlib.util.spec_from_file_location('_inplace_' + name, Path(__file__).with_name(name + '.py'))
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value

locks = _module('portable_lock')
fcntl = locks.fcntl  # Existing Unix failure-injection checks share the real backend.
versions = _module('standard_addons')
paths = _module('archive_paths')
stream_io = _module('stream_io')

def _write(path, raw):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.writing')
    try:
        with temporary.open('wb') as stream:
            if hasattr(raw, 'read'): stream_io.transfer(raw, stream)
            else: stream.write(raw)
            stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists(): temporary.unlink()

def _sync(path):
    if os.name=='nt' and Path(path).is_dir():return
    descriptor = os.open(str(path), os.O_RDONLY)
    try: os.fsync(descriptor)
    finally: os.close(descriptor)

def _plain(path):
    for cursor in (path, *path.parents):
        if cursor.is_symlink(): raise UpdateError('An update target is linked. Nothing has been updated.')

def _tree(path):
    if not path.exists(): return None
    _plain(path)
    if not path.is_dir(): raise UpdateError('An add-on target is not a directory.')
    files = {}; aliases = set()
    for parent, dirs, names in os.walk(path, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d != '__pycache__')
        for name in dirs + names:
            p = Path(parent)/name; relative = p.relative_to(path).as_posix()
            if p.is_symlink() or (not p.is_dir() and not p.is_file()) or relative.casefold() in aliases:
                raise UpdateError('An add-on contains linked or ambiguous files: ' + path.name)
            aliases.add(relative.casefold())
        for name in names:
            if name.endswith(('.pyc', '.pyo')): continue
            p = Path(parent)/name; files[p.relative_to(path).as_posix()] = stream_io.file_hash(p)
    return files

def _identity(raw):
    marker = json.loads(raw)
    if (not isinstance(marker, dict) or marker.get('schema') != 3 or marker.get('edition') not in ('apple', 'general')
            or not re.fullmatch(r'\d+\.\d+\.\d+', marker.get('build_version', ''))
            or type(marker.get('release_revision', 0)) is not int):
        raise UpdateError('This profile needs a supported BlackLanturn installation before it can be updated.')
    return marker

def available(home):
    try:
        path = Path(home).resolve()/'userdata'/META[0]; _plain(path); _identity(path.read_bytes()); return True
    except (OSError, ValueError, TypeError): return False

def _lock(home):
    home = Path(home).resolve(); _plain(home/'addons'); _plain(home/'userdata')
    lock = home/'addons/.blacklanturn-update.lock'; _plain(lock)
    descriptor = os.open(str(lock), os.O_CREAT | os.O_RDWR, 0o600)
    try: locks.acquire(descriptor)
    except OSError as exc:
        os.close(descriptor)
        if exc.errno in (errno.EACCES, errno.EAGAIN):
            raise UpdateBusy('Another BlackLanturn update is running. Please wait for it to finish.') from None
        raise
    return {'home': str(home), 'work': str(home/'addons/.blacklanturn-update'), '_lock': descriptor}

def release(plan):
    descriptor = plan.pop('_lock', None)
    if descriptor is not None:
        try: locks.unlock(descriptor)
        finally: os.close(descriptor)

def _journal(plan, state):
    _write(Path(plan['work'])/'journal.json', json.dumps(state, sort_keys=True).encode())
    _sync(Path(plan['work']))

def _recover_locked(plan):
    work = Path(plan['work']); home = Path(plan['home']); _plain(work)
    if not work.exists(): return False
    journal = work/'journal.json'
    if not journal.exists():
        # Staging never modifies installed code. With our exclusive lock, an
        # unjournaled directory is an interrupted preparation, not a live writer.
        shutil.rmtree(work); return True
    state = json.loads(journal.read_bytes())
    if (state.get('schema') != 1 or state.get('status') not in ('prepared', 'applying', 'committed')
            or not isinstance(state.get('addons'), dict) or not isinstance(state.get('metadata'), dict)):
        raise UpdateError('Update recovery information needs attention. Keep the recovery folder.')
    if any(not ID.fullmatch(aid) or aid in NATIVE for aid in state['addons']):
        raise UpdateError('Update recovery targets are invalid. Keep the recovery folder.')
    if set(state['metadata']) != set(META): raise UpdateError('Update recovery metadata is invalid.')
    if state['status'] != 'committed':
        if state.get('registration'):
            _module('addon_registration').restore(state,plan.get('_registration_kodi'))
        discard = work/'discard'; discard.mkdir(exist_ok=True)
        # Restore the Installer first so a second interrupted recovery still has
        # its normal entry point. JSON key order is not transaction order.
        for aid in sorted(state['addons'], key=lambda aid: (aid == SELF, aid), reverse=True):
            entry = state['addons'][aid]
            target = home/'addons'/aid; old = work/'old'/aid; _plain(target); _plain(old)
            if old.exists():
                if target.exists():
                    abandoned = discard/aid
                    if abandoned.exists(): shutil.rmtree(abandoned)
                    os.replace(target, abandoned)
                os.replace(old, target)
            elif entry.get('started') and entry['before'] is None and target.exists():
                if _tree(target) != entry['after']: raise UpdateError('A new add-on changed during recovery. Keep recovery data.')
                os.replace(target, discard/aid)
        for name, entry in state['metadata'].items():
            if not entry.get('started'): continue
            target = home/'userdata'/name; old = work/'metadata-old'/name; _plain(target)
            if old.is_file(): os.replace(old, target)
            elif not entry['existed'] and target.exists(): target.unlink()
        _sync(home/'addons'); _sync(home/'userdata')
    shutil.rmtree(work)
    return True

def recover(home, before_recover=None):
    plan = _lock(home)
    try:
        # The independent startup caller must preserve registration intent
        # outside our work folder before recovery can remove the journal.
        if before_recover is not None:
            try: before_recover()
            except Exception as exc:
                raise UpdateError('Recovery preparation failed: '+str(exc)) from exc
        return _recover_locked(plan)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise UpdateError('The previous update could not be recovered. Keep the recovery folder and retry: ' + str(exc)) from exc
    finally: release(plan)

def cancel(plan):
    if '_lock' not in plan: return
    try: _recover_locked(plan)
    finally: release(plan)

def _closure(home, chosen, kodi):
    """Check mandatory dependencies of final bundled AND untouched user add-ons."""
    final = {}; addons = home/'addons'
    for root in addons.iterdir():
        if root.name.startswith('.') or root.name in chosen: continue
        meta = root/'addon.xml'
        if meta.is_file():
            node = E.fromstring(meta.read_bytes())
            if node.get('id') != root.name: raise UpdateError('Installed add-on identity differs: ' + root.name)
            final[root.name] = node
    final.update(chosen)
    system = {'xbmc.python': '3.0.1', 'xbmc.gui': '5.17.0', 'xbmc.json': '13.0.0', 'xbmc.addon': '21.3.0', 'kodi.resource': '1.0.0'}
    for aid, node in final.items():
        for dep in node.findall('./requires/import'):
            if dep.get('optional') == 'true': continue
            did = dep.get('addon'); minimum = dep.get('version', '0')
            # Only dependencies affected by this update are relevant for an
            # untouched addon. Kodi owns binary API pseudo-dependencies.
            if aid not in chosen and did not in chosen: continue
            if did in final: actual = final[did].get('version')
            elif did in system: actual = system[did]
            else:
                response = json.loads(kodi.executeJSONRPC(json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'Addons.GetAddonDetails', 'params': {'addonid': did, 'properties': ['version']}})))
                actual = response.get('result', {}).get('addon', {}).get('version')
            if actual is None or versions.compare(actual, minimum) < 0:
                raise UpdateError('Update needs a compatible dependency: ' + aid + ' → ' + str(did) + '. Your add-ons have been kept.')

def prepare(archive_path, home, kodi):
    plan = _lock(home); expanded = None
    try:
        if _recover_locked(plan):
            raise UpdateError('The interrupted update has been recovered. Please start Update BlackLanturn again.')
        home = Path(plan['home']); work = Path(plan['work'])
        installed = _identity((home/'userdata'/META[0]).read_bytes())
        components = _module('component_update')
        if components.is_component(archive_path):
            work.mkdir()
            expanded = components.expand(archive_path, home, work)
            archive_path = expanded
        from resources.libs import platform_compatibility
        validated = platform_compatibility.prepare(archive_path, kodi, home=home, allow_native_changes=False)
        target = validated.get('policy')
        if not target: raise UpdateError('This package does not support in-place updates.')
        with zipfile.ZipFile(archive_path) as archive:
            paths.validate(archive)
            target_raw = archive.read('userdata/'+META[0]); target = _identity(target_raw)
            if target['edition'] != installed['edition']: raise UpdateError('Choose the installed BlackLanturn edition for this update.')
            if (versions.compare(target['build_version'], installed['build_version']), target.get('release_revision', 0)-installed.get('release_revision', 0)) < (0, 0):
                raise UpdateError('This update is older than your installed BlackLanturn build.')
            bundled = {}
            for name in archive.namelist():
                parts = name.split('/')
                if len(parts) == 3 and parts[0] == 'addons' and parts[2] == 'addon.xml':
                    aid = parts[1]
                    if not ID.fullmatch(aid) or aid in NATIVE: raise UpdateError('Unsupported bundled add-on target.')
                    bundled[aid] = versions._meta(archive.read(name), aid)
            chosen = {}; entries = {}; retained = []
            work.mkdir(exist_ok=True); (work/'old').mkdir()
            for aid, node in bundled.items():
                root = home/'addons'/aid; before = _tree(root)
                if before is not None and aid not in MANAGED:
                    current = versions._meta((root/'addon.xml').read_bytes(), aid)
                    if versions.compare(current.get('version'), node.get('version')) > 0:
                        chosen[aid] = current; retained.append(aid); continue
                chosen[aid] = node
                prefix = 'addons/'+aid+'/'
                files = [name for name in archive.namelist() if name.startswith(prefix) and not name.endswith('/')]
                after = {}
                for name in files:
                    with archive.open(name) as source: after[name[len(prefix):]] = stream_io.transfer(source)
                if before == after: retained.append(aid); continue
                if aid == SELF:
                    # A later rollback must restore a Controller that can retry
                    # Installer registration after an interrupted cold recovery.
                    controller = home/'addons/script.blacklanturn.preview'
                    required = 'Update to BlackLanturn Build 1.1.27 before updating the Installer with the build.'
                    if _tree(controller) is None or not (controller/'installer_recovery.py').is_file():
                        raise UpdateError(required)
                    current_controller = versions._meta((controller/'addon.xml').read_bytes(), 'script.blacklanturn.preview')
                    if versions.compare(current_controller.get('version'), '0.1.94') < 0:
                        raise UpdateError(required)
                for name in files:
                    with archive.open(name) as source: _write(work/'new'/aid/name[len(prefix):], source)
                if _tree(work/'new'/aid) != after: raise UpdateError('Staged add-on verification failed: '+aid)
                entries[aid] = {'before': before, 'after': after, 'started': False}
                if aid == SELF:
                    response = json.loads(kodi.executeJSONRPC(json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'Addons.GetAddonDetails', 'params': {'addonid': SELF, 'properties': ['enabled']}})))
                    enabled = response.get('result', {}).get('addon', {}).get('enabled')
                    if type(enabled) is not bool:
                        raise UpdateError('The Installer enabled state could not be checked. Nothing has been updated; restart Kodi and retry.')
                    entries[aid]['enabled_before'] = enabled
            _closure(home, chosen, kodi)
            completion = dict(schema=1, id=target['release_id'], edition=target['edition'], version=target['build_version'], revision=target.get('release_revision', 0), complete=True)
            incoming = {META[0]: target_raw, META[1]: archive.read('userdata/'+META[1]), META[2]: json.dumps(completion, sort_keys=True).encode()}
            metadata = {}
            for name, raw in incoming.items():
                dst = home/'userdata'/name; _plain(dst)
                metadata[name] = {'existed': dst.exists(), 'started': False}
                if dst.exists(): _write(work/'metadata-old'/name, dst.read_bytes())
                _write(work/'metadata-new'/name, raw)
            state = {'schema': 1, 'status': 'prepared', 'addons': entries, 'metadata': metadata}
            _journal(plan, state)
        plan.update(state=state, base_version=installed['build_version'], new_addons=[aid for aid,entry in entries.items() if entry['before'] is None], version=target['build_version'], retained=retained, chosen={aid:node.get('version') for aid,node in chosen.items()})
        return plan
    except Exception as exc:
        try:
            if Path(plan['work']).exists(): _recover_locked(plan)
        finally: release(plan)
        if isinstance(exc, UpdateError): raise
        raise UpdateError('Update preparation failed. Nothing was replaced: '+str(exc)) from exc
    finally:
        if expanded is not None:
            try: expanded.unlink()
            except OSError: pass

def apply(plan, registrar=None):
    home = Path(plan['home']); work = Path(plan['work']); state = plan['state']
    try:
        if registrar is not None:registrar.snapshot(plan)
        for aid, entry in state['addons'].items():
            if _tree(home/'addons'/aid) != entry['before']: raise UpdateError('An add-on changed while preparing the update. Please retry.')
        state['status'] = 'applying'; _journal(plan, state)
        # Replace our own tree last, after every other add-on has passed readback.
        for aid in sorted(state['addons'], key=lambda aid: (aid == SELF, aid)):
            entry = state['addons'][aid]
            if _tree(home/'addons'/aid) != entry['before']: raise UpdateError('An add-on changed during the update. Previous code will be restored.')
            target = home/'addons'/aid; entry['started'] = True; _journal(plan, state)
            if target.exists(): os.replace(target, work/'old'/aid); _sync(home/'addons'); _sync(work/'old')
            os.replace(work/'new'/aid, target); _sync(home/'addons')
            if _tree(target) != entry['after']: raise UpdateError('Updated source readback failed: '+aid)
        if registrar is not None:registrar.apply(plan,_journal)
        for name, entry in state['metadata'].items():
            entry['started'] = True; _journal(plan, state)
            _write(home/'userdata'/name, (work/'metadata-new'/name).read_bytes())
        _sync(home/'userdata')
        state['status'] = 'committed'; _journal(plan, state)
    except Exception as exc:
        try: _recover_locked(plan)
        except Exception as recovery:
            raise UpdateError('Update stopped. Keep recovery data and reopen Update BlackLanturn to recover: '+str(recovery)) from recovery
        raise UpdateError('Update stopped; previous code and release details were restored: '+str(exc)) from exc
    else:
        # Keep the writer lock until committed cleanup finishes: another updater
        # must never have its newly created staging removed by this writer.
        try: shutil.rmtree(work)
        except OSError: pass
        return {'version': plan['version'], 'updated': list(state['addons']), 'retained': plan['retained']}
    finally: release(plan)
