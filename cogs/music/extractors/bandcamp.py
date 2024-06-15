from .abc import *
from .utils import mark_not_supported
from discord import Embed

from dataclasses import dataclass
import re

from typing import AsyncIterable, override, Self, NamedTuple

__all__ = (
    "BandcampSource",
    "BandcampAlbum",
    "Bandcamp"
)


class Album(NamedTuple):
    name: str
    artist: Uploader


@dataclass(slots=True)
class BandcampSource(Source):
    album: Album = None

    @override
    async def refresh_source(self) -> None:
        info = await Bandcamp().extract_info(self.webpage_url)

        if info["album"]:
            self.title = info["track"]
            self.webpage_url = info["webpage_url"]
            self.source_url = info["url"]
            self.duration = info["duration"]
            self.description = ""
            self.uploader = Uploader(info["artist"], "")
            self.thumbnail_url = info["thumbnail"]
            self.album = Album(
                info["album"],
                Uploader(info["album_artist"], info["uploader_url"])
            )
        else:
            self.title = info["track"]
            self.webpage_url = info["webpage_url"]
            self.source_url = info["url"]
            self.duration = info["duration"]
            self.description = ""
            self.uploader = Uploader(info["artist"], info["uploader_url"])
            self.thumbnail_url = info["thumbnail"]

    @classmethod
    def from_info(cls, info: dict) -> Self:
        if info["album"]:
            return cls(
                title=info["track"],
                webpage_url=info["webpage_url"],
                source_url=info["url"],
                duration=info["duration"],
                description="",
                uploader=Uploader(info["artist"], ""),
                thumbnail_url=info["thumbnail"],
                album=Album(
                    info["album"],
                    Uploader(info["album_artist"], info["uploader_url"])
                )
            )
        return cls(
            title=info["track"],
            webpage_url=info["webpage_url"],
            source_url=info["url"],
            duration=info["duration"],
            description="",
            uploader=Uploader(info["artist"], info["uploader_url"]),
            thumbnail_url=info["thumbnail"]
        )

    @classmethod
    def from_flat_info(cls, info: dict) -> Self:
        """
        Info dict structure
        {
            "ie_key": "Bandcamp",
            "id": "<track_id>",
            "title": "<track title>",
            "_type": "url",
            "url": "<webpage_url>",
            "__x_forwarded_for_ip": null
        }
        """
        return cls(
            title=info["title"],
            webpage_url=info["webpage_url"]
        )

    @override
    @property
    def on_added_embed(self) -> Embed:
        embed = Embed(title='Song added', description=f'[{self.title}]({self.webpage_url})', color=Bandcamp.COLOR)
        embed.set_thumbnail(url=self.thumbnail_url)
        embed.add_field(name='Artist', value=self.uploader.name)
        embed.add_field(name='Duration', value=self.timestamp)
        if self.album is not None:
            embed.add_field(
                name='From',
                value=f"{self.album.name} by"
                      f"[{self.album.artist.name}]({self.album.artist.webpage_url}")
        return embed


class BandcampAlbum(Playlist):
    async def init_metadata(self):
        """Take album data from first track for the attributes.

        BandcampAlbum extractor doesn't provide with album metadata. Requires
        scraping the track for the album metadata
        """
        source: BandcampSource = self[0]
        await source.refresh_source()
        self.uploader = source.album.artist
        self.thumbnail_url = source.thumbnail_url

    @classmethod
    def from_info(cls, info: dict) -> Self:
        """
        Info dict structure
        {
            "_type": "playlist",
            "uploader_id": "<characters>",
            "id": "<album_id>",
            "title": "<album_title>",
            "entries": [<tracks flat info, see :meth:`BandcampSource.from_flat_info`>],
            "webpage_url": "<webpage_url>",
            "original_url": "<webpage_url>",
            "webpage_url_basename": "<webpage_url_basename>",
            "webpage_url_domain": "<webpage_url_domain>",
            "extractor": "Bandcamp:album",
            "extractor_key: "BandcampAlbum",
            "release_year": null?,
            "playlist_count": "<number_of_tracks>",
            "epoch": "<time_of_extraction_in_epoch>"
        }
        """
        return cls(
            (BandcampSource.from_flat_info(info) for info in info["entries"]),
            title=info["title"],
            webpage_url=info["webpage_url"]
        )

    @override
    @property
    def on_added_embed(self) -> Embed:
        embed = Embed(title='Album Added', description=f'[{self.title}]({self.webpage_url})', color=Bandcamp.COLOR)
        if self.thumbnail_url:
            embed.set_thumbnail(url=self.thumbnail_url)
        if self.uploader:
            embed.add_field(name='Artist / Label', value=f"[{self.uploader.name}]({self.uploader.webpage_url})")
        embed.add_field(name='Enqueued', value=f'{len(self)} songs')
        return embed


class Bandcamp(Extractor):
    COLOR = 0x629aa9

    REGEX = re.compile(r'(?:https?://)?[\w-]+\.bandcamp\.com/(?:track|album|releases)')

    def __str__(self):
        return 'Bandcamp'

    @mark_not_supported
    @override
    async def search(self, query: str, *, number_of_results: int = 10) -> AsyncIterable[BandcampSource]:
        ...

    @override
    async def process_query(self, query: str) -> BandcampSource | BandcampAlbum:
        info = await self.extract_info(query)

        match info:
            case {"_type": "url"}:  # for urls that ends with /releases
                return await self.process_query(info["url"])
            case {"_type": "playlist"}:
                album = BandcampAlbum.from_info(info)
                await album.init_metadata()
                return album
            case _:  # track does not have _type
                return BandcampSource.from_info(info)
