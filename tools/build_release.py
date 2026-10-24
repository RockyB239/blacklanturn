"""Reproducible 1.1.18 candidate from verified clean baselines, never live profiles."""
import argparse,ast,hashlib,importlib.util,json,re,sys,xml.etree.ElementTree as ET,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'installer-source/plugin.program.blacklanturninstaller'
PATCH=ROOT/'compatibility/helper-empty-cache'
BASE_HASHES={'General':'49581a62dd63333ff9be861a698d758550e59e2a6091eddb9c3f6f4431eaf3e4','Apple-TV-Mac':'ab396fbbee0bdf726bc1a21e4101bd8ccda3935add041f5b7f005c43a998ca73'}
def sha(data):return hashlib.sha256(data).hexdigest()
def apply_shared_requests(data):
 """One reviewed request implementation; leave edition workarounds untouched."""
 root=ROOT/'compatibility/shared-requests'
 provenance=json.loads((root/'provenance.json').read_text())
 target=provenance['path'];candidate=(root/'reqapi.py').read_bytes()
 if sha(data[target]) not in (provenance['general_before_sha256'],provenance['candidate_sha256']):
  raise ValueError('Unknown shared request source; compatibility review is required')
 if sha(candidate)!=provenance['candidate_sha256']:
  raise ValueError('Reviewed shared request candidate changed')
 data[target]=candidate
def apply_youtube_refresh(data):
 receipt=json.loads((ROOT/'compatibility/youtube-refresh/receipt.json').read_text())
 target='addons/plugin.video.youtube/'+receipt['native_path']
 candidate=(ROOT/'compatibility/youtube-refresh/candidate/function_cache.py').read_bytes()
 if sha(data[target])!=receipt['upstream_sha256'] or sha(candidate)!=receipt['candidate_sha256']:
  raise ValueError('Unknown YouTube cache source; compatibility review is required')
 data[target]=candidate

def zipwrite(path,data):
 with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for name,raw in sorted(data.items()):
   e=zipfile.ZipInfo(name,(2026,10,16,0,0,0));e.compress_type=zipfile.ZIP_DEFLATED;e.external_attr=0o100644<<16;z.writestr(e,raw)
 with zipfile.ZipFile(path) as z:assert z.testzip() is None

def apply_discovery_defaults(data):
 key='userdata/addon_data/script.blacklanturn.preview/rows.json'
 catalog=json.loads((SOURCE/'resources/discovery-lineup.json').read_text())
 assert catalog['schema']==1 and catalog['revision']=='discovery-first-page-1'
 config=json.loads(data[key]);config.update(catalog['defaults'])
 data[key]=json.dumps(config,indent=2).encode()

def apply_display_defaults(data):
 key='userdata/addon_data/script.blacklanturn.preview/rows.json'
 config=json.loads(data[key]);config.update(RatingSources=['rottentomatoes','metacritic','imdb','popcorn'],YouTubeEndSuggestions=True,YouTubeEndAutoplay=False)
 data[key]=json.dumps(config,indent=2).encode()

def apply_youtube_skin(data):
 """Apply the native-tested fullscreen Back route to each portable skin."""
 manifest=json.loads((ROOT/'controller-source/manifest87.json').read_text())['skin']
 home='addons/skin.blacklanturn.preview/xml/Home.xml';addon='addons/skin.blacklanturn.preview/addon.xml'
 candidate=(ROOT/'controller-source/skin-overrides/Home.xml').read_bytes()
 assert sha(data[home])==manifest['baseline_Home.xml'],'Unknown skin Home source'
 assert sha(data[addon])==manifest['baseline_addon.xml'],'Unknown skin addon metadata'
 assert sha(candidate)==manifest['Home.xml'],'Native-tested skin override changed'
 assert ET.fromstring(candidate).tag=='window'
 xml=data[addon];assert b'version="0.1.38"' in xml
 data[home]=candidate;data[addon]=xml.replace(b'version="0.1.38"',b'version="0.1.39"',1)

def apply_umbrella(data):
 """Replace only addon code with pinned complete official92 plus reviewed player."""
 root=ROOT/'compatibility/umbrella-progress'
 source=root/'upstream-6.7.92.zip'
 assert sha(source.read_bytes())=='8dc3b19e70d0e02deb32d06579441288dbe1911ecaec2628d298590e1333853f','Official Umbrella archive changed'
 with zipfile.ZipFile(source) as z:
  assert z.testzip() is None
  files={n[len('plugin.video.umbrella/'):]:z.read(n) for n in z.namelist() if n.startswith('plugin.video.umbrella/') and not n.endswith('/')}
 assert {n:sha(raw) for n,raw in files.items()}==json.loads((root/'upstream-6.7.92-manifest.json').read_text())['files'],'Official Umbrella inventory changed'
 player=root/'duration-candidate/6.7.92/player.py';candidate=player.read_bytes()
 assert sha(candidate)=='904b7eb226045610c213e5083a55d99b4462620b1089fb413a4e2e1b04f1b00c','Reviewed Umbrella player changed'
 files['resources/lib/modules/player.py']=candidate
 autoplay=ROOT/'compatibility/autoplay-size'
 reviewed=json.loads((autoplay/'release-source.json').read_text())
 assert reviewed['patch']=='same-show-source-1'
 for name,digest in reviewed['files'].items():
  raw=(autoplay/'candidate'/name).read_bytes()
  assert sha(raw)==digest,'Reviewed autoplay candidate changed'
  files[name]=raw
 assert {n:sha(raw) for n,raw in files.items()}==json.loads((SOURCE/'resources/managed-umbrella.json').read_text())['files'],'Managed Umbrella inventory changed'
 prefix='addons/plugin.video.umbrella/'
 for name in list(data):
  if name.startswith(prefix):del data[name]
 data.update({prefix+n:raw for n,raw in files.items()})

def build(baselines,output):
 output.mkdir(parents=True,exist_ok=True)
 installer={str(p.relative_to(SOURCE)):p.read_bytes() for p in SOURCE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and not p.name.endswith(('.pyc','.DS_Store'))}
 assert ET.fromstring(installer['addon.xml']).get('version')=='1.0.23'
 installer_zip=output/'plugin.program.blacklanturninstaller-1.0.23.zip'
 zipwrite(installer_zip,{'plugin.program.blacklanturninstaller/'+n:raw for n,raw in installer.items()})
 spec=importlib.util.spec_from_file_location('managed',SOURCE/'resources/libs/managed_addons.py');managed=importlib.util.module_from_spec(spec);spec.loader.exec_module(managed)
 for edition,expected in BASE_HASHES.items():
  source=baselines/f'BlackLanturn-{edition}-Kodi21-1.1.2.zip';assert sha(source.read_bytes())==expected,'Baseline changed'
  with zipfile.ZipFile(source) as z:
   assert z.testzip() is None;before={n:z.read(n) for n in z.namelist()}
  data=dict(before);apply_display_defaults(data);apply_discovery_defaults(data);apply_youtube_skin(data);apply_umbrella(data);apply_shared_requests(data);apply_youtube_refresh(data);prefix='addons/plugin.program.blacklanturninstaller/'
  data={n:d for n,d in data.items() if not n.startswith(prefix)}
  data.update({prefix+n:d for n,d in installer.items()})
  controller_root=ROOT/'controller-source/addon'
  controller={str(p.relative_to(controller_root)):p.read_bytes() for p in controller_root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
  controller_manifest=json.loads((ROOT/'controller-source/manifest87.json').read_text())
  assert controller_manifest['controller']=='0.1.87' and ET.fromstring(controller['addon.xml']).get('version')=='0.1.87'
  expected_controller=controller_manifest['files']
  assert {n:sha(raw) for n,raw in controller.items()}==expected_controller,'Validated controller changed'
  cp='addons/script.blacklanturn.preview/'
  data={n:raw for n,raw in data.items() if not n.startswith(cp)}
  data.update({cp+n:raw for n,raw in controller.items()})
  target='addons/plugin.video.themoviedb.helper/resources/tmdbhelper/lib/items/directories/tmdb/lists_search.py'
  assert sha(before[target])=='27f4d284eab62bfdfb414c6945f84dcbf86affa3e58277ddb5a6d370b4330996'
  data[target]=(PATCH/'candidate/lists_search.py').read_bytes()
  assert sha(data[target])=='3cc1c1165fd57b233b868fb35e4ceca1cf2449a85a44fb5b9f04cde4b6ae2862'
  for name in ('player.py','scrobbler.py','service.py'):
   data['addons/plugin.video.themoviedb.helper/resources/tmdbhelper/lib/monitor/'+name]=(ROOT/'compatibility/helper-progress/candidate'/name).read_bytes()
  gui=ET.fromstring(data['userdata/guisettings.xml'])
  for key,value in {'filecache.memorysize':'64','filecache.readfactor':'400','filecache.buffermode':'4','filecache.chunksize':'131072','locale.audiolanguage':'default','locale.subtitlelanguage':'forced_only'}.items():
   node=next((n for n in gui if n.get('id')==key),None)
   if node is None:node=ET.SubElement(gui,'setting',id=key)
   node.attrib.pop('default',None);node.text=value
  data['userdata/guisettings.xml']=ET.tostring(gui,encoding='utf-8',xml_declaration=True)
  hp='userdata/addon_data/plugin.video.themoviedb.helper/settings.xml'
  helper_settings=ET.fromstring(data[hp]);quality=next(n for n in helper_settings if n.get('id')=='artwork_quality');quality.attrib.pop('default',None);quality.text='1'
  data[hp]=ET.tostring(helper_settings,encoding='utf-8',xml_declaration=True)
  def apply_settings(path,values):
   root=ET.fromstring(data[path])
   for key,value in values.items():
    node=next((n for n in root if n.get('id')==key),None)
    if node is None:node=ET.SubElement(root,'setting',id=key)
    node.attrib.pop('default',None);node.attrib.pop('value',None);node.text=value
   data[path]=ET.tostring(root,encoding='utf-8',xml_declaration=True)
  up='userdata/addon_data/plugin.video.umbrella/settings.xml'
  yp='userdata/addon_data/plugin.video.youtube/settings.xml'
  apply_settings(up,{'provider.external.enabled':'true','external_provider.module':'script.module.cocoscrapers','external_provider.name':'cocoscrapers'})
  apply_settings(yp,{'kodion.mpd.stream.select':'1','kodion.video.stream.select':'1','kodion.history.remote':'true','kodion.history.local':'true'})
  defaults=json.loads((SOURCE/'resources/playback-defaults.json').read_text(encoding='utf-8'))
  for name,fields in defaults.items():apply_settings('userdata/'+name,fields)
  marker=json.loads(data['userdata/blacklanturn-build.json']);marker.update(schema=3,youtube_refresh_patch='youtube-freshness-1',preferences_policy='playback-trakt-youtube-umbrella-network-autoplay-1',autoplay_patch='same-show-source-1',build_version='1.1.18',network_patch='request-reliability-privacy-1',helper_patch='empty-cache-1',installer_min_version='1.0.23',discovery_patch='discovery-first-page-1',controller_version='0.1.87',youtube_end_patch='youtube-end-1',skin_version='0.1.39',helper_search_patch='search-batch-1',helper_playback_patch='sampled-progress-1',umbrella_version='6.7.92',umbrella_patch='event-progress-3')
  data['userdata/blacklanturn-build.json']=json.dumps(marker,indent=2).encode()
  data['userdata/BlackLanturn-README.txt']=(before['userdata/BlackLanturn-README.txt'].decode()+'\nRelease 1.1.16: YouTube end-screen suggestions use signed-in Watch Next with related-video fallback. Autoplay defaults off; optional countdown is 15 seconds, navigation cancels, first Back hides suggestions and second Back returns to the original row. Suggestions can be disabled. Controller 0.1.85 and skin 0.1.39 package the Mac-tested behavior in both editions. New native acceptance is Mac only; Fire Stick testing follows publication at the user request. Installer 1.0.21 preserves existing Standard-update account/settings behavior.\n'+'\nRelease 1.1.15: Flat title Options, retained-row retries and clear local My Stuff wording. Manually chosen episode sources carry their service and size ceiling through the same show, including later seasons; normal autoplay keeps its configured ranking. The source choice is temporary, can be reset from Options and clears at Stop. Queued playback retains its prepared source and tracked progress across native callback handoffs. Controller 0.1.84 and Installer 1.0.20 protect exact reviewed source. New playback was naturally tested on Mac only; Fire/Apple TV device updates and native acceptance are deferred. Standard updates retain supported playback preferences and selected accounts.\n'+'\nRelease 1.1.14: Both editions share request-reliability-privacy-1: server Retry-After cooldown (minimum 60 seconds) and status/hostname-only HTTP error logging. Installer 1.0.19 validates and protects the complete shared dependency using the existing managed-addon update policy. Platform-specific YouTube source, processing limits and playback/default settings are unchanged.\n'+'\n\nRelease 1.1.13: Umbrella 6.7.92 includes event-progress-3 with current-item metadata duration fallback, absolute seek capture and guarded exact-zero resume clearing. Installer 1.0.18 verifies the complete managed Umbrella tree and protects its normal update path before cleanup. Controller 0.1.83 uses YouTube-specific Details and consistent independent preview navigation. Both clean editions default to four ratings with TMDb hidden; ratings remain configurable. The preserved install flow makes Standard versus Account-only reset explicit, repairs preservation controls and hides unconfigured destinations. Standard updates retain selected playback choices and authorizations; account-only reset deliberately uses build defaults and selected accounts. Managed Helper 6.17.9 includes sampled-progress-1 alongside empty-cache-1 and search-batch-1. Position sampling uses the existing playback service only, with no added browsing network requests or background thread. Existing adaptive YouTube recommendations, artwork, watch status, 45-second inline previews, automatic fullscreen quality, language/forced subtitle defaults and device-specific playback compatibility remain retained. Native release acceptance is recorded separately; this package description is not proof.\n').encode()
  data['userdata/BlackLanturn-README.txt']+=b'\nRelease 1.1.18: First-page discovery uses improved category recipes and local ordering without extra duplicate-refill requests. Valid overlap remains available. Installer 1.0.23 upgrades recognized default lists while retaining customized lists, all other controller preferences and selected accounts. Controller 0.1.87; skin 0.1.39 unchanged. Native discovery acceptance is Mac only; other device updates are deferred.\n'
  data['userdata/BlackLanturn-README.txt']+=b'\nRelease 1.1.18: YouTube cache reads retain fetched age; normal full-video history is enabled on clean installs while previews remain excluded. Fresh recommendations place completed videos after unfinished choices. The existing refresh worker publishes primary rows early, then categories, retaining focus and prior results on late errors. Controller 0.1.87 and Installer 1.0.23 protect exact platform-specific YouTube code. Standard preserves saved history privacy choices, playback preferences and selected accounts. Native feature acceptance is Mac only at packaging time.\n'
  allowed={n for n in set(before)|set(data) if n.startswith((prefix,cp,'addons/plugin.video.umbrella/'))}|{'addons/skin.blacklanturn.preview/xml/Home.xml','addons/skin.blacklanturn.preview/addon.xml','addons/plugin.video.youtube/resources/lib/youtube_plugin/kodion/sql_store/function_cache.py','userdata/blacklanturn-build.json','userdata/BlackLanturn-README.txt','userdata/guisettings.xml','userdata/addon_data/script.blacklanturn.preview/rows.json',hp,up,yp,target,'addons/script.module.jurialmunkey/resources/modules/jurialmunkey/reqapi.py'}|{'addons/plugin.video.themoviedb.helper/resources/tmdbhelper/lib/monitor/'+n for n in ('player.py','scrobbler.py','service.py')}
  changed={n for n in set(before)|set(data) if before.get(n)!=data.get(n)};assert changed<=allowed
  for n,raw in data.items():
   assert n.startswith(('addons/','userdata/')) and '..' not in n.split('/')
   assert not any(x in n.split('/') for x in ('__pycache__','.git','packages','__MACOSX'))
   assert not n.endswith(('.pyc','.pyo','.so','.dylib','.dll','.exe','.DS_Store'))
   assert not raw.startswith((b'\x7fELF',b'\xcf\xfa\xed\xfe',b'\xfe\xed\xfa\xcf',b'MZ'))
   if n.endswith('/addon.xml'):ET.fromstring(raw)
   if n.endswith('.py') and n!=prefix+'resources/libs/zipfile.py':ast.parse(raw,n)
   if n.startswith('userdata/') and n not in ('userdata/blacklanturn-build.json','userdata/BlackLanturn-README.txt','userdata/guisettings.xml','userdata/addon_data/script.blacklanturn.preview/rows.json',hp,up,yp):assert raw==before[n],'Userdata changed'
  addons={n.split('/')[1]:ET.fromstring(raw) for n,raw in data.items() if n.startswith('addons/') and n.endswith('/addon.xml')}
  system={'xbmc.python','xbmc.gui','xbmc.json','xbmc.addon','kodi.resource','script.module.pil','script.module.pycryptodome','inputstream.adaptive'}
  for aid,addon in addons.items():
   for dep in addon.findall('./requires/import'):
    if dep.get('optional')=='true':continue
    assert dep.get('addon') in addons or dep.get('addon') in system,(aid,dep.get('addon'))
  out=output/f'BlackLanturn-{edition}-Kodi21-1.1.18.zip';zipwrite(out,data)
  with zipfile.ZipFile(out) as z:managed.verify_archive(z, umbrella=True, network=True, youtube=True)
  files={n:sha(d) for n,d in sorted(data.items())}
  report={'file':out.name,'sha256':sha(out.read_bytes()),'bytes':out.stat().st_size,'files':len(data),'changed_paths':sorted(changed),'helper':'6.17.9 + empty-cache-1 + search-batch-1 + sampled-progress-1','installer':'1.0.23','umbrella':'6.7.92 + event-progress-3','schema':3,'settings_and_rows':'clean 1.1.2 plus exact playback-provider, automatic YouTube quality, watch-indicator, 64MB/4x buffer and High artwork defaults','native_binaries':0}
  (output/(edition+'-package.json')).write_text(json.dumps(report,indent=2));(output/(edition+'-manifest.json')).write_text(json.dumps(files,indent=2));print(json.dumps(report),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--baselines',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();build(a.baselines,a.output)
