from pathlib import Path
from xml.etree import ElementTree as E
import unittest

class MouseArrowLayout(unittest.TestCase):
    def setUp(self):
        self.root=E.parse(Path(__file__).parents[1]/'addon/resources/skins/Default/1080i/LiveReview.xml').getroot()
        self.parents={child:parent for parent in self.root.iter() for child in parent}
    def bounds(self,node,compact):
        x=float(node.findtext('left','0'));y=float(node.findtext('top','0'))
        w=float(node.findtext('width','0'));h=float(node.findtext('height','0'))
        current=node
        while current is not None:
            if current is not node:
                x+=float(current.findtext('left','0'));y+=float(current.findtext('top','0'))
            for animation in current.findall('animation'):
                if compact and animation.get('effect')=='slide' and 'Window.Property(heroCompact)' in animation.get('condition',''):
                    dx,dy=map(float,animation.get('end','0,0').split(','));x+=dx;y+=dy
            current=self.parents.get(current)
        return x,y,w,h
    def test_up_arrow_hit_target_stays_just_above_first_row_and_clear_of_clock(self):
        arrow=self.root.find('.//control[@id="700"]');row=self.root.find('.//control[@id="900"]')
        for compact in (False,True):
            with self.subTest(compact=compact):
                x,y,w,h=self.bounds(arrow,compact);_,row_top,_,_=self.bounds(row,compact)
                self.assertGreaterEqual(row_top-(y+h),8)
                self.assertLessEqual(row_top-(y+h),80,'Up arrow drifted away from the rows')
                self.assertFalse(x<1880 and x+w>1540 and y<216 and y+h>34,'Up arrow overlaps date/time/weather')
    def test_visible_up_arrow_moves_with_its_click_target(self):
        arrow=self.root.find('.//control[@id="700"]')
        icon=next(n for n in self.root.iter('control') if n.findtext('texture')=='arrow-up.png')
        for compact in (False,True):
            with self.subTest(compact=compact):
                x,y,w,h=self.bounds(arrow,compact);ix,iy,iw,ih=self.bounds(icon,compact)
                self.assertGreaterEqual(ix,x);self.assertGreaterEqual(iy,y)
                self.assertLessEqual(ix+iw,x+w);self.assertLessEqual(iy+ih,y+h)
        self.assertIn('Window.Property(input),mouse',arrow.findtext('visible',''))

if __name__=='__main__':unittest.main()
