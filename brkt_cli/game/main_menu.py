from __future__ import division
from asciimatics.effects import Cycle, Stars
from asciimatics.renderers import FigletText
from asciimatics.scene import Scene


def get_scenes(screen):
    effects = [
        Cycle(
            screen,
            FigletText("MAIN MENU", font='big'),
            screen.height // 2 - 8),
        Cycle(
            screen,
            FigletText("PRESS SPACE FOR TETRIS!", font='big'),
            screen.height // 2 + 3),
        Stars(screen, (screen.width + screen.height) // 2)
    ]
    return [Scene(effects, -1)]
