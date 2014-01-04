:mod:`throttler` --- the module containing the throttlers
---------------------------------------------------------

.. automodule:: requests_throttler.throttler

.. currentmodule:: requests_throttler.throttler


:class:`BaseThrottler` - the simplest requests throttler
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: ThrottlerStatusError

.. autoclass:: FullRequestsPoolError

.. autoclass:: BaseThrottler

   .. automethod:: __init__
   .. autoattribute:: name
   .. autoattribute:: delay
   .. autoattribute:: status
   .. autoattribute:: successes
   .. autoattribute:: failures
   .. automethod:: start
   .. automethod:: shutdown(wait_enqueued=True)
   .. automethod:: pause()
   .. automethod:: unpause()
   .. automethod:: submit
   .. automethod:: multi_submit
   .. automethod:: wait_end()
