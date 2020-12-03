import json

import random

import aiofiles

import discord
from discord import File
from discord import Embed
from discord.ext import commands
from discord.ext.commands import has_permissions
from discord.ext.commands import MissingPermissions
from discord.ext.commands.errors import MissingRequiredArgument


class Fun(commands.Cog):

    def __init__(self, client):
        self.bot = client
        with open('./config/server.json', 'r') as data:
            self.server_config = json.load(data)

        with open('./config/fun.json', 'r') as data:
            self.config = json.load(data)

    @commands.Cog.listener()
    async def on_ready(self):

        # Read a list of commands and prefixes
        with open('./config/server.json', 'r') as data:
            self.server_config = json.load(data)

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):

        # Check author is bot or not
        if not msg.author.bot:

            """Reply Bot"""

            if self.config['reply bot']:
                reply = False

                # Check whether message starts with bot prefix
                if not msg.content.startswith(self.server_config['prefix']):
                    reply = True
                else:

                    # Check if the next word is in the commands and aliases list
                    if not msg.content.split()[1] in self.server_config['commands']:
                        reply = True

                if reply:

                    # Randomly reply
                    if random.randint(1, 1000) <= 42:  # 4.2 %
                        if random.randint(1, 100) == 0:  # 1 %
                            await msg.channel.send('*happy furret noises*')
                        else:  # 4.2 %
                            await msg.channel.send(msg.content)

            """Angry Furret"""

            try:
                if (index := (msg_contents := msg.content.split()).index('furret')) >= 1:

                    # Find if cooking related word is before 'furret'
                    if msg_contents[index - 1] in self.config['trigger words']:

                        # Add user id to ["bad user"]
                        self.config["bad users"].append(msg.author.id)

            # Exception when trying to find 'furret' in a message without 'furret'
            except ValueError:
                pass

    @commands.command()
    @has_permissions(manage_messages=True)
    async def replybot(self, ctx: commands.Context):
        """Toggle on or off replybot function"""

        if not self.replybot:
            self.config['reply bot'] = True
            with open('./config/fun.json', 'w') as f:
                json.dump(self.config, f, indent=2)
            await ctx.send('Replybot toggled on')
        else:
            self.config['reply bot'] = False
            with aiofiles.open('./config/fun.json', 'w') as f:
                json.dump(self.config, f, indent=2)
            await ctx.send('Replybot toggled off')

    @replybot.error
    async def replybot_error(self, ctx, error):

        # Missing Permission
        if isinstance(error, MissingPermissions):
            await ctx.send("{} ignored orders!".format('Furret'))

    @commands.command()
    async def send(self, ctx: commands.Context, num: str, *, msg: str = None):
        """Makes furret say whatever you want
        You can specify how many times you want it to repeat
        by typing a number before the sentence.
        Max: 20 times.
        """

        if num.isdecimal():
            if int(num) > 20:
                num = 20
            for i in range(int(num)):
                await ctx.send(msg)
        else:
            if msg is None:
                await ctx.send(num)
            else:
                await ctx.send(f'{num} {msg}')

    @commands.command()
    async def approval(self, ctx: commands.Context):
        """Get approval from furret"""

        # Check whether author have antagonized furret before
        if ctx.author.id in self.config['bad users']:
            await ctx.send(random.choice(self.config['choices']['bad'] + self.config['choices']['very bad']))
            del self.config['bad users'][self.config['bad users'].index(ctx.author.id)]
        else:
            await ctx.send(random.choice(self.config['choices']['good'] + self.config['choices']['bad']))

    @commands.command(aliases=['uwu', 'uwo', 'owu'])
    async def owo(self, ctx: commands.Context, *, msg: str):
        """Owo-fy any words or sentences"""

        translated = ""
        for letter in msg:
            fuwwy_faces = [' OwO', ' UwU', ' :3', '']
            if letter in "lr":
                translated += "w"
            elif letter in "LR":
                translated += "W"
            elif letter in "h":
                translated += "hw"
            elif letter in "H":
                translated += "Hw"
            elif letter in ".,":
                translated += random.choice(fuwwy_faces) + letter
            else:
                translated += letter
        await ctx.send(translated)

    @owo.error
    async def owo_error(self, ctx: commands.Context, error):

        # Missing Argument (msg)
        if isinstance(error, MissingRequiredArgument):
            owo_help = Embed(title='owo command', description='OwO-fy any message after the command', color=0xf0d4b1)
            with open('./config/server.json', 'r') as data:
                self.server_config = json.load(data)
            owo_help.add_field(name='Syntax', value='{}owo [message]'.format(self.server_config['prefix']), inline=True)
            await ctx.send(embed=owo_help)

    @commands.command(aliases=['hewwo', 'hello', 'hi'])
    async def greet(self, ctx: commands.Context):
        """Greet furret"""

        greets = ['Hewwo!', 'Hi', 'Hello']
        await ctx.send(random.choice(greets))

    @commands.command(aliases=['goobye', 'bye'])
    async def farewell(self, ctx: commands.Context):
        """Say goodbye to furret"""

        farewells = ['Goodbye!', 'Cya!', 'Bye!']
        await ctx.send(random.choice(farewells))

    @commands.command(aliases=['walk'])
    async def walcc(self, ctx: commands.Context, suffix: str = None):
        """Furret will walk

        You can specify how you want furret to walk by specifying
        suffix after the command
        1. 'gif' - normal walcc
        2. 'gif2' - hypersonic walcc
        3. 'emote' - walcc emote
        """

        if suffix is not None and suffix.lower() in ('gif', 'gif2', 'emote', 'c', 'e', 'f'):
            if suffix.lower() == 'gif':
                await ctx.send(file=File('./media/furret_walcc.gif'))
            elif suffix.lower() == 'gif2':
                await ctx.send('https://tenor.com/view/furret-walk-fast-speed-space-gif-17881426')
            elif suffix.lower() == 'emote':
                await ctx.send('<a:walk:776008302210973707>' * random.randint(1, 10))
            elif suffix.lower() == 'c':
                await ctx.send(f'{"<a:walk:776008302210973707>" * 6}\n'
                               f'{"<a:walk:776008302210973707>" * 6}\n'
                               f'{"<a:walk:776008302210973707>" * 2}\n'
                               f'{"<a:walk:776008302210973707>" * 2}\n'
                               f'{"<a:walk:776008302210973707>" * 2}\n'
                               f'{"<a:walk:776008302210973707>" * 2}\n'
                               f'{"<a:walk:776008302210973707>" * 2}\n'
                               f'{"<a:walk:776008302210973707>" * 2}\n'
                               f'{"<a:walk:776008302210973707>" * 6}\n'
                               f'{"<a:walk:776008302210973707>" * 6}\n')
            elif suffix.lower() == 'e':
                await ctx.send(f'{"<a:walk:776008302210973707>" * 6}\n'
                               f'{"<a:walk:776008302210973707>" * 6}\n'
                               f'{"<a:walk:776008302210973707>" * 2}\n'
                               f'{"<a:walk:776008302210973707>" * 2}\n'
                               f'{"<a:walk:776008302210973707>" * 6}\n'
                               f'{"<a:walk:776008302210973707>" * 6}\n'
                               f'{"<a:walk:776008302210973707>" * 2}\n'
                               f'{"<a:walk:776008302210973707>" * 2}\n'
                               f'{"<a:walk:776008302210973707>" * 6}\n'
                               f'{"<a:walk:776008302210973707>" * 6}\n')
            elif suffix.lower() == 'f':
                await ctx.send(f'{"<a:walk:776008302210973707>" * 6}\n'
                               f'{"<a:walk:776008302210973707>" * 6}\n'
                               f'{"<a:walk:776008302210973707>" * 2}\n'
                               f'{"<a:walk:776008302210973707>" * 2}\n'
                               f'{"<a:walk:776008302210973707>" * 6}\n'
                               f'{"<a:walk:776008302210973707>" * 6}\n'
                               f'{"<a:walk:776008302210973707>" * 2}\n'
                               f'{"<a:walk:776008302210973707>" * 2}\n'
                               f'{"<a:walk:776008302210973707>" * 2}\n'
                               f'{"<a:walk:776008302210973707>" * 2}\n')
        else:
            if (r1 := random.randint(1, 3)) == 1:
                await ctx.send(file=File('./media/furret_walcc.gif'))
            elif r1 == 2:
                await ctx.send('https://tenor.com/view/furret-walk-fast-speed-space-gif-17881426')
            elif r1 == 3:
                await ctx.send('<a:walk:776008302210973707>' * random.randint(1, 10))


def setup(client):
    client.add_cog(Fun(client))
