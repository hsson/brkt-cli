import logging
import multiprocessing
import os
import sys
import time

import game_controller
from brkt_cli.game import TMP_LOG_FILE


def gamify(func):
    """Decorator that let's you play a game while the underlying function is
    being executed"""

    def func_wrapper(*args, **kwargs):
        if not args[0].fun:
            return func(*args, **kwargs)

        def special_func(*args, **kwargs):
            root = logging.getLogger()
            map(root.removeHandler, root.handlers[:])
            map(root.removeFilter, root.filters[:])
            logging.basicConfig(level=logging.INFO, filename=TMP_LOG_FILE)
            log_file = open(TMP_LOG_FILE, 'w')
            sys.stdout = sys.stderr = log_file
            func(*args, **kwargs)

        print "Game will start in:"
        for i in reversed(range(1)):
            print i + 1
            time.sleep(1)

        p_cli = multiprocessing.Process(target=special_func,
                                        args=args,
                                        kwargs=kwargs)
        p_cli.start()

        p_game = multiprocessing.Process(target=game_controller.main)
        p_game.start()

        with open(TMP_LOG_FILE) as log_file:
            while True:
                if p_game.exitcode is not None:
                    new_data = log_file.readline().strip()
                    if new_data:
                        print new_data
                # if p_cli.exitcode is not None and p_game.exitcode is None:
                #     with open(TMP_LOG_FILE, 'a') as log_file_append:
                #         log_file_append.write('Command is done!')
                if p_cli.exitcode is not None and p_game.exitcode is not None:
                    break
                time.sleep(0.1)

        os.remove(TMP_LOG_FILE)

        return p_cli.exitcode

    return func_wrapper
