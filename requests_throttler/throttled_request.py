"""
.. module:: throttled_request
   :synopsis: The module containing the class representing a request to throttle

.. moduleauthor:: Lou Marvin Caraig <loumarvincaraig@gmail.com>

This module provides the class representing the requests to throttle.

"""

import threading

from requests_throttler.utils import locked


class ThrottledRequestAlreadyFinished(Exception):
    """Exception that occurs when a finished is tried to change some attributes to a finished
    throttled request
    
    :param msg: the message
    :type msg: string

    """

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


class ThrottledRequest(object):
    """This class represents a throttled request

    :param request: the prepared request to throttle
    :type request: requests.PreparedRequest
    :param finished: the flag that indicates if the request has been sent and a response has
                     been received or an exception occured
    :type finished: boolean
    :param response: the response corresponding to the request
    :type response: requests.Response
    :param exception: the exception occured during the request (:const:`None` if no exceptions
                      occured)
    :type exception: Exception
    :param not_done: the condition on which to wait to have the response an to make the
                     object thread-safe
    :type not_done: threading.Condition

    """

    def __init__(self, request):
        """Create a throttled request with the given prepared request

        :param request: the prepared request to throttle
        :type request: requests.PreparedRequest

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
        """The corresponding prepared request

        :getter: Returns :attr:`request`
        :type: requests.PreparedRequest

        """
        return self._request

    @property
    @locked('not_done')
    def finished(self):
        """The flag that indicates if the request has been processed

        :getter: Returns :attr:`finished`
        :type: boolean

        """
        return self._finished

    @property
    def response(self):
        """The response obtained by processing the request

        :getter: Returns :attr:`response`
        :setter: Sets the response received after the processing of the request
        :raise:
            :ThrottledRequestAlreadyFinshed: if the throttled request has already finished
        :type: requests.Response

        """
        return self.get_response(timeout=None)

    @response.setter
    @locked('not_done')
    def response(self, response):
        """Set the response that has been received during the processing of the request

        :param response: the response to set
        :type response: requests.Response
        :raise:
            :ThrottledRequestAlreadyFinshed: if the throttled request has already finished

        """
        if self._finished is True:
            raise ThrottledRequestAlreadyFinished("ThrottledRequest already finished")
        self._response = response
        self._finished = True
        self.not_done.notify()

    @property
    def exception(self):
        """Return the exception that occurs by processing the request (blocking)

        :getter: Returns :attr:`exception`
        :setter: Sets the exception raised during the processing of the request
        :raise:
            :ThrottledRequestAlreadyFinshed: if the throttled request has already finished
        :type: Exception

        """

        return self.get_exception(timeout=None)

    @exception.setter
    @locked('not_done')
    def exception(self, exception):
        """Set the exception that has been raised during the processing of the request

        :param response: the exception to set
        :type response: Exception
        :raise:
            :ThrottledRequestAlreadyFinshed: if the throttled request has already finished

        """
        if self._finished is True:
            raise ThrottledRequestAlreadyFinished("ThrottledRequest already finished.")

        self._exception = exception
        self._finished = True
        self.not_done.notify()

    @locked('not_done')
    def get_response(self, timeout=0):
        """Return the response obtained by processing the request

        If ``timeout`` is :const:`None` it waits until a response has been obtained or an
        execption occurs. When a response has been obtained it is returned, if an exception
        occurs it is raised.
        If ``timeout`` is not :const:`None` and no response still hasn't been obtained after
        the expiration of `timeout`, then :const:`None` is returned.

        :param timeout: the timeout value in seconds (default: 0)
        :type timeout: float
        :return: :attr:`response` or :const:`None`
        :rtype: requests.Response

        """
        if self._wait_finished(timeout):
            if self._exception is None:
                return self._response
            raise self._exception
        else:
            return None

    @locked('not_done')
    def get_exception(self, timeout=0):
        """Return the exception that occurs by processing the request

        If ``timeout`` is :const:`None` it waits until a response has been obtained or an
        execption occurs. If an exception occurs it is returned otherwise :const:`None` is
        returned.
        If ``timeout`` is not :const:`None` and no response still hasn't been obtained
        :const:`None` is returned.

        :param timeout: the timeout value in seconds (default: 0)
        :type timeout: float
        :return: :attr:`exception` or :const:`None`
        :rtype: Exception

        """
        if self._wait_finished(timeout):
            return self._exception
        return None

    def _wait_finished(self, timeout=None):
        """Wait for the request for being finished with an optional ``timeout``

        The waiting is blocking and can last indefenetely if ``timeout`` is :const:`None`.

        :param timeout: the timeout value in seconds (default: 0)
        :return: :const:`True` if the request has been processed, :const:`False` otherwise
        :rtype: boolean

        """
        if timeout is None:
            while not self._finished:
                self.not_done.wait()
        else:
            self.not_done.wait(timeout)
            if not self._finished:
                return False
        return True
