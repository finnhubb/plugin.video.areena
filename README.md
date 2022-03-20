# Unofficial Yle Areena add-on for Kodi
[![Yle logo](images/yle.png)](https://areena.yle.fi/tv)
[![GPLv3 logo](images/gplv3.png)](https://gnu.org/licenses/gpl-3.0)
[![Kodi logo](images/kodi.png)](https://kodi.tv)

===
[Yle Areena](https://areena.yle.fi/tv) add-on for [Kodi](https://github.com/xbmc/xbmc) using combination of web scraping and Yle API. 
This add-on enables Kodi (open source home theater software) playback of live TV and video on demand from Yle, the Finnish Broadcasting Company.

Note: Unofficial project with no endorsement/approval from Kodi Foundation or Yle. It replaces obsolete add-on with the same name from [hirsivaja](https://github.com/hirsivaja/plugin.video.areena).


## Features
- Finnish and Swedish language support.
- Watch live TV channels (up to 48 hour server-side timeshift).
- Browse TV and Movies by category.
- Browse TV and Movies by genre.
- Browse TV by alphabetical order.
- Watch video on demand in HD with subtitles.
- Download video on demand in HD with subtitles.
- Search function.
- DRM restricted content is not supported. (This add-on respects your freedom.)
- Significantly faster than areena.yle.fi in web browser, using much less cpu/ram/battery.
- Memory cache for listings.


## Requirements
This add-on is built for Kodi 19-Matrix.
It requires:
 - Kodi v19.0 (Matrix) or newer.
 - Python 3.6 or newer.
 - [inputstream.adaptive](https://github.com/xbmc/inputstream.adaptive) for video playback with subtitle support.
 - [requests](https://github.com/psf/requests) for network connections.
 - [gazpacho](https://github.com/maxhumber/gazpacho) (bundled) for parsing scraped web pages.


## Installation

 1. [Download](https://kodi.tv/download/) and install Kodi.

 2. [Download]() plugin.video.areena.zip.

 3. Install from Kodi menu: `Add-ons -> Add-on browser -> Install from zip file -> plugin.video.areena.zip`


## Known issues
- Subtitle playback issue for some streams.

  HLS VTT subtitle playback is problematic in Kodi 19-Matrix. Increased support has been added for inputstream.adaptive in Kodi 20-Nexus.
  (Problem is timestamp formatting and exists even if subtitles are downloaded locally and added manually).
  Most streams are MPD from Kaltura with working subtitles. HLS VTT streams direct from Yle may have unplayable subtitles.
  <https://github.com/xbmc/inputstream.adaptive/wiki/Support-for-subtitle-formats>

- Downloaded video issue for some streams.

  Most content is hosted on Kaltura, which is downloadable. Content hosted direct from Yle only provides HLS streams.
  To download these videos, try [yle-dl](https://github.com/aajanki/yle-dl).

- A-Z Alphabetical items in wrong category issue.

  It is possible that content was added or removed from Yle after fetching the list of categories. First try to clear cache from settings menu.
  If items are "leaking" into the previous/next category (eg items starting with 'A' in B-category), file a bug report.
  (This occurs when new alphabet categories of non-Finnish letters are released, and Yle puts them in incorrect order.)
  Some miscategorisations are direct from Yle website, and are unfixable.

- AREENA live TV channel does not always have broadcast stream. When there is no stream, there is nothing to play...

- Sometimes live TV channel streams start playing from beginning of available timeshift (eg -24h or -48h) instead of "live".

- Maximum resolution setting only applies to live TV. For video on demand, inputstream.adaptive handles resolution.



## FAQ
- How to change resolution/subtitles/audio?

>  Open inputstream.adaptive add-on settings and set `Stream Selection` to `Manual`.
>  When video is playing, select desired resolution/subtitles/audio from stream options.

- How to see better search results?

>  Search function is identical to the search box on Yle Areena - not so good.
>  For better results, browse by category to select series/films/documentaries and then use kodi filter.

- Which colors can be used for UI settings?

>  Refer to [kodi forums](https://forum.kodi.tv/showthread.php?tid=210837) for the list of available colors.

- Add-on fails to install! How to install inputstream.adaptive?

>  It should automatically install through Kodi as a dependency for most systems.
>  For some Linux systems, install with your distribution package manager eg:
  `sudo apt install kodi-inputstream-adaptive`

- Something does not work, how to report it?

>  First enable debugging in both add-on settings and in kodi settings.
>  Submit github issue and include [debug log output](https://kodi.wiki/view/Log_file/Easy).
>  Issues that affect only MS-WINDOWS platform are considered Microsoft bugs and will not be examined.
