"""Fail the release gate if packaged Helper, installer, policy or native proof drift."""
import argparse,hashlib,importlib.util,io,json,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'installer-source/plugin.program.blacklanturninstaller'
def verify_playback_defaults(z):
 def settings(aid):
  return {n.get('id'):n.text or '' for n in ET.fromstring(z.read('userdata/addon_data/'+aid+'/settings.xml'))}
 umbrella=settings('plugin.video.umbrella');youtube=settings('plugin.video.youtube');helper=settings('plugin.video.themoviedb.helper')
 assert umbrella.get('provider.external.enabled')=='true','Playback has no configured external provider'
 assert umbrella.get('external_provider.module')=='script.module.cocoscrapers','Playback provider module missing'
 assert umbrella.get('external_provider.name')=='cocoscrapers','Playback provider name missing'
 assert youtube.get('kodion.mpd.stream.select')=='1' and youtube.get('kodion.video.stream.select')=='1','Embedded previews must not open stream-selection prompts'
 assert helper.get('trakt_watchedindicators')=='true','Build must enable authenticated watch metadata'

def verify(folder):
 receipt=json.loads((ROOT/'compatibility/helper-empty-cache/native-verification.json').read_text())
 approved=json.loads((SOURCE/'resources/managed-helper.json').read_text())
 assert receipt.get('source_origin_verified') is True
 assert receipt['passed'] and receipt['tests']==12 and receipt['failures']==receipt['errors']==0
 assert receipt['source_version']==approved['upstream_version'] and receipt['source_files']==approved['files'],'New Helper requires fresh native regression evidence'
 spec=importlib.util.spec_from_file_location('managed',SOURCE/'resources/libs/managed_addons.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 with zipfile.ZipFile(folder/'plugin.program.blacklanturninstaller-1.0.12.zip') as z:
  assert z.testzip() is None
  installer={n:z.read(n) for n in z.namelist()}
  assert all(n.startswith('plugin.program.blacklanturninstaller/') for n in installer)
  expected_installer={'plugin.program.blacklanturninstaller/'+str(p.relative_to(SOURCE)):p.read_bytes() for p in SOURCE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and not p.name.endswith(('.pyc','.DS_Store'))}
  assert installer==expected_installer,'Installer ZIP differs from reviewed source'
 for ed in ('General','Apple-TV-Mac'):
  with zipfile.ZipFile(folder/f'BlackLanturn-{ed}-Kodi21-1.1.5.zip') as z:
   assert z.testzip() is None;m.verify_archive(z);verify_playback_defaults(z)
   p=json.loads(z.read('userdata/blacklanturn-build.json'))
   assert p['schema']==2 and p['helper_patch']=='empty-cache-1' and p['installer_min_version']=='1.0.12'
   assert p['controller_version']=='0.1.73' and p['helper_search_patch']=='search-batch-1'
   gui={n.get('id'):n.text for n in ET.fromstring(z.read('userdata/guisettings.xml'))}
   assert {k:gui[k] for k in ('filecache.memorysize','filecache.readfactor','filecache.buffermode','filecache.chunksize')}=={'filecache.memorysize':'64','filecache.readfactor':'400','filecache.buffermode':'4','filecache.chunksize':'131072'}
   assert next(n.text for n in ET.fromstring(z.read('userdata/addon_data/plugin.video.themoviedb.helper/settings.xml')) if n.get('id')=='artwork_quality')=='1'
   expected=json.loads((ROOT/'controller-source/manifest73.json').read_text())['files']
   actual={n[len('addons/script.blacklanturn.preview/'):]:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.startswith('addons/script.blacklanturn.preview/')}
   assert actual==expected
   for n,d in installer.items():assert z.read('addons/'+n)==d,'Installer mismatch'
   assert z.read('addons/plugin.program.blacklanturninstaller/resources/libs/managed_addons.py')==(SOURCE/'resources/libs/managed_addons.py').read_bytes()
 print('PASS: both packages, protected schema, exact installer, full Helper manifest and native regression evidence')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('artifacts',type=Path);verify(p.parse_args().artifacts)
