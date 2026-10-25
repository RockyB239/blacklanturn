"""Returning from a build update cannot reopen a stale Installer Python session."""
import sys
import unittest
from unittest.mock import patch

import test_installer_preservation_ui as fixture


class UpdateHandoff(unittest.TestCase):
    def setUp(self):
        self.f = fixture.InstallerPreservationUI()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.context = patch.dict(sys.modules, self.f.modules)
        self.context.start()
        self.addCleanup(self.context.stop)

    def run_action(self, params):
        nav = self.f.load('gui/navigation.py')
        refreshes, dispatches, windows = [], [], []
        self.f.config.init_settings = lambda: refreshes.append('settings read')
        # The listing producer is isolated from network/catalog data. The real
        # modal, onClick, action dispatch loop and refresh decision still run.
        nav.rows_for = lambda route: [dict(label='Update', params=params, description='', folder=False, icon='', fanart='')]
        def click(screen):
            windows.append(screen)
            if len(windows) == 1: screen.onClick(screen.control)
        fixture.FakeWindow.callback = click
        nav.dispatch_action = lambda handle, route: dispatches.append(route)
        nav.run(1)
        return refreshes, dispatches, windows

    def test_update_and_legacy_normal_finish_session_without_reading_replaced_installer(self):
        for action in ('update', 'normal'):
            with self.subTest(action=action):
                params = {'mode':'install', 'action':action, 'name':'BlackLanturn Apple TV & Mac'}
                refreshes, dispatched, windows = self.run_action(params)
                self.assertEqual(dispatched, [params])
                self.assertEqual(len(windows), 1, 'An update reopened the outgoing Installer window')
                self.assertEqual(refreshes, ['settings read'], 'Outgoing config read disk after update handoff')

    def test_ordinary_action_still_refreshes_and_reopens_navigation(self):
        params = {'mode':'settings', 'name':'plugin.program.blacklanturninstaller'}
        refreshes, dispatched, windows = self.run_action(params)
        self.assertEqual(dispatched, [params])
        self.assertEqual(len(windows), 2)
        self.assertEqual(len(refreshes), 3)


if __name__ == '__main__': unittest.main()
