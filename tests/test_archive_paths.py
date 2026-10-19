"""Portable ZIP destination identities, using actual ZIP metadata/reader behavior."""
import importlib.util,io,stat,unittest,warnings,zipfile
from pathlib import Path
LIB=Path(__file__).resolve().parents[1]/'installer-source/plugin.program.blacklanturninstaller/resources/libs'
spec=importlib.util.spec_from_file_location('archive_paths_under_test',LIB/'archive_paths.py');PATHS=importlib.util.module_from_spec(spec);spec.loader.exec_module(PATHS)
class ArchivePaths(unittest.TestCase):
 def archive(self,names):
  stream=io.BytesIO()
  with warnings.catch_warnings(),zipfile.ZipFile(stream,'w')as archive:
   warnings.simplefilter('ignore',UserWarning)
   for name in names:archive.writestr(name,b'fixture')
  return stream.getvalue()
 def test_canonical_files_explicit_directories_and_single_decomposed_unicode_are_valid(self):
  raw=self.archive(['addons/','addons/fixture/','addons/fixture/.gitignore','addons/fixture/resources/a.py','addons/fixture/resources/','userdata/cafe\u0301/settings.xml'])
  with zipfile.ZipFile(io.BytesIO(raw))as archive:
   before=archive.namelist();PATHS.validate(archive);self.assertEqual(archive.namelist(),before)
 def test_noncanonical_raw_names_are_rejected(self):
  for name in ('./addons/fixture/a.py','addons/./fixture/a.py','addons//fixture/a.py','addons/fixture/a//','addons/fixture/../a.py','/addons/fixture/a.py','addons\\fixture\\a.py','userdata/./prefs.xml'):
   with self.subTest(name=name),zipfile.ZipFile(io.BytesIO(self.archive([name])))as archive:
    with self.assertRaises(PATHS.PathError):PATHS.validate(archive)
 def test_duplicate_case_unicode_directory_and_file_directory_collisions_are_rejected(self):
  for names in (('addons/fixture/a.py','addons/fixture/a.py'),('addons/fixture/a.py','addons/fixture/A.py'),('userdata/caf\u00e9/settings.xml','userdata/cafe\u0301/settings.xml'),('addons/fixture/Directory/a.py','addons/fixture/directory/b.py'),('addons/fixture/same','addons/fixture/same/child.py'),('addons/fixture/same/','addons/fixture/same')):
   with self.subTest(names=names),zipfile.ZipFile(io.BytesIO(self.archive(names)))as archive:
    with self.assertRaises(PATHS.PathError):PATHS.validate(archive)
 def test_raw_null_filename_cannot_hide_behind_zip_reader_truncation(self):
  raw=self.archive(['userdata/nulXalias.xml']).replace(b'nulXalias.xml',b'nul\x00alias.xml')
  with zipfile.ZipFile(io.BytesIO(raw))as archive:
   item=archive.infolist()[0];self.assertNotEqual(item.orig_filename,item.filename)
   with self.assertRaises(PATHS.PathError):PATHS.validate(archive)
 def test_symlink_metadata_is_rejected_even_at_an_ordinary_filename(self):
  stream=io.BytesIO();item=zipfile.ZipInfo('addons/fixture/link.py');item.external_attr=(stat.S_IFLNK|0o777)<<16
  with zipfile.ZipFile(stream,'w')as archive:archive.writestr(item,b'outside-target')
  with zipfile.ZipFile(stream)as archive:
   with self.assertRaises(PATHS.PathError):PATHS.validate(archive)
if __name__=='__main__':unittest.main()
