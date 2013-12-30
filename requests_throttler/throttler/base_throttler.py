import time
import threading
from collections import deque as queue
from concurrent.futures import ThreadPoolExecutor

import requests

from requests_throttler.utils.timer import Timer
from requests_throttler.utils import locked, get_logger
from requests_throttler.throttled_request.throttled_request import ThrottledRequest

logger = get_logger(__name__)

THROTTLER_STATUS = ['initialized', 'running', 'waiting', 'paused', 'stopped', 'ending', 'ended']
THROTTLER_STATUS_DEPENDENCIES = {'initialized': ['initialized', 'running', 'stopped'],
                                 'running': ['running', 'waiting', 'paused', 'stopped'],
                                 'waiting': ['waiting', 'running', 'paused', 'stopped'],
                                 'paused': ['paused', 'running', 'waiting', 'stopped'],
                                 'stopped': ['stopped', 'ending'],
                                 'ending': ['ending', 'ended']}


class ThrottlerStatusError(Exception):
    
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


    Attributes:
        `_name` - the name of the throttler
        `_requests_pool` - the pool containing the requests (FIFO)
        `_delay` - the delay in seconds between each request
        `_status` - the current status of the thottler
        `_session` - the session to perform the requests
        `_executor` - the executor responsable to start the throttler
        `_timer` - the timer responsable to measure the time between each request
        `_successes` - the number of request that succeded
        `_failures` - the number of request that failed
        `_wait_enqueued` - a flag that indicates if after the shutdown the requests enqueued
                           have to be finished or aborted
        `status_lock` - the condition on which to wait on a specific status change
        `not_empty` - the condition on which to wait when the pool of requests is empty

    """

    def __init__(self, name=None, delay=0, max_pool_size=None):
        """Create a base throttler with the given delay time and pool size

        If `delay` is a negative number then `ValueError` is raised.

        `name` - the name of the throttler (default: `None`)
        `delay` - the fixed positive amount of time that must elapsed bewteen each request
                  in seconds (default: 0)
        `max_pool_size` - the maximum number of enqueueable requests (default: unlimited)

        """
        if delay < 0:
            raise ValueError("The delay value must be positive.")
        self._name = name
        self._requests_pool = queue(maxlen=max_pool_size)
        self._delay = delay
        self._status = 'initialized'
        self._session = requests.Session()
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._timer = Timer(checkpoint=0)
        self._successes = 0
        self._failures = 0
        self._wait_enqueued = None
        self.status_lock = threading.Condition(threading.Lock())
        self.not_empty = threading.Condition(threading.Lock())

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
        """Return the name of the throttler"""

        return self._name

    @property
    def delay(self):
        """Return the delay value between each request"""

        return self._delay

    @property
    @locked('status_lock')
    def status(self):
        """Return the status of the throttler"""

        return self._status

    @status.setter
    @locked('status_lock')
    def status(self, status):
        """Set a new status

        If `status` is invalid then `ThrottlerStatusError` is raised.

        `status` - the new status to assign

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
        """Return the number of successes"""

        return self._successes

    @property
    @locked('status_lock')
    def failures(self):
        """Return the number of failures"""

        return self._failures

    def start(self):
        """Start the throttler by starting the main loop

        If the throller has been already started then `ThrottlerStatusError` is raised.

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

        If `wait_enqueued` is `True` then before stopping the throttlers consumes all requests
        enqueued. Otherwise the throttler is forced to be shutdowned

        `wait_enqueued` - the flag that indicates if the already enqueued requests are to be
                          processed or aborted

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

        If the throttler is not `running` or `waiting` then `ThrottlerStatusError` is raised.

        """
        if self._status == 'paused':
            raise ThrottlerStatusError("Cannot pause an already paused throttler", self._status)
        if self._status not in ['running', 'waiting']:
            raise ThrottlerStatusError("Cannot pause a not running throttler", self._status)

        self._status = 'paused'
        self.status_lock.notify()

    @locked('status_lock')
    def unpause(self):
        """Unpauses the throttler

        If the throttler is not `paused` then `ThrottlerStatusError` is raised.

        """
        if self._status != 'paused':
            raise ThrottlerStatusError("Cannot unpause not paused throttler", self._status)
        self._status = 'running'
        self.status_lock.notify()

    def submit(self, reqs):
        """Submit a single request or an entire list and return the corresponding response

        If `reqs` is a single request then the corresponding throttled request is returned,
        otherwise if `reqs` is a `list` then the list of corresponding throttled requests
        is returned.

        `reqs` - it can be a single request or a list of them
        
        """
        if isinstance(reqs, list):
            return [self._submit(r) for r in reqs]
        return self._submit(reqs)

    def _submit(self, request):
        """Submits the given request by preparing it and enqueueing it

        If the throttler is not `running`, `paused` or `waiting` an exception is raised.
        With the returned throttled request is associated an eventual exception that could be
        raised during the preparation or the enqueueing.

        `request` - the request to submit

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
            self._sleep_or_pause()
            next_request = self._dequeue_request()
            if next_request is None:
                break
            self._send_request(next_request)
        logger.info("Exited from main loop.")
        self._end()

    @locked('status_lock')
    def _end(self):
        """Set the `ended` status"""

        self._status = 'ended'
        self.status_lock.notify()

    @locked('status_lock')
    def wait_end(self):
        """Wait untile the throttler is `ended`"""

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
        """Return the remaining time before performing the next request"""

        return self._delay - self._timer.elapsed()

    def _prepare_request(self, request):
        """Prepare the given request and return the corresponding throttled request

        If an exception occurs during the preparation it is associated to the throttled request
        created.

        `request` - the request to prepare

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

        `throttled_request` - the throttled request to send
        
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

        If the the pool of requests is full `FullRequestPoolError` is raised.

        `throttled_request` - the throttled request to enqueue

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

        If the throttler is `running` and no requests are eunqueued the throttler waits until
        a new request arrives.

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

        Returns a tuple of the form (`waiting`, `proceed`) where `waiting` indicates if the
        throttler has to wait while `proceed` indicates if the throttler has to proceed.

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
