"""
Memory cache functions for kodi addon.

The window property from kodi has the ability to accept arbitrary data as a "property".
This interface is used to store (key: val) pairs as a property of the kodi HOME window:

    a) addon id + hash(locale + parameter_string): json_data
        key: language specific hash of the parameters passed to the the addon.
        val: json data required to create a specific kodi listing.

    b) addon-id-cache-ids: CSV
        key: static, addon-specific string
        val: A CSV list of all keys from a) with data stored.
"""

from hashlib import blake2s
import json

import xbmcgui

from resources.lib.kodi import get_addon_id
from resources.lib.logger import log


def get_cache_key():
    """ The master id used to store the CSV list of cached ids. """
    return f"{get_addon_id()}-cache-ids"


def get_cache_id(param_string):
    """ Creates hash of the parameter string to use (with addon id) as the cache id. """
    id_hash = blake2s(param_string.encode("utf-8", "surrogateescape")).hexdigest()[0:10]
    return f"{get_addon_id()}-{id_hash}"


def erase():
    """ Clears all cached results from the memory cache. """
    memcache = xbmcgui.Window(10000)
    cache_id_key = get_cache_key()
    cache_id_list = memcache.getProperty(cache_id_key)[1:].split(",")

    for _id in cache_id_list:
        memcache.clearProperty(_id)
    memcache.clearProperty(cache_id_key)


def add_data(param_string, content, content_type):
    """ Adds a json object to the memory cache. """
    memcache = xbmcgui.Window(10000)
    cache_id = get_cache_id(param_string)
    cache_data = json.dumps((content, content_type))
    memcache.setProperty(cache_id, cache_data)
    log(f"Added {cache_id} to cache.")

    # Add the cache_id to a CSV list of cached ids, which is itself stored in the cache.
    cache_id_key = get_cache_key()
    cache_id_list = memcache.getProperty(cache_id_key)
    cache_id_list += ("," + cache_id)
    log(f"List of cached ids: {cache_id_list}")
    memcache.setProperty(cache_id_key, cache_id_list)


def get_data(param_string):
    """ Retrieve json object from memory cache.  """
    memcache = xbmcgui.Window(10000)
    cache_id = get_cache_id(param_string)
    cached_data = memcache.getProperty(cache_id)
    log(f'Cache data {cache_id} exists: {cached_data != ""}')

    if not cached_data:
        return None

    return json.loads(cached_data)
