"""Apple TV Kodi21.3 storage regression; writes only UUID-owned fake XML.

Stage beside native_storage.py and run using an idle-device recovery guard.
No real setting, authorization, viewing history or addon registry is changed.
"""
import hashlib
import json
import traceback
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from native_storage import listdir, read_xml, require

PROTECTED_XML = (
    'guisettings.xml',
    'addon_data/plugin.video.themoviedb.helper/settings.xml',
    'addon_data/plugin.video.umbrella/settings.xml',
)


def run(vfs, home):
    home = Path(home)
    userdata = home / 'userdata'
    before = {name: hashlib.sha256(read_xml(vfs, userdata / name)).hexdigest()
              for name in PROTECTED_XML}
    owned = userdata / ('BlackLanturn-cache-probe-' + uuid.uuid4().hex)
    require(owned.parent == userdata and not owned.exists(), 'Unsafe owned probe directory')
    owned.mkdir()
    path = owned / 'settings.xml'
    sentinel = b'<settings version="2"><setting id="probe">fake-account-value</setting></settings>'
    result = {'passed': False}
    try:
        stream = vfs.File(str(path), 'w')
        try:
            require(stream.write(sentinel.decode('utf-8')), 'Owned probe write failed')
        finally:
            stream.close()
        require(read_xml(vfs, path) == sentinel, 'Initial owned XML read failed')

        # The only deliberately unsafe listing is this freshly owned directory.
        # Never substitute any actual addon profile or the userdata root here.
        _, files = vfs.listdir(str(owned))
        stream = vfs.File(str(path))
        try:
            raw_after_legacy_listing = bytes(stream.readBytes())
        finally:
            stream.close()
        result['legacy_trigger_reproduced'] = (
            'settings.xml' not in files and vfs.exists(str(path))
            and raw_after_legacy_listing != sentinel)
        require(result['legacy_trigger_reproduced'], 'Expected21.3 cache trigger not reproduced')
        require(read_xml(vfs, path) == sentinel, 'Guarded read did not repair false cache miss')
        require(read_xml(vfs, path) == sentinel, 'Repeated guarded read changed XML')
        result['guarded_read_preserved_xml'] = True
    finally:
        # Restore the directory cache before deleting only the owned fake file.
        listdir(vfs, owned)
        if vfs.exists(str(path)):
            require(vfs.delete(str(path)), 'Owned native XML cleanup failed')
        if path.is_file():
            path.unlink()
        owned.rmdir()
    after = {name: hashlib.sha256(read_xml(vfs, userdata / name)).hexdigest()
             for name in PROTECTED_XML}
    require(before == after, 'Protected real XML changed during diagnostic')
    result.update(passed=True, real_settings_byte_unchanged=True,
                  protected_xml_count=len(before), owned_probe_removed=True)
    return result


if __name__ == '__main__':
    import xbmcvfs
    try:
        result = run(xbmcvfs, xbmcvfs.translatePath('special://home/'))
        result['stage'] = 'completed'
    except Exception:
        result = {'passed': False, 'stage': 'failed', 'error': traceback.format_exc()}
    (Path(__file__).parent / 'ui-result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
