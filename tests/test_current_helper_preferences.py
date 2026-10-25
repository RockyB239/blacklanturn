"""Current Helper consolidates playback sync into watched-source selection."""
from test_build_preferences import BuildPreferences

class CurrentHelperPreferences(BuildPreferences):
 def test_standard_retains_historical_playback_choice_without_writing_obsolete_clean_default(self):
  name='addon_data/plugin.video.themoviedb.helper/settings.xml'
  self.assertNotIn('sync_source_playback',self.m.DEFAULTS[name])
  self.put(name,{'sync_source_watched':'MDbList','sync_source_playback':'Trakt'})
  accounts=self.m.prepare(self.home,self.accounts(),['plugin.video.themoviedb.helper'],False)
  self.put(name,{'sync_source_watched':'Trakt'})
  self.m.restore(self.home,accounts,['plugin.video.themoviedb.helper'])
  self.assertEqual(self.get(name)['sync_source_watched'],'MDbList')
  self.assertEqual(self.get(name).get('sync_source_playback'),'Trakt')
