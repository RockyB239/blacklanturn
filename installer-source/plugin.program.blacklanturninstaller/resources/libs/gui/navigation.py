"""Branded navigation over OpenWizard's existing catalog and maintenance menus."""
import os,re
import xbmc, xbmcgui, xbmcplugin
from resources.libs.common.config import CONFIG
from resources.libs.common import directory, tools
from resources.libs.gui.navigation_model import Navigation, capture, entry, encode, perform, activation, handoff

SIDEBAR=[('Home',{},'home.png'),('Builds',{'mode':'builds'},'builds.png'),
 ('Maintenance',{'mode':'maint'},'maintenance.png'),('Save Data',{'mode':'savedata'},'savedata.png'),
 ('Addon Installer',{'mode':'addons'},'addoninstaller.png'),('More tools',{'mode':'tools'},'settings.png')]
MAINT={'clean':'clean_menu','addon':'addon_menu','logging':'logging_menu','misc':'misc_menu','backup':'backup_menu','tweaks':'tweaks_menu'}
SIMPLE={'savedata':'save_menu','trakt':'trakt_menu','realdebrid':'debrid_menu','login':'login_menu',
 'enableaddons':'enable_addons','removeaddondata':'remove_addon_data_menu','nettools':'net_tools',
 'systeminfo':'system_info','viewIP':'view_ip','youtube':'youtube_menu','apk':'apk_menu','developer':'developer'}

def producer(route):
    mode=route.get('mode');name=route.get('name')
    if mode=='builds':
        from resources.libs.gui.build_menu import BuildMenu
        return BuildMenu().get_listing
    if mode=='viewbuild':
        from resources.libs.gui.build_menu import BuildMenu
        return lambda:BuildMenu().view_build(name)
    if mode=='maint' and (not name or name in MAINT):
        from resources.libs.gui.maintenance_menu import MaintenanceMenu
        return getattr(MaintenanceMenu(),MAINT[name] if name else 'get_listing')
    if mode=='tools':return tools_menu
    if mode in SIMPLE:
        from resources.libs.gui import menu
        fn=getattr(menu,SIMPLE[mode])
        return (lambda:fn(route.get('url'))) if mode in ('apk','youtube') else fn
    if mode=='addons' and not route.get('action'):
        from resources.libs.gui.addon_menu import AddonMenu
        return lambda:AddonMenu().show_menu(url=route.get('url'))
    if mode=='advanced_settings' and route.get('action') in (None,'show_section','quick_configure'):
        from resources.libs import advanced
        a=advanced.AdvancedMenu()
        if route.get('action')=='quick_configure':return a.quick_configure
        return (lambda:a.show_section(route.get('tags'))) if route.get('action') else (lambda:a.show_menu(url=route.get('url')))
    return None

def tools_menu():
    specs=[('Installer settings',{'mode':'settings','name':CONFIG.ADDON_ID}),
           ('View Kodi log',{'mode':'viewlog'}),('View installer log',{'mode':'viewwizlog'}),
           ('View errors in log',{'mode':'viewerrorlog'}),('View latest error',{'mode':'viewerrorlast'}),
           ('Upload log file',{'mode':'uploadlog'})]
    if getattr(CONFIG,'HIDECONTACT','Yes')=='No':specs.append(('Help & contact',{'mode':'contact'}))
    if getattr(tools,'platform',lambda:None)()=='android' or getattr(CONFIG,'DEVELOPER','false')=='true':specs.append(('APK Installer',{'mode':'apk'}))
    if getattr(CONFIG,'YOUTUBETITLE',''):specs.append((CONFIG.YOUTUBETITLE,{'mode':'youtube'}))
    if getattr(CONFIG,'DEVELOPER','false')=='true':specs.append(('Developer Menu',{'mode':'developer'}))
    for label,params in specs:
        directory._add_menu_item(label,params,None,'',True,getattr(CONFIG,'ADDON_FANART',''),
            getattr(CONFIG,'ICONSETTINGS',''),None,producer(params) is not None)

def rows_for(route):
    if not route:
        specs=[('Browse builds',{'mode':'builds'},'Choose the edition made for your device.','builds.png'),
          ('Save your data',{'mode':'savedata'},'Review the accounts and settings to keep before installing.','savedata.png'),
          ('Maintenance',{'mode':'maint'},'Cleaning, backups, logs and tools for your Kodi setup.','maintenance.png'),
          ('Installer settings',{'mode':'settings','name':CONFIG.ADDON_ID},'Adjust installation preferences and automatic maintenance.','settings.png')]
        return [entry(t,p,d,p['mode']!='settings',os.path.join(CONFIG.ADDON_PATH,'resources','media',i)) for t,p,d,i in specs]
    fn=producer(route)
    if fn is None:return None
    return capture(directory,fn)

def dispatch_action(handle,params):
    # The modal is closed before callbacks. Refresh the branded screen ourselves;
    # Container.Refresh would re-enter the underlying plugin directory.
    from resources.libs.common.router import Router
    original=xbmc.executebuiltin
    def builtin(command,*args,**kwargs):
        if command.strip().lower().replace('()','')=='container.refresh':return
        return original(command,*args,**kwargs)
    xbmc.executebuiltin=builtin
    try:Router().dispatch(handle,encode(params))
    finally:xbmc.executebuiltin=original

class InstallerNavigation(xbmcgui.WindowXMLDialog):
    def __init__(self,*args,**kwargs):
        self.nav=kwargs.pop('navigation');self.rows=kwargs.pop('rows');self.pending=None
        super().__init__(*args,**kwargs)
    def onInit(self):
        mode=self.nav.route.get('mode')
        layout='home' if not mode else 'builds' if mode=='builds' and any(r['params'].get('mode')=='viewbuild' for r in self.rows) else 'list'
        self.setProperty('addon.icon',CONFIG.ADDON_ICON);self.setProperty('layout',layout);self.setProperty('heading',self.nav.title)
        self.setProperty('brand.version','Installer '+CONFIG.ADDON_VERSION)
        self.setProperty('breadcrumb',' / '.join([s[1] for s in self.nav.stack]+[self.nav.title]))
        subtitles={'home':'Your BlackLanturn setup, all in one place.','builds':'Choose a build, then review its installation options.','savedata':'Choose which accounts and settings to preserve.','maint':'Keep your setup running smoothly.'}
        self.setProperty('subtitle',subtitles.get(mode or 'home','Select a tool or press Back to return.'))
        sidebar=self.getControl(100);sidebar.reset();active_index=0
        for title,route,icon in SIDEBAR:
            li=xbmcgui.ListItem(title);li.setArt({'icon':os.path.join(CONFIG.ADDON_PATH,'resources/media',icon)})
            active=(not mode and not route) or (mode and route.get('mode')==mode) or (mode in ('viewbuild',) and route.get('mode')=='builds') or (mode in ('trakt','realdebrid','login') and route.get('mode')=='savedata')
            li.setProperty('active','true' if active else 'false');sidebar.addItem(li)
            if active:active_index=SIDEBAR.index((title,route,icon))
        sidebar.selectItem(active_index)
        self.control=200 if layout=='home' else 201 if layout=='builds' else 202
        if layout=='builds':self.rows=[r for r in self.rows if r['params'].get('mode')=='viewbuild']
        if not self.rows:self.rows=[entry('Nothing available',{},'Try again later or choose another section.',False)]
        listing=self.getControl(self.control);listing.reset()
        for r in self.rows:
            li=xbmcgui.ListItem(r['label']);li.setProperty('description',r['description'])
            li.setArt({'icon':CONFIG.ADDON_ICON if layout=='builds' or (mode=='viewbuild' and r['params'].get('mode')!='savedata') else r['icon'] or CONFIG.ADDON_ICON,'fanart':r['fanart'] or CONFIG.ADDON_FANART})
            if layout=='builds':
                name=r['params'].get('name',r['label']);short=name
                for match,title in [('Apple TV & Mac','Apple TV & Mac'),('BlackLanturn General','General'),('Apple TV','Apple TV'),('Fire TV','Fire TV / Fire Stick'),('Android General','Android General'),('Mac','Mac')]:
                    if match in name:short=title;break
                version=re.search(r'\(v([^)]*)\)',r['label'])
                li.setProperty('card.title',short)
                li.setProperty('card.subtitle',('Kodi '+str(CONFIG.KODIV)+'  •  v'+version.group(1) if version else 'Kodi '+str(CONFIG.KODIV))+'\n'+('Apple TV / macOS' if 'Apple TV & Mac' in name else 'Fire TV / Android' if name == 'BlackLanturn General' else 'Experimental' if 'Experimental' in name else 'Apple Silicon' if 'Apple Silicon' in name else 'ARM32' if 'ARM32' in name else ''))
            li.setProperty('kind','Open' if r['folder'] else 'Select' if r['params'] else 'Info')
            listing.addItem(li)
        listing.selectItem(min(self.nav.selected,len(self.rows)-1));self.setFocusId(self.control)
        self.setProperty('footer','Back: previous screen     •     Left: sidebar     •     Select: open')
    def remember(self):self.nav.selected=self.getControl(self.control).getSelectedPosition()
    def onClick(self,control):
        self.remember()
        if control==100:
            title,route,_=SIDEBAR[self.getControl(100).getSelectedPosition()]
            self.pending=('switch',route,title);self.close()
        elif control in (200,201,202):
            r=self.rows[self.nav.selected]
            if r['params']:self.pending=(activation(r,producer(r['params']) is not None),r['params'],r['label']);self.close()
        elif control==300:self.pending=('back',{},'');self.close()
        elif control==301:self.pending=('action',{'mode':'settings','name':CONFIG.ADDON_ID},'Settings');self.close()
    def onAction(self,action):
        if action.getId() in (9,10,92):self.remember();self.pending=('back',{},'');self.close()
        elif action.getId()==2 and self.getFocusId()==100:self.setFocusId(self.control)
        elif action.getId()==3 and self.getFocusId() in (300,301):self.setFocusId(self.control)

def run(handle,initial=None):
    tools.ensure_folders()
    nav=Navigation(initial,'Home' if not initial else initial.get('name') or initial.get('mode','Home').title())
    while not xbmc.Monitor().abortRequested():
        try:
            CONFIG.init_settings()
            rows=rows_for(nav.route)
            if rows is None:
                xbmc.executebuiltin('ActivateWindow(Programs,plugin://'+CONFIG.ADDON_ID+'/?'+encode(dict(nav.route,legacy='1'))+',return)');break
            screen=InstallerNavigation('InstallerNavigation.xml',CONFIG.ADDON_PATH,'Default','1080i',navigation=nav,rows=rows)
            screen.doModal();pending=screen.pending;del screen
            if not pending:break
            kind,params,title=pending
            if kind=='back':
                if not nav.back():break
            elif kind=='switch':nav.switch(params,title)
            elif kind=='open':nav.push(params,title)
            else:
                perform(params,lambda p:dispatch_action(handle,p),CONFIG.init_settings)
                if handoff(params):break
        except Exception as exc:
            xbmc.log('BlackLanturn navigation: '+str(exc),xbmc.LOGERROR)
            if not xbmcgui.Dialog().yesno('BlackLanturn Installer','This screen could not be opened. Try again?',nolabel='Back',yeslabel='Retry'):
                if not nav.back():break
