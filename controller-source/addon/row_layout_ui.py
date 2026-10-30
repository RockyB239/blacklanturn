"""Remote-friendly local row controls, using BlackLanturn's existing dialogs."""
import time
from row_layout import row_key
SECTIONS=('Home','Movies','Shows','YouTube','My Stuff','Add-ons')
class RowCustomization:
    def row_layout_scope(self):
        section=getattr(self,'section','')
        if section not in SECTIONS or getattr(self,'mode','home')!='home':return None
        if any(getattr(self,k,None) is not None for k in ('search_state','episode_browser_context','person_context')) or getattr(self,'discovery_stack',[]):return None
        if section=='YouTube':
            tab=getattr(self,'youtube_tab','home')
            return 'YouTube/'+tab if tab in ('home','subscriptions','library','channels') else None
        return section if getattr(self,'active_page',None) is None else None
    def arrange_rows(self,definitions):
        scope=self.row_layout_scope()
        if scope:self.layout_raw_rows=list(definitions);self.layout_active_scope=scope
        store=getattr(self,'row_layouts',None)
        return store.rows(scope,definitions) if store is not None and scope else list(definitions)
    def append_layout_rows(self,rows):
        store=getattr(self,'row_layouts',None);scope=self.row_layout_scope()
        prior=list(getattr(self,'layout_raw_rows',self.page_definitions));known={row_key(r) for r in prior}
        prior.extend(r for r in rows if row_key(r) not in known);self.layout_raw_rows=prior
        current={row_key(r) for r in self.page_definitions}
        ordered=store.rows(scope,prior) if store is not None and scope else prior
        return [r for r in ordered if row_key(r) not in current]
    def refreshed_layout_catalog(self,definitions):
        store=getattr(self,'row_layouts',None);scope=self.row_layout_scope()
        ordered=store.rows(scope,definitions) if store is not None and scope else list(definitions)
        # Existing native controls retain their positions; changes below them
        # are available now, and saved order applies on the next section entry.
        prefix=list(self.page_definitions[:self.row_offset+2])
        kept={row_key(r) for r in prefix}
        available={row_key(r) for r in definitions}
        self.layout_raw_rows=list(definitions)+[r for r in prefix if row_key(r) not in available]
        return prefix+[r for r in ordered if row_key(r) not in kept],min(self.row_offset,max(0,len(prefix)-2))
    def customization_definitions(self,section,tab=None):
        from discovery_core import page_rows
        if section=='My Stuff':
            from live_core import my_stuff_rows
            from live_review import tmdb
            return my_stuff_rows(self.config['Saved'],tmdb)+getattr(self,'personal_rows',lambda:[])()
        if section=='YouTube':
            from youtube_core import tab_rows,account_options
            from youtube_browser import read_account_store
            tab=tab or 'home'
            if self.section=='YouTube' and getattr(self,'youtube_tab','')==tab:return list(getattr(self,'layout_raw_rows',self.page_definitions))
            if tab=='home':return self.saved_youtube_home()
            options={}
            if tab=='library':
                try:options=account_options(read_account_store())
                except (OSError,ValueError,TypeError):pass
            return tab_rows(tab,account=options)
        return page_rows(self.config,section)
    def customize_rows(self,current_only=False):
        import xbmcgui
        self.actions_open=True;self.input_generation=getattr(self,'input_generation',0)+1;self.dwell=time.monotonic();changed=False
        section=self.section;tab=getattr(self,'youtube_tab','home')
        try:
            self.stop_preview()
            if not current_only:
                selected=xbmcgui.Dialog().select('Customize rows for',list(SECTIONS),preselect=SECTIONS.index(section) if section in SECTIONS else 0)
                if selected<0:return
                section=SECTIONS[selected]
                if section=='YouTube':
                    tabs=('home','subscriptions','library','channels');choice=xbmcgui.Dialog().select('YouTube rows',['Home','Subscriptions','Library','Channels'])
                    if choice<0:return
                    tab=tabs[choice]
            scope='YouTube/'+tab if section=='YouTube' else section
            definitions=self.customization_definitions(section,tab);store=self.row_layouts;position=0
            while self.alive:
                rows=store.rows(scope,definitions,include_hidden=True)
                names=[]
                for row in rows:
                    hidden,pinned=store.flags(scope,row);names.append(row.get('label','Row')+('  ·  Pinned' if pinned else '')+('  ·  Hidden' if hidden else ''))
                chosen=xbmcgui.Dialog().select(section+(' · '+tab.title() if section=='YouTube' else '')+' rows',names+['Restore default arrangement'],preselect=min(position,len(names)))
                if chosen<0:break
                position=chosen
                try:
                    if chosen==len(rows):
                        if xbmcgui.Dialog().yesno('Restore default arrangement?','Reset row order, pins and hidden rows for this section. Your sources, accounts and saved titles stay unchanged.'):
                            store.reset(scope);changed=True
                        continue
                    row=rows[chosen];hidden,pinned=store.flags(scope,row)
                    choice=xbmcgui.Dialog().select(row.get('label','Row'),['Move up','Move down','Unpin row' if pinned else 'Pin to top','Show row' if hidden else 'Hide row'])
                    if choice<0:continue
                    action=('up','down','unpin' if pinned else 'pin','show' if hidden else 'hide')[choice]
                    if store.change(scope,definitions,row,action):changed=True
                    else:xbmcgui.Dialog().notification('Customize rows','Already at the edge of this pinned or unpinned group',time=2500)
                except (OSError,ValueError) as exc:xbmcgui.Dialog().ok('Customize rows',str(exc))
        finally:
            if changed and self.alive:
                if self.section=='YouTube':self.load_youtube_section(getattr(self,'youtube_tab','home'))
                else:self.load_section()
            self.dwell=time.monotonic();self.actions_open=False
