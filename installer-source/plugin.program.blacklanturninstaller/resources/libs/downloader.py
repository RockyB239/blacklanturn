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

import requests
import sys
import os
import time

from resources.libs.common import logging
from resources.libs.common import tools
from resources.libs.common.config import CONFIG


class Downloader:
    def __init__(self):
        self.dialog = xbmcgui.Dialog()
        self.progress_dialog = xbmcgui.DialogProgress()

    def download(self, url, dest):
        self.progress_dialog.create(CONFIG.ADDONTITLE, "Downloading Content")
        self.progress_dialog.update(0)
        response = None
        completed = False
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            if self.progress_dialog.iscanceled():
                return False
            response = tools.open_url(url, stream=True)
            if not response:
                logging.log_notify(CONFIG.ADDONTITLE, "Download unavailable. Your current build has been kept.")
                return False
            try:
                total = int(response.headers.get('content-length', '0'))
            except (TypeError, ValueError):
                total = 0
            downloaded = 0
            monitor = xbmc.Monitor()
            with open(dest, 'wb') as output:
                # Stream even when Content-Length is absent; don't buffer a build in memory.
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if self.progress_dialog.iscanceled() or monitor.abortRequested():
                        return False
                    if not chunk:
                        continue
                    output.write(chunk)
                    downloaded += len(chunk)
                    percent = min(100, int(100 * downloaded / total)) if total > 0 else 0
                    self.progress_dialog.update(percent, 'Downloaded {:.1f} MB{}'.format(downloaded / (1024 * 1024), ' of {:.1f} MB'.format(total / (1024 * 1024)) if total > 0 else ''))
            if self.progress_dialog.iscanceled() or monitor.abortRequested() or not downloaded or (total > 0 and downloaded != total):
                return False
            completed = True
            return True
        except (OSError, requests.exceptions.RequestException):
            logging.log_notify(CONFIG.ADDONTITLE, "Download incomplete. Your current build has been kept.")
            return False
        finally:
            if response is not None:
                response.close()
            self.progress_dialog.close()
            if not completed and os.path.isfile(dest):
                try:
                    os.remove(dest)
                except OSError:
                    pass
