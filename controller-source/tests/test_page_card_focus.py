"""The selected navigation card must be visibly distinguishable from its peers."""
from pathlib import Path
from xml.etree import ElementTree as E
import re,unittest
ROOT=Path(__file__).parents[1]/'addon'

def visible(condition,kind,focus):
    condition=re.sub(r'String.IsEqual\(ListItem.Property\(cardArtKind\),(\w+)\)',lambda m:str(kind==m[1]),condition)
    condition=re.sub(r'Control.HasFocus\((\d+)\)',lambda m:str(focus==int(m[1])),condition)
    return eval(condition.replace('[','(').replace(']',')').replace('!',' not ').replace('+',' and ').replace('|',' or ').strip(),{'__builtins__':{}},{}) if condition else True

class PageCardFocus(unittest.TestCase):
    def test_previous_text_fallback_has_a_focus_frame_in_both_row_layouts(self):
        root=E.parse(ROOT/'resources/skins/Default/1080i/LiveReview.xml').getroot()
        for cid in (900,901):
            row=root.find(f'.//control[@id="{cid}"]')
            for layout in row.findall('focusedlayout'):
                if layout.get('width')=='292':continue
                with self.subTest(row=cid,layout=layout.get('condition')):
                    frames=[c for c in layout.findall('.//control') if c.findtext('texture')=='ring-large-rounded.png']
                    active=[c for c in frames if visible(c.findtext('visible',''),'paging',cid)]
                    self.assertTrue(active,'Previous page has no visible selection frame')
                    self.assertTrue(all((c.findtext('width'),c.findtext('height'))==('470','264') for c in active),'Navigation focus border must fill the ordinary card footprint')
                    self.assertFalse(any(visible(c.findtext('visible',''),'paging',50) for c in frames),'Inactive rows must not show a selected page frame')

if __name__=='__main__':unittest.main()
