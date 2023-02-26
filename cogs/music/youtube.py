from cogs.music.objects import Extractor, Song, Playlist, PartialSource

from dataclasses import dataclass
import asyncio
import re
import functools
from discord import Embed

from typing import AsyncIterable


@dataclass(slots=True)
class YouTubeSong(Song):
    is_live: bool

    def __init__(self, **kwargs):
        self.title = kwargs.get('title')
        self.webpage_url = kwargs.get('webpage_url')
        self.source_url = kwargs.get('url')
        self.uploader = kwargs.get('uploader')
        self.thumbnail_url = kwargs.get('thumbnails')[-1]['url']
        self.duration = kwargs.get('duration')
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
            return super(YouTubeSong, self).timestamp


@dataclass(slots=True)
class YoutubePartialSource(PartialSource):
    is_live: bool

    def __init__(self, **kwargs):
        self.title = kwargs.get('title')
        self.webpage_url = f'https://youtu.be/{kwargs.get("url")}'
        self.uploader = kwargs.get('uploader')
        if kwargs.get('duration'):  # if duration is not null or None, None only pops up if the video is live
            self.duration = kwargs.get('duration')
            self.is_live = False
        else:
            self.duration = 0
            self.is_live = True
        self.requester = kwargs.get('requester', '')

    @property
    def timestamp(self) -> str:
        if self.is_live:
            return 'LIVE'
        else:
            return super(YoutubePartialSource, self).timestamp

    def convert_source(self) -> YouTubeSong:
        data = Extractor().extract_info(self.webpage_url)
        return YouTubeSong(requester=self.requester, **data)


@dataclass
class YouTubePlaylist(Playlist):
    uploader: str

    def __init__(self, **kwargs):
        self.title = kwargs.get('title')
        self.webpage_url = kwargs.get('webpage_url')
        self.uploader = kwargs.get('uploader')
        self.sources = tuple(YoutubePartialSource(**data) for data in kwargs.get("entries"))

    @property
    def embed(self) -> Embed:
        embed = Embed(title='Playlist Added', description=f'[{self.title}]({self.webpage_url})', color=YouTube.COLOR)
        if self.uploader:
            embed.add_field(name='Channel', value=self.uploader)
        embed.add_field(name='Enqueued', value=f'{len(self.sources)} songs')
        return embed


class YouTube(Extractor):
    cookie_path = r'./cogs/music/youtube_cookies.txt'
    COLOR = 0xFF0000  # red

    REGEX = re.compile(r'((?:https?:)?//)?((?:www|m)\.)?(youtube\.com|youtu.be)(/(?:[\w\-]+\?v=|embed/|v/)?)([\w\-]+)(\S+)')  # youtube urls, include embeds, and link copy
    VIDEO_REGEX = re.compile(r'https?://www.youtube.com/watch\?v=[^&\s]+')  # youtube VIDEO url, usually copied from address bar
    PLAYLIST_REGEX = re.compile(r'https?://(?:www\.)?youtube.com/.+list=[^&]+')  # youtube PLAYLIST url

    def __str__(self):
        return 'YouTube'

    async def _get_song(self, query_or_url: str) -> YouTubeSong:
        loop = asyncio.get_event_loop()
        if not self.REGEX.match(query_or_url):  # need to search yt
            data = await loop.run_in_executor(None, functools.partial(self.extract_info, query=f"ytsearch:{query_or_url}"))
            data = data['entries'][0]
        else:
            data = await loop.run_in_executor(None, functools.partial(self.extract_info, query=query_or_url))
        return YouTubeSong(**data)

    async def _get_playlist(self, url) -> YouTubePlaylist:
        if not self.PLAYLIST_REGEX.match(url):
            raise TypeError(f'{url} is not a YouTube playlist url')

        ydl_options = self.ydl_options.copy()
        ydl_options['extract_flat'] = True

        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, functools.partial(self.extract_info, query=url, ydl_options=ydl_options))
        return YouTubePlaylist(**data)

    async def search(self, query: str, results=10) -> AsyncIterable[YoutubePartialSource]:
        ydl_options = self.ydl_options.copy()
        ydl_options['extract_flat'] = True

        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, functools.partial(self.extract_info, query=f'ytsearch{results}:{query}', ydl_options=ydl_options))

        for video in data['entries']:
            yield YoutubePartialSource(**video)

    async def process_query(self, query: str, requester) -> YouTubeSong | YouTubePlaylist:
        if self.PLAYLIST_REGEX.match(query):
            playlist = await self._get_playlist(query)
            playlist.set_requester(requester)
            return playlist
        else:
            song = await self._get_song(query)
            song.requester = requester
            return song
