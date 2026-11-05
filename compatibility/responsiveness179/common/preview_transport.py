"""Decorative previews only: isolated finite transport in the existing YT proxy.

No Kodi settings, shared request classes, account stores or full-video requests
are modified. Socket inactivity timeout bounds stalled reads; read1 plus a
monotonic request budget also stops a continuously trickled fixed-length body.
"""
import re
import os
import socket
import threading
import time
from select import select
from urllib.parse import urljoin, urlsplit, urlunsplit, parse_qs, urlencode
from base64 import urlsafe_b64encode
from json import dumps as json_dumps

from requests import Session
from requests.exceptions import RequestException
from urllib3.exceptions import HTTPError

TOKEN_PARAM = '__blpreview'
CANCEL_SUFFIX = '/blacklanturn-preview-cancel'
READ_TIMEOUT = .75
CONNECT_TIMEOUT = 2.0
REQUEST_SECONDS = 8.0
MAX_ACTIVE = 4
MAX_ENTRIES = 64
ENTRY_SECONDS = 180.0
CHUNK_SIZE = 65536
_slots = threading.BoundedSemaphore(MAX_ACTIVE)
_lock = threading.Lock()
_entries = {}


def valid_token(token):
    return bool(isinstance(token, str) and re.fullmatch(r'[a-f0-9]{32}', token))


def _entry(token):
    if not valid_token(token):
        return None
    now = time.monotonic()
    with _lock:
        for key, item in list(_entries.items()):
            if now - item[0] > ENTRY_SECONDS:
                del _entries[key]
        item = _entries.get(token)
        if item is None:
            if len(_entries) >= MAX_ENTRIES:
                return None
            item = (now, threading.Event())
            _entries[token] = item
        return item[1]


def cancel(token):
    event = _entry(token)
    if event is None:
        return False
    event.set()
    return True


def _current(handler, event, deadline):
    if event.is_set() or handler._close_all or time.monotonic() >= deadline:
        return False
    if handler.wfile.closed:
        return False
    try:
        if select((handler.request,), (), (), 0)[0]:
            return bool(handler.request.recv(1, socket.MSG_PEEK))
    except (OSError, ValueError):
        return False
    return True


def serve(handler, token, urls, method, headers, verify, proxies, proxy_base=None):
    """Return early/EOF on cancelled, expired, saturated or failed preview only."""
    handler.close_connection = True
    event = _entry(token)
    if event is None:
        handler.send_error(503)
        return
    if event.is_set():
        handler.send_error(410)
        return
    if not _slots.acquire(False):
        handler.send_error(503)
        return
    sent = False
    deadline = time.monotonic() + REQUEST_SECONDS
    try:
        handler.request.settimeout(READ_TIMEOUT)
        # A private session avoids shared retry policy/cookie/auth mutation.
        # Preserve the installed proxy/SSL policy; request headers are the
        # existing signed stream's headers, not any extra account credentials.
        with Session() as session:
            session.trust_env = False
            for url in urls[:2]:
                if not _current(handler, event, deadline):
                    break
                request_headers = {key:value for key,value in headers.items() if key.lower() != 'accept-encoding'}
                request_headers['Accept-Encoding'] = 'identity'
                request_headers.pop('Host', None)
                for _ in range(4):
                    if not _current(handler, event, deadline):
                        break
                    request = session.prepare_request(__import__('requests').Request(method, url, headers=request_headers))
                    # Session.send eagerly drains redirect bodies even when
                    # allow_redirects=False. Use its no-retry adapter directly
                    # so *every* preview response remains streaming/bounded.
                    with session.get_adapter(url).send(request, stream=True,
                                         timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
                                         verify=verify, proxies=proxies) as response:
                        if response.is_redirect:
                            target_url = urljoin(url, response.headers['Location'])
                            if urlsplit(target_url).scheme != 'https':
                                return
                            request_headers = scoped_headers(request_headers, url, target_url)
                            url = target_url
                            continue
                        if response.status_code not in (200, 206):
                            break
                        content_type = response.headers.get('Content-Type', '').lower()
                        if ('application/dash+xml' in content_type or 'manifest/dash' in urlsplit(url).path or urlsplit(url).path.lower().endswith('.mpd')):
                            # Generated local MPDs are already scoped by the
                            # player client. External DASH needs a separate XML
                            # rewrite; never let remote media bypass ownership.
                            break
                        is_hls = method != 'HEAD' and ('mpegurl' in content_type or urlsplit(url).path.lower().endswith('.m3u8'))
                        playlist = None
                        if is_hls:
                            if not proxy_base or response.headers.get('Content-Encoding', 'identity') != 'identity':
                                return
                            chunks = []; size = 0
                            while _current(handler, event, deadline):
                                chunk = response.raw.read1(CHUNK_SIZE, decode_content=False)
                                if not chunk:
                                    break
                                size += len(chunk)
                                if size > 1048576:
                                    return
                                chunks.append(chunk)
                            if not _current(handler, event, deadline):
                                return
                            playlist = rewrite_playlist(b''.join(chunks), url, proxy_base, token, request_headers)
                        # Never response.content: a 200 response may be a whole
                        # video, not a range. Forward incrementally for both.
                        handler.send_response(response.status_code)
                        for name, value in response.headers.items():
                            if name.lower() not in (('connection', 'transfer-encoding', 'content-length') if playlist is not None else ('connection', 'transfer-encoding')):
                                handler.send_header(name, value)
                        if playlist is not None:
                            handler.send_header('Content-Length', str(len(playlist)))
                        handler.send_header('Connection', 'close')
                        handler.end_headers()
                        sent = True
                        if method == 'HEAD':
                            return
                        if playlist is not None:
                            handler.wfile.write(playlist)
                            return
                        reader = getattr(response.raw, 'read1', None)
                        if reader is None:
                            # Fail closed on untested urllib3; read(amt) can
                            # wait forever when the peer continually trickles.
                            return
                        while _current(handler, event, deadline):
                            data = reader(CHUNK_SIZE, decode_content=False)
                            if not data or not _current(handler, event, deadline):
                                break
                            handler.wfile.write(data)
                        return
    except (RequestException, HTTPError, OSError, ValueError):
        pass  # Decorative preview failure retains artwork in the controller.
    finally:
        _slots.release()
    if not sent:
        handler.send_error(502)


def manifest_filename(base, token):
    """Bound disposable preview MPDs, preserving every other cache file."""
    if not valid_token(token):
        raise ValueError('Invalid preview transport token')
    now = time.time()
    count = 0
    for entry in os.scandir(base):
        name = entry.name
        if not (name.startswith('blacklanturn-preview-') and name.endswith('.mpd')
                and valid_token(name[len('blacklanturn-preview-'):-4])):
            continue
        try:
            if now - entry.stat().st_mtime > ENTRY_SECONDS:
                os.remove(entry.path)
            else:
                count += 1
        except OSError:
            pass
    if count >= MAX_ENTRIES:
        raise RuntimeError('Preview manifest cache is full')
    return 'blacklanturn-preview-%s.mpd' % token


def wrap_url(url, proxy_base, token, headers=None):
    parts = urlsplit(url)
    if parts.scheme not in ('http', 'https') or not parts.hostname:
        raise ValueError('Unsupported preview stream URL')
    params = parse_qs(parts.query, keep_blank_values=True)
    params.update({'__host': [parts.netloc], '__path': [parts.path],
                   '__method': ['GET'], '__blpreview': [token],
                   '__scheme': [parts.scheme],
                   '__headers': [urlsafe_b64encode(json_dumps(headers or {}).encode('utf-8')).decode('ascii')]})
    base = urlsplit(proxy_base)
    return urlunsplit((base.scheme, base.netloc, '/youtube/stream', urlencode(params, doseq=True), ''))


def rewrite_playlist(data, source_url, proxy_base, token, headers):
    text = data.decode('utf-8-sig')
    if not text.lstrip().startswith('#EXTM3U'):
        raise ValueError('Invalid preview HLS playlist')
    output = []; size = 0; uri_count = 0
    def uri(value):
        nonlocal uri_count
        uri_count += 1
        if uri_count > 2048:
            raise ValueError('Preview HLS playlist has too many URIs')
        target=urljoin(source_url, value)
        return wrap_url(target, proxy_base, token, scoped_headers(headers, source_url, target))
    for line in text.splitlines():
        if line and not line.startswith('#'):
            line = uri(line.strip())
        elif 'URI="' in line:
            line = re.sub(r'URI="([^"]+)"', lambda match:'URI="%s"' % uri(match.group(1)), line)
        encoded = (line+'\n').encode('utf-8'); size += len(encoded)
        if size > 2097152:
            raise ValueError('Preview HLS playlist is too large')
        output.append(encoded)
    return b''.join(output)


def scoped_headers(headers, source_url, target_url):
    """Keep signed CDN authorization only within its Googlevideo CDN family."""
    source=urlsplit(source_url);target=urlsplit(target_url)
    same_origin=(source.scheme.lower(),source.netloc.lower())==(target.scheme.lower(),target.netloc.lower())
    google_cdn=all((part.hostname or '').endswith('.googlevideo.com') for part in (source,target))
    result={}
    for key,value in headers.items():
        lower=key.lower()
        if lower=='host':continue
        if not same_origin and (lower in ('cookie','proxy-authorization') or (lower=='authorization' and not google_cdn)):continue
        result[key]=value
    return result
