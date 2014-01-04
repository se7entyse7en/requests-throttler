import time
import unittest

import requests

from requests_throttler.throttled_request import \
    ThrottledRequest, \
    ThrottledRequestAlreadyFinished


class TestThrottledRequestCase(unittest.TestCase):

    def setUp(self):
        self.req_url = 'http://www.google.com'
        self.default_to = 0.1
        self.places = 2

    def test_blank_throttled_request(self):
        req = requests.Request(method='GET', url=self.req_url)
        throttled_request = ThrottledRequest(req)

        self.assertEqual(req, throttled_request.request)
        self.assertEqual(False, throttled_request.finished)
        self.assertIsNone(None, throttled_request.get_response(timeout=0))
        self.assertIsNone(None, throttled_request.get_exception(timeout=0))

    def test_response(self):
        req = requests.Request(method='GET', url=self.req_url)
        throttled_request = ThrottledRequest(req)
        res = requests.get(url=self.req_url)
        throttled_request.response = res

        with self.assertRaises(ThrottledRequestAlreadyFinished):
            throttled_request.response = res
        self.assertEqual(True, throttled_request.finished)

        self.assertEqual(res, throttled_request.get_response(timeout=0))
        self.assertEqual(res, throttled_request.response)

        self.assertEqual(None, throttled_request.get_exception(timeout=0))
        self.assertEqual(None, throttled_request.exception)

    def test_exception(self):
        req = requests.Request(method='GET', url=self.req_url)
        throttled_request = ThrottledRequest(req)
        e = Exception()
        throttled_request.exception = e

        with self.assertRaises(ThrottledRequestAlreadyFinished):
            throttled_request.exception = e

        self.assertEqual(True, throttled_request.finished)

        with self.assertRaises(Exception):
            throttled_request.get_response(timeout=0)
        with self.assertRaises(Exception):
            throttled_request.response

        self.assertEqual(e, throttled_request.get_exception(timeout=0))
        self.assertEqual(e, throttled_request.exception)

    def test_blank_throttled_request_timeouts(self):
        req = requests.Request(method='GET', url=self.req_url)
        throttled_request = ThrottledRequest(req)

        self.assertEqual(req, throttled_request.request)
        self.assertEqual(False, throttled_request.finished)

        now = time.time()
        self.assertIsNone(None, throttled_request.get_response(timeout=self.default_to))
        self.assertAlmostEqual(time.time(), now + self.default_to, places=self.places)

        now = time.time()
        self.assertIsNone(None, throttled_request.get_exception(timeout=self.default_to))
        self.assertAlmostEqual(time.time(), now + self.default_to, places=self.places)

    def test_response_timeouts(self):
        req = requests.Request(method='GET', url=self.req_url)
        throttled_request = ThrottledRequest(req)
        res = requests.get(url=self.req_url)
        throttled_request.response = res

        with self.assertRaises(ThrottledRequestAlreadyFinished):
            throttled_request.response = res
        self.assertEqual(True, throttled_request.finished)

        self.assertEqual(res, throttled_request.get_response(timeout=self.default_to))
        self.assertEqual(res, throttled_request.response)

        self.assertEqual(None, throttled_request.get_exception(timeout=self.default_to))
        self.assertEqual(None, throttled_request.exception)

    def test_exception_timeouts(self):
        req = requests.Request(method='GET', url=self.req_url)
        throttled_request = ThrottledRequest(req)
        e = Exception()
        throttled_request.exception = e

        with self.assertRaises(ThrottledRequestAlreadyFinished):
            throttled_request.exception = e

        self.assertEqual(True, throttled_request.finished)

        with self.assertRaises(Exception):
            throttled_request.get_response(timeout=self.default_to)
        with self.assertRaises(Exception):
            throttled_request.response

        self.assertEqual(e, throttled_request.get_exception(timeout=self.default_to))
        self.assertEqual(e, throttled_request.exception)

    def test_wait_finished(self):
        req = requests.Request(method='GET', url=self.req_url)
        throttled_request = ThrottledRequest(req)
        with throttled_request.not_done:
            self.assertEqual(False, throttled_request._wait_finished(timeout=self.default_to))
        
        res = requests.get(url=self.req_url)
        throttled_request.response = res
        with throttled_request.not_done:
            self.assertEqual(True, throttled_request._wait_finished(timeout=self.default_to))
