import configparser
import traceback
import logging
import os

from discord import Intents, Status, Game, AllowedMentions
from discord.ext.commands import Bot, when_mentioned_or, is_owner, has_permissions
from discord.ext.commands import ExtensionNotLoaded, ExtensionAlreadyLoaded, ExtensionFailed, CommandNotFound, MissingRequiredArgument


logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(module)s]: %(message)s',
    datefmt='%H:%M:%S'
)

config_file = 'bot.ini'
config = configparser.ConfigParser()
config.read(config_file)

token = config.get('Bot', 'token')
prefix = config.get('Bot', 'prefix').strip('"')
cog_path = config.get('Cogs', 'cog_path')

bot = Bot(command_prefix=when_mentioned_or(prefix),
          intents=Intents.all(),
          status=Status.online,
          activity=Game(f'Pokémon | {prefix}help'),
          allowed_mentions=AllowedMentions(replied_user=False))


def commit_config():
    with open(config_file, 'w') as f:
        config.write(f)


def load(ext):
    bot.load_extension(f'.{ext}', package=os.path.basename(cog_path))


def unload(ext):
    bot.unload_extension(f'.{ext}', package=os.path.basename(cog_path))


def reload(ext):
    try:
        unload(ext)
    except ExtensionNotLoaded:
        pass
    load(ext)


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


@bot.command(name='load')
@is_owner()
async def _load(ctx, extension):
    """Load local extension(s)"""
    try:
        load(extension)
        await ctx.reply(f'Loaded {extension}.py')
    except ExtensionAlreadyLoaded:
        await ctx.reply(f'{extension}.py is already loaded')


@bot.command(name='unload')
@is_owner()
async def _unload(ctx, extension):
    """Unload local extension(s)"""
    try:
        unload(extension)
        await ctx.reply(f'Unloaded {extension}.py')
    except ExtensionNotLoaded:
        await ctx.reply(f'{extension}.py is not loaded')


@bot.command(name='reload')
@is_owner()
async def _reload(ctx, extension):
    """Reload local extension(s)"""
    reload(extension)
    await ctx.reply(f'Reloaded {extension}.py')
        

@bot.command()
async def ping(ctx):
    """Ping the bot"""
    await ctx.reply(f'Pong! {round(bot.latency * 1000)}ms')


@bot.command()
@has_permissions(manage_roles=True)
async def prefix(ctx, prefix):
    """Changes the bot prefix"""
    bot.command_prefix = prefix  # update bot prefix

    # update config
    config['Bot']['prefix'] = f"'{prefix}'"
    commit_config()

    await bot.change_presence(activity=Game(name=f'Pokémon | {prefix}help'))
    await ctx.reply(f'Prefix changed to `{bot.command_prefix}`')


# Initialise all local cogs on start
for folder in os.listdir(cog_path):
    try:
        if os.path.isdir(f'{cog_path}/{folder}'):
            load(folder)
    except ExtensionFailed:
        logging.exception('')

bot.run(token)
