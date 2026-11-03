import threading
import unittest

from genre_lookahead import GenreLookahead


class GenreLookaheadTests(unittest.TestCase):
    def test_dwell_only_fetches_one_page_and_reuses_exact_selection(self):
        now = [0.]
        started = threading.Event()
        release = threading.Event()

        def fetch(path):
            started.set()
            release.wait(2)
            return [path]

        lookahead = GenreLookahead({'action': 'a', 'comedy': 'b'}, fetch,
                                   clock=lambda: now[0])
        try:
            lookahead.observe('action')
            self.assertFalse(started.is_set())
            now[0] = 0.5
            lookahead.observe('action')
            self.assertTrue(started.wait(1))
            lookahead.observe('comedy')
            now[0] = 1.
            lookahead.observe('comedy')
            self.assertIsNone(lookahead.take('b', lambda: True))
            release.set()
            self.assertEqual(lookahead.take('a', lambda: True), ['a'])
            self.assertIsNone(lookahead.take('a', lambda: True))
        finally:
            release.set()

    def test_already_saved_or_cancelled_work_is_not_used(self):
        now = [0.]
        lookahead = GenreLookahead({'action': 'a'}, self.fail,
                                   cached=lambda path: True, clock=lambda: now[0])
        lookahead.observe('action')
        now[0] = 1.
        lookahead.observe('action')
        lookahead.close()
        self.assertIsNone(lookahead.take('a', lambda: True))

    def test_selected_request_can_be_abandoned_while_provider_remains_busy(self):
        now = [0.]
        started = threading.Event()
        release = threading.Event()
        waiting = threading.Event()
        stop = threading.Event()
        result = []

        def fetch(path):
            started.set()
            release.wait(2)
            return ['obsolete']

        def current():
            waiting.set()
            return not stop.is_set()

        lookahead = GenreLookahead({'action': 'a'}, fetch, clock=lambda: now[0])
        lookahead.observe('action')
        now[0] = 1.
        lookahead.observe('action')
        try:
            self.assertTrue(started.wait(1))
            consumer = threading.Thread(target=lambda: result.append(lookahead.take('a', current)))
            consumer.start()
            self.assertTrue(waiting.wait(1))
            stop.set()
            consumer.join(.5)
            self.assertEqual(result, [None])
        finally:
            release.set()
            self.assertTrue(lookahead.done.wait(1))
