import sys
from pathlib import Path
import threading
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
from streaming_lookahead import StreamingLookahead

ROW='plugin://plugin.video.themoviedb.helper/?info=discover&tmdb_type=tv&with_watch_providers=8&watch_region=US&with_id=true&nextpage=true&widget=false'
OTHER=ROW.replace('providers=8','providers=9')

class StreamingLookahead179(unittest.TestCase):
    def test_dwell_starts_one_full_request_and_select_hands_off_same_inflight_request(self):
        now=[0.];started=threading.Event();release=threading.Event();calls=[]
        data=[dict(file='title',art={'poster':'full'},resume={'position':13},playcount=1)]
        def fetch(path):
            calls.append(path);started.set();release.wait(2);return data
        request=StreamingLookahead(fetch,clock=lambda:now[0])
        try:
            request.observe(ROW);now[0]=.2;request.observe(ROW)
            self.assertFalse(started.is_set())
            now[0]=.5;request.observe(ROW)
            self.assertTrue(started.wait(1))
            request.observe(OTHER);now[0]=1.;request.observe(OTHER)
            request.close();result=[]
            consumer=threading.Thread(target=lambda:result.append(request.take(ROW,lambda:True)))
            consumer.start();self.assertTrue(consumer.is_alive())
            release.set();consumer.join(1)
            self.assertEqual(calls,[ROW]);self.assertEqual(result,[data])
            self.assertIsNone(request.take(ROW,lambda:True))
        finally:release.set();request.done.wait(1)

    def test_brief_focus_moves_do_no_work_and_non_service_routes_are_rejected(self):
        now=[0.];calls=[]
        request=StreamingLookahead(lambda path:calls.append(path),clock=lambda:now[0])
        request.observe(ROW);now[0]=.1;request.observe(OTHER)
        now[0]=.2;request.observe('');now[0]=2.;request.observe('')
        for path in ('plugin://plugin.video.youtube/?info=discover',ROW+'&page=2',ROW+'&with_genres=18'):
            request.observe(path);now[0]+=1;request.observe(path)
        self.assertEqual(calls,[])
        request.close()

    def test_long_picker_dwell_cannot_extend_120_second_freshness(self):
        now=[0.];request=StreamingLookahead(lambda path:['full'],clock=lambda:now[0])
        request.observe(ROW);now[0]=1.;request.observe(ROW)
        self.assertTrue(request.done.wait(1));now[0]=121.
        self.assertIsNone(request.take(ROW,lambda:True))

    def test_fresh_completion_is_reusable_and_cancelled_owner_cannot_consume(self):
        for current,expected in ((lambda:True,['full']),(lambda:False,None)):
            now=[0.];request=StreamingLookahead(lambda path:['full'],clock=lambda:now[0])
            request.observe(ROW);now[0]=1.;request.observe(ROW)
            self.assertTrue(request.done.wait(1));now[0]=120.
            self.assertEqual(request.take(ROW,current),expected)

    def test_fresh_cache_or_ineligible_owner_does_not_trigger_provider(self):
        now=[0.];calls=[]
        request=StreamingLookahead(lambda path:calls.append(path),cached=lambda path:True,clock=lambda:now[0])
        request.observe(ROW);now[0]=1.;request.observe(ROW)
        self.assertTrue(request.done.wait(1));self.assertEqual(calls,[])
        self.assertIsNone(request.take(ROW,lambda:True))

if __name__=='__main__':unittest.main(verbosity=2)
