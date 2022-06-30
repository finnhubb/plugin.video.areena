"""
Top level abstraction for program logic.

The addon_areena_main can be considered equivalent to the main event loop.
It is stateless, and events are user interactions within the kodi addon
(passed to the event loop function in the form of callback parameters, with data)
triggering appropriate actions.

General flow of program usage, navigating through kodi to play a stream:

1. Categories (and genres) are scraped from areena.yle.fi as the user navigates.
    Listing for each category created by kodi.
2. API tokens for accessing content within those categories are scraped.
    Listing for each subcategory created by kodi.
3. API calls return json data for media items, which is parsed to extract media data.
    Listings for each media item created by kodi.
4. API call to yle requesting stream manifest url (HLS)
    If it's an yle stream it's already HD, so play it with inpustream.adaptive.
    If it's a kaltura stream it's only 720p max
5. API call to kaltura to request 1080p stream manifest url (MPD)
    Play it with inputstream.adaptive.

Each stage 1-4 operates using an yle_id which refers to the desired content.
This field _mostly_ corresponds to the path on areena. eg 1-12345 yle.areena.fi/1-12345

Step 5 uses a kaltura_id to look up the 1080 kaltura stream flavor.
These are extracted from the yle json. eg 1_ab12xy

For each step 1-3 if the results exist in the memory cache, they are used.
If they don't exist, the results are cached for subsequent access.
This reduces latency of navigating by limiting repetitive network requests.
The cache lives only in RAM and is cleared on kodi exit, or through the addon settings.

"""
import json

from urllib.parse import parse_qsl

from resources.lib.logger import log
from resources.lib.misc import mkdict
from resources.lib.network import download_file, get_http_headers, get_url_response
from resources.lib import cache
from resources.lib import kaltura
from resources.lib import kodi
from resources.lib import utils
from resources.lib import yle


def addon_areena_main(param_string):
    """ Router function that decides action depending on param_string addon was invoked with. """
    # Parse a URL-encoded param_string to the dictionary of
    # {<parameter>: <value>} elements
    params = dict(parse_qsl(param_string))

    # Check the parameters passed to the plugin.
    if not params:
        # The plugin was called from Kodi UI without any parameters.
        event_type = "menu"
    else:
        event_type = params.get("type", "")

    locale = kodi.get_setting("language")
    log(f"Performing action: {str(params)}")

    if event_type in ["category", "package", "subcategory", "alphabetical", "series", "results"]:
        try_cache(param_string, locale) or show_remote_list(event_type, params, param_string, locale)

    elif event_type in ["search", "settings", "clear_cache", "download"]:
        do_command(event_type, params)

    elif event_type in ["menu", "channel", "downloads"]:
        show_local_list(event_type)

    elif event_type in ["program", "clip", "video", "live"]:
        play_media(event_type, params, locale)

    else:
        log(f"Unknown event: {event_type}")


def do_command(event_type, params):
    """ Runs the specified command action. """
    if event_type == "download":
        yle_id = params.get("yle_id", "")
        kaltura_id = params.get("kaltura_id", "")
        filename = params.get("filename", "")
        try_download_video(yle_id, kaltura_id, filename)

    elif event_type == "search":
        # Requests user input for a search.
        kodi.new_search()

    elif event_type == "settings":
        # Display settings for the addon.
        kodi.open_settings()

    elif event_type == "clear_cache":
        # Clears the memory cache of listings.
        cache.erase()


def play_media(event_type, params, locale):
    """ Plays a live broadcast, vod stream, or local file. """
    yle_id = params.get("yle_id", "")
    kaltura_id = params.get("kaltura_id", "")

    if event_type == "live":
        # Live TV channel.
        manifest, stream_format = get_live_stream_manifest(yle_id, locale)
        headers = get_http_headers()

    elif event_type in ["program", "clip"]:
        # Video on demand media.
        manifest, stream_format, _ = get_vod_stream_manifest(yle_id, kaltura_id, "vod")
        headers = get_http_headers()

    elif event_type == "video":
        # Local media file.
        manifest = yle_id
        stream_format = None
        headers = None

    kodi.play_media_stream(manifest, stream_format, headers)


def show_local_list(event_type):
    """ Displays a list of content. """
    if event_type == "menu":
        # Addon home screen.
        content = populate_home_menu()
        # List type should be files, but prevents kodi showing custom icons.
        list_type = ""

    elif event_type == "channel":
        # List of live channels.
        content = populate_tv_channels()
        list_type = "videos"

    elif event_type == "downloads":
        # List of downloaded content.
        content = populate_downloads()
        list_type = "videos"

    kodi.create_listing(content, list_type)


def show_remote_list(event_type, params, param_string, locale):
    """ Generates, caches and displays a list of remote content. """
    yle_id = params.get("yle_id", "")

    if event_type in ["category", "package"]:
        # List of subcategories in the selected category.
        content = get_category(yle_id, locale)
        list_type = "files"

    elif event_type == "subcategory":
        # List of content in the selected subcategory.
        # Yle api JWT for specific series or category.
        api_tok = params.get("api_tok", "")
        # Number of expected results and offset for api query.
        offset = int(params.get("offset", "0"))
        count = int(params.get("count", "2000"))

        content = get_series(locale, api_tok, offset, count)
        list_type = "movies"

    elif event_type == "alphabetical":
        # List of all TV series in alphabetical order.
        content = get_alphabetical_categories(locale)
        list_type = "videos"

    elif event_type == "series":
        # List of episodes for the selected series.
        content = get_episodes(yle_id, locale)
        list_type = "episodes"

    elif event_type == "results":
        # List of search results from yle.
        content = get_search_results(yle_id, locale)
        list_type = "videos"

    log(f"Content list: {event_type} {json.dumps(content, indent=2)}")
    cache.add_data(locale + param_string, content, list_type)
    kodi.create_listing(content, list_type)


def try_cache(param_string, locale):
    """ Create pages for the specific param_string if the contents exist in cache. """
    cached_data = cache.get_data(locale + param_string)

    if not cached_data:
        return False

    content, content_type = cached_data
    kodi.create_listing(content, content_type)

    return True


def get_category(path, locale):
    """ Fetches category items. """
    url = yle.get_base_url(locale) + path
    res = get_url_response(url)

    if path == "/tv":
        return yle.get_root_categories(res)

    return yle.get_sub_categories(res)


def get_series(locale, token, offset, count):
    """ Fetches list of series or films. """
    url = yle.get_api_list_url("content", token, locale)
    return get_extended_content(url, locale, offset, total=count)


def get_alphabetical_categories(locale):
    """ Fetches content by alphabetical category. """
    tok = yle.get_api_alphabetical_token(locale)
    url = yle.get_api_list_url("content", tok, locale)
    res = get_url_response(url)

    return yle.get_alphabetical_categories(res, locale)


def get_episodes(path, locale):
    """ Fetches media content list, usually episodes. """
    show_clips = kodi.get_setting("show_clips")
    url = yle.get_base_url(locale) + '/' + path
    res = get_url_response(url)
    token, seasons = yle.get_season_ids(res, show_clips)

    ctx = []
    for season_name, yle_id in seasons:
        url = yle.get_api_episodes_url(token, yle_id, locale)
        res = get_url_response(url)
        ctx += yle.get_category_content(res, locale, season_name)
    return ctx


def get_extended_content(base_url, locale, offset, total):
    """ Fetches list of content (series/films or episodes) that requires multiple api calls. """
    ctx = []
    while total > 0:
        # Number of results to request.
        requested = min(total, 100)
        url = yle.create_api_query(base_url, requested, offset)
        res = get_url_response(url)
        content, count = yle.get_query_content(res, locale)
        ctx.extend(content)
        # Total available remaining entries on the server for this category.
        total = min(total, count) - requested
        # Increment the offset by the number of results.
        offset += requested

    return ctx


def get_search_results(query, locale):
    """ Fetches content results for the supplied search query. """
    url = yle.get_api_search_url(query, locale)
    res = get_url_response(url)

    return yle.get_category_content(res, locale)


def populate_tv_channels():
    """ Creates the live tv channel items. """
    return [
        mkdict("yle TV1", "live", "622365/yletv1fin", kodi.get_icon_path("tv1.png")),
        mkdict("yle TV2", "live", "622366/yletv2fin", kodi.get_icon_path("tv2.png")),
        mkdict("yle TEEMA FEM", "live", "622367/yletvteemafemfin", kodi.get_icon_path("teema_fem.png")),
        # Note: the yle-areena broadcast requires an api call to get the stream url.
        mkdict("yle AREENA", "live", "yle-areena", kodi.get_icon_path("y_areena.png"))
    ]


def populate_home_menu():
    """ Creates the initial addon menu items. """
    return [
        mkdict(kodi.localize(33023), "alphabetical"),
        mkdict(kodi.localize(33024), "category"),
        mkdict(kodi.localize(33025), "category", "/tv"),
        mkdict(kodi.localize(33026), "channel"),
        mkdict(kodi.localize(33027), "search", icon=kodi.get_icon_path("search.png")),
        mkdict(kodi.localize(33001), "settings", icon=kodi.get_icon_path("settings.png")),
        mkdict(kodi.localize(33020), "downloads")
    ]


def populate_downloads():
    """ Extract the list of media items saved to disk. """
    downloads = kodi.get_download_path()
    files = utils.get_local_directory_items(downloads)
    content = [mkdict(name, "video", path) for name, path in files]

    return content


def download_video(manifest, filename, filepath, filesize, subs):
    """ Download a video (and subtitles) directly to the file system. """
    log(f"Starting download: {filename}.")
    kodi.send_notification_download("start", filename)
    download_file(manifest, filepath, offset=filesize)

    # Download all subs, overwrite/replace if they exist.
    for subname, url in subs.items():
        subpath = utils.get_subtitle_filepath(filepath, subname)
        download_file(url, subpath, offset=0)

    log(f"Download of {filename} completed successfully.")
    kodi.send_notification_download("success", filename)


def try_download_video(yle_id, kaltura_id, filename):
    """ Download a video if it is downloadable. """
    manifest, stream_format, subs = get_vod_stream_manifest(yle_id, kaltura_id, mode="download")

    # Yle hosted streams not supported for download.
    if stream_format == "hls":
        log(f"Download of {filename} failed: Stream type not supported for download.")
        kodi.send_notification_download("failed", filename)

    filename, filepath, filesize = utils.get_download_filepath(filename, ext=".mp4")

    if filepath:
        download_video(manifest, filename, filepath, filesize, subs)


def get_hls_stream_manifest(yle_id):
    """ Fetches the url for the HLS stream manifest url (m3u) from yle areena. """
    url = yle.get_api_stream_url(yle_id)
    res = get_url_response(url)
    manifest, kaltura_id = yle.get_stream_manifest(res)

    return manifest, kaltura_id


def get_mpd_stream_manifest(kaltura_id, mode):
    """ Fetches the playable MPD stream manifest url (mpd) from kaltura. """
    url = kaltura.get_api_url("multirequest")
    payload = kaltura.get_api_payload(kaltura_id)
    res = get_url_response(url, payload)
    manifest = kaltura.get_hd_mpd_stream_manifest(res, mode)
    subtitles = None
    if mode == "download":
        subtitles = kaltura.get_subtitles(res)

    return manifest, subtitles


def get_vod_stream_manifest(yle_id, kaltura_id, mode):
    """ Fetches best playable live stream manifest. """
    # Get stream manifest from yle, and possibly kaltura_id.
    # 1080p stream is included in the hls_manifest for yleawodamd.
    if not kaltura_id:
        manifest, kaltura_id = get_hls_stream_manifest(yle_id)
        stream_format = "hls"
        subs = {}

    if kaltura_id:
        # 720p stream is included in the hls_manifest for kaltura.
        # Kaltura legacy requires api call to extract 1080p stream.
        manifest, subs = get_mpd_stream_manifest(kaltura_id, mode)
        stream_format = "mpd"

    return manifest, stream_format, subs


def get_live_broadcast(media_id, locale):
    """ Fetches the playable stream manifest for the live AREENA broadcast. """
    url = yle.get_api_live_url(media_id, locale)
    res = get_url_response(url)
    yle_id = yle.get_live_stream_media_id(res)
    manifest, _ = get_hls_stream_manifest(yle_id)

    return manifest


def get_live_stream_manifest(yle_id, locale):
    """ Fetches appropriate playable live stream manifest. """
    if yle_id == "yle-areena":
        manifest = get_live_broadcast(yle_id, locale)
    else:
        manifest = yle.get_live_tv_url(yle_id)

    return manifest, "hls"
