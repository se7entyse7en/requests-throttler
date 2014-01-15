RequestsThrottler: HTTP requests throttler
==========================================

RequestsThrottler is an Apache2 Licensed HTTP library, written in Python, and powered by futures and `Requests <https://github.com/kennethreitz/requests>`_.
See the full documentation at `<http://pythonhosted.org/RequestsThrottler>`_.

With RequestsThrottler you can easily throttle HTTP requests! After having created your throttler with a delay of your choice, you just have to:

1. Start the throttler 
2. Submit your requests
3. Shutdown the throttler

Here's an example:
::

    import requests
    from requests_throttler import BaseThrottler

    bt = BaseThrottler(name='base-throttler', delay=1.5)
    request = requests.Request(method='GET', url='http://www.google.com')
    reqs = [request for i in range(0, 5)]

    bt.start()
    throttled_requests = bt.multi_submit(reqs)
    bt.shutdown()

    responses = [tr.response for tr in throttled_requests]


Too hard? Then just submit your requests inside a with statement! Here's an example:
::

    import requests
    from requests_throttler import BaseThrottler

    with BaseThrottler(name='base-throttler', delay=1.5) as bt:
        request = requests.Request(method='GET', url='http://www.google.com')
        reqs = [request for i in range(0, 5)]
        throttled_requests = bt.multi_submit(reqs)

    responses = [tr.response for tr in throttled_requests]


Installation
------------

Use ``pip`` to install RequestsThrottler:
::

    $ pip install RequestsThrottler


Features
--------

- ``BaseThrottler`` a simple throttler with a fixed amount of delay
