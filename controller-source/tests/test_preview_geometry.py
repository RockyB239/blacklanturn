import sys,unittest,importlib.util
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))

class PreviewGeometry(unittest.TestCase):
    def fit(self,stream,aspect='',compact=True):
        self.assertIsNotNone(importlib.util.find_spec('preview_geometry'),'Preview fit must use the hero rectangle')
        from preview_geometry import preview_fill_viewmode
        return preview_fill_viewmode(stream,aspect,compact)

    def test_16_9_trailer_covers_actual_hero_instead_of_tv_screen(self):
        mode=self.fit({'width':1280,'height':720},'1.78')
        self.assertAlmostEqual(mode['zoom'],(1530/689)/(1280/720))
        self.assertEqual(mode['pixelratio'],1.0)

    def test_scope_matches_both_hero_geometries(self):
        for compact,ratio in [(True,1530/689),(False,1800/810)]:
            for width,height in [(1280,720),(1920,800),(640,480)]:
                zoom=self.fit({'width':width,'height':height},compact=compact)['zoom']
                source=width/height
                # Fit-inside rectangle followed by this zoom must cover both axes.
                fitted_width=min(ratio,source)
                fitted_height=min(1,ratio/source)
                self.assertGreaterEqual(fitted_width*zoom+1e-9,ratio)
                self.assertGreaterEqual(fitted_height*zoom+1e-9,1)

    def test_non_square_pixels_use_reported_display_aspect(self):
        self.assertAlmostEqual(self.fit({'width':720,'height':576},'1.78')['zoom'],(1530/689)/1.78)

    def test_missing_stream_can_use_display_aspect(self):
        self.assertAlmostEqual(self.fit({},'2.40')['zoom'],2.4/(1530/689))

    def test_invalid_metadata_never_stops_preview_or_sends_nonfinite_zoom(self):
        for stream,aspect in [({},''),({'width':0,'height':0},'NaN'),({'width':'bad','height':720},'inf')]:
            self.assertEqual(self.fit(stream,aspect),'zoom')

if __name__=='__main__':unittest.main()
