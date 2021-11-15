from cogs.music.base_source import BaseExtractor, BaseSong, BasePlaylist, timestamp
from cogs.music.youtube import YouTube
from cogs.music.soundcloud import SoundCloud
from cogs.music.bandcamp import Bandcamp
from cogs.music.queue import LoopType, Queue

import re
import json
import asyncio
from typing import Optional
from datetime import timedelta
from youtube_dl.utils import ExtractorError, DownloadError

from discord import VoiceChannel, Embed
from discord.ext import commands
from discord.ext.commands import MissingRequiredArgument


class Music(commands.Cog):
    CONFIG_PATH = r'./cogs/music/music.json'

    def __init__(self, bot):
        self.bot = bot
        self.queues: dict[int, Queue] = {}
        self.default_extractor = self.config['default_extractor']

    def get_default_extractor(self):
        return self._extractor

    def set_default_extractor(self, extractor_name: str):
        match extractor_name.casefold():
            case 'yt' | 'youtube':
                self._extractor = YouTube
            case 'sc' | 'soundcloud':
                self._extractor = SoundCloud
            case 'bd' | 'bandcamp':
                self._extractor = Bandcamp

    default_extractor = property(get_default_extractor, set_default_extractor)

    def read_config(self) -> dict:
        with open(self.CONFIG_PATH, 'r') as f:
            config = json.load(f)
        return config

    def commit_config(self, settings: dict):
        config = self.read_config()
        config.update(settings)
        with open(self.CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=4)

    config = property(read_config, commit_config)

    @commands.command(aliases=['summon'])
    async def join(self, ctx, channel: VoiceChannel = None):
        """Join a voice channel. Default to your current voice channel if not specified"""
        current_queue = self.queues[ctx.guild.id]

        # if channel is not specified, takes author's channel
        if not channel:
            if ctx.author.voice.channel:
                channel = ctx.author.voice.channel
            else:
                await ctx.reply('You\'re not in a voice channel')
                return

        # if voice_client == None (first time init) OR voice_client not connected (kicked out or disconnected)
        if not ctx.voice_client or not ctx.voice_client.is_connected():
            current_queue.voice_client = await channel.connect()
        # is connected, check if the member's channel is different from the current channel
        elif channel != ctx.voice_client.channel:
            await ctx.voice_client.move_to(channel)

    @commands.command(aliases=['p'])
    async def play(self, ctx, *, query: str, extractor: BaseExtractor = None):
        """Add the specific song from url or query"""
        current_queue = self.queues[ctx.guild.id]
        if not extractor:
            if YouTube.REGEX.match(query):
                extractor = YouTube()
            elif SoundCloud.REGEX.match(query):
                extractor = SoundCloud()
            elif Bandcamp.REGEX.match(query):
                extractor = Bandcamp()
            else:
                extractor = self.default_extractor()  # default

        if not ctx.voice_client or not ctx.voice_client.is_connected():
            await ctx.invoke(self.join)
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
            case BaseSong():
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
            case BasePlaylist():
                # add songs concurrently
                tasks = [asyncio.create_task(extractor.process_query(url, ctx.author)) for url in result.songs_url]

                # function for adding songs from the tasks AND catching exception
                async def add_songs():
                    for i, task in enumerate(tasks):
                        try:
                            song = await task
                            if song:
                                current_queue.add(song)
                        except (DownloadError, ExtractorError):
                            if re.search(r'HTTP Error 429', str(e)):
                                await ctx.reply('Too many requests, please try again later')
                                return
                            await ctx.reply(f'Failed to retrieve data for {result.songs_url[i]}, please try again later')
                            return

                add_song_task = asyncio.create_task(add_songs())

                first_song = await tasks[0]
                # playlist add response
                embed = result.embed
                embed.set_thumbnail(url=first_song.thumbnail_url)  # take first song thumbnail
                await ctx.reply(embed=embed)

                if current_queue.playing is None:  # if adding playlist as first item
                    # "play" song and immediately pause, giving option to resume
                    current_queue.play()
                    ctx.voice_client.pause()

                    # for lower end hardware
                    await ctx.reply('Songs are being added in the background, you can use `resume` command to play but keep in mind it will be crackly at parts due to hardware limitations.\n'
                                    'Will automatically start playing once finished adding songs.')

                    await add_song_task  # wait till finish adding songs
                    if ctx.voice_client.is_paused():  # automatically resume playing
                        ctx.voice_client.resume()
                        await ctx.send(f'Playing `{first_song}`')

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
        number_of_results = number_of_results if number_of_results <= 10 else 10

        async with ctx.typing():
            yt = YouTube()
            results = []
            async for song in yt.search(query, results=number_of_results):
                results.append(song)

        if results:
            # results embed
            embed = Embed(color=0x818555)
            for i, song in enumerate(results, start=1):
                embed.add_field(name='\u200b',
                                value=f'`{i}.` [{song.title}]({song.webpage_url}) | `{timestamp(song.duration)}`',
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
            await ctx.reply('Furret is not playing anything')
            return

        current_queue = self.queues[ctx.guild.id]

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
        """Skip the current playing song"""
        current_queue = self.queues[ctx.guild.id]

        song = current_queue.skip()
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
    async def shuffle(self, ctx):
        """Shuffle the queue"""

        current_queue = self.queues[ctx.guild.id]

        current_queue.shuffle()
        await ctx.reply('Queue shuffled')

    @commands.command()
    async def volume(self, ctx, volume: int = None):
        """Change player volume, 1 - 100"""
        current_queue = self.queues[ctx.guild.id]

        if volume is None:
            await ctx.reply(f'Volume is at `{current_queue.volume}%`')
            return
        current_queue.volume = volume
        await ctx.reply(f'Volume changed to `{volume}%`')

    @commands.command()
    async def np(self, ctx):
        """Show the playing song information and progress"""
        current_playing = self.queues[ctx.guild.id].playing
        player = ctx.voice_client._player

        embed = Embed(title='Now Playing', description=f'[{current_playing.title}]({current_playing.webpage_url})')
        embed.set_thumbnail(url=current_playing.thumbnail_url)
        embed.add_field(name='\u200b',
                        value=f'`{timestamp(timedelta(seconds=player.DELAY * player.loops))} / {timestamp(current_playing.duration)}`',
                        inline=False)
        await ctx.reply(embed=embed)

    @commands.command()
    async def move(self, ctx, song_position: int, ending_position: int):
        """Move song from one position to another"""
        current_queue = self.queues[ctx.guild.id]

        moved_song = current_queue[song_position]
        current_queue.move(song_position, ending_position)
        await ctx.reply(f'Moved `{moved_song}` to position `{ending_position}`')

    @commands.command()
    async def remove(self, ctx, position: int):
        """Remove the song on a specified position"""
        current_queue = self.queues[ctx.guild.id]
        try:
            removed = current_queue.pop(position-1)
        except IndexError:
            await ctx.reply(f'No song found in position `{position}`')
            return
        await ctx.reply(f'Removed `{removed.title}`')

    @commands.command()
    async def clear(self, ctx):
        """Clear queue. Doesn't affect current playing song"""
        current_queue = self.queues[ctx.guild.id]

        current_queue.clear()
        await ctx.reply("Queue cleared")

    @commands.command(aliases=['disconnect', 'dc'])
    async def stop(self, ctx):
        """Disconnect and clear queue"""
        current_queue = self.queues[ctx.guild.id]

        current_queue.stop()
        await ctx.voice_client.disconnect()
        del self.queues[ctx.guild.id]

    @commands.command()
    async def loop(self, ctx, mode=None):
        """Show or change between loop modes"""
        current_queue = self.queues[ctx.guild.id]

        if not mode:
            match self.loop:
                case LoopType.LOOP_QUEUE:
                    loop = 'Looping queue'
                case LoopType.LOOP_SONG:
                    loop = 'Looping song'
                case _:
                    loop = 'No loop'
            await ctx.reply(f'{loop}\n'
                            f'`loop <clear|queue|song>` to change loop mode')
        else:
            match mode:
                case ('off' | 'clear'):
                    current_queue.loop = LoopType.NO_LOOP
                    await ctx.reply('Not looping')
                case ('queue' | 'q'):
                    current_queue.loop = LoopType.LOOP_QUEUE
                    await ctx.reply('Looping queue')
                case ('song' | 's'):
                    current_queue.loop = LoopType.LOOP_SONG
                    await ctx.reply('Looping song')

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

    # @commands.group()
    # async def playlist(self, ctx):
    #     pass
    #
    # @playlist.command()
    # async def list(self, ctx):
    #     playlists: list[SavedPlaylist] = []
    #     with open(r'./config/music.json', 'r') as f:
    #         for playlist in json.load(f)['saved_playlist']:
    #             playlists.append(SavedPlaylist(**playlist))
    #
    #     embed = Embed(title='Saved Playlists')
    #     for playlist in playlists:
    #         msgs = (f"`{i}.` {song['name']}\n" for i, song in zip(range(2), playlist.songs))
    #         embed.add_field(name=f'{playlist.name} | {playlist.owner_name} | `{len(playlist)}` songs',
    #                         value=f'{"".join(msgs)}',
    #                         inline=False)

    @join.before_invoke
    @play.before_invoke
    @search.before_invoke
    async def create_queue(self, ctx):
        if ctx.guild.id not in self.queues:
            self.queues[ctx.guild.id] = Queue()


def setup(bot):
    bot.add_cog(Music(bot))
