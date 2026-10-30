"""Branded next-series chooser: inspect/save/open only, never autoplay."""
import json,threading,time
from pathlib import Path
import xbmc,xbmcgui
from live_runtime import read_controller_config,write_controller_config
from title_preferences import title_key
from personal_library import snapshot
from youtube_core import end_card_height

class SeriesEndDialog(xbmcgui.WindowXMLDialog):
    def onInit(self):
        self.result=None;self.active=True;self.modal=False;self.selection=0
        self.setProperty('suggestions','true');self.setProperty('details','false')
        self.setProperty('endedTitle','You’re caught up with '+str(self.target.get('showtitle') or self.target.get('tvshowtitle') or 'this series'))
        art=self.target.get('art') or {};self.setProperty('backdrop',art.get('fanart') or art.get('landscape') or 'blacklanturn-splash.png')
        self.setProperty('suggestionSource','More shows to explore');self.setProperty('status','Choose a show for Details · Nothing starts automatically')
        labels=['System.ScreenWidth','System.ScreenHeight']
        screen=json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc':'2.0','id':1,'method':'XBMC.GetInfoLabels','params':{'labels':labels}}))).get('result',{})
        height=end_card_height(screen.get(labels[0]),screen.get(labels[1]))
        for n in range(3):
            exists=n<len(self.items)
            for cid in (7000,7100,7200,7300,7400):self.getControl(cid+n).setVisible(exists)
            if not exists:continue
            item=self.items[n];art=item.get('art') or {}
            wide=art.get('landscape') or art.get('fanart') or art.get('thumb') or item.get('thumbnail') or art.get('poster','')
            self.setProperty('cardThumb'+str(n),wide);self.setProperty('cardTitle'+str(n),item.get('title') or item.get('label','Show'))
            genre=item.get('genre') or [];genre=' / '.join(genre[:2]) if isinstance(genre,list) else str(genre)
            self.setProperty('cardCaption'+str(n),' · '.join(str(v) for v in (item.get('year') or '',genre) if v))
            self.getControl(7100+n).setHeight(height);self.getControl(7200+n).setHeight(height+10)
            self.getControl(7300+n).setPosition(134+556*n,348+height+18)
            self.getControl(7400+n).setPosition(134+556*n,348+height+123)
            self.getControl(7000+n).setHeight(height+150)
            self.getControl(7000+n).controlRight(self.getControl(7000+min(n+1,len(self.items)-1)))
        self.setFocusId(7000)
        threading.Thread(target=self.monitor,name='BlackLanturnSeriesDialog',daemon=True).start()
    def monitor(self):
        monitor=xbmc.Monitor()
        while self.active and not monitor.abortRequested():
            if not self.session.current() or xbmc.Player().isPlaying():self.finish();return
            if monitor.waitForAbort(.2):return
    def finish(self):self.active=False;self.close()
    def selected(self):return self.items[max(0,min(self.selection,len(self.items)-1))]
    def details(self):
        item=self.selected();self.setProperty('detailTitle',item.get('title') or item.get('label',''))
        self.setProperty('detailBody',item.get('plot') or 'No description available.');self.setProperty('details','true');self.setFocusId(7020)
    def save_selected(self):
        try:
            path=self.session.store/'rows.json';config=read_controller_config(path);item=self.selected();saved=config.setdefault('Saved',[])
            if not isinstance(saved,list):raise ValueError('Saved titles could not be read')
            if not any(title_key(x)==title_key(item) for x in saved):saved.append(snapshot(item));write_controller_config(path,config)
            xbmcgui.Dialog().notification('My Stuff','Saved on this device',time=2000)
        except (OSError,ValueError,TypeError):xbmcgui.Dialog().notification('My Stuff','Could not save; your existing data was kept')
    def onClick(self,cid):
        if cid in (7000,7001,7002):self.selection=cid-7000;self.details()
        elif cid==7010:self.result={'action':'series','item':self.selected()};self.finish()
        elif cid==7011:self.save_selected()
        elif cid==7012:self.finish()
        elif cid==7013:
            try:
                path=self.session.store/'rows.json';config=read_controller_config(path);config['SeriesEndSuggestions']=False;write_controller_config(path,config);self.finish()
            except (OSError,ValueError,TypeError):xbmcgui.Dialog().notification('BlackLanturn','Could not save this preference')
        elif cid==7014:self.details()
        elif cid==7020:self.setProperty('details','false');self.setFocusId(7000+self.selection)
    def onFocus(self,cid):
        if cid in (7000,7001,7002):self.selection=cid-7000
    def onAction(self,action):
        if action.getId() in (9,10,92):
            if self.getProperty('details')=='true':self.onClick(7020)
            else:self.finish()
        elif action.getId() in (117,101):self.details()
