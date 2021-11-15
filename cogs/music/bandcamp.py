from cogs.music.base_source import BaseExtractor, BaseSong, BasePlaylist, timestamp

from dataclasses import dataclass
from datetime import timedelta
import re
from youtube_dl import YoutubeDL
import asyncio

from discord import Embed


class Bandcamp(BaseExtractor):
    COLOR = 0x629aa9

    @dataclass(slots=True)
    class BandcampSong(BaseSong):
        album: str

        def __init__(self, **kwargs):
            self.title = kwargs.get('title')
            self.webpage_url = kwargs.get('webpage_url')
            self.source_url = kwargs.get('url')
            self.uploader = kwargs.get('artist')
            self.thumbnail_url = kwargs.get('thumbnail')
            self.duration = timedelta(seconds=kwargs.get('duration'))
            self.album = kwargs.get('album')
            self.requester = kwargs.get('requester', '')

        @property
        def embed(self) -> Embed:
            embed = Embed(title='Song added', description=f'[{self.title}]({self.webpage_url})', color=Bandcamp.COLOR)
            embed.set_thumbnail(url=self.thumbnail_url)
            embed.add_field(name='Artist', value=self.uploader)
            embed.add_field(name='Duration', value=timestamp(self.duration))
            if self.album:
                embed.add_field(name='From album', value=self.album)
            return embed

    @dataclass(slots=True)
    class BandcampAlbum(BasePlaylist):
        uploader: str

        def __init__(self, **kwargs):
            self.title = kwargs.get('title')
            self.webpage_url = kwargs.get('webpage_url')
            self.uploader = kwargs.get('uploader_id')
            self.songs_url = tuple(f'{entry["url"]}' for entry in kwargs.get('entries'))

        @property
        def embed(self) -> Embed:
            embed = Embed(title='Album Added', description=f'[{self.title}]({self.webpage_url})', color=Bandcamp.COLOR)
            embed.add_field(name='Artist / Label', value=self.uploader)
            embed.add_field(name='Enqueued', value=f'{len(self.songs_url)} songs')
            return embed

    REGEX = re.compile(r'(?:https?://)?[\w-]+\.bandcamp\.com.+')
    TRACK_REGEX = re.compile(r'(?:https?://)?[\w-]+\.bandcamp\.com/track/.+')
    ALBUM_REGEX = re.compile(r'(?:https?://)?[\w-]+\.bandcamp\.com/album/.+')

    def __str__(self):
        return 'Bandcamp'

    async def _get_song(self, url: str) -> BandcampSong:
        if not self.TRACK_REGEX.match(url):
            raise TypeError(f'{url} is not a Bandcamp url')

        ydl_options = self.ydl_options

        with YoutubeDL(ydl_options) as ydl:
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
        return self.BandcampSong(**data)

    async def _get_playlist(self, url) -> BandcampAlbum:
        if not self.ALBUM_REGEX.match(url):
            raise TypeError(f'{url} is not a Bandcamp album url')

        ydl_options = self.ydl_options
        ydl_options['extract_flat'] = True

        with YoutubeDL(ydl_options) as ydl:
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
        return self.BandcampAlbum(**data)

    async def process_query(self, url: str, requester) -> BandcampSong | BandcampAlbum:
        if self.ALBUM_REGEX.match(url):
            return await self._get_playlist(url)
        else:
            song = await self._get_song(url)
            song.requester = requester
            return song
