"""Specific interest rows reject broad-category drift without replacing the feed."""
import copy,unittest
import youtube_relevance as relevance,youtube_home as home
from test_youtube_relevance import ident,entry,video,metadata

def raw(title,category='27',topics=()):
 data=metadata(1,category,topics);data['snippet']['title']=title;return data

class Subjects(unittest.TestCase):
 def test_specific_rows_are_recognized_but_mixed_discovery_rows_are_not_topical(self):
  cases={'Science and more':'science','History and more':'history','Ancient History and more':'ancient_history','Consumer Electronics and more':'electronics','Philosophy':'philosophy','Psychology and more':'psychology','Cooking':'food','Travel and more':'travel','Pets and Animals':'animals','Nature and more':'nature','Mysteries and more':'mysteries','Mobile games':'gaming','Action RPGs':'gaming','Cars':'vehicles','Fitness':'fitness','Beauty':'beauty','Business and Finance':'business','News and politics':'news','Comedy':'comedy','Movies and TV':'screen'}
  for label,want in cases.items():
   with self.subTest(label=label):self.assertEqual(relevance.family(label),want)
  for label in ['Recommended','Recently uploaded','New to you','Continue watching','Recommended podcasts','Podcasts and more','Recommended shows','Science fiction movies','The history of music']:
   with self.subTest(label=label):self.assertIsNone(relevance.family(label))
 def test_science_does_not_treat_all_knowledge_or_technology_as_science(self):
  for title in ['How quantum physics explains black holes','What happens inside a living cell?','An experiment in chemistry']:
   with self.subTest(title=title):self.assertTrue(relevance.matches(raw(title,'28',['Knowledge']),'science'))
  for title in ['A philosopher explains happiness','Election polling explained','The best smartphone of the year','The best science fiction movies']:
   with self.subTest(title=title):self.assertFalse(relevance.matches(raw(title,'28',['Knowledge']),'science'))
 def test_history_and_ancient_history_are_not_interchangeable_with_education(self):
  self.assertTrue(relevance.matches(raw('The fall of the Roman Empire'),'history'))
  self.assertTrue(relevance.matches(raw('How ancient Egypt built its pyramids'),'ancient_history'))
  self.assertFalse(relevance.matches(raw('What caused the Cold War?'),'ancient_history'))
  for title in ['How to solve a quadratic equation','Five habits for a happy life']:
   with self.subTest(title=title):self.assertFalse(relevance.matches(raw(title),'history'))
  self.assertFalse(relevance.matches(raw('Roman Empire campaign walkthrough','20',['Video_game_culture']),'history'))
 def test_electronics_requires_hardware_evidence_instead_of_science_category(self):
  self.assertTrue(relevance.matches(raw('iPhone 18 Pro teardown','28',['Technology']),'electronics'))
  self.assertTrue(relevance.matches(raw('Which laptop GPU should you buy?','28'),'electronics'))
  self.assertFalse(relevance.matches(raw('What is dark matter?','28',['Knowledge']),'electronics'))
  self.assertFalse(relevance.matches(raw('How democracy works','28',['Technology']),'electronics'))
  self.assertTrue(relevance.matches(raw('iOS 27 settings you need to turn off','28',['Technology']),'electronics'))
  self.assertTrue(relevance.matches(raw('Apple Maps vs Google Maps on CarPlay','28',['Technology']),'electronics'))
 def test_ambiguous_names_and_entertainment_titles_are_not_historical_or_financial_evidence(self):
  for title,cat,topics,wanted in [('Roman Reigns returns to WWE Raw','17',['Sport'],'ancient_history'),('Egypt travel guide: best beaches and resorts','19',['Tourism'],'ancient_history'),('Ice Age official movie trailer','24',['Film'],'history'),('Ancient trees in an untouched forest','22',['Nature'],'ancient_history'),('Stock car race highlights','17',['Sport'],'business'),('Samsung Galaxy S26 Ultra review','28',['Technology'],'science'),('Autodesk Maya beginner tutorial','28',['Technology'],'ancient_history'),('Murder investigation: new evidence uncovered','25',['Society'],'business')]:
   with self.subTest(title=title):self.assertFalse(relevance.matches(raw(title,cat,topics),wanted))
  self.assertTrue(relevance.matches(raw('Stonehenge was reanalyzed by archaeologists'),'history'))
  self.assertTrue(relevance.matches(raw('What Göbekli Tepe tells us about ancient people'),'ancient_history'))
 def test_playlist_directories_require_subject_evidence_without_losing_the_native_url_or_art(self):
  good={'id':'VLscience','file':'plugin://plugin.video.youtube/playlist/science/','filetype':'directory','title':'Space exploration','label':'Space exploration','art':{'thumb':'original.jpg'}}
  bad=dict(good,id='VLpolitics',file='plugin://plugin.video.youtube/playlist/politics/',title='Daily politics',label='Daily politics')
  rows=home.local_rows([{'label':'Science and more','items':[bad,good],'youtube_cursor':{'continuation':'native'}}],{},{} )
  self.assertEqual(rows[0]['local_items'],[good]);self.assertEqual(rows[0]['youtube_cursor']['continuation'],'native')
 def test_other_direct_topics_and_subject_evidence_keep_cross_category_relevant_choices(self):
  for want,title,cat,topics in [('philosophy','What did Socrates mean?', '27',['Knowledge']),('psychology','Why cognitive biases change decisions','27',['Knowledge']),('food','How to cook a simple pasta recipe','24',[]),('travel','A guide to visiting Japan','22',['Tourism']),('animals','How a rescue dog learns to trust','22',['Pet']),('vehicles','A restored classic car','22',['Vehicle']),('fitness','A beginner strength workout','26',['Physical_fitness']),('beauty','A makeup tutorial','26',['Physical_attractiveness']),('business','How inflation affects investing','27',[]),('news','Election coverage','25',[]),('comedy','A stand-up set','24',['Humour']),('screen','A new film trailer','24',['Film'])]:
   with self.subTest(want=want):self.assertTrue(relevance.matches(raw(title,cat,topics),want))
 def test_knowledge_metadata_and_creator_identity_do_not_override_unrelated_video_title(self):
  data=raw('Why you should vote for this candidate','27',['Knowledge']);data['snippet']['channelTitle']='Science and History Channel';data['snippet']['description']='We cover physics, history and ancient Egypt.'
  for want in ['science','history','ancient_history','philosophy','psychology','electronics']:
   with self.subTest(want=want):self.assertFalse(relevance.matches(data,want))
 def test_public_title_survives_taxonomy_cache_projection_but_private_or_unneeded_fields_do_not(self):
  data=raw('Ancient Rome and its aqueducts');data['snippet'].update(description='Do not retain',channelTitle='Do not infer affinity',customSecret='not public classification');before=copy.deepcopy(data)
  projected=relevance.taxonomy(data)
  self.assertTrue(relevance.matches(projected,'history'));self.assertEqual(data,before)
  self.assertNotIn('description',projected['snippet']);self.assertNotIn('channelTitle',projected['snippet']);self.assertNotIn('customSecret',projected['snippet'])
 def test_initial_subject_filter_preserves_personalized_order_cards_and_confirmed_seeds(self):
  items={ident(n):video(n) for n in [1,2,3]};groups=[{'label':'Science and more','items':[entry(n) for n in [3,2,1]],'youtube_cursor':{'continuation':'native'}}]
  facts={ident(1):raw('How quantum physics works'),ident(2):raw('The benefits of stoic philosophy'),ident(3):raw('What is a black hole?')};before=copy.deepcopy(items)
  rows=home.local_rows(groups,items,facts)
  self.assertEqual(rows[0]['local_items'],[video(3),video(1)]);self.assertEqual(rows[0]['youtube_fallback']['related_seeds'],[ident(3),ident(1)]);self.assertEqual(rows[0]['youtube_cursor']['relevance_family'],'science');self.assertEqual(items,before)

if __name__=='__main__':unittest.main()
