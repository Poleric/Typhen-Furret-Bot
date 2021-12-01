import os
import traceback
import json
import time
import logging
import socket
from discord import Intents, AllowedMentions, CustomActivity, Status, Game
from discord.ext.commands import is_owner, Bot, when_mentioned_or, has_permissions
from discord.ext.commands.errors import ExtensionNotLoaded, ExtensionFailed, ExtensionAlreadyLoaded, CommandNotFound, MissingRequiredArgument


logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(module)s]: %(message)s',
    datefmt='%H:%M:%S'
)


with open('bot.json', 'r') as data:
    bot_config = json.load(data)


def commit_config():
    with open('bot.json', 'w') as config:
        json.dump(bot_config, config)


# sleep until have network connection
# for startup scripts
while not socket.create_connection(("1.1.1.1", 53)):  # while cant establish connection
    time.sleep(1)

bot = Bot(command_prefix=when_mentioned_or(bot_config['prefix']),
          intents=Intents.all(),
          status=Status.online,
          activity=Game(f'Pokémon | {bot_config["prefix"]}help'),
          allowed_mentions=AllowedMentions(replied_user=False))


def _load(extension):
    bot.load_extension(f'cogs.{extension}')


def _unload(extension):
    bot.unload_extension(f'cogs.{extension}')


def _reload(extension):
    try:
        _unload(extension)
    except ExtensionNotLoaded:
        pass
    _load(extension)


@bot.event
async def on_ready():
    """Called when bot is connected"""
    logging.info(f'Logged in as {bot.user}')


@bot.event
async def on_command_error(ctx, exc, force=False):
    """Quietly handles unknown commands"""
    if not force and ctx.cog and ctx.cog.qualified_name == 'Aternos':
        return

    match exc:
        case CommandNotFound() | MissingRequiredArgument():
            pass
        case _:
            logging.error(
                f'Ignoring exception in command {ctx.command}:\n'
                f'{"".join(traceback.format_exception(type(exc), exc, exc.__traceback__))}'
            )


@bot.command()
@is_owner()
async def clear_console(_):
    """Clear console"""

    os.system('cls' if os.name == 'nt' else 'clear')


@bot.command()
@is_owner()
async def load(ctx, extension):
    """Load local extension(s)"""

    try:
        _load(extension)
        await ctx.reply(f'Loaded {extension}.py')
    except ExtensionAlreadyLoaded:
        await ctx.reply(f'{extension}.py is already loaded')


@bot.command()
@is_owner()
async def unload(ctx, extension):
    """Unload local extension(s)"""

    try:
        _unload(extension)
        await ctx.reply(f'Unloaded {extension}.py')
    except ExtensionNotLoaded:
        await ctx.reply(f'{extension}.py is not loaded')


@bot.command()
@is_owner()
async def reload(ctx, extension):
    """Reload local extension(s)"""

    _reload(extension)
    await ctx.reply(f'Reloaded {extension}.py')
        

@bot.command()
async def ping(ctx):
    """Ping the bot"""

    await ctx.reply(f'Pong! {round(bot.latency * 1000)}ms')


@bot.command()
@has_permissions(manage_roles=True)
async def prefix(ctx, prefix):
    bot.command_prefix = prefix
    bot_config['prefix'] = prefix
    commit_config()
    await bot.change_presence(activity=CustomActivity(name=f'Pokémon | {prefix}help'))
    await ctx.reply(f'Prefix changed to `{bot.command_prefix}`')


# Initialise all local cogs on start
for folder in os.listdir('./cogs'):
    try:
        if os.path.isdir(f'./cogs/{folder}'):
            _load(folder)
    except ExtensionFailed:
        logging.exception('')


# Read token
with open('token', 'r') as f:
    token = f.read()

bot.run(token)
