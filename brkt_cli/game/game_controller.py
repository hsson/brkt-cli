from asciimatics.exceptions import ResizeScreenError
from asciimatics.screen import Screen

import bug_hunt
import game_over
import main_menu
import encryptris
import welcome_screen


def main_game(screen, scene):
    scenes = []
    scenes += welcome_screen.get_scenes(screen)
    scenes += main_menu.get_scenes(screen)
    scenes += game_over.get_scenes(screen)
    scenes += encryptris.get_scenes(screen)
    scenes += bug_hunt.get_scenes(screen)

    screen.play(scenes, stop_on_resize=True, start_scene=scene)


def main():
    last_scene = None
    while True:
        try:
            Screen.wrapper(main_game, catch_interrupt=False, arguments=[
                last_scene])
            break
        except ResizeScreenError as e:
            last_scene = e.scene


if __name__ == "__main__":
    main()
