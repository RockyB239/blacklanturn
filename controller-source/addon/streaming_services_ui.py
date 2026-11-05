"""Remote-first service chooser. Returns one original catalog card or None."""
from pathlib import Path

import xbmcgui

from streaming_services import PAGE_SIZE, ServiceCatalog, ServicePins, service_key

GRID = 5000
FEATURED = 5001
PINNED = 5002
ALL = 5003
PREVIOUS = 5004
NEXT = 5005
MANAGE = 5006
CANCEL = 5007
CONTEXT_MENU = 117
BACK = (9, 10, 92, 216, 247)
TABS = {FEATURED: 'featured', PINNED: 'pinned', ALL: 'all'}
FALLBACK = str(Path(__file__).resolve().parent / 'resources/media/services.png')


class StreamingServicesGrid(xbmcgui.WindowXMLDialog):
    def onInit(self):
        self.result = None
        self.tab = FEATURED
        self.page = 0
        self.manage = False
        self.setProperty('region', ' / '.join(sorted({service.region for service in self.catalog.services.values()})))
        self.setProperty('pinMode', '')
        self.setProperty('pinButtonLabel', 'Manage pins')
        self.setProperty('pinNotice', '')
        self.setProperty('featuredSource', self.catalog.featured_source)
        initial_key = service_key(getattr(self, 'initial_card', None))
        if initial_key in self.catalog.services:
            if all(service.key != initial_key for service in self.catalog.entries('featured', self.pins.keys)):
                self.tab = ALL
        self.show_page(initial_key)

    def show_page(self, keep_key=None, index=0):
        entries = self.catalog.entries(TABS[self.tab], self.pins.keys)
        pages = max(1, (len(entries) + PAGE_SIZE - 1) // PAGE_SIZE)
        self.page = min(max(0, self.page), pages - 1)
        if keep_key:
            absolute = next((n for n, service in enumerate(entries) if service.key == keep_key), None)
            if absolute is not None:
                self.page, index = divmod(absolute, PAGE_SIZE)
        start = self.page * PAGE_SIZE
        self.visible_services = entries[start:start + PAGE_SIZE]
        pin_keys = set(self.pins.keys)
        tiles = []
        for service in self.visible_services:
            art = service.card.get('art') or {}
            logo = art.get('icon') or art.get('thumb') or service.card.get('thumbnail') or FALLBACK
            tile = xbmcgui.ListItem(label=service.name)
            tile.setArt({'icon': logo})
            tile.setProperty('pinned', 'true' if service.key in pin_keys else '')
            tiles.append(tile)
        self.setProperty('activeTab', TABS[self.tab])
        self.setProperty('gridAvailable', 'true' if tiles else '')
        self.setProperty('previousPage', 'true' if self.page > 0 else '')
        self.setProperty('nextPage', 'true' if self.page + 1 < pages else '')
        self.setProperty('pageSummary', f'{start + 1}–{start + len(tiles)} of {len(entries)}' if entries else '')
        panel = self.getControl(GRID)
        panel.reset()
        if tiles:
            panel.addItems(tiles)
            panel.selectItem(min(index, len(tiles) - 1))
        self.setFocusId(GRID if tiles else self.tab)

    def selected_service(self):
        index = self.getControl(GRID).getSelectedPosition()
        if 0 <= index < len(self.visible_services):
            return index, self.visible_services[index]
        return 0, None

    def toggle_pin(self, service, index):
        try:
            pinned = self.pins.toggle(service.key)
        except (OSError, ValueError):
            self.setProperty('pinNotice', 'Could not save streaming service pins.')
            return
        self.setProperty('pinNotice', f'{service.name} ' + ('pinned.' if pinned else 'unpinned.'))
        self.show_page(service.key, index)

    def onClick(self, control):
        if control == CANCEL:
            self.close()
        elif control in TABS:
            self.tab = control
            self.page = 0
            self.setProperty('pinNotice', '')
            self.show_page()
        elif control in (PREVIOUS, NEXT):
            self.page += -1 if control == PREVIOUS else 1
            self.setProperty('pinNotice', '')
            self.show_page()
        elif control == MANAGE:
            self.manage = not self.manage
            self.setProperty('pinMode', 'true' if self.manage else '')
            self.setProperty('pinButtonLabel', 'Done pinning' if self.manage else 'Manage pins')
            self.setProperty('pinNotice', '')
            self.setFocusId(GRID if self.visible_services else self.tab)
        elif control == GRID:
            index, service = self.selected_service()
            if service is None:
                return
            if self.manage:
                self.toggle_pin(service, index)
            else:
                self.result = service.card
                self.close()

    def onAction(self, action):
        action_id = action.getId()
        if action_id in BACK:
            self.close()
        elif action_id == CONTEXT_MENU and self.getFocusId() == GRID:
            index, service = self.selected_service()
            if service is None:
                return
            command = 'Unpin' if service.key in self.pins.keys else 'Pin'
            if xbmcgui.Dialog().contextmenu([f'{command} {service.name}']) == 0:
                self.toggle_pin(service, index)


def choose_streaming_service(root, profile, cards, initial_card=None):
    catalog = ServiceCatalog(cards)
    if not catalog.services:
        return None
    dialog = StreamingServicesGrid('StreamingServicesGrid.xml', str(root), 'Default', '1080i')
    dialog.catalog = catalog
    dialog.pins = ServicePins(profile)
    dialog.initial_card = initial_card
    dialog.result = None
    dialog.doModal()
    return dialog.result
