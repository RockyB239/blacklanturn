"""Checks filtering and wheel routing; catches missing axes and hidden-item focus."""
import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
class ReviewNavigation(unittest.TestCase):
    def test_genre_filters_change_the_visible_catalogue(self):
        from probe_core import catalogue_indices
        items=[{'id':'a','type':'Movie','genre':'Mystery'},{'id':'b','type':'TV','genre':'Crime'},{'id':'c','type':'Movie','genre':'Romance'},{'id':'d','type':'TV','genre':'Drama'}]
        self.assertEqual(catalogue_indices(items,'Movies','Mystery'),[0])
        self.assertEqual(catalogue_indices(items,'Shows','All'),[1,3])
        self.assertEqual(catalogue_indices(items,'Shows','Comedy'),[])
        self.assertEqual(catalogue_indices(items,'My Stuff','All',{'c'}),[2])
    def test_mouse_wheel_moves_along_rows_without_focusing_hidden_cards(self):
        from probe_core import wheel_route
        rows=[[1004,1005,1007,1009],[2000,2001,2002,2003]]
        self.assertEqual(wheel_route(1005,1,rows),('focus',1007))
        self.assertEqual(wheel_route(1007,-1,rows),('focus',1005))
        self.assertEqual(wheel_route(1009,1,rows),('focus',1009))
        self.assertEqual(wheel_route(2002,-1,rows),('focus',2001))
    def test_mouse_wheel_outside_rows_moves_the_page(self):
        from probe_core import wheel_route
        self.assertEqual(wheel_route(0,1,[[1000,1001]]),('vertical','down'))
        self.assertEqual(wheel_route(101,-1,[[1000,1001]]),('vertical','top'))
    def test_mouse_wheel_in_sidebar_moves_between_menu_entries(self):
        from probe_core import wheel_route
        self.assertEqual(wheel_route(12,1,[[1000,1001]]),('focus',13))
        self.assertEqual(wheel_route(10,-1,[[1000,1001]]),('focus',10))
if __name__=='__main__': unittest.main()

class HoverNavigation(unittest.TestCase):
    def test_hover_scroll_waits_then_repeats_and_stops_on_leave(self):
        from probe_core import HoverScroll
        h=HoverScroll()
        self.assertIsNone(h.tick(0,711,True))
        self.assertEqual(h.tick(.4,711,True),711)
        self.assertIsNone(h.tick(.5,711,True))
        self.assertEqual(h.tick(.8,711,True),711)
        self.assertIsNone(h.tick(.9,0,True))
        self.assertIsNone(h.tick(1,711,True))
        self.assertIsNone(h.tick(1.5,711,False))
    def test_hover_does_not_activate_an_ordinary_card(self):
        from probe_core import HoverScroll
        h=HoverScroll()
        self.assertIsNone(h.tick(0,1001,True))
        self.assertIsNone(h.tick(10,1001,True))
