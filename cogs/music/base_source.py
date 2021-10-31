from dataclasses import dataclass
from datetime import timedelta


@dataclass(slots=True)
class Song:
    title: str
    source_url: str
    webpage_url: str
    duration: timedelta
    requester: str

    def __str__(self):
        return self.title


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
