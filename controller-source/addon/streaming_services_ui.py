"""Remote-first service chooser. Returns one original catalog card or None."""
from pathlib import Path
import threading

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
REGION = 5008
RETRY = 5009
CONTEXT_MENU = 117
BACK = (9, 10, 92, 216, 247)
TABS = {FEATURED: 'featured', PINNED: 'pinned', ALL: 'all'}
FALLBACK = str(Path(__file__).resolve().parent / 'resources/media/services.png')


class StreamingServicesGrid(xbmcgui.WindowXMLDialog):
    def onInit(self):
        self.result = None
        self.catalog_input = False
        self.lookahead_input = False
        self.closed_for_catalog = threading.Event()
        self.catalog_lock = threading.RLock()
        self.tab = FEATURED
        self.page = 0
        self.manage = False
        self.setProperty('pinMode', '')
        self.setProperty('pinButtonLabel', 'Manage pins')
        self.setProperty('pinNotice', '')
        load = getattr(self, 'load_catalog', None)
        self.setProperty('catalogStatus', 'Loading services…' if load else '')
        self.show_catalog(self.catalog)
        if getattr(self, 'region_store', None):
            self.setProperty('regional', 'true')
            self.switch_region(self.catalog_region, initial=True)
        if load:
            load(self.catalog_loaded, lambda: not self.closed_for_catalog.is_set())
        if getattr(self,'observe',None):
            def watch_focus():
                keys=['System.CurrentControlId','Container(5000).ListItem.Property(streamingLookaheadPath)']
                while not self.closed_for_catalog.wait(.1):
                    try:
                        state=self.read_labels(keys)
                        if self.closed_for_catalog.is_set():return
                        path=state[keys[1]] if state[keys[0]]==str(GRID) and self.lookahead_input and not self.manage and not getattr(self,'lookahead_paused',False) else ''
                        self.observe(path)
                    except (RuntimeError,KeyError):
                        return
            threading.Thread(target=watch_focus,name='BlackLanturnServiceFocus',daemon=True).start()

    def show_catalog(self, catalog, *, focus=True):
        self.catalog = catalog
        code = getattr(self, 'catalog_region', None)
        region = self.region_label(code) if code else ' / '.join(sorted({service.region for service in catalog.services.values()}))
        self.setProperty('region', region)
        if code:
            self.setProperty('regionButtonLabel', 'Region · ' + region)
        self.setProperty('featuredSource', catalog.featured_source if catalog.services else '')
        initial_key = service_key(getattr(self, 'initial_card', None)) if focus else None
        if initial_key in catalog.services:
            if all(service.key != initial_key for service in catalog.entries('featured', self.pins.keys)):
                self.tab = ALL
        self.show_page(initial_key, focus=focus)

    def catalog_loaded(self, cards):
        catalog = ServiceCatalog(cards)
        with self.catalog_lock:
            if self.closed_for_catalog.is_set():
                return
            self.setProperty('catalogStatus', '' if catalog.services else 'Services unavailable. Reopen to try again.')
            self.show_catalog(catalog, focus=not self.catalog_input)

    def region_label(self, code):
        return getattr(self, 'region_names', {}).get(code, code)

    def choose_region(self):
        self.lookahead_paused = True
        if getattr(self, 'observe', None):
            self.observe('')
        try:
            names, _ = self.region_store.regions()
            if not names:
                xbmcgui.Dialog().notification('Streaming services', 'Regions could not load. Try again.')
                return
            self.region_names = names
            entries = sorted(names, key=lambda code: names[code].casefold())
            target = self.requested_region
            choice = xbmcgui.Dialog().select('Streaming region · TMDb / JustWatch',
                [names[code] for code in entries], preselect=entries.index(target) if target in entries else 0)
            if 0 <= choice < len(entries):
                self.switch_region(entries[choice])
            else:
                with self.catalog_lock:
                    self.setProperty('region', self.region_label(self.catalog_region))
                    self.setProperty('regionButtonLabel', 'Region · ' + self.region_label(self.catalog_region))
        finally:
            self.lookahead_paused = False

    def switch_region(self, code, *, initial=False, force=False):
        with self.catalog_lock:
            self.requested_region = code
            token = self.region_request = object()
            label = self.region_label(code)
            visible_label = self.region_label(self.catalog_region)
            self.setProperty('region', visible_label)
            self.setProperty('regionButtonLabel', 'Region · ' + visible_label)
            self.setProperty('retryRegion', '')
            self.setProperty('regionStatus', f'Loading {label}…')
            if getattr(self, 'observe', None):
                self.observe('')
            self.lookahead_input = False

            def current():
                return self.region_request is token and not self.closed_for_catalog.is_set()

            def receive(cards, state):
                with self.catalog_lock:
                    if not current():
                        return
                    if cards is None:
                        self.setProperty('regionStatus', f'Could not load {label}.')
                        self.setProperty('retryRegion', 'true')
                        if not self.catalog.services:
                            self.setProperty('catalogStatus', 'Services could not load.')
                        return
                    previous = self.catalog_region
                    index, service = self.selected_service()
                    anchor = service.key if service and previous == code else None
                    self.catalog_region = code
                    self.catalog = ServiceCatalog(self.region_store.visible(cards, self.media_kind, code))
                    self.setProperty('region', label)
                    self.setProperty('regionButtonLabel', 'Region · ' + label)
                    self.setProperty('featuredSource', self.catalog.featured_source if self.catalog.services else '')
                    self.setProperty('catalogStatus', '' if self.catalog.services else
                                     f'No streaming services for this section in {label}.')
                    if state in ('stale', 'cached'):
                        self.setProperty('regionStatus', 'Saved results · Retry to refresh' if state == 'stale' else f'Checking {label}…')
                        self.setProperty('retryRegion', 'true' if state == 'stale' else '')
                    else:
                        self.setProperty('regionStatus', '')
                        self.setProperty('retryRegion', '')
                    if previous != code:
                        self.page = 0
                        self.manage = False
                        self.setProperty('pinMode', '')
                        self.setProperty('pinButtonLabel', 'Manage pins')
                        self.setProperty('pinNotice', '')
                    if initial and not self.catalog_input:
                        self.show_catalog(self.catalog)
                    else:
                        focus = self.getFocusId()
                        self.show_page(anchor, index if anchor else 0, focus=False)
                        if focus == GRID and not self.visible_services:
                            self.setFocusId(self.tab)
                        elif focus == RETRY and state == 'fresh':
                            self.setFocusId(REGION)
                    if not initial and (previous != code or self.region_store.selected('') != code) and not self.region_store.select(code):
                        self.setProperty('regionStatus', 'Could not save this region for next time.')

            saved, fresh = self.region_store.cached(self.media_kind, code)
            if saved is not None:
                receive(saved, 'fresh' if fresh and not force else 'cached')
            if force or not fresh:
                self.request_catalog(code, receive, current)

    def dismiss(self):
        with self.catalog_lock:
            self.closed_for_catalog.set()
        self.close()

    def show_page(self, keep_key=None, index=0, *, focus=True):
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
            tile.setProperty('streamingServiceKey', service.key)
            tile.setProperty('pinned', 'true' if service.key in pin_keys else '')
            if getattr(self,'observe',None):tile.setProperty('streamingLookaheadPath',service.card.get('file',''))
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
        if focus:self.setFocusId(GRID if tiles else self.tab)

    def selected_service(self, *, rendered=False):
        index = self.getControl(GRID).getSelectedPosition()
        if not 0 <= index < len(self.visible_services):
            return 0, None
        service = self.visible_services[index]
        labels = getattr(self, 'read_labels', None)
        if rendered and labels:
            key = f'Container({GRID}).ListItem.Property(streamingServiceKey)'
            if labels([key]).get(key) != service.key:
                return 0, None
        return index, service

    def toggle_pin(self, service, index):
        try:
            pinned = self.pins.toggle(service.key)
        except (OSError, ValueError):
            self.setProperty('pinNotice', 'Could not save streaming service pins.')
            return
        self.setProperty('pinNotice', f'{service.name} ' + ('pinned.' if pinned else 'unpinned.'))
        self.show_page(service.key, index)

    def onClick(self, control):
        self.catalog_input = True
        if control == CANCEL:
            self.dismiss()
            return
        if control == REGION:
            self.choose_region()
            return
        if control == RETRY:
            self.switch_region(self.requested_region, force=True)
            return
        selection = None
        with self.catalog_lock:
            if control in TABS:
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
                index, service = self.selected_service(rendered=True)
                if service is None:
                    return
                if self.manage:
                    self.toggle_pin(service, index)
                else:
                    selection = service.card
        if selection is not None:
            self.result = selection
            self.dismiss()

    def onAction(self, action):
        self.catalog_input = True
        action_id = action.getId()
        if action_id in (1,2,3,4) and self.getFocusId()==GRID:
            self.lookahead_input=True
            if getattr(self,'observe',None):self.observe('')
        if action_id in BACK:
            self.dismiss()
        elif action_id == CONTEXT_MENU and self.getFocusId() == GRID:
            index, service = self.selected_service(rendered=True)
            if service is None:
                return
            command = 'Unpin' if service.key in self.pins.keys else 'Pin'
            self.lookahead_paused=True
            if getattr(self,'observe',None):self.observe('')
            try:
                if xbmcgui.Dialog().contextmenu([f'{command} {service.name}']) == 0:
                    self.toggle_pin(service, index)
            finally:
                self.lookahead_paused=False


def choose_streaming_service(root, profile, cards, initial_card=None, load=None, observe=None, read_labels=None,
                             *, region_store=None, media_kind=None, region=None, request_catalog=None):
    catalog = ServiceCatalog(cards or [])
    if not catalog.services and load is None and region_store is None:
        return None
    dialog = StreamingServicesGrid('StreamingServicesGrid.xml', str(root), 'Default', '1080i')
    dialog.catalog = catalog
    dialog.pins = ServicePins(profile)
    dialog.initial_card = initial_card
    dialog.load_catalog = load
    dialog.result = None
    dialog.observe=observe
    dialog.read_labels=read_labels
    if region_store is not None:
        dialog.region_store = region_store
        dialog.media_kind = media_kind
        dialog.catalog_region = dialog.requested_region = region
        from regional_catalog import helper_region_names
        names, _ = region_store.cached_regions()
        dialog.region_names = {**helper_region_names(), **names}
        dialog.request_catalog = request_catalog
    try:
        dialog.doModal()
        return dialog.result
    finally:
        if hasattr(dialog, 'closed_for_catalog'):
            dialog.closed_for_catalog.set()
