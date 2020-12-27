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

    def __init__(self, member: Member, start_time: datetime, duration: timedelta, reason):
        self.member = member
        self.start_time = start_time
        self.end_time = start_time + duration
        self.reason = reason

    def __str__(self):
        return f'{self.member.name}#{self.member.discriminator}'

    @tasks.loop(seconds=0.2)
    async def ensureSilenced(self, afkVoiceChannel: VoiceChannel):
        if datetime.now() < self.end_time:
            if self.member.voice is not None and self.member.voice.channel != afkVoiceChannel:
                await self.member.move_to(afkVoiceChannel, reason=self.reason)
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
    async def bonk(self, ctx: Context, mention: str, duration: str = None, *, reason: str = None):
        """Lock mentioned member in the guild's inactive channel

        Default 30 seconds. Accepted affixes:
        s - seconds
        m - minutes
        h - hours
        d - days
        """
        if ctx.message.mentions:
            if ctx.guild.afk_channel:
                start_time = datetime.now()
                if duration:
                    if duration.isdecimal():
                        duration = timedelta(seconds=int(duration))
                    elif regex := re.match("\d+[smhd]", duration):
                        if (time := regex[0]).endswith('s'):
                            duration = timedelta(seconds=int(time[:-1]))
                        elif time.endswith('m'):
                            duration = timedelta(minutes=int(time[:-1]))
                        elif time.endswith('h'):
                            duration = timedelta(hours=int(time[:-1]))
                        elif time.endswith('d'):
                            duration = timedelta(days=int(time[:-1]))
                    else:
                        reason = f'{duration} {reason if reason else ""}'
                        duration = timedelta(seconds=30)
                else:
                    duration = timedelta(seconds=30)
                member = ctx.message.mentions[0]
                silenced = Silenced(member, start_time, duration, reason)
                self.silenced.append(silenced)
                silenced.ensureSilenced.start(afkVoiceChannel=ctx.guild.afk_channel)
                await ctx.send(f'***BONK!!!*** Go to {ctx.guild.afk_channel.mention}, {member.mention} for {format_timespan(duration.total_seconds())}.')
            else:
                await ctx.send("No inactive channel to send to.")
        else:
            await ctx.send('Who the hell ya wan me to bonk.')

    @commands.command(aliases=['free'])
    async def release(self, ctx: Context, *, mentions: str):
        """Release mentioned member from the guild's inactive channel"""

        for member in ctx.message.mentions:
            for index, silenced in enumerate(self.silenced):
                if silenced.member == member:
                    silenced.ensureSilenced.cancel()
                    released = self.silenced.pop(index)
                    await ctx.send(f'{released.member.mention} is released.')


def setup(client):
    client.add_cog(Administration(client))
