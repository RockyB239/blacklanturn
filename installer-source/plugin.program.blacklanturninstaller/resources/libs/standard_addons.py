"""Conservative Standard-install retention of newer portable ordinary add-ons.

This checks declared Kodi/dependency compatibility, not arbitrary upstream runtime
correctness. Managed variants and native components always use their own gates.
Kept code trees remain whole in place; user-data preservation is unchanged.
"""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import xml.etree.ElementTree as E
import zipfile

MANAGED = frozenset(('plugin.video.themoviedb.helper', 'plugin.video.umbrella',
                     'script.module.jurialmunkey', 'plugin.video.youtube'))
NATIVE = frozenset(('inputstream.adaptive', 'script.module.pil'))
RUNTIME = frozenset(('plugin.program.blacklanturninstaller',))
OWN_REPO = 'repository.blacklanturn'
POINTS = frozenset(('xbmc.python.module', 'xbmc.python.script', 'xbmc.python.pluginsource',
                    'xbmc.service', 'kodi.resource.language'))

class ProtectionError(ValueError):
    pass

def _fail(message):
    raise ProtectionError(message + ' No cleanup has run; your current build has been kept.')

def _version(raw):
    if not isinstance(raw, str) or not re.fullmatch(r'(?:[0-9]+:)?[A-Za-z0-9.+_@~]+(?:-[A-Za-z0-9.+_@~]+)?', raw):
        _fail('An ordinary add-on version is invalid.')
    epoch, value = raw.split(':', 1) if ':' in raw else ('0', raw)
    upstream, revision = value.split('-', 1) if '-' in value else (value, '')
    return min(int(epoch), 2**63-1), upstream.lower(), revision.lower()

def _component(a, b):
    # Direct port of Kodi Omega CAddonVersion::CompareComponent (GPL-2.0+).
    while a and b:
        while a and b and not a[0].isdigit() and not b[0].isdigit():
            if a[0] != b[0]:
                return -1 if a[0] == '~' else 1 if b[0] == '~' else (-1 if a[0] < b[0] else 1)
            a, b = a[1:], b[1:]
        if a and b and (not a[0].isdigit() or not b[0].isdigit()):
            return -1 if a[0] == '~' else 1 if b[0] == '~' else (-1 if a[0].isdigit() else 1)
        ma, mb = re.match(r'[0-9]*', a)[0], re.match(r'[0-9]*', b)[0]
        na, nb = min(int(ma or '0'), 2**63-1), min(int(mb or '0'), 2**63-1)
        if na != nb: return -1 if na < nb else 1
        a, b = a[len(ma):], b[len(mb):]
    if not a and not b: return 0
    return (-1 if a[0] == '~' else 1) if a else (1 if b[0] == '~' else -1)

def compare(a, b):
    ea, ua, ra = _version(a); eb, ub, rb = _version(b)
    return (-1 if ea < eb else 1) if ea != eb else (_component(ua, ub) or _component(ra, rb))

def _meta(raw, aid):
    try:
        node = E.fromstring(raw)
        if node.tag != 'addon' or node.get('id') != aid:
            _fail('Ordinary add-on identity differs: ' + aid)
        _version(node.get('version'))
        return node
    except E.ParseError:
        _fail('Ordinary add-on metadata is malformed: ' + aid)

def _portable(node):
    points = {e.get('point') for e in node.findall('extension')} - {'xbmc.addon.metadata', 'kodi.addon.metadata'}
    return (points == {'xbmc.addon.repository'} if node.get('id') == OWN_REPO
            else bool(points) and points <= POINTS)

def _validate(node, files, aid):
    if not _portable(node): _fail('Newer ordinary add-on has unsupported extension types: ' + aid)
    platform = [e.text.strip() if e.text else '' for e in node.findall('./extension/platform')]
    if platform and platform != ['all']: _fail('Newer ordinary add-on is not portable: ' + aid)
    if any(n.lower().endswith(('.so', '.dylib', '.dll', '.pyd')) or (n.endswith('/addon.xml')) for n in files):
        _fail('Ordinary add-on contains native or nested add-on files: ' + aid)
    if aid == OWN_REPO:
        directories = node.findall('./extension[@point="xbmc.addon.repository"]/dir')
        if platform != ['all'] or not directories or any(
                not (directory.findtext(field) or '').strip().startswith('https://')
                for directory in directories for field in ('info', 'checksum', 'datadir')):
            _fail('The BlackLanturn repository metadata is incomplete or incompatible.')
        for asset in node.findall('./extension/assets/*'):
            if asset.text and asset.text not in files:
                _fail('The BlackLanturn repository asset tree is incomplete.')
        return
    python = False
    for dep in node.findall('./requires/import'):
        if dep.get('addon') == 'xbmc.python':
            python = True
            if compare(dep.get('version', '0'), '3.0.0') < 0 or compare(dep.get('version', '0'), '3.0.1') > 0:
                _fail('Newer ordinary add-on requires a different Python API: ' + aid)
    for ext in node.findall('extension'):
        point = ext.get('point')
        if point in POINTS and point != 'kodi.resource.language':
            if not python: _fail('Ordinary Python add-on has no Python 3 requirement: ' + aid)
            library = ext.get('library', '')
            path = PurePosixPath(library)
            if not library or path.is_absolute() or any(p in ('', '.', '..') for p in library.split('/')) or '\\' in library:
                _fail('Ordinary add-on entrypoint is invalid: ' + aid)
            if point == 'xbmc.python.module':
                if library not in files and not any(n.startswith(library + '/') and n.endswith('.py') for n in files):
                    _fail('Ordinary add-on module tree is incomplete: ' + aid)
            elif library not in files:
                _fail('Ordinary add-on entrypoint is missing: ' + aid)

def _tree(root):
    if root.is_symlink() or not root.is_dir(): _fail('Ordinary add-on tree is missing or linked: ' + root.name)
    files = {}; aliases = {}
    for parent, dirs, names in os.walk(root, followlinks=False):
        for name in dirs + names:
            path = Path(parent)/name
            relative = path.relative_to(root).as_posix()
            key = relative.casefold()
            if path.is_symlink() or (not path.is_dir() and not path.is_file()) or (key in aliases and aliases[key] != relative):
                _fail('Ordinary add-on tree has ambiguous or linked files: ' + root.name)
            aliases[key] = relative
        for name in names:
            path = Path(parent)/name
            files[path.relative_to(root).as_posix()] = path.read_bytes()
    return files

def _digest(files):
    digest = hashlib.sha256()
    for name, raw in sorted(files.items()):
        digest.update(name.encode()); digest.update(b'\0'); digest.update(hashlib.sha256(raw).digest())
    return digest.hexdigest()

def keep_state_file(relative, plan):
    """Standard keeps Kodi databases and exact account-scoped YouTube history."""
    if not plan or not plan.get('state'): return False
    parts = PurePosixPath(relative).parts
    if len(parts) >= 3 and parts[:2] == ('userdata', 'Database'): return True
    return (len(parts) == 5 and parts[:3] == ('userdata', 'addon_data', 'plugin.video.youtube')
            and re.fullmatch(r'[A-Za-z0-9_-]+', parts[3]) is not None
            and re.fullmatch(r'(history|bookmarks)\.sqlite(?:-wal|-shm|-journal)?', parts[4]) is not None)

def keep_state_directory(relative, plan):
    if not plan or not plan.get('state'): return False
    parts = PurePosixPath(relative).parts
    return ((len(parts) >= 2 and parts[:2] == ('userdata', 'Database'))
            or parts == ('userdata', 'addon_data', 'plugin.video.youtube')
            or (len(parts) == 4 and parts[:3] == ('userdata', 'addon_data', 'plugin.video.youtube')
                and re.fullmatch(r'[A-Za-z0-9_-]+', parts[3]) is not None))

def verify(home, plan):
    """Recheck every retained byte before any destructive cleanup begins."""
    if not plan: return
    try:
        for aid, digest in plan['preserve'].items():
            if aid in MANAGED | NATIVE | RUNTIME | set(plan.get('excluded', ())) or _digest(_tree(Path(home)/'addons'/aid)) != digest:
                _fail('Ordinary add-on changed after preparation: ' + aid)
    except (OSError, KeyError, TypeError) as exc:
        _fail('Ordinary add-on preparation could not be verified: ' + str(exc))

def prepare(archive_path, home, kodi=None, auth_only=False, kept=(), excluded=()):
    """Decide the complete final trees and validate retained dependency closure."""
    protected = RUNTIME | frozenset(aid for aid in excluded if (Path(home)/'addons'/aid).is_dir())
    result = {'preserve': {}, 'replace': set(), 'state': not auth_only, 'excluded': protected}
    try:
        with zipfile.ZipFile(archive_path) as archive:
            bundled = {}
            for name in archive.namelist():
                parts = name.split('/')
                if len(parts) == 3 and parts[0] == 'addons' and parts[2] == 'addon.xml' and (not auth_only or parts[1] == OWN_REPO):
                    bundled[parts[1]] = _meta(archive.read(name), parts[1])
            if OWN_REPO in bundled:
                prefix = 'addons/' + OWN_REPO + '/'
                files = {n[len(prefix):]: archive.read(n) for n in archive.namelist() if n.startswith(prefix) and not n.endswith('/')}
                _validate(bundled[OWN_REPO], files, OWN_REPO)
                # This one build-managed repository must upgrade despite the
                # historical wipe exclude. Other excluded code stays protected.
                protected = protected - {OWN_REPO}
                result['excluded'] = protected
                result['replace'].add(OWN_REPO)
            if auth_only:
                return result
            chosen = dict(bundled)
            queue = []
            addons = Path(home)/'addons'
            if addons.is_symlink(): _fail('The ordinary add-on root is linked.')
            aliases = {}
            for path in addons.iterdir() if addons.is_dir() else ():
                key = path.name.casefold()
                if key in aliases and aliases[key] != path.name:
                    _fail('Ordinary add-on directory identity is ambiguous: ' + path.name)
                aliases[key] = path.name
            def retain(aid):
                if aid in MANAGED | NATIVE | protected: _fail('Ordinary retention cannot override managed/native/runtime policy: ' + aid)
                if aliases.get(aid.casefold(), aid) != aid: _fail('Ordinary add-on directory identity is ambiguous: ' + aid)
                files = _tree(addons/aid)
                node = _meta(files.get('addon.xml', b''), aid)
                _validate(node, files, aid)
                result['preserve'][aid] = _digest(files)
                chosen[aid] = node
                queue.append(aid)
            for aid, node in bundled.items():
                if aid in MANAGED | NATIVE | protected: continue
                if not _portable(node): continue
                result['replace'].add(aid)
                if (addons/aid).is_symlink(): _fail('Ordinary add-on tree is linked: ' + aid)
                if (addons/aid).exists():
                    installed = _meta((addons/aid/'addon.xml').read_bytes(), aid)
                    if compare(installed.get('version'), node.get('version')) > 0 or aid in kept:
                        retain(aid)
            checked = set()
            while queue:
                aid = queue.pop()
                if aid in checked: continue
                checked.add(aid)
                for dep in chosen[aid].findall('./requires/import'):
                    if dep.get('optional') == 'true': continue
                    dependency, minimum = dep.get('addon'), dep.get('version', '0')
                    if not dependency or not re.fullmatch(r'[a-z0-9_.-]+', dependency): _fail('Ordinary dependency identity is invalid: ' + aid)
                    _version(minimum)
                    if dependency in protected:
                        # These code trees survive wipe and are excluded from
                        # extraction. Bundled self metadata is not the final version.
                        root = addons/dependency
                        path = root/'addon.xml'
                        if root.is_symlink() or path.is_symlink(): _fail('Protected runtime metadata is linked: ' + dependency)
                        actual = _meta(path.read_bytes(), dependency)
                        available = actual.get('version')
                    elif dependency == 'xbmc.python': available = '3.0.1'
                    elif dependency in chosen:
                        available = chosen[dependency].get('version')
                        if dependency not in MANAGED | NATIVE and dependency not in checked:
                            if dependency not in result['preserve']:
                                prefix = 'addons/' + dependency + '/'
                                files = {n[len(prefix):]: archive.read(n) for n in archive.namelist() if n.startswith(prefix) and not n.endswith('/')}
                                _validate(chosen[dependency], files, dependency)
                            queue.append(dependency)
                    elif dependency not in NATIVE and (addons/dependency).is_dir():
                        retain(dependency); available = chosen[dependency].get('version')
                    else:
                        available = None
                        if kodi is not None and (dependency.startswith(('xbmc.', 'kodi.')) or dependency in NATIVE):
                            response = json.loads(kodi.executeJSONRPC(json.dumps({'jsonrpc':'2.0','id':1,'method':'Addons.GetAddonDetails','params':{'addonid':dependency,'properties':['enabled','version']}})))
                            details = response.get('result', {}).get('addon', {})
                            if details.get('enabled'): available = details.get('version')
                    if available is None or compare(available, minimum) < 0:
                        _fail('Newer ordinary add-on requires an unavailable dependency: ' + aid + ' -> ' + dependency)
            verify(home, result)
            return result
    except ProtectionError: raise
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as exc:
        _fail('Ordinary add-on preparation failed: ' + str(exc))
