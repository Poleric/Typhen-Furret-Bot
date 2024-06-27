from discord import Embed, Reaction, Member, \
    ClientException
from discord.ext import commands
from discord.ext.commands import Cog, Bot, Context
from wavelink import Node, Pool, Queue, Player, Playable, Playlist, Search, Filters, \
    TrackStartEventPayload, NodeReadyEventPayload, \
    QueueMode, AutoPlayMode, TrackSource
from .utils import tm
from .embed import QueueEmbed
import itertools
import asyncio
import os

from typing import cast
import logging

logger = logging.getLogger("music")


class Music(Cog):
    def __init__(self, bot: Bot):
        self.bot: Bot = bot

    async def cog_load(self) -> None:
        nodes = [Node(
            uri="http://localhost:2333",
            password=os.getenv("LAVALINK_SERVER_PASSWORD")
        )]
        await Pool.connect(nodes=nodes, client=self.bot, cache_capacity=100)

    async def cog_unload(self) -> None:
        await Pool.close()

    @Cog.listener()
    async def on_wavelink_node_ready(self, payload: NodeReadyEventPayload) -> None:
        logger.info("Wavelink Node connected: %r | Resumed: %s", payload.node, payload.resumed)

    @Cog.listener()
    async def on_wavelink_track_start(self, payload: TrackStartEventPayload) -> None:
        player: Player | None = payload.player
        if not player:
            # Handle edge cases...
            return

        original: Playable | None = payload.original
        track: Playable = payload.track

        embed: Embed = Embed(title="Now Playing")
        embed.description = f"**{track.title}** by `{track.author}`"

        if track.artwork:
            embed.set_thumbnail(url=track.artwork)

        if original and original.recommended:
            embed.description += f"\n\n`This track was recommended via {track.source}`"

        if track.album.name:
            embed.add_field(name="Album", value=track.album.name)

        await player.home.send(embed=embed, silent=True)

    @commands.command(aliases=['p'])
    async def play(self, ctx: Context, query: str):
        """Join a voice channel. Default to your current voice channel if not specified"""
        if not ctx.guild:
            return

        player: Player
        player = cast(Player, ctx.voice_client)  # type: ignore

        if not player:
            try:
                player = await ctx.author.voice.channel.connect(cls=Player)  # type: ignore
            except AttributeError:
                await ctx.send("Please join a voice channel first before using this command.")
                return
            except ClientException:
                await ctx.send("I was unable to join this voice channel. Please try again.")
                return

        # Turn on AutoPlay to enabled mode.
        # enabled = AutoPlay will play songs for us and fetch recommendations...
        # partial = AutoPlay will play songs for us, but WILL NOT fetch recommendations...
        # disabled = AutoPlay will do nothing...
        player.autoplay = AutoPlayMode.enabled

        # Lock the player to this channel...
        if not hasattr(player, "home"):
            player.home = ctx.channel
        elif player.home != ctx.channel:
            await ctx.send(
                f"You can only play songs in {player.home.mention}, as the player has already started there.")
            return

        # This will handle fetching Tracks and Playlists...
        # Seed the doc strings for more information on this method...
        # If spotify is enabled via LavaSrc, this will automatically fetch Spotify tracks if you pass a URL...
        # Defaults to YouTube for non URL based queries...
        tracks: Search = await Playable.search(query, source=TrackSource.YouTube)
        if not tracks:
            await ctx.send(f"{ctx.author.mention} - Could not find any tracks with that query. Please try again.")
            return

        if isinstance(tracks, Playlist):
            # tracks is a playlist...
            added: int = await player.queue.put_wait(tracks)
            await ctx.send(f"Added the playlist **`{tracks.name}`** ({added} songs) to the queue.")
        else:
            track: Playable = tracks[0]
            await player.queue.put_wait(track)
            await ctx.send(f"Added **`{track}`** to the queue.")

        if not player.playing:
            # Play now since we aren't playing anything...
            await player.play(player.queue.get(), volume=30)

    @commands.command(aliases=['s'])
    async def skip(self, ctx: Context):
        """Skip the current song"""
        player: Player = cast(Player, ctx.voice_client)
        if not player:
            return

        await player.skip(force=True)
        await ctx.message.add_reaction("\u2705")

    @commands.command()
    async def speed(self, ctx: Context, speed: int = 100):
        """Change player volume, in percentages"""
        player: Player = cast(Player, ctx.voice_client)
        if not player:
            return

        filters: Filters = player.filters
        filters.timescale.set(pitch=1, speed=speed / 100, rate=1)
        await player.set_filters(filters)

        await ctx.message.add_reaction("\u2705")

    @commands.command(aliases=["resume"])
    async def pause(self, ctx: Context) -> None:
        """Pause or resume playing."""
        player: Player = cast(Player, ctx.voice_client)
        if not player:
            return

        await player.pause(not player.paused)
        await ctx.message.add_reaction("\u2705")

    @commands.command()
    async def volume(self, ctx: Context, volume: int = 100):
        """Change player volume, 1 - 100"""
        player: Player = cast(Player, ctx.voice_client)
        if not player:
            return

        await player.set_volume(volume)
        await ctx.message.add_reaction("\u2705")

    @commands.command(aliases=["dc"])
    async def disconnect(self, ctx: Context):
        """Disconnect the player"""
        player: Player = cast(Player, ctx.voice_client)
        if not player:
            return

        await player.disconnect()
        await ctx.message.add_reaction("\u2705")

    @commands.command()
    async def stop(self, ctx: Context):
        """Disconnect and clear the player"""
        player: Player = cast(Player, ctx.voice_client)
        if not player:
            return

        await player.disconnect()
        player.queue.reset()
        await ctx.message.add_reaction("\u2705")

    @commands.command()
    async def shuffle(self, ctx: Context):
        """Shuffle the queue"""
        player: Player = cast(Player, ctx.voice_client)
        if not player:
            return

        player.queue.shuffle()
        await ctx.message.add_reaction("\u2705")

    @commands.command(aliases=["ss"])
    async def seek(self, ctx: Context, seconds: float):
        """Seek to a timestamp in the current song"""
        player: Player = cast(Player, ctx.voice_client)
        if not player:
            return

        ms = int(seconds * 1000)
        await player.seek(ms)
        await ctx.reply(f'Seeked to `{seconds:.2f}` seconds')

    @commands.command(aliases=["mv"])
    async def move(self, ctx: Context, song_position: int, ending_position: int):
        """Move song from one position to another"""
        player: Player = cast(Player, ctx.voice_client)
        if not player:
            return

        try:
            moved_song = player.queue[song_position - 1]
            player.queue.delete(song_position - 1)
        except IndexError:
            await ctx.reply(f'No song found in position `{song_position}`')
            return
        player.queue.put_at(ending_position - 1, moved_song)
        await ctx.reply(f'Moved `{moved_song.title}` to position `{ending_position}`')

    @commands.command(aliases=["rm"])
    async def remove(self, ctx: Context, position: int):
        """Remove the song on a specified position"""
        player: Player = cast(Player, ctx.voice_client)
        if not player:
            return

        try:
            removed = player.queue[position - 1]
            player.queue.delete(position - 1)
        except IndexError:
            await ctx.reply(f'No song found in position `{position}`')
            return
        await ctx.reply(f'Removed `{removed.title}`')

    @commands.command(aliases=["cls"])
    async def clear(self, ctx: Context):
        """Clear queue. Doesn't affect current playing song"""
        player: Player = cast(Player, ctx.voice_client)
        if not player:
            return

        player.queue.clear()
        await ctx.reply("Queue cleared")

    @commands.command()
    async def loop(self, ctx: Context):
        """Toggle between loop modes"""
        player: Player = cast(Player, ctx.voice_client)
        if not player:
            return

        queue: Queue = player.queue
        match queue.mode:
            case QueueMode.normal:
                queue.mode = QueueMode.loop
                await ctx.reply("Looping queue. :repeat:")
            case QueueMode.loop:
                queue.mode = QueueMode.loop_all
                await ctx.reply("Looping song. :repeat_one:")
            case QueueMode.loop_all:
                queue.mode = QueueMode.loop
                await ctx.reply("Looping off. :red_circle:")

    @commands.command(aliases=["np"])
    async def now_playing(self, ctx: Context):
        """Show the playing song information and progress"""
        player: Player = cast(Player, ctx.voice_client)
        if not player:
            return
        if not player.playing:
            await ctx.reply("Not playing.")
            return

        playing: Playable = player.current

        embed = Embed(title='Now Playing', description=f'[{playing.title}]({playing.uri})')
        embed.set_thumbnail(url=playing.artwork)
        embed.add_field(
            name='\u200b',
            value=f'`{tm.from_millis(player.position)} / {tm.from_millis(playing.length)}`',
            inline=False)
        await ctx.reply(embed=embed)

    @commands.command(aliases=['q'])
    async def queue(self, ctx: Context, page: int = 1):
        """Show the queue in embed form with pages"""
        player: Player = cast(Player, ctx.voice_client)
        if not player:
            await ctx.reply('Not playing anything')
            return

        queue_embed = QueueEmbed(player.queue)
        LEFT = '⬅️'
        RIGHT = '➡️'

        msg = await ctx.reply(embed=queue_embed.get_page(page))
        await msg.add_reaction(LEFT)
        await msg.add_reaction(RIGHT)

        def check(reaction: Reaction, user: Member):
            return not user.bot and reaction.emoji in (LEFT, RIGHT)

        while True:
            on_reaction_add = asyncio.create_task(self.bot.wait_for("reaction_add", check=check))
            on_reaction_remove = asyncio.create_task(self.bot.wait_for("reaction_remove", check=check))
            done, pending = await asyncio.wait(
                [on_reaction_add, on_reaction_remove],
                timeout=10,
                return_when=asyncio.FIRST_COMPLETED
            )

            if not done:
                await msg.remove_reaction(LEFT, self.bot.user)
                await msg.remove_reaction(RIGHT, self.bot.user)
                break

            for task in itertools.chain(done, pending):
                task.cancel()

            reaction, _ = done.pop().result()

            if reaction.emoji == LEFT:
                new_page = page - 1
            else:
                new_page = page + 1

            try:
                await msg.edit(embed=queue_embed.get_page(new_page))
            except IndexError:
                pass
            else:
                page = new_page


async def setup(bot):
    await bot.add_cog(Music(bot))
