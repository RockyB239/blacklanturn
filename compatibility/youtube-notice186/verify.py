"""Verify packaged warning behavior and data preservation through the shipped updater."""
import argparse
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import types
from unittest.mock import patch
import zipfile

import release


def guard_test(files, folder):
    p = folder / release.CLIENT.removeprefix(release.YOUTUBE)
    p.parent.mkdir(parents=True)
    p.write_bytes(files[release.CLIENT])
    guard = types.ModuleType('check')
    exec(compile(files[release.GUARD + 'check.py'], 'check.py', 'exec'), guard.__dict__)
    seen = []
    settings = {'kodion.video.quality.isa': True, 'kodion.mpd.videos': True}
    version = '1:7.4.4+blacklanturn.2'
    youtube = types.SimpleNamespace(getAddonInfo=lambda key: {'version': version, 'path': str(folder)}[key],
                                    getSettingBool=settings.__getitem__)
    mods = {
        'check': guard,
        'xbmc': types.SimpleNamespace(Monitor=lambda: types.SimpleNamespace(waitForAbort=lambda _: False),
                                      LOGINFO=1, log=lambda *_: None, getCondVisibility=lambda _: True),
        'xbmcaddon': types.SimpleNamespace(Addon=lambda _: youtube),
        'xbmcgui': types.SimpleNamespace(Dialog=lambda: types.SimpleNamespace(notification=lambda *args: seen.append(args)),
                                         NOTIFICATION_WARNING='warning'),
        'xbmcvfs': types.SimpleNamespace(translatePath=lambda path: path),
    }
    with patch.dict(sys.modules, mods):
        runtime = {}
        exec(compile(files[release.GUARD + 'runtime.py'], 'runtime.py', 'exec'), runtime)
        run = runtime['run']
        assert run(startup=True) == 'verified' and not seen
        settings['kodion.mpd.videos'] = False
        assert run(startup=True) == 'settings' and len(seen) == 1
        settings['kodion.mpd.videos'] = True
        p.write_bytes(p.read_bytes() + b'\n')
        assert run(startup=True) == 'replaced' and len(seen) == 2
        version = '7.5.0'
        assert run(startup=True) == 'review' and len(seen) == 3


def verify(args):
    artifacts, baselines = args.artifacts.resolve(), args.baselines.resolve()
    report_path = artifacts / 'candidate-packages.json'
    report = json.loads(report_path.read_bytes())
    assert report['versions'] == release.VERSIONS
    for label, (edition, _) in release.EDITIONS.items():
        row = report[label]
        old = release.previous.read_zip(baselines / f'BlackLanturn-{edition}-Kodi21-{release.BASE}.zip')
        new = release.previous.read_zip(artifacts / row['full']['file'])
        changed = {name for name in old.keys() | new.keys() if old.get(name) != new.get(name)}
        assert changed == release.expected_payload(label) | {release.MARKER, release.NOTICES}
        assert {n: b for n, b in new.items() if n.startswith(release.YOUTUBE)} == {
            n: b for n, b in old.items() if n.startswith(release.YOUTUBE)}
        if label == 'general':
            with tempfile.TemporaryDirectory() as directory:
                guard_test(new, Path(directory))
    matrix_script = release.ROOT / 'tools/verify_release165.py'
    matrix = args.output.with_name('install-matrix.json')
    flags = ['--artifacts', str(artifacts), '--baselines', str(baselines), '--output', str(matrix),
             '--baseline-version', release.BASE, '--installer-version', '1.0.54']
    # Load the existing matrix in this process so the direct upgrade uses the
    # exact same extracted installer and Kodi fixtures as the eight cases.
    with patch.object(sys, 'argv', [str(matrix_script), *flags]):
        fixtures = runpy.run_path(str(matrix_script), run_name='notice186_matrix')
    checked = json.loads(matrix.read_bytes())
    assert checked['passed'] and len(checked['checks']) == 8
    direct = []
    for label, (edition, pin) in release.previous.BASELINES.items():
        old = args.previous / f'BlackLanturn-{edition}-Kodi21-1.1.62.zip'
        assert release.prior.file_sha(old) == pin
        row = report[label]
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            with zipfile.ZipFile(old) as archive:
                archive.extractall(home)
            private = home / 'userdata/addon_data/plugin.video.youtube/access_manager.json'
            private.parent.mkdir(parents=True, exist_ok=True)
            private.write_bytes(b'synthetic authorization')
            def saved():
                skip = {'blacklanturn-build.json', 'blacklanturn-releases.json', 'blacklanturn-install-complete.json'}
                return {p.relative_to(home).as_posix(): release.prior.file_sha(p)
                        for p in (home / 'userdata').rglob('*') if p.is_file() and p.name not in skip}
            before = saved()
            update = fixtures['load']('inplace_update')
            update.apply(update.prepare(artifacts / row['full']['file'], home, fixtures['kodi'](label)))
            assert saved() == before
            marker = json.loads((home / release.MARKER).read_bytes())
            assert marker['build_version'] == release.VERSION
            with zipfile.ZipFile(artifacts / row['full']['file']) as archive:
                for name in release.expected_payload(label):
                    assert (home / name).read_bytes() == archive.read(name)
            direct.append(label + ' 1.1.62 direct in-place')
    result = {**checked, 'checks': checked['checks'] + direct, 'packaged_startup_cases': 4,
              'youtube_byte_identical_to_baseline': True}
    args.output.write_bytes(release.prior.encoded(result))
    print(json.dumps(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('artifacts', 'baselines', 'previous', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    verify(parser.parse_args())
