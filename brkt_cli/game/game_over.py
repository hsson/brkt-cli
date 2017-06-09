from asciimatics.effects import Cycle
from asciimatics.renderers import FigletText
from asciimatics.scene import Scene
from asciimatics.screen import Screen
from asciimatics.effects import Effect

import brkt_cli.game
from brkt_cli.yeti import post_json


class ScoreReporter(Effect):

    def __init__(self, screen, y, **kwargs):
        super(ScoreReporter, self).__init__(**kwargs)
        self.x = screen.width // 7
        self.y = y
        self.selection = 0
        self._screen = screen
        self.score_reported = False

    def reset(self):
        pass

    def _draw_image(self, image, x, y, color=Screen.COLOUR_WHITE,
                    colour_map=None):
        for (i, line) in enumerate(image):
            cmap = colour_map[i] if colour_map else None
            self._screen.paint(line,
                               x,
                               y + i,
                               color,
                               bg=Screen.COLOUR_BLACK,
                               transparent=False,
                               colour_map=cmap)

    def _update(self, frame_no):
        game_score = brkt_cli.game.game_score
        game_name = game_score['game'] if game_score else 'Unknown'
        image, _ = FigletText(game_name, font='doom').rendered_text
        self._draw_image(image, 10, 10)

        score = game_score['score'] if game_score else -1
        image, _ = FigletText(str(score), font='doom').rendered_text
        self._draw_image(image, 10, 20)

        # TODO: Remove self.score_reported and have report_score trigger on
        # pushing enter after filling out name or something. And remove this
        # if check as well.
        if not self.score_reported and brkt_cli.game.get_yeti_env() \
                and brkt_cli.game.get_token():
            self.report_score(game=game_name, name='Testname', score=score)
            self.score_reported = True

    @property
    def stop_frame(self):
        return self._stop_frame

    def report_score(self, game, name, score):
        payload = {
            'game': game,
            'name': name,
            'score': score
        }
        post_json(
            brkt_cli.game.get_yeti_env() + '/api/v1/game/score',
            token=brkt_cli.game.get_token(),
            json=payload
        )


def get_scenes(screen):
    scenes = []
    effects = [
        Cycle(
            screen,
            FigletText("GAME OVER", font='big'),
            screen.height // 4
        ),
        ScoreReporter(screen=screen,
                      y=screen.height // 2)
    ]
    scenes.append(Scene(effects, -1, name="Game_Over"))

    return scenes
