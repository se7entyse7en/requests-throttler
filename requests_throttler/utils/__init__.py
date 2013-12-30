import logging
import threading

from requests_throttler.settings import \
    LOG_FORMAT, \
    DEFAULT_LOG_LEVEL


def locked(lock):
    """Decorator usefull to access to a function with a lock named `lock`"""

    def _locked(func):
        def wrapper(*args, **kwargs):
            lock_to_use = getattr(args[0], lock)
            if not isinstance(lock_to_use, threading.Lock().__class__) and \
               not isinstance(lock_to_use, threading.Condition().__class__):
                raise ValueError('`{lock}` is not an instance neither of threading.Lock neither '
                                 'of threading.Condition'.format(lock=lock_to_use))
            with lock_to_use:
                return func(*args, **kwargs)

        return wrapper
    return _locked


def get_logger(name, level=DEFAULT_LOG_LEVEL):
    logging.basicConfig(format=LOG_FORMAT[level])
    logger = logging.getLogger(name)
    logger.setLevel(level)
    return logger
