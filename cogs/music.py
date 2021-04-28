import asyncio

import math

import youtube_dl

import datetime

from random import shuffle

from youtubesearchpython import SearchVideos

import discord
from discord import FFmpegPCMAudio, PCMVolumeTransformer
from discord.ext import commands


ffmpeg_options = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }


class YTDLSource:
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

    ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

    @classmethod
    async def search(cls, query: str, number_of_results: int):
        return SearchVideos(query, offset=1, mode='dict', max_results=number_of_results).result().get('search_result')

    @classmethod
    async def from_url(cls, query, *, loop=None, requester: discord.User):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: cls.ytdl.extract_info(query, download=False))

        if 'entries' in data:
            queue = [Playlist(data)]
            for entry in data['entries']:
                queue.append(Song(data=entry, requester=requester))

            return queue
        else:
            return Song(data=data, requester=requester)


class Playlist:

    def __init__(self, data):
        self.data = data
        self.length = len(data.get('entries'))
        self.title = data['title']
        self.webpage_url = data['webpage_url']
        self.thumbnail = data['entries'][0]['thumbnails'][0].get('url')

    def create_embed(self):
        embed = discord.Embed(title=self.title, color=0xf0d4b1, url=self.webpage_url)
        embed.set_author(name='Playlist Added')
        embed.set_thumbnail(url=self.thumbnail)
        embed.add_field(name='Enqueued', value=f'{self.length} songs', inline=True)
        return embed


class Song:

    def __init__(self, *, data, requester: discord.User):
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.webpage_url = data.get('webpage_url')
        self.uploader = data.get('uploader')
        self.thumbnail = data.get('thumbnails')[0].get('url')
        self.duration = datetime.timedelta(seconds=data.get('duration'))
        self.requester = requester

    def create_embed(self):
        embed = discord.Embed(title=self.title, color=0xf0d4b1, url=self.webpage_url)
        embed.set_author(name='Song Added')
        embed.set_thumbnail(url=self.thumbnail)
        embed.add_field(name='Channel', value=self.uploader, inline=True)
        embed.add_field(name='Duration', value=str(self.duration), inline=True)
        return embed


class Queue:

    def __init__(self):
        self.vc = None
        self._entries = list()
        self.loop_queue = False
        self.loop_song = False
        self.playing = False
        self._duration = datetime.timedelta()

    def __iter__(self):
        return iter(self._entries)

    def __len__(self):
        return len(self._entries)

    def __getitem__(self, key):
        return self._entries[key]

    def shuffle(self):
        playing = self._entries.pop(0)
        shuffle(self._entries)
        self._entries.insert(0, playing)
        return '**Queue shuffled.**'

    def clear(self):
        playing = self._entries.pop(0)
        self._entries.clear()
        self._duration = datetime.timedelta()
        self._entries.append(playing)
        return '**Queue cleared.**'

    def stop(self):
        self._entries.clear()
        self.vc = None
        self.loop_queue = False
        self.loop_song = False
        self._duration = datetime.timedelta()

    def add_song(self, song: Song, top=False):
        if not top:
            self._entries.append(song)
        else:
            self._entries.insert(0, song)
        self._duration += song.duration

    def remove_song_at_index(self, index: int):
        if index == 0 or index >= len(self._entries):
            return None
        else:
            song = self._entries.pop(index)
            self._duration -= song.duration
            return song

    def move_song(self, song_index: int, new_index: int):
        self._entries.insert(new_index, self._entries.pop(song_index))
        return f'**Moved `{self._entries[new_index].title}` to position `{new_index}`**'

    def play(self):
        if self.vc is not None:
            try:
                self.vc.play(PCMVolumeTransformer(FFmpegPCMAudio(self._entries[0].url, **ffmpeg_options)), after=self.play_next)
                self.playing = True
                if not self.loop_song:
                    self._duration -= self._entries[0].duration
            except IndexError:
                pass

    def play_next(self, error):
        self.playing = False
        if error is not None:
            print(f'Player error: {error}')
        if self.loop_song:
            self.play()
        elif self.loop_queue:
            self.add_song(self._entries.pop(0))
            self.play()
        else:
            if len(self._entries) != 0:
                del self._entries[0]
                if len(self._entries) != 0:
                    self.play()

    def create_embed(self, page: int = 1):
        if len(self._entries) == 0:
            embed = discord.Embed(title='Empty queue', color=0xf0d4b1)
        elif page == 1:
            embed = discord.Embed(title='Queue', color=0xf0d4b1)
            for index, song in enumerate(self._entries):
                if index == 0:
                    embed.add_field(name='__Now Playing__',
                                    value=f'[{song.title}]({song.webpage_url}) | `{str(song.duration)}` | `Requested by {song.requester.name}#{song.requester.discriminator}`',
                                    inline=False)
                elif index == 1:
                    embed.add_field(name='__Enqueued__',
                                    value=f'`{index}.` [{song.title}]({song.webpage_url}) | `{str(song.duration)}` | `Requested by {song.requester.name}#{song.requester.discriminator}`',
                                    inline=False)
                elif index <= 10:
                    embed.add_field(name='\u200b',
                                    value=f'`{index}.` [{song.title}]({song.webpage_url}) | `{str(song.duration)}` | `Requested by {song.requester.name}#{song.requester.discriminator}`',
                                    inline=False)
                else:
                    break
            if len(self._entries) > 1:
                embed.add_field(name='\u200b',
                                value=f'**Enqueued:** `{len(self._entries) - 1}` songs | **Total duration:** `{self._duration}`',
                                inline=False)
            if (max_page := math.ceil((len(self._entries) - 1) / 10)) < 1:
                max_page = 1
            embed.set_footer(text=f'Page {page}/{max_page}')
        else:
            embed = discord.Embed(title='Queue', color=0xf0d4b1)
            try:
                for index in range(1 + 10 * (page - 1), 1 + 10 * page):
                    song = self._entries[index]
                    embed.add_field(name='\u200b',
                                    value=f'`{index}.` [{song.title}]({song.webpage_url}) | `{str(song.duration)}` | `Requested by {song.requester.name}#{song.requester.discriminator}`',
                                    inline=False)
            except IndexError:
                pass
            embed.add_field(name='\u200b',
                            value=f'**Enqueued:** `{len(self._entries) - 1}` songs | **Total duration:** `{self._duration}`',
                            inline=False)
            embed.set_footer(text=f'Page {page}/{math.ceil((len(self._entries) - 1) / 10)}')
        return embed


class Music(commands.Cog):

    def __init__(self, client):
        self.bot = client
        self.queues = dict()
        for guild in self.bot.guilds:
            self.queues[guild.id] = Queue()

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            self.queues[guild.id] = Queue()

    @commands.command()
    async def join(self, ctx, *, channel: discord.VoiceChannel):
        """Joins a voice channel"""

        queue = self.queues[ctx.guild.id]
        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)

        queue.vc = await channel.connect()

    @commands.command(aliases=['p'])
    async def play(self, ctx, *, url: str):
        """Plays anything youtube-dl supports"""

        queue = self.queues[ctx.guild.id]

        async with ctx.channel.typing():
            url = url.strip('<').strip('>')
            playlist = False
            if not url.startswith('https://www.youtube.com/'):
                query = await YTDLSource.search(url, 1)
                if len(query) != 0:
                    url = query[0].get('link')
                else:
                    url = None
            if url is not None:
                sources = await YTDLSource.from_url(url, requester=ctx.author)
                if sources is not None:
                    if isinstance(sources, Song):
                        queue.add_song(sources)
                    else:
                        for index, song in enumerate(sources):
                            if index == 0:
                                playlist = True
                            else:
                                queue.add_song(song)

                if playlist:
                    await ctx.reply(embed=sources[0].create_embed())

                if not queue.playing:
                    queue.play()
                    await ctx.reply(f'**Now playing:** `{queue[0].title}`')
                elif not playlist:
                    await ctx.reply(
                        embed=sources.create_embed().add_field(name='Position', value=str(len(queue) - 1), inline=True))
            else:
                await ctx.reply('**No result found.**')

    @commands.command()
    async def search(self, ctx, *, query):
        """Yield at most 10 results from youtube"""

        async with ctx.channel.typing():
            results = await YTDLSource.search(query, 10)
            if len(results) != 0:

                numbers = list()
                embed = discord.Embed(color=0xf0d4b1)
                for search in results:
                    numbers.append(str(search['index'] + 1))
                    embed.add_field(name='\u200b',
                                    value=f'`{search.get("index") + 1}.` [{search.get("title")}]({search.get("link")}) | `{search.get("duration")}`',
                                    inline=False)
                embed.add_field(name='\u200b', value='**Reply `cancel` to cancel search.**', inline=False)

        msg = await ctx.reply(embed=embed)

        def check(message):
            return message.author == ctx.author and (message.content in numbers or message.content == 'cancel')

        try:
            confirmation = await self.bot.wait_for('message', check=check, timeout=30)
        except asyncio.TimeoutError:
            await msg.edit(content='Timeout.', embed=None)
        else:
            if confirmation.content in numbers:
                await msg.delete()
                await ctx.invoke(self.bot.get_command('play'), url=results[int(confirmation.content) - 1].get('link'))
            else:
                await msg.delete()

    @commands.command(aliases=['fp'])
    async def force_play(self, ctx):
        """Force furret to play music in queue when it isn't playing.

        Usually used after furret encounter connection problem and
        it leave the voice channel without any reason.
        """

        queue = self.queues[ctx.guild.id]
        queue.play()

    @commands.command(aliases=['q'])
    async def queue(self, ctx):
        """Shows queue"""

        queue = self.queues[ctx.guild.id]
        if ctx.voice_client is None:
            await ctx.reply('**Furret is not playing anything.**')
        else:
            msg = await ctx.reply(embed=queue.create_embed())
            if (max_page := math.ceil((len(queue) - 1) / 10)) > 1:
                current_page = 1
                await msg.add_reaction('⬅️')
                await msg.add_reaction('➡️')

                def check(reaction, user):
                    return not user.bot and reaction.emoji in ('⬅️', '➡️')

                stop = False
                while not stop:
                    try:
                        reaction, user = await self.bot.wait_for('reaction_add', timeout=10, check=check)
                    except asyncio.TimeoutError:
                        await msg.clear_reactions()
                        stop = True
                    else:
                        await reaction.remove(user)
                        if reaction.emoji == '⬅️' and current_page != 1:
                            current_page -= 1
                            await msg.edit(embed=queue.create_embed(current_page))
                        elif reaction.emoji == '➡️' and current_page != max_page:
                            current_page += 1
                            await msg.edit(embed=queue.create_embed(current_page))

    @commands.command()
    async def volume(self, ctx, volume: int):
        """Changes the song's volume"""

        if ctx.voice_client is None:
            return await ctx.reply("**Not connected to a voice channel.**")

        ctx.voice_client.source.volume = volume / 100
        await ctx.reply("**Changed volume to {}%**".format(volume))

    @commands.command()
    async def shuffle(self, ctx):
        """Shuffles the queue"""

        queue = self.queues[ctx.guild.id]
        await ctx.reply(queue.shuffle())

    @commands.command()
    async def clear(self, ctx):
        """Clears the queue"""
        queue = self.queues[ctx.guild.id]

        await ctx.reply(queue.clear())

    @commands.command()
    async def pause(self, ctx):
        """Pauses the bot"""

        if not ctx.voice_client.is_paused():
            ctx.voice_client.pause()
            await ctx.reply('**Paused.**')
        elif ctx.voice_client.is_paused():
            await ctx.reply('**Already paused.**')

    @commands.command()
    async def resume(self, ctx):
        """Resumes the bot"""

        if ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.reply('**Resumed.**')
        elif not ctx.voice_client.is_paused():
            await ctx.reply('**Already playing.**')

    @commands.command(aliases=['s'])
    async def skip(self, ctx):
        """Skip the current song"""

        ctx.voice_client.stop()
        await ctx.reply('**Skipped.**')

    @commands.command()
    async def loop(self, ctx, arg=None):
        """Loop queue"""

        queue = self.queues[ctx.guild.id]
        if not arg:
            await ctx.reply(f'Loop queue: {"on" if queue.loop_queue else "off"}\n'
                            f'Loop current song: {"on" if queue.loop_song else "off"}\n'
                            f'Specify `queue` or `song` to loop as the argument.')
        elif arg.lower() == 'queue':
            if queue.loop_queue:
                queue.loop_queue = False
                await ctx.reply('**Toggled off**')
            else:
                queue.loop_queue = True
                await ctx.reply('**Toggled on**')
        elif arg.lower() == 'song':
            if queue.loop_song:
                queue.loop_song = False
                await ctx.reply('**Toggled off**')
            else:
                queue.loop_song = True
                await ctx.reply('**Toggled on**')

    @commands.command()
    async def move(self, ctx, song_index: int, new_index: int):
        """Moves song in a specific position to another position"""

        queue = self.queues[ctx.guild.id]
        await ctx.reply(queue.move_song(song_index=song_index, new_index=new_index))

    @commands.command()
    async def remove(self, ctx, song_index: int):
        """Removes song in a specific position"""

        queue = self.queues[ctx.guild.id]

        removed = queue.remove_song_at_index(song_index)
        if removed is not None:
            await ctx.reply(f'**Removed** `{removed.title}`')
        else:
            await ctx.reply(f'**There\'s no song in position** `{song_index}`')

    @commands.command()
    async def stop(self, ctx):
        """Stops and disconnects the bot from voice"""

        queue = self.queues[ctx.guild.id]

        queue.stop()
        await ctx.voice_client.disconnect()

    @commands.command()
    async def fuck(self, ctx, command):
        if command == 'off':
            await ctx.invoke(self.bot.get_command('stop'))

    @play.before_invoke
    @search.before_invoke
    async def ensure_voice(self, ctx):
        queue = self.queues[ctx.guild.id]
        if ctx.author.voice:
            if ctx.voice_client is None:
                queue.vc = await ctx.author.voice.channel.connect()
        else:
            await ctx.reply("**You are not connected to a voice channel.**")
            raise commands.CommandError("**Author not connected to a voice channel.**")
        # elif ctx.voice_client.is_playing:
        #     ctx.voice_client.stop()


def setup(client):
    client.add_cog(Music(client))
