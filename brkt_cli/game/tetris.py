from __future__ import division
from random import shuffle
from collections import deque
from copy import deepcopy
import time


from asciimatics.effects import Effect, Cycle
from asciimatics.renderers import FigletText
from asciimatics.scene import Scene
from asciimatics.screen import Screen
from asciimatics.renderers import StaticRenderer

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
TEST_BLOCK = [
    [1, 1, 1, 1],
    [1, 1, 1, 1],
    [1, 1, 1, 1],
    [1, 1, 1, 1]
]

LEFT = 'left'
RIGHT = 'right'
UP = 'up'
DOWN = 'down'
BLOCK_MATRIX_WIDTH_HEIGHT = 4
TETRIS_WIDTH = 10
TETRIS_HEIGHT = 20


class Block():
    def __init__(self, block_type):
        # self.matrix represents the current rotation of the block, see
        # default rotations above
        self.matrix = block_type
        # self.position is represented using a (x,y) tuple
        self.position = [int(TETRIS_WIDTH / 2 - BLOCK_MATRIX_WIDTH_HEIGHT / 2),
                         -1]

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
        self.last_tick = time.time()
        self.board = [[0 for i in range(TETRIS_HEIGHT)] for k in
                      range(TETRIS_WIDTH)]
        self.spawn_block()

    def game_over(self):
        # do stuff
        self.start_new_game()

    def spawn_block(self):
        self.block = Block(block_type=TEST_BLOCK)

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

    def rotate_block(self):
        # for now we only rotate clockwise, but there's support for
        # counter-clockwise in blocks rotate function
        old_rotation = self.block.rotation
        self.block.rotate()
        if not self.is_legal_state():
            self.block.rotation = old_rotation

    def move_block(self, direction):
        old_position = self.block.position
        self.block.move(direction=direction)
        if not self.is_legal_state():
            self.block.position = old_position

    def drop_block(self):
        # slams the piece as far down from the current position as possible
        old_position = self.block.position
        while self.is_legal_state():
            self.block.move(direction=DOWN)

        self.block.position = old_position

    def add_score(self, amount):
        self.score += amount

    def is_legal_state(self):
        # Checks if the current state of the block is legal with the current
        # state of the board
        for x_index, x_list in enumerate(self.block.matrix):
            for y_index, block_value in enumerate(x_list):
                x, y = self.block.position
                board_x_pos = x + x_index
                board_y_pos = y + y_index
                if board_x_pos < 0 or board_x_pos > TETRIS_WIDTH - 1 or \
                        board_y_pos < 0 or board_y_pos > TETRIS_HEIGHT - 1:
                    board_value = 1
                else:
                    board_value = self.board[board_x_pos][board_y_pos]

                if board_value and block_value:
                    print 'NOT LEGAL'
                    return False
        print 'TOTALLY LEGAL'
        return True

    def get_board(self):
        '''
        Gets a representation of the board that has the block baked into it,
        ready to be rendered!
        '''
        self.maybe_tick_downwards()

        view_board = deepcopy(self.board)
        x, y = self.block.position

        for x_index, x_list in enumerate(self.block.matrix):
            for y_index, block_value in enumerate(x_list):
                # Check that it is a position on the board
                new_x = x + x_index
                new_y = y + y_index
                if new_x < TETRIS_WIDTH and new_x > -1 and \
                        new_y < TETRIS_HEIGHT and new_y > -1:
                    view_board[new_x][new_y] = block_value


        return view_board

    def maybe_tick_downwards(self):
        now = time.time()
        seconds_since_last_tick = int(now - self.last_tick)
        if seconds_since_last_tick > 1:
            self.last_tick = now
            self.move_block(direction=DOWN)


class TetrisBoard(Effect):
    def __init__(self, screen, block_renderer, bg=Screen.COLOUR_MAGENTA,
                 **kwargs):
        """
        :param screen: The Screen being used for the Scene.
        :param block_renderer: The renderer for a single block piece
        :param bg: The default background colour to use for the text.

        Also see the common keyword arguments in :py:obj:`.Effect`.
        """
        super(TetrisBoard, self).__init__(**kwargs)
        self._screen = screen
        self._block_renderer = block_renderer
        self._bg = bg
        self.logical_representation = Tetris()

    def reset(self):
        self.logical_representation.start_new_game()

    def _render_board(self):
        image, colours = self._block_renderer.rendered_text
        block_width = max([len(row) for row in image]) + 1
        block_height = len([row for row in image if row.strip()])
        x = 0
        y = 0
        for row in self.logical_representation.get_board():
            for pos in row:
                for (i, line) in enumerate(image):
                    if not pos:
                        line = " " * len(line)
                    self._screen.paint(line,
                                       x,
                                       y + i,
                                       Screen.COLOUR_WHITE,
                                       bg=self._bg,
                                       colour_map=colours[i])
                x += block_width
            x = 0
            y += block_height

    def _update(self, frame_no):
        self._render_board()

    @property
    def stop_frame(self):
        return 0


def get_scenes(screen):
    effects = [
        Cycle(
                screen,
                FigletText("TETRIS", font='big'),
                screen.height // 2 - 8),
        TetrisBoard(
                screen,
                StaticRenderer(images=['[]']) # FigletText("[]", font='pepper'),
        )
    ]
    return [Scene(effects, -1)]
