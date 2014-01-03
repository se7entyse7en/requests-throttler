import time
import unittest
import calendar
from datetime import datetime

from requests_throttler.utils import \
    Timer, \
    NoCheckpointSetError


class TestTimerTestCase(unittest.TestCase):

    def setUp(self):
        self.default_start = float(calendar.timegm(datetime(2013, 12, 25, 0, 0).timetuple()))
        self.places = 2

    def test_timer(self):
        now = time.time()
        timer = Timer()
        self.assertAlmostEqual(now, timer.start, places=self.places)
        self.assertIsNone(timer.checkpoint)

        now = time.time()
        timer = Timer(checkpoint=200.0)
        self.assertAlmostEqual(now, timer.start, places=self.places)
        self.assertAlmostEqual(200.0, timer.checkpoint)

        timer = Timer(start=self.default_start)
        self.assertAlmostEqual(self.default_start, timer.start)
        self.assertIsNone(timer.checkpoint)

    def test_elapsed_time(self):
        timer = Timer(start=self.default_start)
        self.assertAlmostEqual(time.time() - self.default_start, timer.total_elapsed(),
                               places=self.places)

        self.assertRaises(NoCheckpointSetError, timer.elapsed)
        self.assertRaises(NoCheckpointSetError, timer.get_elapsed_and_set_checkpoint)

        timer.checkpoint = self.default_start + 100
        self.assertAlmostEqual(time.time() - self.default_start - 100, timer.elapsed(),
                               places=self.places)

        self.assertAlmostEqual(time.time() - self.default_start - 100,
                               timer.get_elapsed_and_set_checkpoint(change=False),
                               places=self.places)
        self.assertAlmostEqual(self.default_start + 100, timer.checkpoint)
        self.assertAlmostEqual(time.time() - self.default_start - 100,
                               timer.get_elapsed_and_set_checkpoint(change=True),
                               places=self.places)
        self.assertAlmostEqual(time.time(), timer.checkpoint, places=self.places)

        timer.get_elapsed_and_set_checkpoint(change=True, new_checkpoint=200.0)
        self.assertAlmostEqual(200.0, timer.checkpoint)
