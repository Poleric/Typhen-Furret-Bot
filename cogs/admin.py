# Modules
import typing

# Classes
from datetime import datetime
from datetime import timedelta
from discord.ext import commands
from discord import VoiceChannel
from discord import Member
from discord.ext import tasks
from discord.ext.commands import Context

# Methods
from humanfriendly import format_timespan
from discord.ext.commands import has_permissions


class Silenced:

    def __init__(self, member: Member, start_time: datetime, duration: timedelta, container, afkVoiceChannel: VoiceChannel, reason):
        self.member = member
        self.start_time = start_time
        self.end_time = start_time + duration
        self.container = container
        self.ensureSilenced.start(afkVoiceChannel=afkVoiceChannel)
        self.reason = reason

    def __str__(self):
        return f'{self.member.name}#{self.member.discriminator}'

    @tasks.loop(seconds=0.3)
    async def ensureSilenced(self, afkVoiceChannel: VoiceChannel):
        if datetime.now() < self.end_time:
            if self.member.voice is not None and self.member.voice.channel != afkVoiceChannel:
                await self.member.move_to(afkVoiceChannel, reason=self.reason)
        else:
            del self.container[self.container.find(self.member)]


class SilencedList:

    def __init__(self, *detained):
        self.list = list(detained)

    def __iter__(self):
        return iter(self.list)

    def __getitem__(self, item):
        return self.list[item]

    def __delitem__(self, key):
        print('deleted')
        self.list[key].ensureSilenced.cancel()
        del self.list[key]

    def find(self, query: typing.Union[Member, str]):
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

    def add(self, member: Member, start_time: datetime, duration: timedelta, afkVoiceChannel: VoiceChannel, reason=None):
        if (index := self.find(member)) != -1:
            self[index].end_time += duration
        else:
            self.list.append(Silenced(member, start_time, duration, self, afkVoiceChannel, reason))

    def remove(self, query: typing.Union[Member, str]):
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

    def cog_unload(self):
        for silenced in self.silenced:
            silenced.ensureSilenced.cancel()

    @commands.command(aliases=['silence', 'jail'])
    @has_permissions(administrator=True)
    async def bonk(self, ctx: Context, mentions: commands.Greedy[typing.Union[Member, checkMentionEveryone]], duration: typing.Optional[convertToTime] = timedelta(seconds=30), *reason):
        """Lock mentioned member in the guild's inactive channel

        Default 30 seconds. Accepted affixes:
        s - seconds
        m - minutes
        h - hours
        d - days
        w - weeks
        y - years (365 years)
        """

        if ctx.guild.afk_channel:
            if ctx.message.mention_everyone:
                for member in ctx.guild.members:
                    now = datetime.now()
                    self.silenced.add(member, now, duration, ctx.guild.afk_channel, ' '.join(reason))
                await ctx.reply(f'***NUKE BONK!!!*** Everyone is bonked to {ctx.guild.afk_channel.mention}, for {format_timespan(duration.total_seconds())}')
            else:
                for member in mentions:
                    now = datetime.now()
                    self.silenced.add(member, now, duration, ctx.guild.afk_channel, ' '.join(reason))
                await ctx.reply(f'***BONK!!!*** Go to {ctx.guild.afk_channel.mention}, {", ".join(x.mention for x in mentions)} for {format_timespan(duration.total_seconds())}.')
        else:
            await ctx.reply('No inactive channel to send to.')

    @commands.command(aliases=['free'])
    async def release(self, ctx: Context, mentions: commands.Greedy[Member]):
        """Release mentioned member from the guild's inactive channel"""

        if ctx.message.mention_everyone:
            self.silenced.clear()
            await ctx.reply('Everyone is released.')
        else:
            released = []
            for member in mentions:
                if self.silenced.remove(member):
                    released.append(member)
            await ctx.reply(f'{", ".join(x.mention for x in released)} is released.')



def setup(client):
    client.add_cog(Administration(client))
