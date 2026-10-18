import sys,unittest
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
from types import SimpleNamespace,MethodType
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
from test_window_lifecycle import extract,ROOT

class SearchUI(unittest.TestCase):
    def test_mouse_hover_keeps_hero_buttons_stationary_but_remote_reveals_hero(self):
        for focus in (101,102,103,105,106,600):
            for mouse in (True,False):
                props={'scroll':'credits'}
                obj=SimpleNamespace(alive=True,owner_skin='test',settings_open=False,actions_open=False,mode='home',row_offset=0,section='Home',
                    nav=False,sync_nav_focus=lambda focus:None,apply_nav_width=lambda:None,focus_key=None,mouse=mouse,preview_mode='manual',dwell=100,owned_preview=False,preview_attempts=None,preview_generation=0,
                    getFocusId=lambda:focus,getProperty=lambda k:props.get(k,''),
                    setProperty=lambda k,v:props.__setitem__(k,v),hover=SimpleNamespace(tick=lambda *a:None))
                namespace={'xbmc':SimpleNamespace(Monitor=lambda:SimpleNamespace(abortRequested=lambda:False),getSkinDir=lambda:'test'),
                    'time':SimpleNamespace(monotonic=lambda:0,sleep=lambda n:setattr(obj,'alive',False))}
                extract(ROOT/'live_review.py','monitor',namespace,'LiveReview')(obj)
                self.assertEqual(props['scroll'],'credits' if mouse else 'top',f'focus={focus}, mouse={mouse}')
    def test_background_preview_does_not_capture_mouse_clicks(self):
        import xml.etree.ElementTree as E
        xml=E.parse(Path(__file__).parents[1]/'addon/resources/skins/Default/1080i/LiveReview.xml')
        video=xml.find(".//control[@type='videowindow']")
        self.assertEqual((video.findtext('width'),video.findtext('height')),('1800','810'))
        hitrect=video.find('hitrect')
        self.assertIsNotNone(hitrect,'Background preview must not open fullscreen on a mouse click')
        self.assertEqual((hitrect.get('w'),hitrect.get('h')),('0','0'))
        self.assertEqual((hitrect.get('x'),hitrect.get('y')),('-1','-1'))
    def test_people_and_collection_heroes_do_not_claim_an_unwatched_status(self):
        import re
        import xml.etree.ElementTree as E
        xml=E.parse(Path(__file__).parents[1]/'addon/resources/skins/Default/1080i/LiveReview.xml')
        condition=next(c for c in xml.findall('.//control') if c.findtext('label')=='$INFO[Window.Property(watchMeta)]').findtext('visible')
        for browsable,expected in [('true',False),('false',True)]:
            expression=condition.replace('String.IsEmpty(Window.Property(watchMeta))','False')
            expression=re.sub(r'String.IsEqual\(Window.Property\(browsable\),true\)',str(browsable=='true'),expression)
            actual=eval(expression.replace('!',' not ').replace('+',' and ').strip())
            self.assertEqual(actual,expected,'Watch status belongs to media titles, not people or collections')
    def test_native_search_filters_are_visible_and_do_not_overlap_the_notice(self):
        import re
        import xml.etree.ElementTree as E
        xml=E.parse(Path(__file__).parents[1]/'addon/resources/skins/Default/1080i/LiveReview.xml')
        def visible(condition):
            values={'page':'home','browseFilters':'false','episodeBrowser':'false','searchBrowser':'true'}
            condition=re.sub(r'String.IsEqual\(Window.Property\((\w+)\),(\w+)\)',lambda m:str(values.get(m[1])==m[2]),condition)
            return eval(condition.replace('[','(').replace(']',')').replace('!',' not ').replace('+',' and ').replace('|',' or ').strip())
        filters=xml.find(".//control[@id='600']/visible").text
        notice=next(c for c in xml.findall('.//control') if c.findtext('label')=='$INFO[Window.Property(notice)]').findtext('visible')
        self.assertTrue(visible(filters),'Search categories are hidden in native Kodi')
        self.assertFalse(visible(notice),'Notice overlaps search category buttons')
    def core(self):
        import search_ui
        return search_ui
    def test_four_real_search_routes_encode_the_entire_query(self):
        ui=self.core();query='Alien & Blade / 2049?'
        routes=[x for x in ui.search_sources(query) if x['kind']!='all']
        self.assertEqual([x['kind'] for x in routes],['movie','tv','person','company','collection'])
        for route in routes:
            parts=urlsplit(route['path']);params=parse_qs(parts.query)
            self.assertEqual(parts.netloc,'plugin.video.themoviedb.helper')
            self.assertEqual(params['query'],[query]);self.assertEqual(params['info'],['search'])
            self.assertEqual(params['tmdb_type'],[route['kind']])
        self.assertEqual(ui.search_sources('  '),[])
    def test_people_and_collections_open_discovery_instead_of_playback(self):
        ui=self.core()
        person={'file':'plugin://plugin.video.themoviedb.helper/?info=credits_in_both&tmdb_type=person&tmdb_id=42','label':'Person'}
        routes=ui.discovery_result(person)
        self.assertEqual([parse_qs(urlsplit(r['path']).query)['info'][0] for r in routes['rows']],['stars_in_movies','stars_in_tvshows'])
        collection={'file':'plugin://plugin.video.themoviedb.helper/?info=collection&tmdb_type=collection&tmdb_id=19','title':'Franchise','plot':'Has a plot','filetype':'directory'}
        self.assertEqual(ui.discovery_result(collection)['rows'][0]['path'],collection['file'])
        self.assertIsNone(ui.discovery_result({'file':'plugin://other/?tmdb_type=person&tmdb_id=42'}))
        self.assertIsNone(ui.discovery_result({'file':'plugin://plugin.video.themoviedb.helper/?info=search&tmdb_type=person&tmdb_id=42&page=2'}))
    def test_search_category_switch_preserves_query_and_resets_only_its_results(self):
        ui=self.core();props={};loaded=[];selections=[]
        obj=SimpleNamespace(search_state={'query':'Dune','kind':'movie'},selected={'file':'old'},
            stop_preview=lambda:None,populate_search=lambda:selections.append('chips'),
            setProperty=lambda k,v:props.__setitem__(k,v),set_rows=lambda rows:loaded.extend(rows))
        method=extract(ROOT/'live_review.py','select_search',{'search_sources':ui.search_sources,'clear_search_selection':ui.clear_search_selection},'LiveReview')
        method(obj,next(n for n,(kind,label) in enumerate(ui.SEARCH_KINDS) if kind=='person'))
        self.assertEqual(obj.search_state,{'query':'Dune','kind':'person'})
        self.assertEqual(parse_qs(urlsplit(loaded[0]['path']).query)['tmdb_type'],['person'])
        self.assertEqual(props['searchBrowser'],'true');self.assertIsNone(obj.selected)
    def test_opening_search_remembers_previous_page_and_cancel_does_not_change_it(self):
        ui=self.core();saved=[];opened=[];props={}
        dialog=SimpleNamespace(input=lambda *a,**kw:'New search')
        obj=SimpleNamespace(search_state=None,search_origin=None,discovery_stack=[],config={'SearchQuery':'Old search'},
            capture_browse=lambda **kw:{'selected':'original title','positions':[4,0]},
            save=lambda **kw:saved.append(True),stop_preview=lambda:None,
            setProperty=lambda k,v:props.__setitem__(k,v),select_search=lambda n:opened.append(n),
            getControl=lambda n:SimpleNamespace(setHeight=lambda n:None))
        method=extract(ROOT/'live_review.py','open_search',{'xbmcgui':SimpleNamespace(Dialog=lambda:dialog),'SEARCH_KINDS':ui.SEARCH_KINDS},'LiveReview')
        method(obj)
        self.assertEqual(obj.search_origin['positions'],[4,0]);self.assertEqual(obj.config['SearchQuery'],'New search')
        self.assertEqual(opened,[0]);self.assertEqual(saved,[True])
        previous=dict(obj.search_state);dialog.input=lambda *a,**kw:'';method(obj)
        self.assertEqual(obj.search_state,previous);self.assertEqual(opened,[0])
    def test_discovery_return_restores_search_without_a_second_provider_request(self):
        ui=self.core();props={};loaded=[];stack=[]
        obj=SimpleNamespace(section='Home',discovery_stack=stack,capture_browse=lambda **kw:{'search_state':{'query':'Dune','kind':'person'},'positions':[3,0]},
            stop_preview=lambda:None,getControl=lambda n:SimpleNamespace(setHeight=lambda h:None),
            setProperty=lambda k,v:props.__setitem__(k,v),set_rows=lambda rows:loaded.extend(rows))
        method=extract(ROOT/'live_review.py','open_discovery',{},'LiveReview')
        method(obj,ui.discovery_result({'file':'plugin://plugin.video.themoviedb.helper/?info=credits_in_both&tmdb_type=person&tmdb_id=42'}))
        self.assertEqual(stack[0]['positions'],[3,0]);self.assertIsNone(obj.search_state)
        self.assertEqual(props['searchBrowser'],'false');self.assertEqual(len(loaded),2)
        self.assertEqual(props['captionRows'],'false');self.assertEqual(props['filmographyBrowser'],'true')
    def test_people_primary_action_never_launches_the_provider_as_video(self):
        ui=self.core();opened=[];finished=[]
        obj=SimpleNamespace(actions_open=False,selected={'file':'plugin://plugin.video.themoviedb.helper/?info=credits_in_both&tmdb_type=person&tmdb_id=42'},
            open_discovery=lambda discovery:opened.append(discovery),finish=lambda:finished.append(True))
        extract(ROOT/'live_review.py','onClick',{'discovery_result':ui.discovery_result},'LiveReview')(obj,101)
        self.assertEqual(len(opened),1);self.assertEqual(finished,[])
    def test_selecting_people_or_collection_cards_opens_named_discovery(self):
        ui=self.core()
        for kind,info in [('person','credits_in_both'),('collection','collection')]:
            opened=[];generic=[]
            item={'title':'Named result','file':'plugin://plugin.video.themoviedb.helper/?info='+info+'&tmdb_type='+kind+'&tmdb_id=42','filetype':'directory'}
            obj=SimpleNamespace(actions_open=False,chosen=lambda cid:item,open_discovery=lambda d:opened.append(d),load_path=lambda *a,**k:generic.append(a),details=lambda item:generic.append(item))
            extract(ROOT/'live_review.py','onClick',{'discovery_result':ui.discovery_result,'is_browse_folder':lambda item:True},'LiveReview')(obj,900)
            self.assertEqual(len(opened),1,'Card selection must use the same named discovery as the hero action')
            self.assertEqual(generic,[])
            self.assertIn('Named result',opened[0]['heading'])
    def test_integration_status_reports_availability_without_claiming_account_auth(self):
        calls=[];shown=[]
        def rpc(method,params):
            calls.append((method,params))
            if params['addonid'].endswith('youtube'):return {'error':{'message':'Missing'}}
            return {'result':{'addon':{'enabled':True,'version':'1.2.3'}}}
        obj=SimpleNamespace(row_states={0:'error'},getProperty=lambda key:'Watching')
        method=extract(ROOT/'live_review.py','integration_status',{'rpc':rpc,'xbmcgui':SimpleNamespace(Dialog=lambda:SimpleNamespace(textviewer=lambda *args:shown.append(args)))},'LiveReview')
        method(obj)
        self.assertEqual(len(calls),3)
        self.assertIn('Previews: Not installed',shown[0][1]);self.assertIn('does not confirm an account is linked',shown[0][1])
        self.assertIn('List unavailable: Watching',shown[0][1])
    def test_back_from_discovery_restores_the_exact_parent_search(self):
        from live_core import PageHistory
        parent={'search_state':{'query':'Dune','kind':'person'},'positions':[3,0]};restored=[]
        obj=SimpleNamespace(actions_open=False,nav=False,mode='home',last_row=0,histories=[PageHistory()],
            episode_browser_context=None,person_context=None,discovery_stack=[parent],search_state=None,
            generation=4,setProperty=lambda *a:None,stop_preview=lambda:None,restore_browse=lambda state:restored.append(state))
        extract(ROOT/'live_review.py','onAction',{},'LiveReview')(obj,SimpleNamespace(getId=lambda:92))
        self.assertEqual(restored,[parent]);self.assertEqual(obj.discovery_stack,[])
    def test_back_from_search_returns_to_the_origin_page(self):
        from live_core import PageHistory
        restored=[];origin={'navigation_id':'shows','positions':[5,0]}
        obj=SimpleNamespace(actions_open=False,nav=False,mode='home',last_row=0,histories=[PageHistory()],
            episode_browser_context=None,person_context=None,discovery_stack=[],search_state={'query':'Dune'},search_origin=origin,
            generation=4,setProperty=lambda *a:None,stop_preview=lambda:None,restore_browse=lambda state:restored.append(state))
        extract(ROOT/'live_review.py','onAction',{},'LiveReview')(obj,SimpleNamespace(getId=lambda:92))
        self.assertEqual(restored,[origin])

if __name__=='__main__':unittest.main()
