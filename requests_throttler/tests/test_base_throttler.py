import unittest

import requests

from requests_throttler.throttled_request import ThrottledRequest
from requests_throttler.throttler import \
    BaseThrottler, \
    THROTTLER_STATUS, \
    THROTTLER_STATUS_DEPENDENCIES, \
    ThrottlerStatusError, \
    FullRequestsPoolError


class TestBaseThrottler(unittest.TestCase):

    def setUp(self):
        self.default_delay = 0.3
        self.default_request = requests.Request(method='GET', url='http://www.google.com')

    def test_base_throttler(self):
        bt = BaseThrottler(name='bt')
        self.assertEqual('bt', bt.name)
        self.assertIsNone(bt._requests_pool.maxlen)
        self.assertEqual(0, bt.delay)
        self.assertEqual('initialized', bt._status)
        self.assertEqual(0, bt.successes)
        self.assertEqual(0, bt.failures)
        bt._inc_successes()
        self.assertEqual(1, bt.successes)
        bt._inc_failures()
        self.assertEqual(1, bt.failures)

        bt = BaseThrottler(name='bt', delay=5)
        self.assertEqual(5, bt.delay)

        bt = BaseThrottler(name='bt', reqs_over_time=(5, 15))
        self.assertEqual(3, bt.delay)

        bt = BaseThrottler(name='bt', delay=1, reqs_over_time=(5, 15))
        self.assertEqual(1, bt.delay)

        with self.assertRaises(ValueError):
            BaseThrottler(name='bt', delay=-1)

        with self.assertRaises(ValueError):
            BaseThrottler(name='bt', reqs_over_time=(-1, -1))

        for status in THROTTLER_STATUS:
            bt._status = status
            self.assertEqual(status, bt._status)

    def test_set_status(self):
        bt = BaseThrottler()
        for k, v1 in THROTTLER_STATUS_DEPENDENCIES.iteritems():
            bt._status = k
            for v2 in THROTTLER_STATUS:
                if v2 in v1:
                    bt.status = v2
                    self.assertEqual(v2, bt._status)
                else:
                    with self.assertRaises(ThrottlerStatusError):
                        bt.status = v2
                bt._status = k
            
        with self.assertRaises(ThrottlerStatusError):
            bt.status = 'invalid-status'

    def test_start(self):
        bt = BaseThrottler()
        for status in set(THROTTLER_STATUS).difference(set(['initialized'])):
            bt._status = status
            self.assertRaises(ThrottlerStatusError, bt.start)

    def test_shutdown(self):
        bt = BaseThrottler()
        for status in THROTTLER_STATUS:
            bt._status = status
            if status in ['stopped', 'ending', 'ended']:
                self.assertRaises(ThrottlerStatusError, bt.shutdown)
            else:
                bt.shutdown()
                self.assertTrue(bt._wait_enqueued)
                self.assertEqual('stopped', bt._status)

        for status in THROTTLER_STATUS:
            bt._status = status
            if status in ['stopped', 'ending', 'ended']:
                self.assertRaises(ThrottlerStatusError, bt.shutdown)
            else:
                bt.shutdown(wait_enqueued=False)
                self.assertFalse(bt._wait_enqueued)
                self.assertEqual('stopped', bt._status)

    def test_context(self):
        with BaseThrottler() as bt:
            self.assertIn(bt._status, ['runnning', 'waiting'])
        self.assertIn(bt._status, ['stopped', 'ending'])

    def test_pause(self):
        bt = BaseThrottler()
        for status in THROTTLER_STATUS:
            bt._status = status
            if status not in ['running', 'waiting']:
                self.assertRaises(ThrottlerStatusError, bt.pause)
            else:
                bt.pause()
                self.assertEqual('paused', bt._status)

    def test_unpause(self):
        bt = BaseThrottler()
        for status in THROTTLER_STATUS:
            bt._status = status
            if status != 'paused':
                self.assertRaises(ThrottlerStatusError, bt.unpause)
            else:
                bt.unpause()
                self.assertEqual('running', bt._status)

    def test_submit(self):
        bt = BaseThrottler(delay=self.default_delay)
        bt.start()

        throttled_request = bt.submit(self.default_request)
        self.assertIsInstance(throttled_request, ThrottledRequest)
        reqs = [self.default_request for i in range(0, 10)]

        throttled_requests = bt.multi_submit(reqs)
        self.assertIsInstance(throttled_requests, list)
        self.assertEqual(10, len(throttled_requests))

        bt.shutdown()

        with BaseThrottler(delay=self.default_delay) as bt:
            throttled_request = bt.submit(self.default_request)
            self.assertIsInstance(throttled_request, ThrottledRequest)

            reqs = [self.default_request for i in range(0, 10)]
            throttled_requests = bt.multi_submit(reqs)
            self.assertIsInstance(throttled_requests, list)
            self.assertEqual(10, len(throttled_requests))

    def test_do_submit(self):
        bt = BaseThrottler(delay=self.default_delay)
        bt.start()

        throttled_request = bt._submit(self.default_request)
        self.assertIsInstance(throttled_request, ThrottledRequest)

        bt.shutdown()

        with BaseThrottler(delay=self.default_delay) as bt:
            throttled_request = bt._submit(self.default_request)
            self.assertIsInstance(throttled_request, ThrottledRequest)

    def test_submit_paused(self):
        ### deadlock
        throttled_requests = []
        with BaseThrottler(delay=self.default_delay) as bt:
            bt.pause()

            tr_1 = bt.submit(self.default_request)
            self.assertEqual(1, len(bt._requests_pool))

            tr_2 = bt.submit(self.default_request)
            self.assertEqual(2, len(bt._requests_pool))

            tr_3 = bt.submit(self.default_request)
            self.assertEqual(3, len(bt._requests_pool))

            throttled_requests = [tr_1, tr_2, tr_3]
            [self.assertIsInstance(tr, ThrottledRequest) for tr in throttled_requests]

            [self.assertFalse(tr.finished) for tr in throttled_requests]
            [self.assertIsNone(tr._response) for tr in throttled_requests]

            bt.unpause()

        bt.wait_end()

        [self.assertTrue(tr.finished) for tr in throttled_requests]
        [self.assertIsNotNone(tr._response) for tr in throttled_requests]

    def test_prepare_request(self):
        bt = BaseThrottler()

        throttled_request, prepared = bt._prepare_request(self.default_request)
        self.assertTrue(prepared)

        self.assertFalse(throttled_request.finished)
        self.assertIsNone(throttled_request._response)
        self.assertIsNone(throttled_request._exception)

        request = requests.Request(method=None, url=None)
        throttled_request, prepared = bt._prepare_request(request)
        self.assertFalse(prepared)

        self.assertEqual(1, bt.failures)
        self.assertTrue(throttled_request.finished)
        self.assertIsNone(throttled_request._response)
        self.assertIsNotNone(throttled_request._exception)

        with self.assertRaises(Exception):
            throttled_request.response

        self.assertIsInstance(throttled_request._exception, Exception)

    def test_send_request(self):
        bt = BaseThrottler()

        throttled_request, _ = bt._prepare_request(self.default_request)
        bt._send_request(throttled_request)
      
        self.assertEqual(1, bt.successes)
        self.assertEqual(0, bt.failures)
        self.assertTrue(throttled_request.finished)
        self.assertIsNotNone(throttled_request._response)
        self.assertIsNone(throttled_request._exception)

        bt = BaseThrottler()

        request = requests.Request(method=None, url='http://None')
        throttled_request, _ = bt._prepare_request(request)
        bt._send_request(throttled_request)
      
        self.assertEqual(1, bt.failures)
        self.assertEqual(0, bt.successes)
        self.assertTrue(throttled_request.finished)
        self.assertIsNone(throttled_request._response)
        self.assertIsNotNone(throttled_request._exception)
        self.assertIsInstance(throttled_request._exception, Exception)

        with self.assertRaises(Exception):
            throttled_request.response

    def test_enqueue_request(self):
        bt = BaseThrottler(max_pool_size=1)
        throttled_request, _ = bt._prepare_request(self.default_request)
        bt._enqueue_request(throttled_request)
        self.assertEqual(1, len(bt._requests_pool))

        throttled_request, _ = bt._prepare_request(self.default_request)
        with self.assertRaises(FullRequestsPoolError):
            bt._enqueue_request(throttled_request)

    def test_dequeue_request(self):
        bt = BaseThrottler()
        for wait_enqueued in [True, False]:
            bt._status = 'stopped'
            request = bt._dequeue_request()
            self.assertIsNone(request)

        bt._status = 'running'
        throttled_request, _ = bt._prepare_request(self.default_request)
        bt._enqueue_request(throttled_request)
        request = bt._dequeue_request()
        self.assertEqual(throttled_request, request)

    def test_dequeue_condition(self):
        bt = BaseThrottler()

        bt._status = 'running'
        self.assertEqual((True, False), bt._dequeue_condition())
        self.assertEqual('waiting', bt._status)

        bt._status = 'paused'
        self.assertEqual((True, False), bt._dequeue_condition())
        self.assertEqual('paused', bt._status)

        for wait_enqueued in [True, False]:
            bt._status = 'stopped'
            bt._wait_enqueued = wait_enqueued
            self.assertEqual((False, False), bt._dequeue_condition())
        self.assertEqual('ending', bt._status)

        throttled_request, _ = bt._prepare_request(self.default_request)
        bt._enqueue_request(throttled_request)

        bt._status = 'running'
        self.assertEqual((False, True), bt._dequeue_condition())
        self.assertEqual('running', bt._status)

        bt._status = 'paused'
        self.assertEqual((True, False), bt._dequeue_condition())
        self.assertEqual('paused', bt._status)
        
        for wait_enqueued in [True, False]:
            bt._status = 'stopped'
            bt._wait_enqueued = wait_enqueued
            if wait_enqueued:
                self.assertEqual((False, True), bt._dequeue_condition())
            else:
                self.assertEqual((False, False), bt._dequeue_condition())
        self.assertEqual('ending', bt._status)
