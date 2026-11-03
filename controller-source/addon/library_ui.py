"""Explicit local library actions using existing BlackLanturn native dialogs."""
import time,threading
from functools import wraps
from title_preferences import title_key

def owned(method):
    @wraps(method)
    def call(self,*args,**kwargs):
        import xbmcgui
        previous=getattr(self,'actions_open',False);self.actions_open=True
        self.input_generation=getattr(self,'input_generation',0)+1;self.dwell=time.monotonic()
        try:
            self.stop_preview();return method(self,*args,**kwargs)
        except (OSError,ValueError) as exc:xbmcgui.Dialog().ok('My library',str(exc))
        finally:self.actions_open=previous;self.dwell=time.monotonic()
    return call

class LibraryActions:
    def commit_library(self,value):
        previous=self.config;self.config=value
        try:
            if self.save(invalidate=False) is False:raise ValueError('Library could not be saved; original data was kept')
        except Exception:self.config=previous;raise
    def personal_rows(self):
        import personal_library as library
        return library.collection_rows(self.config)
    def hydrate_library_items(self,items):
        from local_watch import hydrate_local
        from live_review import PROFILE
        return hydrate_local(PROFILE/'addon_data/plugin.video.themoviedb.helper',items)
    @owned
    def add_to_collection(self,item):
        import personal_library as library
        import xbmcgui
        if not title_key(item):return
        while self.alive:
            records=library.collections(self.config);key=title_key(item)
            names=[('✓ ' if any(title_key(x)==key for x in c['items']) else '')+c['name'] for c in records]
            n=xbmcgui.Dialog().select('Collections for '+(item.get('label') or item.get('title','title')),names+['Create collection…'])
            if n<0:return
            if n==len(records):
                name=xbmcgui.Dialog().input('New collection name').strip()
                if not name:return
                updated=library.create_collection(self.config,name);ident=updated['PersonalCollections'][-1]['id']
                self.commit_library(library.membership(updated,ident,item,True))
            else:
                record=records[n];present=any(title_key(x)==key for x in record['items'])
                self.commit_library(library.membership(self.config,record['id'],item,not present))
    @owned
    def manage_collections(self):
        import personal_library as library
        import xbmcgui
        changed=False
        while self.alive:
            records=library.collections(self.config)
            n=xbmcgui.Dialog().select('Personal collections',[c['name']+' · '+str(len(c['items']))+' titles' for c in records]+['Create collection…'])
            if n<0:break
            if n==len(records):
                name=xbmcgui.Dialog().input('New collection name').strip()
                if not name:break
                self.commit_library(library.create_collection(self.config,name));changed=True;continue
            c=records[n];action=xbmcgui.Dialog().select(c['name'],['View titles','Rename','Move up','Move down','Remove a title…','Delete collection…'])
            if action<0:continue
            if action==0:
                self.open_discovery({'heading':'MY COLLECTIONS / '+c['name'],'rows':[{'id':'personal-'+c['id'],'label':c['name'],'path':'','local_items':c['items']}]});return
            if action==4:
                index=xbmcgui.Dialog().select('Remove from '+c['name'],[x.get('label') or x.get('title','Title') for x in c['items']])
                if index>=0:self.commit_library(library.membership(self.config,c['id'],c['items'][index],False));changed=True
                continue
            name=xbmcgui.Dialog().input('Collection name',defaultt=c['name']).strip() if action==1 else None
            if action==1 and not name:continue
            if action==5 and not xbmcgui.Dialog().yesno('Delete '+c['name']+'?','Only this collection is removed. Watched history, other collections and saved titles stay unchanged.'):continue
            self.commit_library(library.edit_collection(self.config,c['id'],{1:'rename',2:'up',3:'down',5:'delete'}[action],name));changed=True
        if changed and self.section=='My Stuff' and not getattr(self,'search_state',None):self.load_section()
    @owned
    def choose_saved_search(self):
        import personal_library as library
        import xbmcgui
        records=library.searches(self.config)
        if not records:return None
        n=xbmcgui.Dialog().select('Search',['New search…']+[x['name']+' · '+x['kind'].title() for x in records]+['Manage saved searches…'])
        if n<0:return False
        if n==0:return None
        if n==len(records)+1:self.manage_searches();return False
        record=records[n-1];return record['query'],library.KINDS.index(record['kind'])
    @owned
    def save_current_search(self):
        import personal_library as library
        import xbmcgui
        state=getattr(self,'search_state',None)
        if not state:return
        name=xbmcgui.Dialog().input('Name this saved search',defaultt=state['query']).strip()
        if not name:return
        self.commit_library(library.save_search(self.config,name,state['query'],state['kind']))
        xbmcgui.Dialog().notification('Saved searches','Saved on this device',time=2000)
    @owned
    def manage_searches(self):
        import personal_library as library
        import xbmcgui
        while self.alive:
            records=library.searches(self.config)
            if not records:xbmcgui.Dialog().ok('Saved searches','Run a search, then choose Options → Save this search.');return
            n=xbmcgui.Dialog().select('Saved searches',[x['name']+' · '+x['kind'].title() for x in records])
            if n<0:return
            record=records[n];choice=xbmcgui.Dialog().select(record['name'],['Search now','Rename','Delete saved search'])
            if choice==0:self.open_search(query=record['query'],position=library.KINDS.index(record['kind']));return
            if choice==1:
                name=xbmcgui.Dialog().input('Saved search name',defaultt=record['name']).strip()
                if name:self.commit_library(library.edit_search(self.config,record['id'],'rename',name))
            elif choice==2 and xbmcgui.Dialog().yesno('Delete saved search?','Remove only this saved search. Your titles and watched history stay unchanged.'):
                self.commit_library(library.edit_search(self.config,record['id'],'delete'))
    def open_movie_series(self,item):
        """Slow provider work stays off the native callback and cannot replace newer navigation."""
        from movie_series import collection_identity,release_order,load_series
        from live_review import PROFILE,tmdb,get_list
        import xbmcgui
        key=title_key(item)
        if not key or not key.startswith('movie:'):return
        generation=getattr(self,'generation',0);lifetime=getattr(self,'window_lifetime',None);input_generation=getattr(self,'input_generation',0)
        token=object();self.movie_series_request=token;selected=title_key(getattr(self,'selected',None))
        def current():return self.alive and self.movie_series_request is token and generation==getattr(self,'generation',0) and input_generation==getattr(self,'input_generation',0) and lifetime is getattr(self,'window_lifetime',None) and selected==title_key(getattr(self,'selected',None)) and not self.actions_open and not getattr(self,'settings_open',False)
        self.setProperty('notice','Finding movie series…')
        def work():
            try:
                if not current():return
                get_list(tmdb('details','movie',tmdb_id=key.split(':')[1]))
                if not current():return
                collection=collection_identity(PROFILE/'addon_data/plugin.video.themoviedb.helper',key.split(':')[1])
                if not collection:self.setProperty('notice','No movie series is listed for this title');return
                path=tmdb('collection','collection',tmdb_id=collection['id']);items=load_series(path,get_list,current)
                if not current():return
                ordered,nxt=release_order(self.hydrate_library_items(items))
                if not ordered:self.setProperty('notice','Movie series is unavailable; try again later');return
                self.open_discovery({'heading':'MOVIE SERIES / '+collection['name'],'rows':[{'label':'Release order'+(' · Next unwatched: '+(nxt.get('label') or nxt.get('title','Movie')) if nxt else ''),'path':'','local_items':ordered}]})
                if nxt:self.setProperty('notice','Next unwatched · '+(nxt.get('label') or nxt.get('title','Movie')))
            except Exception:
                if current():self.setProperty('notice','Movie series is unavailable; your browsing position was kept')
        threading.Thread(target=work,name='BlackLanturnMovieSeries',daemon=True).start()
    @owned
    def toggle_watch_tonight(self, item):
        import xbmcgui
        from watch_tonight import contains, item_key, toggle
        added = not contains(self.config, item_key(item))
        updated = toggle(self.config, item)
        self.commit_library(updated)
        xbmcgui.Dialog().notification('Watch Tonight', 'Added to your queue' if added else 'Removed from your queue', time=2200)

    @owned
    def open_next_watch_tonight(self):
        import xbmcgui
        from watch_tonight import entries
        items = entries(self.config)
        if items:
            self.details(items[0])
        else:
            xbmcgui.Dialog().ok('Watch Tonight', 'Choose Add to Watch Tonight in a movie or episode’s Options.')

    @owned
    def manage_watch_tonight(self):
        import xbmcgui
        from watch_tonight import edit, entries, item_key, label
        dialog = xbmcgui.Dialog()
        position = 0
        while self.alive:
            items = entries(self.config)
            if not items:
                dialog.ok('Watch Tonight', 'Choose Add to Watch Tonight in a movie or episode’s Options.')
                return
            labels = [f'{index + 1}. {label(item)}' for index, item in enumerate(items)]
            position = dialog.select('Watch Tonight', labels, preselect=min(position, len(items) - 1))
            if position < 0:
                return
            item = items[position]
            actions = [('open', 'Open details')]
            if position > 0:
                actions.append(('up', 'Move up'))
            if position + 1 < len(items):
                actions.append(('down', 'Move down'))
            actions.append(('remove', 'Remove from Watch Tonight'))
            choice = dialog.select(label(item), [caption for _, caption in actions])
            if choice < 0:
                continue
            action = actions[choice][0]
            if action == 'open':
                self.details(item)
                return
            self.commit_library(edit(self.config, item_key(item), action))
            position += {'up': -1, 'down': 1}.get(action, 0)

    def open_coming_up(self):
        from datetime import date
        import xbmcaddon
        import xbmcgui
        from coming_up import calendar_path, group_airings, load_airings
        from live_review import get_list

        notice = 'Loading upcoming Trakt air dates…'
        with self.preview_dispatch_lock:
            if not self.alive or self.actions_open or getattr(self, 'settings_open', False):
                return
            self.input_generation = getattr(self, 'input_generation', 0) + 1
            epoch = self.input_generation
            generation = getattr(self, 'generation', 0)
            lifetime = getattr(self, 'window_lifetime', None)
            self.dwell = time.monotonic()
            previous = self.getProperty('notice')
            prior = getattr(self, 'coming_up_request', None)
            request = (object(), prior[1] if prior and previous == notice else previous)
            self.coming_up_request = request
            self.stop_preview()
            self.setProperty('notice', notice)

        def current():
            return (self.alive and epoch == self.input_generation
                    and generation == getattr(self, 'generation', 0)
                    and lifetime is getattr(self, 'window_lifetime', None)
                    and self.coming_up_request is request
                    and not self.actions_open and not getattr(self, 'settings_open', False))

        def clear_notice():
            if self.alive and lifetime is getattr(self, 'window_lifetime', None) and self.coming_up_request is request:
                self.coming_up_request = None
                if self.getProperty('notice') == notice:
                    self.setProperty('notice', request[1])

        def provider(path):
            with self.list_lock:
                return get_list(path) if current() else []

        def work():
            if not current():
                with self.preview_dispatch_lock:
                    clear_notice()
                return
            groups = {}
            today = date.today()
            try:
                helper = xbmcaddon.Addon('plugin.video.themoviedb.helper')
                if not helper.getSetting('trakt_token').strip():
                    message = 'Connect Trakt in TMDb Helper settings to see your upcoming TV air dates.'
                else:
                    groups = group_airings(load_airings(calendar_path(), provider, current), today)
                    message = 'Trakt returned no air dates for the next seven days. Check the connection if you expected airings.'
            except Exception:
                message = 'Trakt air dates are unavailable. Try again later.'
            with self.preview_dispatch_lock:
                owns_request = current()
                clear_notice()
                if not owns_request:
                    return
                self.actions_open = True
            try:
                self.stop_preview()
                dialog = xbmcgui.Dialog()
                if groups:
                    self.show_coming_up(dialog, groups, today)
                else:
                    dialog.ok('Coming Up', message)
            finally:
                self.actions_open = False
                self.dwell = time.monotonic()

        threading.Thread(target=work, name='BlackLanturnComingUp', daemon=True).start()

    def show_coming_up(self, dialog, groups, today):
        from watch_tonight import label
        days = list(groups)
        labels = ['Date unknown' if day is None else
                  f"{'Today' if day == today else day.strftime('%A')} · {day.strftime('%b')} {day.day}"
                  for day in days]
        position = 0
        while self.alive:
            position = dialog.select('Coming Up · TV air dates only', labels, preselect=position)
            if position < 0:
                return
            items = groups[days[position]]
            selected = dialog.select(labels[position]+' · Streaming availability unknown', [label(item) for item in items])
            if selected >= 0 and self.alive:
                self.details(items[selected])
                return

    def library_title_actions(self,item):
        key=title_key(item)
        actions = [('library_add', 'Add to collection…')] if key else []
        if key and key.startswith('movie:'):
            actions.append(('movie_series', 'View movie series · release order'))
        from watch_tonight import contains, item_key
        queue_key = item_key(item)
        if queue_key:
            try:
                queued = contains(self.config, queue_key)
                label = 'Remove from Watch Tonight' if queued else 'Add to Watch Tonight'
            except ValueError:
                label = 'Watch Tonight…'
            actions.append(('watch_tonight_toggle', label))
        return actions
    def library_context_actions(self):
        actions=[]
        if getattr(self,'search_state',None):actions.append(('save_search','Save this search…'))
        if getattr(self,'section','')=='My Stuff':
            # The bundled Helper's personal calendar caches are shared across
            # Trakt accounts in the profile. Keep the picker private until scoped.
            actions.extend([('watch_tonight_next', 'Open next from Watch Tonight'), ('watch_tonight', 'Manage Watch Tonight…'),
                            ('collections','Personal collections…'), ('saved_searches','Saved searches…')])
        return actions
    def refresh_library_watch(self,fresh):
        import personal_library as library
        from playback_core import restored_position
        updated=library.refresh_watch(self.config,fresh)
        if updated!=self.config:self.commit_library(updated)
        key=title_key(fresh)
        if not key:return
        def replace(files):return [dict(x,**{k:fresh[k] for k in ('playcount','resume') if k in fresh}) if title_key(x)==key else x for x in files]
        for definition in getattr(self,'page_definitions',[]):
            if 'local_items' in definition:definition['local_items']=replace(definition['local_items'])
        for n,(path,files) in enumerate(zip(self.paths,self.rows)):
            if path or not any(title_key(x)==key for x in files):continue
            position=self.getControl(900+n).getSelectedPosition()
            self.apply_row(n,replace(files),self.row_labels.get(n,self.getProperty('row'+str(n))),position,update_selected=False)
        if self.getProperty('eyebrow').startswith('MOVIE SERIES / '):
            from movie_series import release_order
            _,nxt=release_order(self.page_definitions[0].get('local_items',[]))
            label='Release order'+(' · Next unwatched: '+(nxt.get('label') or nxt.get('title','Movie')) if nxt else '')
            self.page_definitions[0]['label']=label;self.row_labels[0]=label;self.setProperty('row0',label)
            self.setProperty('notice','Next unwatched · '+(nxt.get('label') or nxt.get('title','Movie')) if nxt else 'No confirmed unwatched release')
