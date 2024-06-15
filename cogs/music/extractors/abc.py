import re
import asyncio
import functools
from discord import Embed, User
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterable, Self, NamedTuple
from .utils import timestamp, strip_seconds

from yt_dlp import YoutubeDL

__all__ = (
    "Uploader",
    "Source",
    "Playlist",
    "Extractor"
)


MISSING = object()


class Uploader(NamedTuple):
    name: str
    webpage_url: str


@dataclass(slots=True)
class Source(ABC):
    title: str
    webpage_url: str

    source_url: str = MISSING
    duration: float = MISSING

    description: str = MISSING
    uploader: Uploader = MISSING
    thumbnail_url: str = MISSING

    requester: User = MISSING

    def __str__(self):
        return self.title

    @property
    def timestamp(self) -> str:
        return timestamp(*strip_seconds(self.duration))

    @property
    def is_partial(self) -> bool:
        return self.source_url is MISSING

    @abstractmethod
    async def refresh_source(self) -> None:
        raise NotImplementedError

    @property
    @abstractmethod
    def on_added_embed(self) -> Embed:
        raise NotImplementedError

    @property
    # @abstractmethod
    def info_embed(self) -> Embed:
        raise NotImplementedError


class Playlist[T](tuple, ABC):
    title: str
    webpage_url: str

    description: str
    uploader: Uploader
    thumbnail_url: str

    def __new__(
            cls,
            *args,
            title: str,
            webpage_url: str,
            description: str = "",
            uploader: Uploader = None,
            thumbnail_url: str = "",
            **kwargs):
        self: tuple[T] = super().__new__(*args, **kwargs)
        self.title = title
        self.webpage_url = webpage_url
        self.description = description
        self.uploader = uploader
        self.thumbnail_url = thumbnail_url
        return self

    def __str__(self):
        return self.title

    @property
    @abstractmethod
    def on_added_embed(self) -> Embed:
        raise NotImplementedError

    # @abstractmethod
    @property
    def info_embed(self) -> Embed:
        raise NotImplementedError


class Extractor(ABC):
    ydl_options = {
        "quiet": True,
        "format": "bestaudio/best",
        "extract_flat": True,

        "socket_timeout": 10
    }
    __instance: Self = None

    REGEX: re.Pattern

    # singleton
    def __new__(cls, *args, **kwargs):
        if not isinstance(cls.__instance, cls):
            cls.__instance = super().__new__(cls, *args, **kwargs)
        return cls.__instance

    def __init__(self, *, ydl_options: dict = None, n_threads: int = 1):
        if ydl_options:
            self.ydl_options.update(ydl_options)
        self.ydl_options["postprocessor_args"] = ["-threads", n_threads]

        self.yt_dlp = YoutubeDL(self.ydl_options)

    def close(self) -> None:
        self.yt_dlp.close()

    async def extract_info(self, query: str, *, ie_key: str = None):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            functools.partial(
                self.yt_dlp.extract_info,
                url=query,
                ie_key=ie_key,
                download=False
            )
        )

    @abstractmethod
    async def process_query(self, query: str) -> Source | Playlist:
        raise NotImplementedError

    @abstractmethod
    async def search(self, query: str, *, number_of_results: int = 10) -> AsyncIterable[Source]:
        raise NotImplementedError
