import sys,unittest,importlib.util
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
class PlaybackInfo(unittest.TestCase):
 def fields(self,current,target=None,details=None):
  self.assertIsNotNone(importlib.util.find_spec('playback_info'),'Playback Info needs a title-safe metadata handoff')
  from playback_info import playback_info_fields
  return playback_info_fields(current,target or {},details or {})
 def test_episode_credits_include_guests_and_roles(self):
  current={'type':'episode','showtitle':'Example','season':1,'episode':2,'title':'Chapter Two','plot':'Short synopsis'}
  details={**current,'plot':'Full episode synopsis','cast':[{'name':'Regular','role':'Detective'}],'guest_stars':[{'name':'Guest','character':'Witness'}]}
  got=self.fields(current,details=details)
  self.assertEqual(got['castLabel'],'Episode cast')
  self.assertEqual(got['cast'],'Regular — Detective\nGuest — Witness')
  self.assertEqual(got['plot'],'Full episode synopsis')
 def test_series_fallback_is_labelled_and_does_not_replace_episode_synopsis(self):
  got=self.fields({'type':'episode','showtitle':'Example','season':1,'episode':2,'title':'Chapter Two','plot':'Episode synopsis'},
    {'title':'Example','filetype':'directory','cast':[{'name':'Regular','role':'Detective'}],'plot':'Series synopsis'})
  self.assertEqual(got['castLabel'],'Series cast')
  self.assertEqual(got['plot'],'Episode synopsis')
 def test_next_episode_never_inherits_previous_episode_guest_or_plot(self):
  prior={'type':'episode','showtitle':'Example','season':1,'episode':2,'title':'Two','plot':'Prior','cast':[{'name':'Prior guest'}]}
  got=self.fields({**prior,'episode':3,'title':'Three','plot':'Next','cast':[]},prior,prior)
  self.assertEqual(got['cast'],'')
  self.assertEqual(got['plot'],'Next')
 def test_another_movie_or_show_never_inherits_metadata(self):
  got=self.fields({'type':'movie','title':'Different','year':2025},{'title':'Original','year':2025,'cast':[{'name':'Wrong'}]})
  self.assertEqual(got['cast'],'')
 def test_provider_cast_is_available_without_a_detail_lookup(self):
  got=self.fields({'type':'episode','showtitle':'Example','season':1,'episode':2,'title':'Two','cast':[{'name':'Regular','role':'Detective'}]})
  self.assertEqual(got['cast'],'Regular — Detective')
  self.assertEqual(got['castLabel'],'Cast')
 def test_portrait_slots_are_bounded_deduplicated_and_clear_on_next_episode(self):
  current={'type':'episode','showtitle':'Example','season':1,'episode':2,'title':'Two'}
  people=[{'name':'Actor '+str(i),'role':'Role '+str(i),'thumbnail':'https://example.org/'+str(i)+'.jpg'} for i in range(8)]
  details={**current,'cast':people+[people[0]],'guest_stars':[{'name':'Guest','character':'Visitor','profile_path':'/guest.jpg'}]}
  got=self.fields(current,details=details)
  self.assertIn('cast1.name',got,'Compact Info needs portrait slots')
  self.assertEqual(got['cast1.name'],'Actor 0')
  self.assertEqual(got['cast1.thumb'],'https://example.org/0.jpg')
  self.assertEqual(got['cast6.name'],'Actor 5')
  self.assertNotIn('cast7.name',got)
  empty=self.fields({**current,'episode':3,'title':'Three'},details=details)
  for i in range(1,7):
   self.assertEqual(empty['cast'+str(i)+'.name'],'')
   self.assertEqual(empty['cast'+str(i)+'.thumb'],'')
 def test_missing_portrait_keeps_name_and_tmdb_portrait_is_resolved(self):
  got=self.fields({'title':'Movie','year':2026,'cast':[{'name':'One','profile_path':'/face.jpg'},{'name':'Two'}]})
  self.assertIn('cast1.thumb',got,'Cast thumbnails are not handed to the skin')
  self.assertEqual(got['cast1.thumb'],'https://image.tmdb.org/t/p/w185/face.jpg')
  self.assertEqual(got['cast2.name'],'Two')
  self.assertEqual(got['cast2.thumb'],'')
 def test_person_link_is_matched_by_name_only_for_the_current_title(self):
  current={'type':'episode','showtitle':'Example','season':1,'episode':2,'title':'Two'}
  details={**current,'cast':[{'name':'Actor','role':'Detective'}],'people':[{'title':'Actor','plot':'Person biography','file':'plugin://plugin.video.themoviedb.helper/?info=details&type=person&tmdb_id=123'}]}
  got=self.fields(current,details=details)
  self.assertIn('cast1.id',got,'Cast needs a validated person identity for selectable details')
  self.assertEqual(got['cast1.id'],'123')
  self.assertEqual(got.get('cast1.bio'),'Person biography')
  wrong=self.fields({**current,'episode':3,'title':'Three'},details=details)
  self.assertEqual(wrong['cast1.id'],'')
if __name__=='__main__':unittest.main()
