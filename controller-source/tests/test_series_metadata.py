import unittest,sys,types,tempfile
from pathlib import Path
from unittest.mock import patch
import series_metadata
class Metadata(unittest.TestCase):
 def test_direct_client_request_is_bounded_and_never_launches_kodi_provider(self):
  calls=[]
  class API:
   req_api_url='https://api.themoviedb.org/3';req_language='en-US'
   def get_request_url(self,*a,**k):calls.append((a,k));return 'https://api.themoviedb.org/3/tv/1'
  class Response:
   def __enter__(self):return self
   def __exit__(self,*a):pass
   def read(self,size):calls.append(('limit',size));return b'{"id":1}'
  mods={'xbmcaddon':types.SimpleNamespace(Addon=lambda _:types.SimpleNamespace(getAddonInfo=lambda _:'/existing/helper')),'tmdbhelper.lib.api.tmdb.api':types.SimpleNamespace(TMDbAPI=API)}
  with patch.dict(sys.modules,mods),patch.object(series_metadata,'urlopen',lambda request,timeout:(calls.append(('timeout',timeout)) or Response())):
   self.assertEqual(series_metadata.load_show_package('1'),{'id':1})
  self.assertEqual(calls,[(('tv','1'),{'append_to_response':'recommendations,similar','language':'en-US'}),('timeout',4),('limit',1048577)])
