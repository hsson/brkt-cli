import random
import time

from asciimatics.effects import Effect
from asciimatics.exceptions import NextScene
from asciimatics.particles import Rain
from asciimatics.paths import Path
from asciimatics.scene import Scene
from asciimatics.sprites import Arrow

import brkt_cli.game

MAX_MISSED_DUCKS = 5


class DuckHuntStats():
    missed_ducks = 0
    hit_ducks = 0


class Duck(Arrow):
    def __init__(self, screen, path):
        super(Duck, self).__init__(screen, path)

    def _update(self, frame_no):
        last_y_pos = self.last_position()[1]
        if last_y_pos is not None and last_y_pos < -5:
            DuckHuntStats.missed_ducks += 1
            self.delete_count = 1
        super(Duck, self)._update(frame_no)


class DuckSpawner(Effect):
    def __init__(self, screen, spawn_rate):
        """
        Spawns ducks with random paths
        :param screen: screen
        :param spawn_rate: delay between new ducks
        """
        super(DuckSpawner, self).__init__()
        self._screen = screen
        self.spawn_rate = spawn_rate
        self.last_spawn_time = 0

    def spawn_duck(self):
        path = Path()
        path.jump_to(self._screen.width * random.randint(0, 1),
                     self._screen.height)
        target = int(self._screen.width * random.random())
        path.move_straight_to(target, -10, 40)
        self._scene.add_effect(Duck(self._screen, path))
        self.last_spawn_time = time.time()

    def _update(self, frame_no):
        if DuckHuntStats.missed_ducks > MAX_MISSED_DUCKS:
            brkt_cli.game.game_score = {
                'score': DuckHuntStats.hit_ducks,
                'game': 'duck_hunt'
            }
            raise NextScene("Game_Over")
        if time.time() > self.last_spawn_time + self.spawn_rate:
            self.spawn_duck()

    def reset(self):
        pass

    @property
    def stop_frame(self):
        return self._stop_frame


def get_scenes(screen):
    scenes = []

    # MAIN GAME
    effects = [
        DuckSpawner(screen, 1),
        Rain(
                screen,
                9999999
        )
    ]
    scenes.append(Scene(effects, -1, name="Duck_Hunt_Game"))

    return scenes
