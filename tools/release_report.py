"""Generate canonical versions and review deltas from packaged public metadata.

Upstream input is an explicit backend snapshot, never a consumer startup fetch.
Only add-on IDs/versions are exported; userdata and account contents are excluded.
"""
import argparse,json,xml.etree.ElementTree as E,zipfile
from pathlib import Path

def report(artifact,upstream=None):
    with zipfile.ZipFile(artifact) as archive:
        marker=json.loads(archive.read('userdata/blacklanturn-build.json'));addons={}
        for name in archive.namelist():
            parts=name.split('/')
            if len(parts)==3 and parts[0]=='addons' and parts[-1]=='addon.xml':
                node=E.fromstring(archive.read(name));addons[parts[1]]=node.get('version')
    pending=[]
    for aid,version in (upstream or {}).items():
        if aid in addons and str(version)!=addons[aid].split(':')[-1].split('+blacklanturn')[0]:
            pending.append({'addon':aid,'bundled':addons[aid],'upstream':str(version),'action':'Review source and required patches before scheduling a BlackLanturn release'})
    return {'schema':1,'artifact':Path(artifact).name,'build':marker['build_version'],'edition':marker['edition'],
            'controller':addons.get('script.blacklanturn.preview'),'installer':addons.get('plugin.program.blacklanturninstaller'),
            'repository':addons.get('repository.blacklanturn'),'addons':addons,'upstream_review':pending}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('artifact',type=Path);parser.add_argument('--upstream',type=Path);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    result=report(args.artifact,json.loads(args.upstream.read_bytes()) if args.upstream else None)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
