"""
Kodi helper functions that interface with the xbmc* libraries.
Used to check settings, perform search, create listings, play media.
"""
import sys

from urllib.parse import urlencode

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs


def get_addon_handle():
    """ Integer identifier of this kodi addon. """
    return int(sys.argv[1])


def get_addon_id():
    """ URL identifier of this kodi addon: eg "plugin.video.xyz". """
    return xbmcaddon.Addon().getAddonInfo("id")


def get_icon_path(filename):
    """ On disk path of kodi addon resource. """
    addon_path = xbmcaddon.Addon().getAddonInfo("path")
    return xbmcvfs.translatePath(addon_path + f'resources/media/{filename}')


def get_setting(label):
    """ Get the value from addon settings. """
    return xbmcaddon.Addon().getSetting(label)


def open_settings():
    """ Opens the addon settings. """
    xbmcaddon.Addon().openSettings()


def localize(translation_id):
    """ Translate text to GLOBAL kodi language setting (not addon setting). """
    return xbmcaddon.Addon().getLocalizedString(translation_id)


def get_user_input(heading):
    """ Requests and returns input text requested from user. """
    return xbmcgui.Dialog().input(heading)


def get_download_path():
    """ Returns filepath for downloads: User specified or default to kodi temp. """
    return get_setting("download_path") or xbmcvfs.translatePath("special://temp")


def send_notification(status, msg):
    """ Send a popup alert notification to the kodi interface. """
    icon = xbmcaddon.Addon().getAddonInfo("icon")
    xbmc.executebuiltin(f"Notification({status} ,{msg}, 5000, {icon})")


def send_notification_download(status, filename):
    """ Send notificaiton to UI for download event. """
    if status == "start":
        status = localize(33030)
        msg = localize(33032)
    elif status == "success":
        status = localize(33030)
        msg = localize(33033)
    elif status == "failed":
        status = localize(33031)
        msg = localize(33034)

    send_notification(status, f"{filename} {msg}")


def create_popup(heading, msg, left, mid, right):
    """
    Create custom dialog box popup with three options and cancel.
    The order of the xbmc.Dialog().yesnocustom() is backwards.
    The response code is also in a deranged order.
    This wrapper function makes the interface more logical.
    res code: left = 0, mid = 1, right = 2, cancel -1.
    """
    res = xbmcgui.Dialog().yesnocustom(heading, msg, right, mid, left)
    choice = [1, 0, 2, -1]

    return choice[res]


def create_EEXIST_popup(filename):
    """ Prompts user for choice when download file preexists. """
    msg = f"{localize(33035)} {filename}"
    # create_popup(heading, msg, replace, rename, resume)
    res = create_popup(localize(33030), msg, localize(33036), localize(33037), localize(33038))
    choice = ["replace", "rename", "resume", "cancel"]

    return choice[res]


def create_list_item_info(title, attrs):
    """ Adds metadata to a video item (playable or series folder) """
    return {"sorttitle": title, "plot": attrs.get("description"), "duration": attrs.get("duration")}


def create_list_item_video_title(name, attrs):
    """ Creates title name for video in kodi interface. """
    prefix = ""

    # requires python >= 3.8
    # if (season := attrs.get("season")):
    if attrs.get("season"):
        season = attrs.get("season")
        prefix += f"{localize(33028)} {season} "

    # requires python >= 3.8
    # if (episode := attrs.get("episode")):
    if attrs.get("episode"):
        episode = attrs.get("episode")
        prefix += f"{localize(33028)} {episode} "

    return prefix + name


def create_callback_url(attrs):
    """ Create plugin recursive callback URL, with attrs dictionary as parameters. """
    param_string = urlencode(attrs, encoding="utf-8", errors="surrogateescape")
    return f"plugin://{get_addon_id()}/?{param_string}"


def create_colored_label(title, color):
    """ Formats the title with specified color tags. """
    return f"[COLOR {color}]{title}[/COLOR]"


def create_list_item(title, color, attrs):
    """ Creates list item for the kodi interface. """
    label = create_colored_label(title, color)
    list_item = xbmcgui.ListItem(label=label.encode("utf-8", "surrogateescape"), offscreen=True)

    # Set the video properties for media or folders containing media.
    if attrs:
        list_item.setInfo("video", create_list_item_info(title.encode("utf-8", "surrogateescape"), attrs))

    return list_item


def create_list_item_media(_type, name, color, item, url):
    """ Creates list item for playable media in the kodi interface. """

    title = create_list_item_video_title(name, item)
    list_item = create_list_item(title, color, item)

    # Mark the video as playable.
    list_item.setProperty("IsPlayable", "true")

    # Don't enable download option for live streams or local videos.
    if _type in ["live", "video"]:
        return list_item

    # Create a download callback event for the vod stream.
    api_data = item.get("api_data")
    api_data["type"] = "download"
    # Format the filename for saving to the filesystem
    api_data["filename"] = title.strip().replace("/", ":")
    url = create_callback_url(api_data)

    # Create a "Download" button in the context menu.
    list_item.addContextMenuItems([(localize(33039), f"RunPlugin({url})")])

    return list_item


def create_list_entry(item, colors):
    """ Creates the appropriate listing entries for provided item. """
    api_data = item.get("api_data")
    _type = api_data.get("type")
    name = item.get("name")
    url = create_callback_url(api_data)

    if _type in ["search", "settings"]:
        is_folder = False
        list_item = create_list_item(name, colors["title"], attrs=None)

    elif _type in ["program", "live", "clip", "video"]:
        is_folder = False
        list_item = create_list_item_media(_type, name, colors["title"], item, url)

    else: # [category, subcategory, series, package].
        is_folder = True
        list_item = create_list_item(name, colors["folder"], item)

    # Add image as thumb if we have one.
    # requires python >= 3.8
    # if (img := item.get("image")):
    #    list_item.setArt({"thumb": img})
    if item.get("image"):
        list_item.setArt({"thumb": item.get("image")})
    return (url, list_item, is_folder)


def create_listing(content, content_type):
    """ Populates listing of items and displays the contents in the Kodi interface. """
    _handle = get_addon_handle()

    # Get colors here instead of calling get_setting() for each item.
    colors = {"title": get_setting("title_color"), "folder": get_setting("folder_color")}

    # Generate the listing items.
    listing = [create_list_entry(item, colors) for item in content]
    # Add our listing to Kodi.
    xbmcplugin.addDirectoryItems(_handle, listing, len(listing))

    # The first sort method added is applied and the others appear as options.
    xbmcplugin.addSortMethod(_handle, int(get_setting("sort_method")))
    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_NONE)
    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_VIDEO_SORT_TITLE)
    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_DURATION)
    xbmcplugin.endOfDirectory(_handle)

    # Mark the contents of the folder to tell kodi how to display it.
    xbmcplugin.setContent(_handle, content_type)


def new_search():
    """
    Returning to search results after playing a video is broken in kodi.
    The video listing is "updated" to mark the video as played, which invalidates the cache.
    This causes the addon to be called again with the search param URL, triggering a new search.
    See: https://forum.kodi.tv/showthread.php?tid=351108
    The solution is to replace current xbmc window with a call to our addon to show the results.
    """
    # Request user input for the search query.
    query = get_user_input(localize(33027))

    # Don't perform an empty search.
    if query:
        api_data = {"type": "results", "yle_id": query}
        url = create_callback_url(api_data)
        xbmc.executebuiltin(f"Container.Update({url}, replace)")


def play_media_stream(url, stream_format, headers):
    """ Opens the url (with inputstream adaptive if not a local file) to play the media. """
    _handle = get_addon_handle()

    if headers:
        headers = urlencode(headers)
        # Affix the headers twice: to the URL (ffmpeg), and for inputstream.adaptive
        # This ensures the headers will be affixed if a different inputstreamer is used.
        url = f"{url}|{headers}"

    play_item = xbmcgui.ListItem(path=url)
    play_item.setContentLookup(False)

    # Try to use inputstream adaptive for network stream playback.
    if stream_format:
        play_item.setProperty("inputstream", "inputstream.adaptive")
        play_item.setProperty("inputstream.adaptive.stream_headers", headers)
        play_item.setProperty("inputstream.adaptive.manifest_type", stream_format)

    xbmcplugin.setResolvedUrl(_handle, True, listitem=play_item)
