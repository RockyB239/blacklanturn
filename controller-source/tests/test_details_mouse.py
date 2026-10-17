"""Regression: details arrows must move visible lists, never hidden home rows."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest

# Execute the real controller method without requiring Kodi's embedded modules.
tree=ast.parse((Path(__file__).parents[1]/'addon/live_review.py').read_text())
cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='LiveReview')
method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='arrow')
namespace={'event':lambda *a,**k:None}
exec(compile(ast.Module(body=[method],type_ignores=[]),'live_review.py','exec'),namespace)

class ListControl:
    def __init__(self):self.position=0
    def getSelectedPosition(self):return self.position
    def selectItem(self,position):self.position=position

class DetailsMouse(unittest.TestCase):
    def review(self,mode='details'):
        controls={cid:ListControl() for cid in (900,901,3000,3100)}
        props={'scroll':'top'}
        updates=[]
        obj=SimpleNamespace(mode=mode,last_row=0,rows=[[{'label':'home A'},{'label':'home B'}],[]],cast_people=[{}, {}, {}],related=[{}, {}],getControl=controls.__getitem__,getProperty=lambda k:props.get(k,''),setProperty=props.__setitem__,update=updates.append)
        obj.arrow=namespace['arrow'].__get__(obj)
        return obj,controls,props,updates
    def test_similar_arrow_moves_similar_list_and_keeps_title(self):
        obj,controls,props,updates=self.review()
        obj.arrow(713)
        self.assertEqual(controls[3100].position,1)
        self.assertEqual(controls[900].position,0)
        self.assertEqual(updates,[])
    def test_cast_arrow_moves_portraits_without_opening_filmography(self):
        obj,controls,props,updates=self.review()
        obj.arrow(721)
        self.assertEqual(controls[3000].position,1)
        self.assertEqual(controls[900].position,0)
        self.assertEqual(updates,[])
    def test_page_down_reaches_similar_then_up_returns_through_cast(self):
        obj,controls,props,updates=self.review()
        obj.arrow(701);self.assertEqual(props['scroll'],'down')
        obj.arrow(701);self.assertEqual(props['scroll'],'related')
        obj.arrow(701);self.assertEqual(props['scroll'],'related')
        obj.arrow(700);self.assertEqual(props['scroll'],'down')
        obj.arrow(700);self.assertEqual(props['scroll'],'top')
    def test_empty_details_rows_do_not_select_negative_position(self):
        obj,controls,props,updates=self.review();obj.related=[];obj.cast_people=[]
        obj.arrow(712);obj.arrow(721)
        self.assertEqual(controls[3100].position,0)
        self.assertEqual(controls[3000].position,0)
        self.assertEqual(updates,[])
    def test_home_arrows_keep_existing_row_navigation(self):
        obj,controls,props,updates=self.review('home')
        obj.arrow(711)
        self.assertEqual(controls[900].position,1)
        self.assertEqual(updates,[{'label':'home B'}])
        obj.arrow(701);self.assertEqual(props['scroll'],'down')
        obj.arrow(700);self.assertEqual(props['scroll'],'top')

class DetailsHover(unittest.TestCase):
    def test_details_row_arrows_repeat_only_while_mouse_is_over_them(self):
        import sys
        sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
        from probe_core import HoverScroll
        for cid in (712,713,720,721):
            h=HoverScroll()
            self.assertIsNone(h.tick(0,cid,True))
            self.assertEqual(h.tick(.4,cid,True),cid)
            self.assertIsNone(h.tick(.5,0,True))
            self.assertIsNone(h.tick(.9,cid,False))
