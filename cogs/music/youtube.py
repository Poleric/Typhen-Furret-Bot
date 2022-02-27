from cogs.music.base_source import BaseExtractor, BaseSong, BasePlaylist, BaseResult, timestamp

from youtube_dl import YoutubeDL
from dataclasses import dataclass
from datetime import timedelta
from typing import AsyncIterable
import asyncio
import re

from discord import Embed


class YouTube(BaseExtractor):
    cookie_path = r'./cogs/music/youtube_cookies.txt'
    COLOR = 0xFF0000

    @dataclass(slots=True)
    class YouTubeSong(BaseSong):
        is_live: bool

        def __init__(self, **kwargs):
            self.title = kwargs.get('title')
            self.webpage_url = kwargs.get('webpage_url')
            self.source_url = kwargs.get('url')
            self.uploader = kwargs.get('uploader')
            self.thumbnail_url = kwargs.get('thumbnails')[-1]['url']
            self.duration = timedelta(seconds=kwargs.get('duration'))
            self.requester = kwargs.get('requester', '')
            self.is_live = kwargs.get('is_live', False)

        @property
        def embed(self) -> Embed:
            embed = Embed(title='Song added', description=f'[{self.title}]({self.webpage_url})', color=YouTube.COLOR)
            embed.set_thumbnail(url=self.thumbnail_url)
            embed.add_field(name='Channel', value=self.uploader)
            embed.add_field(name='Duration', value=self.timestamp)
            return embed

        @property
        def timestamp(self) -> str:
            if self.is_live:
                return 'LIVE'
            else:
                return timestamp(self.duration)

    @dataclass(slots=True)
    class YouTubePlaylist(BasePlaylist):
        uploader: str

        def __init__(self, **kwargs):
            self.title = kwargs.get('title')
            self.webpage_url = kwargs.get('webpage_url')
            self.uploader = kwargs.get('uploader')
            self.songs_url = tuple(f'https://youtu.be/{entry["url"]}' for entry in kwargs.get('entries'))

        @property
        def embed(self) -> Embed:
            embed = Embed(title='Playlist Added', description=f'[{self.title}]({self.webpage_url})', color=YouTube.COLOR)
            if self.uploader:
                embed.add_field(name='Channel', value=self.uploader)
            embed.add_field(name='Enqueued', value=f'{len(self.songs_url)} songs')
            return embed

    @dataclass(slots=True)
    class YouTubeResult(BaseResult):
        uploader: str
        is_live: bool

        def __init__(self, **kwargs):
            self.title = kwargs.get('title')
            self.webpage_url = f'https://youtu.be/{kwargs.get("url")}'
            self.uploader = kwargs.get('uploader')
            if kwargs.get('duration'):  # if duration is not null or None, None only pops up if the video is live
                self.duration = timedelta(seconds=kwargs.get('duration'))
                self.is_live = False
            else:
                self.duration = timedelta(seconds=0)
                self.is_live = True

        @property
        def timestamp(self) -> str:
            if self.is_live:
                return 'LIVE'
            else:
                return timestamp(self.duration)

    REGEX = re.compile(r'((?:https?:)?//)?((?:www|m)\.)?(youtube\.com|youtu.be)(/(?:[\w\-]+\?v=|embed/|v/)?)([\w\-]+)(\S+)')  # youtube urls, include embeds, and link copy
    VIDEO_REGEX = re.compile(r'https?://www.youtube.com/watch\?v=[^&\s]+')  # youtube VIDEO url, usually copied from address bar
    PLAYLIST_REGEX = re.compile(r'https?://(?:www\.)?youtube.com/.+list=[^&]+')  # youtube PLAYLIST url

    def __str__(self):
        return 'YouTube'

    async def _get_song(self, query_or_url: str) -> YouTubeSong:
        ydl_options = self.ydl_options

        with YoutubeDL(ydl_options) as ydl:
            loop = asyncio.get_event_loop()
            if not self.REGEX.match(query_or_url):  # need to search yt
                data = await loop.run_in_executor(None, lambda: ydl.extract_info(f'ytsearch:{query_or_url}', download=False))
                data = data['entries'][0]
            else:
                data = await loop.run_in_executor(None, lambda: ydl.extract_info(query_or_url, download=False))
        return self.YouTubeSong(**data)

    async def _get_playlist(self, url) -> YouTubePlaylist:
        if not self.PLAYLIST_REGEX.match(url):
            raise TypeError(f'{url} is not a YouTube playlist url')

        ydl_options = self.ydl_options
        ydl_options['extract_flat'] = True

        with YoutubeDL(ydl_options) as ydl:
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
        return self.YouTubePlaylist(**data)

    async def search(self, query: str, results=10) -> AsyncIterable[YouTubeResult]:
        ydl_options = self.ydl_options
        ydl_options['extract_flat'] = True

        with YoutubeDL(ydl_options) as ydl:
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ydl.extract_info(f'ytsearch{results}:{query}', download=False))

        for video in data['entries']:
            yield self.YouTubeResult(**video)

    async def process_query(self, query: str, requester) -> YouTubeSong | YouTubePlaylist:
        if self.PLAYLIST_REGEX.match(query):
            return await self._get_playlist(query)
        else:
            song = await self._get_song(query)
            song.requester = requester
            return song
