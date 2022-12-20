from cogs.game.minesweeper import Minesweeper
from discord.ext import commands


class Game(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def minesweeper(self, ctx, width: int = 10, height: int = 10, mines: int | float = 20, starting_row: int = None, starting_column: int = None):
        """Generate a minesweeper board"""
        # board = Minesweeper(width, height, mines=mines, starting_tile=(starting_row, starting_column) if starting_row and starting_column else None)
        # msg = ''
        # character_count = 0
        # for line in board.discord_board.split('\n'):
        #     character_count += len(line)
        #     if character_count < 1000:
        #         msg += line + '\n'
        #     else:
        #         await ctx.send(msg)
        #         character_count = 0
        #         msg = line + '\n'
        # await ctx.send(msg)


async def setup(bot):
    await bot.add_cog(Game(bot))
