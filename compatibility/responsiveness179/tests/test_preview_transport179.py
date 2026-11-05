import importlib.util, io, pathlib, socket, sys, threading, time, unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT=pathlib.Path(__file__).resolve().parents[1]
import os,zipfile
EDITION=os.environ.get('BLACKLANTURN_PREVIEW_EDITION','apple')
assert EDITION in ('general','apple')
def upstream_http():
    edition='General' if EDITION=='general' else 'Apple-TV-Mac'
    with zipfile.ZipFile(ROOT.parents[1]/'baselines'/f'BlackLanturn-{edition}-Kodi21-1.1.61.zip') as archive:
        return archive.read('addons/plugin.video.youtube/resources/lib/youtube_plugin/kodion/network/http_server.py').decode()
spec=importlib.util.spec_from_file_location('preview_transport',ROOT/'common/preview_transport.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class Upstream(BaseHTTPRequestHandler):
    protocol_version='HTTP/1.0'
    def log_message(self,*a):pass
    def do_HEAD(self):
        self.send_response(200);self.send_header('Content-Length','1000000');self.end_headers()
    def do_GET(self):
        if self.path=='/external.mpd':
            body=b'<MPD><BaseURL>https://r1.googlevideo.com/video</BaseURL></MPD>';self.send_response(200);self.send_header('Content-Type','application/dash+xml');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body);return
        if self.path=='/headers':time.sleep(2);return
        if self.path=='/master.m3u8':
            body=b'#EXTM3U\n#EXTINF:5,\nsegment.ts\n';self.send_response(200);self.send_header('Content-Type','application/vnd.apple.mpegurl');Upstream.last_encoding=self.headers.get('Accept-Encoding')
            if Upstream.last_encoding!='identity':
                import gzip
                body=gzip.compress(body);self.send_header('Content-Encoding','gzip')
            self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body);return
        self.send_response(200);self.send_header('Content-Length','1000000');self.end_headers()
        try:
            if self.path=='/stall':time.sleep(2);return
            if self.path=='/trickle':
                for _ in range(100):self.wfile.write(b'x');self.wfile.flush();time.sleep(.03)
            else:self.wfile.write(b'x'*65536);self.wfile.flush();time.sleep(2)
        except (OSError,ValueError):pass

class Handler:
    _close_all=False
    def __init__(self):
        self.request,self.client=socket.socketpair();self.wfile=io.BytesIO();self.headers={};self.status=None;self.sent={};self.close_connection=False
    def send_response(self,status):self.status=status
    def send_header(self,key,val):self.sent[key]=val
    def end_headers(self):pass
    def send_error(self,status):self.status=status
    def close(self):self.request.close();self.client.close()

class TransportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Upstream);cls.server.daemon_threads=True
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.base='http://127.0.0.1:%s'%cls.server.server_port
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.thread.join(1)
    def setUp(self):
        self.h=Handler();self.token='a'*32;m.READ_TIMEOUT=.15;m.REQUEST_SECONDS=.35
        m._entries.clear()
    def tearDown(self):self.h.close()
    def serve(self,path):return m.serve(self.h,self.token,[self.base+path],method='GET',headers={},verify=True,proxies=None)
    def test_stalled_body_is_bounded_and_not_buffered(self):
        start=time.monotonic();self.serve('/stall');self.assertLess(time.monotonic()-start,.8)
        self.assertEqual(self.h.wfile.getvalue(),b'');self.assertTrue(self.h.close_connection)
    def test_trickled_body_cannot_extend_total_deadline(self):
        start=time.monotonic();self.serve('/trickle');self.assertLess(time.monotonic()-start,.8)
        self.assertGreater(len(self.h.wfile.getvalue()),0);self.assertLess(len(self.h.wfile.getvalue()),100)
    def test_stalled_headers_bounded_by_read_timeout(self):
        start=time.monotonic();self.serve('/headers');self.assertLess(time.monotonic()-start,.8)
        self.assertEqual(self.h.status,502)
    def test_hls_response_is_bounded_and_rewritten_in_transport(self):
        m.serve(self.h,self.token,[self.base+'/master.m3u8'],method='GET',headers={},verify=True,proxies=None,proxy_base='http://127.0.0.1:50152')
        data=self.h.wfile.getvalue();self.assertIn(b'__blpreview=',data);self.assertEqual(int(self.h.sent['Content-Length']),len(data));self.assertEqual(self.h.status,200)
    def test_hls_compression_negotiation_overrides_existing_gzip_preference(self):
        m.serve(self.h,self.token,[self.base+'/master.m3u8'],method='GET',headers={'Accept-Encoding':'gzip, deflate'},verify=True,proxies=None,proxy_base='http://127.0.0.1:50152')
        self.assertEqual(Upstream.last_encoding,'identity');self.assertEqual(self.h.status,200);self.assertIn(b'__blpreview=',self.h.wfile.getvalue())
    def test_preview_head_does_not_open_a_body_read(self):
        m.serve(self.h,self.token,[self.base+'/stall'],method='HEAD',headers={},verify=True,proxies=None)
        self.assertEqual(self.h.status,200);self.assertEqual(self.h.wfile.getvalue(),b'');self.assertEqual(self.h.sent['Content-Length'],'1000000')
    def test_external_dash_fails_closed_without_remote_segments(self):
        self.serve('/external.mpd');self.assertEqual(self.h.status,502);self.assertEqual(self.h.wfile.getvalue(),b'')
    def test_cancel_before_first_segment_has_no_upstream_request(self):
        self.assertTrue(m.cancel(self.token));self.serve('/stall');self.assertEqual(self.h.status,410)
    def test_cancellation_during_trickled_body(self):
        t=threading.Thread(target=lambda:self.serve('/trickle'));t.start();time.sleep(.09);m.cancel(self.token)
        t.join(.5);self.assertFalse(t.is_alive());self.assertLess(len(self.h.wfile.getvalue()),20)
    def test_client_disconnect_stops_body(self):
        self.h.client.close();start=time.monotonic();self.serve('/trickle');self.assertLess(time.monotonic()-start,.3)
    def test_registry_is_bounded_and_active_limit_rejects(self):
        for i in range(m.MAX_ENTRIES):self.assertTrue(m.cancel('%032x'%i))
        self.assertFalse(m.cancel('f'*32));self.assertLessEqual(len(m._entries),m.MAX_ENTRIES)
        m._entries.clear()
        for _ in range(m.MAX_ACTIVE):self.assertTrue(m._slots.acquire(False))
        try:self.serve('/stall');self.assertEqual(self.h.status,503)
        finally:
            for _ in range(m.MAX_ACTIVE):m._slots.release()
    def test_cancel_is_isolated_from_other_preview(self):
        m.cancel('b'*32);self.serve('/trickle');self.assertEqual(self.h.status,200);self.assertGreater(len(self.h.wfile.getvalue()),0)
    def test_normal_timeout_class_is_never_mutated(self):
        text=(ROOT/EDITION/'http_server.py').read_text();normal=text.split("elif path['path'].startswith(PATHS.STREAM_PROXY):",1)[1]
        self.assertIn('serve_preview',normal);self.assertNotIn('BaseRequestsClass._timeout =',text)
        self.assertIn('response.raw.read(\n                                amt=1048576,',text)
if __name__=='__main__':unittest.main()

class PropagationTests(unittest.TestCase):
    def method(self,name):
        import ast,base64,json,re,types,urllib.parse
        tree=ast.parse((ROOT/EDITION/'player_client.py').read_text())
        node=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name==name)
        code=ast.Module(body=[node],type_ignores=[])
        env={'re_compile':re.compile,'re_sub':re.sub,'urlsplit':urllib.parse.urlsplit,'parse_qs':urllib.parse.parse_qs,'urlencode':urllib.parse.urlencode,'urlsafe_b64encode':base64.urlsafe_b64encode,'json_dumps':json.dumps,'PATHS':types.SimpleNamespace(STREAM_PROXY='/youtube/stream'),'get_connect_address':lambda *a,**k:'127.0.0.1:50152'}
        exec(compile(code,'player_client.py','exec'),env);return env[name]
    def test_same_video_normal_and_preview_urls_have_disjoint_scope(self):
        from types import SimpleNamespace
        from urllib.parse import urlsplit,parse_qs
        method=self.method('_process_url_params');scope={'token':None}
        client=SimpleNamespace(video_id='samevideo',_context=SimpleNamespace(get_param=lambda name:scope['token']))
        original='https://r1.googlevideo.com/videoplayback?itag=137&clen=100'
        normal=method(client,original,stream_proxy=True)
        scope['token']='a'*32;preview=method(client,original,stream_proxy=True)
        scope['token']=None;normal2=method(client,original,stream_proxy=True)
        self.assertEqual(normal,normal2);self.assertNotIn('__blpreview',parse_qs(urlsplit(normal).query))
        self.assertEqual(parse_qs(urlsplit(preview).query)['__blpreview'],['a'*32])
        self.assertEqual(urlsplit(preview).netloc,'127.0.0.1:50152')
    def test_full_video_proxy_branch_is_byte_identical(self):
        old=upstream_http();new=(ROOT/EDITION/'http_server.py').read_text()
        start="            original_path = params.pop('__path', empty)[0] or '/videoplayback'\n            request_servers"
        self.assertEqual(old[old.index(start):old.index('    def do_HEAD')],new[new.index(start):new.index('    def do_HEAD')])
    def test_manifest_names_are_disjoint_and_cache_bounded(self):
        import tempfile,os
        with tempfile.TemporaryDirectory() as tmp:
            a=m.manifest_filename(tmp,'a'*32);b=m.manifest_filename(tmp,'b'*32)
            self.assertNotEqual(a,b);self.assertNotEqual(a,'samevideo.mpd')
            normal=pathlib.Path(tmp)/'samevideo.mpd';normal.write_text('keep')
            for i in range(m.MAX_ENTRIES):(pathlib.Path(tmp)/('blacklanturn-preview-%032x.mpd'%i)).touch()
            with self.assertRaises(RuntimeError):m.manifest_filename(tmp,'f'*32)
            old=pathlib.Path(tmp)/'blacklanturn-preview-00000000000000000000000000000000.mpd'
            os.utime(old,(0,0));self.assertEqual(m.manifest_filename(tmp,'f'*32),'blacklanturn-preview-'+('f'*32)+'.mpd')
            self.assertFalse(old.exists());self.assertEqual(normal.read_text(),'keep')

class ProgressiveHLSTests(unittest.TestCase):
    def test_progressive_url_preserves_headers_range_and_signed_query(self):
        import urllib.parse,json,base64
        source='https://r1.googlevideo.com/videoplayback?signature=a%2Bb&range=0-100'
        result=m.wrap_url(source,'http://127.0.0.1:50152','a'*32,{'Authorization':'fixture','Range':'bytes=0-100'})
        p=urllib.parse.urlsplit(result);q=urllib.parse.parse_qs(p.query)
        self.assertEqual(p.netloc,'127.0.0.1:50152');self.assertEqual(q['signature'],['a+b'])
        self.assertEqual(q['__blpreview'],['a'*32]);self.assertEqual(q['__method'],['GET'])
        self.assertEqual(json.loads(base64.urlsafe_b64decode(q['__headers'][0])),{'Authorization':'fixture','Range':'bytes=0-100'})
    def test_hls_master_media_segments_and_key_uris_stay_scoped(self):
        from urllib.parse import urlsplit,parse_qs
        data=b'#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1000\nlevel/main.m3u8\n#EXT-X-KEY:METHOD=AES-128,URI="/key.bin"\nsegment.ts\n'
        result=m.rewrite_playlist(data,'https://example.invalid/a/master.m3u8','http://127.0.0.1:50152','a'*32,{}).decode()
        self.assertNotIn('\nsegment.ts',result);self.assertNotIn('URI="/key.bin"',result)
        paths=[]
        import re
        urls=[line for line in result.splitlines() if line and not line.startswith('#')]+re.findall(r'URI="([^"]+)"',result)
        for url in urls:
            p=urlsplit(url);q=parse_qs(p.query);self.assertEqual(p.netloc,'127.0.0.1:50152');self.assertEqual(q['__blpreview'],['a'*32]);paths.append(q['__path'][0])
        self.assertEqual(set(paths),{'/a/level/main.m3u8','/key.bin','/a/segment.ts'})
    def test_hls_rewrite_rejects_unbounded_uri_expansion(self):
        with self.assertRaises(ValueError):m.rewrite_playlist(b'#EXTM3U\n'+(b'x\n'*2049),'https://example.invalid/a','http://127.0.0.1:50152','a'*32,{})

class CredentialScopeTests(unittest.TestCase):
    def test_redirect_headers_are_case_insensitive_and_foreign_safe(self):
        headers={'authorization':'fixture','COOKIE':'private','Proxy-Authorization':'proxy','Host':'r1.googlevideo.com','User-Agent':'test'}
        clean=m.scoped_headers(headers,'https://r1.googlevideo.com/a','https://cdn.example.invalid/a')
        self.assertEqual(clean,{'User-Agent':'test'})
        cdn=m.scoped_headers(headers,'https://r1.googlevideo.com/a','https://r2.googlevideo.com/a')
        self.assertEqual(cdn,{'authorization':'fixture','User-Agent':'test'})
    def test_foreign_hls_children_cannot_reintroduce_credentials(self):
        from urllib.parse import urlsplit,parse_qs
        import json,base64
        result=m.rewrite_playlist(b'#EXTM3U\nhttps://foreign.invalid/a.ts\n','https://cdn.example.invalid/master.m3u8','http://127.0.0.1:50152','a'*32,{'Authorization':'fixture','Cookie':'private'}).decode().splitlines()[1]
        params=parse_qs(urlsplit(result).query)
        self.assertEqual(json.loads(base64.urlsafe_b64decode(params['__headers'][0])),{})

class HandlerLifecycleTests(unittest.TestCase):
    def server_class(self):
        import ast,socket,socketserver
        tree=ast.parse((ROOT/EDITION/'http_server.py').read_text());node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='HTTPServer')
        ns={'socket':socket,'ThreadingMixIn':socketserver.ThreadingMixIn,'TCPServer':socketserver.TCPServer,'select':lambda *a:([],[],[])}
        exec(compile(ast.Module(body=[node],type_ignores=[]),'http_server.py','exec'),ns);return ns['HTTPServer']
    def test_completed_preview_handlers_do_not_accumulate(self):
        from types import SimpleNamespace
        cls=self.server_class();server=object.__new__(cls)
        for _ in range(100):
            handler=SimpleNamespace(_blacklanturn_preview_request=True,_close_all=False,wfile=SimpleNamespace(closed=True),handle=lambda:None)
            server.RequestHandlerClass=lambda *a:handler;server.finish_request(None,None)
        self.assertEqual(cls._handlers,[])
        normal=SimpleNamespace(_close_all=False,wfile=SimpleNamespace(closed=True),handle=lambda:None)
        server.RequestHandlerClass=lambda *a:normal;server.finish_request(None,None);self.assertEqual(cls._handlers,[normal])
    def test_failed_preview_handler_is_also_released(self):
        from types import SimpleNamespace
        cls=self.server_class();server=object.__new__(cls)
        def fail():raise ValueError('fixture')
        handler=SimpleNamespace(_blacklanturn_preview_request=True,_close_all=False,wfile=SimpleNamespace(closed=True),handle=fail)
        server.RequestHandlerClass=lambda *a:handler
        with self.assertRaises(ValueError):server.finish_request(None,None)
        self.assertEqual(cls._handlers,[])

class CancelPeerTests(unittest.TestCase):
    def run_cancel(self,peer,local):
        import ast,types,tempfile,os,json
        source=ast.parse((ROOT/EDITION/'http_server.py').read_text());cls=next(n for n in source.body if isinstance(n,ast.ClassDef) and n.name=='RequestHandler');node=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='do_GET')
        paths=types.SimpleNamespace(STREAM_PROXY='/youtube/stream');ns={'PATHS':paths,'CANCEL_SUFFIX':m.CANCEL_SUFFIX,'TOKEN_PARAM':m.TOKEN_PARAM,'valid_token':m.valid_token,'cancel_preview':lambda token:True,'os':os}
        exec(compile(ast.Module(body=[node],type_ignores=[]),'do_GET','exec'),ns)
        output=[]
        handler=types.SimpleNamespace(_context=types.SimpleNamespace(get_settings=lambda:object()),connection_allowed=lambda method:(True,{'path':'/youtube/stream'+m.CANCEL_SUFFIX,'params':{m.TOKEN_PARAM:['a'*32]}}),client_address=(peer,123),request=types.SimpleNamespace(getsockname=lambda:(local,50152)),BASE_PATH='/private/tmp/preview179-does-not-exist',send_response=output.append,send_error=output.append,send_header=lambda *a:None,end_headers=lambda:None)
        ns['do_GET'](handler);return output
    def test_loopback_or_same_device_peer_accepted(self):
        self.assertEqual(self.run_cancel('127.0.0.1','192.168.1.20'),[204])
        self.assertEqual(self.run_cancel('192.168.1.20','192.168.1.20'),[204])
    def test_unrelated_remote_peer_cannot_cancel(self):
        self.assertEqual(self.run_cancel('192.168.1.21','192.168.1.20'),[403])

class ExternalDashPreparationTests(unittest.TestCase):
    def test_external_dash_never_reaches_listitem_or_native_play(self):
        import ast,types,sys
        from unittest.mock import patch
        source=ast.parse((ROOT.parents[1]/'controller-source/addon/youtube_provider.py').read_text());node=next(n for n in source.body if isinstance(n,ast.FunctionDef) and n.name=='_prepare_preview');ns={}
        exec(compile(ast.Module(body=[node],type_ignores=[]),'youtube_provider.py','exec'),ns)
        calls=[];current={'path':'https://www.youtube.com/api/manifest/dash/id/test'}
        media=types.SimpleNamespace(use_mpd=lambda:True,get_uri=lambda:current['path'])
        modules={'youtube_plugin.youtube.helper.yt_play':types.SimpleNamespace(_play_stream=lambda *a:media),'youtube_plugin.kodion.items':types.SimpleNamespace(playback_item=lambda *a:calls.append('converted') or object())}
        with patch.dict(sys.modules,modules):
            self.assertIsNone(ns['_prepare_preview'](types.SimpleNamespace(provider=object()),object()));self.assertEqual(calls,[])
            current['path']='http://127.0.0.1:50152/youtube/manifest/dash?file=fixture.mpd';self.assertIsNotNone(ns['_prepare_preview'](types.SimpleNamespace(provider=object()),object()));self.assertEqual(calls,['converted'])
