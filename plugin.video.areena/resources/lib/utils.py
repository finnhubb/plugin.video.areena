"""
Utility functions for yle areena kodi addon.

Notes on filenames, os functions, and encoding:

Things to remember:
- Python os functions accept either bytes or unicode strings: return type matches input type.
- Everything in the OS is bytes (eg. filenames), so use bytes as input to os functions.
- Python3 has absurd byte strings, so use unicode strings everywhere else to retain sanity.
  eg unexpected behavior -  FALSE: b"a"[0] == b"a"
- UTF-8 is a superset of 7-bit ASCII, pairs well with unicode, and is the default on modern OS.

Follow the unicode sandwich principle:
Read data in with bytes, decode as utf-8 to unicode strings.
...perform string operations on unicode...
Encode unicode strings as utf-8 when writing data out.


Since the underlying bytes can possibly be invalid utf-8, errors must be handled appropriately.
The surrogateescape error mode represents the invalid utf-8 bytes as reserved unicode code points.
It is the only error mode in python that provides lossless handling of the invalid utf-8 bytes.
eg TRUE: b"\xff" == b"\xff".decode("utf-8", "surrogateescape").encode("utf-8", "surrogateescape")

The caveat is that this is a python-specific representation of the bytes
and may not the default error handler for all functions on all systems.
Beware when passing the unicode strings to external functions that may encode them differently.

In particular, kodi functions do not handle surrogatescaped unicode, but accepts bytes.
"""
import os

from resources.lib.kodi import get_setting, get_download_path, create_EEXIST_popup, get_user_input


def get_max_bitrate_resolution_from_settings() -> int:
    """
    Bitrate corresponding to user specified resolution limit.
    Bitrate values extracted from: $youtube-dl --list-formats url
    """
    # Maps to resolution [Automatic, 180, 270, 360, 576, 720, 1080]
    # Live urls are maximum 720p, so use that by default.
    bitrate = [None, 184, 414, 896, 1896, 4096, None]
    resolution_limit = int(get_setting("max_resolution"))

    return bitrate[resolution_limit] or 4096


def get_local_directory_items(path):
    """ Gets a list of items from a local directory and their full paths. """
    # The path argument to os.listdir must be bytes
    # to force the returned value to be bytes.
    dirpath = path.encode("utf-8", "surrogateescape")
    dirlist = os.listdir(dirpath)
    files = [f for f in dirlist if f.endswith(b".mp4")]
    filepaths = [os.path.join(dirpath, fname) for fname in files]

    return [(x.decode("utf-8", "surrogateescape"), y.decode("utf-8", "surrogateescape"))
            for (x, y) in zip(files, filepaths)]


def get_subtitle_filepath(filepath, subext):
    """ Formats the path to save the subtitle file to and deletes file if it exists. """
    # Extract basename and path.
    path, file = os.path.split(filepath.encode("utf-8", "surrogateescape"))
    # Remove file extension.
    fname, _ = os.path.splitext(file)
    # Append subtitle extension.
    subpath = os.path.join(path, fname + subext.encode("utf-8", "surrogateescape"))

    if os.path.isfile(subpath):
        os.remove(subpath)

    return subpath.decode("utf-8", "surrogateescape")


def get_download_filepath(title, ext):
    """
    Generates the full path to save the downloaded file.
    If the file exists, user is prompted to replace, rename, resume or cancel.
    """
    filesize = 0
    target_dir = get_download_path().encode("utf-8", "surrogateescape")

    # Replaces slashes to avoid invalid POSIX filenames.
    filename = (title + ext).replace("/", ":")
    filepath = os.path.join(target_dir, filename.encode("utf-8", "surrogateescape"))

    # Loop while suggested target filename exists.
    while os.path.isfile(filepath):
        # Ask user how to proceed with existing file.
        user_choice = create_EEXIST_popup(filename)

        if user_choice == "cancel":
            filepath = b""
            break

        if user_choice == "replace":
            os.remove(filepath)
            break

        if user_choice == "resume":
            # Calculate the file size to use for resume offset writes.
            filesize = os.path.getsize(filepath)
            break

        if user_choice == "rename":
            filename = get_user_input(f"{title} ({ext})")

            # User provided no filename; cancel.
            if not filename:
                filepath = b""
                break

            # Replaces any slashes to avoid directory traversal.
            filename = (filename + ext).replace("/", ":")
            filepath = os.path.join(target_dir, filename.encode("utf-8", "surrogateescape"))

    return filename, filepath.decode("utf-8", "surrogateescape"), filesize
