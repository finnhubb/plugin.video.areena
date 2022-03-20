"""
yle areena kodi plugin wrapper function.
"""
import sys

from resources.lib.router import addon_areena_main

if __name__ == '__main__':
    # Call the router function and pass the plugin call parameters to it.
    # We use string slicing to trim the leading '?' from the plugin call paramstring
    addon_areena_main(sys.argv[2][1:])
