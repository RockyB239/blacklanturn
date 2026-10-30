"""One cancellable late-playback lookup; never waits during playback return."""
import threading,time
from pathlib import Path
from series_end_core import observed_episode,completed_latest,map_recommendations,suggestions,should_offer
from live_core import episode_identity
from title_preferences import TitlePreferences
from live_runtime import read_controller_config

class SeriesEndSession:
    def __init__(self,target,owner_skin):
        import xbmcaddon,xbmcvfs
        self.target=target or {};self.owner_skin=owner_skin;self.alive=True;self.invalid=False
        self.key=None;self.items=[];self.qualified=False;self.reason='';self.attempted=set();self.worker=None
        self.store=Path(xbmcvfs.translatePath(xbmcaddon.Addon('script.blacklanturn.preview').getAddonInfo('profile')))
        self.profile=Path(xbmcvfs.translatePath('special://profile/'))/'addon_data/plugin.video.themoviedb.helper'
        try:self.enabled=bool(episode_identity(self.target) and read_controller_config(self.store/'rows.json').get('SeriesEndSuggestions',True))
        except (OSError,ValueError,TypeError):self.enabled=False
    def current(self):
        import xbmc
        return self.alive and not self.invalid and xbmc.getSkinDir()==self.owner_skin
    def observe_current(self,player,current):
        if not self.enabled or not self.current():return
        key=observed_episode(self.target,current,player)
        if key is None:
            # Initial player metadata can be empty. Once observed, an episode
            # must remain identifiable; never offer its choices for another stream.
            if self.key is not None or current.get('type') in ('movie','episode') and (current.get('showtitle') or current.get('type')=='movie'):
                self.invalid=True;self.items=[];self.qualified=False
            return
        if self.key!=key:self.key=key;self.items=[];self.qualified=False;self.reason=''
        try:position=player.getTime();total=player.getTotalTime()
        except RuntimeError:return
        if total<60 or position<.5 or total-position>45 or key in self.attempted:return
        if self.worker and self.worker.is_alive():return
        self.attempted.add(key)
        def owned():return self.current() and self.key==key
        def work():
            try:
                from series_metadata import load_show_package
                from local_watch import hydrate_local
                package=load_show_package(key[0])
                if not owned() or not completed_latest(package,key):return
                items=hydrate_local(self.profile,map_recommendations(package))
                prefs=TitlePreferences(self.store/'title-preferences.json')
                if prefs.error:return
                choices=suggestions(items,key[0],prefs)
                if owned():self.items=choices;self.qualified=True
            except Exception:pass # Unknown availability must not become an end screen.
        self.worker=threading.Thread(target=work,name='BlackLanturnSeriesEnd',daemon=True);self.worker.start()
    def prompt(self):
        import xbmc
        try:enabled=read_controller_config(self.store/'rows.json').get('SeriesEndSuggestions',True)
        except (OSError,ValueError,TypeError):return None
        if not should_offer(self.reason,enabled,self.current() and not xbmc.Player().isPlaying(),self.qualified,bool(self.items)):return None
        from series_end_ui import SeriesEndDialog
        dialog=SeriesEndDialog('SeriesEnd.xml',str(Path(__file__).parent),'Default','1080i')
        dialog.items=self.items;dialog.target=self.target;dialog.session=self
        dialog.doModal();result=dialog.result;del dialog
        return result
    def close(self):self.alive=False
