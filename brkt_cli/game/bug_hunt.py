import random
import time

from asciimatics.effects import Effect, Sprite
from asciimatics.event import KeyboardEvent, MouseEvent
from asciimatics.exceptions import NextScene
from asciimatics.particles import Explosion, Rain
from asciimatics.paths import DynamicPath, Path
from asciimatics.renderers import SpeechBubble, StaticRenderer
from asciimatics.scene import Scene
from asciimatics.screen import Screen
from asciimatics.sprites import Arrow

import brkt_cli.game
from log_streamer import LogStreamer

MAX_MISSED_BUGS = 5


class BugHuntStats(object):
    missed_bugs = 0
    hit_bugs = 0


class MouseController(DynamicPath):
    def __init__(self, sprite, screen, x, y):
        super(MouseController, self).__init__(screen, x, y)
        self._sprite = sprite

    def process_event(self, event):
        if isinstance(event, MouseEvent):
            self._x = event.x
            self._y = event.y
            if event.buttons & MouseEvent.DOUBLE_CLICK != 0:
                # Try to whack the other sprites when mouse is clicked
                self._sprite.shoot(powerful=True)
            elif event.buttons & MouseEvent.LEFT_CLICK != 0:
                # Try to whack the other sprites when mouse is clicked
                self._sprite.shoot(powerful=False)
            else:
                return event
        else:
            return event


class Gun(Sprite):
    def __init__(self, screen):
        """
        See :py:obj:`.Sprite` for details.
        """
        super(Gun, self).__init__(
                screen,
                renderer_dict={
                    "default": StaticRenderer(images=["X"])
                },
                path=MouseController(
                        self, screen, screen.width // 2, screen.height // 2),
                colour=Screen.COLOUR_BLACK)
        self._screen = screen

    def shoot(self, powerful=True):
        x, y = self._path.next_pos()
        for bug in [e for e in self._scene.effects if isinstance(e, Bug)]:
            try:
                if self.overlaps(bug, use_new_pos=True):
                    bug.get_shot()
            except TypeError:
                # Probably compared against an unitialized sprite
                pass
        if powerful:
            self._scene.add_effect(Explosion(self._screen, x, y, 25))
        else:
            #TODO(Adam): Does the same for now which is kinda lame
            self._scene.add_effect(Explosion(self._screen, x, y, 25))

class Bug(Arrow):
    def __init__(self, screen, path):
        super(Bug, self).__init__(screen, path)

    def _update(self, frame_no):
        last_y_pos = self.last_position()[1]
        if last_y_pos is not None and last_y_pos < -5:
            BugHuntStats.missed_bugs += 1
            self.delete_count = 1
        super(Bug, self)._update(frame_no)

    def get_shot(self):
        BugHuntStats.hit_bugs += 1
        self.delete_count = 1


class BugSpawner(Effect):
    def __init__(self, screen, spawn_rate):
        """
        Spawns bugs with random paths
        :param screen: screen
        :param spawn_rate: delay between new bugs
        """
        super(BugSpawner, self).__init__()
        self._screen = screen
        self.spawn_rate = spawn_rate
        self.last_spawn_time = 0

    def spawn_bug(self):
        path = Path()
        path.jump_to(self._screen.width * random.randint(0, 1),
                     self._screen.height)
        target = int(self._screen.width * random.random())
        path.move_straight_to(target, -10, 100)
        self._scene.add_effect(Bug(self._screen, path))
        self.last_spawn_time = time.time()

    def _update(self, frame_no):
        if BugHuntStats.missed_bugs >= MAX_MISSED_BUGS:
            brkt_cli.game.game_score = {
                'score': BugHuntStats.hit_bugs,
                'game': 'bug_hunt'
            }
            raise NextScene("Game_Over")
        if time.time() > self.last_spawn_time + self.spawn_rate:
            self.spawn_bug()

        image, _ = SpeechBubble(
                "Score: %d" % BugHuntStats.hit_bugs).rendered_text
        for i, line in enumerate(image):
            self._screen.paint(line,
                               (self._screen.width - len(line)) // 2,
                               self._screen.height - 5 + i,
                               Screen.COLOUR_WHITE)

        image, _ = SpeechBubble(
                "Misses left: %d" % (MAX_MISSED_BUGS -
                                     BugHuntStats.missed_bugs,)
        ).rendered_text
        for i, line in enumerate(image):
            self._screen.paint(line,
                               (self._screen.width - len(line)) // 2,
                               self._screen.height - 3 + i,
                               Screen.COLOUR_WHITE)

    def process_event(self, event):
        if isinstance(event, KeyboardEvent):
            key = event.key_code
            if key == Screen.KEY_ESCAPE:
                raise NextScene("Main_Menu")
            else:
                # Consume all keyboard presses
                pass
        else:
            return event

    def reset(self):
        super(BugSpawner, self).reset()
        BugHuntStats.missed_bugs = 0
        BugHuntStats.hit_bugs = 0

    @property
    def stop_frame(self):
        return self._stop_frame


def get_scenes(screen):
    scenes = []

    # MAIN GAME
    effects = [
        BugSpawner(screen, 1),
        Gun(screen),
        Rain(
                screen,
                9999999
        ),
        LogStreamer(
                screen,
                0,
                screen.height - 3)

    ]
    scenes.append(Scene(effects, -1, name="Bug_Hunt_Game"))

    return scenes
