"""Smaller downloads, reconstructed before the normal whole-tree validator.

Unchanged code must match exact reviewed hashes; changed add-ons are complete
trees. No binary diffs, profile defaults, or relaxed transaction protections.
"""
from pathlib import Path
import hashlib,importlib.util,json,os,re,tempfile,zipfile

NAME='userdata/blacklanturn-components.json'
ID=re.compile(r'[a-z0-9][a-z0-9_.-]{0,120}')

def digest(files):
    values={k:hashlib.sha256(v).hexdigest() for k,v in files.items()}
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

def installed_tree(home,aid):
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
            result[path.relative_to(root).as_posix()]=path.read_bytes()
    return result

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
            data={n:archive.read(n) for n in archive.namelist() if n!=NAME and not n.endswith('/')}
        if json.loads(data['userdata/blacklanturn-build.json']).get('release_id')!=doc['target']:raise ValueError('Component target identity differs')
        incoming=trees(data)
        if set(incoming)!=(set(doc['addons'])-set(doc['retained'])):raise ValueError('Component add-on set differs')
        for aid,value in doc['retained'].items():
            files=installed_tree(home,aid)
            if value!=doc['addons'][aid] or digest(files)!=value:raise ValueError('Component base source differs; use the complete update')
            incoming[aid]=files
            data.update({'addons/'+aid+'/'+name:raw for name,raw in files.items()})
        if any(digest(files)!=doc['addons'][aid] for aid,files in incoming.items()):raise ValueError('Component source verification failed')
        descriptor,temporary=tempfile.mkstemp(prefix='.BlackLanturn-components-',suffix='.zip',dir=directory);os.close(descriptor)
        with zipfile.ZipFile(temporary,'w',zipfile.ZIP_STORED) as merged:
            for name,raw in sorted(data.items()):merged.writestr(name,raw)
        return Path(temporary)
    except Exception:
        if temporary:
            try:os.unlink(temporary)
            except OSError:pass
        raise
