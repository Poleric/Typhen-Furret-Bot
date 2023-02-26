from cogs.music.objects import Extractor, Song, Playlist, strip_timestamp
from cogs.music.youtube import YouTube
from cogs.music.soundcloud import SoundCloud
from cogs.music.bandcamp import Bandcamp
from cogs.music.queue import LoopType, Queue, NotConnected

import re
import json
import asyncio
from typing import Optional
from datetime import timedelta
from yt_dlp.utils import ExtractorError, DownloadError

from discord import VoiceChannel, Embed
from discord.ext import commands
from discord.ext.commands import MissingRequiredArgument


class Music(commands.Cog):
    CONFIG_PATH = r'./cogs/music/music.json'

    def __init__(self, bot):
        self.bot = bot
        self.queues: dict[int, Queue] = {}
        self.default_extractor = self.config['default_extractor']

    @property
    def default_extractor(self):
        return self._extractor

    @default_extractor.setter
    def default_extractor(self, extractor_name: str):
        match extractor_name.casefold():
            case 'yt' | 'youtube':
                self._extractor = YouTube
            case 'sc' | 'soundcloud':
                self._extractor = SoundCloud
            case 'bd' | 'bandcamp':
                self._extractor = Bandcamp

    @property
    def config(self) -> dict:
        try:
            with open(self.CONFIG_PATH, 'r') as f:
                config = json.load(f)
        except FileNotFoundError:
            config = {"default_extractor": "YouTube"}
            with open(self.CONFIG_PATH, "w") as f:
                json.dump(config, f)
        return config

    @config.setter
    def config(self, settings: dict):
        config = self.config
        config.update(settings)
        with open(self.CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=4)

    @commands.command(aliases=['summon'])
    async def join(self, ctx, channel: VoiceChannel = None):
        """Join a voice channel. Default to your current voice channel if not specified"""
        # if channel is not specified, takes author's channel
        if not channel:
            if ctx.author.voice.channel:
                channel = ctx.author.voice.channel
            else:
                await ctx.reply('You\'re not in a voice channel')
                return

        # check if connected to vc
        if not ctx.voice_client or not ctx.voice_client.is_connected():  # is not connected to a vc
            await channel.connect()
        # is connected to vc
        elif channel != ctx.voice_client.channel:  # check if the channel is different
            await ctx.voice_client.move_to(channel)

    async def auto_join(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_connected():
            return

        if not ctx.author.voice:
            await ctx.reply("You\'re not in a voice channel")
            raise NotConnected

        await ctx.invoke(self.join, channel=ctx.author.voice.channel)

    def get_queue(self, ctx):
        """Get queue related to the current server. Create a new one if it doesn't exist"""
        if ctx.guild.id not in self.queues:
            self.queues[ctx.guild.id] = Queue(ctx.voice_client)
        else:
            self.queues[ctx.guild.id].voice_client = ctx.voice_client
        return self.queues[ctx.guild.id]

    @commands.command(aliases=['p'])
    async def play(self, ctx, *, query: str, extractor: Extractor = None):
        """Add the specific song from url or query"""
        await self.auto_join(ctx)
        current_queue = self.get_queue(ctx)

        if not extractor:
            if YouTube.REGEX.match(query):
                extractor = YouTube()
            elif SoundCloud.REGEX.match(query):
                extractor = SoundCloud()
            elif Bandcamp.REGEX.match(query):
                extractor = Bandcamp()
            else:
                extractor = self.default_extractor()  # default

        async with ctx.typing():
            try:
                result = await extractor.process_query(query, requester=ctx.author)
            except (DownloadError, ExtractorError) as e:
                if re.search(r'HTTP Error 429', str(e)):
                    await ctx.reply('Too many requests, please try again later')
                    return
                await ctx.reply('Failed to retrieve data, please try again later')
                return
        match result:
            case Song():
                current_queue.add(result)

                # check if queue is empty
                # is empty - play song and reply the song name
                # is not empty - reply song added embed
                if current_queue.playing is None:
                    current_queue.play()
                    await ctx.send(f'Playing `{result}`')
                else:
                    embed = result.embed
                    embed.add_field(name='Position in queue', value=str(len(current_queue)))
                    await ctx.reply(embed=embed)
            case Playlist():
                current_queue.add_playlist(result)
                # playlist add response
                embed = result.embed
                await ctx.reply(embed=embed)

                if current_queue.playing is None:  # if adding playlist as first item
                    current_queue.play()

    @commands.command(aliases=['yt'])
    async def youtube(self, ctx, *, query: str):
        """Use Youtube to search and play"""
        await ctx.invoke(self.play, query=query, extractor=YouTube())

    @commands.command(aliases=['sc'])
    async def soundcloud(self, ctx, *, query: str):
        """Use SoundCloud to search and play"""
        await ctx.invoke(self.play, query=query, extractor=SoundCloud())

    @commands.command(aliases=['bd'])
    async def bandcamp(self, ctx, *, query: str):
        """Use Bandcamp to play"""
        await ctx.invoke(self.play, query=query, extractor=Bandcamp())

    @play.error
    @youtube.error
    @soundcloud.error
    @bandcamp.error
    async def play_error(self, ctx, exception):
        match exception:
            case MissingRequiredArgument():
                await ctx.reply('No query found.\n'
                                'Supported sites includes:\n'
                                '- YouTube\n'
                                '- SoundCloud\n'
                                '- Bandcamp (urls only)')
            case _:
                raise exception

    @commands.command()
    async def search(self, ctx, number_of_results: Optional[int] = 10, *, query: str):  # TODO: support searching for other extractors
        """Shows results from YouTube to choose from, max 10 results"""
        async with ctx.typing():
            yt = YouTube()
            results = []
            async for song in yt.search(query, results=min(10, number_of_results)):
                results.append(song)

        if not results:  # reply no results message when results list is empty
            await ctx.reply('No results')
            return

        # results embed
        embed = Embed(color=0x818555)
        for i, song in enumerate(results, start=1):
            embed.add_field(name='\u200b',
                            value=f'`{i}.` [{song.title}]({song.webpage_url}) | `{song.timestamp}`',
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
                await ctx.invoke(self.youtube, query=results[int(response.content) - 1].webpage_url)
            else:  # response is to cancel
                await msg.delete()

    @commands.command(aliases=['q'])
    async def queue(self, ctx, page: int = 1):
        """Show the queue in embed form with pages"""
        if not ctx.voice_client:
            await ctx.reply('Not playing anything')
            return

        current_queue = self.get_queue(ctx)

        msg = await ctx.reply(embed=current_queue.embed(page))
        max_page = current_queue.max_page
        if max_page > 1:
            current_page = page
            await msg.add_reaction('⬅️')
            await msg.add_reaction('➡️')

            def check(reaction, user):
                return not user.bot and reaction.emoji in ('⬅️', '➡️')

            while True:
                max_page = current_queue.max_page
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
        """Skip the current playing song

        Skipping with loop on results in song being added back last in queue.
        """
        current_queue = self.get_queue(ctx)

        song = current_queue.playing
        if song:
            current_queue.skip()
            await ctx.reply(f'Skipped `{song}`')
        else:
            await ctx.reply('Not playing anything')

    @commands.command()
    async def pause(self, ctx):
        """Pause the current playing song"""

        self.get_queue(ctx).pause()
        await ctx.reply('Player paused')

    @commands.command()
    async def resume(self, ctx):
        """Resume the current paused song"""

        self.get_queue(ctx).resume()
        await ctx.reply('Player resumed')

    @commands.command()
    async def shuffle(self, ctx):
        """Shuffle the queue"""

        self.get_queue(ctx).shuffle()
        await ctx.reply('Queue shuffled')

    @commands.command()
    async def volume(self, ctx, volume: int = None):
        """Change player volume, 1 - 100"""
        current_queue = self.get_queue(ctx)

        if volume is None:
            await ctx.reply(f'Volume is at `{current_queue.volume}%`')
            return

        current_queue.volume = volume
        await ctx.reply(f'Volume changed to `{volume}%`')

    @commands.command()
    async def np(self, ctx):
        """Show the playing song information and progress"""
        current_queue = self.get_queue(ctx)

        embed = Embed(title='Now Playing', description=f'[{current_queue.playing.title}]({current_queue.playing.webpage_url})')
        embed.set_thumbnail(url=current_queue.playing.thumbnail_url)
        embed.add_field(name='\u200b',
                        value=f'`{strip_timestamp(timedelta(seconds=current_queue.timer.get_elapsed()))} / {current_queue.playing.timestamp}`',
                        inline=False)
        await ctx.reply(embed=embed)

    @commands.command()
    async def move(self, ctx, song_position: int, ending_position: int):
        """Move song from one position to another"""
        current_queue = self.get_queue(ctx)

        moved_song = current_queue[song_position-1]
        current_queue.move(song_position-1, ending_position-1)
        await ctx.reply(f'Moved `{moved_song}` to position `{ending_position}`')

    @commands.command()
    async def remove(self, ctx, position: int):
        """Remove the song on a specified position"""
        current_queue = self.get_queue(ctx)
        try:
            removed = current_queue.pop(position - 1)
        except IndexError:
            await ctx.reply(f'No song found in position `{position}`')
            return
        await ctx.reply(f'Removed `{removed.title}`')

    @commands.command(aliases=['pop'])
    async def undo(self, ctx):
        """Removes the last song. Skips song if the last song is playing."""
        current_queue = self.get_queue(ctx)

        if len(current_queue):  # if theres song in queue
            await ctx.invoke(self.remove, position=len(current_queue))
        else:  # skip
            await ctx.invoke(self.skip)

    @commands.command()
    async def clear(self, ctx):
        """Clear queue. Doesn't affect current playing song"""

        self.get_queue(ctx).clear()
        await ctx.reply("Queue cleared")

    @commands.command(aliases=['disconnect', 'dc'])
    async def stop(self, ctx):
        """Disconnect and clear queue"""

        ctx.voice_client.stop()
        await ctx.voice_client.disconnect()
        del self.queues[ctx.guild.id]

    @commands.command()
    async def loop(self, ctx, mode='song'):
        """Show or change between loop modes, defaults to looping song if not specified

        Options:
            off / clear   - clear looping
            queue         - loops queue (song get added back to last in queue when finished)
            song / repeat - loops song
        """
        current_queue = self.get_queue(ctx)

        match mode:
            case ('off' | 'clear'):
                current_queue.loop = LoopType.NO_LOOP
                await ctx.reply('Loop turned off')
            case ('queue' | 'q'):
                current_queue.loop = LoopType.LOOP_QUEUE
                await ctx.reply('Loop queue :white_check_mark:')
            case ('song' | 's' | 'repeat' | 'r'):
                current_queue.loop = LoopType.LOOP_SONG
                await ctx.reply('Loop song :white_check_mark:')
            case _:
                await ctx.reply(f'Valid options are `off`, `queue`, `song`')

    @commands.command()
    async def default(self, ctx, website: str = None):
        """Show or set default website to search when not specified

        Current supported website list
        - YouTube
        - SoundCloud
        - Bandcamp
        """

        if not website:
            await ctx.reply(f'Default website is `{self.default_extractor()}`')
            return

        # setting variable and config
        self.default_extractor = website
        self.config = {
            'default_extractor': str(self.default_extractor())
        }

        await ctx.reply(f'Default website changed to `{self.default_extractor()}`')


async def setup(bot):
    await bot.add_cog(Music(bot))
