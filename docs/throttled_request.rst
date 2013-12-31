:mod:`throttled_request` --- the module containing the objects to throttle
--------------------------------------------------------------------------

.. automodule:: requests_throttler.throttled_request

.. currentmodule:: requests_throttler.throttled_request


:class:`ThrottledRequest` --- the throttled request object
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: ThrottledRequestAlreadyFinished

.. autoclass:: ThrottledRequest

   .. automethod:: __init__
   .. autoattribute:: request
   .. autoattribute:: finished
   .. autoattribute:: response
   .. autoattribute:: exception
   .. automethod:: get_response(timeout=0)
   .. automethod:: get_exception(timeout=0)
