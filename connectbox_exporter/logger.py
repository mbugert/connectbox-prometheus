from logging import Logger, NOTSET, addLevelName, INFO, DEBUG, StreamHandler, Formatter
import sys

VERBOSE = 5


class VerboseLogger(Logger):
    """
    Logger with custom log level VERBOSE which is lower than DEBUG.
    """

    def __init__(self, name, level=NOTSET):
        super().__init__(name, level)
        addLevelName(VERBOSE, "VERBOSE")

    def verbose(self, msg, *args, **kwargs):
        if self.isEnabledFor(VERBOSE):
            self._log(VERBOSE, msg, args, **kwargs)


def get_logger(verbosity: int) -> VerboseLogger:
    """
    Get logger object which logs to stdout with given verbosity.
    :param verbosity: logs INFO if 0, DEBUG if 1 and VERBOSE if >1
    :return:
    """
    if verbosity <= 0:
        log_level = INFO
    elif verbosity == 1:
        log_level = DEBUG
    else:
        log_level = VERBOSE

    logger = VerboseLogger("connectbox_exporter")
    logger.setLevel(log_level)
    handler = StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    formatter = Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger
