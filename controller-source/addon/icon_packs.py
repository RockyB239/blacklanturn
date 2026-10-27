"""External, installed icon resources; preferences stay in the user's config."""
from copy import deepcopy
from pathlib import Path
import re
from itertools import islice
from extensions import contained,descriptor

DEFAULT_PACK='original'
PACK_CHOICES=[('original','Original')]
EXTRA_ICON_CHOICES=[]
_roots={}
_assets={}

def configure(owners):
    PACK_CHOICES[:]=[('original','Original')];EXTRA_ICON_CHOICES.clear();_roots.clear();_assets.clear()
    # Built-in packs do not depend on Kodi registering a new image addon.
    for root in [Path(__file__).resolve().parent/'resources/icon-packs', *owners]:
        doc=descriptor(root,'blacklanturn-icons.json') or {}
        packs=doc.get('packs',[]);icons=doc.get('icons',[])
        if not isinstance(packs,list) or not isinstance(icons,list):continue
        for pack in packs[:16]:
            if not isinstance(pack,dict):continue
            key=pack.get('id');label=pack.get('label');target=contained(root,pack.get('directory'))
            if (not isinstance(key,str) or not re.fullmatch(r'[a-z0-9-]{1,64}',key) or key in dict(PACK_CHOICES)
                or not isinstance(label,str) or not 0<len(label)<=80 or target is None or not target.is_dir()):continue
            # The approved directory is canonical; each accepted asset is one
            # filename component. Validate once, outside sidebar redraws.
            canonical=target.resolve();assets={}
            for asset in islice(canonical.iterdir(),256):
                if re.fullmatch(r'[a-z0-9-]+\.png',asset.name) and not asset.is_symlink() and asset.is_file():assets[asset.stem]=str(asset)
            _roots[key]=canonical;_assets[key]=assets;PACK_CHOICES.append((key,label))
        for pair in icons[:128]:
            if (isinstance(pair,list) and len(pair)==2 and isinstance(pair[0],str) and re.fullmatch(r'[a-z0-9-]{1,64}',pair[0])
                and isinstance(pair[1],str) and 0<len(pair[1])<=80 and pair[0] not in dict(EXTRA_ICON_CHOICES)):
                EXTRA_ICON_CHOICES.append(tuple(pair))

def selected_pack(config):
    value=config.get('IconPack')
    if value in dict(PACK_CHOICES):return value
    return PACK_CHOICES[1][0] if len(PACK_CHOICES)>1 else DEFAULT_PACK

def pack_label(config):return dict(PACK_CHOICES)[selected_pack(config)]

def with_pack(config,pack):
    if pack not in dict(PACK_CHOICES):raise ValueError('Unsupported icon pack')
    result=deepcopy(config);result['IconPack']=pack;return result

def icon_path(root,icon_id,pack=DEFAULT_PACK):
    root=Path(root);slug=icon_id if isinstance(icon_id,str) and re.fullmatch(r'[a-z0-9-]+',icon_id) else 'bookmark'
    media=root/'resources/media'
    if slug!='blacklanturn-lantern' and pack in _roots:
        target=_assets[pack].get(slug)
        if target is not None:return target
    legacy=media/(slug+'.png')
    return str(legacy if legacy.is_file() else media/'bookmark.png')
