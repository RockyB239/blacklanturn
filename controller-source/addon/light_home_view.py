"""Persistent native Home: show validated saved cards before importing features."""
import json,time,threading
from pathlib import Path
import xbmc,xbmcgui,xbmcvfs,xbmcaddon
from light_home_state import EarlyIntent
from light_home_adapter import ControllerAdapter

ROOT=Path(__file__).resolve().parent
STORE=Path(xbmcvfs.translatePath(xbmcaddon.Addon('script.blacklanturn.preview').getAddonInfo('profile')))


class LightweightHome(xbmcgui.WindowXML):
    def onInit(self):
        previous=getattr(self,'controller',None)
        if previous is not None:
            previous.onInit();return
        self._alive=True;self._epoch=object();self._intent=EarlyIntent();self.controller=None;self._imported=None;self._import_error=None;self._attaching=False
        self._owner_skin=xbmc.getSkinDir();self._window_id=xbmcgui.getCurrentWindowId()
        self._early=getattr(self,'early_home',None) if not (getattr(self,'resume_backend',None) or getattr(self,'resume_playback',None)) else None
        self._early_rows=[];self._selected=None;self._last_row=0;self._nav=False
        if self._early:
            try:self._paint_home()
            except Exception:self._early=None
        if not self._early:self.setProperty('loading','true');self.setProperty('loadingStatus','Starting BlackLanturn…')
        epoch=self._epoch
        def load():
            if not self._alive or self._epoch is not epoch:return
            try:
                from live_review import LiveReview,initialize_addons
                if not self._alive or self._epoch is not epoch:return
                initialize_addons()
                ready=LiveReview
            except Exception as exc:
                ready=None;self._import_error=exc
            if not self._alive or self._epoch is not epoch:return
            self._imported=ready
            # Kodi delivers GUI_MSG_CLICKED to this retained window's callback;
            # the worker only imports Python and posts a native GUI message.
            xbmc.executebuiltin('SendClick(%d,5)'%self._window_id)
        threading.Thread(target=load,name='BlackLanturnControllerImport',daemon=True).start()
    def _paint_home(self):
        from light_home_cards import media_item
        from browse_controls import page_cards
        from live_core import PageHistory
        record=self._early['record'];prefs=self._early['preferences']
        for key,value in record['properties'].items():self.setProperty(key,value)
        startup=getattr(self,'startup_home',None)
        if startup:self.setProperty('startupOwner',startup.owner)
        self.setProperty('nav','closed')
        self._heroes={};self._early_rows=[]
        for n,row in enumerate(record['rows']):
            files=prefs.apply(row['items']);files,_=page_cards(files,PageHistory(),row['path'])
            if not files:raise ValueError('Saved Home has no visible titles')
            self._early_rows.append(files)
            self._heroes.update((item['file'],hero) for item,hero in zip(row['items'],row['heroes']))
            control=self.getControl(900+n);control.setHeight(276);control.reset();control.addItems([media_item(item) for item in files]);control.setVisible(True);control.selectItem(0)
            self.setProperty('row'+str(n),row['label']);self.setProperty('rowState'+str(n),'ready');self.setProperty('rowMessage'+str(n),'')
        sidebar=self.getControl(50);sidebar.reset();items=[]
        for entry in record['sidebar']:
            item=xbmcgui.ListItem(label=entry['label']);item.setArt({'icon':entry['icon']});item.setProperty('active','true' if entry['id']=='home' else 'false');items.append(item)
        sidebar.setHeight(864);sidebar.addItems(items);sidebar.setVisible(True);sidebar.selectItem(next(i for i,e in enumerate(record['sidebar']) if e['id']=='home'));sidebar.controlUp(sidebar);sidebar.controlDown(sidebar)
        for cid in (10,50,15):self.getControl(cid).setWidth(82)
        for cid in (101,600,900,901,3000,3100):self.getControl(cid).controlLeft(sidebar)
        self.getControl(900).controlUp(self.getControl(101));self.getControl(900).controlDown(self.getControl(901));self.getControl(901).controlUp(self.getControl(900));self.getControl(901).controlDown(self.getControl(901))
        for cid in (101,102,103,105,106):self.getControl(cid).controlDown(self.getControl(900))
        self.getControl(5).controlRight(self.getControl(900));self.getControl(5).controlDown(self.getControl(900))
        self._show_item(self._early_rows[0][0]);self.setFocusId(5)
        self.setProperty('lightHome','painted')
    def _show_item(self,item):
        hero=self._heroes.get(item.get('file'))
        if not hero:return
        self._selected=item
        for key,value in hero['properties'].items():self.setProperty(key,value)
        self.setProperty('allEpisodes','false')
        self.getControl(101).setLabel(hero['play']);self.getControl(103).setLabel(hero['saved']);self.getControl(251).setHeight(hero['height'])
        from youtube_core import automatic_preview
        cfg=self._early['config'];mode=cfg.get('PreviewMode','manual')
        manual=not automatic_preview(cfg,'Home',mode) and self._early['record']['properties']['previewsReady']=='true'
        self.getControl(101).controlRight(self.getControl(102));self.getControl(103).controlLeft(self.getControl(102));self.getControl(103).controlRight(self.getControl(105 if manual else 103));self.getControl(105).controlLeft(self.getControl(103));self.getControl(105).controlRight(self.getControl(105))
    def _sync_selection(self):
        if not self._early:return
        focus=self.getFocusId()
        if focus!=5:self.setProperty('startupIdle','false')
        if focus in (900,901):
            n=focus-900;pos=self.getControl(focus).getSelectedPosition()
            if 0<=pos<len(self._early_rows[n]):self._last_row=n;self._show_item(self._early_rows[n][pos])
        opened=focus in (10,50,15)
        if opened!=self._nav:
            self._nav=opened;self.setProperty('nav','open' if opened else 'closed')
            for cid in (10,50,15):self.getControl(cid).setWidth(350 if opened else 82)
    def _remember(self,kind,cid):
        self._sync_selection();key=(self._selected or {}).get('file','')
        if cid==50 and self._early:
            pos=self.getControl(50).getSelectedPosition();key=self._early['record']['sidebar'][pos]['id']
        self._intent.choose(kind,cid,key)
    def _attach(self):
        if self.controller or self._attaching or not self._alive:return
        if xbmc.getSkinDir()!=self._owner_skin:self.close();return
        if self._import_error:
            self.startup_error=type(self._import_error).__name__;self.close();return
        if self._imported is None:return
        self._attaching=True
        try:
            self._sync_selection()
            properties=dict(self._early['record']['properties']) if self._early else {}
            controller=ControllerAdapter(self._imported,self,properties)
            for name in ('resume_backend','resume_playback','startup_home'):setattr(controller,name,getattr(self,name,None))
            if not self._early:
                controller.adopt({});controller.defer_startup_workers=False;self.controller=controller;controller.onInit();return
            controller.onInit()
            if not controller.alive:self.close();return
            # A last-moment account/config change cannot adopt old cards.
            from light_home_model import display_scope,adoption_definitions
            cache=getattr(controller,'home_snapshot_cache',None)
            scope=display_scope(STORE,cache.scope if cache else None)
            definitions=adoption_definitions(controller.config,controller.arrange_rows,self._early['record'])
            if scope!=self._early['record']['scope'] or definitions is None:
                self._intent.cancel();controller.adopt({});self.controller=controller;controller.defer_startup_workers=False;controller.onInit();return
            from live_core import PageHistory
            rows=self._early['record']['rows'];paths=[row['path'] for row in rows]
            state=dict(rows=self._early_rows,paths=paths,histories=[PageHistory(),PageHistory()],selected=self._selected,last_row=self._last_row,return_focus=900+self._last_row,page_definitions=definitions,row_offset=0,row_cache={},window_ready=[True,True],row_labels={n:row['label'] for n,row in enumerate(rows)},row_states={0:'ready',1:'ready'},snapshot_rows={0:True,1:True},startup_idle=self.getFocusId()==5,nav=self._nav,nav_width_requested=350 if self._nav else 82,nav_width_applied=350 if self._nav else 82,title_preferences=self._early['preferences'],title_raw_rows={n:(paths[n],rows[n]['items']) for n in range(2)},title_empty_rows={},focus_key=(self.getFocusId(),self.getControl(self.getFocusId()).getSelectedPosition() if self.getFocusId() in (900,901) else 0))
            controller.adopt(state);controller.defer_startup_workers=False;self.controller=controller;controller.row_navigation()
            self.setProperty('lightHome','attached')
            adopted_generation=controller.generation;adopted_paths=tuple(controller.paths);adopted_definitions=[dict(row) for row in controller.page_definitions[:2]]
            intent=self._intent.take()
            if intent:
                kind,cid,key=intent
                if cid==50:
                    position=next((i for i,e in enumerate(controller.navigation_items) if e['id']==key),None)
                    if position is not None:controller.dispatch_navigation(controller.navigation_items[position])
                else:
                    selected=next(((n,p,item) for n,row in enumerate(controller.rows) for p,item in enumerate(row) if item.get('file')==key),None)
                    if selected:
                        n,p,item=selected;controller.last_row=n;controller.selected=item
                        controller.dispatch_choice(kind,cid,item)
            if not controller.alive:return
            lifetime=controller.window_lifetime
            def start():
                try:
                    if not controller.alive or controller.window_lifetime is not lifetime or controller.generation!=adopted_generation or tuple(controller.paths)!=adopted_paths or controller.section!='Home':return
                    pending=[(n,dict(row,_snapshot_refresh=True)) for n,row in enumerate(adopted_definitions)]
                    controller.request_row_loads(pending)
                except Exception as exc:
                    from live_review import event
                    event('light_home_setup_error',error_type=type(exc).__name__)
            threading.Thread(target=start,name='BlackLanturnHomeRefresh',daemon=True).start()
            threading.Thread(target=lambda:controller.monitor(lifetime),name='BlackLanturnLiveFocus',daemon=True).start()
        except Exception as exc:
            self.startup_error=type(exc).__name__
            if 'controller' in locals():controller.retire()
            self.close()
        finally:self._attaching=False
    def onClick(self,cid):
        if not getattr(self,'_alive',False):return
        if cid==5 and (self._imported is not None or self._import_error is not None):self._attach();return
        if self.controller:return self.controller.onClick(cid)
        self._remember('click',cid)
    def onAction(self,action):
        if not getattr(self,'_alive',False):return
        if self.controller:return self.controller.onAction(action)
        aid=action.getId()
        if aid in (9,10,92):
            self._intent.cancel();self.setFocusId(50);self._sync_selection();return
        if aid in (117,101):self._remember('context',self.getFocusId());return
        if aid==2 and self._nav:self.setFocusId(900+self._last_row)
        self._sync_selection()
    def close(self):
        self._alive=False
        if hasattr(self,'_intent'):self._intent.retire()
        if self.controller:self.controller.alive=False
        return super().close()
    def dispose(self):
        self._alive=False
        if hasattr(self,'_intent'):self._intent.retire()
        if getattr(self,'controller',None):self.controller.retire()
        self.controller=None;self._early=None;self._early_rows=[];self._imported=None
