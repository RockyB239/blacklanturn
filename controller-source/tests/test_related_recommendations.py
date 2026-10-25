"""More-like-this must prefer usable recommendations without request fanout."""
import unittest
from urllib.parse import urlencode,parse_qs,urlsplit
from related_titles import load_related

def route(info,kind,**params):
    return 'plugin://plugin.video.themoviedb.helper/?'+urlencode(dict(info=info,tmdb_type=kind,nextpage='true',widget='true',**params))

def title(n):return {'file':route('seasons','tv',tmdb_id=n),'label':str(n),'filetype':'directory','playcount':1,'resume':{'position':4}}

class RelatedRecommendations(unittest.TestCase):
    def test_recommendations_keep_provider_order_art_status_and_exact_next_route_without_similar_request(self):
        origin=route('recommendations','tv',tmdb_id='1413');nxt=origin+'&page=2&reload=123'
        rows=[title(2),title(1),{'file':nxt,'label':'Next page','filetype':'directory'}];calls=[]
        def provider(path):calls.append(path);return rows
        path,items=load_related(route,provider,'tv','1413')
        self.assertEqual(path,origin);self.assertEqual(items,rows);self.assertEqual(calls,[origin])
    def test_empty_or_navigation_only_or_malformed_recommendations_use_similar_once(self):
        for result in ([],None,{},[{'file':route('recommendations','tv',tmdb_id='1413')+'&page=2','filetype':'directory'}],[{'label':'No results'}]):
            with self.subTest(result=result):
                calls=[]
                def provider(path):
                    calls.append(path)
                    return result if parse_qs(urlsplit(path).query)['info']==['recommendations'] else [title(3)]
                path,items=load_related(route,provider,'tv','1413')
                self.assertEqual(path,route('similar','tv',tmdb_id='1413'));self.assertEqual(items,[title(3)])
                self.assertEqual(len(calls),2)
    def test_unavailable_recommendations_can_use_similar_without_breaking_details(self):
        def provider(path):
            if 'info=recommendations' in path:raise RuntimeError('offline')
            return [title(3)]
        self.assertEqual(load_related(route,provider,'tv','1413')[1],[title(3)])
    def test_cancelled_request_does_not_make_fallback_or_return_stale_titles(self):
        active=[True];calls=[]
        def provider(path):calls.append(path);active[0]=False;return []
        self.assertEqual(load_related(route,provider,'tv','1413',valid=lambda:active[0]),('',[]));self.assertEqual(len(calls),1)
    def test_both_empty_do_not_return_a_navigation_only_trap(self):
        path,items=load_related(route,lambda path:[{'file':path+'&page=2','filetype':'directory'}],'tv','1413')
        self.assertEqual(items,[])
    def test_invalid_identity_never_makes_provider_request(self):
        def provider(path):self.fail('invalid identity contacted provider')
        for kind,ident in [('person','1'),('tv',''),('movie','../1')]:
            self.assertEqual(load_related(route,provider,kind,ident),('',[]))

    def test_malformed_route_does_not_block_empty_recommendations_fallback(self):
        def provider(path):
            return [{'file':'plugin://[broken','label':'Bad'}] if 'info=recommendations' in path else [title(3)]
        self.assertEqual(load_related(route,provider,'tv','1413')[1],[title(3)])

    def test_mixed_bad_link_does_not_remove_valid_recommendations_or_force_fallback(self):
        calls=[]
        def provider(path):calls.append(path);return [{'file':'plugin://[broken','label':'bad'},title(3)]
        self.assertEqual(load_related(route,provider,'tv','1413')[1],[title(3)]);self.assertEqual(len(calls),1)

if __name__=='__main__':unittest.main()
