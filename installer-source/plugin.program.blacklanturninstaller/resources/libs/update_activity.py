"""Temporary cross-script update activity; never a saved user preference."""
from contextlib import contextmanager
import json,math,threading,time,uuid,os,importlib.util
from pathlib import Path
KEY='BlackLanturn.UpdateActivity'
LEASE_SECONDS=10

def _window():
    import xbmcgui
    return xbmcgui.Window(10000)

def active(window=None,clock=time.time):
    try:
        value=json.loads((window or _window()).getProperty(KEY))
        until=value['until'];now=clock()
        return (isinstance(value['owner'],str) and bool(value['owner']) and type(until) in (int,float)
                and math.isfinite(until) and now<until<=now+LEASE_SECONDS+1)
    except (ImportError,AttributeError,RuntimeError,ValueError,TypeError,KeyError):return False

@contextmanager
def _exclusive(path):
    if path is None:
        yield;return
    path=Path(path).parent.resolve()/Path(path).name
    if any(p.is_symlink() for p in (path,*path.parents)):raise RuntimeError('The update lock path is linked. Nothing has changed.')
    spec=importlib.util.spec_from_file_location('_update_activity_lock',Path(__file__).with_name('portable_lock.py'))
    locks=importlib.util.module_from_spec(spec);spec.loader.exec_module(locks)
    descriptor=os.open(str(path),os.O_RDWR|os.O_CREAT|getattr(os,'O_NOFOLLOW',0),0o600)
    acquired=False
    try:
        try:locks.acquire(descriptor);acquired=True
        except BlockingIOError as exc:raise RuntimeError('Another BlackLanturn update is running. Keep Kodi open and let it finish.') from exc
        yield
    finally:
        if acquired:locks.unlock(descriptor)
        os.close(descriptor)

@contextmanager
def hold(window=None,lock_path=None):
    try:window=window or _window()
    except (ImportError,AttributeError,RuntimeError):
        yield;return
    if lock_path is None:
        try:
            import xbmcvfs
            lock_path=Path(xbmcvfs.translatePath('special://home/addons/'))/'.blacklanturn-download.lock'
        except (ImportError,AttributeError):pass
    with _exclusive(lock_path):
        owner=uuid.uuid4().hex;stop=threading.Event()
        def renew():window.setProperty(KEY,json.dumps({'owner':owner,'until':time.time()+LEASE_SECONDS}))
        renew()
        def heartbeat():
            while not stop.wait(2):
                try:renew()
                except (AttributeError,RuntimeError):return
        worker=threading.Thread(target=heartbeat,name='BlackLanturnUpdateLease',daemon=True);worker.start()
        try:yield
        finally:
            stop.set();worker.join(timeout=3)
            try:
                value=json.loads(window.getProperty(KEY))
                if value.get('owner')==owner:window.clearProperty(KEY)
            except (AttributeError,RuntimeError,ValueError,TypeError):pass
