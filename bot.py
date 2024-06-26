import os
import asyncio

from discord import Intents, Game
from discord.ext.commands import Bot, Context, errors

from setup_logging import setup_logging
import logging
import traceback

logger = logging.getLogger("bot")

DEFAULT_PREFIX = "!"
DEFAULT_ACTIVITY_MESSAGE = "!help"
EXTENSIONS_TO_LOAD = (
    "cogs.admin",
    "cogs.fun",
    "cogs.game",
    "cogs.music",
    "cogs.qotd"
)


class Furret(Bot):
    def __init__(self, *args, **kwargs):
        setup_logging()
        super().__init__(*args, **kwargs)

    async def on_ready(self):
        logger.info(f"Logged in as {self.user}")

    async def on_command_error(self, ctx: Context, exc: errors.CommandError, /) -> None:
        logger.error(
            f'Ignoring exception in command {ctx.command}:\n'
            f'{"".join(traceback.format_exception(type(exc), exc, exc.__traceback__))}'
        )

    async def setup_hook(self) -> None:
        await self.autoload_extension()

    async def autoload_extension(self) -> None:
        for module in EXTENSIONS_TO_LOAD:
            await self.load_extension(module)


bot = Furret(
    intents=Intents.all(),
    command_prefix=DEFAULT_PREFIX,
    activity=Game(name=DEFAULT_ACTIVITY_MESSAGE)
)


@bot.command()
async def ping(ctx: Context):
    """Ping the bot"""
    await ctx.reply(f'Pong! {round(bot.latency * 1000)}ms')


async def main():
    token = os.getenv("DISCORD_BOT_TOKEN")
    await bot.start(token)


asyncio.run(main())
