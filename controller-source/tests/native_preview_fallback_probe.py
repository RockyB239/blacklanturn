"""Native failure injection fixture; never used by the normal launcher."""
import sys
from pathlib import Path
import xbmcgui,xbmcvfs
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'addon'))
from live_review import LiveReview,event
expected=ROOT/'BlackLanturn-Test.app/Contents/Resources/Kodi/portable_data/userdata'
if Path(xbmcvfs.translatePath('special://profile')).resolve()!=expected.resolve():
    raise RuntimeError('Native fallback fixture requires the disposable test profile')
class FailureProbe(LiveReview):
    def play_preview_candidate(self,url):
        if url and not getattr(self,'injected',False):
            self.injected=True
            bad='plugin://plugin.video.youtube/play/?video_id=00000000000'
            self.preview_attempts.candidates.insert(1,url)
            self.preview_attempts.candidates[0]=bad
            url=bad
            event('native_fallback_failure_injected')
        super().play_preview_candidate(url)
dialog=FailureProbe('LiveReview.xml',str(ROOT/'addon'),'Default','1080i')
dialog.doModal()
del dialog
