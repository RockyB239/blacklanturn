"""Same-title fallback skips failures, stops after success and cancels stale work."""
import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
import live_core

class PreviewFallback(unittest.TestCase):
    def test_deduplicates_youtube_ids_and_ignores_unrelated_sources(self):
        fn=getattr(live_core,'preview_candidates',None)
        self.assertIsNotNone(fn)
        first='plugin://plugin.video.youtube/play/?video_id=AAAAAAAAAAA'
        rows=[{'file':first+'&x=1'},{'file':'plugin://plugin.video.youtube/play/?video_id=BBBBBBBBBBB'}, {'file':'plugin://plugin.video.umbrella/?action=play'}]
        self.assertEqual(fn(first,rows),[first,rows[1]['file']])
    def test_english_dub_precedes_subtitled_primary_and_preserves_foreign_fallback(self):
        url=lambda key:'plugin://plugin.video.youtube/play/?video_id='+key
        primary=url('SUBTITLE123')
        rows=[{'file':url('GERMAN12345'),'label':'Official trailer','language':'de'}, {'file':url('ENGLISHDUB1'),'label':'English dubbed trailer','language':'en'}, {'file':primary,'label':'Teaser [Subtitled]','language':'en'}]
        self.assertEqual(live_core.preview_candidates(primary,rows),[url('ENGLISHDUB1'),primary,url('GERMAN12345')])
    def test_known_english_video_can_displace_unknown_primary(self):
        primary='plugin://plugin.video.youtube/play/?video_id=PRIMARY1234'
        english='plugin://plugin.video.youtube/play/?video_id=ENGLISH1234'
        self.assertEqual(live_core.preview_candidates(primary,[{'file':english,'language':'eng','label':'Trailer'}]),[english,primary])
    def test_opening_credits_are_not_preferred_to_an_available_trailer(self):
        primary='plugin://plugin.video.youtube/play/?video_id=SUBTITLE123'
        intro='plugin://plugin.video.youtube/play/?video_id=INTRO123456'
        metadata={'SUBTITLE123':{'language':'en','name':'Teaser [Subtitled]','type':'Trailer'},'INTRO123456':{'language':'en','name':'Opening credits','type':'Opening Credits'}}
        self.assertEqual(live_core.preview_candidates(primary,[{'file':intro}],metadata=metadata),[primary,intro])
    def test_failure_moves_to_next_then_success_stops_retries(self):
        cls=getattr(live_core,'PreviewAttempts',None);self.assertIsNotNone(cls)
        q=cls(['first','second'])
        self.assertEqual(q.start(0),'first')
        self.assertEqual(q.tick(1,playing=False,error=True),'second')
        self.assertIsNone(q.tick(2,playing=True))
        self.assertIsNone(q.tick(20,playing=False))
        self.assertTrue(q.finished)
    def test_timeout_and_exhaustion_do_not_loop(self):
        cls=getattr(live_core,'PreviewAttempts',None);self.assertIsNotNone(cls)
        q=cls(['first','second'],timeout=12)
        self.assertEqual(q.start(0),'first')
        self.assertIsNone(q.tick(11,playing=False))
        self.assertEqual(q.tick(12,playing=False),'second')
        self.assertIsNone(q.tick(24,playing=False));self.assertTrue(q.finished)
        self.assertIsNone(q.tick(40,playing=False,error=True))
    def test_cancellation_prevents_late_retry(self):
        cls=getattr(live_core,'PreviewAttempts',None);self.assertIsNotNone(cls)
        q=cls(['first','second']);q.start(0);q.cancel()
        self.assertIsNone(q.tick(20,playing=False,error=True));self.assertTrue(q.finished)
    def test_brief_start_then_playback_error_still_falls_back(self):
        cls=getattr(live_core,'PreviewAttempts',None);self.assertIsNotNone(cls)
        q=cls(['first','second']);q.start(0);q.tick(1,playing=True)
        self.assertEqual(q.tick(2,playing=False,error=True),'second')

    def test_monitor_cannot_start_an_unpublished_request(self):
        q=live_core.PreviewAttempts(['first','second'])
        self.assertIsNone(q.tick(500,playing=False))
        self.assertEqual(q.index,-1)
