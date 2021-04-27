import json
import filetype
import io

from discord import Member, File
from discord.ext import commands
from discord.ext.commands import has_permissions, Context


class General(commands.Cog):

    def __init__(self, client):
        self.bot = client
        with open('./config/server.json', 'r') as data:
            self.server_config = json.load(data)

    @commands.Cog.listener()
    async def on_ready(self):

        # Read a list of commands and prefixes
        with open('./config/server.json', 'r') as data:
            self.server_config = json.load(data)

    @commands.command()
    async def ping(self, ctx: commands.Context):
        """Show latency"""

        await ctx.reply(f'Pong! {round(self.bot.latency * 1000)}ms')

    @commands.command()
    @has_permissions(manage_roles=True)
    async def prefix(self, ctx: Context, prefix: str):
        """Get or set bot's prefix"""

        self.server_config['prefix'] = prefix
        with open('./config/server.json', 'w') as f:
            json.dump(self.server_config, f, indent=2)
        self.bot.command_prefix = prefix
        await self.bot.change_presence(activity=discord.Game('Pokémon | {}help'.format(self.server_config['prefix'])))
        await ctx.reply('Prefix changed to {}'.format(self.server_config['prefix']))

    @commands.command()
    async def avatar(self, ctx: Context, member: Member = None):
        if not member:
            member: Member = ctx.author
        avatar = await member.avatar_url.read()
        extension = filetype.guess_extension(avatar)
        await ctx.reply(file=File(fp=io.BytesIO(avatar), filename=f'{member}.{extension}'))


def setup(client):
    client.add_cog(General(client))
