"""Labelled native grid over the configured genre/category pages."""
from pathlib import Path
import threading
import xbmcgui
from navigation_core import default_icon
ROOT=Path(__file__).resolve().parent
class GenrePicker(xbmcgui.WindowXMLDialog):
    def onInit(self):
        from icon_packs import icon_path
        from shelf_tools import STREAMING_GENRE_ID
        self.result=None
        self.choices=[{'id':'','label':'All'},{'id':STREAMING_GENRE_ID,'label':'Streaming Services'}]+list(self.pages)
        self.setProperty('genreOverflow','true' if len(self.choices)>18 else 'false')
        self.setProperty('section','Browse '+self.section)
        items=[]
        for page in self.choices:
            item=xbmcgui.ListItem(label=page['label'])
            if getattr(self,'observe',None):item.setProperty('genreLookaheadId',page['id'])
            aliases={'Streaming Services':'services','All':'collections','Action & Adventure':'adventure','Sci-Fi & Fantasy':'science-fiction','Westerns':'western'}
            icon=aliases.get(page['label']) or default_icon(page['label'],{'kind':'page'})
            artwork=icon_path(ROOT,icon,getattr(self,'pack','original'))
            item.setArt({'icon':artwork,'thumb':artwork});items.append(item)
        panel=self.getControl(5000);panel.reset();panel.addItems(items)
        panel.selectItem(next((n for n,p in enumerate(self.choices) if p['id']==self.current_page),0))
        self.setFocusId(5000)
        if getattr(self,'observe',None):
            def watch_focus():
                keys=['System.CurrentControlId','Container(5000).ListItem.Property(genreLookaheadId)']
                while not self.closed_for_lookahead.wait(.1):
                    try:
                        state=self.read_labels(keys)
                        if self.closed_for_lookahead.is_set():return
                        self.observe(state[keys[1]] if state[keys[0]]=='5000' else '')
                    except (RuntimeError, KeyError):
                        return
            threading.Thread(target=watch_focus,name='BlackLanturnGenreFocus',daemon=True).start()
    def onClick(self,cid):
        if cid==5000:
            index=self.getControl(5000).getSelectedPosition()
            if 0<=index<len(self.choices):self.result=self.choices[index]['id']
            self.close()
        elif cid==5001:self.close()
    def onAction(self,action):
        if action.getId() in (9,10,92,216,247):self.close()
def choose_genre(section,pages,current_page,pack='original',observe=None,read_labels=None):
    dialog=GenrePicker('GenrePicker.xml',str(ROOT),'Default','1080i')
    dialog.section=section;dialog.pages=pages;dialog.current_page=current_page;dialog.pack=pack;dialog.result=None
    dialog.observe=observe;dialog.read_labels=read_labels;dialog.closed_for_lookahead=threading.Event()
    try:
        dialog.doModal()
        return dialog.result
    finally:
        dialog.closed_for_lookahead.set()
