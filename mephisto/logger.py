"""
Logger template
"""

import logging

# create logger
logger = (
    logging.getLogger()
)  # Here we can supply a name, not sure if we need or want to
logger.setLevel(logging.INFO)

# create console handler and set level to debug
ch = logging.StreamHandler()

# create formatter
formatter = logging.Formatter("<%(levelname)s> %(module)s : %(message)s")

# add formatter to ch
ch.setFormatter(formatter)

# add ch to logger
if not logger.handlers:
    logger.addHandler(ch)

# based on stackoverflow post - quick and dirty hack for colors ;)
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
