"""
 _    ___   ___  ___ ___ ___
| |  / _ \ / __|/ __| __| _ \
| |_| (_) | (_ | (_ | _||   /
|____\___/ \___|\___|___|_|_\

"""

import logging


class CustomFormatter(logging.Formatter):
    width = 10

    def format(self, record):
        return "%s %s: %s" % (
            "[{}]".format(record.levelname).ljust(self.width),
            # record.name,
            record.module,
            record.msg,
        )


logger = logging.getLogger("MEPHISTO")

if not logger.handlers and not logging.getLogger().handlers:

    logger.setLevel(logging.INFO)

    ch = logging.StreamHandler()

    # formatter = logging.Formatter("<%(levelname)s> %(module)s : %(message)s")
    formatter = CustomFormatter()

    ch.setFormatter(formatter)
    logger.addHandler(ch)

    BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = [30 + _i for _i in range(8)]
    RESET_SEQ = "\033[0m"
    COLOR_SEQ = "\033[1;%dm"
    BOLD_SEQ = "\033[1m"
    colorMapping = {
        logging.INFO: GREEN,
        logging.DEBUG: BLUE,
        logging.WARNING: YELLOW,
        logging.ERROR: RED,
    }
    for loglevel, color in colorMapping.items():
        logging.addLevelName(
            loglevel,
            "{COLOR_SEQ}{LEVELNAME}{RESET_SEQ}".format(
                COLOR_SEQ=COLOR_SEQ % color,
                LEVELNAME=logging.getLevelName(loglevel),
                RESET_SEQ=RESET_SEQ,
            ),
        )
