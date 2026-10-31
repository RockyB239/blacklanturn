"""Host-only verification of release51's actual full/component artifacts."""
import argparse,hashlib,importlib.util,json,sys,tempfile,zipfile,xml.etree.ElementTree as E
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def verify(baselines,artifacts):
 builder=load('verification151_builder',ROOT/'tools/build_release151.py');i=ROOT/'installer-source/plugin.program.blacklanturninstaller';sys.path.insert(0,str(i))
 from resources.libs import platform_compatibility,helper_providers
 report=json.loads((artifacts/'candidate-packages.json').read_bytes());results={};entries=[]
 for edition,label in (('General','general'),('Apple-TV-Mac','apple')):
  record=report[label];full=artifacts/record['full']['file'];component=artifacts/record['components']['file'];base=baselines/('BlackLanturn-'+edition+'-Kodi21-1.1.40.zip')
  assert builder.file_sha(base)==builder.PINS[edition]
  assert builder.file_sha(full)==record['full']['sha256'];assert builder.file_sha(component)==record['components']['sha256']
  with zipfile.ZipFile(full) as z,zipfile.ZipFile(base) as old:
   assert z.testzip() is None;names=z.namelist();assert len(names)==len(set(names))
   newdata={n:z.read(n) for n in names};olddata={n:old.read(n) for n in old.namelist() if not n.endswith('/')}
   for n in set(newdata)|set(olddata):
    if n.startswith('userdata/') and n not in builder.META:assert newdata.get(n)==olddata.get(n),n
   assert not any(n.startswith(('addons/plugin.video.blacklanturn.fights/','addons/script.module.slyguy/','userdata/Database/')) for n in names)
   for n in names:
    if n.startswith('userdata/') and n.endswith('settings.xml'):
     for node in E.fromstring(z.read(n)).iter('setting'):
      sid=node.get('id','').lower();value=node.get('value',node.text or '').strip()
      if any(term in sid for term in ('token','password','secret','apikey','api_key','client_id','username')):assert value in ('','true','false','0'),sid
   entry=json.loads(z.read('userdata/blacklanturn-releases.json'))['releases'][0];entries.append(entry)
   for n,pin in entry['files'].items():assert hashlib.sha256(z.read(n)).hexdigest()==pin,n
   for n,pin in json.loads((ROOT/'controller-source/manifest115.json').read_bytes())['files'].items():assert entry['files'][builder.CP+n]==pin
   helper_providers.verify_archive(z)
   for pack in ('sculpted-silver','smoked-glass'):assert sum('/icon-packs/packs/'+pack+'/' in n for n in names)>60
  def rpc(raw):
   req=json.loads(raw);assert req['method']=='Addons.GetAddonDetails';aid=req['params']['addonid'];return json.dumps({'result':{'addon':{'addonid':aid,'enabled':True,'version':'21.5.25' if aid=='inputstream.adaptive' else '5.1.0'}}})
  k=SimpleNamespace(executeJSONRPC=rpc,getInfoLabel=lambda _: '21.3',getCondVisibility=lambda c:c in (('System.Platform.Android',) if label=='general' else ('System.Platform.OSX','System.Platform.Darwin')),Monitor=lambda:SimpleNamespace(abortRequested=lambda:False),executebuiltin=lambda *a,**kw:(_ for _ in ()).throw(AssertionError('native write')))
  with tempfile.TemporaryDirectory() as directory:
   result=platform_compatibility.prepare(full,k,home=directory,allow_native_changes=False);assert result['policy']['helper_sync_policy']=='providers-1';assert list(Path(directory).iterdir())==[]
  with zipfile.ZipFile(component) as z:assert z.testzip() is None
  results[label]={'crc':True,'proofs':len(entry['files']),'userdata_preserved':True,'credentials_absent':True,'exact_provider_group':True,'platform_preflight':True,'full_sha256':record['full']['sha256']}
 feed=json.dumps({'schema':1,'releases':entries},indent=2).encode();assert len(feed)<=262144
 installer=artifacts/report['installer']['file'];assert builder.file_sha(installer)==report['installer']['sha256']
 with zipfile.ZipFile(installer) as z:assert z.testzip() is None;assert all(n.startswith('plugin.program.blacklanturninstaller/') for n in z.namelist())
 results['release_feed_bytes']=len(feed);print(json.dumps(results,indent=2));return results
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--baselines',type=Path,required=True);p.add_argument('--artifacts',type=Path,required=True);a=p.parse_args();verify(a.baselines,a.artifacts)
