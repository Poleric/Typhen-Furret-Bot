from discord import Embed
from wavelink import Queue, Playable, QueueMode

import itertools
import math
from .utils import md_embed_link, tm


class QueueEmbed:
    def __init__(self, queue: Queue):
        self.queue: Queue = queue

    @property
    def max_page(self) -> int:
        return math.ceil(len(self.queue) / 10) or 1

    @staticmethod
    def generate_row(song: Playable) -> str:
        """Returns string in the form of '[Song Name](Song Url) | `12:34`'"""

        return f"{md_embed_link(song.title, song.uri)} | " \
               f"`{tm.from_millis(song.length)}`"

    @staticmethod
    def queue_total_ms(queue: Queue) -> int:
        return sum(song.length for song in queue)

    def add_header(self, embed: Embed) -> None:
        """Generates and add the header in place, for the top page"""
        queue = self.queue

        if queue.loaded:
            embed.add_field(
                name="__Now Playing__",
                value=self.generate_row(queue.loaded),
                inline=False
            )
        else:
            embed.add_field(
                name="__Now Playing__",
                value="Nothing, try requesting a few songs",
                inline=False
            )

    def add_body(self, embed: Embed, page: int) -> None:
        header = "__Enqueued__"
        for i, song in enumerate(
                itertools.islice(self.queue, 10 * (page - 1), 10 * page),  # q[0:10] // q[10:20] // q[10(n-1):10n]
                start=10 * (page - 1) + 1
        ):
            embed.add_field(
                name=header,
                value=f"`{i}.` {self.generate_row(song)}",
                inline=False
            )

            header = "\u200b"

    def add_footer(self, embed: Embed, page: int) -> None:
        match self.queue.mode:
            case QueueMode.loop_all:
                loop = "Looping: Queue :repeat:"
            case QueueMode.loop:
                loop = "Looping: Song :repeat_one:"
            case _:
                loop = "No loop"

        embed.set_footer(
            text=f"Page {page}/{self.max_page} | "
                 f"{loop} | "
                 f"Duration: {tm.from_millis(self.queue_total_ms(self.queue))}"
        )

    def get_page(self, page: int) -> Embed:
        if page < 1 or page > self.max_page:
            raise IndexError(f"Page specified '{page}' does not exists. Max page available is '{self.max_page}'")

        embed = Embed(title="Queue", color=0x25fa30)
        if page == 1:
            self.add_header(embed)

        self.add_body(embed, page)

        self.add_footer(embed, page)

        return embed
