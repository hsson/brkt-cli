from asciimatics.effects import Cycle
from asciimatics.renderers import FigletText
from asciimatics.scene import Scene


def get_scenes(screen):
    scenes = []
    effects = [
        Cycle(
                screen,
                FigletText("GAME OVER", font='big'),
                screen.height // 2 - 8),
    ]
    scenes.append(Scene(effects, -1, name="Game_Over"))

    return scenes
