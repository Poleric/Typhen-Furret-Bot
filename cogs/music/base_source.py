from dataclasses import dataclass
from datetime import timedelta
from youtube_dl import YoutubeDL
import re


def clean_timestamp(timestamp: str, milisecond: bool) -> str:
    days, hours, minutes, seconds, miliseconds = re.match(r'(?:(\d+) days?, )?(\d+):(\d+):(\d+)(?:.(\d+))?', timestamp).groups('')
    if days:  # if timedelta string > 24 hours, return original string
        return timestamp

    clean = ''
    if not hours == '0':
        clean += f'{hours}:'
    clean += f'{minutes}:{seconds}'
    if milisecond:
        clean += f'.{miliseconds}'
    return clean


def timestamp(time: timedelta, milisecond: bool = False):
    return clean_timestamp(str(time), milisecond=milisecond)


class BaseExtractor:
    quiet: bool = True  # change to False for debugging
    timeout: int = 60  # timeout for 1 minutes, youtube-dl defaults to 10 min
    cookie_path = r''

    @property
    def ydl_options(self) -> dict:
        options = {
            'quiet': self.quiet,

            'format': 'bestaudio/best',
            'socket_timeout': self.timeout,
            'source_address': '0.0.0.0',
            'postprocessor_args': ['-threads', '1']
        }
        if self.cookie_path:
            options['cookiefile'] = self.cookie_path

        return options


@dataclass(slots=True)
class BaseSong:
    title: str
    source_url: str
    webpage_url: str
    uploader: str
    thumbnail_url: str
    duration: timedelta
    requester: str

    def __str__(self):
        return self.title

    def refresh_source(self):
        """Refreshes the source url. Usually called in cases of Error 403 Access Forbidden"""
        ydl_options = {
            'quiet': True,

            'format': 'bestaudio/best',
            'forceurl': True,
            'socket_timeout': 10,
            'source_address': '0.0.0.0',
            'postprocessor_args': ['-threads', '1']
        }

        with YoutubeDL(ydl_options) as ydl:
            self.source_url = ydl.extract_info(self.webpage_url, download=False)['url']


@dataclass(slots=True)
class BasePlaylist:  # urls container
    title: str
    webpage_url: str
    songs_url: tuple[str]

    def __str__(self):
        return self.title

    def __len__(self):
        return len(self.songs_url)


@dataclass(slots=True)
class BaseResult:
    title: str
    webpage_url: str
    duration: timedelta
