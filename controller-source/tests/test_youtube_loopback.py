import ast,socket,unittest,os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

class YouTubeLoopback(unittest.TestCase):
    def test_explicit_loopback_manifest_never_uses_lan_fallback(self):
        root=Path(__file__).resolve().parents[1]
        p=Path(os.environ.get('BL_YOUTUBE_SOURCE',str(root/'fixtures/youtube_http_server.py')))
        tree=ast.parse(p.read_text())
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='get_connect_address')
        module=ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[]))
        connection=Mock();connection.connect.side_effect=OSError(49,'Cannot assign requested address')
        fake_socket=SimpleNamespace(AF_INET=socket.AF_INET,AF_INET6=socket.AF_INET6,SOCK_DGRAM=socket.SOCK_DGRAM,SOL_SOCKET=socket.SOL_SOCKET,SO_REUSEADDR=socket.SO_REUSEADDR,SO_REUSEPORT=socket.SO_REUSEPORT,error=OSError,socket=lambda *args:connection)
        namespace={'socket':fake_socket,'is_ipv6':lambda x:':' in x,'logging':SimpleNamespace(exception=lambda *a:None),'xbmc':SimpleNamespace(getIPAddress=lambda:'192.0.2.55')}
        exec(compile(module,str(p),'exec'),namespace)
        settings=SimpleNamespace(httpd_listen=lambda:'127.0.0.1',httpd_port=lambda:50152)
        context=SimpleNamespace(get_settings=lambda:settings)
        self.assertEqual(namespace['get_connect_address'](context,as_netloc=True),'127.0.0.1:50152')

if __name__=='__main__':unittest.main()
