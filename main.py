import os
import traceback
import json
import time
from datetime import datetime
import socket
import discord
from discord import Intents, AllowedMentions, CustomActivity
from discord.ext.commands import is_owner, Bot, when_mentioned_or, has_permissions, CommandNotFound
from discord.ext.commands.errors import ExtensionNotLoaded, ExtensionFailed, ExtensionAlreadyLoaded


with open('./config/bot.json', 'r') as data:
    bot_config = json.load(data)


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


activity_text = lambda x: f'Pokémon | {x}help'
bot = Bot(command_prefix=when_mentioned_or(bot_config['prefix']),
          intents=Intents.all(),
          status=discord.Status.online,
          activity=discord.Game(activity_text(bot_config['prefix'])),
          allowed_mentions=AllowedMentions(replied_user=False))


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

    # unload [cog_name]
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

    # reload [cog_name]
    else:
        bot.unload_extension(f'cogs.{extension}')
        bot.load_extension(f'cogs.{extension}')
        await ctx.send('Reloaded {}.py'.format(extension))
        

@bot.command()
async def ping(ctx):
    """Ping the bot"""

    await ctx.reply(f'Pong! {round(bot.latency * 1000)}ms')


@bot.command()
@has_permissions(manage_roles=True)
async def prefix(_, prefix):
    bot.command_prefix = prefix
    bot_config['prefix'] = prefix
    with open('bot.json', 'w') as f:
        f.write(bot_config)
    await bot.change_presence(activity=CustomActivity(name=activity_text(prefix)))


# Initialise all local cogs on start
for file in os.listdir('./cogs/'):
    try:
        if file.endswith('.py') and not file.startswith('.'):
            bot.load_extension('cogs.{}'.format(file[:-3]))
    except ExtensionFailed:
        traceback.print_exc()


# Read token
with open('token', 'r') as f:
    token = f.read()

bot.run(token)
