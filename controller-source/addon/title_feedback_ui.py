"""Local, reversible title feedback with the existing BlackLanturn controls."""
from pathlib import Path
import time
import xbmcgui
from title_preferences import title_key,discovery_scope,record_item
ROOT=Path(__file__).resolve().parent

class FeedbackUndo(xbmcgui.WindowXMLDialog):
    def onInit(self):
        self.undone=False
        for name in ('heading','message'):self.setProperty(name,getattr(self,name,''))
        self.setFocusId(901)
    def onClick(self,cid):
        if cid in (900,901):self.undone=cid==900;self.close()
    def onAction(self,action):
        if action.getId() in (9,10,92):self.close()

def offer_undo(heading,message):
    dialog=FeedbackUndo('FeedbackUndo.xml',str(ROOT),'Default','1080i')
    dialog.heading=heading;dialog.message=message;dialog.undone=False
    dialog.doModal();result=dialog.undone;del dialog;return result

class TitleFeedback:
    def title_feedback_actions(self,item):
        key=title_key(item);store=getattr(self,'title_preferences',None)
        if not key or store is None:return []
        kind='show' if key.startswith('tv:') else 'movie'
        state=store.state(item)
        if state=='hide':return [('title_restore','Unhide this '+kind)]
        if state=='less':return [('title_restore','Restore normal frequency'),('title_hide','Hide this '+kind)]
        return [('title_hide','Hide this '+kind),('title_less','Show this title less often')]
    def raw_title_row(self,n):
        raw=getattr(self,'title_raw_rows',{}).get(n)
        return raw[1] if raw and raw[0]==self.paths[n] else self.rows[n]
    def hydrate_title_row(self,n,files):
        from playback_core import item_key
        raw=getattr(self,'title_raw_rows',{}).get(n)
        if not raw or raw[0]!=self.paths[n]:return
        fresh={item_key(item):item for item in files};updated=[]
        for item in raw[1]:
            replacement=fresh.get(item_key(item))
            if replacement is None:updated.append(item);continue
            value={k:v for k,v in item.items() if k not in ('playcount','resume')}
            value.update({k:replacement[k] for k in ('playcount','resume') if k in replacement});updated.append(value)
        self.title_raw_rows[n]=(raw[0],updated)
    def prepare_title_row(self,n,files):
        if not hasattr(self,'title_raw_rows'):self.title_raw_rows={}
        self.title_raw_rows[n]=(self.paths[n],files)
        store=getattr(self,'title_preferences',None)
        result=store.apply(files,enabled=discovery_scope(self,self.paths[n])) if store is not None else files
        if not hasattr(self,'title_empty_rows'):self.title_empty_rows={}
        self.title_empty_rows[n]=bool(files and not result)
        return result
    def refresh_title_feedback(self):
        # Repaint just the two visible pages from original data. No cache clear,
        # provider calls, new page fetch, or watched-state write is needed.
        with self.preview_dispatch_lock:
            focus=self.getFocusId();last=getattr(self,'last_row',0)
            for n in range(2):
                raw=self.raw_title_row(n);old=self.rows[n];pos=self.getControl(900+n).getSelectedPosition()
                anchor=old[pos] if 0<=pos<len(old) else None
                from playback_core import restored_position
                position=restored_position(raw,anchor,pos)
                self.apply_row(n,raw,self.row_labels.get(n,''),position,update_selected=False)
            if self.mode=='details':
                raw=getattr(self,'title_related_raw',None)
                if raw is not None:
                    from browse_controls import page_cards
                    self.related,_=page_cards(self.title_preferences.apply(raw),self.related_history,self.related_path)
                    from live_review import media_item
                    control=self.getControl(3100);position=control.getSelectedPosition();control.reset();control.addItems([media_item(x) for x in self.related])
                    if self.related:control.selectItem(min(position,len(self.related)-1))
                    elif focus==3100:focus=101
            elif focus in (900,901,101,102,103,105,106):
                slot=focus-900 if focus in (900,901) else last
                if not self.rows[slot]:slot=1-slot
                if self.rows[slot]:
                    if focus in (900,901):focus=900+slot
                    pos=self.getControl(900+slot).getSelectedPosition();self.update(self.rows[slot][max(0,min(pos,len(self.rows[slot])-1))])
                else:
                    self.selected=None;self.setProperty('hasSelection','false');self.setProperty('notice','Titles hidden by your choices · Settings → Recommendations to restore')
                    focus=50;self.set_nav(True,pending_focus=True)
            self.setFocusId(focus);self.focus_key=None
    def change_title_feedback(self,item,action):
        self.actions_open=True
        self.input_generation=getattr(self,'input_generation',0)+1;self.dwell=time.monotonic()
        try:
            self.stop_preview()
            state=self.title_preferences.state(item)
            prior=next((dict((k,v) for k,v in r.items() if k!='key') for r in self.title_preferences.entries(state) if r['key']==title_key(item)),None)
            with self.preview_dispatch_lock:
                if action=='title_restore':
                    self.title_preferences.restore(item);heading='Title restored';message='This title is eligible for normal recommendations again.'
                else:
                    self.title_preferences.set(item,'hide' if action=='title_hide' else 'less')
                    heading='Title hidden' if action=='title_hide' else 'You’ll see this title less often'
                    message='Only this title is affected. Search, My Stuff and watch progress remain available.' if action=='title_hide' else 'Only this title is affected. Eligible in roughly one in four new Kodi sessions. Your genres stay unchanged.'
                self.refresh_title_feedback()
            if offer_undo(heading,message):
                with self.preview_dispatch_lock:
                    self.title_preferences.restore(item,prior);self.refresh_title_feedback()
        except (OSError,ValueError):
            xbmcgui.Dialog().ok('BlackLanturn','This choice could not be saved. Existing title preferences and your accounts are unchanged.')
        finally:self.dwell=time.monotonic();self.actions_open=False
    def manage_title_feedback(self,mode):
        title='Hidden titles' if mode=='hide' else 'Reduced titles'
        while self.alive:
            rows=self.title_preferences.entries(mode)
            if not rows:
                xbmcgui.Dialog().ok(title,'No titles in this list.');return
            labels=[r['label']+'  ·  '+('Show' if r['key'].startswith('tv:') else 'Movie') for r in rows]
            chosen=xbmcgui.Dialog().select(title+' · Select to '+('unhide' if mode=='hide' else 'restore normal frequency'),labels)
            if chosen<0:return
            self.change_title_feedback(record_item(rows[chosen]),'title_restore')
