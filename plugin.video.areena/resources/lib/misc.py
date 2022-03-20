"""
Miscellaneous helper functions for yle areena kodi addon.
"""

import re


def kwdict(**kwargs):
    """  Helper function: populates dictionary with keyword arguments. """
    return kwargs


def mkdict(name, _type, _yle_id=None, icon=None):
    """ Helper function to create dictionary for media data. """
    _api_data = {x:y for x,y in kwdict(type=_type, yle_id=_yle_id).items() if y}
    return {x:y for x,y in kwdict(name=name, image=icon, api_data=_api_data).items() if y}


def extract_suffix(word, string):
    """ Returns suffix from string after first occurrence of word, else -1."""
    start = string.find(word) + len(word)
    return string[start:]


def get_duration_seconds(time_stamp):
    """ Parses the ISO8601 timestamp into a duration of total seconds. """
    # ISO8601_PERIOD_REGEX adapted from isodate module.
    rgx = re.compile(
        r"^(?P<sign>[+-])?"
        r"P(?!\b)"
        r"(?P<years>[0-9]+([,.][0-9]+)?Y)?"
        r"(?P<months>[0-9]+([,.][0-9]+)?M)?"
        r"(?P<weeks>[0-9]+([,.][0-9]+)?W)?"
        r"(?P<days>[0-9]+([,.][0-9]+)?D)?"
        r"((?P<separator>T)((?P<hours>[0-9]+([,.][0-9]+)?)H)?"
        r"((?P<minutes>[0-9]+([,.][0-9]+)?)M)?"
        r"((?P<seconds>[0-9]+([,.][0-9]+)?)S)?)?$"
    )

    try:
        match = re.match(rgx, time_stamp).groupdict()
    except (AttributeError, LookupError, TypeError, ValueError):
        return ""

    seconds = (float(match.get("hours") or 0) * 3600
             + float(match.get("minutes") or 0) * 60
             + float(match.get("seconds") or 0))

    return str(seconds)
