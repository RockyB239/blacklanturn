import sys,unittest,importlib.util,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))

def frame(top=0,bottom=0,dark=False,width=120,height=54):
    darkpixel=bytes((16,16,16,255));brightpixel=bytes((110,80,60,255))
    return b''.join((darkpixel if dark or y<top or y>=height-bottom else brightpixel)*width for y in range(height))

class PreviewBars(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('preview_bars'),'Persistent bars must be detected before reframing')
        import preview_bars
        return preview_bars

    def test_embedded_balanced_borders_are_measured_from_pixels(self):
        m=self.module()
        self.assertEqual(m.top_border_fraction(frame(3,3),120,54),3/54)
        self.assertEqual(m.top_border_fraction(frame(),120,54),0)

    def test_dark_scenes_invalid_captures_and_one_sided_shadows_are_ignored(self):
        m=self.module()
        for pixels in (frame(dark=True),b'',frame(4,0),frame(20,20)):
            self.assertIsNone(m.top_border_fraction(pixels,120,54))

    def test_shift_removes_only_measured_top_padding_without_stretch_or_extra_zoom(self):
        m=self.module();fit={'zoom':1.25,'pixelratio':1.0,'verticalshift':0.0,'nonlinearstretch':False}
        adjusted=m.top_aligned_viewmode(fit,0.04,16/9,True)
        self.assertAlmostEqual(adjusted['verticalshift'],-1.0355555555555556)
        self.assertEqual(adjusted['zoom'],1.25);self.assertEqual(adjusted['pixelratio'],1.0)
        self.assertEqual(fit['verticalshift'],0)
        self.assertEqual(m.top_aligned_viewmode(fit,0,16/9,True),fit)

    def test_flipped_android_texture_uses_opposite_crop_direction(self):
        m=self.module();fit={'zoom':1.25,'pixelratio':1.0,'verticalshift':0.0,'nonlinearstretch':False}
        self.assertAlmostEqual(m.top_aligned_viewmode(fit,0.04,16/9,True,flipped=True)['verticalshift'],1.0355555555555556)

    def test_scan_requires_several_consistent_frames_and_releases_capture(self):
        m=self.module();calls=[]
        class Capture:
            def capture(self,w,h):calls.append((w,h));self.w=w;self.h=h
            def getImage(self,ms):return frame(3,3,width=self.w,height=self.h)
        scan=m.PreviewBarScan(Capture,True,0)
        for now in (0.7,1.1,1.5):
            scan.tick(now);self.assertFalse(scan.done)
        scan.tick(1.9)
        self.assertTrue(scan.done);self.assertIsNone(scan.capture)
        self.assertEqual(scan.result,3/108);self.assertEqual(calls,[(240,108)])

    def test_uncertain_frames_stop_after_bounded_work(self):
        m=self.module()
        class Capture:
            def capture(self,w,h):self.w=w;self.h=h
            def getImage(self,ms):return frame(dark=True,width=self.w,height=self.h)
        scan=m.PreviewBarScan(Capture,True,0)
        for i in range(35):scan.tick(1+i*0.4)
        self.assertTrue(scan.done);self.assertIsNone(scan.result);self.assertIsNone(scan.capture)

    def test_buffered_start_does_not_exhaust_scan_before_frames_arrive(self):
        m=self.module()
        class Capture:
            def capture(self,w,h):self.w=w;self.h=h;self.calls=0
            def getImage(self,ms):
                self.calls+=1
                return b'' if self.calls<=16 else frame(4,4,width=self.w,height=self.h)
        scan=m.PreviewBarScan(Capture,True,0)
        for i in range(20):scan.tick(1+i*.4)
        self.assertTrue(scan.done)
        self.assertEqual(scan.result,4/108)
        self.assertIsNone(scan.capture)

    def test_cancelled_scan_cannot_change_next_title(self):
        m=self.module();scan=m.PreviewBarScan(lambda:self.fail('Cancelled scan must not capture'),True,0)
        scan.close();scan.tick(4)
        self.assertTrue(scan.done);self.assertIsNone(scan.result)

    def test_trailer_cache_survives_restart_and_keeps_framing_geometries_separate(self):
        m=self.module()
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'cache.json';cache=m.PreviewFramingCache(path)
            cache.put('youtube:ABC:compact',0.03);cache.put('youtube:DEF:compact',0)
            again=m.PreviewFramingCache(path)
            self.assertEqual(again.get('youtube:ABC:compact'),0.03)
            self.assertEqual(again.get('youtube:DEF:compact'),0)
            self.assertIsNone(again.get('youtube:ABC:details'))

if __name__=='__main__':unittest.main()
