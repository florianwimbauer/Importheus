# Setting up the root logger

import logging
from tqdm import tqdm

from core.clickhouse import TableCreator, CollCreator


class TqdmLoggingHandler(logging.Handler):
    """
    custom logging handler that handles tqdm progress bars with logging messages
    """
    def emit(self, record):
        try:
            msg = self.format(record)
            tqdm.write(msg)
            self.flush()
        except Exception:
            self.handleError(record)

class InfoFilter(logging.Filter):
    def filter(self, record):
        return record.levelno == logging.INFO


def setup_logging(is_verbose: bool, logfile: str = "importheus.log") -> logging.Logger:
    """
    sets up the logging environment for the whole framework. this is the root logger
    is only called once from the main.py to create the specific logger

    Args:
        is_verbose: if this execution shoud be verbose or not
        logfile: where to log everything

    Returns:
        the configured logger that can be used to write all the logs to main

    """

    logger = logging.getLogger("importheus")  # creating the central logger
    logger.setLevel(logging.DEBUG)  # setting the central logging level

    # .log logging handler
    file_handler = logging.FileHandler(logfile)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(file_handler)

    # terminal logging for ERROR-Messages
    error_terminal_handler = TqdmLoggingHandler()
    error_terminal_handler.setLevel(logging.ERROR)
    error_terminal_handler.setFormatter(
        logging.Formatter("[%(levelname)s] %(name)s: %(message)s")
    )
    logger.addHandler(error_terminal_handler)

    # terminal logging handler for Info messages (only executes if --verbose is set)
    if is_verbose:
        terminal_handler = TqdmLoggingHandler()
        terminal_handler.setLevel(logging.INFO)
        terminal_handler.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
        terminal_handler.addFilter(InfoFilter())
        logger.addHandler(terminal_handler)

    return logger


# Definition of the logging table that is used in the analyzer TODO should the log really look like this?
logtable_name: str = "logtable"
logTable = TableCreator(name=logtable_name, columns=[
    CollCreator("id", "UInt32"),
    CollCreator("timestamp", "DateTime"),
    CollCreator("file", "String"),
    CollCreator("type", "String"),
    CollCreator("table", "String"),
    CollCreator("totalRows", "UInt32"),
    CollCreator("successRows", "UInt32"),
    CollCreator("errRows", "UInt32")
    ])
