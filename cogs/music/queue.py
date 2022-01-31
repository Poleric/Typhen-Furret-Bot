from cogs.music.base_source import BaseSong, timestamp

from enum import Enum, auto
from collections import deque
from datetime import timedelta
import math
import random
import logging

from discord import Embed, PCMVolumeTransformer, FFmpegPCMAudio


class LoopType(Enum):
    NO_LOOP = auto()
    LOOP_QUEUE = auto()
    LOOP_SONG = auto()


class Queue:
    class NotConnectedToVoice(Exception):
        pass

    class PageError(Exception):
        pass

    ffmpeg_options = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }

    def __init__(self, voice_client):
        self.voice_client = voice_client

        self._songs: deque[BaseSong] = deque()
        self.playing = None

        # Player settings
        self._volume = 100
        self._loop: LoopType = LoopType.NO_LOOP

    @property
    def duration(self) -> timedelta:
        """Return the a timedelta of the total duration of all the songs in the queue"""

        return sum((song.duration for song in self._songs), timedelta())

    @property
    def max_page(self):
        return math.ceil(len(self._songs) / 10) or 1

    @property
    def volume(self) -> int:
        return self._volume

    @volume.setter
    def volume(self, volume: int):
        self._volume = volume
        if self.voice_client.source:
            self.voice_client.source.volume = volume / 100

    @property
    def loop(self) -> LoopType:
        return self._loop

    @loop.setter
    def loop(self, mode):
        if isinstance(mode, LoopType):
            self._loop = mode

    def __len__(self):
        return len(self._songs)

    def __iter__(self):
        yield from self._songs

    def __getitem__(self, key: int) -> BaseSong:
        return self._songs[key-1]

    def add(self, song: BaseSong) -> None:
        """Append Song into the queue"""

        self._songs.append(song)

    def add_top(self, song: BaseSong) -> None:
        """Append left Song into the queue"""

        self._songs.appendleft(song)

    def pop(self, index: int) -> BaseSong:
        """
        Pop a song from the specific index in the queue
        Return Song
        """

        if index > len(self._songs) - 1:
            raise IndexError('The song does not exist lmao')
        self._songs.rotate(-index)
        popped = self._songs.popleft()
        self._songs.rotate(index)
        return popped

    def move(self, starting_index, ending_index):
        """
        Move song from starting index to ending index
        Return moved Song
        """

        if starting_index > len(self._songs):
            raise IndexError('The song does not exist lmao')
        self._songs.rotate(1-starting_index)
        popped = self._songs.popleft()
        self._songs.rotate(starting_index-ending_index)
        self._songs.appendleft(popped)
        self._songs.rotate(ending_index-1)

    def shuffle(self) -> None:
        """Shuffle queue"""

        random.shuffle(self._songs)

    def clear(self) -> None:
        """Clear queue"""

        self._songs.clear()

    def play(self) -> None:
        """Start or resume playing from the queue"""
        if self.voice_client is None or not self.voice_client.is_connected():  # Check if theres a voice client in the first place
            raise self.NotConnectedToVoice()

        def make_audio_source():
            source = FFmpegPCMAudio(source=self.playing.source_url, **Queue.ffmpeg_options)
            if not source.read():
                source = make_audio_source()
            return source

        if not self.playing:
            self.playing = self._songs.popleft()
            self.voice_client.play(PCMVolumeTransformer(original=make_audio_source(), volume=self._volume / 100),
                                   after=self.play_next)

    def play_next(self, error):
        if error:
            logging.error(f'PLAYER ERROR: {error}')

        match self.loop:
            case LoopType.LOOP_QUEUE:
                self._songs.append(self.playing)
            case LoopType.LOOP_SONG:
                self._songs.appendleft(self.playing)
        self.playing = None
        if self._songs:
            self.play()

    def skip(self):
        """Skip and current playing song"""
        self.voice_client.stop()

    def stop(self):
        """Stop playing and cleanup"""
        self.clear()
        self.skip()

    def embed(self, page: int = 1) -> Embed:
        # Error checking
        if page < 1 or page > self.max_page:
            raise self.PageError('Page does not exist')
        embed = Embed(title='Queue', color=0x25fa30)
        # Shows playing song, only when first "page" of the embed
        if page == 1:
            if self.playing:  # Check if theres a playing song
                embed.add_field(name='__Now Playing__',
                                value=f'[{self.playing.title}]({self.playing.webpage_url}) | `{timestamp(self.playing.duration)}` | `Requested by {self.playing.requester}`',
                                inline=False)
            else:  # No playing song
                embed.add_field(name='__Now Playing__',
                                value='Nothing, try requesting a few songs',
                                inline=False)
                return embed
        # range of 0 | 10 | 20... to 9 | 19 | 29
        for i in range(10 * (page - 1), 10 * page - 1):
            try:
                if i == 0 or i % 10 == 0:  # Check if its the n0th of elements
                    embed.add_field(name='__Enqueued__',
                                    value=f'`{i+1}.` [{self._songs[i].title}]({self._songs[i].webpage_url}) | `{timestamp(self._songs[i].duration)}` | `Requested by {self._songs[i].requester}`',
                                    inline=False)
                else:  # Normal song display field
                    embed.add_field(name='\u200b',
                                    value=f'`{i+1}.` [{self._songs[i].title}]({self._songs[i].webpage_url}) | `{timestamp(self._songs[i].duration)}` | `Requested by {self._songs[i].requester}`',
                                    inline=False)
            except IndexError:
                break
        match self.loop:
            case LoopType.LOOP_QUEUE:
                loop = 'Looping: queue'
            case LoopType.LOOP_SONG:
                loop = 'Looping: song'
            case _:
                loop = 'No loop'
        embed.set_footer(text=f'Page {page}/{self.max_page} | {loop} | Duration: {timestamp(self.duration)}')
        return embed
