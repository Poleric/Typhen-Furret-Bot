import json
from discord import Embed, Message
from discord.ext import commands


class BotFeatures(commands.Cog):

    def __init__(self, client):
        self.bot = client

    @commands.command()
    async def embed_to_dict(self, ctx, message: Message):
        for embed in message.embeds:
            await ctx.reply(json.dumps(embed.to_dict(), indent=2))

    @commands.command(aliases=['embed'])
    async def dict_to_embed(self, ctx, *, dictlike):
        json_acceptable = dictlike.replace("'", "\"").replace('True', 'true').replace('False', 'false')
        await ctx.reply(embed=Embed.from_dict(json.loads(json_acceptable)))


def setup(client):
    client.add_cog(BotFeatures(client))
