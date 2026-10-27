"""Opt-in inline entry points owned by enabled, installed add-ons.

Descriptors and assets live in their owner's tree, never in managed host code.
No code is loaded until the user opens that add-on's root sidebar destination.
"""
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit,parse_qs
import importlib.util,json,re

def contained(root,relative):
    if not isinstance(relative,str) or not re.fullmatch(r'[A-Za-z0-9_./-]+',relative):return None
    part=PurePosixPath(relative)
    if part.is_absolute() or any(p in ('..','.') for p in part.parts):return None
    root=Path(root).resolve();target=root.joinpath(*part.parts)
    if target.is_symlink() or not target.resolve().is_relative_to(root):return None
    return target

def descriptor(root,name):
    try:
        target=contained(root,name)
        if target is None:return None
        with target.open('rb') as stream:raw=stream.read(65537)
        if len(raw)>65536:return None
        value=json.loads(raw)
        return value if isinstance(value,dict) and value.get('schema')==1 else None
    except (OSError,ValueError,TypeError,RecursionError):return None

def inline_request(path,resolve_owner):
    try:
        url=urlsplit(path)
        if url.scheme!='plugin' or url.path not in ('','/') or url.fragment or not re.fullmatch(r'[a-z0-9_.-]+',url.netloc):return None
        root=resolve_owner(url.netloc)
        if root is None:return None
        spec=descriptor(root,'blacklanturn-extension.json')
        inline=(spec or {}).get('inline',{})
        query=parse_qs(url.query,keep_blank_values=True)
        declared=inline.get('query',{})
        if query and (not isinstance(declared,dict) or query!={key:[value] for key,value in declared.items() if isinstance(key,str) and isinstance(value,str)}):return None
        entry=inline.get('entry')
        target=contained(root,entry)
        if target is None or target.suffix!='.py' or not target.is_file():return None
        return {'addon':url.netloc,'entry':entry}
    except (OSError,ValueError,TypeError,AttributeError):return None

def run_inline(request,resolve_owner):
    # Resolve/validate again after closing the host window: the owner may have
    # been disabled or replaced while that window was active.
    aid=request.get('addon','')
    checked=inline_request('plugin://'+aid+'/',resolve_owner)
    if checked!=request:return False
    target=contained(resolve_owner(aid),request['entry'])
    spec=importlib.util.spec_from_file_location('_blacklanturn_inline_'+aid.replace('.','_'),target)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return True
