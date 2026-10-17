import copy
import importlib.util
from pathlib import Path
import unittest


class Acceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).with_name('native_paging.py')
        if path.exists():
            spec = importlib.util.spec_from_file_location('native_paging', path)
            cls.probe = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.probe)
        else:
            cls.probe = None

    def helper(self, name):
        self.assertIsNotNone(self.probe, 'Native paging acceptance helpers are not implemented')
        return getattr(self.probe, name)

    def cards(self):
        return [
            {'path': 'plugin://title/1', 'kind': '', 'source': {'art': {'poster': 'p'}, 'playcount': 1, 'resume': {'position': 12, 'total': 100}}, 'native': {'label': 'One', 'watchState': 'progress'}},
            {'path': 'plugin://page/2', 'kind': 'next', 'source': {}, 'native': {'label': 'Next page'}},
        ]

    def test_changed_art_or_resume_cannot_pass_previous_restoration(self):
        compare = self.helper('metadata_equality')
        original = self.cards()
        for field, value in [('art', {'poster': 'different'}), ('resume', {'position': 0, 'total': 100}), ('playcount', 0)]:
            changed = copy.deepcopy(original)
            changed[0]['source'][field] = value
            self.assertFalse(compare(original, changed)['equal'])
        self.assertTrue(compare(original, copy.deepcopy(original))['equal'])

    def test_missing_values_duplicate_paths_and_native_changes_are_not_equal(self):
        compare = self.helper('metadata_equality')
        original = self.cards()
        changed = copy.deepcopy(original)
        del changed[0]['source']['playcount']
        self.assertFalse(compare(original, changed)['equal'])
        changed = copy.deepcopy(original)
        changed[0]['native']['watchState'] = 'unwatched'
        self.assertFalse(compare(original, changed)['equal'])
        self.assertFalse(compare(original, original + [original[0]])['equal'])

    def test_prepared_event_requires_target_generation_revision_and_new_time(self):
        match = self.helper('matching_prepared_event')
        key = (7, 2, 'plugin://page/2')
        exact = {'event': 'next_page_prepared', 'time': 10, 'target': 'plugin://page/2', 'generation': 7, 'revision': 2}
        self.assertEqual(match([exact], key, 9), exact)
        for field, value in [('target', 'plugin://page/3'), ('generation', 8), ('revision', 3), ('time', 8)]:
            wrong = dict(exact, **{field: value})
            self.assertIsNone(match([wrong], key, 9))
        self.assertIsNone(match([{'event': 'next_page_prepared', 'time': 10}], key, 9))

    def test_wrong_window_error_empty_and_unrendered_cards_are_not_ready(self):
        ready = self.helper('row_ready')
        value = {'window': 13001, 'expected_window': 13001, 'heading': 'SHOWS', 'state': 'ready', 'notice': '', 'loading': False, 'cards': self.cards(), 'native_count': 2}
        self.assertTrue(ready(value, 'SHOWS'))
        for field, wrong in [('window', 10000), ('state', 'error'), ('state', 'empty'), ('loading', True), ('native_count', 1), ('cards', [])]:
            self.assertFalse(ready(dict(value, **{field: wrong}), 'SHOWS'))
        missing = copy.deepcopy(value)
        missing['cards'][0]['native']['label'] = ''
        self.assertFalse(ready(missing, 'SHOWS'))

    def test_synthetic_previous_identity_does_not_require_a_provider_path(self):
        self.assertTrue(hasattr(self.probe, 'card_transport_matches'), 'Synthetic Previous must use its action identity')
        match = self.helper('card_transport_matches')
        previous = {'file': 'blacklanturn://previous-page', '_page_control': 'previous', 'label': 'Previous'}
        self.assertTrue(match(previous, '', 'previous', 'Previous'))
        self.assertTrue(match(previous, 'blacklanturn://previous-page/', 'previous', 'Previous'))
        self.assertFalse(match(previous, '', 'next', 'Previous'))
        self.assertFalse(match(previous, '', 'previous', 'Wrong card'))
        self.assertFalse(match({'file': 'plugin://title/1'}, 'plugin://title/2', '', 'Title'))
        self.assertFalse(match({'file': 'plugin://page/2', '_page_control': 'next'}, 'plugin://page/3', 'next', 'Next'))

    def test_previous_destination_is_history_route_and_next_remains_exact(self):
        self.assertTrue(hasattr(self.probe, 'page_destination'), 'Previous must resolve the existing history route')
        destination = self.helper('page_destination')
        self.assertEqual(destination('previous', 'blacklanturn://previous-page', [('plugin://page/1', 20)]), 'plugin://page/1')
        self.assertEqual(destination('next', 'plugin://page/2', []), 'plugin://page/2')
        with self.assertRaises(ValueError):
            destination('previous', 'blacklanturn://previous-page', [])

    def test_labels_use_gui_rpc_instead_of_native_pointer_reads(self):
        import json
        from types import SimpleNamespace,MethodType
        calls=[]
        def execute(text):
            request=json.loads(text);calls.append(request);return json.dumps({'result':{'Container(900).ListItem.Art(poster)':'original-art'}})
        state=SimpleNamespace(xbmc=SimpleNamespace(executeJSONRPC=execute,getInfoLabel=lambda _:self.fail('Unsafe direct native getter')))
        self.assertTrue(hasattr(self.probe.PagingProbe,'read_labels'),'Batch labels must use the GUI dispatcher')
        state.read_labels=MethodType(self.probe.PagingProbe.read_labels,state)
        self.assertEqual(self.probe.PagingProbe.info(state,'Container(900).ListItem.Art(poster)'),'original-art')
        self.assertEqual(calls[0]['method'],'XBMC.GetInfoLabels')
        self.assertEqual(calls[0]['params']['labels'],['Container(900).ListItem.Art(poster)'])

    def test_only_verified_owned_cancellation_interval_excludes_expected_abort(self):
        self.assertTrue(hasattr(self.probe,'runtime_failures'),'Expected cancelled work must be distinguished from failed pages')
        f=self.probe.runtime_failures
        aborted={'event':'page_error','error_type':'PageCancelled','time':11}
        ordinary={'event':'page_error','error_type':'TimeoutError','time':11}
        early=dict(aborted,time=8);late=dict(aborted,time=15)
        owned={'status':'passed','first_back_epoch':10,'finished_epoch':12}
        self.assertEqual(f([early,aborted,ordinary,late],owned),[early,ordinary,late])
        self.assertEqual(f([aborted],dict(owned,status='observed')),[aborted])
        self.assertEqual(f([aborted],{}),[aborted])

    def test_sidebar_accounts_for_deep_page_history(self):
        from types import SimpleNamespace
        import time
        state=SimpleNamespace(view=SimpleNamespace(histories=[SimpleNamespace(pages=list(range(20)))]),
            deadline=time.monotonic()+30,work_deadline=time.monotonic()+30,
            guard=lambda:None,monitor=SimpleNamespace(waitForAbort=lambda _:None))
        actions=[]
        state.focus=lambda:50 if len(actions)>20 else 900
        state.action=lambda name:actions.append(name)
        self.probe.PagingProbe.sidebar(state)
        self.assertGreater(len(actions),20)
        self.assertLessEqual(len(actions),32)

    def test_timeout_retains_expected_actual_routes_rejection_and_events(self):
        from types import SimpleNamespace
        state = SimpleNamespace(R={'stage': 'next/back cycle 1'},
            wait_context={'heading': 'SHOWS', 'path': 'plugin://page/2'},
            last_rejection={'reason': 'native/model card identity mismatch', 'index': 0},
            last_snapshot=None, events=[{'event': 'page_loaded', 'back': False}],
            cheap_snapshot=lambda: {'path': 'plugin://page/1', 'state': 'ready'},
            read_events=lambda: None, save=lambda: None)
        self.probe.PagingProbe.capture_timeout(state, 24, False)
        diagnostic = state.R['timeouts'][0]
        self.assertEqual(diagnostic['expected']['path'], 'plugin://page/2')
        self.assertEqual(diagnostic['ui']['path'], 'plugin://page/1')
        self.assertEqual(diagnostic['raw_snapshot_rejection']['index'], 0)
        self.assertEqual(diagnostic['events_tail'], [{'event': 'page_loaded', 'back': False}])


if __name__ == '__main__':
    unittest.main()
