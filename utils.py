import time


class NoCheckpointSetError(Exception):

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


class Timer(object):
    """This class provides an utility to calculates elapsed time since a start/check point


    Attributes:
        `_start` - the starting time of the timer
        `_checkpoint` - the last checkpoint of the timer

    """

    def __init__(self, start=None, checkpoint=None):
        """Create the timer with the given starting time and an eventual checkpoint

        `start` - the starting time of the timer (default: now)
        `checkpoint` - the checkpoint (default: `None`)

        """
        self._start = start if start is not None else time.time()
        self._checkpoint = checkpoint

    @property
    def start(self):
        """Return the timer starting time"""

        return self._start

    @property
    def checkpoint(self):
        """Return the last checkpoint"""

        return self._checkpoint

    @checkpoint.setter
    def checkpoint(self, checkpoint):
        """Set a checkpoint"""

        self._checkpoint = checkpoint

    def total_elapsed(self):
        """Return the elapsed time since the timer starting time"""

        return time.time() - self._start

    def elapsed(self):
        """Return the elapsed time since the last checkpoint

        It raises `NoCheckpointSetError` if `checkpoint` is `None`.

        """
        if self._checkpoint is None:
            raise NoCheckpointSetError("No checkpoint has been set.")
        return time.time() - self._checkpoint

    def get_elapsed_and_set_checkpoint(self, change=True, new_checkpoint=None):
        """Return the elapsed time since the last checkpoint and change the checkpoint

        The checkpoint is changed with `new_checkpoint` if `change` is `True`. If
        `new_checkpoint` is `None`, then to checkpoint is assigned the current time. It
        raises `NoCheckpointSetError` if `checkpoint` is `None`.

        `change` - the flag that indicates if the checkpoint is to be changed (default: `True`)
        `new_checkpoint` - the new checkpoint to assign (default: `None`)

        """
        if self._checkpoint is None:
            raise NoCheckpointSetError("No checkpoint has been set.")
        now = time.time()
        elapsed = now - self._checkpoint
        if change:
            self._checkpoint = now if new_checkpoint is None else new_checkpoint
        return elapsed
