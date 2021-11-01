from cogs.music.base_source import Song, Playlist, timestamp
from cogs.music.youtube import YouTube
from cogs.music.queue import LoopType, Queue

import asyncio
from typing import Optional
from datetime import timedelta

from discord import VoiceChannel, Embed
from discord.ext import commands
from discord.ext.commands import MissingRequiredArgument


class Music(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.queues: dict[int, Queue] = {}

    @commands.command(aliases=['summon'])
    async def join(self, ctx, channel: VoiceChannel = None):
        """Joins a voice channel"""
        current_queue = self.queues[ctx.guild.id]

        # if channel is not specified
        if not channel:
            if ctx.author.voice.channel:
                channel = ctx.author.voice.channel
            else:
                await ctx.reply('No voice channel found')
                return

        # if voice_client == None (first time init) OR voice_client not connected (kicked out or disconnected)
        if not ctx.voice_client or not ctx.voice_client.is_connected():
            current_queue.voice_client = await channel.connect()
        # is connected, check if the member's channel is different from the current channel
        elif channel != ctx.voice_client.channel:
            current_queue.voice_client = await channel.connect()

    @commands.command(aliases=['p'])
    async def play(self, ctx, *, query: str):
        if YouTube.YT_REGEX.match(query):  # query matches youtube urls
            await ctx.invoke(self.youtube, query=query)
            return

        # resort to default website search
        await ctx.invoke(self.youtube, query=query)

    @commands.command(aliases=['yt'])
    async def youtube(self, ctx, *, query: str):
        """Add and play songs from Youtube. Auto search if not a url."""
        current_queue = self.queues[ctx.guild.id]
        empty_queue = current_queue.playing is None

        await ctx.invoke(self.join)
        async with ctx.typing():
            yt = YouTube()
            result = await yt.process_query(query, requester=ctx.author)
        match result:
            case Song():
                current_queue.add(result)

                # song add response IF the queue is not empty before adding songs
                if not empty_queue:
                    embed = result.embed
                    embed.add_field(name='Position in queue', value=str(len(current_queue)))
                    await ctx.reply(embed=embed)
            case Playlist():
                # add songs concurrently
                tasks = [asyncio.create_task(yt.get_video(url, ctx.author)) for url in result.songs_url]

                # function for adding songs from the tasks
                async def add_songs():
                    for task in tasks:
                        song = await task
                        current_queue.add(song)
                asyncio.create_task(add_songs())

                # playlist add response
                embed = result.embed
                embed.set_thumbnail(url=(await tasks[0]).thumbnail_url)  # take first song thumbnail
                await ctx.reply(embed=embed)

                result = await tasks[0]

        if empty_queue:
            current_queue.play()
            await ctx.reply(f'Playing `{result}`')

    @commands.command()
    async def search(self, ctx, number_of_results: Optional[int] = 10, *, query: str):
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
    async def volume(self, ctx, volume: int):
        """Change player volume, 1 - 100"""
        current_queue = self.queues[ctx.guild.id]

        current_queue.volume = volume
        await ctx.reply(f'Volume changed to `{volume}%`')

    @commands.command()
    async def np(self, ctx):
        current_playing = self.queues[ctx.guild.id].playing
        player = ctx.voice_client._player

        embed = Embed(title='Now Playing', description=f'[{current_playing.title}]({current_playing.webpage_url})')
        embed.set_thumbnail(url=current_playing.thumbnail_url)
        embed.add_field(name='\u200b',
                        value=f'`{timestamp(timedelta(seconds=player.DELAY * player.loops))} / {timestamp(current_playing.duration)}`',
                        inline=False)
        await ctx.reply(embed=embed)

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

        moved_song = current_queue[song_position]
        current_queue.move(song_position, ending_position)
        await ctx.reply(f'Moved `{moved_song}` to position `{ending_position}`')

    @commands.command()
    async def remove(self, ctx, position: int):
        """Remove the song on a specified position"""
        current_queue = self.queues[ctx.guild.id]

        removed = current_queue.pop(position-1)
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

        current_queue.clear()
        await ctx.voice_client.disconnect()
        del self.queues[ctx.guild.id]

    @commands.command()
    async def loop(self, ctx, mode=None):
        current_queue = self.queues[ctx.guild.id]

        if not mode:
            await ctx.reply(f'{current_queue.loop.value}\n'
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
    @youtube.before_invoke
    @search.before_invoke
    async def create_queue(self, ctx):
        if ctx.guild.id not in self.queues:
            self.queues[ctx.guild.id] = Queue()


def setup(bot):
    bot.add_cog(Music(bot))
