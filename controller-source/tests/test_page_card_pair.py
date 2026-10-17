"""Paging uses matching native cards without changing provider routes or back anchors."""
import copy,sys,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
from browse_controls import page_cards
from live_core import PageHistory,card_artwork,is_browse_folder,episode_identity
from test_window_lifecycle import ROOT,extract
from search_ui import discovery_result

class PageCardPair(unittest.TestCase):
 def cards(self):
  origin='plugin://plugin.video.themoviedb.helper/?info=trending&tmdb_type=tv'
  provider={'label':'Next page','filetype':'directory','file':origin+'&page=3','art':{'landscape':'provider.png','fanart':'provider-hero.png'},'plot':'provider metadata'}
  history=PageHistory();history.push(origin,8)
  cards,pos=page_cards([{'label':'Title','file':'plugin://title'},provider],history,origin+'&page=2')
  return cards,pos,provider,history
 def test_both_directions_choose_packaged_native_card_icons_and_keep_provider_route(self):
  cards,pos,provider,_=self.cards()
  self.assertEqual(pos,1)
  for card,direction,label in ((cards[0],'previous','Previous'),(cards[-1],'next','Next')):
   with self.subTest(direction=direction):
    art=card_artwork(card)
    self.assertEqual(art['kind'],'paging')
    self.assertEqual(card['label'],label)
    image=Path(art['image']);self.assertTrue(image.is_file())
    self.assertEqual(image.parent,ROOT/'resources/media')
    self.assertNotEqual(art['image'],'provider.png')
    self.assertNotIn('fanart',card.get('art',{}))
  self.assertEqual(cards[-1]['file'],provider['file'])
 def test_normalization_does_not_mutate_provider_art(self):
  cards,_,provider,_=self.cards()
  self.assertEqual(provider['art'],{'landscape':'provider.png','fanart':'provider-hero.png'})
 def test_next_card_opens_paging_even_when_it_has_helpful_description(self):
  cards,_,_,_=self.cards();calls=[];next_card=dict(cards[-1],plot='Show more titles.')
  state=SimpleNamespace(actions_open=False,chosen=lambda cid:next_card,load_path=lambda *a,**kw:calls.append((a,kw)),details=lambda item:self.fail('Next must not open a details page'))
  click=extract(ROOT/'live_review.py','onClick',{'discovery_result':discovery_result,'is_browse_folder':is_browse_folder,'episode_identity':episode_identity},'LiveReview')
  click(state,900)
  self.assertEqual(calls,[((0,next_card['file'],next_card['label']),{})])
 def test_previous_uses_its_rows_exact_saved_anchor(self):
  cards,_,_,history=self.cards();calls=[]
  state=SimpleNamespace(actions_open=False,chosen=lambda cid:cards[0],histories=[history],load_path=lambda *a,**kw:calls.append((a,kw)))
  extract(ROOT/'live_review.py','onClick',{},'LiveReview')(state,900)
  self.assertEqual(calls,[((0,'plugin://plugin.video.themoviedb.helper/?info=trending&tmdb_type=tv'),{'back':True,'position':8})])
  self.assertEqual(history.pages,[])

if __name__=='__main__':unittest.main()
