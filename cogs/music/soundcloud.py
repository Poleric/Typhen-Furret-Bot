from cogs.music.base_source import BaseExtractor, BaseSong, BasePlaylist, timestamp

from youtube_dl import YoutubeDL
from dataclasses import dataclass
from datetime import timedelta
# from typing import AsyncIterable
import asyncio
import re

from discord import Embed


class SoundCloud(BaseExtractor):
    COLOR = 0xFE5000

    @dataclass(slots=True)
    class SoundCloudSong(BaseSong):
        def __init__(self, **kwargs):
            self.title = kwargs.get('title')
            self.source_url = kwargs.get('url')
            self.webpage_url = kwargs.get('webpage_url')
            self.uploader = kwargs.get('uploader')
            self.thumbnail_url = kwargs.get('thumbnails')[-1]['url']
            self.duration = timedelta(seconds=kwargs.get('duration'))
            self.requester = kwargs.get('requester', '')

        @property
        def embed(self) -> Embed:
            embed = Embed(title='Song added', description=f'[{self.title}]({self.webpage_url})', color=SoundCloud.COLOR)
            embed.set_thumbnail(url=self.thumbnail_url)
            embed.add_field(name='Artist', value=self.uploader)
            embed.add_field(name='Duration', value=timestamp(self.duration))
            return embed

    @dataclass(slots=True)
    class SoundCloudPlaylist(BasePlaylist):
        def __init__(self, **kwargs):
            self.title = kwargs.get('title')
            self.webpage_url = kwargs.get('webpage_url')
            self.songs_url = tuple(f'{entry["url"]}' for entry in kwargs.get('entries'))

        @property
        def embed(self) -> Embed:
            embed = Embed(title='Playlist Added', description=f'[{self.title}]({self.webpage_url})', color=SoundCloud.COLOR)
            embed.add_field(name='Enqueued', value=f'{len(self.songs_url)} songs')
            return embed

    REGEX = re.compile(r'(?:https?://)?(?:www|api.+\.)?(?:soundcloud\.com|snd\.sc).+')
    PLAYLIST_REGEX = re.compile(r'(?:https?://)?soundcloud\.com/[a-z0-9-_]+/sets/.+')

    def __str__(self):
        return 'SoundCloud'

    async def _get_song(self, query_or_url) -> SoundCloudSong:
        ydl_options = self.ydl_options

        with YoutubeDL(ydl_options) as ydl:
            loop = asyncio.get_event_loop()
            if not self.REGEX.match(query_or_url):  # need to search sc
                data = await loop.run_in_executor(None, lambda: ydl.extract_info(f'scsearch:{query_or_url}', download=False))
                data = data['entries'][0]
            else:
                data = await loop.run_in_executor(None, lambda: ydl.extract_info(query_or_url, download=False))
        return self.SoundCloudSong(**data)

    async def _get_playlist(self, url) -> SoundCloudPlaylist:
        if not self.PLAYLIST_REGEX.match(url):
            raise TypeError(f'{url} is not a SoundCloud playlist url')

        ydl_options = self.ydl_options
        ydl_options['extract_flat'] = True

        with YoutubeDL(ydl_options) as ydl:
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
        return self.SoundCloudPlaylist(**data)

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
            return await self._get_playlist(query)
        else:
            song = await self._get_song(query)
            song.requester = requester
            return song
