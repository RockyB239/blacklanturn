"""Read-only presentation artwork shared with the installed controller.

Fresh installs keep Installer artwork until a saved controller pack and its
corresponding installed asset exist. No controller code or settings are changed.
"""
import json
from pathlib import Path

PACKS=('sculpted-silver','smoked-glass')
ICONS={'home.png':'home','builds.png':'builds','updates.png':'updates',
       'maintenance-wrench.png':'maintenance','maintenance.png':'maintenance',
       'savedata.png':'backup','addoninstaller.png':'addons','apkinstaller.png':'program-addons',
       'settings.png':'settings','wizard.png':'builds','information.png':'guide',
       'keeplogin.png':'my-stuff','keeptrakt.png':'history','keepdebrid.png':'services',
       'speed.png':'services'}

class MenuArtwork:
    def __init__(self,config):
        self.media=Path(config.ADDON_PATH)/'resources/media'
        self.pack_root=None
        data=getattr(config,'ADDON_DATA',None)
        addons=getattr(config,'ADDONS',None)
        if not data or not addons:return
        try:
            saved=json.loads((Path(data)/'script.blacklanturn.preview/rows.json').read_text(encoding='utf-8'))
            pack=saved.get('IconPack') if isinstance(saved,dict) else None
        except (OSError,ValueError,TypeError):return
        if pack in PACKS:
            self.pack_root=Path(addons)/'script.blacklanturn.preview/resources/icon-packs/packs'/pack

    def icon(self,source):
        if not isinstance(source,str) or not source or '://' in source or self.pack_root is None:return source
        path=Path(source)
        # Real build/third-party art and the brand mark retain their identities.
        if path.parent!=self.media:return source
        slug=ICONS.get(path.name)
        if slug is None:return source
        target=self.pack_root/(slug+'.png')
        return str(target) if target.is_file() and not target.is_symlink() else source
