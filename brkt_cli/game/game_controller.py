from asciimatics.exceptions import ResizeScreenError
from asciimatics.screen import Screen

import duck_hunt
import game_over
import main_menu
import tetris


def main_game(screen):
    scenes = []
    scenes += main_menu.get_scenes(screen)
    scenes += game_over.get_scenes(screen)
    scenes += tetris.get_scenes(screen)
    scenes += duck_hunt.get_scenes(screen)

    screen.play(scenes, stop_on_resize=True)


def main():
    try:
        Screen.wrapper(main_game)
    except ResizeScreenError:
        pass


if __name__ == "__main__":
    main()
