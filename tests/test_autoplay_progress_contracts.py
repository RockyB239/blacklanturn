"""Apply the retained duration/zero/Stop contracts to the exact new release player.

Historical fixtures remain untouched; the same contract suite runs separately
against the newly packaged player implementation in every release check.
"""
import importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def load_tests(loader, standard_tests, pattern):
    spec=importlib.util.spec_from_file_location('autoplay_current_progress',ROOT/'tests/test_umbrella_duration_fallback.py')
    current=importlib.util.module_from_spec(spec);spec.loader.exec_module(current)
    path=ROOT/'compatibility/addons134/patched/plugin.video.umbrella/resources/lib/modules/player.py'
    current.source=lambda version:path.read_bytes()
    current.ZERO.source=current.source
    return loader.suiteClass((loader.loadTestsFromModule(current),loader.loadTestsFromModule(current.ZERO)))
