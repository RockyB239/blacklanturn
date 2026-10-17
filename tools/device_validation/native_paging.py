"""Fire paging acceptance, executed by the existing controller startup hook.

Only ordinary Action inputs and read-only labels/controller Python data are used.
There are no Window objects, activation calls, direct callbacks, or settings writes.
Call main(base=..., out=...) or exec with BASE/OUT and __name__='__main__'.
The 240-second cooperative deadline includes a reserved Home recovery interval.
"""
import copy
import gc
import hashlib
import json
import os
from pathlib import Path
import time
import traceback


def card_transport_matches(source, native_path, native_kind, native_label):
    kind = source.get('_page_control', '')
    if native_kind != kind:
        return False
    if kind == 'previous':
        # This control is an action marker, not a provider route. The actual
        # callback ignores its file field and pops the controller's history.
        return (source.get('file') == 'blacklanturn://previous-page'
                and native_label == source.get('label') == 'Previous')
    return bool(native_path) and native_path == source.get('file')


def page_destination(kind, selected_path, history):
    if kind == 'previous':
        if not history or not history[-1][0]:
            raise ValueError('Previous has no existing history destination')
        return history[-1][0]
    if kind != 'next' or not selected_path:
        raise ValueError('Invalid next-page destination')
    return selected_path


def metadata_equality(before, after):
    """Compare title order and all captured metadata by exact provider path."""
    def index(cards):
        result = {}
        order = []
        for card in cards:
            if card.get('kind'):
                continue
            path = card.get('path')
            if not path or path in result:
                raise ValueError('Missing or duplicate title path')
            order.append(path)
            result[path] = {'source': card['source'], 'native': card['native']}
        return order, result
    try:
        old_order, old = index(before)
        new_order, new = index(after)
    except (KeyError, ValueError) as exc:
        return {'equal': False, 'error': str(exc)}
    missing = sorted(set(old) - set(new))
    added = sorted(set(new) - set(old))
    changed = sorted(path for path in set(old) & set(new) if old[path] != new[path])
    return {'equal': bool(old) and old_order == new_order and not (missing or added or changed),
            'order_equal': old_order == new_order, 'missing': missing, 'added': added,
            'changed': changed, 'compared_titles': len(old)}


def matching_prepared_event(events, key, since):
    """An uncorrelated legacy event is insufficient to call a page prepared."""
    generation, revision, target = key
    digest = hashlib.sha256(target.encode()).hexdigest()
    for event in reversed(events):
        if (event.get('event') == 'next_page_prepared'
                and isinstance(event.get('time'), (int, float)) and event['time'] >= since
                and event.get('generation') == generation and event.get('revision') == revision
                and (event.get('target') == target or event.get('target_sha256') == digest)):
            return event
    return None


def row_ready(value, heading):
    cards = value.get('cards') or []
    return (value.get('window') == value.get('expected_window')
            and value.get('heading') == heading and value.get('state') == 'ready'
            and not value.get('loading') and bool(cards)
            and value.get('native_count') == len(cards)
            and all(card.get('path') and card.get('native', {}).get('label') for card in cards)
            and value.get('notice') != 'Loading provider page…'
            and not value.get('notice', '').startswith('Page unavailable'))


def runtime_failures(events,cancellation):
    start=cancellation.get('first_back_epoch');end=cancellation.get('finished_epoch')
    verified=(cancellation.get('status')=='passed' and isinstance(start,(int,float)) and isinstance(end,(int,float)))
    def expected(event):
        t=event.get('time')
        return (verified and event.get('event')=='page_error' and event.get('error_type')=='PageCancelled'
                and isinstance(t,(int,float)) and start<=t<=end)
    return [e for e in events if e.get('event') in ('row_error','page_error','directory_rpc_error') and not expected(e)]


class PagingProbe:
    def __init__(self, base, out):
        import xbmc
        import xbmcgui
        import xbmcvfs
        self.xbmc, self.gui = xbmc, xbmcgui
        self.monitor = xbmc.Monitor()
        self.base, self.out = Path(base), Path(out)
        self.start = time.monotonic()
        self.deadline = min(self.start + 240, globals().get('SHARED_DEADLINE', float('inf')))
        self.work_deadline = self.deadline - 15
        self.window = None
        self.view = None
        self.log = Path(xbmcvfs.translatePath('special://profile/')) / 'addon_data/script.blacklanturn.preview/logs/live-runtime.jsonl'
        self.log_cursor = None
        self.log_identity = None
        self.events = []
        self.wait_context = None
        self.last_snapshot = None
        self.last_rejection = None
        self.R = {'status': 'running', 'completed': False, 'passed': False,
                  'stage': 'discover current Home', 'pid': os.getpid(), 'started_epoch': time.time(),
                  'timing': 'native monotonic; ordinary Action input to stable rendered cards; retained caches',
                  'deadline_seconds': 240, 'cycles': [],
                  'device': globals().get('DEVICE_NAME', 'fire'), 'phase': globals().get('TRIAL_PHASE', 'unspecified'),
                  'acceptance_scope': 'passed covers ordinary paging and metadata integrity; preload coverage is reported separately',
                  'cancellation': {'status': 'unavailable', 'reason': 'No owned in-flight preload observed'},
                  'metadata_scope': 'Full provider art/playcount/resume fields plus rendered paths/art/watch labels; no playback/history actions',
                  'prepared_event_requirement': {'event': 'next_page_prepared', 'fields': ['time', 'generation', 'revision', 'target_sha256 (SHA256 of exact route) or target']}}

    def save(self):
        self.base.mkdir(parents=True, exist_ok=True)
        self.R['elapsed_seconds'] = round(time.monotonic() - self.start, 3)
        pending = self.out.with_suffix('.pending')
        pending.write_text(json.dumps(self.R, indent=2), encoding='utf-8')
        pending.replace(self.out)

    def stage(self, name):
        self.R['stage'] = name
        self.save()

    def read_labels(self,labels):
        request={'jsonrpc':'2.0','id':1,'method':'XBMC.GetInfoLabels','params':{'labels':list(labels)}}
        if hasattr(self,'_trace'):self._trace('GUI-label-batch','begin')
        try:
            response=json.loads(self.xbmc.executeJSONRPC(json.dumps(request)))
            if 'error' in response:raise RuntimeError('GUI label dispatch failed')
            return response['result']
        finally:
            if hasattr(self,'_trace'):self._trace('GUI-label-batch','end')

    def info(self,label):
        return self.read_labels([label]).get(label,'')

    def prop(self, name):
        return self.info('Window(%s).Property(%s)' % (self.window, name))

    def focus(self):
        return int(self.info('System.CurrentControlId') or 0)

    def rpc(self, method):
        response = json.loads(self.xbmc.executeJSONRPC(json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method})))
        if 'error' in response:
            raise RuntimeError(method + ' failed: ' + str(response['error']))
        return response['result']

    def action(self, name):
        if self.gui.getCurrentWindowId() != self.window:
            raise RuntimeError('Current controller window changed before ordinary input')
        self.xbmc.executebuiltin('Action(' + name + ')', False)

    def wait(self, test, seconds=15, recovery=False):
        end = min(time.monotonic() + seconds, self.deadline if recovery else self.work_deadline)
        while time.monotonic() < end and not self.monitor.abortRequested():
            result = test()
            if result:
                return result
            self.monitor.waitForAbort(.05)
        self.capture_timeout(seconds, recovery)
        raise RuntimeError('Native timeout at ' + self.R['stage'])

    def cheap_snapshot(self):
        view=self.view
        names=('System.CurrentControlId','Container(900).NumItems','Container(900).ListItem.Property(pageControl)','Container(900).ListItem.FileNameAndPath','Container(900).ListItemAbsolute(0).FileNameAndPath')
        props=('eyebrow','rowState0','notice','preview','loading')
        keys=list(names)+['Window(%s).Property(%s)' % (self.window,n) for n in props]
        values=self.read_labels(keys);read=lambda key:values.get(key,'');prop=lambda n:read('Window(%s).Property(%s)' % (self.window,n))
        out={'window':self.gui.getCurrentWindowId(),'expected_window':self.window,'focus':int(read(names[0]) or 0),'heading':prop('eyebrow'),'state':prop('rowState0'),'notice':prop('notice'),'preview':prop('preview'),'loading_property':prop('loading'),'native_count':int(read(names[1]) or 0),'selected_kind':read(names[2]),'selected_native_path':read(names[3])}
        if view is not None:
            out.update(path=view.paths[0],generation=view.generation,revision=getattr(view.result_cache,'revision',None),model_count=len(view.rows[0]),loading_paths=copy.deepcopy(getattr(view,'loading_paths',{})),row_window_busy=bool(getattr(view,'row_window_busy',False)))
            out['loading']=0 in out['loading_paths'] or out['loading_property']=='true'
            out['model_first_path']=view.rows[0][0].get('file') if view.rows[0] else None
            out['native_first_path']=read(names[4])
        return out

    def capture_timeout(self, seconds, recovery):
        diagnostic = {'stage': self.R['stage'], 'timeout_seconds': seconds, 'recovery': recovery,
                      'expected': copy.deepcopy(self.wait_context),
                      'raw_snapshot_rejection': copy.deepcopy(self.last_rejection),
                      'last_valid_raw_snapshot': self.last_snapshot}
        try:
            diagnostic['ui'] = self.cheap_snapshot()
            self.read_events()
            diagnostic['events_tail'] = self.events[-80:]
        except Exception as exc:
            diagnostic['diagnostic_error'] = type(exc).__name__ + ': ' + str(exc)
        self.R.setdefault('timeouts', []).append(diagnostic)
        self.save()

    def guard(self):
        if self.gui.getCurrentWindowId() != self.window:
            raise RuntimeError('Controller window changed during paging')
        if self.view is not None and not getattr(self.view, 'alive', False):
            raise RuntimeError('Original controller is no longer alive')
        self.read_events()
        if any(event.get('event') == 'live_opened' for event in self.events):
            raise RuntimeError('Controller reinitialized during paging')

    def baseline_events(self):
        raw = self.log.read_bytes()
        end = raw.rfind(b'\n') + 1
        parsed = [json.loads(line) for line in raw[:end].splitlines() if line.strip()]
        stat = self.log.stat()
        self.log_identity = (stat.st_dev, stat.st_ino)
        self.log_cursor = end
        self.R['live_opened_before'] = sum(event.get('event') == 'live_opened' for event in parsed)
        self.R['log_start_byte'] = end

    def read_events(self):
        if self.log_cursor is None:
            return
        stat = self.log.stat()
        if (stat.st_dev, stat.st_ino) != self.log_identity or stat.st_size < self.log_cursor:
            raise RuntimeError('Runtime event log rotated; exact lifecycle delta unavailable')
        with self.log.open('rb') as stream:
            stream.seek(self.log_cursor)
            raw = stream.read(8 * 1024 * 1024 + 1)
        if len(raw) > 8 * 1024 * 1024:
            raise RuntimeError('Runtime log exceeded bounded read')
        end = raw.rfind(b'\n') + 1
        self.events.extend(json.loads(line) for line in raw[:end].splitlines() if line.strip())
        self.log_cursor += end

    def discover(self):
        current = self.gui.getCurrentWindowId()
        if current < 13000 or self.info('Window(%s).Property(eyebrow)' % current) != 'HOME':
            return False
        views = [item for item in gc.get_objects() if type(item).__name__ == 'LiveReview'
                 and type(item).__module__ == 'live_review' and getattr(item, 'alive', False)]
        if len(views) != 1:
            raise RuntimeError('Expected exactly one alive LiveReview in the existing interpreter')
        self.window, self.view = current, views[0]
        import threading,sys
        stream=(self.base/'boundaries.jsonl').open('a',encoding='utf-8',buffering=1)
        lock=threading.Lock()
        def trace(name,phase):
            with lock:
                stream.write(json.dumps({'time':time.time(),'method':name,'phase':phase,'thread':threading.current_thread().name,'ident':threading.get_ident(),'native_id':getattr(threading,'get_native_id',lambda:None)(),'generation':self.view.generation})+'\n');stream.flush()
        def wrap(original,name):
            def called(*args,**kw):
                trace(name,'begin')
                try:return original(*args,**kw)
                finally:trace(name,'end')
            return called
        for name in ('load_path','page_files','apply_row'):
            setattr(self.view,name,wrap(getattr(self.view,name),name))
        module=sys.modules['live_review'];module.media_item=wrap(module.media_item,'media_item')
        self._trace=trace;self._trace_stream=stream
        return True

    def both_rows_ready(self):
        self.guard()
        if self.prop('loading') == 'true' or getattr(self.view, 'row_window_busy', False):
            return False
        for row in (0, 1):
            state = self.prop('rowState' + str(row))
            count = int(self.info('Container(%d).NumItems' % (900 + row)) or 0)
            if state not in ('ready', 'empty') or count != len(self.view.rows[row]):
                return False
            if (state == 'ready') != bool(count):
                return False
        return not getattr(self.view, 'loading_paths', {})

    def raw_snapshot(self, row=0):
        self.guard()
        view = self.view
        generation, paths = view.generation, tuple(view.paths)
        owner = view.rows[row]
        source = copy.deepcopy(owner)
        cid = 900 + row
        props=('eyebrow','rowState'+str(row),'notice','loading')
        keys=['Container(%d).NumItems' % cid,'System.CurrentControlId','Container(%d).ListItem.Property(pageControl)' % cid,'Container(%d).ListItem.FileNameAndPath' % cid]+['Window(%s).Property(%s)' % (self.window,n) for n in props]
        for index,data in enumerate(source):
            prefix='Container(%d).ListItemAbsolute(%d).' % (cid,index)
            keys.extend(prefix+name for name in ('FileNameAndPath','Label','PlayCount','Property(pageControl)','Property(cardArtKind)','Property(watchState)','Property(watchLabel)','Property(watchPercent)'))
            art_keys=sorted(set((data.get('art') or {}).keys()) | {'poster','landscape','thumb','fanart','clearlogo','square','navigation'})
            keys.extend(prefix+'Art('+key+')' for key in art_keys)
        native_values=self.read_labels(keys)
        read=lambda label:native_values.get(label,'')
        prop=lambda n:read('Window(%s).Property(%s)' % (self.window,n))
        count = int(read('Container(%d).NumItems' % cid) or 0)
        if count != len(source):
            self.last_rejection = {'reason': 'native/model count mismatch', 'native_count': count, 'model_count': len(source)}
            return None
        cards = []
        for index, data in enumerate(source):
            prefix = 'Container(%d).ListItemAbsolute(%d).' % (cid, index)
            native_path = read(prefix + 'FileNameAndPath')
            native_kind = read(prefix + 'Property(pageControl)')
            native_label = read(prefix + 'Label')
            if not card_transport_matches(data, native_path, native_kind, native_label):
                self.last_rejection = {'reason': 'native/model card identity mismatch', 'index': index,
                    'native_path': native_path, 'model_path': data.get('file'), 'native_kind': native_kind,
                    'model_kind': data.get('_page_control', ''), 'native_label': native_label, 'model_label': data.get('label')}
                return None
            art_keys = sorted(set((data.get('art') or {}).keys()) | {'poster', 'landscape', 'thumb', 'fanart', 'clearlogo', 'square', 'navigation'})
            native = {'label': native_label, 'path': native_path, 'playcount': read(prefix + 'PlayCount'),
                      'art': {key: read(prefix + 'Art(' + key + ')') for key in art_keys}}
            for key in ('pageControl', 'cardArtKind', 'watchState', 'watchLabel', 'watchPercent'):
                native[key] = read(prefix + 'Property(' + key + ')')
            fields = ('title', 'label', 'filetype', 'art', 'thumbnail', 'uniqueid', 'playcount', 'resume', 'season', 'episode', 'showtitle')
            cards.append({'path': data['file'] if native_kind == 'previous' else native_path, 'kind': native['pageControl'],
                          'source': {key: data[key] for key in fields if key in data}, 'native': native,
                          'identity_basis': 'synthetic Previous action: exact kind and label' if native_kind == 'previous' else 'exact provider path',
                          'native_path_matches_model': native_path == data.get('file')})
        if generation != view.generation or paths != tuple(view.paths) or owner is not view.rows[row]:
            self.last_rejection = {'reason': 'model owner changed during raw snapshot', 'generation_before': generation, 'generation_after': view.generation}
            return None
        self.last_rejection = None
        return {'window': self.gui.getCurrentWindowId(), 'expected_window': self.window,
                'heading': prop('eyebrow'), 'state': prop('rowState' + str(row)),
                'notice': prop('notice'), 'loading': row in getattr(view, 'loading_paths', {}) or prop('loading') == 'true',
                'native_count': count, 'cards': cards, 'path': paths[row], 'generation': generation,
                'revision': getattr(view.result_cache, 'revision', None), 'focus': int(read('System.CurrentControlId') or 0),
                'selected_kind': read('Container(%d).ListItem.Property(pageControl)' % cid),
                'selected_path': read('Container(%d).ListItem.FileNameAndPath' % cid)}

    def stable_row(self, heading, expected_path=None, seconds=22, recovery=False):
        last = None
        since = 0
        self.wait_context = {'heading': heading, 'path': expected_path}
        self.last_snapshot = None
        self.last_rejection = None
        def ready():
            nonlocal last, since
            self.guard()
            cheap = self.cheap_snapshot()
            if (cheap['window'] != self.window or cheap['heading'] != heading or cheap['state'] != 'ready'
                    or cheap['loading'] or not cheap['native_count'] or cheap['native_count'] != cheap['model_count']
                    or (expected_path is not None and cheap['path'] != expected_path)):
                last = None
                return None
            value = self.raw_snapshot()
            if value:
                self.last_snapshot = value
            if not value or not row_ready(value, heading) or (expected_path is not None and value['path'] != expected_path):
                last = None
                return None
            signature = json.dumps({'cards': value['cards'], 'path': value['path'], 'generation': value['generation']}, sort_keys=True)
            if signature != last:
                last, since = signature, time.monotonic()
                return None
            return value if time.monotonic() - since >= .10 else None
        return self.wait(ready, seconds, recovery)

    def sidebar(self, recovery=False):
        histories=getattr(getattr(self,'view',None),'histories',[])
        attempts=12+max((len(h.pages) for h in histories),default=0)
        for _ in range(attempts):
            self.guard()
            if self.focus() == 50:
                self.monitor.waitForAbort(.15)
                if self.focus() == 50:
                    return
            if time.monotonic() >= (self.deadline if recovery else self.work_deadline):
                break
            self.action('Back')
            self.monitor.waitForAbort(.15)
        raise RuntimeError('Sidebar inaccessible')

    def section(self, name, recovery=False):
        self.sidebar(recovery)
        self.action('FirstPage')
        self.wait(lambda: self.info('Container(50).ListItem.Label') == 'Search', 3, recovery)
        for _ in range(12):
            label = self.info('Container(50).ListItem.Label')
            if label == name:
                break
            self.action('Down')
            self.wait(lambda: self.info('Container(50).ListItem.Label') != label, 3, recovery)
        else:
            raise RuntimeError('Missing sidebar section ' + name)
        self.action('Select')
        result = self.stable_row(name.upper(), seconds=30, recovery=recovery)
        if name == 'Shows':
            self.wait(lambda: self.focus() == 900, 4, recovery)
        return result

    def edge(self, kind):
        self.action('LastPage' if kind == 'next' else 'FirstPage')
        self.wait(lambda: self.focus() == 900 and self.info('Container(900).ListItem.Property(pageControl)') == kind, 3)
        return self.info('Container(900).ListItem.FileNameAndPath')

    def click_page(self, kind, target, seconds=24):
        if self.info('Container(900).ListItem.Property(pageControl)') != kind:
            raise RuntimeError('Paging selection changed before Select')
        if self.info('Container(900).ListItem.FileNameAndPath') != target:
            raise RuntimeError('Paging target changed before Select')
        expected = page_destination(kind, target, copy.deepcopy(self.view.histories[0].pages))
        self.R['pending_click'] = {'kind': kind, 'selected_native_path': target,
            'expected_controller_path': expected, 'before': self.cheap_snapshot(), 'epoch': time.time()}
        self.save()
        started = time.monotonic()
        self.action('Select')
        page = self.stable_row('SHOWS', expected, seconds=seconds)
        self.R.pop('pending_click', None)
        return {'seconds': round(time.monotonic() - started, 3), 'expected_path': expected, 'page': page}

    def owned_job(self, key):
        ahead = getattr(self.view, 'page_ahead', None)
        job = getattr(ahead, 'job', None)
        return job if job and tuple(job[0]) == tuple(key) and not job[1].is_set() else None

    def cancellation(self):
        self.stage('observe pending preload cancellation')
        # Finish on the already visited next page, then approach an unvisited
        # following page so a cached completed job cannot masquerade as pending.
        target = self.edge('next')
        self.click_page('next', target)
        origin = self.stable_row('SHOWS')
        target = self.edge('next')
        key = (origin['generation'], origin['revision'], target)
        end = min(time.monotonic() + 5, self.work_deadline - 15)
        job = None
        while time.monotonic() < end:
            self.guard()
            job = self.owned_job(key)
            if job:
                break
            self.monitor.waitForAbort(.02)
        if job is None:
            self.R['cancellation']['reason'] = 'No matching unfinished PageAhead job observed within five seconds; cached/disabled/too-fast remains possible'
            return
        observed = time.monotonic()
        # Capture the exact Python Event without calling controller methods or
        # changing locks, generations, caches, flags, or worker state.
        self.R['cancellation'] = {'status': 'observed', 'target_sha256': hashlib.sha256(target.encode()).hexdigest(),
                                  'generation': key[0], 'revision': key[1], 'unfinished_before_navigation': not job[1].is_set()}
        self.guard()
        if job[1].is_set():
            self.R['cancellation'].update(status='unavailable', reason='Matching preload finished before the first navigation input')
            return
        self.R['cancellation']['unfinished_at_first_back'] = True
        self.R['cancellation']['first_back_epoch']=time.time()
        self.action('Back')
        self.monitor.waitForAbort(.10)
        self.sidebar()
        home = self.section('Home')
        self.sidebar()
        end = min(time.monotonic() + 8, self.work_deadline)
        while time.monotonic() < end and not job[1].is_set():
            self.guard()
            if self.prop('eyebrow') != 'HOME':
                raise RuntimeError('Obsolete preload displaced Home')
            self.monitor.waitForAbort(.05)
        self.monitor.waitForAbort(.20)
        final = self.stable_row('HOME', home['path'], seconds=3)
        comparison = metadata_equality(home['cards'], final['cards'])
        if not comparison['equal']:
            raise RuntimeError('Home metadata changed after cancelled navigation')
        self.R['cancellation'].update({'status': 'passed' if job[1].is_set() else 'unavailable',
            'worker_finished': job[1].is_set(), 'home_preserved': comparison,
            'elapsed_seconds': round(time.monotonic() - observed, 3)})
        self.R['cancellation']['finished_epoch']=time.time()
        if not job[1].is_set():
            self.R['cancellation']['reason'] = 'Owned job did not finish inside the bounded observation; no stale publication observed'

    def run(self):
        try:
            self.save()
            self.wait(self.discover, 35)
            self.stable_row('HOME', seconds=30)
            self.wait(self.both_rows_ready, 25)
            if self.rpc('Player.GetActivePlayers'):
                raise RuntimeError('Playback active before paging; left untouched')
            self.baseline_events()
            self.R['ui_window'] = self.window
            self.R['controller_python_identity'] = id(self.view)
            self.stage('Shows trending route')
            current = self.section('Shows')
            from urllib.parse import parse_qs, urlsplit
            route = parse_qs(urlsplit(current['path']).query)
            if route.get('tmdb_type') != ['tv'] or route.get('info') not in (['trending_week'], ['trending_day'], ['trakt_trending']):
                raise RuntimeError('Shows row is not the expected existing trending TV route')
            self.R['initial_page'] = current
            for cycle in range(3):
                self.stage('next/back cycle ' + str(cycle + 1))
                before = self.stable_row('SHOWS')
                event_epoch = time.time()
                target = self.edge('next')
                key = (before['generation'], before['revision'], target)
                # Bounded ordinary dwell; no event means ordinary-next timing,
                # never an invented prepared-page success.
                dwell_end = min(time.monotonic() + (1 if cycle == 0 else 4), self.work_deadline)
                prepared = None
                while time.monotonic() < dwell_end:
                    self.guard()
                    prepared = matching_prepared_event(self.events, key, event_epoch)
                    if prepared:
                        break
                    self.monitor.waitForAbort(.05)
                forward = self.click_page('next', target)
                previous = self.edge('previous')
                # The actual previous card is an ordinary navigation route.
                backward = self.click_page('previous', previous)
                equality = metadata_equality(before['cards'], backward['page']['cards'])
                result = {'cycle': cycle + 1, 'next': forward, 'previous': backward,
                    'metadata_restored': equality, 'prepared_event': prepared, 'passed': False,
                    'next_classification': 'prepared' if prepared else 'ordinary; preparation unverified'}
                self.R['cycles'].append(result)
                self.save()
                if backward['page']['path'] != before['path'] or not equality['equal']:
                    raise RuntimeError('Previous did not restore exact title order/art/watch/resume')
                if backward['page']['selected_kind'] != 'next':
                    raise RuntimeError('Previous did not restore selected Next card')
                result['passed'] = True
                self.save()
                # Advance once so subsequent cycles cover new provider pages.
                if cycle < 2:
                    target = self.edge('next')
                    self.click_page('next', target)
            self.R['prepared_replays']=[]
            for replay in range(30):
                self.stage('prepared-page replay '+str(replay+1))
                before=self.stable_row('SHOWS')
                target=self.edge('next');forward=self.click_page('next',target)
                previous=self.edge('previous');backward=self.click_page('previous',previous)
                equality=metadata_equality(before['cards'],backward['page']['cards'])
                self.R['prepared_replays'].append({'index':replay+1,'next_seconds':forward['seconds'],'previous_seconds':backward['seconds'],'metadata':equality})
                self.save()
                if not equality['equal']:raise RuntimeError('Prepared replay changed metadata')
            self.cancellation()
            self.stage('return Home/sidebar')
            self.section('Home')
            self.sidebar()
            self.guard()
            self.R['active_players'] = self.rpc('Player.GetActivePlayers')
            if self.R['active_players']:
                raise RuntimeError('Unexpected playback during paging')
            self.R['final_ui'] = {'window': self.gui.getCurrentWindowId(), 'heading': self.prop('eyebrow'), 'focus': self.focus()}
            self.R['completed'] = True
            self.R['status'] = 'completed'
        except Exception as exc:
            self.R.update(status='failed', error=str(exc), traceback=traceback.format_exc())
            try:
                if self.view is not None and not self.rpc('Player.GetActivePlayers'):
                    self.section('Home', recovery=True)
                    self.sidebar(recovery=True)
                    self.R['recovered_home'] = True
            except Exception as recovery:
                self.R['recovery_error'] = str(recovery)
        finally:
            try:
                self.read_events()
                if self.log_cursor is not None:
                    delta = sum(event.get('event') == 'live_opened' for event in self.events)
                    self.R['live_opened_delta'] = delta
                    self.R['live_opened_after'] = self.R['live_opened_before'] + delta
                    self.R['lifecycle_count_exact'] = True
                    self.R['runtime_errors']=runtime_failures(self.events,self.R['cancellation'])
                    self.R['expected_page_cancellations']=[e for e in self.events if e.get('event')=='page_error' and e not in self.R['runtime_errors']]
                    self.R['events'] = self.events
                    self.R['passed'] = bool(self.R['completed'] and len(self.R['cycles']) == 3
                        and all(cycle['passed'] for cycle in self.R['cycles']) and delta == 0 and not self.R['runtime_errors'])
                else:
                    self.R['lifecycle_count_exact'] = False
            except Exception as exc:
                self.R['lifecycle_count_exact'] = False
                self.R['audit_error'] = str(exc)
                self.R['passed'] = False
            self.R['prepared_page_verified'] = any(cycle.get('prepared_event') for cycle in self.R['cycles'])
            self.R['pending_cancellation_verified'] = self.R['cancellation']['status'] == 'passed'
            self.R['preload_coverage_complete'] = bool(self.R['prepared_page_verified'] and self.R['pending_cancellation_verified'])
            observed = {}
            for cycle in self.R['cycles']:
                for card in cycle['previous']['page']['cards']:
                    if not card['kind']:
                        observed[card['path']] = card['source']
            self.R['metadata_fixture_coverage'] = {
                'unique_titles': len(observed),
                'artwork_present': sum(bool(item.get('art')) for item in observed.values()),
                'playcount_present': sum('playcount' in item for item in observed.values()),
                'resume_present': sum('resume' in item for item in observed.values()),
                'watched_titles': sum(isinstance(item.get('playcount'), (int, float)) and item['playcount'] > 0 for item in observed.values()),
                'in_progress_titles': sum(isinstance(item.get('resume'), dict) and isinstance(item['resume'].get('position'), (int, float)) and item['resume']['position'] > 0 for item in observed.values()),
                'note': 'Zero watched/in-progress titles means those nonzero fixtures were unavailable; no history was manufactured'}
            self.save()
        return self.R


def main(base=None, out=None):
    base = Path(base or globals().get('BASE') or Path(__file__).parent)
    out = Path(out or globals().get('OUT') or base / 'paging.json')
    return PagingProbe(base, out).run()


if __name__ == '__main__':
    main()
