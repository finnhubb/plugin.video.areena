"""
Wrapper module for xbmc logger.
"""

import xbmc

from resources.lib.kodi import get_setting, get_addon_id


def log(msg):
    """ Log something to the kodi.log file """
    if get_setting("debug") == "true":
        xbmc.log(msg=f"{get_addon_id()}, {msg}", level=xbmc.LOGDEBUG)
