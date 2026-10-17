"""Bounded native Fire search A/B/A protocol; existing provider caches retained."""
import copy
import gc
import hashlib
import json
import re
import time
import traceback
from pathlib import Path
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

BASE = Path(__file__).parent
OUT = BASE / 'benchmark.json'
MON = xbmc.Monitor()
START = globals().get('BOOT_MONO', time.monotonic())
DEVICE = globals().get('DEVICE_NAME', 'fire')
TRIAL_CONFIG = json.loads((BASE / 'trial.json').read_text(encoding='utf-8')) if (BASE / 'trial.json').is_file() else {}
PHASE = globals().get('TRIAL_PHASE', TRIAL_CONFIG.get('phase', 'unspecified'))
DEADLINE = min(START + 480, globals().get('SHARED_DEADLINE', float('inf')))
H = Path(xbmcvfs.translatePath('special://home/'))
PROFILE = Path(xbmcvfs.translatePath('special://profile/'))
ROWS = PROFILE / 'addon_data/script.blacklanturn.preview/rows.json'
BEFORE_ROWS = ROWS.read_bytes()
UI_WINDOW = None
VIEW = None
OWN_PREVIEW = False
BEFORE_SOFTWARE = None
R = {'status': 'running', 'device': DEVICE, 'phase': PHASE, 'stage': 'startup',
     'row_visits': [], 'searches': [], 'poll_seconds': .05,
     'timing': 'native monotonic clock; existing disk/provider caches retained',
     'deadline_seconds': 480}


def save():
    pending = OUT.with_suffix('.pending')
    pending.write_text(json.dumps(R, indent=2, ensure_ascii=False), encoding='utf-8')
    pending.replace(OUT)


def stage(name):
    R['stage'] = name
    save()


def rpc(method, params=None):
    value = json.loads(xbmc.executeJSONRPC(json.dumps(
        {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params or {}})))
    if 'error' in value:
        raise RuntimeError(method + ': ' + value['error'].get('message', 'RPC failure'))
    return value['result']


def info(key):
    response=rpc('XBMC.GetInfoLabels',{'labels':[key]})
    return response.get(key,'')


def unique_view():
    views = [obj for obj in gc.get_objects()
             if type(obj).__name__ == 'LiveReview'
             and type(obj).__module__ == 'live_review'
             and getattr(obj, 'alive', False)]
    if len(views) != 1:
        raise RuntimeError('Expected exactly one alive LiveReview; got ' + str(len(views)))
    return views[0]


def detect_ui():
    global UI_WINDOW, VIEW
    current = xbmcgui.getCurrentWindowId()
    if current >= 13000 and info('Window(' + str(current) + ').Property(eyebrow)') == 'HOME':
        view = unique_view()
        if view.getProperty('eyebrow') != 'HOME':
            return False
        UI_WINDOW, VIEW = current, view
        return True
    return False


def active_ui():
    return UI_WINDOW is not None and xbmcgui.getCurrentWindowId() == UI_WINDOW


def prop(key):
    return info('Window(' + str(UI_WINDOW or 13000) + ').Property(' + key + ')')


def focus():
    return int(info('System.CurrentControlId') or 0)


def count(number):
    return int(info('Container(' + str(number) + ').NumItems') or 0)


def label(number):
    return info('Container(' + str(number) + ').ListItem.Label')


def act(name):
    xbmc.executebuiltin('Action(' + name + ')', False)


def wait(test, seconds=12):
    end = min(time.monotonic() + seconds, DEADLINE)
    while not MON.abortRequested() and time.monotonic() < end:
        result = test()
        if result:
            return result
        MON.waitForAbort(.05)
    raise RuntimeError('Native timeout at ' + R['stage'])


def players():
    return rpc('Player.GetActivePlayers')


def snapshot():
    props=['eyebrow','rowState0','rowState1','row0','row1','preview']
    keys=['Window('+str(UI_WINDOW or 13000)+').Property('+n+')' for n in props]+['System.CurrentControlId','Container(900).NumItems','Container(901).NumItems']
    values=rpc('XBMC.GetInfoLabels',{'labels':keys});read=lambda key:values.get(key,'');prop_read=lambda n:read('Window('+str(UI_WINDOW or 13000)+').Property('+n+')')
    return {'window':xbmcgui.getCurrentWindowId(),'focus':int(read('System.CurrentControlId') or 0),'eyebrow':prop_read('eyebrow'),'states':[prop_read('rowState0'),prop_read('rowState1')],'model_states':[getattr(VIEW,'row_states',{}).get(i) for i in range(2)],'counts':[int(read('Container(%d).NumItems' % n) or 0) for n in (900,901)],'labels':[prop_read('row0'),prop_read('row1')],'preview':prop_read('preview')}


def valid_rows(state, heading=None):
    """A retained ready row whose underlying refresh failed is not accepted."""
    return (state['window'] == UI_WINDOW
            and (heading is None or state['eyebrow'] == heading)
            and all(state['states'][i] in ('ready', 'empty')
                    and state['model_states'][i] in ('ready', 'empty')
                    and state['states'][i] == state['model_states'][i]
                    and ((state['states'][i] == 'ready' and state['counts'][i] > 0)
                         or (state['states'][i] == 'empty' and state['counts'][i] == 0))
                    for i in range(2)))


def settled(heading=None):
    state = snapshot()
    return state if valid_rows(state, heading) else None


def search_label_matches(value, query, row_state):
    if row_state == 'empty':
        value = re.sub(r'\s+·\s+No titles$', '', value)
    return value.endswith(' · ' + query)


def cards_snapshot():
    """Allow a bounded render-frame lag without changing the measured latency."""
    view = unique_view()
    if view is not VIEW or not active_ui():
        raise RuntimeError('Controller or active window changed while reading cards')
    with view.preview_dispatch_lock:
        owner = (view.generation, tuple(view.paths), tuple(id(row) for row in view.rows))
        heading = prop('eyebrow')
    started = time.monotonic()
    deadline = min(started + 3, DEADLINE)
    last_valid = None
    last_rejection = None
    attempts = 0
    while time.monotonic() < deadline and not MON.abortRequested():
        attempts += 1
        with view.preview_dispatch_lock:
            if (view is not VIEW or not view.alive or not active_ui()
                    or owner != (view.generation, tuple(view.paths), tuple(id(row) for row in view.rows))):
                raise RuntimeError('Controller, window, or row owner changed while reading cards')
            before = snapshot()
            if (not active_ui()
                    or owner != (view.generation, tuple(view.paths), tuple(id(row) for row in view.rows))):
                raise RuntimeError('Window or row owner changed during metadata label read')
            if before['eyebrow'] != heading or 'error' in before['states'] + before['model_states']:
                raise RuntimeError('Heading or row error changed while reading cards: ' + str(before))
            counts_match = all(len(view.rows[i]) == before['counts'][i] for i in range(2))
            if valid_rows(before, heading) and counts_match:
                rows = copy.deepcopy(view.rows)
                cards = [[{'label': item.get('label'), 'title': item.get('title'),
                           'file': item.get('file'), 'art': item.get('art'),
                           'playcount': item.get('playcount'), 'resume': item.get('resume'),
                           'present': [key for key in ('file', 'art', 'playcount', 'resume') if key in item]}
                          for item in row] for row in rows]
                digest = hashlib.sha256(json.dumps(cards, sort_keys=True).encode('utf-8')).hexdigest()
                signature = (digest, tuple(before['states']), tuple(before['counts']), tuple(before['labels']))
                if signature == last_valid:
                    if (not active_ui()
                            or owner != (view.generation, tuple(view.paths), tuple(id(row) for row in view.rows))):
                        raise RuntimeError('Window or row owner changed during metadata copy')
                    if last_rejection is not None:
                        R.setdefault('metadata_capture_retries', []).append({
                            'stage': R['stage'], 'attempts': attempts,
                            'seconds': round(time.monotonic() - started, 3),
                            'last_rejection': last_rejection})
                    return {'paths': list(owner[1]), 'generation': owner[0], 'rows': cards, 'digest': digest}
                last_valid = signature
            else:
                last_rejection = before
                last_valid = None
        # No controller/provider callbacks, refetches, or waiting with its lock held.
        MON.waitForAbort(min(.05, max(0, deadline - time.monotonic())))
    R['metadata_capture_failure'] = {'stage': R['stage'], 'attempts': attempts,
                                     'seconds': round(time.monotonic() - started, 3),
                                     'last_rejection': last_rejection}
    raise RuntimeError('Stable metadata snapshot unavailable within three seconds')


def sidebar():
    for _ in range(15):
        if active_ui() and focus() == 50:
            MON.waitForAbort(.35)
            if active_ui() and focus() == 50:
                return
        act('Back')
        MON.waitForAbort(.35)
    raise RuntimeError('Sidebar inaccessible ' + str(snapshot()))


def select_section(name):
    sidebar()
    act('FirstPage')
    wait(lambda: active_ui() and label(50) == 'Search', 4)
    for _ in range(10):
        if label(50) == name:
            break
        old = label(50)
        act('Down')
        wait(lambda: active_ui() and label(50) != old, 4)
    else:
        raise RuntimeError('Missing section ' + name)
    started = time.monotonic()
    act('Select')
    MON.waitForAbort(.12)
    return started


def row_visit(name):
    started = select_section(name)
    state = wait(lambda: settled(name.upper()), 50)
    MON.waitForAbort(.12)
    state = wait(lambda: settled(name.upper()), 10)
    elapsed = time.monotonic() - started
    R['row_visits'].append({'section': name, 'seconds': round(elapsed, 3),
                            'ui': state, 'cards': cards_snapshot()})
    sidebar()
    save()


def search(query):
    # Preserve prior timing definition: first exact title then both rows stable .25 s.
    select_section('Home')
    wait(lambda: settled('HOME'), 30)
    sidebar()
    if DEVICE == 'apple':
        R['search_input'] = 'existing open_search(query=...) callback; tvOS keyboard excluded'
        started = time.monotonic()
        VIEW.open_search(query=query)
        VIEW.setFocusId(600)
    else:
        R['search_input'] = 'Kodi Input.SendText(done=True); keyboard typing excluded'
        select_section('Search')
        wait(lambda: xbmcgui.getCurrentWindowDialogId() == 10103
             or xbmcgui.getCurrentWindowId() == 10103, 8)
        started = time.monotonic()
        rpc('Input.SendText', {'text': query, 'done': True})
        wait(lambda: active_ui() and xbmcgui.getCurrentWindowDialogId() != 10103, 8)
    wait(lambda: active_ui() and prop('eyebrow') == 'SEARCH · ' + query
         and prop('rowState0') == 'ready'
         and getattr(VIEW, 'row_states', {}).get(0) == 'ready' and count(900) > 0
         and search_label_matches(prop('row0'), query, 'ready')
         and info('Container(900).ListItemAbsolute(0).Label').casefold() == query.casefold(), 65)
    first = time.monotonic() - started
    previous = None
    since = 0

    def stable():
        nonlocal previous, since
        state = settled('SEARCH · ' + query)
        if not state or not all(search_label_matches(state['labels'][i], query, state['states'][i])
                                for i in range(2)):
            previous = None
            return None
        signature = json.dumps(state['states'] + state['counts'] + state['labels'])
        if signature != previous:
            previous, since = signature, time.monotonic()
            return None
        return state if time.monotonic() - since >= .25 else None

    state = wait(stable, 65)
    both = time.monotonic() - started
    R['searches'].append({'query': query, 'first_seconds': round(first, 3),
                          'both_seconds': round(both, 3), 'ui': state, 'cards': cards_snapshot()})
    save()


def software():
    hashes = {}
    for addon in ('script.blacklanturn.preview', 'plugin.video.themoviedb.helper'):
        root = H / 'addons' / addon
        for file in root.rglob('*'):
            if file.is_file() and '__pycache__' not in file.parts and file.suffix not in ('.pyc', '.pyo'):
                hashes[addon + '/' + str(file.relative_to(root))] = hashlib.sha256(file.read_bytes()).hexdigest()
    return hashes


def nonsecret_settings():
    keys = {'plugin.video.umbrella': ['provider.external.enabled', 'external_provider.module',
            'external_provider.name', 'remove.hdr', 'remove.dolby.vision', 'remove.hevc'],
            'plugin.video.youtube': ['kodion.mpd.stream.select', 'kodion.video.stream.select',
            'kodion.mpd.quality.selection', 'kodion.mpd.videos'],
            'plugin.video.themoviedb.helper': ['artwork_quality', 'trakt_watchedindicators']}
    return {addon: {key: xbmcaddon.Addon(addon).getSetting(key) for key in fields}
            for addon, fields in keys.items()}


def core_settings():
    out = {}
    for key in ('filecache.memorysize', 'filecache.readfactor', 'filecache.buffermode',
                'filecache.chunksize', 'videoplayer.usemediacodecsurface',
                'videoplayer.usemediacodec', 'videoscreen.resolution'):
        try:
            out[key] = rpc('Settings.GetSettingValue', {'setting': key})['value']
        except RuntimeError:
            out[key] = 'unavailable'
    return out


def metrics():
    return {key: info(key) for key in ('System.FPS', 'System.Memory(used)', 'System.Memory(free)',
            'System.Memory(total)', 'System.CpuUsage', 'System.ScreenWidth', 'System.ScreenHeight')}


def seconds(value):
    return value['hours'] * 3600 + value['minutes'] * 60 + value['seconds'] + value['milliseconds'] / 1000


def preview_check():
    global OWN_PREVIEW
    stage('embedded preview')
    wait(lambda: active_ui() and prop('eyebrow') == 'SEARCH · October Sky' and count(900) > 0, 10)
    if focus() != 900:
        act('Down')
        MON.waitForAbort(.2)
    if focus() != 900:
        raise RuntimeError('Search result row not focused')
    act('FirstPage')
    MON.waitForAbort(.2)
    act('Select')
    wait(lambda: active_ui() and prop('page') == 'details' and focus() == 101, 12)
    if prop('title') != 'October Sky':
        raise RuntimeError('First search title differed: ' + prop('title'))
    if prop('previewsReady') != 'true':
        raise RuntimeError('YouTube preview is not configured')
    for _ in range(8):
        if focus() == 105:
            break
        old = focus()
        act('Right')
        wait(lambda: active_ui() and focus() != old, 3)
    else:
        raise RuntimeError('Preview button not available')
    started = time.monotonic()
    OWN_PREVIEW = True
    act('Select')

    def ready():
        if not active_ui():
            raise RuntimeError('Preview escaped the controller window')
        return players() if prop('preview') == 'playing' else None

    playing = wait(ready, 65)
    elapsed = time.monotonic() - started
    player_id = playing[0]['playerid']
    before = rpc('Player.GetProperties', {'playerid': player_id, 'properties': ['time', 'speed', 'currentvideostream']})
    # Observe the entire sample so a short fullscreen escape cannot be hidden.
    sample_start = time.monotonic()
    while time.monotonic() - sample_start < 5:
        if not active_ui():
            raise RuntimeError('Preview escaped the controller window during playback')
        if time.monotonic() >= DEADLINE or MON.abortRequested():
            raise RuntimeError('Deadline during preview sample')
        MON.waitForAbort(.05)
    after = rpc('Player.GetProperties', {'playerid': player_id, 'properties': ['time', 'speed']})
    advance = seconds(after['time']) - seconds(before['time'])
    act('Back')
    MON.waitForAbort(.3)
    sidebar()
    wait(lambda: not players(), 10)
    OWN_PREVIEW = False
    R['preview'] = {'status': 'passed' if advance >= 3.5 else 'stalled',
                    'start_seconds': round(elapsed, 3), 'advance_seconds': round(advance, 3),
                    'sample_seconds': 5, 'video': before['currentvideostream'],
                    'windowed': True, 'navigation_stopped': True}
    save()
    if R['preview']['status'] != 'passed':
        raise RuntimeError('Embedded preview did not advance normally')


def paging_check():
    script = BASE / 'native_paging.py'
    if not script.is_file():
        R['paging'] = {'status': 'not_run', 'reason': 'No native_paging.py staged'}
        raise RuntimeError('Required paging harness missing')
    stage('paging and cancellation')
    namespace = {'__name__': '__main__', '__file__': str(script), 'BASE': BASE,
                 'SHARED_DEADLINE': DEADLINE, 'DEVICE_NAME': DEVICE, 'TRIAL_PHASE': PHASE}
    exec(compile(script.read_text(encoding='utf-8'), str(script), 'exec'), namespace, namespace)
    report = json.loads((BASE / 'paging.json').read_text(encoding='utf-8'))
    R['paging'] = report
    save()
    if report.get('status') != 'completed' or report.get('passed') is not True:
        raise RuntimeError('Paging acceptance failed; see paging.json')
    R['preload_coverage_complete'] = report.get('preload_coverage_complete', False)
    # Coverage remains distinct from navigation success; baseline has no preloader.
    if PHASE in ('candidate', 'B') and not R['preload_coverage_complete']:
        raise RuntimeError('Candidate preloading coverage incomplete; see paging.json')


def restore_query():
    old = json.loads(BEFORE_ROWS)
    now = json.loads(ROWS.read_bytes())
    ignore_search = lambda value: {key: data for key, data in value.items() if key != 'SearchQuery'}
    view = unique_view()
    with view.preview_dispatch_lock:
        current_config = view.config
        if ignore_search(old) != ignore_search(now) or ignore_search(old) != ignore_search(current_config):
            R['search_query_restored'] = False
            R['config_changed_outside_search'] = True
            return
        if 'SearchQuery' in old:
            current_config['SearchQuery'] = old['SearchQuery']
        else:
            current_config.pop('SearchQuery', None)
        ROWS.write_bytes(BEFORE_ROWS)
        R['search_query_restored'] = (ROWS.read_bytes() == BEFORE_ROWS
                                     and current_config.get('SearchQuery') == old.get('SearchQuery')
                                     and ('SearchQuery' in current_config) == ('SearchQuery' in old))
        R['search_query_restored_in_memory'] = R['search_query_restored']


try:
    save()
    wait(detect_ui, 100)
    R['ui_window'] = UI_WINDOW
    ready_state = wait(lambda: settled('HOME'), 100)
    MON.waitForAbort(.1)
    ready_state = wait(lambda: settled('HOME'), 15)
    R['startup'] = {'controller_to_rows_seconds': round(time.monotonic() - START, 3),
                    'ready_epoch': time.time(), 'ui': ready_state}
    save()
    if players():
        raise RuntimeError('Playback active before benchmark; left untouched')
    sidebar()
    R['versions'] = {addon: xbmcaddon.Addon(addon).getAddonInfo('version') for addon in
                     ('script.blacklanturn.preview', 'skin.blacklanturn.preview',
                      'plugin.video.themoviedb.helper', 'plugin.video.youtube', 'plugin.video.umbrella')}
    R['kodi'] = rpc('Application.GetProperties', {'properties': ['version']})['version']
    R['before_settings'] = nonsecret_settings()
    R['before_core'] = core_settings()
    BEFORE_SOFTWARE = software()
    R['software_before_digest'] = hashlib.sha256(json.dumps(BEFORE_SOFTWARE, sort_keys=True).encode('utf-8')).hexdigest()
    R['idle_metrics'] = metrics()
    save()
    for cycle in range(4):
        stage('row visits ' + str(cycle + 1))
        for section in ('Shows', 'Movies', 'Home'):
            row_visit(section)
    for query in ['A24'] * 3 + ['October Sky'] * 3:
        stage('search ' + query + ' ' + str(len(R['searches']) + 1))
        search(query)
    preview_check()
    row_visit('Home')
    paging_check()
    row_visit('Home')
    sidebar()
    R['status'] = 'verification_pending'
except Exception as error:
    R['status'] = 'stopped'
    R['error'] = str(error)
    R['error_type'] = type(error).__name__
    R['traceback'] = traceback.format_exc()
    R['diagnostic'] = snapshot()
    try:
        # This run started its own preview only after confirming an idle player.
        if OWN_PREVIEW:
            act('Back')
            MON.waitForAbort(.5)
            for player in players():
                title = rpc('Player.GetItem', {'playerid': player['playerid'], 'properties': ['title']}).get('item', {}).get('title', '')
                if 'trailer' in title.lower() or 'october sky' in title.lower():
                    rpc('Player.Stop', {'playerid': player['playerid']})
        sidebar()
    except Exception:
        pass
finally:
    try:
        restore_query()
    except Exception as error:
        R['search_query_restored'] = False
        R['restore_error'] = type(error).__name__ + ': ' + str(error)
    try:
        R['after_settings'] = nonsecret_settings()
        R['after_core'] = core_settings()
        R['settings_unchanged'] = (R.get('before_settings') == R['after_settings']
                                   and R.get('before_core') == R['after_core'])
        R['software_unchanged'] = BEFORE_SOFTWARE is not None and software() == BEFORE_SOFTWARE
        R['final_ui'] = snapshot()
        R['active_players'] = players()
        acceptable = (R.get('preview', {}).get('status') == 'passed'
                      and R.get('paging', {}).get('passed') is True
                      and R['settings_unchanged'] and R['software_unchanged']
                      and R['search_query_restored'] and not R['active_players']
                      and active_ui() and focus() == 50 and prop('eyebrow') == 'HOME')
        R['acceptance_passed'] = bool(acceptable and R['status'] == 'verification_pending')
        if R['status'] == 'verification_pending':
            R['status'] = 'completed' if R['acceptance_passed'] else 'stopped'
            if not R['acceptance_passed']:
                R['error'] = 'Final preview, paging, preservation, or Home-idle acceptance failed'
    except Exception as error:
        R['status'] = 'stopped'
        R['final_verification_error'] = type(error).__name__ + ': ' + str(error)
    R['elapsed_seconds'] = round(time.monotonic() - START, 3)
    save()
