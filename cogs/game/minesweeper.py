import numpy as np
from typing import Iterator
from scipy.signal import convolve2d


CoordT = tuple[int, int]


class Board:
    def __init__(self, width, height):
        self.width: int = width
        self.height: int = height
        self.board: np.ndarray = np.zeros((height, width), dtype=np.int8)  # create a board width x height size with zeros

    def get_adjacent_coords(self, coordinate: CoordT) -> Iterator[CoordT]:
        """Get the coordinates of row and column of adjacent cell given a coordinate."""

        for dx in range(-1, 2):  # -1, 0, 1
            for dy in range(-1, 2):  # -1, 0, 1
                range_x = range(self.width)  # X bounds
                range_y = range(self.height)  # Y bounds

                new_x, new_y = coordinate[0] + dx, coordinate[1] + dy  # adjacent cell

                if new_x in range_x and new_y in range_y and (dx, dy) != (0, 0):
                    yield new_x, new_y

    def coords_to_number(self, coordinate: CoordT) -> int:
        """Translate a 2d coordinate of row and column starting from top right into a 1d number"""

        return coordinate[0] * self.width + coordinate[1]

    def number_to_coords(self, number: int) -> CoordT:
        """Translate a 1d number to a 2d coordinate of row and column starting from top right according to the board matrix"""

        return divmod(number, self.width)


class Minesweeper(Board):
    ADJ_MINE_KERNEL = np.ones((3, 3), dtype=np.int8) * -1

    def __init__(self, width: int, height: int, mines: int | float, *, starting_tile: CoordT = None):
        """Create a minesweeper board

        :param: width <int> - the width of the board
        :param: height <int> - the height of the board
        :param: mines <int> - the number of mines in the board
                      <float> (0, 1) - the mine density of the board, from 0 to 1
        :param: starting_tile <tuple[int]> - the coordinate of the starting tile, usually to exclude mines from
        """

        super().__init__(width, height)
        if 0 < mines < 1:  # convert mine density to mines
            mines = max(1, int(mines*self.width*self.height))  # min 1 mine

        assert isinstance(mines, int), "Mines can only be an integer, or a decimal number between 0 and 1 to represent mine density"  # make sure mines is an integer

        if not starting_tile:
            starting_tile = (np.random.randint(0, self.height-1), np.random.randint(0, self.width-1))
        self.starting_tile: CoordT = starting_tile

        self.convol_generation(mines)

    def get_randomized_coords_for_mines(self, n: int) -> Iterator[CoordT]:
        """Get randomized coordinates for mine placements, will exclude starting position and the adjacent tiles to it."""

        cell_num = list(range(self.width * self.height))  # get position in 1d space

        cell_num.remove(self.coords_to_number(self.starting_tile))  # exclude starting position
        for coord in self.get_adjacent_coords(self.starting_tile):  # exclude the tiles adjacent to the starting position
            cell_num.remove(self.coords_to_number(coord))

        # get random position and convert to 2d coordinates
        yield from map(self.number_to_coords, np.random.choice(cell_num, size=n, replace=False))

    # def generate_board(self, mines) -> None:
    #     """Generate a board with mines and markings. For loops implementation"""
    #     for coord in self.get_randomized_coords_for_mines(mines, self.starting_tile):
    #         self.board[coord] = -1
    #         for coord in self.get_adjacent_tiles_coordinates(coord):
    #             if self.board[coord] != -1:
    #                 self.board[coord] += 1

    def convol_generation(self, mines: int) -> None:  # 5x faster than for loops implementation, not that it really matters, it's just cool
        """Generate a board with mines and markings. Matrix convolution implementation"""

        # add mines
        for coord in self.get_randomized_coords_for_mines(mines):
            self.board[coord] = -1

        # marks adjacent mines numbers
        # - convolve a board, then mark -1 for spot that was previously a mine
        self.board = np.where(self.board == -1, -1, (convolve2d(self.board, self.ADJ_MINE_KERNEL, mode="same")))
