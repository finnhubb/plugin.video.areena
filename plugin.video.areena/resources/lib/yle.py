"""
Yle areena scraping, parsing, and API functions.

Scrapes yle web pages and parses json responses into the following format:

media_data: {
    "name": program title,
    "description" : program plot,
    "duration": str(float(seconds)),
    "image": "https://images.cdn.yle.fi/.../.jpg",
    "api_data": {
        "type": "series",
        "yle_id": "/1-12345" or "/tv/ohjelmat/30-12"
        "kaltura_id": "/1_ab12xy"
    }
}

The media_data is used to construct the kodi item listings.
The api_data is used to create url requests for stream manifests.

"""
import json

from resources.lib.logger import log
from resources.lib.misc import extract_suffix, get_duration_seconds, kwdict
from resources.lib.gazpacho import Soup


def get_base_url(locale):
    """ Get the base yle areena url for Finnish or Swedish, based on language settings. """
    return {"fi": "https://areena.yle.fi",
            "sv": "https://arenan.yle.fi"}.get(locale)


def get_package_path(locale):
    """ Gets the path for package/series content. eg yle.areena.fi/tv/ohjelmat/12345"""
    return {"fi": "/tv/ohjelmat/",
            "sv": "/tv/program/"}.get(locale)


def get_live_tv_url(media_id):
    """ Returns resolution specific live tv channel url. """
    return f"https://yletv.akamaized.net/hls/live/{media_id}/master.m3u8"


def get_image_url(_version, _id):
    """ constructs artwork image url for a series/episode/movie item. """
    return (f"https://images.cdn.yle.fi/image/upload/"
            f"ar_16:9,w_720,c_fit,d_yle-areena.jpg,f_auto,fl_lossy,q_auto:eco/"
            f"v{_version}/{_id}.jpg")


def get_api_live_url(media_id, language):
    """ Constructs yle api live stream url for a supplied media_id. """
    return (f"https://areena.api.yle.fi/v1/ui/players/{media_id}.json?"
            f"language={language}&"
            f"v=9&"
            f"app_id=player_static_prod&"
            f"app_key=8930d72170e48303cf5f3867780d549b")


def get_api_stream_url(media_id):
    """ Constructs yle api stream preview url for a supplied media_id. """
    return (f"https://player.api.yle.fi/v1/preview/{media_id}.json?"
            f"language=fin&"
            f"ssl=true&"
            f"countryCode=FI&"
            f"host=areenaylefi"
            f"&app_id=player_static_prod"
            f"&app_key=8930d72170e48303cf5f3867780d549b")


def get_api_list_url(content_or_packages, token, language):
    """ Constructs yle api query with supplied token (signed jwt specifying the query). """
    return (f"https://areena.api.yle.fi/v1/ui/{content_or_packages}/list?"
            f"token={token}&"
            f"language={language}&"
            f"v=9&"
            f"app_id=areena_web_personal_prod&"
            f"app_key=6c64d890124735033c50099ca25dd2fe")


def get_api_episodes_url(token, yle_id, language):
    """ Constructs yle api query with supplied token (signed jwt specifying the query). """
    return (f"https://areena.api.yle.fi/v1/ui/content/list?"
            f"token={token}&"
            f"path.season={yle_id}&"
            f"language={language}&"
            f"v=9&"
            f"client=yle-areena-web&"
            f"app_id=areena-web-items&"
            f"app_key=v9No1mV0omg2BppmDkmDL6tGKw1pRFZt")


def get_api_search_url(query, language):
    """ Constructs yle api url for a supplied search query. """
    return (f"https://areena.api.yle.fi/v1/ui/search?"
            f"app_id=areena_web_frontend_prod&"
            f"app_key=4622a8f8505bb056c956832a70c105d4&"
            f"client=yle-areena-web&"
            f"language={language}&"
            f"v=9&"
            f"episodes=true&"
            f"packages=true&"
            f"query={query}&"
            f"service=tv&"
            f"offset=0&limit=999")


def get_api_alphabetical_token(locale):
    """ Returns language specific api token to access alphabetical categories. """
    return {
    "fi": ("eyJhbGciOiJIUzI1NiJ9.eyJzb3VyY2UiOiJodHRwczovL3BhY2thZ2VzLmFwaS55bGUuZmkvdjQvcGFja2Fn"
           "ZXMvMzAtNDg4L2FvLmpzb24_Z3JvdXBpbmc9dGl0bGUuZmkmbGFuZ3VhZ2U9ZmkiLCJwcmVzZW50YXRpb25Pd"
           "mVycmlkZSI6Imxpc3RDYXJkIiwiYW5hbHl0aWNzIjp7ImNvbnRleHQiOnsiY29tc2NvcmUiOnsieWxlX3JlZm"
           "VyZXIiOiJ0di52aWV3LjU3LVJ5eUpud2I5Yi5rYWlra2lfdHZfb2hqZWxtYXQuYV9vLnVudGl0bGVkX2xpc3Q"
           "iLCJ5bGVfcGFja2FnZV9pZCI6IjMwLTQ4OCJ9fX19.3aS55Qzc98NXw3s_05dwspnKO5uKWktr8FYaDOzo1P0"),

    "sv": ("eyJhbGciOiJIUzI1NiJ9.eyJzb3VyY2UiOiJodHRwczovL3Byb2dyYW1zLmFwaS55bGUuZmkvdjMvc2NoZW1hL"
           "3YxL3BhY2thZ2VzLzMwLTQ4OC9hbz9ncm91cGluZz10aXRsZS5zdiZsYW5ndWFnZT1zdiIsInByZXNlbnRhdGl"
           "vbk92ZXJyaWRlIjoibGlzdENhcmQiLCJhbmFseXRpY3MiOnsiY29udGV4dCI6eyJjb21zY29yZSI6eyJ5bGVfc"
           "mVmZXJlciI6InR2LnZpZXcuNTctUnl5Sm53YjliLmFsbGFfdHZfcHJvZ3JhbS5hX28udW50aXRsZWRfbGlzdCI"
           "sInlsZV9wYWNrYWdlX2lkIjoiMzAtNDg4In19fX0.v4kayxYaMtPxseJCAKrueSHwNca7nVmvjECwMdhQMkQ")
            }.get(locale)


def get_root_categories(site):
    """ Scrapes the yle areena home page menu bar for a list of categories. """
    categories = []
    soup = Soup(site.text).find("li", {"class": "menu__item"})
    menu_items = [x.find("a") for x in soup]

    _type = "category"

    for entry in menu_items:
        _name = entry.text
        _id = entry.attrs.get("href")

        # Discard live-tv channels, alphabetical and duplicate categories.
        if not _name or any(x in _id for x in [":", "?", "kaikki", "alla"]):
            continue

        api_data = kwdict(type=_type, yle_id=_id)
        media_data = kwdict(name=_name, api_data=api_data)
        categories.append(media_data)

    return categories


def get_sub_categories(site):
    """ Scrapes the yle areena category page for JSON and extracts a list of subcategories. """
    categories = []
    soup = Soup(site.text).find("div", {"class": "package-view"}).attrs.get("data-view")
    json_data = json.loads(soup)["tabs"][0]["content"]

    _type = "subcategory"

    for entry in json_data:
        _name = entry.get("title", "")

        try:
            _id = entry["controls"][0]["destination"]["uri"].split("/")[-1]
            _api_tok = extract_token(entry["source"]["uri"])
        except (AttributeError, LookupError, TypeError, ValueError):
            continue
        api_data = kwdict(type=_type, yle_id=_id, api_tok=_api_tok)
        media_data = kwdict(name=_name, api_data=api_data)
        categories.append(media_data)

    return categories


def get_season_ids(site, show_clips):
    """ Scrapes the yle areena season page for JSON and extracts a list of season ids and content link. """
    soup = Soup(site.text).find("script", {"id": "__NEXT_DATA__"})
    json_data = json.loads(soup.text)

    jwt_url = json_data['props']['pageProps']['view']['tabs'][0]['content'][0]['source']['uri']
    api_tok = extract_token(jwt_url)
    api_tok = api_tok[:api_tok.rfind("&path")]

    seasons = json_data['props']['pageProps']['view']['tabs'][0]['content'][0]['filters']
    payload = []

    if seasons:
        paths = seasons[0]['options']
        payload += [(x['title'], x['parameters']['path.season']) for x in paths]

    elif show_clips:
        payload += [("", "")]

    return (api_tok, payload)


def sort_alphabetical_categories(categories):
    """
    Queries are performed by requesting a sequence of items with an offset.
    The offset is the number of items to skip.
    (ie the cumulative number of prior entries in the list).
    The order that the content is stored does not match the order the content is listed.
    Therefore the order needs adjusting before calculating offsets.

    listed order: A-Z,À,Ä,Å,Ö,Þ,Ž
    stored order: A-T,Þ,U-Z,Ž,Å,Ä,Ö
    """
    alphabet = ["0-9","A","À","B","C","D","E","F","G","H","I","J","K","L","M","N","O",
                  "P","Q","R","S","T","Þ","U","V","W","X","Y","Z","Ž","Å","Ä","Ö"]
    # Sort the list of dictionaries by their "name" value, using the provided sort ordering.
    sorted_categories = sorted(categories, key=lambda entry: alphabet.index(entry["name"]))
    offset = 0

    for item in sorted_categories:
        # Set the offset to the cumulative total of contents for previous categories.
        item["api_data"]["offset"] = offset

        # Increment the offset by the size of this category.
        offset += item["api_data"]["count"]

    return sorted_categories


def get_alphabetical_categories(site, locale):
    """ Parses JSON for a list of alphabetical categories and the number of items per category. """
    categories = []
    json_data = site.json()["meta"]["resultGroups"]
    log(f"Alphabetical content: {json.dumps(json_data, indent=2)}")

    _type = "subcategory"
    _id = "-"
    _api_tok = get_api_alphabetical_token(locale)

    for entry in json_data:
        _name = entry.get("key", "")
        _count = int(entry.get("count", "0"))

        _api_data = kwdict(type=_type, yle_id=_id, count=_count, api_tok=_api_tok)
        media_data = kwdict(name=_name, api_data=_api_data)
        categories.append(media_data)

    return sort_alphabetical_categories(categories)


def get_category_content(site, locale, title_prefix=None):
    """ Extracts all media (programs and series lists) from the yle API JSON response. """
    content = []
    json_data = site.json()["data"]
    log(f"Category content: {json.dumps(json_data, indent=2)}")
    title_prefix = title_prefix or ""

    for entry in json_data:
        _name = entry.get("title", "")
        _type = entry.get("pointer", {}).get("type", "")
        _id = entry.get("pointer", {}).get("uri", "").split("/")[-1]
        _description = entry.get("description", "")

        # Packages require additional scraping, so the full path is needed.
        if _type == "package":
            _id = get_package_path(locale) + _id

        try:
            _image = get_image_url(entry["image"]["version"], entry["image"]["id"])
        except (AttributeError, LookupError, TypeError, ValueError):
            _image = ""

        try:
            _duration = extract_duration_timestamp(entry["labels"])
        except (AttributeError, LookupError, TypeError, ValueError):
            _duration = ""

        api_data = kwdict(type=_type, yle_id=_id)
        media_data = kwdict(name=f"{title_prefix} {_name}",
                            description=_description,
                            duration=_duration,
                            image=_image,
                            api_data=api_data)
        content.append(media_data)

    return content


def create_api_query(url, limit, offset):
    """ Appends an offset and receiving limit for a content list request. """
    return url + f"&limit={limit}&offset={offset}"


def get_query_content(res, locale):
    """ Parses response for appropriate content and returns the total number of items available. """
    content = get_category_content(res, locale)
    count = res.json()["meta"]["count"]

    return (content, count)


def extract_duration_timestamp(json_data):
    """ Find and parse the duration timestamp stored in inconsistent locations in the JSON. """
    timestamp = (i.get("raw") for i in json_data if i.get("rawType") == "duration")
    try:
        return get_duration_seconds(next(timestamp))
    except StopIteration:
        return ""


def extract_token(url):
    """
    Extracts the relevant web-browser api link that will return JSON list of media.
    e.g. https://areena.api.yle.fi/v1/ui/content/list?token=eyJ0eXAiOiJKV1QiLCJhbG...
    The token is JWT HMAC'd server-side with HS256, so we cannot craft custom queries.
    Since the server rejects unauthenticated JWT the tokens must be scraped from yle.
    """
    return extract_suffix("token=", url)


def get_kaltura_id_or_none(media_data):
    """
    Determines content provider of the stream media.
    Only kaltura streams use the media_id in the api requests.
    """
    # Need to return empty string as "None" would be converted
    # to the string "None" when urlencoded as a callback parameter.
    if not media_data:
        return ""

    media_info = media_data.split("-")
    media_host = media_info[0]

    # Kaltura
    if media_host == "29":
        media_id = media_info[1]

    # yleawodamd.akamaized.net, yleawsmpodamdip4v
    elif media_host in ["55", "67"]:
        media_id = ""

    else:
        # Raise an error for media_id is unreferenced to learn the new type.
        log(f"Unknown stream media type: {media_data}")

    return media_id


def get_stream_manifest(site):
    """ Extracts the media_id and stream manifest from the yle api json response. """
    json_data = site.json()["data"].get("ongoing_ondemand", {}) or site.json()["data"].get("ongoing_event", {})
    manifest_url = json_data.get("manifest_url")
    media_data = json_data.get("media_id")
    return manifest_url, get_kaltura_id_or_none(media_data)


def get_live_stream_media_id(site):
    """ Extracts the media_id for a live stream from the yle api json response. """
    log(f"Live stream: {json.dumps(site.json(), indent=2)}")
    return site.json()["data"]["live"]["item"]["id"]
