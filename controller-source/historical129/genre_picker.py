"""Labelled native grid over the configured genre/category pages."""
from pathlib import Path
import xbmcgui
from navigation_core import default_icon
ROOT=Path(__file__).resolve().parent
class GenrePicker(xbmcgui.WindowXMLDialog):
    def onInit(self):
        self.result=None
        self.choices=[{'id':'','label':'All'}]+list(self.pages)
        self.setProperty('section','Browse '+self.section)
        items=[]
        for page in self.choices:
            item=xbmcgui.ListItem(label=page['label'])
            aliases={'All':'collections','Action & Adventure':'adventure','Sci-Fi & Fantasy':'science-fiction','Westerns':'western'}
            icon=aliases.get(page['label']) or default_icon(page['label'],{'kind':'page'})
            artwork=str(ROOT/'resources/media'/(icon+'.png'))
            item.setArt({'icon':artwork,'thumb':artwork});items.append(item)
        panel=self.getControl(5000);panel.reset();panel.addItems(items)
        panel.selectItem(next((n for n,p in enumerate(self.choices) if p['id']==self.current_page),0))
        self.setFocusId(5000)
    def onClick(self,cid):
        if cid==5000:
            index=self.getControl(5000).getSelectedPosition()
            if 0<=index<len(self.choices):self.result=self.choices[index]['id']
            self.close()
        elif cid==5001:self.close()
    def onAction(self,action):
        if action.getId() in (9,10,92,216,247):self.close()
def choose_genre(section,pages,current_page):
    dialog=GenrePicker('GenrePicker.xml',str(ROOT),'Default','1080i')
    dialog.section=section;dialog.pages=pages;dialog.current_page=current_page;dialog.result=None
    dialog.doModal();result=dialog.result;del dialog
    return result
