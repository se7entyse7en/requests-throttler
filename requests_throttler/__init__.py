__title__ = 'RequestsThrottler'
__version__ = '0.2.3'
__author__ = 'Lou Marvin Caraig'
__author_email__ = 'loumarvincaraig@gmail.com'
__project_url__ = 'https://github.com/se7entyse7en/requests-throttler'
__license__ = 'Apache 2.0'
__copyright__ = 'Copyright 2014 Lou Marvin Caraig'


from . import utils
from .throttled_request import ThrottledRequest
from .throttler import BaseThrottler
from .exceptions import *
