from cogs.music.objects import Extractor, Song, Playlist, PartialSource

from dataclasses import dataclass
import asyncio
import re
import functools
from discord import Embed

# from typing import AsyncIterable


@dataclass(slots=True)
class SoundCloudSong(Song):
    def __init__(self, **kwargs):
        self.title = kwargs.get('title')
        self.source_url = kwargs.get('url')
        self.webpage_url = kwargs.get('webpage_url')
        self.uploader = kwargs.get('uploader')
        self.thumbnail_url = kwargs.get('thumbnails')[-1]['url']
        self.duration = kwargs.get('duration')
        self.requester = kwargs.get('requester', '')

    @property
    def embed(self) -> Embed:
        embed = Embed(title='Song added', description=f'[{self.title}]({self.webpage_url})', color=SoundCloud.COLOR)
        embed.set_thumbnail(url=self.thumbnail_url)
        embed.add_field(name='Artist', value=self.uploader)
        embed.add_field(name='Duration', value=self.timestamp)
        return embed


@dataclass(slots=True)
class SoundCloudPartialSource(PartialSource):
    def __init__(self, **kwargs):
        self.title = kwargs.get('title')
        self.webpage_url = f'https://youtu.be/{kwargs.get("url")}'
        self.uploader = kwargs.get('uploader')
        self.duration = kwargs.get('duration')
        self.requester = kwargs.get('requester', '')

    def convert_source(self) -> SoundCloudSong:
        data = Extractor().extract_info(self.webpage_url)
        return SoundCloudSong(requester=self.requester, **data)


@dataclass
class SoundCloudPlaylist(Playlist):
    def __init__(self, **kwargs):
        self.title = kwargs.get('title')
        self.webpage_url = kwargs.get('webpage_url')
        self.sources = tuple(SoundCloudPartialSource(**data) for data in kwargs.get('entries'))

    @property
    def embed(self) -> Embed:
        embed = Embed(title='Playlist Added', description=f'[{self.title}]({self.webpage_url})', color=SoundCloud.COLOR)
        embed.add_field(name='Enqueued', value=f'{len(self.sources)} songs')
        return embed


class SoundCloud(Extractor):
    COLOR = 0xFE5000

    REGEX = re.compile(r'(?:https?://)?(?:www|api.+\.)?(?:soundcloud\.com|snd\.sc).+')
    PLAYLIST_REGEX = re.compile(r'(?:https?://)?soundcloud\.com/[a-z0-9-_]+/sets/.+')

    def __str__(self):
        return 'SoundCloud'

    async def _get_song(self, query_or_url) -> SoundCloudSong:
        loop = asyncio.get_event_loop()
        if not self.REGEX.match(query_or_url):  # need to search sc
            data = await loop.run_in_executor(None, functools.partial(self.extract_info, query=f"scsearch:{query_or_url}"))
            data = data['entries'][0]
        else:
            data = await loop.run_in_executor(None, functools.partial(self.extract_info, query=query_or_url))
        return SoundCloudSong(**data)

    async def _get_playlist(self, url) -> SoundCloudPlaylist:
        if not self.PLAYLIST_REGEX.match(url):
            raise TypeError(f'{url} is not a SoundCloud playlist url')

        ydl_options = self.ydl_options.copy()
        ydl_options['extract_flat'] = True

        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, functools.partial(self.extract_info, query=url, ydl_options=ydl_options))
        return SoundCloudPlaylist(**data)

    # async def search(self, query: str, results=10) -> AsyncIterable[SoundCloudSong]:  # doesnt work, come back eventually or prob never
    #     ydl_options = {
    #         'quiet': True,
    #
    #         'extract_flat': True,
    #         'forcetitle': True,
    #         'forceduration': True,
    #         'socket_timeout': 10,
    #         'source_address': '0.0.0.0',
    #         'postprocessor_args': ['-threads', '1']
    #     }
    #
    #     with YoutubeDL(ydl_options) as ydl:
    #         loop = asyncio.get_event_loop()
    #         data = await loop.run_in_executor(None, lambda: ydl.extract_info(f'scsearch{results}:{query}', download=False))
    #     tasks = [asyncio.create_task(self._get_song(entry['url'])) for entry in data['entries']]
    #
    #     for task in tasks:
    #         yield await task

    async def process_query(self, query: str, requester) -> SoundCloudSong | SoundCloudPlaylist:
        if self.PLAYLIST_REGEX.match(query):
            playlist = await self._get_playlist(query)
            playlist.set_requester(requester)
            return playlist
        else:
            song = await self._get_song(query)
            song.requester = requester
            return song
