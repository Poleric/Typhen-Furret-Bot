import os
import traceback
import json

import datetime

import discord
from discord import Intents
from discord.ext import commands
from discord.ext.commands import is_owner
from discord.ext.commands import CommandNotFound
from discord.ext.commands.errors import ExtensionNotLoaded
from discord.ext.commands.errors import ExtensionAlreadyLoaded
from discord.ext.commands.errors import ExtensionFailed

with open('./config/server.json', 'r') as data:
    server_config = json.load(data)

bot = commands.Bot(command_prefix=commands.when_mentioned_or(server_config['prefix']),
                   intents=Intents.all(),
                   status=discord.Status.online,
                   activity=discord.Game('Pokémon | {}help'.format(server_config['prefix'])))


"""Commands"""


@bot.event
async def on_ready():
    """Trigger when bot is online"""

    print(f'Bot is logged in as\n'
          f'name: {bot.user.name}\n'
          f'id: {bot.user.id}\n'
          f'on {datetime.datetime.now()}')


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, CommandNotFound):
        return
    else:
        raise error


@bot.command()
@is_owner()
async def load(ctx, extension):
    """Load local extension(s)"""

    # load all
    if extension.lower() == 'all':
        for file in os.listdir('./cogs'):
            try:
                if file.endswith('.py'):
                    bot.load_extension(f'cogs.{file[:-3]}')
            except ExtensionAlreadyLoaded:
                pass
        await ctx.send('Loaded all extensions')

    # load {any}
    else:
        bot.load_extension(f'cogs.{extension}')
        await ctx.send('Loaded {}.py'.format(extension))


@bot.command()
@is_owner()
async def unload(ctx, extension):
    """Unload local extension(s)"""

    # unload all
    if extension.lower() == 'all':
        for file in os.listdir('./cogs'):
            try:
                if file.endswith('.py'):
                    bot.unload_extension(f'cogs.{file[:-3]}')
            except ExtensionNotLoaded:
                pass
        await ctx.send('Unloaded all extensions')

    # unload {any}
    else:
        bot.unload_extension(f'cogs.{extension}')
        await ctx.send('Unloaded {}.py'.format(extension))


@bot.command()
@is_owner()
async def reload(ctx, extension):
    """Reload local extension(s)"""

    # reload all
    if extension.lower() == 'all':
        not_loaded = str()
        for file in os.listdir('./cogs'):
            try:
                if file.endswith('.py'):
                    bot.unload_extension(f'cogs.{file[:-3]}')
                    bot.load_extension(f'cogs.{file[:-3]}')
            except ExtensionNotLoaded:
                not_loaded += file
        if len(not_loaded) > 0:
            await ctx.send('Reloaded all except {}'.format(not_loaded))
        else:
            await ctx.send('Reloaded all extensions')

    # reload {any}
    else:
        bot.unload_extension(f'cogs.{extension}')
        bot.load_extension(f'cogs.{extension}')
        await ctx.send('Reloaded {}.py'.format(extension))


"""Initialization"""


# Load all cogs on start
ignore = ['']
for file in os.listdir('./cogs/'):
    try:
        if file.endswith('.py') and not file.startswith('.'):
            bot.load_extension('cogs.{}'.format(file[:-3]))
    except ExtensionFailed:
        traceback.print_exc()

# Write commands and aliases list into server.json
commands = list()
for command in bot.commands:
    commands.append(command.name)
    for alias in command.aliases:
        commands.append(alias)

with open('./config/server.json', 'w') as f:
    server_config['commands'] = commands
    json.dump(server_config, f, indent=2)

# Read token from local file and run bot
with open('token.txt', 'r') as f:
    bot.run(f.read())
