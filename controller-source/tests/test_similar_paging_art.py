"""Normalized Similar pagination must render branded artwork in the Details row."""
import re,unittest
from pathlib import Path
from xml.etree import ElementTree as E
from test_window_lifecycle import ROOT
from browse_controls import page_card
from native_list_fixture import media_functions


def visible(node,parents,item,focus):
    while node is not None:
        condition=node.findtext('visible','')
        if condition:
            condition=re.sub(r'String.IsEqual\(ListItem.Property\((\w+)\),([^)]*)\)',lambda m:str(item.properties.get(m[1],'')==m[2]),condition)
            condition=re.sub(r'String.IsEqual\(Window.Property\((\w+)\),([^)]*)\)',lambda m:str(''==m[2]),condition)
            condition=re.sub(r'Control.HasFocus\((\d+)\)',lambda m:str(focus==int(m[1])),condition)
            expression=condition.replace('[','(').replace(']',')').replace('!',' not ').replace('+',' and ').replace('|',' or ')
            if not eval(expression.strip(),{'__builtins__':{}},{}):return False
        node=parents.get(node)
    return True


class SimilarPagingArt(unittest.TestCase):
    def layouts(self):
        root=E.parse(ROOT/'resources/skins/Default/1080i/LiveReview.xml').getroot()
        row=root.find('.//control[@id="3100"]')
        return [(tag,row.find(tag)) for tag in ('itemlayout','focusedlayout')]

    def test_real_paging_items_render_the_packaged_branded_art_in_both_details_layouts(self):
        render=media_functions()['media_item']
        for direction in ('previous','next'):
            item=render(page_card(direction,'plugin://provider/exact-page'))
            self.assertEqual(item.properties['cardArtKind'],'paging')
            self.assertEqual(item.properties['pageControl'],direction)
            self.assertEqual(item.path,'plugin://provider/exact-page')
            expected=str(ROOT/'resources/media'/('page-'+direction+'.png'))
            self.assertEqual(item.art['navigation'],expected);self.assertTrue(Path(expected).is_file())
            for name,layout in self.layouts():
                with self.subTest(direction=direction,layout=name):
                    parents={child:parent for parent in layout.iter() for child in parent}
                    images=[node for node in layout.iter('control') if node.get('type')=='image' and node.findtext('texture')=='$INFO[ListItem.Art(navigation)]' and visible(node,parents,item,3100)]
                    self.assertEqual(len(images),1,'The real paging item has no visible branded navigation art in Details')
                    image=images[0]
                    self.assertEqual(image.findtext('aspectratio'),'keep')
                    self.assertGreater(float(image.findtext('width')),0);self.assertGreater(float(image.findtext('height')),0)
                    labels=[node.findtext('label','') for node in layout.iter('control') if visible(node,parents,item,3100)]
                    self.assertIn('BlackLan[COLOR FF29D9EE]turn[/COLOR]',labels)
                    self.assertIn('Previous' if direction=='previous' else 'Next',labels)

    def test_real_paging_item_has_a_full_card_focus_frame_only_when_details_row_is_focused(self):
        item=media_functions()['media_item'](page_card('next','plugin://provider/page2'))
        layout=dict(self.layouts())['focusedlayout']
        parents={child:parent for parent in layout.iter() for child in parent}
        frames=[node for node in layout.iter('control') if node.findtext('texture')=='ring-large-rounded.png']
        active=[node for node in frames if visible(node,parents,item,3100)]
        self.assertEqual(len(active),1,'Selected Similar paging must have a visible focus frame')
        self.assertEqual((active[0].findtext('width'),active[0].findtext('height')),('470','264'))
        self.assertFalse(any(visible(node,parents,item,3000) for node in frames),'An unfocused Similar row must not retain its paging frame')

if __name__=='__main__':unittest.main()
