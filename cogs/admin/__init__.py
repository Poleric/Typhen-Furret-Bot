from typing import Optional, Union  # discordpy dont support pipe as union

# asyncio.sleep for nuke commands
import asyncio

# for bonk command
from datetime import timedelta
from humanfriendly import format_timespan
from cogs.admin.bonk import Bonked

from discord import TextChannel, VoiceChannel, Member, Role
from discord.ext import commands
from discord.ext.commands import has_permissions, Greedy
from discord.ext.commands import MissingPermissions


def time_format_to_timedelta(time_format) -> timedelta:
    time = int(time_format[:-1])
    time_format = time_format.casefold()

    if time_format.endswith('s'):
        seconds = time
    elif time_format.endswith('m'):
        seconds = time*60
    elif time_format.endswith('h'):
        seconds = time*3600
    elif time_format.endswith('d'):
        seconds = time*86400
    elif time_format.endswith('w'):
        seconds = time*604800
    elif time_format.endswith('M'):
        seconds = time*2592000
    elif time_format.endswith('y'):
        seconds = time*31536000
    elif time_format.endswith('D'):
        seconds = time*315360000
    elif time_format.endswith('c'):
        seconds = time*3153600000
    else:
        raise ValueError(f'Unsupported time format "{time_format[-1]}"')

    if seconds > timedelta.max.total_seconds():
        return timedelta.max
    return timedelta(seconds=seconds)


class Admin(commands.Cog):

    __slots__ = ('bot', 'bonked')

    def __init__(self, bot):
        self.bot = bot
        self.bonked = {}

    @commands.command()
    @has_permissions(administrator=True)
    async def nuke(self, ctx, channel: Optional[Union[TextChannel, VoiceChannel]] = None, countdown: int = 30):
        """Starts a nuke countdown in a channel for specified amount of time"""
        if channel is None:  # defaults to ctx.channel if channel is not specified
            channel = ctx.channel

        message = await channel.send(f'**NUKING CHANNEL IN {countdown} SECONDS**')
        for _ in range(countdown):
            await asyncio.sleep(1)
            countdown -= 1
            if countdown != 0:
                await message.edit(content=f'**NUKING CHANNEL IN {countdown} SECONDS**')
            else:
                await message.reply('*happy furret noises*')
        # await channel.delete(reason='Nuked')

    @commands.group()
    @has_permissions(administrator=True)
    async def bonk(self, ctx, mentions: Greedy[Union[Member, Role]], channel: Optional[VoiceChannel] = None, duration: Optional[time_format_to_timedelta] = timedelta(seconds=30), *, reason=''):
        """Lock mentioned members / roles in the server's inactive channel

        Default to 30 seconds. Time formats are (case sensitive):
        s - seconds
        m - minutes
        h - hours
        d - days
        w - weeks
        M - months (30 days)
        y - years (365 days)
        D - decades (10 years / 3650 days)
        c - centuries (100 years / 36500 days)  prob not good using centuries cuz idk by the time unbonked already dead

        max value is 999999999 days, 23 hours, 59 minutes, 59 seconds, and 999999 microseconds. Any higher will be defaulted to this value.
        """
        if ctx.invoked_subcommand:
            return

        if not channel:  # defaulting to guild's inactive channel if not specified
            if ctx.guild.afk_channel:
                channel = ctx.guild.afk_channel
            else:
                await ctx.reply('No channel to send to')
                return

        def silence(member):
            if member.id in self.bonked:
                self.bonked[member.id].add_time(duration)
            else:
                self.bonked[member.id] = Bonked(member, channel, duration, reason=reason)

        added = []
        for mention in mentions:
            match mention:
                case Member() as member:
                    if member.id == self.bot.user.id:  # for the lols
                        if len(mentions) == 1:
                            await ctx.reply('No, I don\'t think I will.')
                            return
                    else:
                        silence(member)
                        added.append(member)
                case Role():
                    for member in mention.members:
                        silence(member)
                        added.append(member)

        await ctx.reply(f'***BONK!!!*** Go to {channel.mention} {", ".join(x.mention for x in added)} for {format_timespan(duration.total_seconds())}')

    @bonk.command(name='list', aliases=['ls'])
    async def _list(self, ctx):
        if not self.bonked:
            await ctx.reply('No one was being naughty')
            return
        await ctx.reply('Bonked list:\n' '\n'.join(f'{v.member} - <t:{v.end_time.timestamp()}:R>' for v in self.bonked.values()))

    @commands.command(aliases=['release'])
    async def unbonk(self, ctx, mentions: Greedy[Member]):
        released = []
        for member in mentions:
            if member.id in self.bonked:
                self.bonked[member.id].unbonk()
                released.append(member)

        if released:
            await ctx.reply(f'{", ".join(x.mention for x in released)} is released.')
        else:
            await ctx.reply(f'{", ".join(x.mention for x in mentions)} is not bonked.')

    @bonk.error
    async def bonk_error(self, ctx, exc):
        match exc:
            case MissingPermissions():
                await ctx.reply('**You have no power here**')
            case _:
                raise exc

    @bonk.before_invoke
    @unbonk.before_invoke
    async def auto_clear(self, _ctx):
        for k, v in list(self.bonked.items()):
            if not v.bonked:
                del self.bonked[k]


def setup(bot):
    bot.add_cog(Admin(bot))
