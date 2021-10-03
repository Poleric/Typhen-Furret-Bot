# import json
import typing

import youtube_dl
import re
import math
import asyncio
from datetime import timedelta, datetime
from dataclasses import dataclass
from collections import deque
import random
from enum import Enum

from discord import User, Member, VoiceChannel, VoiceClient, PCMVolumeTransformer, FFmpegPCMAudio, Embed
from discord.ext import commands
from discord.ext.commands.errors import MissingRequiredArgument


@dataclass()
class Song:
    title: str
    source_url: str
    webpage_url: str
    uploader: str
    thumbnail_url: str
    duration: timedelta
    requester: str | User | Member

    def __str__(self):
        return self.title

    @classmethod
    def from_data(cls, data, requester):
        return cls(data['title'], data['url'], data['webpage_url'], data['uploader'],
                   data['thumbnails'][0]['url'], timedelta(seconds=data['duration']), requester)


@dataclass()
class Playlist:
    title: str
    songs: list[Song]
    webpage_url: str
    uploader: str
    requester: str | User | Member

    def __str__(self):
        return self.title

    def __iter__(self):
        return self.songs

    def __getitem__(self, item):
        return self.songs[item]

    @classmethod
    def from_data(cls, data, requester):
        return cls(data['title'], [Song.from_data(song_data, requester) for song_data in data['entries']],
                   data['webpage_url'], data['uploader'], requester)


async def search(query: str, requester, *, number_of_results: int = None, loop=None) -> Song | Playlist | list[Song] | None:
    youtube_dl.utils.bug_reports_message = lambda: ''
    ydl_options = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True
    }
    ydl = youtube_dl.YoutubeDL(ydl_options)

    loop = loop or asyncio.get_event_loop()
    # direct search from url
    if re.match(r'https?://.*youtu.*/playlist\?list=.*', query):  # yt playlist url pattern
        data = await loop.run_in_executor(None, lambda: ydl.extract_info(query, download=False))
        return Playlist.from_data(data, requester)
    elif re.match(r'https?://.*youtu.*/.*', query):  # yt video url pattern
        data = await loop.run_in_executor(None, lambda: ydl.extract_info(query, download=False))
        return Song.from_data(data, requester)

    # non url query
    else:
        # search from query
        results = await loop.run_in_executor(None, lambda: ydl.extract_info(f'ytsearch{number_of_results or 1}:{query}', download=False))
        if results['entries']:
            if not number_of_results:
                return Song.from_data(results['entries'][0], requester)
            else:
                return [Song.from_data(data, requester) for data in results['entries']]
        else:
            return


class LoopType(Enum):
    NO_LOOP = "Looping: off"
    LOOP_QUEUE = "Looping: queue"
    LOOP_SONG = "Looping: song"


@dataclass()
class Queue:
    class NotConnectedToVoice(Exception):
        pass

    class PageError(Exception):
        pass

    _songs: deque[Song] = deque()
    voice_client: VoiceClient = None
    # Queue options
    _playing: Song = None
    _volume: int = 100  # 1 - 100
    loop: LoopType = LoopType.NO_LOOP

    ffmpeg_options = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }

    @property
    def duration(self) -> timedelta:
        """Return the a timedelta of the total duration of all the songs in the queue"""

        return sum((song.duration for song in self._songs), timedelta())

    @property
    def max_page(self):
        return math.ceil(len(self._songs) / 10) or 1

    def get_volume(self) -> int:
        return self._volume

    def set_volume(self, volume: int) -> None:
        self._volume = volume
        if self.voice_client.source:
            self.voice_client.source.volume = volume / 100

    volume = property(get_volume, set_volume)

    def __len__(self):
        return len(self._songs)

    def __iter__(self):
        yield from self._songs

    def __getitem__(self, key: int) -> Song:
        return self._songs[key]

    def __str__(self):
        return str(self._songs)

    def loop_mode(self, mode: LoopType):
        if isinstance(mode, LoopType):
            self.loop = mode
            return self.loop

    def add(self, song: Song) -> None:
        """Append Song into the queue"""

        self._songs.append(song)

    def add_left(self, song: Song) -> None:
        """Append left Song into the queue"""

        self._songs.appendleft(song)

    def pop(self, index: int) -> Song:
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
        if starting_index > len(self._songs) - 1:
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

        if self.voice_client is None:  # Check if theres a voice client in the first place
            raise self.NotConnectedToVoice('No VoiceClient found')
        self._playing = self._songs.popleft()
        self.voice_client.play(
            PCMVolumeTransformer(FFmpegPCMAudio(self._playing.source_url, **self.ffmpeg_options), self._volume / 100),
            after=self.play_next)

    def play_next(self, error):
        if error:
            print(f'{datetime.now}: {error=}\n')
        match self.loop:
            case LoopType.LOOP_QUEUE:
                self._songs.append(self._playing)
            case LoopType.LOOP_SONG:
                self._songs.appendleft(self._playing)
        if self._songs:
            self.play()

    def skip(self):
        """Skip and return current playing song"""
        self.voice_client.stop()
        return self._playing

    def embed(self, page: int = 1) -> Embed:
        # Error checking
        if page < 1 or page > self.max_page:
            raise self.PageError('Page does not exist')
        embed = Embed(title='Queue', color=0x25fa30)
        # Shows playing song, only when first "page" of the embed
        if page == 1:
            if self._playing:  # Check if theres a playing song
                embed.add_field(name='__Now Playing__',
                                value=f'[{self._playing.title}]({self._playing.webpage_url}) | `{self._playing.duration}` | `Requested by {self._playing.requester}`',
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
                                    value=f'`{i+1}.` [{self._songs[i].title}]({self._songs[i].webpage_url}) | `{self._songs[i].duration}` | `Requested by {self._songs[i].requester}`',
                                    inline=False)
                else:  # Normal song display field
                    embed.add_field(name='\u200b',
                                    value=f'`{i+1}.` [{self._songs[i].title}]({self._songs[i].webpage_url}) | `{self._songs[i].duration}` | `Requested by {self._songs[i].requester}`',
                                    inline=False)
            except IndexError:
                break
        embed.set_footer(text=f'Page {page}/{self.max_page} | {self.loop.value} | Duration: {self.duration}')
        return embed


class Music(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.queues: dict[int, Queue] = {}

    @commands.command(aliases=['summon'])
    async def join(self, ctx, channel: VoiceChannel = None):
        """Joins a voice channel"""
        current_queue = self.queues[ctx.guild.id]

        if not channel:
            if ctx.author.voice.channel:
                channel = ctx.author.voice.channel
            else:
                await ctx.reply('No voice channel found')
                return

        if not current_queue.voice_client:
            current_queue.voice_client = await channel.connect()

    @commands.command(aliases=['p'])
    async def play(self, ctx, *, query: str):
        """Add and play songs from url or song name"""
        current_queue = self.queues[ctx.guild.id]

        if not ctx.voice_client:
            await ctx.invoke(self.join)

        result = await search(query, ctx.author)
        match result:
            case Song():
                current_queue.add(result)
                # Song added response
                if ctx.voice_client.is_playing():  # Check if its playing, reply "song addition to queue" response
                    embed = Embed(title='Song added', description=f'[{result}]({result.webpage_url})', color=0x33c9a4)
                    embed.set_thumbnail(url=result.thumbnail_url)
                    embed.add_field(name='Channel', value=result.uploader)
                    embed.add_field(name='Duration', value=str(result.duration))
                    embed.add_field(name='Position in queue', value=str(len(current_queue)))
                    await ctx.reply(embed=embed)
            case Playlist():
                for song in result:
                    current_queue.add(song)
                # Playlist added response
                embed = Embed(title='Playlist Added', description=f'[{result}]({result.webpage_url})', color=0x33c9a4)
                embed.set_thumbnail(url=result[0].thumbnail_url)
                embed.add_field(name='Enqueued', value=f'{len(result)} songs')
                await ctx.reply(embed=embed)
            case _:
                # No results response
                await ctx.reply(f'No results found for {query}')
                return

        if not ctx.voice_client.is_playing():
            await ctx.reply(f'Playing `{result}`')
            current_queue.play()

    @commands.command()
    async def search(self, ctx, number_of_results: typing.Optional[int] = 10, *, query: str):
        """Shows results from YouTube to choose from, max 10 results"""
        number_of_results = number_of_results if number_of_results <= 10 else 10

        async with ctx.typing():
            results: list[Song] = await search(query, ctx.author, number_of_results=number_of_results)

        if results:
            # results embed
            embed = Embed(color=0x818555)
            for i, song in enumerate(results, start=1):
                embed.add_field(name='\u200b',
                                value=f'`{i}.` [{song.title}]({song.webpage_url}) | `{song.duration}`',
                                inline=False)
            embed.add_field(name='\u200b', value='**Reply `cancel` to cancel search.**', inline=False)

            msg = await ctx.reply(embed=embed)

            # check if the message is by the one who searched and is choosing or cancelling the search
            def check(message):
                return message.author == ctx.author and (message.content in map(str, range(1, len(results)+1)) or message.content == 'cancel')

            try:
                # wait for response
                response = await self.bot.wait_for('message', check=check, timeout=30)
            except asyncio.TimeoutError:  # timeout
                await msg.edit(content='Timeout', embed=None)
            else:
                if response.content in map(str, range(1, len(results)+1)):  # a number
                    await msg.delete()
                    await ctx.invoke(self.play, query=results[int(response.content) - 1].webpage_url)
                else:  # response is to cancel
                    await msg.delete()

    @commands.command(aliases=['q'])
    async def queue(self, ctx, page: int = 1):
        """Show the queue in embed form with pages"""
        current_queue = self.queues[ctx.guild.id]

        if not ctx.voice_client:
            await ctx.reply('Furret is not playing anything')
            return
        msg = await ctx.reply(embed=current_queue.embed(page))
        max_page = current_queue.max_page
        if max_page > 1:
            current_page = page
            await msg.add_reaction('⬅️')
            await msg.add_reaction('➡️')

            def check(reaction, user):
                return not user.bot and reaction.emoji in ('⬅️', '➡️')

            while True:
                try:
                    reaction, user = await self.bot.wait_for('reaction_add', timeout=10, check=check)
                except asyncio.TimeoutError:
                    await msg.clear_reactions()
                    break
                else:
                    await reaction.remove(user)
                    if reaction.emoji == '⬅️' and current_page != 1:
                        current_page -= 1
                    elif reaction.emoji == '➡️' and current_page != max_page:
                        current_page += 1
                    await msg.edit(embed=current_queue.embed(current_page))

    @commands.command(aliases=['s'])
    async def skip(self, ctx):
        """Skip the current playing song"""

        song = self.queues[ctx.guild.id].skip()
        await ctx.reply(f'Skipped `{song}`')

    @commands.command()
    async def pause(self, ctx):
        """Pause the current playing song"""

        if not ctx.voice_client.is_paused():
            ctx.voice_client.pause()
            await ctx.reply('Player paused')

    @commands.command()
    async def resume(self, ctx):
        """Resume the current paused song"""

        if ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.reply('Player resumed')

    @commands.command()
    async def volume(self, ctx, volume: int):
        """Change player volume, 1 - 100"""

        self.queues[ctx.guild.id].volume = volume
        await ctx.reply(f'Volume changed to `{volume}%`')

    @volume.error
    async def volume_error(self, ctx, error):
        match error:
            case MissingRequiredArgument():
                await ctx.reply(f'Volume is at `{self.queue[ctx.guild.id].volume}%`')
            case _:
                raise error

    @commands.command()
    async def move(self, ctx, song_position: int, ending_position: int):
        """Move song from one position to another"""
        current_queue = self.queues[ctx.guild.id]

        current_queue.move(song_position-1, ending_position-1)
        await ctx.reply(f'Moved `{current_queue[ending_position-1]}` to position `{ending_position}`')

    @commands.command()
    async def remove(self, ctx, position: int):
        """Remove the song on a specified position"""

        removed = self.queues[ctx.guild.id].pop(position-1)
        await ctx.reply(f'Removed `{removed.title}`')

    @commands.command()
    async def clear(self, ctx):
        """Clear queue. Doesn't affect current playing song"""

        self.queues[ctx.guild.id].clear()
        await ctx.reply("Queue cleared")

    @commands.command()
    async def stop(self, ctx):
        """Disconnect and clear queue"""

        await ctx.voice_client.disconnect()
        del self.queues[ctx.guild.id]

    @commands.command(aliases=['dc'])
    async def disconnect(self, ctx):
        """Disconnect and keep the queue"""

        await ctx.invoke(self.pause)
        await ctx.voice_client.disconnect()

    @commands.command()
    async def loop(self, ctx, mode=None):
        if not mode:
            await ctx.reply(f'{self.queues[ctx.guild.id].loop.value}\n'
                            f'`loop <clear|queue|song>` to change loop mode')
        else:
            match mode:
                case ('off' | 'clear'):
                    self.queues[ctx.guild.id].loop_mode(LoopType.NO_LOOP)
                    await ctx.reply('Not looping')
                case ('queue' | 'q'):
                    self.queues[ctx.guild.id].loop_mode(LoopType.LOOP_QUEUE)
                    await ctx.reply('Looping queue')
                case ('song' | 's'):
                    self.queues[ctx.guild.id].loop_mode(LoopType.LOOP_SONG)
                    await ctx.reply('Looping song')

    #
    # @commands.group()
    # async def playlist(self, ctx):
    #     if not ctx.invoked_subcommand:
    #         await ctx.
    #
    # @playlist.command()
    # async def save(self, ctx, *, playlist_name: str):
    #     entries = {playlist_name: [(song.title, song.webpage_url) for song in self.queues[ctx.guild.id]]}
    #     with open(r'.\config\music.json', 'w') as f:
    #         data = json.load(f)
    #         data['playlist'].update(entries)
    #         json.dump(data, f)
    #     await ctx.reply(f'Playlist `{playlist_name}` created.')
    #
    # @playlist.command()
    # async def play(self, ctx, *, playlist_name: str):

    @join.before_invoke
    @play.before_invoke
    @search.before_invoke
    async def create_queue(self, ctx):
        if ctx.guild.id not in self.queues:
            self.queues[ctx.guild.id] = Queue()


def setup(bot):
    bot.add_cog(Music(bot))
