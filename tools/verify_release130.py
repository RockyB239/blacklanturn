"""Exact optimization candidate verification, separate from historical gates."""
import argparse,hashlib,importlib.util,json,zipfile,xml.etree.ElementTree as E
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def sha(raw):return hashlib.sha256(raw).hexdigest()
def inventory(root):return {p.relative_to(root).as_posix():sha(p.read_bytes()) for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo') and p.name!='.DS_Store'}

def verify(artifacts,baselines):
    manifest=json.loads((ROOT/'controller-source/manifest96.json').read_bytes())
    if inventory(ROOT/'controller-source/addon')!=manifest['files']:raise ValueError('Controller source differs')
    spec=importlib.util.spec_from_file_location('release130_managed',ROOT/'installer-source/plugin.program.blacklanturninstaller/resources/libs/managed_addons.py')
    managed=importlib.util.module_from_spec(spec);spec.loader.exec_module(managed)
    result={}
    for edition in ('General','Apple-TV-Mac'):
        path=artifacts/('BlackLanturn-'+edition+'-Kodi21-1.1.30.zip')
        with zipfile.ZipFile(path) as archive,zipfile.ZipFile(baselines/('BlackLanturn-'+edition+'-Kodi21-1.1.29.zip')) as baseline:
            if archive.testzip() is not None:raise ValueError('CRC failed')
            managed.verify_archive(archive,umbrella=True,network=True,youtube=True)
            actual={n:archive.read(n) for n in archive.namelist()}
            if any(n.startswith(('addons/plugin.video.blacklanturn.fights/','addons/resource.images.blacklanturn.personal/')) for n in actual):raise ValueError('Private addon leaked into public build')
            for aid,expected in (('script.blacklanturn.preview',manifest['files']),('plugin.program.blacklanturninstaller',inventory(ROOT/'installer-source/plugin.program.blacklanturninstaller'))):
                prefix='addons/'+aid+'/'
                if {n[len(prefix):]:sha(raw) for n,raw in actual.items() if n.startswith(prefix)}!=expected:raise ValueError('Packaged source differs: '+aid)
            marker=json.loads(actual['userdata/blacklanturn-build.json'])
            if marker['build_version']!='1.1.30' or marker['controller_version']!='0.1.96':raise ValueError('Release identity differs')
            entry=json.loads(actual['userdata/blacklanturn-releases.json'])['releases'][0]
            if entry['id']!=marker['release_id'] or any(sha(actual[n])!=digest for n,digest in entry['files'].items()):raise ValueError('Release proof differs')
            for name in baseline.namelist():
                if name in ('userdata/blacklanturn-build.json','userdata/blacklanturn-releases.json','userdata/BlackLanturn-README.txt') or name.startswith(('addons/script.blacklanturn.preview/','addons/plugin.program.blacklanturninstaller/')):continue
                if actual.get(name)!=baseline.read(name):raise ValueError('Inherited source/defaults changed: '+name)
        result[edition]={'passed':True,'sha256':sha(path.read_bytes()),'bytes':path.stat().st_size,'controller_files':len(manifest['files'])}
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('artifacts',type=Path);parser.add_argument('--baselines',type=Path,required=True);args=parser.parse_args()
    result=verify(args.artifacts,args.baselines);(args.artifacts/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
