import importlib.util,tempfile,unittest,os
from pathlib import Path
from unittest.mock import patch
LIB=Path(__file__).parents[1]/'installer-source/plugin.program.blacklanturninstaller/resources/libs'
class PortableLock(unittest.TestCase):
 def module(self):
  spec=importlib.util.spec_from_file_location('portable_lock_test',LIB/'portable_lock.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
 def test_real_single_writer_and_release(self):
  m=self.module()
  with tempfile.TemporaryDirectory() as t:
   path=Path(t)/'lock';a=os.open(path,os.O_CREAT|os.O_RDWR,0o600);b=os.open(path,os.O_RDWR)
   try:
    m.acquire(a)
    with self.assertRaises(OSError):m.acquire(b)
    m.unlock(a);m.acquire(b);m.unlock(b)
   finally:os.close(a);os.close(b)
 def test_windows_uses_nonblocking_one_byte_lock_and_unlock(self):
  from types import SimpleNamespace
  m=self.module();calls=[];api=SimpleNamespace(LK_NBLCK=2,LK_UNLCK=0,locking=lambda fd,kind,size:calls.append((kind,size,os.lseek(fd,0,os.SEEK_CUR))))
  with tempfile.TemporaryDirectory() as t:
   fd=os.open(Path(t)/'lock',os.O_CREAT|os.O_RDWR,0o600)
   try:
    with patch.object(m,'fcntl',None),patch.object(m,'msvcrt',api):m.acquire(fd);m.unlock(fd)
   finally:os.close(fd)
  self.assertEqual(calls,[(2,1,0),(0,1,0)])
