from functools import wraps
from typing import override, Callable, Self
import math
import asyncio
import itertools

from discord import VoiceClient, Embed, User

from .queue import MusicQueue
from .audio import TempoVolumeControlsPCMAudio, create_source
from .errors import Forbidden
from .loop_mode import LoopMode
from .extractors.abc import Source, Playlist
from .extractors.utils import strip_seconds, timestamp

MS_PER_PACKET = 20


class MusicClient(MusicQueue, VoiceClient):
    source: TempoVolumeControlsPCMAudio
    playing: Source
    _volume: float
    _speed: float

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._time_ms: float = 0

    @property
    def elapsed_seconds(self) -> float:
        return self._time_ms / 1000

    @override
    def set_volume(self, volume: float) -> None:
        if self.source is not None:
            self.source.volume = volume

    @override
    def set_speed(self, speed: float) -> None:
        if self.source is not None:
            self.source.tempo = speed

    @staticmethod
    def ensure_playing[T, **P](func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapper(self: Self, *args: P.args, **kwargs: P.kwargs) -> T:
            ret: T = func(self, *args, **kwargs)
            if not self.is_playing() and not self.is_paused():
                self.end_playing(None)
            return ret

        return wrapper

    @override
    def send_audio_packet(self, data: bytes, *, encode: bool = True) -> None:
        self._time_ms += self.source.tempo * MS_PER_PACKET
        super().send_audio_packet(data, encode=encode)

    @override
    def start_playing(self, *, seek: float = 0) -> None:
        self._time_ms = seek * 1000

        loop = asyncio.get_event_loop()
        if self.playing.is_partial:
            loop.run_until_complete(self.playing.refresh_source())

        for _ in range(3):
            try:
                source = create_source(self.playing.source_url, seek_seconds=seek, tempo=self.speed, volume=self.volume)
            except Forbidden:
                loop.run_until_complete(self.playing.refresh_source())
            else:
                self.play(source, after=self.end_playing)
                return

        # stop trying to play song
        self.skip()

    @override
    def end_playing(self, exc: Exception | None) -> None:  # noqa
        if not exc:
            self.load_next_song()
            self.start_playing()
            return
        else:
            match exc:
                case Forbidden():
                    self.start_playing(seek=self.elapsed_seconds)
                case _:
                    ...

    @override
    @ensure_playing
    def add(self, source: Source | Playlist, requester: User) -> None:
        super().add(source, requester)

    @override
    @ensure_playing
    def add_left(self, source: Source | Playlist, requester: User) -> None:
        super().add_left(source, requester)

    @override
    def seek(self, seek: float) -> None:
        self.start_playing(seek=seek)

    @property
    def max_page(self) -> int:
        return math.ceil(len(self.queue) / 10) or 1

    def embed(self, page) -> Embed:
        if page < 1 or page > self.max_page:
            raise IndexError(f"Page specified '{page}' does not exists. Max page available is '{self.max_page}'")

        embed = Embed(title="Queue", color=0x25fa30)
        if page == 1:
            if self.playing:  # Check if there's a playing song
                embed.add_field(
                    name="__Now Playing__",
                    value=f"[{self.playing.title}]({self.playing.webpage_url}) | `{self.playing.timestamp}`"
                          f" | `Requested by {self.playing.requester}`",  # noqa
                    inline=False)
            else:  # No playing song
                embed.add_field(
                    name="__Now Playing__",
                    value="Nothing, try requesting a few songs",
                    inline=False)
                return embed

            # Bottom part (The queued songs)
        for i, song in enumerate(
                itertools.islice(self.queue, 10 * (page - 1), 10 * page),  # self[0:10] // self[10:20] // self[10(n-1):10n]
                start=1
        ):
            header = "\u200b"
            if i == 1:  # Check if it's the first element
                header = "__Enqueued__"  # changes the top title

            embed.add_field(
                name=header,
                value=f"`{10 * (page - 1) + i}.` [{song.title}]({song.webpage_url}) | `{song.timestamp}`"
                      f" | `Requested by {song.requester}`",  # noqa
                inline=False)

        match self.loop:
            case LoopMode.LOOP_QUEUE:
                loop = "Looping: Queue :repeat:"
            case LoopMode.LOOP_SONG:
                loop = "Looping: Song :repeat_one:"
            case _:
                loop = "No loop"
        embed.set_footer(
            text=f"Page {page}/{self.max_page}"
                 f" | {loop}"
                 f" | Duration: {timestamp(*strip_seconds(self.total_duration))}"
            )

        return embed
