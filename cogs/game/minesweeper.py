import numpy as np
from typing import Iterator
from scipy.signal import convolve2d


CoordT = tuple[int, int]


class Board:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.board = np.zeros((height, width), dtype=np.int8)  # create a board width x height size with zeros

    def check_in_bounds(self, coordinate: CoordT):
        """Utility function to check if the coordinate is within the board bounds"""

        row, column = coordinate

        if row < 0 or row >= self.height:
            return False
        if column < 0 or column >= self.width:
            return False
        return True

    def coords_to_number(self, coordinate: CoordT) -> int:
        """Translate a 2d coordinate of row and column starting from top right into a 1d number"""

        return coordinate[0] * self.width + coordinate[1]

    def number_to_coords(self, number: int) -> CoordT:
        """Translate a 1d number to a 2d coordinate of row and column starting from top right according to the board matrix"""

        return divmod(number, self.width)

    def get_adjacent_tiles_coordinates(self, coordinate: CoordT) -> Iterator[CoordT]:
        """Get adjacent tiles coordinate. Doesn't give coordinates from the other side of the board, exp. target is at the side of the board"""

        row, column = coordinate

        adjacent_coords = ((row - 1, column - 1), (row - 1, column), (row - 1, column + 1),  # top part
                           (row, column - 1), (row, column + 1),  # side part
                           (row + 1, column - 1), (row + 1, column), (row + 1, column + 1))  # bottom part

        yield from filter(self.check_in_bounds, adjacent_coords)


class Minesweeper(Board):
    ADJ_MINE_KERNEL = np.ones((3, 3), dtype=np.int8) * -1

    def __init__(self, width: int, height: int, mines: int | float, *, starting_tile: tuple[int, int] = None):
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

        assert isinstance(mines, int)  # make sure mines is an integer

        if not starting_tile:
            starting_tile = (np.random.randint(0, self.height-1), np.random.randint(0, self.width-1))
        self.starting_tile = starting_tile

        self.convol_generation(mines)

    def get_randomized_coords_for_mines(self, n: int, starting_tile: tuple[int, int]) -> Iterator[CoordT]:
        cell_num = list(range(self.width * self.height))

        cell_num.remove(self.coords_to_number(starting_tile))  # exclude starting position
        for coord in self.get_adjacent_tiles_coordinates(starting_tile):  # exclude the tiles adjacent to the starting position
            cell_num.remove(self.coords_to_number(coord))
        yield from map(self.number_to_coords, np.random.choice(cell_num, size=n, replace=False))

    # def generate_board(self, mines) -> None:
    #     """Generate a board with mines and markings."""
    #     for coord in self.get_randomized_coords_for_mines(mines, self.starting_tile):
    #         self.board[coord] = -1
    #         for coord in self.get_adjacent_tiles_coordinates(coord):
    #             if self.board[coord] != -1:
    #                 self.board[coord] += 1

    def convol_generation(self, mines) -> None:  # 5x faster than for loops generation
        """Generate a board with mines and markings. Uses matrix convolution"""

        # add mines
        for coord in self.get_randomized_coords_for_mines(mines, self.starting_tile):
            self.board[coord] = -1

        # mark adjacent mines numbers
        # convolute a board, then mark -1 for spot that was previously a mine
        self.board = np.where(self.board == -1, -1, (convolve2d(self.board, self.ADJ_MINE_KERNEL, mode="same")))


