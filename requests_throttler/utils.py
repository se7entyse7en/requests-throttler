"""
.. module:: utils
   :synopsis: A module containing some utilities

.. moduleauthor:: Lou Marvin Caraig <loumarvincaraig@gmail.com>

This module provides some utilities used by other modules.

"""

import time
import logging
import threading
from functools import wraps

from requests_throttler.settings import \
    LOG_FORMAT, \
    DEFAULT_LOG_LEVEL


def locked(lock):
    """Decorator usefull to access to a function with a lock named *lock*

    :param lock: the name of the lock to use
    :type lock: :class:`threading.Lock` or :class:`threading.Condition`
    :return: the decorated function

    """
    def _locked(func):
        @wraps(func)
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


class NoCheckpointSetError(Exception):
    """Exception that occurs when no checkpoint is set and it is needed
    
    :param msg: the message
    :type msg: string

    """

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


class Timer(object):
    """This class provides an utility to calculates elapsed time since a start/check point

    :param start: the starting time of the timer
    :type start: float
    :param checkpoint: the last checkpoint of the timer
    :type checkpoint: float

    """

    def __init__(self, start=None, checkpoint=None):
        """Create the timer with the given starting time and an eventual checkpoint

        :param start: the starting time of the timer (default: *now*)
        :type start: float
        :param checkpoint: the last checkpoint of the timer (default: :const:`None`)
        :type checkpoint: float

        """
        self._start = start if start is not None else time.time()
        self._checkpoint = checkpoint

    @property
    def start(self):
        """The timer starting time

        :getter: Returns :attr:`start`
        :type: float

        """
        return self._start

    @property
    def checkpoint(self):
        """The last checkpoint

        :getter: Returns :attr:`checkpoint`
        :setter: Sets the checkpoint
        :type: float

        """
        return self._checkpoint

    @checkpoint.setter
    def checkpoint(self, checkpoint):
        """Set a checkpoint

        :param checkpoint: the new checkpoint
        :type checkpoint: float

        """
        self._checkpoint = checkpoint

    def total_elapsed(self):
        """Return the elapsed time since the timer starting time

        :return: the total elapsed time since the starting time of the timer
        :rtype: float

        """
        return time.time() - self._start

    def elapsed(self):
        """Return the elapsed time since the last checkpoint

        :return: the elapsed time since the last checkpoint
        :rtype: float
        :raises:
            :NoCheckpointSetError: if :attr:`checkpoint` is :const:`None`

        """
        if self._checkpoint is None:
            raise NoCheckpointSetError("No checkpoint has been set.")
        return time.time() - self._checkpoint

    def get_elapsed_and_set_checkpoint(self, change=True, new_checkpoint=None):
        """Return the elapsed time since the last checkpoint and change the checkpoint

        The :attr:`checkpoint` is changed with ``new_checkpoint`` if ``change`` is :const:`True`.
        If ``new_checkpoint`` is ``None``, then to ``checkpoint`` is assigned the current time.

        :param change: the flag that indicates if the checkpoint is to be changed
                       (default: :const:`True`)
        :type change: boolean
        :param new_checkpoint: the new checkpoint to assign (default: :const:`None`)
        :type new_checkpoint: float
        :return: the elapsed time since the last checkpoint
        :rtype: float
        :raise:
            :NoCheckpointSetError: if :attr:`checkpoint` is :const:`None`

        """
        if self._checkpoint is None:
            raise NoCheckpointSetError("No checkpoint has been set.")
        now = time.time()
        elapsed = now - self._checkpoint
        if change:
            self._checkpoint = now if new_checkpoint is None else new_checkpoint
        return elapsed
