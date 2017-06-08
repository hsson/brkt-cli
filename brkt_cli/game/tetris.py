
from random import shuffle
from collections import deque

I_BLOCK = [
    [0, 1, 0, 0],
    [0, 1, 0, 0],
    [0, 1, 0, 0],
    [0, 1, 0, 0]
]
L_BLOCK = [
    [0, 0, 0, 0],
    [0, 0, 1, 0],
    [1, 1, 1, 0],
    [0, 0, 0, 0]
]
J_BLOCK = [
    [0, 0, 0, 0],
    [0, 1, 0, 0],
    [0, 1, 1, 1],
    [0, 0, 0, 0]
]
S_BLOCK = [
    [0, 0, 0, 0],
    [0, 1, 1, 0],
    [1, 1, 0, 0],
    [0, 0, 0, 0]
]
Z_BLOCK = [
    [0, 0, 0, 0],
    [0, 1, 1, 0],
    [0, 0, 1, 1],
    [0, 0, 0, 0]
]
T_BLOCK = [
    [0, 0, 0, 0],
    [0, 1, 0, 0],
    [1, 1, 1, 0],
    [0, 0, 0, 0]
]
O_BLOCK = [
    [0, 0, 0, 0],
    [0, 1, 1, 0],
    [0, 1, 1, 0],
    [0, 0, 0, 0]
]
LEFT = 'left'
RIGHT = 'right'
UP = 'up'
DOWN = 'down'
BLOCK_MATRIX_WIDTH_HEIGHT = 4


class Block():
    def __init__(self, block_type):
        # self.matrix represents the current rotation of the block, see
        # default rotations above
        self.matrix = block_type
        # self.position is represented using a (x,y) tuple
        self.position = INITIAL_POSITION  # TODO: Get this from the renderer

    def move(self, direction):
        if direction == LEFT:
            self.position[0] -= 1
        elif direction == RIGHT:
            self.position[0] += 1
        elif direction == DOWN:
            self.position[1] += 1
        else:
            raise RuntimeError('Illegal movement: %s' % direction)

    def rotate(self, clockwise=True):
        if clockwise:
            self.matrix = zip(*self.matrix[::-1])
        else:
            self.matrix = zip(*self.matrix)[::-1]


class Tetris():
    '''
    The boards state is stored in the renderer, we just handle actions here as
    well as keep track of our moving piece, until it becomes part of the
    board (is placed)
    '''
    def __init__(self):
        self.start_new_game()

    def start_new_game(self):
        # The board has 'height' number of rows and 'width' number of colums
        self.block = None
        self.block_queue = deque()
        self.score = 0

    def game_over(self):
        # do stuff
        self.start_new_game()

    def spawn_block(self):
        self.block = Block(block_type=self.get_new_block_type())

    def get_new_block_type(self):
        # We use 7 bag randomization for this
        if not self.block_queue:
            blocks = [I_BLOCK,
                      L_BLOCK,
                      J_BLOCK,
                      S_BLOCK,
                      Z_BLOCK,
                      T_BLOCK,
                      O_BLOCK]
            shuffle(blocks)
            self.block_queue = deque(blocks)

        return self.block_queue.pop()

    def rotate(self, block):
        # for now we only rotate clockwise, but there's support for
        # counter-clockwise in blocks rotate function
        old_rotation = block.rotation
        block.rotate()
        if not self.is_legal_state():
            block.rotation = old_rotation

    def move(self, block, direction):
        old_position = block.position
        block.move(direction=direction)
        if not self.is_legal_state():
            block.position = old_position

    def drop(self, block):
        # slams the piece as far down from the current position as possible
        old_position = block.position
        while self.is_legal_state():
            block.move(direction=DOWN)

        block.position = old_position

    def add_score(self, amount):
        self.score += amount

    def is_legal_state(self):
        # Checks if the current state of the block is legal with the current
        # state of the board
        current_state = CURRENT_STATE  # TODO: Get this from the renderer

        # TODO: This looks really overcomplicated lol
        padding = BLOCK_MATRIX_WIDTH_HEIGHT
        current_state_with_borders = []
        for row in current_state:
            row_with_borders = []
            for column in row:
                column_with_borders = [padding] + column + [padding]
                row_with_borders.append(column_with_borders)
            row_with_borders = [padding] + row_with_borders + [padding]
            current_state_with_borders.append(row_with_borders)

        block_position_considering_borders = (self.block.position[0] + padding,
                                              self.block.position[1] + padding)

        # Check so that the padded board with the offset block does not
        # overlap in any place.

        for row_index in range(BLOCK_MATRIX_WIDTH_HEIGHT):
            for column_index in range(BLOCK_MATRIX_WIDTH_HEIGHT):
                board_pixel = current_state_with_borders[
                    block_position_considering_borders[0] + row_index][
                        block_position_considering_borders[1] + column_index]
                block_pixel = self.block.matrix[row_index][column_index]

                if board_pixel and block_pixel:
                    return False
