Release History
---------------


0.2.3 (2014-02-16)
^^^^^^^^^^^^^^^^^^

- Fixed installation via ``pip`` (thanks to Gavin D'mello for reporting the problem)

  
0.2.2 (2014-01-15)
^^^^^^^^^^^^^^^^^^

- Added possibility to use a user-defined session when using ``BaseThrottler``
- Fixed example, updated README


0.2.1 (2014-01-14)
^^^^^^^^^^^^^^^^^^

- Added implicit way to set ``delay`` for ``BaseThrottler`` by using ``reqs_over_time``


0.2.0 (2014-01-04)
^^^^^^^^^^^^^^^^^^

- Reorganized modules
- Changed ``submit`` method signature in favor of two methods: ``submit`` and ``multi_submit``
- Added documentation


0.1.1 (2013-12-31)
^^^^^^^^^^^^^^^^^^

- Fixed not working previous release
- Changed example.py


0.1.0 (2013-12-30)
^^^^^^^^^^^^^^^^^^

- ``BaseThrottler`` a simple throttler with a fixed amount of delay
