"""Expose the actual-source Umbrella progress contract to the release test suite."""
import importlib.util
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / 'compatibility/umbrella-progress/tests/test_umbrella_progress.py'
SPEC = importlib.util.spec_from_file_location('umbrella_progress_contract', PATH)
CONTRACT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTRACT)


def load_tests(loader, tests, pattern):
    return loader.loadTestsFromModule(CONTRACT)
