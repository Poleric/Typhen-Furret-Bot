import numpy as np
from discord.ext import commands


class BaseBoard:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        # Create empty board
        self.board = np.array([[0 for _ in range(width)] for _ in range(height)])  # 0 - not mines, 1 - mines

    def coords_to_number(self, row: int, column: int) -> int:
        return row * self.width + column

    def number_to_coords(self, number: int) -> tuple:
        return divmod(number, self.width)

    def get_adjacent_tiles_coordinates(self, row, column):
        adjacent_coords = ((row - 1, column - 1), (row - 1, column), (row - 1, column + 1),
                           (row, column - 1), (row, column + 1),
                           (row + 1, column - 1), (row + 1, column), (row + 1, column + 1))

        def check_in_bounds(coordinates):
            row = coordinates[0]
            column = coordinates[1]
            if row < 0 or row >= self.height:
                return False
            if column < 0 or column >= self.width:
                return False
            return True

        yield from filter(check_in_bounds, adjacent_coords)

    def get_randomized_coords_for_mines(self, n, starting_tile: tuple[int, int]):
        cell_num = list(range(self.width * self.height))
        if starting_tile:
            cell_num.remove(self.coords_to_number(*starting_tile))
            for adj_row, adj_column in self.get_adjacent_tiles_coordinates(*starting_tile):
                cell_num.remove(self.coords_to_number(adj_row, adj_column))
        yield from map(self.number_to_coords, np.random.choice(cell_num, size=n, replace=False))


class CompleteBoard(BaseBoard):
    def __init__(self, width, height, mines, starting_tile: tuple[int, int] = None):
        super().__init__(width, height)
        if not starting_tile:
            starting_tile = (np.random.choice(range(self.height)), np.random.choice(range(self.width)))
        self.starting_tile = starting_tile
        self._generate_board(mines, starting_tile)

    def _generate_board(self, mines, starting_tile):
        for row, column in self.get_randomized_coords_for_mines(mines, starting_tile):
            self.board[row, column] = -1
            for adj_row, adj_column in self.get_adjacent_tiles_coordinates(row, column):
                if self.board[adj_row, adj_column] != -1:
                    self.board[adj_row, adj_column] += 1

    @property
    def discord_board(self) -> str:
        to_emoji = {
            -1: ':bomb:',
            0: ':blue_square:',
            1: ':one:',
            2: ':two:',
            3: ':three:',
            4: ':four:',
            5: ':five:',
            6: ':six:',
            7: ':seven:',
            8: ':eight:'
        }

        formatted_string = ''

        for row, array in enumerate(self.board):
            for column, tile in enumerate(array):
                if (row, column) == self.starting_tile:
                    formatted_string += to_emoji[tile]
                else:
                    formatted_string += f'||{to_emoji[tile]}||'
            formatted_string += '\n'

        return formatted_string


class Game(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def minesweeper(self, ctx, width: int = 10, height: int = 10, mines: int = 20, starting_row: int = None, starting_column: int = None):
        """Generate a minesweeper board"""
        board = CompleteBoard(width, height, mines=mines, starting_tile=(starting_row, starting_column) if starting_row and starting_column else None)
        msg = ''
        character_count = 0
        for line in board.discord_board.split('\n'):
            character_count += len(line)
            if character_count < 1000:
                msg += line + '\n'
            else:
                await ctx.send(msg)
                character_count = 0
                msg = line + '\n'
        await ctx.send(msg)


async def setup(bot):
    await bot.add_cog(Game(bot))
