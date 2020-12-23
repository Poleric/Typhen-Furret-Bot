# Modules
import re

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

    def __init__(self, member: Member, start_time: datetime, duration: timedelta):
        self.member = member
        self.start_time = start_time
        self.end_time = start_time + duration

    def __str__(self):
        return f'{self.member.name}#{self.member.discriminator}'

    @tasks.loop(seconds=0.2)
    async def ensureSilenced(self, afkVoiceChannel: VoiceChannel):
        if datetime.now() < self.end_time:
            if self.member.voice is not None and self.member.voice.channel != afkVoiceChannel:
                await self.member.move_to(afkVoiceChannel, reason='Silenced')
        else:
            self.ensureSilenced.cancel()


class Administration(commands.Cog):

    def __init__(self, client):
        self.bot = client
        self.silenced = list()

    def cog_unload(self):
        for silenced in self.silenced:
            silenced.ensureSilenced.cancel()

    @commands.command(aliases=['silence', 'jail'])
    @has_permissions(administrator=True)
    async def bonk(self, ctx: Context, *, mentions: str):
        """Lock mentioned member in the guild's inactive channel

        Default 30 seconds. Accepted affixes:
        s - seconds
        m - minutes
        h - hours
        d - days
        """

        start_time = datetime.now()
        duration = timedelta(seconds=30)
        time_str = mentions.split()[-1]
        if time_str.isdecimal():
            duration = timedelta(seconds=int(time_str))
        elif regex := re.match("\d+[smhd]", time_str):
            if (time := regex[0]).endswith('s'):
                duration = timedelta(seconds=int(time[:-1]))
            elif time.endswith('m'):
                duration = timedelta(minutes=int(time[:-1]))
            elif time.endswith('h'):
                duration = timedelta(hours=int(time[:-1]))
            elif time.endswith('d'):
                duration = timedelta(days=int(time[:-1]))

        for member in ctx.message.mentions:
            silenced = Silenced(member, start_time, duration)
            self.silenced.append(silenced)
            silenced.ensureSilenced.start(afkVoiceChannel=ctx.guild.afk_channel)
            await ctx.send(f'***BONK!!!*** Go to {ctx.guild.afk_channel.mention}, {member.mention} for {format_timespan(duration.total_seconds())}.')

    @commands.command(aliases=['free'])
    async def release(self, ctx: Context):
        """Release mentioned member from the guild's inactive channel"""

        for member in ctx.message.mentions:
            for index, silenced in enumerate(self.silenced):
                if silenced.member == member:
                    silenced.ensureSilenced.cancel()
                    released = self.silenced.pop(index)
                    await ctx.send(f'{released.member.mention} is released.')


def setup(client):
    client.add_cog(Administration(client))
