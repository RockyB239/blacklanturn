import xbmcaddon
import os

#########################################################
#         Global Variables - DON'T EDIT!!!              #
#########################################################
ADDON_ID = xbmcaddon.Addon().getAddonInfo('id')
PATH = xbmcaddon.Addon().getAddonInfo('path')
ART = os.path.join(PATH, 'resources', 'media')
#########################################################

#########################################################
#        User Edit Variables                            #
#########################################################
ADDONTITLE = '[COLOR FFEEF4F7]BlackLan[/COLOR][COLOR FF29D9EE]turn[/COLOR][COLOR FFEEF4F7] Installer[/COLOR]'
BUILDERNAME = 'BlackLanturn'
EXCLUDES = [ADDON_ID, 'repository.blacklanturn']

# Text File with build info in it.
# This will point to the BlackLanturn build catalog hosted on GitHub Pages.
BUILDFILE = 'https://rockyb239.github.io/blacklanturn/hosted-files/builds-v2.txt'

# How often you would like it to check for build updates in days.
# 0 means every startup of Kodi.
UPDATECHECK = 0

# Text File with apk info in it. Leave as 'http://' to ignore.
APKFILE = 'http://'

# Text File with Youtube Videos urls. Leave as 'http://' to ignore.
YOUTUBETITLE = ''
YOUTUBEFILE = 'http://'

# Text File for addon installer. Leave as 'http://' to ignore.
ADDONFILE = 'http://'

# Text File for advanced settings. Leave as 'http://' to ignore.
ADVANCEDFILE = 'http://'
#########################################################

#########################################################
#        Theming Menu Items                             #
#########################################################
ICONBUILDS = os.path.join(ART, 'builds.png')
ICONMAINT = os.path.join(ART, 'maintenance-wrench.png')
ICONSPEED = os.path.join(ART, 'speed.png')
ICONAPK = os.path.join(ART, 'apkinstaller.png')
ICONADDONS = os.path.join(ART, 'addoninstaller.png')
ICONYOUTUBE = os.path.join(ART, 'youtube.png')
ICONSAVE = os.path.join(ART, 'savedata.png')
ICONTRAKT = os.path.join(ART, 'keeptrakt.png')
ICONREAL = os.path.join(ART, 'keepdebrid.png')
ICONLOGIN = os.path.join(ART, 'keeplogin.png')
ICONCONTACT = os.path.join(ART, 'information.png')
ICONSETTINGS = os.path.join(ART, 'settings.png')

# Hide the section separators 'Yes' or 'No'
HIDESPACERS = 'No'

# Character used in separator
SPACER = '='

COLOR1 = 'FF29D9EE'
COLOR2 = 'FFEEF4F7'

# Primary menu items
THEME1 = '[COLOR FFEEF4F7]{}[/COLOR]'

# Build Names
THEME2 = u'[COLOR {color1}]{{}}[/COLOR]'.format(color1=COLOR1)

# Alternate items
THEME3 = u'[COLOR {color2}]{{}}[/COLOR]'.format(color2=COLOR2)

# Current Build Header
THEME4 = u'[COLOR {color1}]Current Build:[/COLOR] [COLOR {color2}]{{}}[/COLOR]'.format(color1=COLOR1, color2=COLOR2)

# Current Theme Header
THEME5 = u'[COLOR {color1}]Current Theme:[/COLOR] [COLOR {color2}]{{}}[/COLOR]'.format(color1=COLOR1, color2=COLOR2)

#########################################################
#        Contact Page                                   #
#########################################################
HIDECONTACT = 'No'
CONTACT = 'Thank you for choosing BlackLanturn Installer.\n\nBlackLanturn is a private Kodi build distribution system for Kodi 21.3 Omega.'
CONTACTICON = os.path.join(ART, 'qricon.png')
CONTACTFANART = 'http://'
#########################################################

#########################################################
#        Auto Update For Those With No Repo             #
#########################################################
AUTOUPDATE = 'Yes'
#########################################################

#########################################################
#        Auto Install Repo If Not Installed             #
#########################################################
AUTOINSTALL = 'No'
REPOID = 'repository.blacklanturn'

# These will be updated after we confirm your final GitHub Pages URL structure.
REPOADDONXML = 'http://'
REPOZIPURL = 'http://'
#########################################################

#########################################################
#        Notification Window                            #
#########################################################
ENABLE = 'No'
NOTIFICATION = 'http://'
HEADERTYPE = 'Text'
FONTHEADER = 'Font14'
HEADERMESSAGE = '[COLOR FFEEF4F7]BlackLan[/COLOR][COLOR FF29D9EE]turn[/COLOR][COLOR FFEEF4F7] Installer[/COLOR]'
HEADERIMAGE = 'http://'
FONTSETTINGS = 'Font13'
BACKGROUND = 'http://'
#########################################################