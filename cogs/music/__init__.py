from .extractors import *
from .extractors.utils import timestamp, strip_seconds
from .client import MusicClient
from .loop_mode import LoopMode

import asyncio
from typing import Optional, cast
from discord.ext.commands._types import Check
from yt_dlp.utils import ExtractorError, DownloadError

from discord import VoiceChannel, Embed, Message, Reaction, Member
from discord.ext import commands
from discord.ext.commands import MissingRequiredArgument, Context, Bot, check


DEFAULT_EXTRACTOR = Youtube


def is_ctx_connected(ctx: Context) -> bool:
    client: MusicClient = cast(MusicClient, ctx.voice_client)
    return client and client.is_connected()


class Music(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot: Bot = bot

    @staticmethod
    def ignore_on_no_voice_client() -> Check:
        async def predicate(ctx: Context) -> bool:
            return is_ctx_connected(ctx)

        return check(predicate)

    async def implicit_join(self, ctx: Context) -> None:
        if not is_ctx_connected(ctx):
            if ctx.author.voice:
                await ctx.invoke(self.join, channel=ctx.author.voice.channel)

    @commands.command(aliases=['summon'])
    async def join(self, ctx, channel: VoiceChannel = None):
        """Join a voice channel. Default to your current voice channel if not specified"""
        # if channel is not specified, takes author's channel
        channel = channel or ctx.author.voice.channel

        if channel is None:
            await ctx.reply("You're not in a voice channel")
            return

        if not is_ctx_connected(ctx):
            await channel.connect(cls=MusicClient)
            return

        if channel != ctx.voice_client.channel:
            await ctx.voice_client.move_to(channel)

    @commands.command(aliases=['p'])
    async def play(self, ctx: Context, *, query: str, extractor: type[Extractor] = None):
        """Add the specific song from url or query"""
        if extractor is None:
            extractor = choose_extractor(query) or DEFAULT_EXTRACTOR

        async with ctx.typing():
            try:
                source = await extractor().process_query(query)
            except (DownloadError, ExtractorError) as e:
                if 'HTTP Error 429' in str(e):
                    await ctx.reply('Too many requests, please try again later')
                    return
                await ctx.reply('Failed to retrieve data, please try again later')
                return

        if not is_ctx_connected(ctx) and ctx.author.voice:
            await ctx.invoke(self.join, channel=ctx.author.voice.channel)

        client: MusicClient = cast(MusicClient, ctx.voice_client)
        client.add(source, ctx.author)
        await ctx.reply(embed=source.on_added_embed)

    @commands.command(aliases=['yt'])
    async def youtube(self, ctx, *, query: str):
        """Use YouTube to search and play"""
        await ctx.invoke(self.play, query=query, extractor=Youtube)

    @commands.command(aliases=['sc'])
    async def soundcloud(self, ctx, *, query: str):
        """Use SoundCloud to search and play"""
        await ctx.invoke(self.play, query=query, extractor=Soundcloud)

    @commands.command(aliases=['bd'])
    async def bandcamp(self, ctx, *, query: str):
        """Use Bandcamp to play"""
        await ctx.invoke(self.play, query=query, extractor=Bandcamp)

    @play.error
    @youtube.error
    @soundcloud.error
    @bandcamp.error
    async def play_error(self, ctx: Context, exception):
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
    async def search(self, ctx: Context, number_of_results: Optional[int] = 10, *, query: str):  # TODO: support searching for other extractors
        """Shows results from YouTube to choose from, max 10 results"""
        async with ctx.typing():
            results = [song async for song in Youtube().search(query, number_of_results=min(10, number_of_results))]

        if len(results) == 0:
            await ctx.reply('No results')
            return

        embed = Embed(color=0x818555)
        for i, song in enumerate(results, start=1):
            embed.add_field(name='\u200b',
                            value=f'`{i}.` [{song.title}]({song.webpage_url}) | `{song.timestamp}`',
                            inline=False)
        embed.add_field(name='\u200b', value='**Reply `cancel` to cancel search.**', inline=False)

        msg = await ctx.reply(embed=embed)

        # wait for response
        def check(message: Message):
            if message.author != ctx.author:
                return

            if message.content.casefold() == 'cancel':
                return True

            try:
                return int(message.content) in range(1, len(results) + 1)
            except ValueError:
                pass

        try:
            response = await self.bot.wait_for('message', check=check, timeout=30)
        except asyncio.TimeoutError:  # timeout
            await msg.edit(content='Timeout', embed=None)
        else:
            if not response.content.casefold() == 'cancel':
                await ctx.invoke(self.youtube, query=results[int(response.content) - 1].webpage_url)  # noqa
            await msg.delete()

    @commands.command(aliases=['q'])
    async def queue(self, ctx: Context, page: int = 1):
        """Show the queue in embed form with pages"""
        client: MusicClient = cast(MusicClient, ctx.voice_client)

        if not client:
            await ctx.reply('Not playing anything')
            return

        msg = await ctx.reply(embed=client.embed(page))
        max_page = client.max_page

        LEFT = '⬅️'
        RIGHT = '➡️'
        if max_page > 1:
            current_page = page
            await msg.add_reaction(LEFT)
            await msg.add_reaction(RIGHT)

            def check(reaction: Reaction, user: Member):
                return not user.bot and reaction.emoji in (LEFT, RIGHT)

            while True:
                max_page = client.max_page
                try:
                    reaction, user = await self.bot.wait_for('reaction_add', timeout=10, check=check)
                except asyncio.TimeoutError:
                    await msg.remove_reaction(LEFT, self.bot.user)
                    await msg.remove_reaction(RIGHT, self.bot.user)
                    break
                else:
                    await reaction.remove(user)
                    if reaction.emoji == LEFT and current_page != 1:
                        current_page -= 1
                    elif reaction.emoji == RIGHT and current_page != max_page:
                        current_page += 1
                    await msg.edit(embed=client.embed(current_page))

    @ignore_on_no_voice_client()
    @commands.command(aliases=['s'])
    async def skip(self, ctx: Context):
        """Skip the current playing song

        Skipping with loop on results in song being added back last in queue.
        """
        client: MusicClient = cast(MusicClient, ctx.voice_client)

        song = client.playing
        if song:
            client.skip()
            await ctx.reply(f'Skipped `{song}`')
        else:
            await ctx.reply('Not playing anything.')

    @ignore_on_no_voice_client()
    @commands.command()
    async def pause(self, ctx: Context):
        """Pause the current playing song"""
        client: MusicClient = cast(MusicClient, ctx.voice_client)

        client.pause()
        await ctx.reply('Player paused. :pause_button:')

    @ignore_on_no_voice_client()
    @commands.command()
    async def resume(self, ctx: Context):
        """Resume the current paused song"""
        client: MusicClient = cast(MusicClient, ctx.voice_client)

        client.resume()
        await ctx.reply('Player resumed. :arrow_forward:')

    @ignore_on_no_voice_client()
    @commands.command()
    async def shuffle(self, ctx: Context):
        """Shuffle the queue"""
        client: MusicClient = cast(MusicClient, ctx.voice_client)

        client.shuffle()
        await ctx.reply('Queue shuffled. :twisted_rightwards_arrows: ')

    @ignore_on_no_voice_client()
    @commands.command()
    async def volume(self, ctx: Context, volume: int = None):
        """Change player volume, 1 - 100"""
        client: MusicClient = cast(MusicClient, ctx.voice_client)

        if volume is None:
            await ctx.reply(f'Volume is at `{client.volume}%`')
            return

        client.volume = volume / 100
        await ctx.reply(f'Volume changed to `{volume}%`')

    @ignore_on_no_voice_client()
    @commands.command()
    async def speed(self, ctx: Context, speed: int = None):
        """Change player volume, 1 - 100"""
        client: MusicClient = cast(MusicClient, ctx.voice_client)

        if speed is None:
            await ctx.reply(f'Speed is at `{client.volume}%`')
            return

        client.speed = speed / 100
        await ctx.reply(f'Speed changed to `{speed}%`')

    @ignore_on_no_voice_client()
    @commands.command()
    async def seek(self, ctx: Context, seconds: int):
        """Change player volume, 1 - 100"""
        client: MusicClient = cast(MusicClient, ctx.voice_client)

        client.seek(seek=seconds)
        await ctx.reply(f'Seeked to `{seconds}` seconds')

    @ignore_on_no_voice_client()
    @commands.command(aliases=["np"])
    async def now_playing(self, ctx: Context):
        """Show the playing song information and progress"""

        client: MusicClient = cast(MusicClient, ctx.voice_client)

        playing: Source = client.playing

        embed = Embed(title='Now Playing', description=f'[{playing.title}]({playing.webpage_url})')
        embed.set_thumbnail(url=playing.thumbnail_url)
        embed.add_field(
            name='\u200b',
            value=f'`{timestamp(*strip_seconds(client.elapsed_seconds))} / {playing.timestamp}`',
            inline=False)
        await ctx.reply(embed=embed)

    @ignore_on_no_voice_client()
    @commands.command(aliases=["mv"])
    async def move(self, ctx: Context, song_position: int, ending_position: int):
        """Move song from one position to another"""
        client: MusicClient = cast(MusicClient, ctx.voice_client)

        moved_song = client.move(song_position-1, ending_position-1)
        await ctx.reply(f'Moved `{moved_song}` to position `{ending_position}`')

    @ignore_on_no_voice_client()
    @commands.command(aliases=["rm"])
    async def remove(self, ctx: Context, position: int):
        """Remove the song on a specified position"""
        client: MusicClient = cast(MusicClient, ctx.voice_client)

        try:
            removed = client.queue[position - 1]
            client.remove(position - 1)
        except IndexError:
            await ctx.reply(f'No song found in position `{position}`')
            return
        await ctx.reply(f'Removed `{removed.title}`')

    @ignore_on_no_voice_client()
    @commands.command(aliases=["cls"])
    async def clear(self, ctx: Context):
        """Clear queue. Doesn't affect current playing song"""
        client: MusicClient = cast(MusicClient, ctx.voice_client)

        client.clear()
        await ctx.reply("Queue cleared")

    @ignore_on_no_voice_client()
    @commands.command(aliases=['disconnect', 'dc'])
    async def stop(self, ctx: Context):
        """Disconnect and clear queue"""
        client: MusicClient = cast(MusicClient, ctx.voice_client)

        client.clear_all()
        await client.disconnect(force=False)

    @ignore_on_no_voice_client()
    @commands.command()
    async def loop(self, ctx: Context):
        """Toggle between loop modes"""
        client: MusicClient = cast(MusicClient, ctx.voice_client)

        match client.loop_mode:
            case LoopMode.NO_LOOP:
                client.loop_mode = LoopMode.LOOP_QUEUE
                await ctx.reply("Looping queue. :repeat:")
            case LoopMode.LOOP_SONG:
                client.loop_mode = LoopMode.LOOP_SONG
                await ctx.reply("Looping song. :repeat_one:")
            case LoopMode.LOOP_SONG:
                client.loop_mode = LoopMode.NO_LOOP
                await ctx.reply("Looping off. :red_circle:")


async def setup(bot):
    await bot.add_cog(Music(bot))
