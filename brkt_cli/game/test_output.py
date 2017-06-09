import logging
import multiprocessing
import sys
import time

import game_controller as game


def log_printer(tmp_log_file):
    logging.basicConfig(level=logging.INFO, filename=tmp_log_file)

    log_file = open(tmp_log_file, 'w')
    sys.stdout = sys.stderr = log_file
    logger = logging.getLogger(__name__)
    for i in range(10):
        logger.info(time.time())
        time.sleep(0.5)
        print time.time()


if __name__ == '__main__':

    tmp_log_file = 'tmp_log_file.log'
    p_log = multiprocessing.Process(target=log_printer, args=(tmp_log_file,))
    p_log.start()

    p_game = multiprocessing.Process(target=game.main)
    p_game.start()

    try:
        p_log.join()
        p_game.join()
    finally:
        with open(tmp_log_file) as log_file:
            print log_file.read()
