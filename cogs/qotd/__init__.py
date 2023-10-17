from discord import Message, Thread
from discord.ext import commands
from discord.ext.commands import Bot
import re

from cogs.qotd.classes import QOTD, QOTDs

THREAD_NAME_LENGTH_LIMIT = 100
QOTD_PATTERN = r" ?QOTD[: ]"
PIN_REASON = "QOTD"


def is_qotd(content: str) -> bool:
    return bool(re.match(QOTD_PATTERN, content, flags=re.IGNORECASE))


def trim_string_keep_words(string: str, n_chars: int, *, seperator: str = ' ') -> str:
    if len(string) <= n_chars:
        return string

    i = string.rfind(
        seperator,
        0,  # the start index
        n_chars  # the end index, does not include itself
    )  # find last seperator to trim off
    assert i < n_chars  # i would always be < n_chars

    if i < 0:  # the entire string is a single word.
        return string[:n_chars]
    return string[:i]


async def create_qotd_thread(msg: Message) -> Thread:
    stripped_content: str = msg.clean_content.strip()
    if len(stripped_content) > THREAD_NAME_LENGTH_LIMIT:
        stripped_content = trim_string_keep_words(stripped_content, THREAD_NAME_LENGTH_LIMIT - 3) + "..."

    return await msg.create_thread(name=stripped_content)


class QuestionOfTheDay(commands.Cog):
    qotd_channel_ids = [
        838658959626862662,  # qotd
        958968475349569558  # test
    ]

    def __init__(self, bot: Bot):
        self.bot: Bot = bot
        self.pinned_qotd = QOTDs(bot=bot)

    async def create_qotd(self, msg: Message):
        """Make message QOTD and schedule removal in a day"""
        await create_qotd_thread(msg)

        await msg.pin(reason=PIN_REASON)
        self.pinned_qotd.add(QOTD.from_message(msg))

    @commands.Cog.listener()
    async def on_message(self, msg: Message):
        if msg.channel.id in self.qotd_channel_ids \
                and is_qotd(msg.content):  # check if the message is a qotd
            await self.create_qotd(msg)


async def setup(bot):
    await bot.add_cog(QuestionOfTheDay(bot))
