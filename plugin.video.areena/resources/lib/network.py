"""
Network interface functions: fetch url response and download files.
"""

from random import randint

import requests

from resources.lib.logger import log


def random_elisa_ipv4():
    """
    Generates an Finnish IP address from 91.152.0.0/13.
    (Excluding the ~2k IPs ending with .0 or .255)
    """
    return f"91.15{randint(2,9)}.{randint(0,255)}.{randint(1,254)}"


def get_http_headers():
    """ HTTP headers used for yle and kaltura api requests. """
    tbb_user_agent = "Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0"
    url = "https://areena.yle.fi"
    return {"User-Agent": tbb_user_agent,
            "X-Forwarded-For": random_elisa_ipv4(),
            "Referer": url,
            "Origin": url}


def get_url_response(url, body=None):
    """ Performs HTTP request to provided url and returns response. """
    headers = get_http_headers()
    log(f"Accessing url: {url}")

    if body:
        res = requests.post(url, headers=headers, json=body)

    else:
        res = requests.get(url, headers=headers)

    log(f"Response headers: {res.headers}")
    res.raise_for_status()

    return res


def download_file(url, path, offset):
    """ Downloads a file to the filesystem. """
    headers = get_http_headers()
    log(f"Accessing url: {url}")

    # File partially exists, resume download.
    if offset:
        headers["Range"] = f"bytes={offset}-"

    res = requests.get(url, allow_redirects=True, headers=headers, stream=True)
    log(f"Response headers: {res.headers}")
    # The response will be 416 if attempting to resume a completed download.
    if res.status_code == 416:
        return

    res.raise_for_status()

    with open(path.encode("utf-8", "surrogateescape"), "ab") as file:
        for chunk in res.iter_content(chunk_size=1024**2):
            file.write(chunk)
