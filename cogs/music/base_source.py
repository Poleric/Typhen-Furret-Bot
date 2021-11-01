from dataclasses import dataclass
from datetime import timedelta
import re


def clean_timestamp(timestamp: str, milisecond: bool) -> str:
    hours, minutes, seconds, miliseconds = re.match(r'(\d+):(\d+):(\d+)(?:.(\d+))?', timestamp).groups('')
    clean = ''
    if not hours == '0':
        clean += f'{hours}:'
    clean += f'{minutes}:{seconds}'
    if milisecond:
        clean += f'.{miliseconds}'
    return clean


def timestamp(time: timedelta, milisecond: bool = False):
    return clean_timestamp(str(time), milisecond=milisecond)


@dataclass(slots=True)
class Song:
    title: str
    source_url: str
    webpage_url: str
    duration: timedelta
    requester: str

    def __str__(self):
        return self.title

    def refresh_source(self):
        """Refreshes the source url. Usually called in cases of Error 403 Access Forbidden"""
        pass


@dataclass(slots=True)
class Playlist:  # urls container
    title: str
    webpage_url: str
    songs_url: tuple[str]

    def __str__(self):
        return self.title

    def __len__(self):
        return len(self.songs_url)


@dataclass(slots=True)
class SearchResult:
    title: str
    webpage_url: str
    duration: timedelta
