from __future__ import unicode_literals

import re
import locale
import datetime

from .common import InfoExtractor
from ..utils import (
    clean_html,
    determine_ext,
    ExtractorError,
    int_or_none,
    js_to_json,
    mimetype2ext,
    try_get,
    unified_strdate,
)

from youtube_dl.utils import (
    parse_resolution,
    write_string,
)

class MassengeschmackTVIE(InfoExtractor):
    IE_NAME = 'massengeschmack.tv'
    _VALID_URL = r'https?://(?:www\.)?massengeschmack\.tv/play/(?P<id>[^?&#]+)'

    _TEST = {
        'url': 'https://massengeschmack.tv/play/fktv202',
        'md5': '95fbe64de62c05181af3e7c67b08dd9a',
        'info_dict': {
            'id': 'fktv202',
            'ext': 'mp4',
            'title': 'Fernsehkritik-TV - Folge 202',
            'thumbnail': r're:^https?://.*\.jpg$',
            'upload_date': '20170318',
            'description': 'md5:7e711f67d9e7157189adf9173d401db6',
            'series': 'Fernsehkritik-TV',
            'episode_number': 202,
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        # errorhandling
        ERRORS = {
            r'<form id="register-form" action="/register':
            'Login required to access %s.',
        }

        for error_re, error_msg in ERRORS.items():
            if re.search(error_re, webpage):
                raise ExtractorError(error_msg % video_id, expected=True)

        # metadata lookup
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

        # provide de_DE locale for parsing of timestamp
        locale.setlocale(locale.LC_ALL, 'de_DE.UTF-8')

        upload_date = unified_strdate(datetime.datetime.strptime(
            releasetime, '%d. %B %Y %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S'))

        # format (for streaming) lookup: webpage 
        sources = self._parse_json(self._search_regex(r'(?s)MEDIA\s*=\s*(\[.+?\]);', webpage, 'media'), video_id, js_to_json)

        formats = []
        for source in sources:
            furl = source.get('src')
            if not furl:
                continue
            furl = self._proto_relative_url(furl)
            ext = determine_ext(furl) or mimetype2ext(source.get('type'))
            if ext == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    furl, video_id, 'mp4', 'm3u8_native',
                    m3u8_id='hls', fatal=False))
            else:
                formats.append({
                    'url': furl,
                    'format_id': determine_ext(furl),
                })

        # format (for download) lookup: API

        downloads = self._download_json(
            'https://massengeschmack.tv/api/v2/downloads/%s' % video_id,
            video_id,
            note='Fetching download-optimized formats via API',
            errnote='Unable to query API',
            fatal=False,
            headers={'content-type': 'application/json'})

        files = try_get(downloads, lambda x: x['files'], list) or []

        for file in files:
            file_url = self._proto_relative_url(file.get('url'))
            if not file_url:
                continue
            file_ext = determine_ext(file_url)
            file_type = file.get('t')
            file_size = file.get('size')
            file_desc = file.get('desc')
            format_id_list = file_desc.lower().split()

            if file_type == 'film':
                file_dimensions = file.get('dimensions')
                resolution = parse_resolution(file_dimensions)
                width = int_or_none(resolution.get('width'))
                height =  int_or_none(resolution.get('height')) or int_or_none(file_desc)
                vcodec = None
                format_id = ''.join(format_id_list)

            if file_type == 'music':
                vcodec = 'none'
                format_id = '-'.join(format_id_list)

            formats.append({
                'format_id': 'http-' + format_id,
                'format_note': file_desc,
                'url': file_url,
                'ext': file_ext,
                'filesize': file_size,
                'width': width,
                'height': height,
                'vcodec': vcodec,
            })

        self._sort_formats(formats, ('width', 'height', 'filesize', 'tbr'))

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'thumbnail': thumbnail,
            'upload_date': upload_date,
            'description': description,
            'series': series,
            'episode_number': episode_number,
        }
