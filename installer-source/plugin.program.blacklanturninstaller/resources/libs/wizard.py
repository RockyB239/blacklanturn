################################################################################
#      Copyright (C) 2019 drinfernoo                                           #
#                                                                              #
#  This Program is free software; you can redistribute it and/or modify        #
#  it under the terms of the GNU General Public License as published by        #
#  the Free Software Foundation; either version 2, or (at your option)         #
#  any later version.                                                          #
#                                                                              #
#  This Program is distributed in the hope that it will be useful,             #
#  but WITHOUT ANY WARRANTY; without even the implied warranty of              #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the                #
#  GNU General Public License for more details.                                #
#                                                                              #
#  You should have received a copy of the GNU General Public License           #
#  along with XBMC; see the file COPYING.  If not, write to                    #
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.       #
#  http://www.gnu.org/copyleft/gpl.html                                        #
################################################################################

import xbmc
import xbmcgui

import os

from resources.libs import check
from resources.libs import db
from resources.libs import extract
from resources.libs import install
from resources.libs import skin
from resources.libs.common import logging
from resources.libs.common import tools
from resources.libs.common.config import CONFIG
from resources.libs.downloader import Downloader


def install_mode(config):
    return 'Account-only reset' if config.get_setting('authonlyclean') == 'true' else 'Standard'

def install_summary(config):
    """Describe the same saved choices consumed by OpenWizard's build install."""
    def choices(items):
        return ', '.join('{}: {}'.format(label, 'ON' if getattr(config, key, 'false') == 'true' else 'OFF')
                         for key, label in items)
    accounts = choices((('KEEPTRAKT', 'Trakt'), ('KEEPDEBRID', 'Debrid'), ('KEEPLOGIN', 'Login')))
    if config.get_setting('authonlyclean') == 'true':
        return ('Mode: Account-only reset\nAccounts to keep - {}\n'
                'Reset settings, playback preferences, sources, favourites and other user data to build defaults. '
                'Only selected accounts are kept. Standard Keep options are ignored.').format(accounts)
    settings = choices((('KEEPSOURCES', 'Sources'), ('KEEPPROFILES', 'Profiles'),
                        ('KEEPPLAYERCORE', 'playercorefactory.xml'), ('KEEPGUISETTINGS', 'guisettings.xml'),
                        ('KEEPADVANCED', 'advancedsettings.xml'), ('KEEPFAVS', 'Favourites'),
                        ('KEEPSUPER', 'Super Favourites'), ('KEEPREPOS', 'Repositories'),
                        ('KEEPWHITELIST', 'Whitelist')))
    return ('Mode: Standard\nAccounts to keep - {}\nKeep options - {}\n'
            'Supported build preferences are preserved; other unselected user data is replaced.').format(accounts, settings)


def install_confirmation(config):
    """Put the decision before detail in Kodi's short native yes/no textbox."""
    summary = install_summary(config).splitlines()
    if config.get_setting('authonlyclean') == 'true':
        return '\n'.join((summary[0], 'Reset settings and playback; Keep options ignored.', summary[1],
                          'Other user data is replaced by build defaults.'))
    return '\n'.join((summary[0], 'Preserve accounts, preferences and selected Keep data.', summary[1], summary[2],
                      'Other unselected user data is replaced.'))


class Wizard:

    def __init__(self):
        tools.ensure_folders(CONFIG.PACKAGES)
        
        self.dialog = xbmcgui.Dialog()
        self.dialogProgress = xbmcgui.DialogProgress()

    def _prompt_for_wipe(self):
        # Should we wipe first?
        if self.dialog.yesno(CONFIG.ADDONTITLE,
                           "[COLOR {0}]Do you wish to restore your".format(CONFIG.COLOR2),
                           "Kodi configuration to default settings",
                           "Before installing the build backup?[/COLOR]",
                           nolabel='[B][COLOR red]No[/COLOR][/B]',
                           yeslabel='[B][COLOR springgreen]Yes[/COLOR][/B]'):
            install.wipe()

    def build(self, name, over=False):
        # if action == 'normal':
            # if CONFIG.KEEPTRAKT == 'true':
                # from resources.libs import traktit
                # traktit.auto_update('all')
                # CONFIG.set_setting('traktnextsave', tools.get_date(days=3, formatted=True))
            # if CONFIG.KEEPDEBRID == 'true':
                # from resources.libs import debridit
                # debridit.auto_update('all')
                # CONFIG.set_setting('debridnextsave', tools.get_date(days=3, formatted=True))
            # if CONFIG.KEEPLOGIN == 'true':
                # from resources.libs import loginit
                # loginit.auto_update('all')
                # CONFIG.set_setting('loginnextsave', tools.get_date(days=3, formatted=True))

        temp_kodiv = int(CONFIG.KODIV)
        buildv = int(float(check.check_build(name, 'kodi')))

        if not temp_kodiv == buildv:
            warning = True
        else:
            warning = False

        # Even update calls must review the saved preservation mode before download.
        reviewed_auth_only = CONFIG.get_setting('authonlyclean') == 'true'
        summary = install_confirmation(CONFIG)
        title = '{} v{}'.format(name, check.check_build(name, 'version'))
        if warning:
            title = 'WARNING: ' + title
            summary += '\nTargets Kodi {} (installed: {}). Skin display may differ.'.format(buildv, CONFIG.KODIV)
        yes_pressed = self.dialog.yesno(
            title, summary,
            nolabel='Cancel', yeslabel='Reset & install' if reviewed_auth_only else 'Install')
        if yes_pressed:
            CONFIG.clear_setting('build')
            CONFIG.set_setting('authorizationsrestored', 'false')
            buildzip = check.check_build(name, 'url')
            zipname = name.replace('\\', '').replace('/', '').replace(':', '').replace('*', '').replace('?', '').replace('"', '').replace('<', '').replace('>', '').replace('|', '')

            self.dialogProgress.create(CONFIG.ADDONTITLE, '[COLOR {0}][B]Downloading:[/B][/COLOR] [COLOR {1}]{2} v{3}[/COLOR]\n\nPlease Wait'.format(CONFIG.COLOR2, CONFIG.COLOR1, name, check.check_build(name, 'version')))

            lib = os.path.join(CONFIG.MYBUILDS, '{0}.zip'.format(zipname))
            
            try:
                os.remove(lib)
            except:
                pass

            if Downloader().download(buildzip, lib) is False:
                self.dialogProgress.close()
                return
            xbmc.sleep(500)
            
            if os.path.getsize(lib) == 0:
                try:
                    os.remove(lib)
                except:
                    pass
                    
                return
                
            self.dialogProgress.update(0, 'Checking download and playback setup…')
            from resources.libs import platform_compatibility
            try:
                prepared = platform_compatibility.prepare(lib, xbmc, home=CONFIG.HOME)
            except platform_compatibility.CompatibilityError as exc:
                self.dialogProgress.close()
                self.dialog.ok(CONFIG.ADDONTITLE, str(exc))
                return

            protected_helper = (prepared.get('policy') or {}).get('schema') in (2, 3)
            protected_preferences = (prepared.get('policy') or {}).get('schema') == 3
            protected_network = (prepared.get('policy') or {}).get('preferences_policy') in ('playback-trakt-youtube-umbrella-network-1', 'playback-trakt-youtube-umbrella-network-autoplay-1')
            protected_umbrella = (prepared.get('policy') or {}).get('preferences_policy') in ('playback-trakt-youtube-umbrella-1', 'playback-trakt-youtube-umbrella-network-1', 'playback-trakt-youtube-umbrella-network-autoplay-1')
            if protected_umbrella and not reviewed_auth_only and CONFIG.KEEPWHITELIST == 'true':
                from resources.libs import managed_addons, whitelist
                try:
                    kept = {entry[2] for entry in whitelist.whitelist('read')}
                    # Match the same two dependency levels retained by wipe.
                    for addon in tuple(kept):
                        for dependency in db.depends_list(addon):
                            kept.add(dependency)
                            kept.update(db.depends_list(dependency))
                    managed_addons.verify_kept(CONFIG.HOME, kept, network=protected_network)
                except (managed_addons.ProtectionError, OSError, ValueError, TypeError, IndexError) as exc:
                    self.dialogProgress.close()
                    self.dialog.ok(CONFIG.ADDONTITLE, str(exc))
                    return
            if reviewed_auth_only and not protected_helper:
                self.dialogProgress.close()
                self.dialog.ok(CONFIG.ADDONTITLE,
                               'Account-only reset is unavailable for this older build. '
                               'No cleanup has run. Choose Standard in Save Data to install it with your selected Keep options.')
                return
            auth_only = protected_helper and reviewed_auth_only
            if auth_only:
                for option in ('KEEPFAVS', 'KEEPSOURCES', 'KEEPPROFILES', 'KEEPPLAYERCORE',
                               'KEEPADVANCED', 'KEEPGUISETTINGS', 'KEEPREPOS', 'KEEPSUPER',
                               'KEEPWHITELIST'):
                    setattr(CONFIG, option, 'false')
            if protected_helper:
                from resources.libs import managed_addons
                try:
                    managed_addons.protect(os.path.join(CONFIG.DATABASE, db.latest_db('Addons')), umbrella=protected_umbrella, network=protected_network)
                    xbmc.executebuiltin('UpdateLocalAddons', wait=True)
                except (managed_addons.ProtectionError, RuntimeError) as exc:
                    self.dialogProgress.close()
                    self.dialog.ok(CONFIG.ADDONTITLE, str(exc))
                    return

            if protected_helper:
                from resources.libs import authorizations
                categories = {category for category, enabled in (
                    ('trakt', CONFIG.KEEPTRAKT), ('debrid', CONFIG.KEEPDEBRID),
                    ('login', CONFIG.KEEPLOGIN)) if enabled == 'true'}
                try:
                    account_backup = os.path.join(CONFIG.PLUGIN_DATA, 'authorizations.json')
                    pending_accounts = os.path.join(CONFIG.PLUGIN_DATA, 'authorizations.pending.json')
                    accounts = authorizations.prepare(CONFIG.HOME, prepared['addon_ids'], categories, pending_accounts)
                    if protected_preferences:
                        from resources.libs import build_preferences
                        try:
                            accounts = build_preferences.prepare(CONFIG.HOME, accounts, prepared['addon_ids'], auth_only=auth_only)
                            authorizations.save(pending_accounts, accounts)
                        except build_preferences.PreferenceError as exc:
                            raise authorizations.AuthorizationError(str(exc)) from exc
                except authorizations.AuthorizationError as exc:
                    self.dialogProgress.close()
                    self.dialog.ok(CONFIG.ADDONTITLE, str(exc))
                    return

            if install.wipe(accounts_prepared=protected_helper, auth_only=auth_only) is False:
                self.dialogProgress.close()
                return

            if not auth_only:
                skin.look_and_feel_data('save')
            
            title = '[COLOR {0}][B]Installing:[/B][/COLOR] [COLOR {1}]{2} v{3}[/COLOR]'.format(CONFIG.COLOR2, CONFIG.COLOR1, name, check.check_build(name, 'version'))
            self.dialogProgress.update(0, '{}\n\nPlease Wait'.format(title))
            percent, errors, error = extract.all(lib, CONFIG.HOME, title=title)
            
            skin.skin_to_default('Build Install')

            if protected_helper and int(float(percent)) == 100 and int(float(errors)) == 0:
                try:
                    authorizations.restore(CONFIG.HOME, accounts, prepared['addon_ids'])
                    if protected_preferences:
                        try:
                            build_preferences.restore(CONFIG.HOME, accounts, prepared['addon_ids'])
                        except build_preferences.PreferenceError as exc:
                            raise authorizations.AuthorizationError(str(exc)) from exc
                    authorizations.commit(pending_accounts, account_backup)
                except authorizations.AuthorizationError as exc:
                    self.dialogProgress.close()
                    self.dialog.ok(CONFIG.ADDONTITLE, str(exc))
                    return

            if protected_helper:
                if int(float(percent)) != 100 or int(float(errors)) != 0:
                    self.dialogProgress.close()
                    self.dialog.ok(CONFIG.ADDONTITLE, 'The build did not finish installing. Helper updates remain protected. Reinstall this build before continuing.')
                    return
                try:
                    managed_addons.protect(os.path.join(CONFIG.DATABASE, db.latest_db('Addons')), umbrella=protected_umbrella, network=protected_network)
                    xbmc.executebuiltin('UpdateLocalAddons', wait=True)
                except (managed_addons.ProtectionError, RuntimeError) as exc:
                    self.dialogProgress.close()
                    self.dialog.ok(CONFIG.ADDONTITLE, 'Installation needs attention: ' + str(exc))
                    return

            if int(float(percent)) > 0:
                # Retain the device registry and register only the extracted add-ons.
                db.addon_database(prepared['addon_ids'], 1, array=True)
                db.fix_metas()
                CONFIG.set_setting('buildname', name)
                CONFIG.set_setting('buildversion', check.check_build(name, 'version'))
                CONFIG.set_setting('buildtheme', '')
                CONFIG.set_setting('latestversion', check.check_build(name, 'version'))
                CONFIG.set_setting('nextbuildcheck', tools.get_date(days=CONFIG.UPDATECHECK, formatted=True))
                CONFIG.set_setting('installed', 'true')
                CONFIG.set_setting('authorizationsrestored', 'true' if protected_helper else 'false')
                CONFIG.set_setting('extract', str(percent))
                CONFIG.set_setting('errors', str(errors))
                logging.log('INSTALLED {0}: [ERRORS:{1}]'.format(percent, errors))

                try:
                    os.remove(lib)
                except:
                    pass

                if int(float(errors)) > 0:
                    yes_pressed = self.dialog.yesno(CONFIG.ADDONTITLE,
                                       '[COLOR {0}][COLOR {1}]{2} v{3}[/COLOR]'.format(CONFIG.COLOR2, CONFIG.COLOR1,
                                                                                       name, check.check_build(name, 'version')),
                                       'Completed: [COLOR {0}]{1}{2}[/COLOR] [Errors:[COLOR {3}]{4}[/COLOR]]'.format(
                                           CONFIG.COLOR1, percent, '%', CONFIG.COLOR1, errors),
                                       'Would you like to view the errors?[/COLOR]',
                                       nolabel='[B][COLOR red]No Thanks[/COLOR][/B]',
                                       yeslabel='[B][COLOR springgreen]View Errors[/COLOR][/B]')
                    if yes_pressed:
                        from resources.libs.gui import window
                        window.show_text_box("Viewing Build Install Errors", error)
                self.dialogProgress.close()

                from resources.libs.gui.build_menu import BuildMenu
                themecount = BuildMenu().theme_count(name)

                if themecount > 0:
                    self.theme(name)

                db.addon_database(CONFIG.ADDON_ID, 1)
                if not protected_helper:
                    db.force_check_updates(over=True)

                self.dialog.ok(CONFIG.ADDONTITLE, "[COLOR {0}]To save changes you now need to force close Kodi, Press OK to force close Kodi[/COLOR]".format(CONFIG.COLOR2))
                tools.kill_kodi(over=True)
            else:
                from resources.libs.gui import window
                window.show_text_box("Viewing Build Install Errors", error)
        else:
            logging.log_notify(CONFIG.ADDONTITLE,
                               '[COLOR {0}]Build Install: Cancelled![/COLOR]'.format(CONFIG.COLOR2))

    def gui(self, name, over=False):
        if name == CONFIG.get_setting('buildname'):
            if over:
                yes_pressed = 1
            else:
                yes_pressed = self.dialog.yesno(CONFIG.ADDONTITLE,
                                   '[COLOR {0}]Would you like to apply the guifix for:'.format(CONFIG.COLOR2),
                                   '[COLOR {0}]{1}[/COLOR]?[/COLOR]'.format(CONFIG.COLOR1, name),
                                   nolabel='[B][COLOR red]No, Cancel[/COLOR][/B]',
                                   yeslabel='[B][COLOR springgreen]Apply Fix[/COLOR][/B]')
        else:
            yes_pressed = self.dialog.yesno("{0} - [COLOR red]WARNING!![/COLOR]".format(CONFIG.ADDONTITLE),
                               "[COLOR {0}][COLOR {1}]{2}[/COLOR] community build is not currently installed.".format(
                                   CONFIG.COLOR2, CONFIG.COLOR1, name),
                               "Would you like to apply the guiFix anyways?.[/COLOR]",
                               nolabel='[B][COLOR red]No, Cancel[/COLOR][/B]',
                               yeslabel='[B][COLOR springgreen]Apply Fix[/COLOR][/B]')
        if yes_pressed:
            guizip = check.check_build(name, 'gui')
            zipname = name.replace('\\', '').replace('/', '').replace(':', '').replace('*', '').replace('?', '').replace('"', '').replace('<', '').replace('>', '').replace('|', '')

            response = tools.open_url(guizip, check=True)
            if not response:
                logging.log_notify(CONFIG.ADDONTITLE,
                                   '[COLOR {0}]GuiFix: Invalid Zip Url![/COLOR]'.format(CONFIG.COLOR2))
                return

            self.dialogProgress.create(CONFIG.ADDONTITLE, '[COLOR {0}][B]Downloading GuiFix:[/B][/COLOR] [COLOR {1}]{2}[/COLOR]\n\nPlease Wait'.format(CONFIG.COLOR2, CONFIG.COLOR1, name))

            lib = os.path.join(CONFIG.PACKAGES, '{0}_guisettings.zip'.format(zipname))
            
            try:
                os.remove(lib)
            except:
                pass

            Downloader().download(guizip, lib)
            xbmc.sleep(500)
            
            if os.path.getsize(lib) == 0:
                try:
                    os.remove(lib)
                except:
                    pass
                    
                return
            
            title = '[COLOR {0}][B]Installing:[/B][/COLOR] [COLOR {1}]{2}[/COLOR]'.format(CONFIG.COLOR2, CONFIG.COLOR1, name)
            self.dialogProgress.update(0, '{}\n\nPlease Wait'.format(title))
            extract.all(lib, CONFIG.USERDATA, title=title)
            self.dialogProgress.close()
            skin.skin_to_default('Build Install')
            skin.look_and_feel_data('save')
            installed = db.grab_addons(lib)
            db.addon_database(installed, 1, True)

            self.dialog.ok(CONFIG.ADDONTITLE, "[COLOR {0}]To save changes you now need to force close Kodi, Press OK to force close Kodi[/COLOR]".format(CONFIG.COLOR2))
            tools.kill_kodi(over=True)
        else:
            logging.log_notify(CONFIG.ADDONTITLE,
                               '[COLOR {0}]GuiFix: Cancelled![/COLOR]'.format(CONFIG.COLOR2))

    def theme(self, name, theme='', over=False):
        installtheme = False

        if not theme:
            themefile = check.check_build(name, 'theme')

            response = tools.open_url(themefile, check=True)
            if response:
                from resources.libs.gui.build_menu import BuildMenu
                themes = BuildMenu().theme_count(name, False)
                if len(themes) > 0:
                    if self.dialog.yesno(CONFIG.ADDONTITLE,
                                    "[COLOR {0}]The Build [COLOR {1}]{2}[/COLOR] comes with [COLOR {3}]{4}[/COLOR] different themes".format(
                                        CONFIG.COLOR2, CONFIG.COLOR1, name, CONFIG.COLOR1, len(themes)),
                                    "Would you like to install one now?[/COLOR]",
                                    yeslabel="[B][COLOR springgreen]Install Theme[/COLOR][/B]",
                                    nolabel="[B][COLOR red]Cancel Themes[/COLOR][/B]"):
                        logging.log("Theme List: {0}".format(str(themes)))
                        ret = self.dialog.select(CONFIG.ADDONTITLE, themes)
                        logging.log("Theme install selected: {0}".format(ret))
                        if not ret == -1:
                            theme = themes[ret]
                            installtheme = True
                        else:
                            logging.log_notify(CONFIG.ADDONTITLE,
                                               '[COLOR {0}]Theme Install: Cancelled![/COLOR]'.format(CONFIG.COLOR2))
                            return
                    else:
                        logging.log_notify(CONFIG.ADDONTITLE,
                                           '[COLOR {0}]Theme Install: Cancelled![/COLOR]'.format(CONFIG.COLOR2))
                        return
            else:
                logging.log_notify(CONFIG.ADDONTITLE,
                                   '[COLOR {0}]Theme Install: None Found![/COLOR]'.format(CONFIG.COLOR2))
        else:
            installtheme = self.dialog.yesno(CONFIG.ADDONTITLE,
                                        '[COLOR {0}]Would you like to install the theme:'.format(CONFIG.COLOR2),
                                        '[COLOR {0}]{1}[/COLOR]'.format(CONFIG.COLOR1, theme),
                                        'for [COLOR {0}]{1} v{2}[/COLOR]?[/COLOR]'.format(CONFIG.COLOR1, name,
                                                                                          check.check_build(name,
                                                                                                            'version')),
                                        yeslabel="[B][COLOR springgreen]Install Theme[/COLOR][/B]",
                                        nolabel="[B][COLOR red]Cancel Themes[/COLOR][/B]")
                                        
        if installtheme:
            themezip = check.check_theme(name, theme, 'url')
            zipname = name.replace('\\', '').replace('/', '').replace(':', '').replace('*', '').replace('?', '').replace('"', '').replace('<', '').replace('>', '').replace('|', '')

            response = tools.open_url(themezip, check=True)
            if not response:
                logging.log_notify(CONFIG.ADDONTITLE,
                                   '[COLOR {0}]Theme Install: Invalid Zip Url![/COLOR]'.format(CONFIG.COLOR2))
                return False

            self.dialogProgress.create(CONFIG.ADDONTITLE, '[COLOR {0}][B]Downloading:[/B][/COLOR] [COLOR {1}]{2}[/COLOR]\n\nPlease Wait'.format(CONFIG.COLOR2, CONFIG.COLOR1, theme))

            lib = os.path.join(CONFIG.PACKAGES, '{0}.zip'.format(zipname))
            
            try:
                os.remove(lib)
            except:
                pass

            Downloader().download(themezip, lib)
            xbmc.sleep(500)
            
            if os.path.getsize(lib) == 0:
                try:
                    os.remove(lib)
                except:
                    pass
                    
                return
            
            self.dialogProgress.update(0, "Installing {0}".format(name))

            test1 = False
            test2 = False
            
            from resources.libs import skin
            from resources.libs import test
            test1 = test.test_theme(lib) if CONFIG.SKIN not in skin.DEFAULT_SKINS else False
            test2 = test.test_gui(lib) if CONFIG.SKIN not in skin.DEFAULT_SKINS else False

            if test1:
                skin.look_and_feel_data('save')
                swap = skin.skin_to_default('Theme Install')

                if not swap:
                    return False

                xbmc.sleep(500)

            title = '[COLOR {0}][B]Installing Theme:[/B][/COLOR] [COLOR {1}]{2}[/COLOR]'.format(CONFIG.COLOR2,
                                                                                                CONFIG.COLOR1,
                                                                                                theme)
            self.dialogProgress.update(0, '{}\n\nPlease Wait'.format(title))
            percent, errors, error = extract.all(lib, CONFIG.HOME, title=title)
            CONFIG.set_setting('buildtheme', theme)
            logging.log('INSTALLED {0}: [ERRORS:{1}]'.format(percent, errors))
            self.dialogProgress.close()

            db.force_check_updates(over=True)
            installed = db.grab_addons(lib)
            db.addon_database(installed, 1, True)

            if test2:
                skin.look_and_feel_data('save')
                skin.skin_to_default("Theme Install")
                gotoskin = CONFIG.get_setting('defaultskin')
                skin.switch_to_skin(gotoskin, "Theme Installer")
                skin.look_and_feel_data('restore')
            elif test1:
                skin.look_and_feel_data('save')
                skin.skin_to_default("Theme Install")
                gotoskin = CONFIG.get_setting('defaultskin')
                skin.switch_to_skin(gotoskin, "Theme Installer")
                skin.look_and_feel_data('restore')
            else:
                xbmc.executebuiltin("ReloadSkin()")
                xbmc.sleep(1000)
                xbmc.executebuiltin("Container.Refresh()")
        else:
            logging.log_notify(CONFIG.ADDONTITLE,
                               '[COLOR {0}]Theme Install: Cancelled![/COLOR]'.format(CONFIG.COLOR2))


def wizard(action, name, url):
    cls = Wizard()

    if action in ['fresh', 'normal']:
        cls.build(action, name)
    elif action == 'gui':
        cls.gui(name)
    elif action == 'theme':
        cls.theme(name, url)
