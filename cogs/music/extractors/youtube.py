from .abc import *
from discord import Embed
from .utils import strip_seconds, timestamp

from dataclasses import dataclass
import re

from typing import AsyncIterable, override, Self


__all__ = (
    "YoutubeSource",
    "YouTubePlaylist",
    "Youtube"
)

@dataclass(slots=True)
class YoutubeSource(Source):
    is_live: bool = False

    @override
    @property
    def timestamp(self) -> str:
        if self.is_live:
            return 'LIVE'
        else:
            return timestamp(*strip_seconds(self.duration))

    @override
    async def refresh_source(self) -> None:
        info = await Youtube().extract_info(self.webpage_url)

        self.title = info["title"]
        self.webpage_url = info["webpage_url"]
        self.source_url = info["url"]
        self.duration = info["duration"]
        self.description = info["description"]
        self.uploader = Uploader(info["uploader"], info["uploader_url"])
        self.thumbnail_url = info["thumbnail"]
        self.is_live = info["is_live"]

    @classmethod
    def from_info(cls, info: dict) -> Self:
        return cls(
            title=info["title"],
            webpage_url=info["webpage_url"],
            source_url=info["url"],
            duration=info["duration"],
            description=info["description"],
            uploader=Uploader(info["uploader"], info["uploader_url"]),
            thumbnail_url=info["thumbnail"],
            is_live=info["is_live"]
        )

    @classmethod
    def from_flat_info(cls, info: dict) -> Self:
        return cls(
            title=info["title"],
            webpage_url=info["url"],
            duration=info["duration"],
            uploader=Uploader(info["uploader"], info["uploader_url"]),
            thumbnail_url=info["thumbnails"][-1]["url"]
        )

    @override
    @property
    def on_added_embed(self) -> Embed:
        embed = Embed(title='Song added', description=f'[{self.title}]({self.webpage_url})', color=Youtube.COLOR)
        embed.set_thumbnail(url=self.thumbnail_url)
        embed.add_field(name='Channel', value=f"[{self.uploader.name}]({self.uploader.webpage_url})")
        embed.add_field(name='Duration', value=self.timestamp)
        return embed


class YouTubePlaylist(Playlist):
    @classmethod
    def from_info(cls, info: dict) -> Self:
        return cls(
            (YoutubeSource.from_flat_info(info) for info in info["entries"]),
            title=info["title"],
            webpage_url=info["webpage_url"],
            description=info["description"],
            uploader=Uploader(info["uploader"], info["uploader_url"]),
            thumbnail_url=info["thumbnails"][-1]["url"]
        )

    @override
    @property
    def on_added_embed(self) -> Embed:
        embed = Embed(title='Playlist Added', description=f'[{self.title}]({self.webpage_url})', color=Youtube.COLOR)
        if self.thumbnail_url:
            embed.set_thumbnail(url=self.thumbnail_url)
        if self.uploader:
            embed.add_field(name='Channel', value=f"[{self.uploader.name}]({self.uploader.webpage_url})")
        embed.add_field(name='Enqueued', value=f'{len(self)} songs')
        return embed


class Youtube(Extractor):
    COLOR = 0xFF0000  # red

    REGEX = re.compile(
        r'((?:https?:)?//)?((?:www|m)\.)?(youtube\.com|youtu.be)(/(?:[\w\-]+\?v=|embed/|v/)?)([\w\-]+)(\S+)')
        # youtube urls, include embeds, and link copy

    def __init__(self, *args, ignore_shorts: bool = False, **kwargs):
        # does not fill back the rejected entries
        # if ignore_shorts:
        #     self.ydl_options["match_filter"] = self.ignore_short
        super().__init__(*args, **kwargs)

    def __str__(self):
        return 'YouTube'

    @staticmethod
    def ignore_short(info_dict: dict, *, incomplete: bool):
        if "/shorts/" in info_dict["url"]:
            return f"{info_dict["url"]} is a shorts. Ignoring shorts."

    @override
    async def search(self, query: str, *, number_of_results: int = 10) -> AsyncIterable[YoutubeSource]:
        number_of_results = await self.extract_info(f"ytsearch{number_of_results}:{query}")

        for info in number_of_results['entries']:
            yield YoutubeSource.from_flat_info(info)

    @override
    async def process_query(self, query: str) -> YoutubeSource | YouTubePlaylist:
        if not self.REGEX.match(query):
            # use search
            async for source in self.search(query, number_of_results=1):
                await source.refresh_source()
                return source

        info = await self.extract_info(query)

        match info:
            case {"_type": "video"}:
                return YoutubeSource.from_info(info)
            case {"_type": "playlist"}:
                return YouTubePlaylist.from_info(info)
            case _:
                # shorts does not have _type
                if self.ignore_short(info, incomplete=False):
                    return YoutubeSource.from_info(info)
                ...
