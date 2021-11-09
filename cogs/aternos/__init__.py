from cogs.aternos.server import Aternos, Server
from cogs.aternos.exceptions import *

from discord.ext import commands


class Minecraft(commands.Cog):
    def __init__(self, bot, session_id):
        self.bot = bot
        self._aternos = Aternos(session_id)

    @commands.group(aliases=['minecraft', 'mc'])
    async def aternos(self, ctx):
        """Aternos commands

        commands
        status [<server num>] - show server status
        start [<server num>] - start server
        stop [<server num>] - close server
        restart [<server num>] - restart server
        """

        if not ctx.invoked_subcommand:
            await ctx.reply(embed=self._aternos.embed)

    @aternos.group(aliases=['info'])
    async def status(self, ctx, server: int = None):
        """Show server status

        Shown info
        - server ip
        - online status
        - player count
        - server software
        - waiting time
        """

        if not server:
            await ctx.reply(embed=self._aternos.embed)
            return

        try:
            await ctx.reply(embed=self._aternos[server].embed)
        except IndexError:
            await ctx.reply('Server does not exist')

    @aternos.group(aliases=['open', 'on'])
    async def start(self, ctx, server: int = None):
        """Start server. Reminds when server's online"""

        if not server:
            await ctx.reply('Specify a server number to start')
            return

        try:
            async def remind():
                await ctx.reply('Server\'s online')

            success = self._aternos[server].start(remind)
            if success:
                await ctx.reply('Server\'s starting')
        except IndexError:
            await ctx.reply('Server does not exist')
        except ServerNotOffline:
            await ctx.reply('Server is not offline')

    @aternos.group(aliases=['close', 'off'])
    async def stop(self, ctx, server: int = None):
        """Close server"""

        if not server:
            await ctx.reply('Specify a server number to stop')
            return

        try:
            success = self._aternos[server].stop()
            if success:
                await ctx.reply('Server\'s stopping')
        except IndexError:
            await ctx.reply('Server does not exist')
        except ServerNotOnline:
            await ctx.reply('Server is not online')

    @aternos.group(aliases=['reset'])
    async def restart(self, ctx, server: int = None):
        """Restart server. Reminds when server's online"""

        if not server:
            await ctx.reply('Specify a server number to restart')
            return

        try:
            async def remind():
                await ctx.reply('Server\'s online')

            success = self._aternos[server].restart(remind)
            if success:
                await ctx.reply('Server\'s restarting')
        except IndexError:
            await ctx.reply('Server does not exist')
        except ServerNotOnline:
            await ctx.reply('Server is not online')


def setup(bot):
    # hardcoded session id TODO: make config file
    bot.add_cog(Minecraft(bot, 'vJNZi3yIpvR0ug0DeUUR828XoJ6cIH36Yrv4vUNevjamO1Tje31577A1rRaH3eHWGwBPa0Yxm6jKjSFVT8o2UQ8r3Go89JrzVUpa'))
