"""Smaller downloads, reconstructed before the normal whole-tree validator.

Unchanged code must match exact reviewed hashes; changed add-ons are complete
trees. No binary diffs, profile defaults, or relaxed transaction protections.
"""
from pathlib import Path
import hashlib,importlib.util,json,os,re,tempfile,zipfile

NAME='userdata/blacklanturn-components.json'
ID=re.compile(r'[a-z0-9][a-z0-9_.-]{0,120}')
_io_spec=importlib.util.spec_from_file_location('_component_stream_io',Path(__file__).with_name('stream_io.py'))
stream_io=importlib.util.module_from_spec(_io_spec);_io_spec.loader.exec_module(stream_io)

def digest(files):
    values={k:hashlib.sha256(v).hexdigest() for k,v in files.items()}
    return digest_hashes(values)

def digest_hashes(values):
    return hashlib.sha256(json.dumps(values,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def validate(archive):
    spec=importlib.util.spec_from_file_location('_component_paths',Path(__file__).with_name('archive_paths.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.validate(archive)

def trees(data):
    result={}
    for name,raw in data.items():
        parts=name.split('/')
        if len(parts)>=3 and parts[0]=='addons':result.setdefault(parts[1],{})['/'.join(parts[2:])]=raw
    return result

def _write(archive,name,raw):
    info=zipfile.ZipInfo(name,(2026,10,16,0,0,0))
    info.compress_type=archive.compression
    info.external_attr=0o100644<<16
    archive.writestr(info,raw)

def build(base,target,output):
    with zipfile.ZipFile(base) as old,zipfile.ZipFile(target) as new:
        validate(old);validate(new)
        before={n:old.read(n) for n in old.namelist() if not n.endswith('/')}
        after={n:new.read(n) for n in new.namelist() if not n.endswith('/')}
    old_trees=trees(before);new_trees=trees(after)
    hashes={aid:digest(files) for aid,files in new_trees.items()}
    retained={aid:value for aid,value in hashes.items() if aid in old_trees and digest(old_trees[aid])==value}
    doc={'schema':1,'base':json.loads(before['userdata/blacklanturn-build.json'])['release_id'],
         'target':json.loads(after['userdata/blacklanturn-build.json'])['release_id'],'addons':hashes,'retained':retained}
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
        _write(archive,NAME,json.dumps(doc,sort_keys=True,separators=(',',':')))
        for name,raw in sorted(after.items()):
            parts=name.split('/')
            if len(parts)>=3 and parts[0]=='addons' and parts[1] in retained:continue
            _write(archive,name,raw)
    return doc

def is_component(path):
    with zipfile.ZipFile(path) as archive:return NAME in archive.namelist()

def installed_paths(home,aid):
    root=Path(home)/'addons'/aid
    if not root.is_dir() or root.is_symlink():raise ValueError('Component base add-on is unavailable')
    result={}
    for parent,dirs,names in os.walk(root,followlinks=False):
        dirs[:]=[d for d in dirs if d!='__pycache__']
        for name in dirs+names:
            path=Path(parent)/name
            if path.is_symlink():raise ValueError('Component base contains linked files')
        for name in names:
            if name.endswith(('.pyc','.pyo')):continue
            path=Path(parent)/name
            if not path.is_file():raise ValueError('Component base contains unsupported files')
            result[path.relative_to(root).as_posix()]=path
    return result

def installed_tree(home,aid):
    """Legacy tooling interface; runtime reconstruction uses paths and hashes."""
    return {name:path.read_bytes() for name,path in installed_paths(home,aid).items()}

def copy_entry(archive,name,source):
    info=zipfile.ZipInfo(name,(2026,10,16,0,0,0));info.compress_type=archive.compression;info.external_attr=0o100644<<16
    with archive.open(info,'w',force_zip64=True) as target:return stream_io.transfer(source,target)

def expand(path,home,directory):
    temporary=None
    try:
        with zipfile.ZipFile(path) as archive:
            validate(archive)
            if archive.getinfo(NAME).file_size>65536:raise ValueError('Component manifest exceeds limit')
            doc=json.loads(archive.read(NAME))
            if (not isinstance(doc,dict) or set(doc)!={'schema','base','target','addons','retained'} or doc['schema']!=1
                or not isinstance(doc['addons'],dict) or not isinstance(doc['retained'],dict) or len(doc['addons'])>256
                or not set(doc['retained']).issubset(doc['addons'])):raise ValueError('Invalid component manifest')
            if json.loads((Path(home)/'userdata/blacklanturn-build.json').read_bytes()).get('release_id')!=doc['base']:
                raise ValueError('Component base release differs; use the complete update')
            for aid,value in doc['addons'].items():
                if not ID.fullmatch(aid) or not isinstance(value,str) or not re.fullmatch(r'[a-f0-9]{64}',value):raise ValueError('Invalid component identity')
            names=[n for n in archive.namelist() if n!=NAME and not n.endswith('/')]
            marker='userdata/blacklanturn-build.json'
            if archive.getinfo(marker).file_size>32768:raise ValueError('Component target identity exceeds limit')
            if json.loads(archive.read(marker)).get('release_id')!=doc['target']:raise ValueError('Component target identity differs')
            incoming={n.split('/')[1] for n in names if n.startswith('addons/') and n.count('/')>=2}
            if incoming!=(set(doc['addons'])-set(doc['retained'])):raise ValueError('Component add-on set differs')
            retained={}
            # Reject a nonmatching local installation before reading payload data
            # or creating a reconstructed archive. Only names/hashes stay in RAM.
            candidates={aid:installed_paths(home,aid) for aid in doc['retained']}
            # Detect small changed add-ons before hashing large fonts/resources.
            for aid,files in sorted(candidates.items(),key=lambda pair:sum(p.stat().st_size for p in pair[1].values())):
                value=doc['retained'][aid]
                hashes={name:stream_io.file_hash(path) for name,path in files.items()}
                if value!=doc['addons'][aid] or digest_hashes(hashes)!=value:raise ValueError('Component base source differs; use the complete update')
                retained[aid]=files
            descriptor,temporary=tempfile.mkstemp(prefix='.BlackLanturn-components-',suffix='.zip',dir=directory);os.close(descriptor)
            actual={aid:{} for aid in doc['addons']}
            with zipfile.ZipFile(temporary,'w',zipfile.ZIP_STORED) as merged:
                for name in sorted(names):
                    with archive.open(name) as source:checksum=copy_entry(merged,name,source)
                    if name.startswith('addons/'):
                        _,aid,relative=name.split('/',2);actual[aid][relative]=checksum
                for aid,files in retained.items():
                    if set(installed_paths(home,aid))!=set(files):raise ValueError('Component base source changed during reconstruction')
                    for relative,path in sorted(files.items()):
                        if path.is_symlink() or not path.is_file():raise ValueError('Component source changed during reconstruction')
                        with path.open('rb') as source:actual[aid][relative]=copy_entry(merged,'addons/'+aid+'/'+relative,source)
                if any(digest_hashes(files)!=doc['addons'][aid] for aid,files in actual.items()):raise ValueError('Component source verification failed')
        return Path(temporary)
    except Exception:
        if temporary:
            try:os.unlink(temporary)
            except OSError:pass
        raise
