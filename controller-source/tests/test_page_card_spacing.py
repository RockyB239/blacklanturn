"""Paging art shares title-card spacing and uses opposing directional layouts."""
from pathlib import Path
from xml.etree import ElementTree as E
import re,unittest
ROOT=Path(__file__).parents[1]/'addon/resources/skins/Default/1080i/LiveReview.xml'

def number(c,key):return float(c.findtext(key,'0'))
def visible(c,parents,direction):
 while c is not None:
  value=c.findtext('visible','')
  if value:
   value=re.sub(r'String.IsEqual\(ListItem.Property\(cardArtKind\),(\w+)\)',lambda m:str(m[1]=='paging'),value)
   value=re.sub(r'String.IsEqual\(ListItem.Property\(pageControl\),(\w+)\)',lambda m:str(m[1]==direction),value)
   if not eval(value.replace('+',' and ').replace('|',' or ').replace('!',' not ').replace('[','(').replace(']',')').strip(),{'__builtins__':{}},{}):return False
  c=parents.get(c)
 return True

class PageCardSpacing(unittest.TestCase):
 def layouts(self):
  r=E.parse(ROOT).getroot()
  for cid in (900,901):
   for l in r.find(f'.//control[@id="{cid}"]'):
    if l.tag in ('itemlayout','focusedlayout') and l.get('width')!='292':yield cid,l
 def test_navigation_and_title_art_have_the_same_inter_card_gap(self):
  for cid,l in self.layouts():
   if l.tag!='itemlayout':continue
   with self.subTest(row=cid,layout=l.get('condition')):
    g=next(c for c in l.findall('control') if c.findtext('visible')=='String.IsEqual(ListItem.Property(cardArtKind),paging)')
    bg=next(c for c in g.findall('control') if c.findtext('texture')=='action-rounded-rest.png')
    art=next(c for c in l.findall('control') if c.findtext('texture')=='$INFO[ListItem.Art(landscape)]')
    slot=float(l.get('width'))
    gap=lambda c:slot-number(c,'left')-number(c,'width')+number(art,'left')
    self.assertEqual(gap(bg),gap(art),'Navigation card is narrower than the slot and leaves extra empty space')
 def test_next_reverses_image_text_and_chevron_columns(self):
  for cid,l in self.layouts():
   with self.subTest(row=cid,layout=l.tag,condition=l.get('condition')):
    g=next(c for c in l.findall('control') if c.findtext('visible')=='String.IsEqual(ListItem.Property(cardArtKind),paging)')
    parents={child:parent for parent in g.iter() for child in parent}
    controls=list(g.iter('control'))
    def icon(direction):return next(c for c in controls if c.findtext('texture')=='$INFO[ListItem.Art(navigation)]' and visible(c,parents,direction))
    prev,next_=icon('previous'),icon('next')
    pl=next(c for c in controls if c.findtext('label')=='Previous');nl=next(c for c in controls if c.findtext('label')==('$INFO[ListItem.Label]' if l.get('condition')=='String.IsEqual(Window.Property(youtubeBrowser),true)' else 'Next'))
    pa=next(c for c in controls if c.findtext('texture')=='arrow-left.png');na=next(c for c in controls if c.findtext('texture')=='arrow-right.png')
    self.assertLessEqual(number(pl,'left')+number(pl,'width'),number(prev,'left'))
    self.assertLessEqual(number(next_,'left')+number(next_,'width'),number(nl,'left'),'Next lantern must be left of its label')
    self.assertLessEqual(number(pa,'left')+number(pa,'width'),number(pl,'left'))
    self.assertGreaterEqual(number(na,'left'),number(nl,'left')+number(nl,'width'),'Next chevron must follow its label')

if __name__=='__main__':unittest.main()
