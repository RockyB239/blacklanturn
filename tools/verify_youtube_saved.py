"""Source-bound promotion of the actual Mac/Fire saved-row acceptance."""
import hashlib,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def inventory(root):return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo') and p.name!='.DS_Store'}
def verify(receipt,manifest):
 assert receipt.get('schema')==1 and receipt.get('feature')=='youtube-saved-rows-1' and receipt.get('passed') is True
 assert receipt.get('controller')==manifest.get('controller')=='0.1.91'
 assert receipt.get('files')==manifest.get('files')==inventory(ROOT/'controller-source/addon'),'Untested controller source'
 assert set(receipt.get('devices',{}))=={'mac','fire'} and receipt.get('apple_tv_accessed') is False
 for dev in receipt['devices'].values():
  for key in ('native_source_exact','measurement_valid','native_watch_matches','refresh_focus_retained','navigable_after','preservation_passed','history_preserved'):assert dev.get(key) is True,key
  assert dev.get('fresh_feed_calls')==0 and dev.get('native_watch_cards_compared',0)>=50 and dev.get('saved_rows',0)>=3
  assert dev.get('continuation_after',0)>dev.get('continuation_before',0)>=50
  before,after=dev.get('before_all_seconds'),dev.get('after_all_seconds')
  assert isinstance(before,list) and isinstance(after,list) and len(before)==len(after)==3
  assert all(type(x) in (int,float) and math.isfinite(x) and x>0 for x in before+after)
  assert max(after)<1,'Saved first usable row regression'
 return True
