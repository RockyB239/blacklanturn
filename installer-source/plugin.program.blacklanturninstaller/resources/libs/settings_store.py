"""Bounded settings I/O, including Kodi tvOS virtual XML; never log file contents."""
import os,tempfile
from pathlib import Path
try:
 import xbmcvfs
except ImportError:
 xbmcvfs=None
try:
 import xbmc
 TVOS=bool(xbmc.getCondVisibility('System.Platform.TVOS'))
except (ImportError,AttributeError):
 TVOS=False
MAX_BYTES=4*1024*1024

def virtual_xml(path):
 return TVOS and xbmcvfs is not None and Path(path).suffix.lower()=='.xml'

def _native(path):
 return virtual_xml(path) or (xbmcvfs is not None and not path.is_file() and xbmcvfs.exists(str(path)))

def exists(path):
 path=Path(path)
 if path.is_symlink():raise ValueError('Settings link is unsupported')
 if virtual_xml(path):return bool(xbmcvfs.exists(str(path)))
 return path.is_file() or (xbmcvfs is not None and xbmcvfs.exists(str(path)))

def read(path):
 path=Path(path)
 if not exists(path):raise FileNotFoundError(str(path))
 if not _native(path):
  if path.stat().st_size>MAX_BYTES:raise ValueError('Settings file exceeds limit')
  raw=path.read_bytes()
 else:
  f=xbmcvfs.File(str(path))
  try:
   if f.size()>MAX_BYTES:raise ValueError('Settings file exceeds limit')
   raw=bytes(f.readBytes())
  finally:f.close()
 if len(raw)>MAX_BYTES:raise ValueError('Settings file exceeds limit')
 return raw

def write(path,raw):
 path=Path(path)
 if not isinstance(raw,bytes) or len(raw)>MAX_BYTES:raise ValueError('Settings file exceeds limit')
 if path.is_symlink():raise ValueError('Settings link is unsupported')
 path.parent.mkdir(parents=True,exist_ok=True)
 if _native(path):
  old=read(path) if exists(path) else None
  try:
   f=xbmcvfs.File(str(path),'w')
   try:
    if not f.write(raw.decode('utf-8')):raise ValueError('Native settings write rejected')
   finally:f.close()
   if read(path)!=raw:raise ValueError('Native settings readback mismatch')
  except Exception:
   if old is not None:
    f=xbmcvfs.File(str(path),'w')
    try:
     if not f.write(old.decode('utf-8')):raise ValueError('Native settings recovery rejected')
    finally:f.close()
    if read(path)!=old:raise ValueError('Native settings recovery readback mismatch')
   elif exists(path):
    if not xbmcvfs.delete(str(path)):raise ValueError('Native incomplete settings cleanup failed')
   raise
 else:
  descriptor,name=tempfile.mkstemp(prefix=path.name+'.',suffix='.pending',dir=str(path.parent));temp=Path(name)
  try:
   with os.fdopen(descriptor,'wb') as stream:stream.write(raw)
   temp.replace(path)
  finally:
   if temp.exists():temp.unlink()
  if read(path)!=raw:raise ValueError('Settings readback mismatch')

def native_userdata_xml(home):
 """Inventory tvOS XML before physical cleanup removes its parent directories."""
 if not TVOS or xbmcvfs is None:return []
 home=Path(home);userdata=home/'userdata';directories=set();found=set()
 for root,dirs,files in os.walk(userdata,followlinks=False):
  dirs[:]=[d for d in dirs if not (Path(root)/d).is_symlink()]
  directories.add(Path(root))
  if len(directories)>10000:raise ValueError('Settings directory inventory exceeds limit')
 # Addon settings can persist after tvOS evicts their cache directory.
 addons=home/'addons'
 if addons.is_dir():
  for addon in addons.iterdir():
   if addon.is_dir() and not addon.is_symlink():
    path=userdata/'addon_data'/addon.name/'settings.xml'
    if exists(path):found.add(path)
 for directory in directories:
  _,files=xbmcvfs.listdir(str(directory)+'/')
  for name in files:
   if Path(name).name!=name:raise ValueError('Unexpected native settings path')
   if name.lower().endswith('.xml'):found.add(directory/name)
 if len(found)>10000:raise ValueError('Settings inventory exceeds limit')
 for path in found:
  for parent in [path]+list(path.parents):
   if parent==home:break
   if parent.is_symlink():raise ValueError('Settings link is unsupported')
 return sorted(found)

def delete(path):
 path=Path(path)
 if path.is_symlink():raise ValueError('Settings link is unsupported')
 if virtual_xml(path) and xbmcvfs.exists(str(path)):
  if not xbmcvfs.delete(str(path)):raise ValueError('Native settings cleanup failed')
 if path.is_file():path.unlink()
 if exists(path):raise ValueError('Settings cleanup readback failed')
