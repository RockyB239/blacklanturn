import sys,unittest,sqlite3,tempfile,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
class PreviewLanguageCache(unittest.TestCase):
 def test_only_the_requested_title_is_read_and_database_is_not_modified(self):
  import preview_language
  with tempfile.TemporaryDirectory() as tmp:
   db=Path(tmp)/'database_07/ItemDetails.db';db.parent.mkdir()
   with sqlite3.connect(db) as c:
    c.execute('CREATE TABLE video (parent_id TEXT,key TEXT,name TEXT,iso_language TEXT,content TEXT)')
    c.executemany('INSERT INTO video VALUES (?,?,?,?,?)',[('tv.70523','dark','Teaser [Subtitled]','en','Trailer'),('movie.70523','other','English dubbed trailer','en','Trailer')])
   before=db.read_bytes();rows=preview_language.cached_video_metadata(Path(tmp),('tv','70523'))
   self.assertEqual(rows,{'dark':{'name':'Teaser [Subtitled]','language':'en','type':'Trailer'}})
   self.assertEqual(db.read_bytes(),before)
 def test_missing_or_changed_cache_schema_falls_back_without_failing_preview(self):
  import preview_language
  with tempfile.TemporaryDirectory() as tmp:
   self.assertEqual(preview_language.cached_video_metadata(Path(tmp),('tv','70523')), {})
   db=Path(tmp)/'database_08/ItemDetails.db';db.parent.mkdir()
   with sqlite3.connect(db) as c:c.execute('CREATE TABLE video (name TEXT)')
   self.assertEqual(preview_language.cached_video_metadata(Path(tmp),('tv','70523')), {})
 def test_malformed_identity_never_selects_other_titles(self):
  import preview_language
  self.assertEqual(preview_language.cached_video_metadata(Path('/nonexistent'),('tv',"70523' OR 1=1")),{})
if __name__=='__main__':unittest.main()

class PreviewTitleAliases(unittest.TestCase):
 def test_reads_only_selected_identity_aliases_without_writes(self):
  import preview_language
  fn=getattr(preview_language,'cached_title_aliases',None);self.assertIsNotNone(fn)
  with tempfile.TemporaryDirectory() as tmp:
   db=Path(tmp)/'database_07/ItemDetails.db';db.parent.mkdir()
   with sqlite3.connect(db) as c:
    c.execute('CREATE TABLE tvshow(id TEXT,title TEXT,originaltitle TEXT)');c.executemany('INSERT INTO tvshow VALUES(?,?,?)',[('tv.1','Money Heist','La casa de papel'),('tv.2','Another title','Wrong alias')])
   before=db.read_bytes();self.assertEqual(fn(Path(tmp),('tv','1')),['Money Heist','La casa de papel']);self.assertEqual(db.read_bytes(),before)
 def test_missing_schema_and_invalid_identity_return_no_alias(self):
  import preview_language
  fn=getattr(preview_language,'cached_title_aliases',None);self.assertIsNotNone(fn)
  with tempfile.TemporaryDirectory() as tmp:
   self.assertEqual(fn(Path(tmp),('tv','missing')),[]);self.assertEqual(fn(Path(tmp),('tv','1')),[])
