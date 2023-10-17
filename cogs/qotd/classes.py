import dataclasses
from dataclasses import dataclass, field
import asyncio
import time

import json

from typing import IO
from discord import Message
from discord.ext.commands import Bot

A_DAY_IN_SECONDS = 10


@dataclass(slots=True, frozen=True)
class QOTD:
    msg_id: int
    channel_id: int
    created_time: int = field(default_factory=lambda: int(time.time()))  # in unix time, from time.time()

    @property
    def end_time(self) -> int:
        return self.created_time + A_DAY_IN_SECONDS

    @classmethod
    def from_message(cls, msg: Message):
        return cls(
            msg_id=msg.id,
            channel_id=msg.channel.id,
            created_time=int(msg.created_at.timestamp())
        )


class QOTDs(set):
    """Stores tuple pair of the QOTD and its unpin task"""

    def __init__(self, *args, bot: Bot, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot: Bot = bot  # needed to fetch message from its id

    async def unpin_task(self, qotd: QOTD):
        diff = qotd.end_time - time.time()
        await asyncio.sleep(diff)

        channel = await self.bot.fetch_channel(qotd.channel_id)
        msg: Message = await channel.fetch_message(qotd.msg_id)

        await msg.unpin()

    def add(self, qotd: QOTD, /) -> None:
        assert isinstance(qotd, QOTD)

        task = asyncio.create_task(self.unpin_task(qotd))

        elements = (qotd, task)
        super().add(elements)

        task.add_done_callback(lambda res: self.remove(elements))

    def save(self, fp: IO):
        # TODO: might be kinda suck for performance reason
        data = [dataclasses.asdict(d[0]) for d in self]
        json.dump(data, fp, indent=4)

    @classmethod
    def load_from_file(cls, fp: IO, *args, **kwargs):
        self: QOTDs = cls(*args, **kwargs)

        data = json.load(fp)
        for d in data:
            self.add(QOTD(**d))

        return self
