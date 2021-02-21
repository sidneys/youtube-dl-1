# coding: utf-8
from __future__ import unicode_literals

import itertools
import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    orderedSet,
    unified_strdate,
    urlencode_postdata,
)


class BitChuteIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?bitchute\.com/(?:video|embed|torrent/[^/]+)/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://www.bitchute.com/video/szoMrox2JEI/',
        'md5': '66c4a70e6bfc40dcb6be3eb1d74939eb',
        'info_dict': {
            'id': 'szoMrox2JEI',
            'ext': 'mp4',
            'title': 'Fuck bitches get money',
            'description': 'md5:3f21f6fb5b1d17c3dee9cf6b5fe60b3a',
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader': 'Victoria X Rave',
            'upload_date': '20170813',
        },
    }, {
        'url': 'https://www.bitchute.com/embed/lbb5G1hjPhw/',
        'only_matching': True,
    }, {
        'url': 'https://www.bitchute.com/torrent/Zee5BE49045h/szoMrox2JEI.webtorrent',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(
            'https://www.bitchute.com/video/%s' % video_id, video_id, headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.57 Safari/537.36',
            })

        ERRORS = {
            r'<h1 class="page-title text-center">404 - Page not found</h1>':
            'Video %s does not exist.',

            r'<h1 class="page-title">Unavailable Content</h1>':
            'Video %s is unavailable as the contents have been deemed potentially illegal within your country by the BitChute moderation team.',
        }

        for error_re, error_msg in ERRORS.items():
            if re.search(error_re, webpage):
                raise ExtractorError(error_msg % video_id, expected=True)

        title = self._html_search_regex(
            (r'<[^>]+\bid=["\']video-title[^>]+>([^<]+)', r'<title>([^<]+)'),
            webpage, 'title', default=None) or self._html_search_meta(
            'description', webpage, 'title',
            default=None) or self._og_search_description(webpage)

        format_urls = []
        for mobj in re.finditer(
                r'addWebSeed\s*\(\s*(["\'])(?P<url>(?:(?!\1).)+)\1', webpage):
            format_urls.append(mobj.group('url'))
        format_urls.extend(re.findall(r'as=(https?://[^&"\']+)', webpage))

        formats = [
            {'url': format_url}
            for format_url in orderedSet(format_urls)]

        if not formats:
            formats = self._parse_html5_media_entries(
                url, webpage, video_id)[0]['formats']

        for f in formats:
            f['format'] = 'MPEG4 container, H.264, AAC LC'
            f['format_id'] = 'H264-AAC'
            f['protocol'] = 'https'
            f['http_headers'] = {
                'Referer': url
            }

        self._check_formats(formats, video_id)
        self._sort_formats(formats)

        description = self._html_search_regex(
            r'(?s)<div\b[^>]+\bclass=["\']full hidden[^>]+>(.+?)</div>',
            webpage, 'description', fatal=False)
        thumbnail = self._og_search_thumbnail(
            webpage, default=None) or self._html_search_meta(
            'twitter:image:src', webpage, 'thumbnail')
        uploader = self._html_search_regex(
            (r'(?s)<div class=["\']channel-banner.*?<p\b[^>]+\bclass=["\']name[^>]+>(.+?)</p>',
             r'(?s)<p\b[^>]+\bclass=["\']video-author[^>]+>(.+?)</p>'),
            webpage, 'uploader', fatal=False)

        upload_date = unified_strdate(self._search_regex(
            r'class=["\']video-publish-date[^>]+>[^<]+ at \d+:\d+ UTC on (.+?)\.',
            webpage, 'upload date', fatal=False))

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'uploader': uploader,
            'upload_date': upload_date,
            'formats': formats,
        }


class BitChuteChannelIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?bitchute\.com/channel/(?P<id>[^/?#&]+)'
    _TEST = {
        'url': 'https://www.bitchute.com/channel/victoriaxrave/',
        'playlist_mincount': 185,
        'info_dict': {
            'id': 'victoriaxrave',
        },
    }

    _TOKEN = 'zyG6tQcGPE5swyAEFLqKUwMuMMuF6IO2DZ6ZDQjGfsL0e4dcTLwqkTTul05Jdve7'

    def _entries(self, channel_id):
        channel_url = 'https://www.bitchute.com/channel/%s/' % channel_id
        offset = 0
        for page_num in itertools.count(1):
            data = self._download_json(
                '%sextend/' % channel_url, channel_id,
                'Downloading channel page %d' % page_num,
                data=urlencode_postdata({
                    'csrfmiddlewaretoken': self._TOKEN,
                    'name': '',
                    'offset': offset,
                }), headers={
                    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                    'Referer': channel_url,
                    'X-Requested-With': 'XMLHttpRequest',
                    'Cookie': 'csrftoken=%s' % self._TOKEN,
                })
            if data.get('success') is False:
                break
            html = data.get('html')
            if not html:
                break
            if re.search(r'<h1 class="page-title">Blocked Content</h1>', webpage):
                raise ExtractorError('Channel %s has been blocked for breaching the BitChute Community Guidelines.' % channel_id, expected=True)
            video_ids = re.findall(
                r'class=["\']channel-videos-image-container[^>]+>\s*<a\b[^>]+\bhref=["\']/video/([^"\'/]+)',
                html)
            if not video_ids:
                break
            offset += len(video_ids)
            for video_id in video_ids:
                yield self.url_result(
                    'https://www.bitchute.com/video/%s' % video_id,
                    ie=BitChuteIE.ie_key(), video_id=video_id)

    def _real_extract(self, url):
        channel_id = self._match_id(url)
        return self.playlist_result(
            self._entries(channel_id), playlist_id=channel_id)


class BitChutePlaylistIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?bitchute\.com/playlist/(?P<id>[^/?#&]+)'
    _TEST = {
        'url': 'https://www.bitchute.com/playlist/g4WTfWTdYEQa/',
        'playlist_mincount': 1,
        'info_dict': {
            'id': 'g4WTfWTdYEQa',
            'title': 'Podcasts',
            'description': 'Podcast Playlist',
        },
    }
    _PAGE_SIZE = 25

    _TOKEN = 'zyG6tQcGPE5swyAEFLqKUwMuMMuF6IO2DZ6ZDQjGfsL0e4dcTLwqkTTul05Jdve7'

    def _entries(self, playlist_id):
        playlist_url = 'https://www.bitchute.com/playlist/%s' % playlist_id
        video_index = 0
        for pagechunk_number in itertools.count(start=1, step=1):
            data = self._download_json(
                url_or_request='%s/extend/' % playlist_url,
                video_id=playlist_id,
                note='Downloading playlist page chunk: %d' % pagechunk_number,
                data=urlencode_postdata({
                    'csrfmiddlewaretoken': self._TOKEN,
                    'offset': video_index,
                }),
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                    'Referer': playlist_url,
                    'X-Requested-With': 'XMLHttpRequest',
                    'Cookie': 'csrftoken=%s' % self._TOKEN,
                })
            if data.get('success') is False:
                break
            html = data.get('html')
            if not html:
                break
            video_ids = re.findall(
                r'class=["\']image-container[^>]+>\s*<a\b[^>]+\bhref=["\']/video/([^"\'/]+)',
                html)
            if not video_ids:
                break

            # Remember video offset pointer
            video_index += len(video_ids)

            for video_id in video_ids:
                yield self.url_result(
                    'https://www.bitchute.com/video/%s' % video_id,
                    ie=BitChuteIE.ie_key(),
                    video_id=video_id)

            # Exit iterator if this is last page chunk
            if len(video_ids) < self._PAGE_SIZE:
                break

    def _real_extract(self, url):
        playlist_id = self._match_id(url)

        webpage = self._download_webpage(
            'https://www.bitchute.com/playlist/%s' % playlist_id, playlist_id, headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.57 Safari/537.36',
            })

        playlist_title = self._html_search_regex(
            (r'<[^>]+\bid=["\']playlist-title[^>]+>([^<]+)', r'<title>([^<]+)'),
            webpage, 'title', default=None) or self._html_search_meta(
            'description', webpage, 'title',
            default=None) or self._og_search_description(webpage)

        playlist_description = self._html_search_regex(
            r'(?s)<div class=["\']description.*?[^>]+>(.*?)</p>',
            webpage, 'description', fatal=False)

        return self.playlist_result(
            self._entries(playlist_id), playlist_id=playlist_id, playlist_title=playlist_title, playlist_description=playlist_description)
