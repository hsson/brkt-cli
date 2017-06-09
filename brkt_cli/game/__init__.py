import logging
import multiprocessing
import os
import sys
import time
import uuid

import game_controller

game_score = None
yeti_env = None
token = None


def get_yeti_env():
    return yeti_env


def get_token():
    return token


def gamify(func):
    """Decorator that let's you play a game while the underlying function is
    being executed"""

    def func_wrapper(*args, **kwargs):
        tmp_log_file = '%s.log' % uuid.uuid4()

        print "Game will start in:"
        for i in reversed(range(1)):
            print i + 1
            time.sleep(1)

        def special_func(*args, **kwargs):
            root = logging.getLogger()
            map(root.removeHandler, root.handlers[:])
            map(root.removeFilter, root.filters[:])
            logging.basicConfig(level=logging.INFO, filename=tmp_log_file)
            log_file = open(tmp_log_file, 'w')
            sys.stdout = sys.stderr = log_file
            func(*args, **kwargs)

        p_cli = multiprocessing.Process(target=special_func,
                                        args=args,
                                        kwargs=kwargs)
        p_cli.start()

        p_game = multiprocessing.Process(target=game_controller.main)
        p_game.start()

        p_cli.join()

        p_game.join()

        with open(tmp_log_file) as log_file:
            print log_file.read()

        os.remove(tmp_log_file)

        return p_cli.exitcode

    return func_wrapper
