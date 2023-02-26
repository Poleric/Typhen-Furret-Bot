from cogs.music.objects import Extractor, Song, Playlist, PartialSource

from dataclasses import dataclass
import asyncio
import re
import functools
from discord import Embed


@dataclass(slots=True)
class BandcampSong(Song):
    album: str

    def __init__(self, **kwargs):
        self.title = kwargs.get('title')
        self.webpage_url = kwargs.get('webpage_url')
        self.source_url = kwargs.get('url')
        self.uploader = kwargs.get('artist')
        self.thumbnail_url = kwargs.get('thumbnail')
        self.duration = kwargs.get('duration')
        self.album = kwargs.get('album')
        self.requester = kwargs.get('requester', '')

    @property
    def embed(self) -> Embed:
        embed = Embed(title='Song added', description=f'[{self.title}]({self.webpage_url})', color=Bandcamp.COLOR)
        embed.set_thumbnail(url=self.thumbnail_url)
        embed.add_field(name='Artist', value=self.uploader)
        embed.add_field(name='Duration', value=self.timestamp)
        if self.album:
            embed.add_field(name='From album', value=self.album)
        return embed


@dataclass(slots=True)
class BandcampPartialSource(PartialSource):
    def __init__(self, **kwargs):
        self.title = kwargs.get('title')
        self.webpage_url = f'https://youtu.be/{kwargs.get("url")}'
        self.uploader = kwargs.get('uploader')
        self.duration = kwargs.get('duration')
        self.requester = kwargs.get('requester', '')

    def convert_source(self) -> BandcampSong:
        data = Extractor().extract_info(self.webpage_url)
        return BandcampSong(requester=self.requester, **data)


@dataclass
class BandcampAlbum(Playlist):
    def __init__(self, **kwargs):
        self.title = kwargs.get('title')
        self.webpage_url = kwargs.get('webpage_url')
        self.uploader = kwargs.get('uploader_id')
        self.sources = tuple(BandcampPartialSource(**data) for data in kwargs.get('entries'))

    @property
    def embed(self) -> Embed:
        embed = Embed(title='Album Added', description=f'[{self.title}]({self.webpage_url})', color=Bandcamp.COLOR)
        embed.add_field(name='Artist / Label', value=self.uploader)
        embed.add_field(name='Enqueued', value=f'{len(self.sources)} songs')
        return embed


class Bandcamp(Extractor):
    COLOR = 0x629aa9

    REGEX = re.compile(r'(?:https?://)?[\w-]+\.bandcamp\.com.+')
    TRACK_REGEX = re.compile(r'(?:https?://)?[\w-]+\.bandcamp\.com/track/.+')
    ALBUM_REGEX = re.compile(r'(?:https?://)?[\w-]+\.bandcamp\.com/(?:album/.+|releases)')

    def __str__(self):
        return 'Bandcamp'

    async def _get_song(self, url: str) -> BandcampSong:
        if not self.TRACK_REGEX.match(url):
            raise TypeError(f'{url} is not a Bandcamp url')

        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, functools.partial(self.extract_info, query=url))
        return BandcampSong(**data)

    async def _get_playlist(self, url) -> BandcampAlbum:
        if not self.ALBUM_REGEX.match(url):
            raise TypeError(f'{url} is not a Bandcamp album url')

        ydl_options = self.ydl_options.copy()
        ydl_options['extract_flat'] = True

        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, functools.partial(self.extract_info, query=url, ydl_options=ydl_options))
        return BandcampAlbum(**data)

    async def process_query(self, url: str, requester) -> BandcampSong | BandcampAlbum:
        if self.ALBUM_REGEX.match(url):
            playlist = await self._get_playlist(url)
            playlist.set_requester(requester)
            return playlist
        else:
            song = await self._get_song(url)
            song.requester = requester
            return song
