"""
Kaltura API functions for yle areena kodi addon.

The kaltura API accepts a POST request with a specified kaltura_id
It returns:
    1. flavorAssts: list of available resolutions (flavors) for that media id
    2. sources: list of streams (format) that support each flavor

This module select a source with "deliveryProfileId" containing
"id" from a "flavorAsset" with desired resolution.

The delivery profile ids appear to be mostly static.
eg. 1080p mpegdash with subtitles always has delivery profile id 14471.

Live streams sometimes differ.

formats:
"mpegdash" (MPD) - best subtitle support.
"applehttp" (HLS)
"hdnetworkmanifest" (F4M) - flash media manifest.
"url" (MP4) - direct link to media file.

Example ["flavorAssets"] entry
{
"flavorParamsId": 1005961,
"width": 1920,
"height": 1080,
"id": "1_abc123xyz", # match
...
}

Example ["sources"] entry
{
"deliveryProfileId": 14471,
"format": "mpegdash",
"protocols": "http,https",
"flavorIds": "1_789xyz345,1_abc123xyz", # match
"url": "https://cdnapisec.kaltura.com/.../manifest.mpd",
"drm": [],
"objectType": "KalturaPlaybackSource"
}

"""

import json
import re
from resources.lib.logger import log
from resources.lib.misc import extract_suffix


def get_api_url(service):
    """ API endpoint for Kaltura CDN that hosts most yle videos and subtitles. """
    return f"https://cdnapisec.kaltura.com/api_v3/service/{service}"


def get_subtitle_url(url):
    """ Extracts subtitle info from provided url and crafts downloadable url. """
    return get_api_url(extract_suffix("service/", url))


def get_api_payload(entry_id):
    """
    Kaltura api request payload. Thanks to yle-dl.
    https://developer.kaltura.com/api-docs/service/session/action/startWidgetSession
    https://developer.kaltura.com/api-docs/service/baseEntry/action/getPlaybackContext
    """
    return {
        "apiVersion": "3.3.0",
        "format": 1,
        "ks": "",
        "clientTag": "html5:v0.39.4",
        "partnerId": "1955031",
        "0": {
            "service": "session",
            "action": "startWidgetSession",
            "widgetId": "_1955031",
        },
        "1": {
            "service": "baseEntry",
            "action": "getPlaybackContext",
            "entryId": entry_id,
            "ks": "{1:result:ks}",
            "contextDataParams": {
                "objectType": "KalturaContextDataParams",
                "flavorTags": "all",
            },
        },
    }


def get_hd_mpd_stream_manifest(site, mode):
    """ Selects highest quality stream manifest from kaltura. """
    log(f"Kaltura stream flavors:{json.dumps(site.json(), indent=2)}")

    sources = site.json()[1]["sources"]

    if mode == "live":
        target_stream = 16231
    elif mode == "download":
        # mp4
        target_stream = 14441
    elif mode == "vod":
        # 1080 mpeg-dash with subs
        target_stream = 14471

    manifest = next(s.get("url") for s in sources if s.get("deliveryProfileId") == target_stream)

    if mode == "download":
        # strip all flavors except the last one, which should be 1080p.
        manifest = re.sub("[0-9][^,/]+,", "", manifest)

    return manifest


def get_subtitles(site):
    """ Extracts all language subtitles and crafts the direct download url. """
    subs = site.json()[1]["playbackCaptions"]
    return {f'.{c.get("label")}-{c.get("languageCode")}.sub': get_subtitle_url(c.get("url")) for c in subs}
