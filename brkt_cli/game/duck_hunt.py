from asciimatics.effects import Cycle
from asciimatics.renderers import FigletText
from asciimatics.scene import Scene
from asciimatics.particles import Rain


def get_scenes(screen):
    scenes = []

    # MAIN GAME
    effects = [
        Cycle(
                screen,
                FigletText("DUCKHUNT", font='big'),
                screen.height // 2 - 8),
        Rain(
            screen,
            9999999
        )
    ]
    scenes.append(Scene(effects, -1, name="Duck_Hunt_Game"))

    return scenes