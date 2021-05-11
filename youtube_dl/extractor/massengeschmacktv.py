from __future__ import unicode_literals

import re
import locale
import datetime

from .common import InfoExtractor
from ..utils import (
    clean_html,
    determine_ext,
    int_or_none,
    js_to_json,
    mimetype2ext,
    parse_filesize,
    unified_strdate,
)


class MassengeschmackTVIE(InfoExtractor):
    IE_NAME = 'massengeschmack.tv'
    _VALID_URL = r'https?://(?:www\.)?massengeschmack\.tv/play/(?P<id>[^?&#]+)'

    _TEST = {
        'url': 'https://massengeschmack.tv/play/fktv202',
        'md5': 'a9e054db9c2b5a08f0a0527cc201e8d3',
        'info_dict': {
            'id': 'fktv202',
            'ext': 'mp4',
            'title': 'Fernsehkritik-TV - Folge 202',
        },
    }

    def _real_extract(self, url):
        # Metadata
        episode = self._match_id(url)

        webpage = self._download_webpage(url, episode)

        thumbnail = self._search_regex(r'POSTER\s*=\s*"([^"]+)', webpage, 'thumbnail', fatal=False)

        title = self._html_search_regex(
            [r'<title[^>]*>(.*?)</title>'],
            webpage, 'title')

        episode_number = int_or_none(self._search_regex(
            r' - Folge (\d+)', title, 'episode_number', default=None))

        series = self._search_regex(
            r'(.+?) - Folge', title, 'series', default=None)

        description = self._html_search_regex(
            r'(?s)<p\b[^>]+\bid=["\']clip-description[^>]+>([^<]+)<',
            webpage, 'description', fatal=False)

        releasetime = self._html_search_regex(
            r'(?s)<h6\b[^>]+\bid=["\']clip-releasetime[^>]+>(.+?)</span>',
            webpage, 'releasetime', fatal=False)

        # set correct locale for date parsing
        locale.setlocale(locale.LC_ALL, 'de_DE.UTF-8')

        upload_date = unified_strdate(datetime.datetime.strptime(
            releasetime, '%d. %B %Y %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S'))

        # Formats
        sources = self._parse_json(self._search_regex(r'(?s)MEDIA\s*=\s*(\[.+?\]);', webpage, 'media'), episode, js_to_json)

        formats = []
        for source in sources:
            furl = source.get('src')
            if not furl:
                continue
            furl = self._proto_relative_url(furl)
            ext = determine_ext(furl) or mimetype2ext(source.get('type'))
            if ext == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    furl, episode, 'mp4', 'm3u8_native',
                    m3u8_id='hls', fatal=False))
            else:
                formats.append({
                    'url': furl,
                    'format_id': determine_ext(furl),
                })

        for (durl, format_id, width, height, filesize) in re.findall(r'''(?x)
                                   <a[^>]+?href="(?P<url>(?:https:)?//[^"]+)".*?
                                   <strong>(?P<format_id>.+?)</strong>.*?
                                   <small>(?:(?P<width>\d+)x(?P<height>\d+))?\s+?\((?P<filesize>[\d,]+\s*[GM]iB)\)</small>
                                ''', webpage):
            formats.append({
                'url': durl,
                'format_id': format_id,
                'width': int_or_none(width),
                'height': int_or_none(height),
                'filesize': parse_filesize(filesize),
                'vcodec': 'none' if format_id.startswith('Audio') else None,
            })

        self._sort_formats(formats, ('width', 'height', 'filesize', 'tbr'))

        return {
            'id': episode,
            'title': title,
            'formats': formats,
            'thumbnail': thumbnail,
            'upload_date': upload_date,
            'description': description,
            'series': series,
            'episode_number': episode_number,
        }
