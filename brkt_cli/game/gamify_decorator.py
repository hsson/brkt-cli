import logging
import multiprocessing
import os
import sys
import time
import logging

import game_controller
import brkt_cli.game as game
from brkt_cli import brkt_env_from_values


def gamify(func):
    """Decorator that let's you play a game while the underlying function is
    being executed"""

    def func_wrapper(*args, **kwargs):
        try:
            brkt_env = brkt_env_from_values(args[0], args[1])
            game.yeti_env = 'http://%s:30948' % (brkt_env.api_host)
            token = args[0].token
            if not token:
                token = os.getenv('BRKT_API_TOKEN')
            game.token = token
        except Exception as e:
            logging.error("You can play but you can't post to yeti :(. "
                          "Error: %s", e)

        logging.info("Starting BRKT Entertainment System")
        time.sleep(1)

        def special_func(*args, **kwargs):
            root = logging.getLogger()
            map(root.removeHandler, root.handlers[:])
            map(root.removeFilter, root.filters[:])
            logging.basicConfig(level=logging.INFO, filename=game.TMP_LOG_FILE)
            log_file = open(game.TMP_LOG_FILE, 'w')
            sys.stdout = sys.stderr = log_file
            func(*args, **kwargs)

        p_cli = multiprocessing.Process(target=special_func,
                                        args=args,
                                        kwargs=kwargs)
        p_cli.start()

        p_game = multiprocessing.Process(target=game_controller.main)
        p_game.start()

        # We want to let the new process create the file before trying to
        # read it. Kinda glitchy :(
        time.sleep(1)

        with open(game.TMP_LOG_FILE) as log_file:
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

        os.remove(game.TMP_LOG_FILE)

        return p_cli.exitcode

    return func_wrapper
