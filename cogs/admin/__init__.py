# Modules
import asyncio
from typing import Optional, Union

# Classes
from datetime import datetime, timedelta
from discord import Member, VoiceChannel, Role, TextChannel
from discord.ext import commands, tasks
from discord.ext.commands import Context, MissingPermissions

# Methods
from humanfriendly import format_timespan
from discord.ext.commands import has_permissions


class Silenced:

    def __init__(self, member: Member, voice_channel: VoiceChannel, reason, start_time=None, duration=timedelta(seconds=30), container=None):
        self.member = member
        self.start_time: datetime = start_time or datetime.now()
        self.end_time = self.start_time + duration
        self.container = container
        self.ensureSilenced.start(voice_channel=voice_channel)
        self.reason = reason

    def __str__(self):
        return f'{self.member.name}#{self.member.discriminator}'

    @tasks.loop(seconds=0.3)
    async def ensureSilenced(self, voice_channel: VoiceChannel):
        if datetime.now() < self.end_time:
            if self.member.voice is not None and self.member.voice.channel != voice_channel:
                await self.member.move_to(voice_channel, reason=self.reason)
        else:
            if self.container:
                del self.container[self.container.find(self.member)]


class SilencedList:

    def __init__(self, *detained):
        self.list = list(detained)

    def __iter__(self):
        return iter(self.list)

    def __getitem__(self, item):
        return self.list[item]

    def __delitem__(self, key):
        self.list[key].ensureSilenced.cancel()
        del self.list[key]

    def find(self, query: Union[Member, str]):
        """Returns index"""

        if isinstance(query, Member):
            for i, silenced in enumerate(self):
                if silenced.member == query:
                    return i
        elif isinstance(query, str):
            for i, silenced in enumerate(self):
                if str(silenced).startswith(query):
                    return i
        return -1

    def add(self, member: Member, start_time: datetime, duration: timedelta, voice_channel: VoiceChannel, reason=None):
        if (index := self.find(member)) != -1:
            self[index].end_time += duration
        else:
            self.list.append(Silenced(member, voice_channel, reason, start_time, duration, self))

    def remove(self, query: Union[Member, str]):
        if (index := self.find(query)) != -1:
            del self[index]
            return True
        else:
            return False

    def clear(self):
        for index, _ in enumerate(self):
            del self[index]


def convertToLower(string):
    return string.lower()


def convertToTime(abstract_time: convertToLower):
    if abstract_time.endswith('s'):
        duration = timedelta(seconds=int(abstract_time[:-1]))
    elif abstract_time.endswith('m'):
        duration = timedelta(minutes=int(abstract_time[:-1]))
    elif abstract_time.endswith('h'):
        duration = timedelta(hours=int(abstract_time[:-1]))
    elif abstract_time.endswith('d'):
        duration = timedelta(days=int(abstract_time[:-1]))
    elif abstract_time.endswith('w'):
        duration = timedelta(weeks=int(abstract_time[:-1]))
    elif abstract_time.endswith('y'):
        duration = timedelta(days=364*int(abstract_time[:-1]))
    else:
        raise ValueError
    return duration


def checkMentionEveryone(mention):
    if mention in ('@everyone', '@here'):
        return None
    else:
        raise Exception


class Administration(commands.Cog):

    def __init__(self, client):
        self.bot = client
        self.silenced = SilencedList()
        self.whitelist = list()

    def cog_unload(self):
        for silenced in self.silenced:
            silenced.ensureSilenced.cancel()

    @commands.command(aliases=['silence', 'jail'])
    @has_permissions(administrator=True)
    async def bonk(self, ctx: Context, mentions: commands.Greedy[Union[Member, Role, checkMentionEveryone]], channel: Optional[VoiceChannel] = None, duration: Optional[convertToTime] = timedelta(seconds=30), *reason):
        """Lock mentioned member in the guild's inactive channel

        Default 30 seconds. Accepted affixes:
        s - seconds
        m - minutes
        h - hours
        d - days
        w - weeks
        y - years (365 years)
        """

        if not channel:
            if ctx.guild.afk_channel:
                channel = ctx.guild.afk_channel
            else:
                await ctx.reply('No channel to send to.')
                return
        now = datetime.now()
        if ctx.message.mention_everyone:
            for member in ctx.channel.members:
                if member in self.whitelist:
                    pass
                else:
                    self.silenced.add(member, now, duration, channel, ' '.join(reason))
            await ctx.reply(f'***NUKE BONK!!!*** @everyone is bonked to {channel.mention}, for {format_timespan(duration.total_seconds())}')
        else:
            if mentions:
                for mention in mentions:
                    if isinstance(mention, Role):
                        for member in mention.members:
                            self.silenced.add(member, now, duration, channel, ' '.join(reason))
                    else:
                        self.silenced.add(mention, now, duration, channel, ' '.join(reason))
                await ctx.reply(f'***BONK!!!*** Go to {channel.mention}, {", ".join(x.mention for x in mentions)} for {format_timespan(duration.total_seconds())}.')

    @bonk.error
    async def bonk_error(self, ctx, error):
        error = error.original
        if isinstance(error, MissingPermissions):
            await ctx.reply('**You have no power here**')

    @commands.command(aliases=['free', 'release'])
    async def unbonk(self, ctx: Context, mentions: commands.Greedy[Member]):
        """Release mentioned member from the guild's inactive channel"""

        if ctx.message.mention_everyone:
            self.silenced.clear()
            await ctx.reply('Everyone is released.')
        else:
            if mentions:
                released = []
                for member in mentions:
                    if self.silenced.remove(member):
                        released.append(member)
                if released:
                    await ctx.reply(f'{", ".join(x.mention for x in released)} is released.')
                else:
                    await ctx.reply(f'{", ".join(x.mention for x in mentions)} is not bonked.')

    # @commands.command()
    # async def purge(self, ctx: Context, mention: Optional[Member] = None, limit: Optional[int] = 5):
    #     def is_user(m):
    #         return m.author == mention if mention else True
    #
    #     await ctx.message.delete()
    #     await ctx.channel.purge(limit=limit, check=is_user)

    @commands.command()
    @has_permissions(administrator=True)
    async def nuke(self, ctx: Context, channel: Optional[Union[TextChannel, VoiceChannel]] = None, countdown: Optional[int] = 30):
        if not channel:
            channel = ctx.channel
        message = await channel.send(f'**NUKING CHANNEL IN {countdown} SECONDS**')
        for _ in range(countdown):
            await asyncio.sleep(1)
            countdown -= 1
            await message.edit(content=f'**NUKING CHANNEL IN {countdown} SECONDS**')


def setup(client):
    client.add_cog(Administration(client))
