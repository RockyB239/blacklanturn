"""Hero metadata retains a full episode date with separate watch-state space."""
import sys
import unittest
from pathlib import Path
from xml.etree import ElementTree as E

ROOT = Path(__file__).parents[1] / 'addon'
sys.path.insert(0, str(ROOT))
from live_core import title_presentation


class HeroMetadataFit(unittest.TestCase):
    def test_episode_runtime_rating_date_and_watch_state_have_separate_space(self):
        item = {
            'type': 'episode', 'filetype': 'file', 'season': 1, 'episode': 2,
            'premiered': '2026-10-21', 'runtime': 2400, 'mpaa': 'TV-MA',
            'file': 'plugin://plugin.video.themoviedb.helper/?info=play&tmdb_type=tv&tmdb_id=1&season=1&episode=2',
            'resume': {'position': 480, 'total': 2400},
        }
        info = title_presentation(item)
        self.assertEqual(info['technical'], '40 min  ·  TV-MA  ·  Aired Oct 21, 2026')
        self.assertEqual(info['watch'], 'In progress · 20%')
        tree = E.parse(ROOT / 'resources/skins/Default/1080i/LiveReview.xml')
        pairs = []
        for group in tree.iter('control'):
            technical = [c for c in group.findall('control') if c.findtext('label') == '$INFO[Window.Property(technicalMeta)]']
            if not technical:
                continue
            watch = next(c for c in group.findall('control') if c.findtext('label') == '$INFO[Window.Property(watchMeta)]')
            pairs.append((technical[0], watch))
        self.assertEqual(len(pairs), 2, 'Both full and compact heroes need date/watch space')
        for technical, watch in pairs:
            with self.subTest(top=technical.findtext('top')):
                # The audit identified clipping at 370/400px. A 530px regression
                # budget leaves room for this date plus longer month/day text.
                self.assertGreaterEqual(int(technical.findtext('width')), 530)
                technical_end = int(technical.findtext('left')) + int(technical.findtext('width'))
                self.assertGreaterEqual(int(watch.findtext('left')) - technical_end, 20)
                self.assertGreaterEqual(int(watch.findtext('width')), 450)
                self.assertEqual(technical.findtext('top'), watch.findtext('top'))
                self.assertLessEqual(int(watch.findtext('left')) + int(watch.findtext('width')), 1440)


if __name__ == '__main__':
    unittest.main()
