from cogs.aternos.server import Servers, Server
from cogs.aternos.classes import Online, Offline, Crashed, WaitingInQueue
from cogs.aternos.exceptions import *

from discord import Embed
from discord.ext import commands


class Minecraft(commands.Cog):
    def __init__(self, bot, session_id):
        self.bot = bot
        self._aternos = Servers(session_id)

    def server_list_embed(self) -> Embed:
        embed = Embed(title='List of servers')
        for i, server in enumerate(self._aternos.servers, start=1):
            embed.add_field(name='\u200b', value=f'`{i}.` {server.ip} | `{server.status}`', inline=False)
        return embed

    def server_embed(self, num) -> Embed:
        server = self._aternos[num]

        status = server.status
        embed = Embed(title=server.ip, color=status.COLOR)
        embed.add_field(name='Status', value=str(status))

        match status:
            case Online():
                embed.add_field(name='Players', value=server.player_count)
            case WaitingInQueue():
                embed.add_field(name='EST', value=status.est)

        embed.add_field(name='Software', value=f'{server.software} {server.version}')
        return embed

    @commands.group(aliases=['minecraft', 'mc'])
    async def aternos(self, ctx):
        """Aternos commands

        commands
        status [<server num>] - show server status
        start [<server num>] - start server
        stop [<server num>] - close server
        restart [<server num>] - restart server
        players [<server num>] - shows players
        """

        if not ctx.invoked_subcommand:
            await ctx.reply(embed=self.server_list_embed())

    @aternos.command(aliases=['info'])
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
            await ctx.reply(embed=self.server_list_embed())
            return

        try:
            await ctx.reply(embed=self.server_embed(server))
        except IndexError:
            await ctx.reply('Server does not exist')

    @aternos.command(aliases=['open', 'on'])
    async def start(self, ctx, server: int = None):
        """Start server. Reminds when server's online"""

        if not server:
            await ctx.reply('Specify a server number to start')
            return

        try:
            # Disabling callback temporarily to reduce frequency of requests
            # async def remind(server_status: bool):
            #     match server_status:
            #         case Online():
            #             await ctx.reply('Server\'s online')
            #         case Crashed():
            #             await ctx.reply('Server crashed')
            #         case Offline():
            #             await ctx.reply('Server went offline, something went wrong')

            success = self._aternos[server].start()
            if success:
                await ctx.reply('Server\'s starting')
        except IndexError:
            await ctx.reply('Server does not exist')
        except ServerNotOffline:
            await ctx.reply('Server is not offline')

    @aternos.command(aliases=['close', 'off'])
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

    @aternos.command(aliases=['reset'])
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

    @aternos.command(aliases=['player'])
    async def players(self, ctx, server: int):
        """Shows the exact players name and status of a server"""

        server = self._aternos[server]
        if not isinstance(server.status, Online):
            await ctx.reply('Server\'s not online')
            return

        players = '\n'.join(f'{player.username} | `{player.status}`' for player in server.players)
        if not players:
            players = 'No players online'

        embed = Embed(title=server.ip, description=players)
        await ctx.reply(embed=embed)


def setup(bot):
    # hardcoded session id TODO: make config file
    session_id = ''
    bot.add_cog(Minecraft(bot, session_id))
