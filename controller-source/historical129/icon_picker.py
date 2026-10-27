"""Remote-friendly, artwork-only native grid. Selection returns a stable icon ID."""
from pathlib import Path
import xbmcgui
from navigation_core import ICON_CHOICES
ROOT=Path(__file__).resolve().parent

class IconPicker(xbmcgui.WindowXMLDialog):
    def onInit(self):
        self.result=None
        self.choices=ICON_CHOICES
        items=[]
        for icon_id,label in self.choices:
            item=xbmcgui.ListItem(label=label)
            artwork=str(ROOT/'resources/media'/(icon_id+'.png'))
            item.setArt({'icon':artwork,'thumb':artwork})
            items.append(item)
        panel=self.getControl(5000)
        panel.reset();panel.addItems(items)
        index=next((i for i,(icon_id,_) in enumerate(self.choices) if icon_id==self.current_icon),0)
        panel.selectItem(index);self.setFocusId(5000)

    def onClick(self,cid):
        if cid==5000:
            index=self.getControl(5000).getSelectedPosition()
            if 0<=index<len(self.choices):self.result=self.choices[index][0]
            self.close()
        elif cid==5001:self.close()

    def onAction(self,action):
        if action.getId() in (9,10,92,216,247):self.close()

def choose_icon(current_icon):
    dialog=IconPicker('IconPicker.xml',str(ROOT),'Default','1080i')
    dialog.current_icon=current_icon;dialog.result=None
    dialog.doModal()
    result=dialog.result
    del dialog
    return result
