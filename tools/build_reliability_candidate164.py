"""Offline personal candidate: preserve public57 and all user/default data.

This is deliberately not a public release recipe: it retains public version
numbers, uses revision164, and emits no hosted catalog or publication metadata.
"""
import argparse,copy,hashlib,importlib.util,json,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PINS={'General':'9aaab1b8cfd9a7387318c13c11c9c086c47881d99b3fef0242fac7db00534594','Apple-TV-Mac':'d72fe93a561d13db57bc0f5b186d20e03176aadeea0c5cd573b554632bd85106'}
UP='addons/plugin.video.umbrella/'
IP='addons/plugin.program.blacklanturninstaller/'
NAMES={'resources/lib/modules/source_preferences.py','resources/lib/modules/sources.py'}
def sha(raw):return hashlib.sha256(raw).hexdigest()
def file_sha(path):
 h=hashlib.sha256()
 with path.open('rb') as stream:
  for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def digest_tree(files):return sha(json.dumps(files,sort_keys=True,separators=(',',':')).encode())
def extend_policy(policy,before,overlays):
 if set(overlays)!=NAMES:raise ValueError('Both exact playback modules are required')
 managed=load('candidate164_managed',ROOT/'installer-source/plugin.program.blacklanturninstaller/resources/libs/managed_addons.py')
 previous={n:managed._digest('plugin.video.umbrella',n,raw) for n,raw in before.items()}
 if previous not in [policy['files'],*policy.get('archive_variants',{}).values()]:raise ValueError('Unreviewed baseline Umbrella tree')
 current={n:managed._digest('plugin.video.umbrella',n,overlays.get(n,raw)) for n,raw in before.items()}
 if set(current)!=set(previous):raise ValueError('Complete source inventory differs')
 result=copy.deepcopy(policy);result.setdefault('archive_variants',{})['reliability164']=current
 accepted=result.setdefault('installed_tree_sha256',{}).setdefault(policy['version'],[])
 if digest_tree(current) not in accepted:accepted.append(digest_tree(current))
 return result
def qualify(report,before,after):
 if after.get('source_sha256')!=report['source_sha256']:return {'passed':False,'failures':['Visual receipt source differs from candidate source']}
 if report.get('playback_source_sha256') and after.get('playback_source_sha256')!=report['playback_source_sha256']:return {'passed':False,'failures':['Playback receipt source differs from candidate entry point']}
 gate=load('candidate164_visible',ROOT/'tools/device_validation/experience_gate.py')
 return gate.compare(before,after)
def overlays():
 folder=ROOT/'compatibility/reliability164'
 result={'addons/script.blacklanturn.preview/'+n:(ROOT/'controller-source/addon'/n).read_bytes() for n in ('live_review.py','default.py')}
 result['addons/skin.blacklanturn.preview/xml/DialogConfirm.xml']=(folder/'skin/xml/DialogConfirm.xml').read_bytes()
 result.update({UP+n:(folder/'umbrella'/n).read_bytes() for n in NAMES})
 manifest=json.loads((folder/'SOURCE-MANIFEST.json').read_text())
 if {n:sha(raw) for n,raw in result.items()}!=manifest['files']:raise ValueError('Candidate frozen overlay source differs')
 return result
def build(baselines,output):
 legacy=load('candidate164_legacy',ROOT/'tools/build_release.py');components=load('candidate164_components',ROOT/'installer-source/plugin.program.blacklanturninstaller/resources/libs/component_update.py')
 patches=overlays();output.mkdir(parents=True,exist_ok=True)
 report={'public_changed':False,'publication_ready':False,'source_sha256':sha(patches['addons/script.blacklanturn.preview/live_review.py']),'playback_source_sha256':sha(patches['addons/script.blacklanturn.preview/default.py']),'candidate_revision':164,'editions':{}}
 installer=None
 for edition,pin in PINS.items():
  base=baselines/('BlackLanturn-'+edition+'-Kodi21-1.1.57.zip')
  if file_sha(base)!=pin:raise ValueError('Public57 baseline pin differs')
  with zipfile.ZipFile(base) as z:
   if z.testzip():raise ValueError('Baseline CRC differs')
   before={n:z.read(n) for n in z.namelist() if not n.endswith('/')}
  data=dict(before);data.update(patches)
  policy=json.loads(before[IP+'resources/managed-umbrella.json'])
  files={n[len(UP):]:raw for n,raw in before.items() if n.startswith(UP)}
  policy=extend_policy(policy,files,{n:patches[UP+n] for n in NAMES})
  data[IP+'resources/managed-umbrella.json']=json.dumps(policy,indent=2).encode()
  marker=json.loads(before['userdata/blacklanturn-build.json']);marker.update(release_revision=164,release_id='blacklanturn-'+marker['edition']+'-1.1.57-r164')
  data['userdata/blacklanturn-build.json']=json.dumps(marker,indent=2).encode()
  feed=json.loads(before['userdata/blacklanturn-releases.json']);entry=feed['releases'][0];entry.update(id=marker['release_id'],revision=164)
  for name in patches.keys()|{IP+'resources/managed-umbrella.json'}:entry['files'][name]=sha(data[name])
  release=load('candidate164_release',ROOT/'controller-source/addon/release_updates.py');release.validate_catalog(feed)
  data['userdata/blacklanturn-releases.json']=json.dumps(feed,indent=2).encode()
  metadata={'userdata/blacklanturn-build.json','userdata/blacklanturn-releases.json'}
  assert all(before.get(n)==data.get(n) for n in before.keys()|data.keys() if n.startswith('userdata/') and n not in metadata)
  legacy.verify_dependency_closure(data)
  full=output/('BlackLanturn-'+edition+'-Reliability164-candidate.zip');legacy.zipwrite(full,data)
  component=output/('BlackLanturn-'+edition+'-Reliability164-components.zip');components.build(base,full,component)
  current={n[len(IP):]:raw for n,raw in data.items() if n.startswith(IP)}
  if installer is not None and current!=installer:raise ValueError('Edition installer source differs')
  installer=current
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory)
   for name,raw in current.items():
    p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
   managed=load('candidate164_archive_'+marker['edition'],root/'resources/libs/managed_addons.py')
   with zipfile.ZipFile(full) as archive:managed.verify_archive(archive,umbrella=True,network=True,youtube=True)
  record={'full':{'file':full.name,'sha256':file_sha(full)},'components':{'file':component.name,'sha256':file_sha(component)},'baseline_sha256':pin,'proof_files':len(entry['files']),'userdata_unchanged_except_release_metadata':True}
  report['editions'][marker['edition']]=record
 legacy.zipwrite(output/'BlackLanturn-Installer-Reliability164-candidate.zip',{'plugin.program.blacklanturninstaller/'+n:raw for n,raw in installer.items()})
 (output/'candidate-packages.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--baselines',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();build(a.baselines,a.output)
