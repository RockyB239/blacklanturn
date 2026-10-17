"""One next-page worker, no queue and no separate result cache."""
import threading
from urllib.parse import urlsplit,parse_qs

def eligible(path):
    """Session-only read routes; native breadcrumb/cursor fields stay intact."""
    try:
        u=urlsplit(path);q=parse_qs(u.query,keep_blank_values=True)
        if (u.scheme,u.netloc,u.path)!=('plugin','plugin.video.themoviedb.helper','/') or u.fragment:return False
        if any(len(v)!=1 for v in q.values()):return False
        if q.get('info',[''])[0] not in ('trakt_trending','trakt_popular','search','popular','top_rated','upcoming','now_playing','trending_day','trending_week','airing_today','on_the_air','discover','similar','recommendations'):return False
        if q.get('tmdb_type',['movie'])[0] not in ('movie','tv','both','person','company','collection'):return False
        if not q.get('page',['1'])[0].isdigit() or not 1<=int(q.get('page',['1'])[0])<=10000:return False
        if not q.get('bl_start',['0'])[0].isdigit() or not 0<=int(q.get('bl_start',['0'])[0])<=10000:return False
        return True
    except (ValueError,TypeError):return False

class PageAhead:
    def __init__(self):
        self.lock=threading.Lock();self.job=None

    def start(self,key,fetch,current):
        with self.lock:
            if self.job and (self.job[0]==key or not self.job[1].is_set()):return False
            done=threading.Event();self.job=(key,done)
        def work():
            try:
                if current():fetch()
            except Exception:
                pass  # Foreground navigation retains normal retry/error handling.
            finally:done.set()
        threading.Thread(target=work,name='BlackLanturnNextPage',daemon=True).start()
        return True

    def wait(self,key,current):
        with self.lock:job=self.job
        if job and job[0]==key:
            while current() and not job[1].wait(.05):pass
