"""Run the existing 12-case native cache contract offline against candidate source.
Only Kodi/UI, provider responses, title mapping and filesystem root are synthetic.
Actual candidate parsers, decorator, BasicCache and SQLite SimpleCache execute.
"""
import contextlib
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import time
import types
S=Path(__file__).resolve().parents[1]
H=S/'candidate/plugin.video.themoviedb.helper'
J=S/'candidate/script.module.jurialmunkey/resources/modules/jurialmunkey'
R=Path(__file__).resolve().parents[4]/'youtube-refresh-mac-2026-10-22/repo'
# Explicit argument accepts the saved, read-only regression suite.
REGRESSION=Path(sys.argv[1])
def module(name,**kw):
 m=types.ModuleType(name);m.__dict__.update(kw);sys.modules[name]=m
 if '.' in name:
  parent,child=name.rsplit('.',1)
  if parent in sys.modules:setattr(sys.modules[parent],child,m)
 return m
def package(name,path):
 m=module(name);m.__path__=[str(path)];return m
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m
 if '.' in name:
  parent,child=name.rsplit('.',1);setattr(sys.modules[parent],child,m)
 spec.loader.exec_module(m);return m
properties={}
class Window:
 def __init__(self,*a):pass
 def getProperty(self,k):return properties.get(k,'')
 def setProperty(self,k,v):properties[k]=v
 def clearProperty(self,k):properties.pop(k,None)
class FileUtils:
 def get_file_path(self,base,filename,**kw):
  p=Path(base)/filename;p.parent.mkdir(parents=True,exist_ok=True);return str(p)
with tempfile.TemporaryDirectory(prefix='cache-contract-',dir=S/'evidence') as d:
 root=Path(d)
 module('xbmc',Monitor=lambda:types.SimpleNamespace(abortRequested=lambda:False),log=lambda *a,**k:None,getLocalizedString=lambda x:str(x))
 module('xbmcgui',Window=Window)
 module('xbmcvfs',exists=lambda p:Path(p).exists(),translatePath=lambda p:str(root/'home'))
 module('xbmcaddon',Addon=lambda *a:object())
 package('jurialmunkey',J)
 module('jurialmunkey.futils',FileUtils=FileUtils,json_loads=json.loads,get_filecache_name=lambda n:hashlib.md5(n.encode()).hexdigest())
 module('jurialmunkey.plugin',format_name=lambda name,*a,**kw:name)
 module('jurialmunkey.tmdate',set_timestamp=lambda delta=0,*a:int(time.time()+delta))
 module('jurialmunkey.locker',MutexPropLock=lambda *a,**kw:contextlib.nullcontext())
 module('jurialmunkey.parser',try_int=lambda n:int(n))
 load('jurialmunkey.ftools',J/'ftools.py')
 load('jurialmunkey.logger',J/'logger.py')
 load('jurialmunkey.scache',J/'scache.py')
 load('jurialmunkey.bcache',J/'bcache.py')
 for name,path in [('tmdbhelper',H/'resources/tmdbhelper'),('tmdbhelper.lib',H/'resources/tmdbhelper/lib'),('tmdbhelper.lib.files',H/'resources/tmdbhelper/lib/files'),('tmdbhelper.lib.addon',H/'resources/tmdbhelper/lib/addon'),('tmdbhelper.lib.items',H/'resources/tmdbhelper/lib/items'),('tmdbhelper.lib.items.directories',H/'resources/tmdbhelper/lib/items/directories'),('tmdbhelper.lib.items.directories.tmdb',H/'resources/tmdbhelper/lib/items/directories/tmdb'),('tmdbhelper.lib.items.directories.trakt',H/'resources/tmdbhelper/lib/items/directories/trakt')]:package(name,path)
 module('tmdbhelper.lib.addon.logger',kodi_log=lambda *a,**kw:None,kodi_traceback=lambda *a,**kw:None)
 module('tmdbhelper.lib.addon.plugin',get_setting=lambda *a:'',get_language=lambda:'en',get_localized=lambda n:str(n),convert_type=lambda *a,**kw:None)
 module('tmdbhelper.lib.files.futils',FileUtils=FileUtils)
 module('tmdbhelper.lib.files.dbdata',DATABASE_NAME='test_database')
 module('tmdbhelper.lib.items.container',ContainerDefaultCacheDirectory=object)
 module('tmdbhelper.lib.items.directories.mapper_standard',FactoryItemMapper=object)
 load('tmdbhelper.lib.files.scache',H/'resources/tmdbhelper/lib/files/scache.py')
 load('tmdbhelper.lib.files.bcache',H/'resources/tmdbhelper/lib/files/bcache.py')
 load('tmdbhelper.lib.items.directories.lists_default',H/'resources/tmdbhelper/lib/items/directories/lists_default.py')
 load('tmdbhelper.lib.items.directories.tmdb.lists_standard',H/'resources/tmdbhelper/lib/items/directories/tmdb/lists_standard.py')
 load('tmdbhelper.lib.items.directories.trakt.lists_standard',H/'resources/tmdbhelper/lib/items/directories/trakt/lists_standard.py')
 suite=load('saved_cache_contract',REGRESSION)
 result=suite.run(root,'ported-offline',addon_root=H)
 print(json.dumps(result,indent=2))
 (S/'evidence/empty-cache-result.json').write_text(json.dumps(result,indent=2))
 sys.exit(0 if result['passed'] else 1)
