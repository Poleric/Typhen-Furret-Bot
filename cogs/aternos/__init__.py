from cogs.aternos.server import Aternos, Server
from cogs.aternos.exceptions import *

from discord.ext import commands


class Minecraft(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.aternos = Aternos('15kpzep3DVMpFTLBfkqEWwtbCuuj3FkBYytLRN53k5GvzQZidAMXh9gGGU0B7G6Coepq4wM3HGzBIwUJoXwPLNeeLqKiLNLfECs7')

    @property
    def servers(self) -> list[Server]:
        return self.aternos.servers

    @commands.group(aliases=['mc'])
    async def minecraft(self, ctx):
        if not ctx.invoked_subcommand:
            await ctx.reply(embed=self.aternos.embed)

    @minecraft.group()
    async def status(self, ctx, server: int = None):
        if not server:
            await ctx.reply(embed=self.aternos.embed)

        try:
            await ctx.reply(embed=self.aternos[server - 1].embed)
        except IndexError:
            await ctx.reply('Server does not exist')

    @minecraft.group()
    async def start(self, ctx, server: int):
        try:
            async def remind():
                await ctx.reply('Server\'s online')

            success = self.aternos[server - 1].start(remind)
            if success:
                await ctx.reply('Server\'s starting')
        except IndexError:
            await ctx.reply('Server does not exist')
        except ServerNotOffline:
            await ctx.reply('Server is not offline')

    @minecraft.group(aliases=['close'])
    async def stop(self, ctx, server: int):
        try:
            success = self.aternos[server - 1].stop()
            if success:
                await ctx.reply('Server\'s stopping')
        except IndexError:
            await ctx.reply('Server does not exist')
        except ServerNotOnline:
            await ctx.reply('Server is not online')

    @minecraft.group()
    async def restart(self, ctx, server: int):
        try:
            async def remind():
                await ctx.reply('Server\'s online')

            success = self.aternos[server - 1].restart(remind)
            if success:
                await ctx.reply('Server\'s restarting')
        except IndexError:
            await ctx.reply('Server does not exist')
        except ServerNotOnline:
            await ctx.reply('Server is not online')


def setup(bot):
    bot.add_cog(Minecraft(bot))
