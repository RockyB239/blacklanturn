"""Presentation state only. Original OpenWizard routes remain authoritative."""
import re
from urllib.parse import urlencode, parse_qsl

def encode(params):return urlencode(params)
def decode(query):return dict(parse_qsl(query.lstrip('?')))
def plain(text):
    return re.sub(r'\[/?(?:COLOR(?: [^\]]+)?|B|I|UPPERCASE|LOWERCASE)\]', '', text or '', flags=re.I)
def entry(label, params, description, folder, icon='', fanart=''):
    label=plain(label)
    if '=' in label and not label.replace('=','').strip():return None
    if label.startswith('===') or not label.strip():return None
    return {'label':label,'params':dict(params or {}),'description':plain(description),
            'folder':bool(folder),'icon':icon,'fanart':fanart}
def capture(directory, producer):
    rows=[];original=directory._add_menu_item
    def collect(display,params,menu,description,overwrite,fanart,icon,themeit,isFolder):
        row=entry(display,params,description,isFolder,icon,fanart)
        if row:rows.append(row)
        return True
    directory._add_menu_item=collect
    try:producer()
    finally:directory._add_menu_item=original
    return rows

def activation(row,supported):return 'open' if supported else 'action'
def handoff(params):
    return (params.get('mode') in {'forceskin','forceprofile','buildpreview','viewVideo','kodiapk','speedtest'}
            or (params.get('mode') == 'install' and params.get('action') in {'update','normal'}))

def perform(params,dispatch,refresh):
    dispatch(dict(params))
    # An update may have replaced this running Installer. Its old Python
    # session must finish without reading new settings or reopening navigation.
    if not handoff(params):refresh()

class Navigation:
    def __init__(self,route=None,title='Home'):
        self.route=dict(route or {});self.title=title;self.selected=0;self.stack=[];self.initial_selection=True
    def push(self,route,title):
        self.stack.append((self.route,self.title,self.selected))
        self.route=dict(route);self.title=title;self.selected=0;self.initial_selection=True
    def switch(self,route,title):
        self.stack=[];self.route=dict(route);self.title=title;self.selected=0;self.initial_selection=True
    def back(self):
        if self.stack:self.route,self.title,self.selected=self.stack.pop();self.initial_selection=False;return True
        if self.route:self.switch({},'Home');return True
        return False
