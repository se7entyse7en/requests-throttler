import threading

from requests_throttler.utils import locked


class ThrottledRequestAlreadyFinished(Exception):

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


class ThrottledRequest(object):
    """This class represents a throttled request


    Attributes:
        `_request` - the prepared request to throttle
        `_finished` - the flag that indicates if the request has been sent and a response has
                      been received or an exception occured
        `_response` - the response corresponding to the request
        `_exception` - the exception occured during the request (`None` if no exceptions
                       occured)
        `not_done` - the condition on which to wait to have the response an to make the
                     object thread-safe

    """

    def __init__(self, request):
        """Create a throttled request with the given prepared request

        `request` - the prepared request to throttle

        """
        self._request = request
        self._finished = False
        self._response = None
        self._exception = None
        self.not_done = threading.Condition(threading.Lock())

    def __str__(self):
        return "[{class_name} <{request}, {response}, {finished}, {exception}>]".format(
            class_name="ThrottledRequest",
            request=repr(self._request),
            response=repr(self._response),
            finished=repr(self._finished),
            exception=repr(self._exception))

    @property
    @locked('not_done')
    def request(self):
        """Return the corresponding request"""

        return self._request

    @property
    @locked('not_done')
    def finished(self):
        """Return the flag that indicates if the request has been processed"""

        return self._finished

    @property
    def response(self):
        """Return the response obtained by processing the request (blocking)"""

        return self.get_response(timeout=None)

    @response.setter
    @locked('not_done')
    def response(self, response):
        """Set the response that has been received during the processing of the request

        It raises `ThrottledRequestAlreadyFinshed` if the throttled request has already
        finished.

        """
        if self._finished is True:
            raise ThrottledRequestAlreadyFinished("ThrottledRequest already finished")
        self._response = response
        self._finished = True
        self.not_done.notify()

    @locked('not_done')
    def get_response(self, timeout=0):
        """Return the response obtained by processing the request

        If `timeout` is `None` it waits until a response has been obtained or an execption
        occurs. When a response has been obtained it is returned, if an exception occurs it
        is raised.
        If `timeout` is not `None` and no response still hasn't been obtained `None` is
        returned.

        `timeout` - the timeout value in seconds (default: 0)

        """
        if self._wait_finished(timeout):
            if self._exception is None:
                return self._response
            raise self._exception
        else:
            return None

    @property
    def exception(self):
        """Return the exception that occurs by processing the request (blocking)"""

        return self.get_exception(timeout=None)

    @exception.setter
    @locked('not_done')
    def exception(self, exception):
        """Set the exception that has been raised during the processing of the request"""

        if self._finished is True:
            raise ThrottledRequestAlreadyFinished("ThrottledRequest already finished.")

        self._exception = exception
        self._finished = True
        self.not_done.notify()

    @locked('not_done')
    def get_exception(self, timeout=0):
        """Return the exception that occurs by processing the request

        If `timeout` is `None` it waits until a response has been obtained or an execption
        occurs. If an exception occurs it is returned otherwise `None` is returned.
        If `timeout` is not `None` and no response still hasn't been obtained `None` is
        returned.

        `timeout` - the timeout value in seconds (default: 0)

        """
        if self._wait_finished(timeout):
            return self._exception
        return None

    def _wait_finished(self, timeout=None):
        """Wait for the request for being finished with an optional `timeout`

        The waiting is blocking and can last indefenetely if `timeout` is `None`. Returns
        `True` if the request has been processed and `False` otherwise.

        `timeout` - the timeout value in seconds (default: 0)

        """
        if timeout is None:
            while not self._finished:
                self.not_done.wait()
        else:
            self.not_done.wait(timeout)
            if not self._finished:
                return False
        return True
