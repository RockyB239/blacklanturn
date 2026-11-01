"""Small, offline bridge for native Kodi menu artwork. Never writes preferences."""
from pathlib import Path
from icon_packs import icon_path,selected_pack
ROOT=Path(__file__).resolve().parent
NATIVE_ICONS={'filemanager':'files','addons':'addons','sysinfo':'tools','eventlog':'notifications','player':'continue-watching','media':'collections','livetv':'live-tv','network':'services','games':'games','interface':'pictures','profiles':'my-stuff','system':'settings','libreelec':'settings','updates':'updates','downloads':'downloads','search':'search'}
def publish_native_icons(config,window_factory=None):
 if window_factory is None:
  import xbmcgui
  window_factory=lambda:xbmcgui.Window(10000)
 window=window_factory();pack=selected_pack(config)
 for key,slug in NATIVE_ICONS.items():window.setProperty('BlackLanturn.Icon.'+key,icon_path(ROOT,slug,pack))
