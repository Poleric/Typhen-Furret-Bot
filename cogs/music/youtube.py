from cogs.music.base_source import Song, Playlist, SearchResult

from typing import AsyncIterable
from dataclasses import dataclass
from datetime import timedelta
from youtube_dl import YoutubeDL
import asyncio
import re

from discord import Embed

class Youtube:
    @dataclass(slots=True)
    class YoutubeSong(Song):
        uploader: str
        thumbnail_url: str

        def __init__(self, requester, **kwargs):
            self.title = kwargs.get('title')
            self.webpage_url = kwargs.get('webpage_url')
            self.source_url = kwargs.get('url')
            self.uploader = kwargs.get('uploader')
            self.thumbnail_url = kwargs.get('thumbnails')[0]['url']
            self.duration = timedelta(seconds=kwargs.get('duration'))
            self.requester = requester

        def refresh_source(self):
            ydl_options = {
                'quiet': True,

                'format': 'bestaudio/best',
                'forceurl': True,
                'socket_timeout': 5,
                'source_address': '0.0.0.0',
                'postprocessor_args': ['-threads', '1']
            }

            with YoutubeDL(ydl_options) as ydl:
                self.source_url = ydl.extract_info(self.webpage_url, download=False)['url']

        @property
        def embed(self) -> Embed:
            embed = Embed(title='Song added', description=f'[{self.title}]({self.webpage_url})', color=0x33c9a4)
            embed.set_thumbnail(url=self.thumbnail_url)
            embed.add_field(name='Channel', value=self.uploader)
            embed.add_field(name='Duration', value=str(self.duration))
            return embed

    @dataclass(slots=True)
    class YoutubePlaylist(Playlist):
        uploader: str

        def __init__(self, **kwargs):
            self.title = kwargs.get('title')
            self.webpage_url = kwargs.get('webpage_url')
            self.uploader = kwargs.get('uploader')
            self.songs_url = tuple(f'https://youtu.be/{entry["url"]}' for entry in kwargs.get('entries'))

        @property
        def embed(self) -> Embed:
            embed = Embed(title='Playlist Added', description=f'[{self.title}]({self.webpage_url})', color=0x33c9a4)
            embed.add_field(name='Enqueued', value=f'{len(self.songs_url)} songs')
            return embed

    @dataclass(slots=True)
    class YoutubeSearchResult(SearchResult):
        uploader: str

        def __init__(self, **kwargs):
            self.title = kwargs.get('title')
            self.webpage_url = f'https://youtu.be/{kwargs.get("url")}'
            self.uploader = kwargs.get('uploader')
            self.duration = timedelta(seconds=kwargs.get('duration'))

    YT_REGEX = re.compile(r'((?:https?:)?//)?((?:www|m)\.)?(youtube\.com|youtu.be)(/(?:[\w\-]+\?v=|embed/|v/)?)([\w\-]+)(\S+)')  # youtube urls, include embeds, and link copy
    VIDEO_REGEX = re.compile(r'https?://www.youtube.com/watch\?v=[^&\s]+')  # youtube VIDEO url, usually copied from address bar
    PLAYLIST_REGEX = re.compile(r'https?://(?:www\.)?youtube.com/.+list=[^&]+')  # youtube PLAYLIST url

    async def get_video(self, query_or_url: str, requester) -> YoutubeSong:
        ydl_options = {
            'quiet': True,

            'format': 'bestaudio/best',
            'socket_timeout': 5,
            'source_address': '0.0.0.0',
            'postprocessor_args': ['-threads', '1']
        }

        with YoutubeDL(ydl_options) as ydl:
            loop = asyncio.get_event_loop()
            if not self.YT_REGEX.match(query_or_url):  # need to search yt
                data = await loop.run_in_executor(None, lambda: ydl.extract_info(f'ytsearch:{query_or_url}', download=False))
                return self.YoutubeSong(**data['entries'][0], requester=requester)
            else:
                data = await loop.run_in_executor(None, lambda: ydl.extract_info(query_or_url, download=False))
                return self.YoutubeSong(**data, requester=requester)

    async def get_playlist(self, url) -> YoutubePlaylist:
        if not self.PLAYLIST_REGEX.match(url):
            raise ValueError(f'{url} is not a playlist url')

        ydl_options = {
            'quiet': True,

            'extract_flat': True,
            'socket_timeout': 5,
            'source_address': '0.0.0.0',
            'postprocessor_args': ['-threads', '1']
        }

        with YoutubeDL(ydl_options) as ydl:
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ydl.extract_info(f'{url}', download=False))
        return self.YoutubePlaylist(**data)

    async def process_query(self, query: str | YoutubeSearchResult, requester) -> YoutubeSong | YoutubePlaylist:
        if isinstance(query, self.YoutubeSearchResult):
            query = query.webpage_url

        if self.PLAYLIST_REGEX.match(query):
            return await self.get_playlist(query)
        else:
            return await self.get_video(query, requester)

    async def search(self, query: str, results=10) -> AsyncIterable[YoutubeSearchResult]:
        ydl_options = {
            'quiet': True,

            'extract_flat': True,
            'socket_timeout': 5,
            'source_address': '0.0.0.0',
            'postprocessor_args': ['-threads', '1']
        }

        with YoutubeDL(ydl_options) as ydl:
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ydl.extract_info(f'ytsearch{results}:{query}', download=False))

        for video in data['entries']:
            yield self.YoutubeSearchResult(**video)
