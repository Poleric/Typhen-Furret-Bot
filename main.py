import os
import traceback
import json
import time
from datetime import datetime
import socket
from discord import Intents, AllowedMentions, CustomActivity, Status, Game
from discord.ext.commands import is_owner, Bot, when_mentioned_or, has_permissions, CommandNotFound
from discord.ext.commands.errors import ExtensionNotLoaded, ExtensionFailed, ExtensionAlreadyLoaded


with open('bot.json', 'r') as data:
    bot_config = json.load(data)


def commit_config():
    with open('bot.json', 'w') as config:
        json.dump(bot_config, config)


def is_connected():
    try:
        # connect to the host -- tells us if the host is actually
        # reachable
        socket.create_connection(("1.1.1.1", 53))
        return True
    except OSError:
        pass
    return False


while not is_connected():
    time.sleep(1)

bot = Bot(command_prefix=when_mentioned_or(bot_config['prefix']),
          intents=Intents.all(),
          status=Status.online,
          activity=Game(f'Pokémon | {bot_config["prefix"]}help'),
          allowed_mentions=AllowedMentions(replied_user=False))


def _load(extension):
    bot.load_extension(f'cogs.{extension}.{extension}')


def _unload(extension):
    bot.unload_extension(f'cogs.{extension}.{extension}')


def _reload(extension):
    try:
        _unload(extension)
    except ExtensionNotLoaded:
        pass
    _load(extension)


@bot.event
async def on_ready():
    """Trigger when bot is online"""

    print(f'Bot is logged in as\n'
          f'name: {bot.user}\n'
          f'id: {bot.user.id}\n'
          f'on {datetime.now()}')


@bot.event
async def on_command_error(_, error):
    """Quietly handles unknown commands"""

    if isinstance(error, CommandNotFound):
        return
    print(f'\n[{datetime.now()}] [ERROR]')
    raise error


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
async def prefix(_, prefix):
    bot.command_prefix = prefix
    bot_config['prefix'] = prefix
    commit_config()
    await bot.change_presence(activity=CustomActivity(name=f'Pokémon | {prefix}help'))


# Initialise all local cogs on start
for folder in os.listdir('./cogs'):
    try:
        if os.path.isdir(f'./cogs/{folder}'):
            _load(folder)
    except ExtensionFailed:
        traceback.print_exc()


# Read token
with open('token', 'r') as f:
    token = f.read()

bot.run(token)
