import io,sys,unittest,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'tools'))
from verify_release import verify_playback_defaults
class LanguageDefaults(unittest.TestCase):
 def archive(self,audio='default',subtitle='forced_only'):
  data={'userdata/guisettings.xml':'<settings><setting id="locale.audiolanguage">'+audio+'</setting><setting id="locale.subtitlelanguage">'+subtitle+'</setting></settings>'}
  for aid,settings in {'plugin.video.umbrella':{'provider.external.enabled':'true','external_provider.module':'script.module.cocoscrapers','external_provider.name':'cocoscrapers'},'plugin.video.youtube':{'kodion.mpd.stream.select':'1','kodion.video.stream.select':'1'},'plugin.video.themoviedb.helper':{'trakt_watchedindicators':'true'}}.items():data['userdata/addon_data/'+aid+'/settings.xml']='<settings>'+''.join('<setting id="'+k+'">'+v+'</setting>' for k,v in settings.items())+'</settings>'
  buf=io.BytesIO()
  with zipfile.ZipFile(buf,'w') as z:
   for k,v in data.items():z.writestr(k,v)
  return zipfile.ZipFile(buf)
 def test_follows_interface_language_with_forced_only_subtitles(self):
  with self.archive() as z:verify_playback_defaults(z)
 def test_rejects_media_default_or_fixed_english_audio_for_clean_release(self):
  for audio in ['mediadefault','English']:
   with self.subTest(audio=audio),self.archive(audio=audio) as z:
    with self.assertRaisesRegex(AssertionError,'language'):verify_playback_defaults(z)
 def test_rejects_original_or_always_on_subtitles(self):
  for subtitle in ['original','default','English']:
   with self.subTest(subtitle=subtitle),self.archive(subtitle=subtitle) as z:
    with self.assertRaisesRegex(AssertionError,'subtitle'):verify_playback_defaults(z)
