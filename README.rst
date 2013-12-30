RequestsThrottler: HTTP requests throttler
==========================================

RequestsThrottler is an Apache2 Licensed HTTP library, written in Python, and powered by futures and `Requests <https://github.com/kennethreitz/requests>`_.

With RequestsThrottler you can easily throttle HTTP requests! After having created your throttler with a delay of your choice, you just have to:

1. Start the throttler 
2. Submit your requests
3. Shutdown the throttler

Here's an example:
::

    bt = BaseThrottler(name='base-throttler', delay=1.5)
    request = requests.Request(method='GET', url='http://www.google.com')

    bt.start()
    throttled_request = bt.submit(request)
    bt.shutdown()

    response = throttled_request.response


Too hard? Then just submit your requests inside a with statement! Here's an example:
::

    with BaseThrottler(name='base-throttler', delay=1.5):
        request = requests.Request(method='GET', url='http://www.google.com')
        throttled_request = bt.submit(request)

    response = throttled_request.response


Try also the ``example.py`` by running:
::

    >>> python example.py


Installation
------------

Use ``pip`` to install RequestsThrottler:
::

    >>> pip install RequestsThrottler


Features
--------

- ``BaseThrottler`` a simple throttler with a fixed amount of delay
