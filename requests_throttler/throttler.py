"""
.. module:: throttler
   :synopsis: The module containing the throttlers

.. moduleauthor:: Lou Marvin Caraig <loumarvincaraig@gmail.com>

This module contains the throttlers.

"""

import time
import threading
from collections import deque as queue
from concurrent.futures import ThreadPoolExecutor

import requests

from requests_throttler.utils import Timer
from requests_throttler.utils import locked, get_logger
from requests_throttler.throttled_request import ThrottledRequest

logger = get_logger(__name__)

THROTTLER_STATUS = ['initialized', 'running', 'waiting', 'paused', 'stopped', 'ending', 'ended']
THROTTLER_STATUS_DEPENDENCIES = {'initialized': ['initialized', 'running', 'stopped'],
                                 'running': ['running', 'waiting', 'paused', 'stopped'],
                                 'waiting': ['waiting', 'running', 'paused', 'stopped'],
                                 'paused': ['paused', 'running', 'waiting', 'stopped'],
                                 'stopped': ['stopped', 'ending'],
                                 'ending': ['ending', 'ended']}


class ThrottlerStatusError(Exception):
    """Exception that occurs when something goes wrong while changing status

    :param msg: the message
    :type msg: string
    :param current_status: the status to set
    :type current_status: string
    :param previous_status: the previous status
    :type previous_status: string

    """
    
    def __init__(self, msg, current_status, previous_status=None):
        self.msg = msg
        self.status = current_status
        self.previous_status = previous_status

    def __str__(self):
        if self.previous_status is None:
            return "{message} (current status: {status})".format(message=self.msg,
                                                                 status=self.status)
        return "{message} ({prev_status} ---> {status})".format(message=self.msg,
                                                                status=self.status,
                                                                prev_status=self.previous_status)


class FullRequestsPoolError(Exception):
    """Exception that occurs when an enqueue is tried in a full pool

    :param msg: the message
    :type msg: string
    :param pool: the pool
    :type pool: collections.deque

    """
    
    def __init__(self, msg, pool):
        self.msg = msg
        self.pool = pool

    def __str__(self):
        return "{message} (pool size: {pool_size})".format(message=self.msg,
                                                           pool_size=self.pool.maxlen)


class BaseThrottler(object):
    """This class provides the base requests throttler

    The base throttler guarantees that between each request a fixed amount of time between them
    elapsed. The pool can be limited by a maximum length and an exception is raised if a request
    is tried to be enqueued in the full pool.

    :param name: the name of the throttler
    :type name: string
    :param requests_pool: the pool containing the requests (FIFO)
    :type requests_pool: collections.dequeue
    :param delay: the delay in seconds between each request
    :type delay: float
    :param status: the current status of the thottler
    :type status: string
    :param session: the session to use to perform the requests
    :type session: requests.Session
    :param executor: the executor responsable to start the throttler
    :type executor: threading.ThreadPoolExecutor
    :param timer: the timer responsable to measure the time between each request
    :type timer: utils.Timer
    :param successes: the number of request that succeded
    :type successes: int
    :param failures: the number of request that failed
    :type successes: int
    :param wait_enqueued: a flag that indicates if after the shutdown the requests enqueued
                          have to be finished or aborted
    :type wait_enqueued: boolean
    :param status_lock: the condition on which to wait on a specific status change
    :type status_lock: threading.Condition
    :param not_empty: the condition on which to wait when the pool of requests is empty
    :type not_empty: threading.Condition

    """

    def __init__(self, *args, **kwargs):
        """Create a base throttler with the given delay time and pool size

        When both ``delay`` and ``reqs_over_time`` are :const:`None`, :attr:`delay` is set to
        :const:`0`.

        :param name: the name of the throttler (default: :const:`None`)
        :type name: string
        :param session: the sessions to use for each request
        :type session: requests.Session
        :param delay: the fixed positive amount of time that must elapsed bewteen each request
                      in seconds (default: :const:`None`)
        :type delay: float
        :param reqs_over_time: a tuple of the form (`number of requests`, `time`) used to
                               calculate the delay to use when it is :const:`None`. The delay
                               will be equal to ``time / number of requests`` (default:
                               :const:`None`)
        :type reqs_over_time: (float, float)
        :param max_pool_size: the maximum number of enqueueable requests (default: *unlimited*)
        :type max_pool_size: int
        :raise:
            :ValueError: if ``delay`` or the value calculated from ``reqs_over_time`` is a
                         negative number

        """
        self._name = kwargs.get('name')
        self._requests_pool = queue(maxlen=kwargs.get('max_pool_size'))
        self._delay = self._get_delay(kwargs.get('delay'), kwargs.get('reqs_over_time'))
        self._status = 'initialized'
        self._session = kwargs.get('session', requests.Session())
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._timer = Timer(checkpoint=0)
        self._successes = 0
        self._failures = 0
        self._wait_enqueued = None
        self.status_lock = threading.Condition(threading.Lock())
        self.not_empty = threading.Condition(threading.Lock())

    def _get_delay(self, delay, reqs_over_time):
        """Calculates the delay to assign

        :param delay: the fixed positive amount of time that must elapsed bewteen each request
                      in seconds (default: :const:`None`)
        :type delay: float
        :param reqs_over_time: a tuple of the form (`number of requests`, `time`) used to
                               calculate the delay to use when it is :const:`None`. The delay
                               will be equal to ``time``/``number of requests``.
        :type reqs_over_time: tuple
        :return: the value of ``delay`` to use (default :const:`0`)
        :rtype: float
        :raise:
            :ValueError: if ``delay`` or the value calculated from ``reqs_over_time`` is a
                         negative number

        """
        if delay is None:
            if reqs_over_time is None:
                return 0
            n_reqs, time_for_reqs = reqs_over_time
            if n_reqs < 0 or time_for_reqs < 0:
                raise ValueError("The number of requests and the time value must be positive.")
            delay = float(time_for_reqs) / n_reqs
        if delay < 0:
            raise ValueError("The delay value must be positive.")
        return delay

    def __str__(self):
        return "[{class_name} <{name}, {delay}, {status}>]".format(class_name="BaseThrottler",
                                                                   name=repr(self._name),
                                                                   delay=repr(self._delay),
                                                                   status=repr(self._status))

    def __enter__(self):
        """Start the throttler by entering in a context"""

        self.start()
        return self

    def __exit__(self, type, value, traceback):
        """Shutdown the throttler by exiting from the context"""

        self.shutdown()
        return value

    @property
    def name(self):
        """The name of the throttler

        :getter: Returns :attr:`name`
        :type: string

        """
        return self._name

    @property
    def delay(self):
        """The delay value between each request

        :getter: Returns :attr:`delay`
        :type: float

        """
        return self._delay

    @property
    @locked('status_lock')
    def status(self):
        """The status of the throttler

        :getter: Returns :attr:`status`
        :setter: Sets the new status
        :raise:
            :ThrottlerStatusError: if the new status is invalid
        :type: string

        """
        return self._status

    @status.setter
    @locked('status_lock')
    def status(self, status):
        """Set a new status

        :param status: the new status to assign
        :raise:
            :ThrottlerStatusError: if the new status is invalid

        """
        if status not in THROTTLER_STATUS:
            raise ThrottlerStatusError("Invalid status.", status)
        if status not in THROTTLER_STATUS_DEPENDENCIES[self._status]:
            raise ThrottlerStatusError("Invalid status stransition.", status,
                                       previous_status=self._status)
        logger.debug("Status changing: %s ---> %s", self._status, status)
        self._status = status

    @property
    @locked('status_lock')
    def successes(self):
        """The number of successes

        :getter: Returns :attr:`successes`
        :type: int

        """
        return self._successes

    @property
    @locked('status_lock')
    def failures(self):
        """The number of failures

        :getter: Returns :attr:`failures`
        :type: int

        """
        return self._failures

    def start(self):
        """Start the throttler by starting the main loop

        :raise:
            :ThrottlerStatusError: if the throller has been already started

        """
        logger.info("Starting base throttler '%s'...", self._name)
        if self.status in ['running', 'waiting', 'paused']:
            raise ThrottlerStatusError("Cannot start an already started throttler.",
                                       self._status)
        if self.status in ['stopped', 'ending', 'ended']:
            raise ThrottlerStatusError("Cannot start an already shutdown throttler.",
                                       self._status)

        self.status = 'running'
        self._executor.submit(self._main_loop)

    @locked('not_empty')
    def shutdown(self, wait_enqueued=True):
        """Shutdown the throttler by shutdowning the executor

        If ``wait_enqueued`` is :const:`True` then before stopping the throttlers consumes all
        the requests enqueued. Otherwise the throttler is forced to be shutdowned.

        :param wait_enqueued: the flag that indicates if the already enqueued requests are to be
                              processed or aborted
        :raise:
            :ThrottlerStatusError: if the throttler has been already shutdowned

        """
        if self.status in ['stopped', 'ending', 'ended']:
            raise ThrottlerStatusError("Cannot shutdown an already shutdown throttler.",
                                       self._status)
        self.status = 'stopped'
        self._wait_enqueued = wait_enqueued
        self.not_empty.notify()
        self._executor.shutdown(wait=False)

    @locked('status_lock')
    def pause(self):
        """Pause the throttler

        :raise:
            :ThrottlerStatusError: if the throttler is not ``running``, ``waiting`` or already
                                   ``paused``

        """
        if self._status == 'paused':
            raise ThrottlerStatusError("Cannot pause an already paused throttler", self._status)
        if self._status not in ['running', 'waiting']:
            raise ThrottlerStatusError("Cannot pause a not running throttler", self._status)

        self._status = 'paused'
        self.status_lock.notify()

    @locked('status_lock')
    def unpause(self):
        """Unpause the throttler

        :raise:
            :ThrottlerStatusError: if the throttler is not ``paused``

        """
        if self._status != 'paused':
            raise ThrottlerStatusError("Cannot unpause not paused throttler", self._status)
        self._status = 'running'
        self.status_lock.notify()

    def submit(self, req):
        """Submit a single request and return the corresponding throttled request

        :param req: the request to throttle
        :type req: requests.Request
        :return: the corresponding throttled request
        :rtype: :class:`requests_throttler.throttled_request.ThrottledRequest`
        :raise:
            :ThrottlerStatusError: if the throttler is not ``running``, ``paused`` or
                                   ``waiting``
        
        """
        return self._submit(req)

    def multi_submit(self, reqs):
        """Submits a list of requests and return the corresponding list of throttled requests

        :param reqs: the list of requests to throttle
        :type req: list(requests.Request)
        :return: the corresponding list of throttled requests
        :rtype: list(:class:`requests_throttler.throttled_request.ThrottledRequest`)
        :raise:
            :ThrottlerStatusError: if the throttler is not ``running``, ``paused`` or
                                   ``waiting``
        
        """
        return [self._submit(r) for r in reqs]

    def _submit(self, request):
        """Submits the given request by preparing it and enqueueing it

        :param req: the request to throttle
        :type req: requests.Request
        :return: the corresponding throttled request
        :rtype: :class:`requests_throttler.throttled_request.ThrottledRequest`
        :raise:
            :ThrottlerStatusError: if the throttler is not ``running``, ``paused`` or
                                   ``waiting``

        """
        logger.info("Submitting request to base throttler (url: %s)...", request.url)
        if self._status not in ['running', 'paused', 'waiting']:
            raise ThrottlerStatusError("Cannot submit request to throttler", self._status)
        throttled_request, prepared = self._prepare_request(request)
        if prepared:
            try:
                self._enqueue_request(throttled_request)
            except FullRequestsPoolError as e:
                throttled_request.exception(e)
                self._inc_failures()
        return throttled_request

    def _main_loop(self):
        """The main loop of the throttler"""

        logger.info("Starting main loop...")
        while True:
            next_request = self._dequeue_request()
            if next_request is None:
                break
            self._sleep_or_pause()
            self._send_request(next_request)
        logger.info("Exited from main loop.")
        self._end()

    @locked('status_lock')
    def _end(self):
        """Set the ``ended`` status"""

        self._status = 'ended'
        self.status_lock.notify()

    @locked('status_lock')
    def wait_end(self):
        """Wait until the throttler is ``ended``"""

        while self._status != 'ended':
            self.status_lock.wait()

    @locked('status_lock')
    def _sleep_or_pause(self):
        """Sleep or pause depending on the status"""

        while self._status == 'paused':
            logger.info("Pausing...")
            self.status_lock.wait()
            logger.info("Unpaused!")
        if not self._status == 'stopped':
            remaining_time = self._remaining_time()
            if remaining_time > 0:
                logger.debug("Start sleeping for %f seconds...", remaining_time)
                time.sleep(remaining_time)
                logger.debug("Awakening...")
            self._timer.checkpoint = time.time()

    def _remaining_time(self):
        """Return the remaining time before performing the next request

        :return: the remaining time before sending the next request
        :rtype: float

        """
        return self._delay - self._timer.elapsed()

    def _prepare_request(self, request):
        """Prepare the given request and return the corresponding throttled request

        If an exception occurs during the preparation it is associated to the throttled request
        created.

        :param req: the request to throttle
        :type req: requests.Request
        :return: the throttled request and the flag indicating if it has been correctly prepared
        :rtype: (:class:`requests_throttler.throttled_requests.ThrottledRequest`, boolean)

        """
        try:
            logger.debug("Preparing request (url: %s)...", request.url)
            prepared_request = request.prepare()
        except requests.exceptions.RequestException as e:
            throttled_request = ThrottledRequest(None)
            throttled_request.exception = e
            self._inc_failures()
            prepared = False
            logger.warning("Unable to prepare the request (url: %s).", request.url)
        else:
            throttled_request = ThrottledRequest(prepared_request)
            prepared = True
            logger.debug("Request prepared!")
        return throttled_request, prepared

    def _send_request(self, throttled_request):
        """Send the given throttled request

        If an exception occurs during the sending it is associated to the throttled request.

        :param throttled_request: the throttled request to send
        :type throttled_request: requests_throttler.throttled_request.ThrottledRequest

        """
        try:
            logger.info("Sending request (url: %s)...", throttled_request.request.url)
            response = self._session.send(throttled_request.request)
        except Exception as e:
            throttled_request.exception = e
            self._inc_failures()
            logger.warning("Unable to send the request (url: %s).",
                           throttled_request.request.url)
        else:
            throttled_request.response = response
            self._inc_successes()
            logger.info("Request sent! (url: %s)", throttled_request.request.url)

    @locked('not_empty')
    def _enqueue_request(self, throttled_request):
        """Enqueue the given throttled request

        :param throttled_request: the throttled request to enqueue
        :type throttled_request: requests_throttler.throttled_request.ThrottledRequest
        :raise:
            :FullRequestsPoolError: if the pool of requests is full

        """
        logger.debug("Enqueueing request (url: %s)...", throttled_request.request.url)
        if len(self._requests_pool) == self._requests_pool.maxlen:
            raise FullRequestsPoolError("The requests pool is full.", self._requests_pool)

        self._requests_pool.append(throttled_request)
        logger.debug("Request enqueued! (url: %s)", throttled_request.request.url)
        self.not_empty.notify()

    @locked('not_empty')
    def _dequeue_request(self):
        """Dequeue the next throttled request to process and return it

        If the throttler is ``running`` and no requests are eunqueued the throttler waits until
        a new request arrives.

        :return: the next throttled request to send
        :rtype: requests_throttler.throttled_request.ThrottledRequest

        """
        logger.debug("Dequeueing request...")
        waiting = True
        while waiting:
            waiting, proceed = self._dequeue_condition()
            if waiting:
                logger.info("Start waiting for new requests...")
                self.not_empty.wait()
                logger.info("Awakening...")
            else:
                waiting = False
        
        if proceed:
            next_request = self._requests_pool.popleft()
        else:
            return None
        logger.debug("Request dequeued! (url: %s)", next_request.request.url)
        self.status = 'running' if self.status not in ['stopped', 'ending'] else self.status
        return next_request

    def _dequeue_condition(self):
        """Check if the throttler has to wait or has to proceed

        :return: a tuple of the form (``waiting``, ``proceed``) where ``waiting`` indicates if
                 the throttler has to wait while ``proceed`` indicates if the throttler has to
                 proceed
        :rtype: (boolean, boolean)

        """
        if self.status == 'stopped':
            self.status = 'ending'
            if not self._wait_enqueued:
                return False, False

        if self.status == 'ending':
            if len(self._requests_pool) == 0:
                return False, False

        if self.status == 'paused':
            return True, False

        if len(self._requests_pool) == 0:
            self.status = 'waiting'
            return True, False

        return False, True

    @locked('status_lock')
    def _inc_successes(self):
        """Increment the number of successes"""

        self._successes += 1

    @locked('status_lock')
    def _inc_failures(self):
        """Increment the number of failures"""

        self._failures += 1
