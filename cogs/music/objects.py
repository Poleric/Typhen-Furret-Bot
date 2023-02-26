from dataclasses import dataclass
from datetime import timedelta
from yt_dlp import YoutubeDL
import re

ydl_options = {
    'quiet': True,

    'format': 'bestaudio/best',
    'socket_timeout': 10,
    'source_address': '0.0.0.0',
    'postprocessor_args': ['-threads', '1']
}


def strip_timestamp(timestamp: str | timedelta, keep_milliseconds=False) -> str:
    """Strip away hh from hh:mm:ss, if h is 0"""
    # strip 0 hour
    stripped = re.sub(r"(?<! |\d)0:(?=\d+:\d+)", "", str(timestamp))

    # strip milliseconds
    if not keep_milliseconds:
        stripped = re.sub(r"\.\d+", "", stripped)

    return stripped


class Extractor:
    cookie_path = r''

    @property
    def ydl_options(self) -> dict:
        options = ydl_options.copy()
        if self.cookie_path:
            options['cookiefile'] = self.cookie_path

        return options

    def extract_info(self, query, *, ydl_options=None):
        ydl_options = ydl_options or self.ydl_options
        with YoutubeDL(ydl_options) as ydl:
            data = ydl.extract_info(query, download=False)
        return data


@dataclass(slots=True)
class PartialSource:
    """Bare minimum to represent a song"""

    title: str
    webpage_url: str
    duration: int
    uploader: str

    requester: str

    def __str__(self):
        return self.title

    @property
    def timestamp(self) -> str:
        return strip_timestamp(timedelta(seconds=self.duration))

    def convert_source(self):
        """Calls source conversion function and returns it."""
        raise NotImplemented


@dataclass(slots=True)
class Song(PartialSource):
    """A source with url to stream from, and other information."""

    source_url: str
    thumbnail_url: str

    def refresh_source(self):
        """Refreshes the source url. Usually called in cases of Error 403 Access Forbidden"""

        with YoutubeDL(ydl_options) as ydl:
            self.source_url = ydl.extract_info(self.webpage_url, download=False)['url']


@dataclass(slots=True)
class Playlist:  # BaseSource container
    title: str
    webpage_url: str
    uploader: str
    sources: tuple[PartialSource, ...]

    def __str__(self):
        return self.title

    def __iter__(self):
        return iter(self.sources)

    def set_requester(self, requester):
        """Sets the requester for all the base source inside"""
        for source in self.sources:
            source.requester = requester
