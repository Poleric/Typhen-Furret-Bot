from typing import Union, Optional
import json
from discord import Member, Message, TextChannel, Emoji, VoiceChannel, CategoryChannel, PermissionOverwrite, Role, Permissions
from typing import Mapping, Union, Tuple
from discord.ext import commands
from discord.ext.commands.errors import EmojiNotFound


class Test(commands.Cog):

    def __init__(self, client):
        self.bot = client

    @commands.command(hidden=True)
    async def test(self, ctx, channel: Union[TextChannel, VoiceChannel, CategoryChannel]):
        await ctx.reply(f'`{channel.name}` in `{channel.category}` @ position `{channel.position}`')
        for users, permissions in channel.overwrites.items():
            overwrites = {}
            perms = {}
            for permissionoverwrite in permissions.pair():
                for permission, value in permissionoverwrite:
                    perms[permission] = value
            overwrites[users.name] = perms
            await ctx.send(f'```{overwrites}```')

    @commands.command(hidden=True)
    async def react(self, ctx, message: Message, emote: Emoji):
        await message.add_reaction(emote)

    @commands.command(hidden=True)
    async def emote(self, ctx, channel: TextChannel, emote: Emoji):
        await channel.send(str(emote))

    @react.error
    @emote.error
    async def emote_error(self, ctx, error):
        if isinstance(error, EmojiNotFound):
            return
        else:
            raise error

    @commands.command(hidden=True)
    async def send_to(self, ctx, channel: Optional[TextChannel] = None, num: Optional[int] = 1, *, msg):
        for i in range(num):
            await channel.send(msg)


def setup(client):
    client.add_cog(Test(client))
