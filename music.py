import asyncio

import youtube_dl

import datetime

from random import shuffle

import discord
from discord.ext import commands


class YTDLSource(discord.PCMVolumeTransformer):
    # Suppress noise about console usage from errors
    youtube_dl.utils.bug_reports_message = lambda: ''

    ytdl_format_options = {
        'format': 'bestaudio/best',
        'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
        'restrictfilenames': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0'  # bind to ipv4 since ipv6 addresses cause issues sometimes
    }

    ffmpeg_options = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }

    ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

    @classmethod
    async def from_url(cls, query, *, loop=None, requester: discord.User):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: cls.ytdl.extract_info(query, download=False))

        queue = list()
        for entry in data['entries']:
            queue.append(Song(discord.FFmpegPCMAudio(entry.get('url'), **cls.ffmpeg_options), data=entry, requester=requester))

        return queue


# class Playlist:
#
#     def __init__(self, data):
#         self.data = data
#         self.length = len(data.get('entries'))
#         self.title = data['title']
#         self.webpage_url = data['webpage_url']
#         self.thumbnail = data.get['entries'][0]['thumbnail']
#
#     def create_embed(self):
#         embed = discord.Embed(title=self.title, color=0xf0d4b1, url=self.webpage_url)
#         embed.set_author(name='Playlist Added')
#         embed.set_thumbnail(url=self.thumbnail)
#         embed.add_field(name='Enqueued', value=f'{self.length} songs', inline=True)


class Song:

    def __init__(self, source, *, data, requester: discord.User):
        self.source = source
        self.data = data
        self.title = data.get('title')
        self.webpage_url = data.get('webpage_url')
        self.uploader = data.get('uploader')
        self.thumbnail = data.get('thumbnails')[0].get('url')
        self.duration = str(datetime.timedelta(seconds=data.get('duration')))
        self.requester = requester

    def create_embed(self):
        embed = discord.Embed(title=self.title, color=0xf0d4b1, url=self.webpage_url)
        embed.set_author(name='Song Added')
        embed.set_thumbnail(url=self.thumbnail)
        embed.add_field(name='Channel', value=self.uploader, inline=True)
        embed.add_field(name='Duration', value=self.duration, inline=True)


class Queue:

    def __init__(self):
        self.vc = None
        self.entries = list()
        self.loop = False

    def __iter__(self):
        return iter(self.entries)

    def __len__(self):
        return len(self.entries)

    def __getitem__(self, key):
        return self.entries[key]

    def shuffle(self):
        shuffle(self.entries)
        return 'Queue shuffled.'

    def clear(self):
        self.entries.clear()
        return 'Queue cleared.'

    def add_song(self, song: Song, top=False):
        if not top:
            self.entries.append(song)
        else:
            self.entries.insert(0, song)

    def remove_song_at_index(self, index: int):
        if index <= 0:
            return f'Position 0 or lower does\'nt exist.'
        else:
            return f'Removed `{self.entries.pop(index)}`'

    def move_song(self, song_index: int, new_index: int):
        self.entries.insert(new_index, self.entries.pop(song_index))
        return f'Moved `{self.entries[new_index]}` to position `{new_index}`'

    def play(self):
        if self.vc is not None:
            self.vc.play(self.entries[0].source, after=self.play_next)

    def play_next(self):
        if not self.loop:
            del self.entries[0]
            self.play()
        else:
            self.entries.append(self.entries.pop(0))
            self.play()

    def create_embed(self):
        if len(self.entries) == 0:
            embed = discord.Embed(title='Empty queue', color=0xf0d4b1)
        else:
            embed = discord.Embed(title='Queue', color=0xf0d4b1)
            for index, song in enumerate(self.entries):
                if index == 0:
                    embed.add_field(name='__Now Playing__', value=f'![{song.title}]!({song.webpage_url}) {song.duration} | Requested by {song.requester.name}{song.requester.discriminator}', inline=False)
                elif index == 1:
                    embed.add_field(name='__Enqueued__', value=f'1. ![{song.title}]!({song.webpage_url}) {song.duration} | Requested by {song.requester.name}{song.requester.discriminator}', inline=False)
                elif index <= 10:
                    embed.add_field(name='\u200b', value=f'{index} ![{song.title}]!({song.webpage_url}) {song.duration} | Requested by {song.requester.name}{song.requester.discriminator}', inline=False)
        return embed


class Music(commands.Cog):

    def __init__(self, client):
        self.bot = client
        self.queue = Queue()

    @commands.command()
    async def join(self, ctx, *, channel: discord.VoiceChannel):
        """Joins a voice channel"""

        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)

        await channel.connect()
        self.queue.vc = ctx.voice_client

    @commands.command(aliases=['p'])
    async def play(self, ctx, *, query):
        """Plays anything youtube-dl supports"""

        sources = YTDLSource.from_url(query=query, requester=ctx.author)
        for song in sources:
            self.queue.add_song(song)
        if not ctx.voice_client.is_playing:
            self.queue.play()
            await ctx.send(f'Now playing: `{self.queue[0].title}`')
        elif ctx.voice_client.is_playing:
            await ctx.send(self.queue[0].create_embed())

    @commands.command(aliases=['q'])
    async def queue(self, ctx):
        """Shows queue"""

        if ctx.voice_client is None:
            await ctx.send('Furret is not playing anything.')
        else:
            await ctx.send(self.queue.create_embed())

    @commands.command()
    async def volume(self, ctx, volume: int):
        """Changes the player's volume"""

        if ctx.voice_client is None:
            return await ctx.send("Not connected to a voice channel.")

        ctx.voice_client.source.volume = volume / 100
        await ctx.send("Changed volume to {}%".format(volume))

    @commands.command()
    async def shuffle(self, ctx):
        """Shuffles the queue"""

        await ctx.send(self.queue.shuffle())

    @commands.command()
    async def clear(self, ctx):
        """Clears the queue"""
        await ctx.send(self.queue.clear())

    @commands.command()
    async def pause(self, ctx):
        """Pauses the bot"""

        if not ctx.voice_client.is_paused():
            ctx.voice_client.pause()
            await ctx.send('Paused.')
        elif ctx.voice_client.is_paused():
            await ctx.send('Already paused.')

    @commands.command()
    async def resume(self, ctx):
        """Resumes the bot"""

        if ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send('Resumed.')
        elif not ctx.voice_client.is_paused():
            await ctx.send('Already playing.')

    @commands.command(aliases=['s'])
    async def skip(self, ctx):
        """Skip the current song"""

        ctx.voice_client.stop()
        self.queue.play()
        await ctx.send('SKipped.')

    @commands.command()
    async def move(self, ctx, song_index: int, new_index: int):
        """Moves song in a specific index / queue position to another index"""

        await ctx.send(self.queue.move_song(song_index=song_index, new_index=new_index))

    @commands.command()
    async def remove(self, ctx, song_index: int):
        """Removes song in a specific index / queue position"""

        await ctx.send(self.queue.remove_song_at_index(song_index))

    @commands.command()
    async def stop(self, ctx):
        """Stops and disconnects the bot from voice"""

        self.queue.clear()
        await ctx.voice_client.disconnect()

    @play.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
                self.queue.vc = ctx.voice_client
            else:
                await ctx.send("You are not connected to a voice channel.")
                raise commands.CommandError("Author not connected to a voice channel.")
        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()


def setup(client):
    client.add_cog(Music(client))