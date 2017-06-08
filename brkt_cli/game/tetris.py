from __future__ import division
import random

from asciimatics.effects import Effect, Cycle
from asciimatics.renderers import FigletText
from asciimatics.scene import Scene
from asciimatics.screen import Screen

TETRIS_WIDTH = 10
TETRIS_HEIGHT = 20


class Tetris_Board(Effect):
    """
    Special effect to scroll some text (from a Renderer) horizontally like a
    banner.
    """

    def __init__(self, screen, block_renderer, bg=Screen.COLOUR_BLACK,
                 **kwargs):
        """
        :param screen: The Screen being used for the Scene.
        :param block_renderer: The renderer for a single block piece
        :param bg: The default background colour to use for the text.

        Also see the common keyword arguments in :py:obj:`.Effect`.
        """
        super(Tetris_Board, self).__init__(**kwargs)
        self._screen = screen
        self._block_renderer = block_renderer
        self._bg = bg
        self._board = None

    def reset(self):
        self._board = [[1 for i in range(TETRIS_WIDTH)] for k in \
                       range(TETRIS_HEIGHT)]

    def _update_board(self):
        for i in range(len(self._board)):
            for j in range(len(self._board[0])):
                self._board[i][j] = random.randint(0, 1)
        pass

    def _render_board(self):
        image, colours = self._block_renderer.rendered_text
        block_width = max([len(row) for row in image]) + 1
        block_height = len([row for row in image if row.strip()])
        x = 0
        y = 0
        for row in self._board:
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

        self._update_board()

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
        # Cycle(
        #         screen,
        #         FigletText("ROCKS!", font='big'),
        #         screen.height // 2 + 3),
        # Stars(screen, (screen.width + screen.height) // 2),
        Tetris_Board(
                screen,
                FigletText("[]", font='pepper'),
        )
    ]
    return [Scene(effects, -1)]
