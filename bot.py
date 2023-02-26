import logging
from datetime import datetime
import os
import traceback
import json
import asyncio
from discord import Intents, Game, Message
from discord.ext.commands import Bot, is_owner, when_mentioned_or, has_permissions, \
    Context, \
    CommandError, CommandNotFound, ExtensionAlreadyLoaded, ExtensionNotLoaded, ExtensionFailed


def save_json_to(json_data: dict, path):
    with open(path, "w") as f:
        json.dump(json_data, f, indent=4)


def read_config(path):
    try:
        with open(path, "r") as f:
            conf = json.load(f)
    except FileNotFoundError:  # doesnt exists, generate default
        conf = {"prefix": {}}
        save_json_to(conf, path)
    return conf


conf = read_config("bot.json")
save_config = lambda: save_json_to(conf, "bot.json")
DEFAULT_PREFIX = "!"
DEFAULT_COG_PATH = r"./cogs"
DEFAULT_ACTIVITY_MESSAGE = "Pokemon | furret help"  # hardcoded lol
LOG_PATH = "./logs"


def get_prefix(bot: Bot, message: Message) -> list[str]:
    extras = conf["prefix"].get(str(message.guild.id), DEFAULT_PREFIX)
    return when_mentioned_or(extras)(bot, message)


bot = Bot(
    intents=Intents.all(),
    command_prefix=get_prefix,
    activity=Game(name=DEFAULT_ACTIVITY_MESSAGE)
)

#  setup logging
dt_fmt = '%H:%M:%S'
formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')

# file handlers
if not os.path.isdir(LOG_PATH):
    os.mkdir(LOG_PATH)
file_handler = logging.FileHandler(filename=f'{LOG_PATH}/{datetime.now():%Y-%m-%d_%H-%M-%S}.log', encoding='utf-8', mode='w')
file_handler.setFormatter(formatter)

# stream handlers setup, print to stdout
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
stream_handler.setLevel(logging.INFO)

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.addHandler(file_handler)
logger.addHandler(stream_handler)


@bot.event
async def on_ready():
    """Called when bot is connected"""
    logging.info(f'Logged in as {bot.user}')


@bot.event
async def on_command_error(ctx: Context, exc: CommandError):
    """Quietly handles unknown commands"""
    exc = getattr(exc, "original", exc)

    match exc:
        case CommandNotFound():
            pass
        case _:
            logging.error(
                f'Ignoring exception in command {ctx.command}:\n'
                f'{"".join(traceback.format_exception(type(exc), exc, exc.__traceback__))}'
            )


@bot.command()
@is_owner()
async def load(ctx: Context, ext: str):
    """Load local extension(s)"""
    try:
        await bot.load_extension(ext)
        await ctx.reply(f'Loaded {ext}')
    except ExtensionAlreadyLoaded:
        await ctx.reply(f'{ext} is already loaded')


@bot.command()
@is_owner()
async def unload(ctx: Context, ext: str):
    """Unload local extension(s)"""
    try:
        await bot.unload_extension(ext)
        await ctx.reply(f'Unloaded {ext}')
    except ExtensionNotLoaded:
        await ctx.reply(f'{ext} is not loaded')


@bot.command()
@is_owner()
async def reload(ctx: Context, ext: str):
    """Reload local extension(s)"""
    try:
        await bot.unload_extension(ext)
        await ctx.reply(f'Reloaded {ext}')
    except ExtensionNotLoaded:
        await ctx.reply(f"{ext} is not loaded, will be loaded.")
    await bot.load_extension(ext)


@bot.command()
async def ping(ctx: Context):
    """Ping the bot"""
    await ctx.reply(f'Pong! {round(bot.latency * 1000)}ms')


@has_permissions(manage_guild=True)
@bot.command()
async def prefix(ctx: Context, prefix: str):
    conf["prefix"][str(ctx.guild.id)] = prefix
    save_config()
    await ctx.reply(f"Server prefix changed to `{prefix}`")


async def main():
    # Initialise all local cogs on start
    for file in os.listdir(DEFAULT_COG_PATH):
        if file == "__pycache__":
            continue

        if not os.path.isdir(f"{DEFAULT_COG_PATH}/{file}") or file.endswith(".py"):
            continue

        try:
            # only works with files that end in .py or a directory
            await bot.load_extension(f"{os.path.basename(DEFAULT_COG_PATH)}.{os.path.basename(file)}")
        except ExtensionFailed as exc:
            logging.error(traceback.format_exception(type(exc), exc, exc.__traceback__))

    # For Windows, in the console: SET BOT_TOKEN=<ur_token_here>
    # For Linux, in the console: EXPORT BOT_TOKEN=<ur_token_here>
    token = os.getenv("BOT_TOKEN")
    await bot.start(token)

asyncio.run(main())
