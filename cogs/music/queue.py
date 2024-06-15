import random
from discord import User
from abc import ABC, abstractmethod
from collections import deque

from .extractors import Source, Playlist
from .loop_mode import LoopMode

from typing import Any


class MusicQueue(ABC):
    MAX_VOLUME: float = 2.0
    MAX_SPEED: float = 2.0

    def __init__(
            self,
            *args,
            loop_mode: LoopMode = LoopMode.NO_LOOP,
            speed: float = 1.0,
            volume: float = 1.0,
            **kwargs):
        super().__init__(*args, **kwargs)
        self.queue: deque[Source] = deque()
        self.playing: Source | None = None

        self.loop_mode: LoopMode = loop_mode
        self.speed: float = speed
        self.volume: float = volume

    @staticmethod
    def add_requester_data[T](source: T, requester: User) -> T:
        source.requester = requester
        return source

    @property
    def volume(self) -> float:
        return self._volume

    @volume.setter
    def volume(self, value: float) -> None:
        value = max(value, 0.0)
        value = min(value, self.MAX_VOLUME)

        self._volume = value
        self.set_volume(value)

    @abstractmethod
    def set_volume(self, volume: float) -> None:
        raise NotImplementedError

    @property
    def speed(self) -> float:
        return self._speed

    @speed.setter
    def speed(self, value: float) -> None:
        value = max(value, 0.0)
        value = min(value, self.MAX_SPEED)

        self._speed = value
        self.set_speed(value)

    @abstractmethod
    def set_speed(self, speed: float) -> None:
        raise NotImplementedError

    @property
    def total_duration(self) -> int:
        return sum(song.duration for song in self.queue)

    @abstractmethod
    def start_playing(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def end_playing(self) -> None:
        raise NotImplementedError

    def load_next_song(self, *, force=False) -> None:
        if self.queue:
            match self.loop_mode:
                case LoopMode.NO_LOOP:
                    self.playing = self.queue.popleft()
                case LoopMode.LOOP_QUEUE:
                    self.queue.append(self.playing)
                    self.playing = self.queue.popleft()
                case LoopMode.LOOP_SONG if force:
                    self.queue.append(self.playing)
                    self.playing = self.queue.popleft()
        else:
            if self.loop_mode == LoopMode.NO_LOOP or force:
                self.playing = None

    """Player methods"""

    def add(self, source: Source | Playlist, requester: User) -> None:
        """Add song"""
        if isinstance(source, Source):
            self.add_requester_data(source, requester)
            self.queue.append(source)
        elif isinstance(source, Playlist):
            self.queue.extend(self.add_requester_data(s, requester) for s in source)

    def add_left(self, source: Source | Playlist, requester: User) -> None:
        """Add song to the front of the queue"""
        if isinstance(source, Source):
            self.add_requester_data(source, requester)
            self.queue.appendleft(source)
        elif isinstance(source, Playlist):
            # extendleft results in a reversed order
            self.queue.extendleft(self.add_requester_data(s, requester) for s in reversed(source))

    def move(self, x: int, y: int) -> Any:
        """Moves song from x to y, shifting everything right.
        Returns the moved song.
        """
        self.queue.rotate(-x)
        tmp = self.queue.popleft()
        self.queue.rotate(-y + x)
        self.queue.appendleft(tmp)
        self.queue.rotate(y)

        return tmp

    def shuffle(self) -> None:
        """Randomizes all the song in the queue"""
        random.shuffle(self.queue)

    def clear(self) -> None:
        """Clear the queue"""
        self.queue.clear()

    def skip(self) -> None:
        """Skip current playing song, even if loop is on."""
        self.load_next_song(force=True)
        self.start_playing()

    def remove(self, x: int) -> None:
        """Removes song at the specified index."""
        self.queue.remove(x)

    def clear_all(self) -> None:
        """Clear the playing and the queue"""
        self.clear()
        self.skip()

    @abstractmethod
    def seek(self, duration: int) -> None:
        """Seek to a specific time of the playing song"""
        raise NotImplementedError
