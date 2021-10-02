import discord
from discord.ext import commands
from discord.ext.commands import MemberConverter
import re
import json
import random
import typing
from collections import defaultdict

from cogs.admin import Silenced


class Fun(commands.Cog):
    CONFIG_PATH = r'.\config\fun.json'

    def __init__(self, bot):
        self._bot = bot
        with open(self.CONFIG_PATH, 'r') as f:
            config = json.load(f)
            self._reply_rate: int = config['replybot']['reply_rate']
            self._blacklist: list[int] = config['replybot']['blacklist']
            self._choices: dict[str, list[str]] = config['choices']
            self._sin_counter: dict[str, int] = defaultdict(int, config['sin_counter'])

    async def _blacklisted(self, ctx):
        for channel_id in self._blacklist:
            channel = await commands.TextChannelConverter().convert(ctx, str(channel_id))
            yield channel

    def _commit(self):
        config = {
            'replybot': {
                'reply_rate': self._reply_rate,
                'blacklist': self._blacklist
            },
            'choices': self._choices,
            'sin_counter': self._sin_counter
        }
        with open(self.CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=4)

    @commands.Cog.listener()
    async def on_message(self, msg):
        # grab context from the message
        ctx = await self._bot.get_context(msg)

        if not msg.author.bot:  # check if message didn't invoke a command
            if re.match(r'(sorry |forgive me )?(father|furret).+(i have sinned)', msg.content.casefold()) and msg.author.voice:
                Silenced(msg.author, msg.guild.afk_channel, 'Sinner')
                await msg.reply(random.choice(['Very well.', 'Thy sins shalt not be forgiven.']))
                self._sin_counter[str(msg.author.id)] += 1
                self._commit()
            elif re.match(r'sorry daddy.+i.+been.+(bad|naughty)', msg.content.casefold()) and msg.author.voice:
                await msg.reply('For the last time, it\'s "Forgive me father, for I have sinned"')
            elif not ctx.valid:
                # replybot part
                if ctx.channel.id not in self._blacklist:
                    if random.random() < self._reply_rate:
                        if random.random() < 0.01:
                            await msg.channel.send('*happy furret noises*')
                        else:
                            await msg.channel.send(f'{msg.content}')

    @commands.group()
    async def replybot(self, ctx):
        """Replybot"""

        if not ctx.invoked_subcommand:
            # Reply rate - reply_rate * 100, and add '%'
            # Blacklists - joins all the channel mentions after using the converter to get the TextChannel object from ids
            await ctx.reply('Reply rate: `{reply_rate}%`\n'
                            'Blacklisted channels: {channels}'.format
                            (reply_rate=self._reply_rate * 100,
                             channels=' '.join([channel.mention async for channel in self._blacklisted(ctx)])))

    @replybot.command(aliases=['rate'])
    async def reply_rate(self, ctx, num_in_percentage: typing.Union[int | float]):
        """Change the rate at which replybot replies at

        Input the rate as numbers in percentage but without the percentage sign
        exp,
        1 = 1%
        0.1 = 0.1%
        """

        self._reply_rate = num_in_percentage / 100

        await ctx.reply(f'Changed to {num_in_percentage}%')

    @replybot.command()
    async def blacklist(self, ctx, channels: commands.Greedy[discord.TextChannel] = None):
        """Blacklist channels from replybot"""

        if not channels:  # if no channels is found
            channels = [ctx.channel]  # set current channel as channel

        blacklisted = list()
        for channel in channels:
            if channel.id not in self._blacklist:
                self._blacklist.append(channel.id)
                blacklisted.append(channel)

        await ctx.reply('Blacklisted {channels}'.format(channels=" ".join(channel.mention for channel in blacklisted)))

    @replybot.command()
    async def unblacklist(self, ctx, channels: commands.Greedy[discord.TextChannel] = None):
        """Unblacklist blacklisted channels from replybot"""

        if not channels:  # if no channels is found
            channels = [ctx.channel]  # set current channel as channel

        unblacklisted = list()
        for channel in channels:
            try:
                self._blacklist.remove(channel.id)
            except ValueError:
                pass
            else:
                unblacklisted.append(channel)

        await ctx.reply(
            'Unblacklisted {channels}'.format(channels=" ".join(channel.mention for channel in unblacklisted)))

    @reply_rate.after_invoke
    @blacklist.after_invoke
    @unblacklist.after_invoke
    async def commit_changes(self, _):
        self._commit()

    @commands.command(aliases=['say'])
    async def send(self, ctx, num: typing.Optional[int] = 1, *, msg: str):
        """Makes furret say whatever you want

        Yoy can optionally specify the amount of time to resend the message, up to 20
        """
        num = num if num <= 20 else 20

        for _ in range(num):
            await ctx.send(msg)

    @commands.command()
    async def approval(self, ctx):
        """Get furret's approval"""
        await ctx.reply(random.choice([*self._choices['good'], *self._choices['bad']]))

    @commands.command(aliases=['uwu', 'uwo', 'owu'])
    async def owo(self, ctx, *, msg: str):
        """Owo-fy any words or sentences"""

        translated = ""
        for letter in msg:
            uwu_faces = [' OwO', ' UwU', ' :3', '']
            if letter in "lr":
                translated += "w"
            elif letter in "LR":
                translated += "W"
            elif letter in "h":
                translated += "hw"
            elif letter in "H":
                translated += "Hw"
            elif letter in ".,":
                translated += random.choice(uwu_faces) + letter
            else:
                translated += letter
        await ctx.reply(translated)

    @commands.command()
    async def pick(self, ctx, num1: int, num2: int):
        """Let furret pick a random number between two number"""

        await ctx.reply(str(random.randint(num1, num2)))

    @commands.command(aliases=['choose'])
    async def choice(self, ctx, *choices):
        """Let furret choose from selections"""

        await ctx.reply(random.choice(choices))

    @commands.command(aliases=['hewwo', 'hello', 'hi'])
    async def greet(self, ctx):
        """Greet furret"""

        greets = ['Hewwo!', 'Hi', 'Hello']
        await ctx.reply(random.choice(greets))

    @commands.command(aliases=['goodbye', 'bye'])
    async def farewell(self, ctx):
        """Say goodbye to furret"""

        farewells = ['Goodbye!', 'Cya!', 'Bye!']
        await ctx.reply(random.choice(farewells))

    @commands.command(aliases=['walk'])
    async def walcc(self, ctx, suffix: str = None):
        """Furret will walk

        You can specify how you want furret to walk by specifying
        suffix after the command
        1. 'gif' - normal walcc
        2. 'gif2' - hypersonic walcc
        3. 'emote' - walcc emote
        """

        if suffix is not None and suffix.lower() in ('gif', 'gif2', 'emote', 'c', 'e', 'f'):
            if suffix.lower() == 'gif':
                await ctx.reply(file=discord.File('./media/furret_walcc.gif'))
            elif suffix.lower() == 'gif2':
                await ctx.reply('https://tenor.com/view/furret-walk-fast-speed-space-gif-17881426')
            elif suffix.lower() == 'emote':
                await ctx.reply('<a:walk:776008302210973707>' * random.randint(1, 10))
            elif suffix.lower() == 'c':
                await ctx.reply(f'{"<a:walk:776008302210973707>" * 6}\n'
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
                await ctx.reply(f'{"<a:walk:776008302210973707>" * 6}\n'
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
                await ctx.reply(f'{"<a:walk:776008302210973707>" * 6}\n'
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
                await ctx.reply(file=discord.File('./media/furret_walcc.gif'))
            elif r1 == 2:
                await ctx.reply('https://tenor.com/view/furret-walk-fast-speed-space-gif-17881426')
            elif r1 == 3:
                await ctx.reply('<a:walk:776008302210973707>' * random.randint(1, 10))

    @commands.command()
    async def sin_counter(self, ctx):
        desc_count: list = [(k, v) for k, v in sorted(self._sin_counter.items(), key=lambda x: x[1], reverse=True)]
        msg = ''
        converter = MemberConverter()
        for id, count in desc_count:
            msg += f'{await converter.convert(ctx=ctx, argument=id)} - {count}\n'
        await ctx.reply(msg)


def setup(client):
    client.add_cog(Fun(client))
