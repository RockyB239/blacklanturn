"""Reproducible 1.1.27 candidate from verified clean baselines, never live profiles."""
import argparse,ast,hashlib,importlib.util,json,re,sys,xml.etree.ElementTree as ET,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'installer-source/plugin.program.blacklanturninstaller'
PATCH=ROOT/'compatibility/helper-empty-cache'
BASE_HASHES={'General':'49581a62dd63333ff9be861a698d758550e59e2a6091eddb9c3f6f4431eaf3e4','Apple-TV-Mac':'ab396fbbee0bdf726bc1a21e4101bd8ccda3935add041f5b7f005c43a998ca73'}
def sha(data):return hashlib.sha256(data).hexdigest()
RELEASE_PROOFS=('addons/repository.blacklanturn/addon.xml', 'addons/repository.blacklanturn/icon.png', 'addons/script.blacklanturn.preview/addon.xml', 'addons/script.blacklanturn.preview/default.py', 'addons/script.blacklanturn.preview/live_review.py', 'addons/script.blacklanturn.preview/filtered_pages.py', 'addons/script.blacklanturn.preview/youtube_saved.py', 'addons/script.blacklanturn.preview/youtube_saved_runtime.py', 'addons/script.blacklanturn.preview/youtube_browser.py', 'addons/script.blacklanturn.preview/youtube_rows.py', 'addons/script.blacklanturn.preview/release_updates.py', 'addons/script.blacklanturn.preview/update_notes_ui.py', 'addons/script.blacklanturn.preview/resources/skins/Default/1080i/UpdateNotice.xml', 'addons/script.blacklanturn.preview/resources/skins/Default/1080i/UpdateNotes.xml', 'addons/plugin.program.blacklanturninstaller/addon.xml', 'addons/plugin.program.blacklanturninstaller/resources/libs/wizard.py', 'addons/plugin.program.blacklanturninstaller/resources/libs/inplace_update.py', 'addons/plugin.program.blacklanturninstaller/resources/libs/build_preferences.py', 'addons/plugin.program.blacklanturninstaller/resources/libs/release_notice_state.py', 'addons/plugin.program.blacklanturninstaller/resources/libs/managed_addons.py', 'addons/plugin.program.blacklanturninstaller/resources/libs/managed_versions.py', 'addons/plugin.video.themoviedb.helper/resources/tmdbhelper/lib/items/directories/tmdb/lists_search.py', 'addons/plugin.video.themoviedb.helper/resources/tmdbhelper/lib/monitor/player.py', 'addons/plugin.video.umbrella/resources/lib/modules/player.py', 'addons/plugin.video.umbrella/resources/lib/modules/control.py', 'addons/plugin.video.youtube/resources/lib/youtube_plugin/kodion/context/xbmc/xbmc_context.py', 'addons/plugin.video.youtube/resources/lib/youtube_plugin/kodion/sql_store/function_cache.py', 'addons/script.module.jurialmunkey/resources/modules/jurialmunkey/reqapi.py', 'addons/skin.blacklanturn.preview/xml/Home.xml')

RELEASE_PROOFS += ('addons/script.blacklanturn.preview/related_titles.py','addons/script.blacklanturn.preview/preview_identity.py','addons/script.blacklanturn.preview/preview_fallback.py','addons/script.blacklanturn.preview/resources/skins/Default/1080i/LiveReview.xml','addons/plugin.program.blacklanturninstaller/resources/libs/gui/navigation.py','addons/plugin.program.blacklanturninstaller/resources/libs/gui/updates_menu.py','addons/plugin.program.blacklanturninstaller/resources/libs/common/router.py','addons/plugin.program.blacklanturninstaller/resources/libs/gui/window.py','addons/plugin.program.blacklanturninstaller/resources/libs/update.py','addons/plugin.program.blacklanturninstaller/startup.py','addons/plugin.program.blacklanturninstaller/uservar.py','addons/plugin.program.blacklanturninstaller/resources/skins/Default/1080i/InstallerNavigation.xml','addons/plugin.program.blacklanturninstaller/resources/skins/Default/1080i/FirstRunSaveData.xml','addons/plugin.program.blacklanturninstaller/resources/media/updates.png','addons/plugin.program.blacklanturninstaller/resources/media/maintenance-wrench.png')

RELEASE_PROOFS += ('addons/script.blacklanturn.preview/installer_recovery.py','addons/plugin.program.blacklanturninstaller/resources/libs/gui/navigation_model.py')

def release_entry(data,edition):
 editions={'General':'general','Apple-TV-Mac':'apple'}
 if edition not in editions:raise ValueError('Unknown release edition')
 marker=json.loads(data['userdata/blacklanturn-build.json'])
 if marker['edition']!=editions[edition]:raise ValueError('Package edition mismatch')
 notes=json.loads((ROOT/('hosted-files/release-notes-'+marker['build_version']+'.json')).read_text())
 return dict(id=marker['release_id'],edition=marker['edition'],version=marker['build_version'],revision=marker['release_revision'],**notes,files={n:sha(data[n]) for n in RELEASE_PROOFS})

def apply_repository(data):
 """Bundle the exact current public repository instead of the old clean baseline."""
 archive=ROOT/'repository.blacklanturn.zip'
 assert sha(archive.read_bytes())=='b7307d60bbfb507848ece7dc039eb20a0501a16e7d8a5f47a9c176c5aeb576be','Public repository archive changed; review and repin before packaging'
 with zipfile.ZipFile(archive) as z:
  assert z.testzip() is None
  assert set(z.namelist())=={'repository.blacklanturn/addon.xml','repository.blacklanturn/icon.png'}
  staged={'addons/'+n:z.read(n) for n in z.namelist()}
 assert ET.fromstring(staged['addons/repository.blacklanturn/addon.xml']).get('version')=='1.0.6'
 for name in list(data):
  if name.startswith('addons/repository.blacklanturn/'):del data[name]
 data.update(staged)

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
 context=ROOT/'compatibility/youtube-context';manifest=json.loads((context/'manifest.json').read_text());target='addons/plugin.video.youtube/'+manifest['path'];candidate=(context/'candidate/xbmc_context.py').read_bytes()
 if sha(data[target])!=manifest['upstream_sha256'] or sha(candidate)!=manifest['candidate_sha256']:
  raise ValueError('Unknown YouTube context source; compatibility review is required')
 data[target]=candidate

def apply_managed_versions(data):
 spec=importlib.util.spec_from_file_location('build_managed_versions',SOURCE/'resources/libs/managed_versions.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 staged=dict(data)
 candidates={key:data['addons/'+key] if sha(data['addons/'+key])==variant['managed_sha256'] else (ROOT/'compatibility/managed-updates/umbrella/candidate'/key.split('/',1)[1]).read_bytes() for key,variant in m.policy()['source_adapters'].items()}
 m.apply_source_adapters(staged,candidates)
 m.apply_metadata(staged)
 data.update(staged)

def apply_preview_check(data):
 """Keep the General-only read-only checker compatible with reviewed metadata."""
 root=ROOT/'compatibility/managed-updates/previewcheck'
 receipt=json.loads((root/'provenance.json').read_text())
 prefix='addons/service.blacklanturn.previewcheck/'
 present={name[len(prefix):]:sha(raw) for name,raw in data.items() if name.startswith(prefix)}
 if not present:return  # The Apple edition does not ship this Fire TV check.
 if present not in (receipt['upstream_files'],receipt['candidate_files']):
  raise ValueError('Unknown General preview checker; compatibility review is required')
 candidates={p.name:p.read_bytes() for p in (root/'candidate').iterdir() if p.is_file()}
 if {n:sha(raw) for n,raw in candidates.items()}!=receipt['candidate_files']:
  raise ValueError('Reviewed General preview checker changed')
 data.update({prefix+n:raw for n,raw in candidates.items()})

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

def current_addon_manifest():
 return json.loads((ROOT/'compatibility/current-addons/manifest.json').read_text())['addons']

def current_addon_files(addon_id, record):
 root=ROOT/'compatibility/current-addons'
 archive=root/record['archive']
 if sha(archive.read_bytes())!=record['archive_sha256']:
  raise ValueError('Current add-on archive changed: '+addon_id)
 with zipfile.ZipFile(archive) as z:
  if z.testzip() is not None:raise ValueError('Invalid current add-on archive: '+addon_id)
  names=[n for n in z.namelist() if not n.endswith('/')]
  if len(names)!=len(set(names)) or any(not n.startswith(addon_id+'/') or '..' in n.split('/') or '' in n.split('/') for n in names):
   raise ValueError('Invalid current add-on archive layout: '+addon_id)
  files={n[len(addon_id)+1:]:z.read(n) for n in names}
 hashes={n:sha(raw) for n,raw in files.items()}
 if hashes!=record['files'] or len(files)!=record['file_count'] or sha(json.dumps(hashes,sort_keys=True,separators=(',',':')).encode())!=record['tree_sha256']:
  raise ValueError('Current add-on complete source changed: '+addon_id)
 xml=ET.fromstring(files['addon.xml'])
 if xml.get('id')!=addon_id or xml.get('version')!=record['version']:
  raise ValueError('Current add-on metadata differs: '+addon_id)
 return files

def apply_current_addons(data, addon_ids=None):
 """Stage complete pinned code, preflight every source before any mutation."""
 manifest=current_addon_manifest();selected=manifest if addon_ids is None else {aid:manifest[aid] for aid in addon_ids}
 staged={aid:current_addon_files(aid,record) for aid,record in selected.items()}
 prefixes=tuple('addons/'+aid+'/' for aid in selected)
 for name in list(data):
  if name.startswith(prefixes):del data[name]
 for aid,files in staged.items():data.update({'addons/'+aid+'/'+n:raw for n,raw in files.items()})

def apply_umbrella(data):
 """Pinned complete current Umbrella, including reviewed source ports."""
 apply_current_addons(data,('plugin.video.umbrella',))

def verify_prior_source_acceptance(receipt):
 """Source-bound previously captured native evidence, not release installation."""
 if receipt.get('schema')!=1 or receipt.get('passed') is not True or receipt.get('runtime')!='21.3' or receipt.get('release_install_acceptance') is not False:
  raise ValueError('Current source evidence scope differs')
 manifest=current_addon_manifest();manifest['plugin.video.themoviedb.helper']=json.loads((ROOT/'compatibility/current-addons/historical-helper-6.18.1-manifest.json').read_text())
 expected={aid:{'version':record['version'],'tree_sha256':record['tree_sha256'],'file_count':record['file_count']} for aid,record in manifest.items()}
 if receipt.get('sources')!=expected:raise ValueError('Current native source identity differs')
 for aid,check in receipt.get('source_readback',{}).items():
  if aid not in expected or check!={'version':expected[aid]['version'],'exact_files':expected[aid]['file_count']}:
   raise ValueError('Current native source readback differs')
 if set(receipt.get('source_readback',{}))!={'plugin.video.umbrella','plugin.video.themoviedb.helper','script.module.infotagger'}:
  raise ValueError('Current native source readback incomplete')
 for key in ('playback_started','playback_advanced','preservation_passed','temporary_favourite_removed','owned_staging_removed','control_tunnel_closed','handed_back_for_use'):
  if receipt.get(key) is not True:raise ValueError('Missing current source evidence: '+key)

def verify_current_source_contract(receipt):
 """Require regressions on exact current Helper source without inventing Fire use."""
 if receipt.get('schema')!=1 or receipt.get('passed') is not True or receipt.get('physical_fire_tested') is not False or receipt.get('release_install_acceptance') is not False:
  raise ValueError('Current source contract scope differs')
 expected={aid:{'version':record['version'],'tree_sha256':record['tree_sha256'],'file_count':record['file_count']} for aid,record in current_addon_manifest().items()}
 sources=receipt.get('sources',{})
 if 'plugin.video.themoviedb.helper' not in sources or any(aid not in expected or value!=expected[aid] for aid,value in sources.items()):
  raise ValueError('Current source contract identity differs')
 result=receipt.get('tests',{})
 if not isinstance(result.get('count'),int) or result['count']<49 or result.get('failures')!=0 or result.get('errors')!=0:
  raise ValueError('Current source regression evidence incomplete')

def _version_key(value):
 epoch,sep,rest=value.partition(':')
 if not sep:epoch,rest='0',epoch
 return int(epoch),tuple(int(x) for x in re.findall(r'\d+',rest.split('+')[0]))

def verify_dependency_closure(data):
 """Audit mandatory bundled dependencies and their declared minimum versions."""
 addons={n.split('/')[1]:ET.fromstring(raw) for n,raw in data.items() if n.startswith('addons/') and n.endswith('/addon.xml') and n.count('/')==2}
 # Target Kodi21.3 API contract is xbmc.python3.0.1. Native platform packages are
 # intentionally resolved by Kodi, never copied from another device.
 system={'xbmc.python':'3.0.1','xbmc.gui':'5.17.0','xbmc.json':'13.0.0','xbmc.addon':'21.3.0','kodi.resource':'1.0.0','script.module.pil':None,'script.module.pycryptodome':None,'inputstream.adaptive':None}
 for aid,addon in addons.items():
  for dep in addon.findall('./requires/import'):
   if dep.get('optional')=='true':continue
   did=dep.get('addon');minimum=dep.get('version','0')
   if did in addons:actual=addons[did].get('version','0')
   elif did in system:actual=system[did]
   else:raise ValueError('Missing mandatory dependency: '+aid+' -> '+str(did))
   if actual is not None and _version_key(actual)<_version_key(minimum):
    raise ValueError('Dependency minimum not met: '+aid+' -> '+did+' requires '+minimum+', found '+actual)


def build(baselines,output):
 output.mkdir(parents=True,exist_ok=True)
 installer={str(p.relative_to(SOURCE)):p.read_bytes() for p in SOURCE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and not p.name.endswith(('.pyc','.DS_Store'))}
 assert ET.fromstring(installer['addon.xml']).get('version')=='1.0.32'
 installer_zip=output/'plugin.program.blacklanturninstaller-1.0.32.zip'
 zipwrite(installer_zip,{'plugin.program.blacklanturninstaller/'+n:raw for n,raw in installer.items()})
 spec=importlib.util.spec_from_file_location('managed',SOURCE/'resources/libs/managed_addons.py');managed=importlib.util.module_from_spec(spec);spec.loader.exec_module(managed)
 for edition,expected in BASE_HASHES.items():
  source=baselines/f'BlackLanturn-{edition}-Kodi21-1.1.2.zip';assert sha(source.read_bytes())==expected,'Baseline changed'
  with zipfile.ZipFile(source) as z:
   assert z.testzip() is None;before={n:z.read(n) for n in z.namelist()}
  data=dict(before);apply_repository(data);apply_display_defaults(data);apply_discovery_defaults(data);apply_youtube_skin(data);apply_current_addons(data);apply_shared_requests(data);apply_youtube_refresh(data);prefix='addons/plugin.program.blacklanturninstaller/'
  data={n:d for n,d in data.items() if not n.startswith(prefix)}
  data.update({prefix+n:d for n,d in installer.items()})
  controller_root=ROOT/'controller-source/addon'
  controller={str(p.relative_to(controller_root)):p.read_bytes() for p in controller_root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
  controller_manifest=json.loads((ROOT/'controller-source/manifest94.json').read_text())
  assert controller_manifest['controller']=='0.1.94' and ET.fromstring(controller['addon.xml']).get('version')=='0.1.94'
  expected_controller=controller_manifest['files']
  assert {n:sha(raw) for n,raw in controller.items()}==expected_controller,'Validated controller changed'
  cp='addons/script.blacklanturn.preview/'
  data={n:raw for n,raw in data.items() if not n.startswith(cp)}
  data.update({cp+n:raw for n,raw in controller.items()})
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
  marker=json.loads(data['userdata/blacklanturn-build.json']);marker.update(schema=3,youtube_refresh_patch='youtube-freshness-2',preferences_policy='playback-trakt-youtube-umbrella-network-autoplay-1',autoplay_patch='same-show-source-1',build_version='1.1.27',managed_update_policy='kodi-version-epoch-1',network_patch='request-reliability-privacy-1',helper_patch='empty-cache-1',installer_min_version='1.0.30',discovery_patch='discovery-first-page-1',controller_version='0.1.94',youtube_end_patch='youtube-end-1',skin_version='0.1.39',helper_search_patch='search-batch-1',helper_playback_patch='sampled-progress-1',umbrella_version='6.7.97',umbrella_patch='event-progress-3')
  marker['youtube_saved_rows_patch']='account-display-rows-1'
  marker['inplace_update_policy']='bundled-code-1'
  marker.update(release_notices='curated-releases-1',release_id='blacklanturn-'+marker['edition']+'-1.1.27-r0',release_revision=0)
  data['userdata/blacklanturn-build.json']=json.dumps(marker,indent=2).encode()
  data['userdata/BlackLanturn-README.txt']=(before['userdata/BlackLanturn-README.txt'].decode()+'\nRelease 1.1.16: YouTube end-screen suggestions use signed-in Watch Next with related-video fallback. Autoplay defaults off; optional countdown is 15 seconds, navigation cancels, first Back hides suggestions and second Back returns to the original row. Suggestions can be disabled. Controller 0.1.85 and skin 0.1.39 package the Mac-tested behavior in both editions. New native acceptance is Mac only; Fire Stick testing follows publication at the user request. Installer 1.0.21 preserves existing Standard-update account/settings behavior.\n'+'\nRelease 1.1.15: Flat title Options, retained-row retries and clear local My Stuff wording. Manually chosen episode sources carry their service and size ceiling through the same show, including later seasons; normal autoplay keeps its configured ranking. The source choice is temporary, can be reset from Options and clears at Stop. Queued playback retains its prepared source and tracked progress across native callback handoffs. Controller 0.1.84 and Installer 1.0.20 protect exact reviewed source. New playback was naturally tested on Mac only; Fire/Apple TV device updates and native acceptance are deferred. Standard updates retain supported playback preferences and selected accounts.\n'+'\nRelease 1.1.14: Both editions share request-reliability-privacy-1: server Retry-After cooldown (minimum 60 seconds) and status/hostname-only HTTP error logging. Installer 1.0.19 validates and protects the complete shared dependency using the existing managed-addon update policy. Platform-specific YouTube source, processing limits and playback/default settings are unchanged.\n'+'\n\nRelease 1.1.13: Umbrella 6.7.92 includes event-progress-3 with current-item metadata duration fallback, absolute seek capture and guarded exact-zero resume clearing. Installer 1.0.18 verifies the complete managed Umbrella tree and protects its normal update path before cleanup. Controller 0.1.83 uses YouTube-specific Details and consistent independent preview navigation. Both clean editions default to four ratings with TMDb hidden; ratings remain configurable. The preserved install flow makes Standard versus Account-only reset explicit, repairs preservation controls and hides unconfigured destinations. Standard updates retain selected playback choices and authorizations; account-only reset deliberately uses build defaults and selected accounts. Managed Helper 6.17.9 includes sampled-progress-1 alongside empty-cache-1 and search-batch-1. Position sampling uses the existing playback service only, with no added browsing network requests or background thread. Existing adaptive YouTube recommendations, artwork, watch status, 45-second inline previews, automatic fullscreen quality, language/forced subtitle defaults and device-specific playback compatibility remain retained. Native release acceptance is recorded separately; this package description is not proof.\n').encode()
  data['userdata/BlackLanturn-README.txt']+=b'\nRelease 1.1.17: First-page discovery uses improved category recipes and local ordering without extra duplicate-refill requests. Valid overlap remains available. Installer 1.0.22 upgrades recognized default lists while retaining customized lists, all other controller preferences and selected accounts. Controller 0.1.87; skin 0.1.39 unchanged. Native discovery acceptance is Mac only; other device updates are deferred.\n'
  data['userdata/BlackLanturn-README.txt']+=b'\nRelease 1.1.18: YouTube cache reads retain fetched age; normal full-video history is enabled on clean installs while previews remain excluded. Fresh recommendations place completed videos after unfinished choices. The existing refresh worker publishes primary rows early, then categories, retaining focus and prior results on late errors. Controller 0.1.87 and Installer 1.0.23 protect exact platform-specific YouTube code. Standard preserves saved history privacy choices, playback preferences and selected accounts. Native feature acceptance is Mac only at packaging time.\n'
  allowed={n for n in set(before)|set(data) if n.startswith((prefix,cp,'addons/plugin.video.umbrella/'))}|{'addons/skin.blacklanturn.preview/xml/Home.xml','addons/skin.blacklanturn.preview/addon.xml','addons/plugin.video.youtube/resources/lib/youtube_plugin/kodion/sql_store/function_cache.py','addons/plugin.video.youtube/resources/lib/youtube_plugin/kodion/context/xbmc/xbmc_context.py','userdata/blacklanturn-build.json','userdata/BlackLanturn-README.txt','userdata/guisettings.xml','userdata/addon_data/script.blacklanturn.preview/rows.json',hp,up,yp,'addons/script.module.jurialmunkey/resources/modules/jurialmunkey/reqapi.py'}|{'addons/plugin.video.themoviedb.helper/resources/tmdbhelper/lib/monitor/'+n for n in ('player.py','scrobbler.py','service.py')}
  allowed.update(n for n in set(before)|set(data) if any(n.startswith('addons/'+aid+'/') for aid in current_addon_manifest()))
  apply_managed_versions(data)
  apply_preview_check(data)
  allowed.update(n for n in data if n.startswith('addons/service.blacklanturn.previewcheck/'))
  allowed.update(n for n in set(before)|set(data) if n.startswith('addons/repository.blacklanturn/'))
  allowed.update('addons/'+aid+'/addon.xml' for aid in ('plugin.video.themoviedb.helper','plugin.video.umbrella','script.module.jurialmunkey','plugin.video.youtube'))
  changed={n for n in set(before)|set(data) if before.get(n)!=data.get(n)};assert changed<=allowed
  for n,raw in data.items():
   assert n.startswith(('addons/','userdata/')) and '..' not in n.split('/')
   assert not any(x in n.split('/') for x in ('__pycache__','.git','packages','__MACOSX'))
   assert not n.endswith(('.pyc','.pyo','.so','.dylib','.dll','.exe','.DS_Store'))
   assert not raw.startswith((b'\x7fELF',b'\xcf\xfa\xed\xfe',b'\xfe\xed\xfa\xcf',b'MZ'))
   if n.endswith('/addon.xml'):ET.fromstring(raw)
   if n.endswith('.py') and n!=prefix+'resources/libs/zipfile.py':ast.parse(raw,n)
   if n.startswith('userdata/') and n not in ('userdata/blacklanturn-build.json','userdata/BlackLanturn-README.txt','userdata/guisettings.xml','userdata/addon_data/script.blacklanturn.preview/rows.json',hp,up,yp):assert raw==before[n],'Userdata changed'
  verify_dependency_closure(data)
  data['userdata/BlackLanturn-README.txt']+=b'\nRelease 1.1.19: YouTube handles missing Kodi plugin-folder values safely, preventing subscription requests from failing when no plugin folder is active. The exact context guard joins the protected cache patch. Installer 1.0.24 is required. Controller 0.1.87, skin 0.1.39, saved playback choices and selected accounts are retained.\n'
  data['userdata/BlackLanturn-README.txt']+=b'\nRelease 1.1.20: Reviewed managed-addon versions survive ordinary Kodi bulk updates. Installer 1.0.27 validates exact metadata and Umbrella internal-version compatibility before cleanup. Existing playback, source-selection, platform workarounds and selected account choices are retained. Explicit manual downgrades remain outside this protection.\n'
  data['userdata/BlackLanturn-README.txt']+=b'Curated BlackLanturn release notices identify the build version and explain important compatibility fixes. They do not report unrelated add-on inventory changes. Checks are cached in the background. Standard preserves notice preference/history and accounts; clean starts quietly. Controller0.1.90 and Installer1.0.27 include first-page discovery latency repair and an install-completion receipt written after account/settings restoration.\n'
  data['userdata/BlackLanturn-README.txt']+=b'\nRelease 1.1.22: Repository 1.0.6 and its current branded icon replace the old baseline repository, preventing Standard updates from downgrading them. Account-scoped saved YouTube display rows appear before overdue recommendations refresh in the background. Current local watched/resume information is read before reuse; no credentials or watched values are stored in display snapshots. Native Mac and Fire Stick reopen, refresh, focus, continuation and protected-state checks passed. Controller 0.1.92 and Installer 1.0.28 retain existing playback and platform fixes. Apple TV was not contacted for this release. Uncached first loads still require YouTube. Standard preserves selected settings/accounts; clean starts without private recommendations.\n'
  data['userdata/BlackLanturn-README.txt']+=b'\nRelease 1.1.25: Complete pinned current Helper6.18.2 and Umbrella6.7.97 retain reviewed BlackLanturn repairs. Current InfoTagger0.1.0, CocoScrapers1.0.45, SkinVariables2.2.10, InputStreamHelper0.8.6 and US English11.0.84 replace stale baseline code. Installer1.0.30 validates current full source and managed metadata; existing platform playback differences and selected Standard-update settings/accounts remain protected. Native current-source Fire playback was previously validated; clean and Standard release-install evidence is recorded separately.\n'
  data['userdata/BlackLanturn-README.txt']+=b'\nUpdate BlackLanturn in Installer updates bundled code and patches in place. All personal data and other installed add-ons remain in place. No Save Data selections are needed for updates. Fresh and Standard installs remain separate setup tools.\n'
  data['userdata/BlackLanturn-README.txt']+=b'\nRelease 1.1.26: Dedicated Updates sidebar and scrollable release notes, clearer in-place versus reinstall wording, restored main Movies/Shows genre actions, Recommendations-first More like this with branded independent paging, and bounded identity-verified missing-preview fallback. Installer1.0.31 / Controller0.1.93. Existing playback settings, authorizations, watched progress, saved data and user-installed add-ons are retained by Update BlackLanturn.\n'
  data['userdata/BlackLanturn-README.txt']+=b'\nRelease 1.1.27: Existing installations first receive Installer1.0.32 once through Kodi repository add-on updating, then install Build1.1.27. Once Build1.1.27 and Installer1.0.32 are installed, future Update BlackLanturn runs update the build and bundled Installer together. Interrupted Installer updates recover before normal controller startup. Selected settings, accounts, saved data and other installed add-ons remain retained.\n'
  data['userdata/blacklanturn-releases.json']=json.dumps({'schema':1,'releases':[release_entry(data,edition)]},indent=2).encode()
  out=output/f'BlackLanturn-{edition}-Kodi21-1.1.27.zip';zipwrite(out,data)
  with zipfile.ZipFile(out) as z:managed.verify_archive(z, umbrella=True, network=True, youtube=True)
  files={n:sha(d) for n,d in sorted(data.items())}
  report={'file':out.name,'sha256':sha(out.read_bytes()),'bytes':out.stat().st_size,'files':len(data),'changed_paths':sorted(changed),'helper':'6.18.2 + empty-cache-1 + search-batch-1 + sampled-progress-1','installer':'1.0.32','umbrella':'6.7.97 + event-progress-3','schema':3,'settings_and_rows':'clean 1.1.2 plus exact playback-provider, automatic YouTube quality, watch-indicator, 64MB/4x buffer and High artwork defaults','native_binaries':0}
  (output/(edition+'-package.json')).write_text(json.dumps(report,indent=2));(output/(edition+'-manifest.json')).write_text(json.dumps(files,indent=2));print(json.dumps(report),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--baselines',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();build(a.baselines,a.output)
