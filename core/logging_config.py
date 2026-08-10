import logging


def configure_error_file_logging(logger, path):
    """Persist errors while keeping existing console handlers quiet."""
    logger.setLevel(logging.ERROR)
    logger.propagate = False

    for handler in logger.handlers:
        handler.setLevel(logging.CRITICAL)

    file_handler = logging.FileHandler(path)
    file_handler.setLevel(logging.ERROR)
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(file_handler)
    return file_handler
