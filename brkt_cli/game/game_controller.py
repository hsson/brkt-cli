from asciimatics.screen import Screen
from asciimatics.exceptions import ResizeScreenError

import main_menu
import tetris
import sys


def main_game(screen):

    scenes = []
    scenes += main_menu.get_scenes(screen)
    scenes += tetris.get_scenes(screen)

    screen.play(scenes, stop_on_resize=True)


if __name__ == "__main__":
    try:
        Screen.wrapper(main_game)
        sys.exit(0)
    except ResizeScreenError:
        pass
