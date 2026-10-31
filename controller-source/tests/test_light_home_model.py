import copy,json,tempfile,time,unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
from light_home_model import validated_record
from light_home_state import write_record
from title_preferences import TitlePreferences
class ModelTests(unittest.TestCase):
    def fixture(self,d):
        icon=Path(d)/'addons/resource.images.test/icon.png';icon.parent.mkdir(parents=True);icon.write_bytes(b'image')
        item={'title':'Example','file':'plugin://plugin.video.themoviedb.helper/?info=seasons&tmdb_type=tv&tmdb_id=123','filetype':'directory','art':{'fanart':'https://image.tmdb.org/t/p/original/image.jpg'}}
        hero={'properties':{'hero':item['art']['fanart'],'title':'Example'},'play':'Episodes','saved':'+ My Stuff','height':155}
        row={'label':'Shows','path':'plugin://plugin.video.themoviedb.helper/?info=trakt_recommendations&tmdb_type=tv','items':[item],'heroes':[hero]}
        return {'rows':[copy.deepcopy(row),copy.deepcopy(row)],'sidebar':[{'id':i,'label':i,'icon':str(icon)} for i in ('search','home','settings')],'properties':{'loading':'false'}}
    def test_valid_model_and_nested_corruption_fail_closed_without_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'display.json';base=self.fixture(d);write_record(p,'scope',base)
            self.assertIsNotNone(validated_record(p,'scope'))
            variants=[]
            for key in ('rows','sidebar','properties'):
                value=copy.deepcopy(base);value[key]=None;variants.append(value)
            for target in ('row','sidebar','hero','properties'):
                value=copy.deepcopy(base)
                if target=='row':value['rows'][0]=None
                elif target=='sidebar':value['sidebar'][0]=None
                elif target=='hero':value['rows'][0]['heroes'][0]=None
                else:value['rows'][0]['heroes'][0]['properties']=None
                variants.append(value)
            for value in variants:
                write_record(p,'scope',value);before=p.read_bytes();self.assertIsNone(validated_record(p,'scope'));self.assertEqual(p.read_bytes(),before)
    def test_private_urls_and_executable_routes_never_render(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'display.json';base=self.fixture(d)
            for value in ('https://private.example/stream?token=secret','plugin://other.addon/?action=delete'):
                record=copy.deepcopy(base);record['rows'][0]['items'][0]['file']=value;write_record(p,'scope',record);self.assertIsNone(validated_record(p,'scope'))
            record=copy.deepcopy(base);record['rows'][0]['heroes'][0]['properties']['hero']='https://private.example/image?token=secret';write_record(p,'scope',record);self.assertIsNone(validated_record(p,'scope'))
    def test_show_less_current_session_applies_once_and_adoption_keeps_same_membership(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'feedback.json';item=self.fixture(d)['rows'][0]['items'][0]
            p.write_text(json.dumps({'version':1,'titles':{'tv:123':{'mode':'less','label':'Example','session':'old'}}}))
            early=TitlePreferences(p);normal=TitlePreferences(p)
            self.assertEqual(early.session,normal.session);self.assertEqual(early.apply([item]),normal.apply([item]))
            before=p.read_bytes();early.apply([item]);self.assertEqual(before,p.read_bytes())
    def test_two_visible_rows_adopt_full_home_catalogue_and_saved_order(self):
        import light_home_model as model
        self.assertTrue(hasattr(model,'adoption_definitions'),'Full Home catalogue must survive early adoption')
        with tempfile.TemporaryDirectory() as d:
            record=self.fixture(d)
            rows=[{'label':'Row '+str(i),'path':record['rows'][0]['path']+'&page='+str(i+1),'enabled':True} for i in range(9)]
            config={'Home':rows}
            order=list(reversed(rows))
            record['rows']=[dict(record['rows'][0],label=r['label'],path=r['path']) for r in order[:2]]
            got=model.adoption_definitions(config,lambda original:list(reversed(original)),record)
            self.assertEqual(got,order);self.assertEqual(len(got),9)
            record['rows'][0]['path']='changed'
            self.assertIsNone(model.adoption_definitions(config,lambda original:list(reversed(original)),record))
