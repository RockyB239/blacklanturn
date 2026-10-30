"""Keep URI validation strict without Python call overhead per URI character."""
import sys,unittest
from pathlib import Path
from urllib.parse import quote
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
from public_rows import _art

class ArtworkValidationCost(unittest.TestCase):
 def calls(self,value):
  count=[0]
  def profile(frame,event,arg):
   if event=='call':count[0]+=1
  previous=sys.getprofile()
  try:
   sys.setprofile(profile);result=_art(value)
  finally:sys.setprofile(previous)
  return result,count[0]
 def test_long_valid_uri_does_not_add_python_calls_per_character(self):
  short='image://'+quote('https://image.tmdb.org/t/p/w500/a.jpg',safe='')+'/'
  long='image://'+quote('https://image.tmdb.org/t/p/w500/'+'x'*2500+'.jpg',safe='')+'/'
  a,short_calls=self.calls(short);b,long_calls=self.calls(long)
  self.assertEqual(a,short);self.assertEqual(b,long)
  self.assertLess(long_calls-short_calls,100,'Long artwork addresses must not cause thousands of interpreter calls')
 def test_every_ascii_control_and_space_stays_rejected_direct_and_wrapped(self):
  for code in range(33):
   value='https://image.tmdb.org/t/p/w500/a'+chr(code)+'.jpg'
   self.assertEqual(_art(value),'');self.assertEqual(_art('image://'+quote(value,safe='')+'/'),'')

if __name__=='__main__':unittest.main()
