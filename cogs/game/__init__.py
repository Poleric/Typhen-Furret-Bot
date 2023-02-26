from cogs.game.minesweeper import Minesweeper
from discord.ext import commands
import numpy as np
from typing import Iterator


CHARACTER_LIMIT = 2000

def translate_board_on_dict(board: np.ndarray, dictionary: dict) -> np.ndarray:
    u, inv = np.unique(board, return_inverse=True)
    return np.array([dictionary.get(k, k) for k in u])[inv].reshape(board.shape)


class Game(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def minesweeper(self, ctx, width: int = 10, height: int = 10, mines: int | float = 20, starting_row: int = None, starting_column: int = None):
        """Generate a minesweeper board"""
        try:
            board = Minesweeper(width, height, mines=mines, starting_tile=(starting_row, starting_column) if starting_row and starting_column else None)
        except AssertionError as e:
            await ctx.reply(str(e))
            return

        d = {
            -1: "<:mine:892802868418084865>",
            0: "<:0_:892802357954506872>",
            1: "<:1_:892802370306711592>",
            2: "<:2_:892802426594291772>",
            3: "<:3_:892802448249487490>",
            4: "<:4_:892802462925324319>",
            5: "<:5_:892802477680914453>",
            6: "<:6_:892802488707735552>",
            7: "<:7_:892802499495485480>",
            8: "<:8_:892802509062697030>",
        }
        readable_board = translate_board_on_dict(board.board, d)

        def flatten_to_string(array: np.ndarray, *, wrapper: str) -> Iterator[str]:
            width = array.shape[1]
            for i, elem in enumerate(array.flatten(), start=1):
                yield f"{wrapper}{elem}{wrapper}"
                if i % width == 0:
                    yield "\n"

        final_msg = ""
        line = ""
        for msg in flatten_to_string(readable_board, wrapper="||"):
            line += msg

            if msg == "\n":
                if len(final_msg) + len(line) > CHARACTER_LIMIT:
                    await ctx.send(final_msg)
                    final_msg = ""

                final_msg += line
                line = ""
        await ctx.send(final_msg)

async def setup(bot):
    await bot.add_cog(Game(bot))
