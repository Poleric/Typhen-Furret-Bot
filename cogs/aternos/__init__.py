from cogs.aternos.server import Aternos, Server
from cogs.aternos.exceptions import *

from discord.ext import commands


class Minecraft(commands.Cog):
    def __init__(self, bot, session_id):
        self.bot = bot
        self.aternos = Aternos(session_id)

    @property
    def servers(self) -> list[Server]:
        return self.aternos.servers

    @commands.group(aliases=['mc'])
    async def minecraft(self, ctx):
        if not ctx.invoked_subcommand:
            await ctx.reply(embed=self.aternos.embed)

    @minecraft.group(aliases=['info'])
    async def status(self, ctx, server: int = None):
        if not server:
            await ctx.reply(embed=self.aternos.embed)
            return

        try:
            await ctx.reply(embed=self.aternos[server].embed)
        except IndexError:
            await ctx.reply('Server does not exist')

    @minecraft.group(aliases=['open', 'on'])
    async def start(self, ctx, server: int = None):
        if not server:
            await ctx.reply('Specify a server number to start')
            return

        try:
            async def remind():
                await ctx.reply('Server\'s online')

            success = self.aternos[server].start(remind)
            if success:
                await ctx.reply('Server\'s starting')
        except IndexError:
            await ctx.reply('Server does not exist')
        except ServerNotOffline:
            await ctx.reply('Server is not offline')

    @minecraft.group(aliases=['close', 'off'])
    async def stop(self, ctx, server: int = None):
        if not server:
            await ctx.reply('Specify a server number to stop')
            return

        try:
            success = self.aternos[server].stop()
            if success:
                await ctx.reply('Server\'s stopping')
        except IndexError:
            await ctx.reply('Server does not exist')
        except ServerNotOnline:
            await ctx.reply('Server is not online')

    @minecraft.group(aliases=['reset'])
    async def restart(self, ctx, server: int = None):
        if not server:
            await ctx.reply('Specify a server number to restart')
            return

        try:
            async def remind():
                await ctx.reply('Server\'s online')

            success = self.aternos[server].restart(remind)
            if success:
                await ctx.reply('Server\'s restarting')
        except IndexError:
            await ctx.reply('Server does not exist')
        except ServerNotOnline:
            await ctx.reply('Server is not online')


def setup(bot):
    bot.add_cog(Minecraft(bot, 'vJNZi3yIpvR0ug0DeUUR828XoJ6cIH36Yrv4vUNevjamO1Tje31577A1rRaH3eHWGwBPa0Yxm6jKjSFVT8o2UQ8r3Go89JrzVUpa'))
