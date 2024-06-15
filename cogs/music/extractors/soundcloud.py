from .abc import *
from .utils import mark_not_supported
from discord import Embed

from dataclasses import dataclass
import re

from typing import AsyncIterable, override, Self


__all__ = (
    "SoundcloudSource",
    "SoundcloudPlaylist",
    "Soundcloud"
)


@dataclass(slots=True)
class SoundcloudSource(Source):
    @override
    async def refresh_source(self) -> None:
        info = await Soundcloud().extract_info(self.webpage_url)

        self.title = info["title"]
        self.webpage_url = info["webpage_url"]
        self.source_url = info["url"]
        self.duration = info["duration"]
        self.description = info["description"]
        self.uploader = Uploader(info["uploader"], info["uploader_url"])
        self.thumbnail_url = info["thumbnails"][-1]["url"]

    @classmethod
    def from_info(cls, info: dict) -> Self:
        return cls(
            title=info["title"],
            webpage_url=info["webpage_url"],
            source_url=info["url"],
            duration=info["duration"],
            description=info["description"],
            uploader=Uploader(info["uploader"], info["uploader_url"]),
            thumbnail_url=info["thumbnails"][-1]["url"]
        )

    @classmethod
    def from_flat_info(cls, info: dict) -> Self:
        """
        Info dict structure
        {
            "ie_key": "Soundcloud",
            "id": "<track_id>",
            "_type": "url",
            "url": "<webpage_url>",
            "__x_forwarded_for_ip": null
        }
        """
        return cls(
            title=info["url"].rsplit("/")[-1],
            webpage_url=info["url"]
        )

    @override
    @property
    def on_added_embed(self) -> Embed:
        embed = Embed(title='Song added', description=f'[{self.title}]({self.webpage_url})', color=Soundcloud.COLOR)
        embed.set_thumbnail(url=self.thumbnail_url)
        embed.add_field(name='Artist', value=self.uploader)
        embed.add_field(name='Duration', value=self.timestamp)
        return embed


class SoundcloudPlaylist(Playlist):
    async def init_metadata(self):
        """Take album data from first track for the attributes.

        Scrape the first track of the playlist to populate playlist metadata.
        """
        source: SoundcloudSource = self[0]
        await source.refresh_source()
        self.thumbnail_url = source.thumbnail_url

    @classmethod
    def from_info(cls, info: dict) -> Self:
        """
        Info dict structure
        {
            "id": "<playlist_id>",
            "title": "<playlist_title>",
            "_type": "playlist",
            "entries": [<song flat info, see :meth:`SoundcloudSource.from_flat_info`>],
            "webpage_url": "<webpage_url>",
            "original_url": "<webpage_url>",
            "webpage_url_basename": "<webpage_url_basename>",
            "webpage_url_domain": "<webpage_url_domain>",
            "extractor": "soundcloud:album",
            "extractor_key: "SoundcloudSet",
            "release_year": null,
            "playlist_count": "<number_of_songs>",
            "epoch": "<time_of_extraction_in_epoch>"
        }
        """
        return cls(
            (SoundcloudSource.from_flat_info(info) for info in info["entries"]),
            title=info["title"],
            webpage_url=info["webpage_url"]
        )

    @property
    def on_added_embed(self) -> Embed:
        embed = Embed(title='Playlist Added', description=f'[{self.title}]({self.webpage_url})', color=Soundcloud.COLOR)
        if self.thumbnail_url:
            embed.set_thumbnail(url=self.thumbnail_url)
        embed.add_field(name='Enqueued', value=f'{len(self)} songs')
        return embed


class Soundcloud(Extractor):
    COLOR = 0xFE5000

    REGEX = re.compile(r'(?:https?://)?(?:www|api.+\.)?(?:soundcloud\.com|snd\.sc).+')

    def __str__(self):
        return 'SoundCloud'

    @mark_not_supported
    @override
    async def search(self, query: str, *, number_of_results: int = 10) -> AsyncIterable[Source]:
        ...

    @override
    async def process_query(self, query: str) -> SoundcloudSource | SoundcloudPlaylist:
        info = await self.extract_info(query)

        match info:
            case {"_type": "playlist"}:
                playlist = SoundcloudPlaylist.from_info(info)
                await playlist.init_metadata()
                return playlist
            case _:
                return SoundcloudSource.from_info(info)
