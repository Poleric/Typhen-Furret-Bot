# Modules
import json

# Classes
from discord.ext import commands
from discord.ext.commands import Context
from datetime import datetime

# Methods
from discord.ext.commands import is_owner


class Logging(commands.Cog):

    def __init__(self, client):
        self.bot = client

    @commands.command()
    @is_owner()
    async def archive(self, ctx: Context, message_amount: int = 100, include_bot_message: str = 'False'):
        def strToBool(str):
            if str in ('True', 'true'):
                return True
            elif str in ('False', 'false'):
                return False
            else:
                return str

        now = datetime.now()
        with open(f'{ctx.guild} {now.date()}.txt', 'a+', encoding="utf-8") as log:
            log.write(f'Archived at {now}\n')
            if strToBool(include_bot_message):
                async for message in ctx.channel.history(limit=message_amount if message_amount > 0 else None, oldest_first=True):
                    content = message.clean_content
                    for embed in message.embeds:
                        content += '\n' + json.dumps(embed.to_dict(), sort_keys=True, indent=4)
                    log.write(f'{message.created_at} {message.author}:\n{content}\n\n')
            else:
                def bot_filter(message):
                    return not message.author.bot

                async for message in ctx.channel.history(limit=message_amount if message_amount > 0 else None, oldest_first=True).filter(bot_filter):
                    content = message.clean_content
                    for embed in message.embeds:
                        content += '\n' + json.dumps(embed.to_dict(), sort_keys=True, indent=4)
                    log.write(f'{message.created_at} {message.author}:\n{content}\n\n')


def setup(client):
    client.add_cog(Logging(client))
