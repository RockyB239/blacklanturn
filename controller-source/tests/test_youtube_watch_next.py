"""The end-screen adapter authenticates only its own Watch Next read."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
import youtube_provider as provider

class Client:
 logged_in=True
 def __init__(self,authorized=True):self.calls=[];self.authorized=authorized
 def get_related_videos(self,video_id,retry=0):
  return self.api_request('tv' if retry else 'v1','POST',path='next',do_auth=False,post_data={'videoId':video_id})
 def api_request(self,client,method,**kwargs):
  self.calls.append((client,kwargs))
  if kwargs['do_auth'] and not self.authorized:return {}
  return {'items':[{'kind':'youtube#video','id':'bbbbbbbbbbb'}]}

class WatchNext(unittest.TestCase):
 def loader(self):
  f=getattr(provider,'watch_next',None);self.assertTrue(callable(f),'Missing signed-in Watch Next adapter');return f
 def test_uses_existing_signed_in_tv_client_and_labels_actual_source(self):
  c=Client();raw,source=self.loader()(c,'aaaaaaaaaaa',lambda:True)
  self.assertEqual(source,'account');self.assertEqual(raw['items'][0]['id'],'bbbbbbbbbbb')
  self.assertEqual(len(c.calls),1);self.assertEqual(c.calls[0][0],'tv');self.assertTrue(c.calls[0][1]['do_auth']);self.assertFalse(c.calls[0][1]['cache'])
 def test_signed_in_failure_falls_back_to_related_without_stalling(self):
  c=Client(False);raw,source=self.loader()(c,'aaaaaaaaaaa',lambda:True)
  self.assertEqual(source,'related');self.assertEqual(raw['items'][0]['id'],'bbbbbbbbbbb');self.assertEqual(len(c.calls),2)
 def test_retired_request_cannot_fall_back_or_use_another_account(self):
  c=Client();self.assertEqual(self.loader()(c,'aaaaaaaaaaa',lambda:False),({},'related'));self.assertEqual(c.calls,[])
