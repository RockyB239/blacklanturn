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


if __name__ == '__main__':
    import sys
    from resources.libs.common import router

    _handle = int(sys.argv[1])
    _params = sys.argv[2][1:]
    
    from resources.libs.gui.navigation_model import decode
    params = decode(_params)
    if params.pop('legacy', None) == '1':
        router.Router().dispatch(_handle, __import__('urllib.parse', fromlist=['urlencode']).urlencode(params))
    else:
        from resources.libs.gui import navigation
        # Existing directory/action URLs remain usable; the root launches the shell.
        if not params or navigation.producer(params) is not None:
            navigation.run(_handle, params or None)
            import xbmcplugin
            xbmcplugin.endOfDirectory(_handle, succeeded=False)
        else:
            router.Router().dispatch(_handle, _params)
