from cogs.music.objects import Song, Playlist, BaseSource, strip_timestamp
from cogs.music.timer import Timer

from enum import Enum
from datetime import timedelta
import math
import random
import logging

from discord import Embed, PCMVolumeTransformer, FFmpegPCMAudio, VoiceClient
from typing import Iterator


class NotConnected(Exception):
    pass


class LoopType(Enum):
    NO_LOOP = 1
    LOOP_QUEUE = 2
    LOOP_SONG = 3


class Queue(list):
    class PageError(Exception):
        pass

    ffmpeg_options = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }

    def __init__(self, voice_client):
        super().__init__()
        self.voice_client: VoiceClient = voice_client
        self.playing: Song | None = None

        # Player settings
        self._volume: int | float = 100
        self._loop: LoopType = LoopType.NO_LOOP
        self.timer: Timer = Timer()

    @property
    def duration(self) -> int:
        """Return the total seconds of the total duration of all the songs in the queue"""

        return sum(song.duration for song in self)

    @property
    def volume(self) -> int | float:
        return self._volume

    @volume.setter
    def volume(self, volume: int | float):
        self._volume = volume
        if self.voice_client.source:
            self.voice_client.source.volume = volume / 100

    @property
    def loop(self) -> LoopType:
        return self._loop

    @loop.setter
    def loop(self, mode: LoopType):
        if isinstance(mode, LoopType):
            self._loop = mode

    def __iter__(self) -> Iterator[Song | BaseSource]:
        return super(Queue, self).__iter__()

    def add(self, song: Song) -> None:
        """Append Song into the queue"""

        self.append(song)

    def add_playlist(self, playlist: Playlist) -> None:
        """Append playlist sources into the queue"""

        self.extend(playlist)

    def add_top(self, song: Song) -> None:
        """Append left Song into the queue"""

        self.insert(0, song)

    def move(self, initial_index: int, final_index: int) -> None:
        """Move song from one pos to another pos"""

        self.insert(final_index, self.pop(initial_index))

    def shuffle(self) -> None:
        """Shuffle queue"""

        random.shuffle(self)

    def assert_vc(self) -> None:
        try:
            assert self.voice_client  # Check if theres a voice client in the first place
            assert self.voice_client.is_connected()
        except AssertionError:
            raise NotConnected

    def play(self) -> None:
        """Start or resume playing from the queue"""
        self.assert_vc()

        def make_audio_source(song):
            source = FFmpegPCMAudio(source=song.source_url, **Queue.ffmpeg_options)
            if not source.read():  # ensure the source url is readable, for example when ffmpeg gets 403 error, it will refresh the source url and read from that again
                song.refresh_source()
                source = make_audio_source(song)
            return source

        if not self.playing:
            self.playing = self.pop(0)
            if isinstance(self.playing, BaseSource):
                self.playing = self.playing.convert_source()

            self.voice_client.play(PCMVolumeTransformer(original=make_audio_source(self.playing), volume=self._volume / 100),
                                   after=self.play_next)
            self.timer.reset()

    def play_next(self, error):
        if error:
            logging.error(f'PLAYER ERROR: {error}')

        if self.playing:
            # Set self.playing as None, adding back self.playing into queue according to the loop mode
            match self.loop:
                case LoopType.LOOP_QUEUE:
                    self.add(self.playing)
                case LoopType.LOOP_SONG:
                    self.add_top(self.playing)
            self.playing = None

        if self:
            self.play()

    def skip(self):
        """Skip and current playing song"""
        # add playing back to the last in the queue if anykind of looping
        match self.loop:
            case LoopType.LOOP_QUEUE | LoopType.LOOP_SONG:
                self.append(self.playing)
        self.playing = None

        self.voice_client.stop()

    def pause(self):
        """Pause the playing and timer"""
        self.assert_vc()

        if not self.voice_client.is_paused():
            self.voice_client.pause()
            self.timer.pause()

    def resume(self):
        """Resume playing"""
        self.assert_vc()

        if self.voice_client.is_paused():
            self.voice_client.resume()
            self.timer.resume()

    @property
    def max_page(self):
        return math.ceil(len(self) / 10) or 1

    def embed(self, page: int = 1) -> Embed:
        # Error checking
        if page < 1 or page > self.max_page:
            raise self.PageError('Page does not exist')
        embed = Embed(title='Queue', color=0x25fa30)
        # Top part (shows playing song)
        if page == 1:
            if self.playing:  # Check if theres a playing song
                embed.add_field(name='__Now Playing__',
                                value=f'[{self.playing.title}]({self.playing.webpage_url}) | `{self.playing.timestamp}` | `Requested by {self.playing.requester}`',
                                inline=False)
            else:  # No playing song
                embed.add_field(name='__Now Playing__',
                                value='Nothing, try requesting a few songs',
                                inline=False)
                return embed

        # Bottom part (The queued songs)
        for i, song in enumerate(self[10*(page-1):10*page], start=1):  # self[0:10] // self[10:20] // self[10(n-1):10n]
            header = "\u200b"
            if i == 1:  # Check if its the first element
                header = "__Enqueued__"  # changes the top title

            embed.add_field(name=header,
                            value=f"`{10 * (page - 1) + i}.` [{song.title}]({song.webpage_url}) | `{song.timestamp}` | `Requested by {song.requester}`",
                            inline=False)

        match self.loop:
            case LoopType.LOOP_QUEUE:
                loop = 'Looping: Queue'
            case LoopType.LOOP_SONG:
                loop = 'Looping: Song'
            case _:
                loop = 'No loop'
        embed.set_footer(text=f'Page {page}/{self.max_page} | {loop} | Duration: {strip_timestamp(timedelta(seconds=self.duration))}')
        return embed
