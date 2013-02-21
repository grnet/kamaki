Extending kamaki.clients
========================

By default, kamaki clients are REST clients (they manage HTTP requests and responses to communicate with services). This is achieved by importing the connection module, which is an httplib wrapper.

Connection
----------

The connection module features an error handling and logging system, a lazy response mechanism, a pooling mechanism as well as concurrency control for thread-demanding client functions (e.g. store upload).

How to build a client
---------------------

All service clients consist of a subclass of the Client class and implement separate client functionalities as member methods. There is also an error class to raise exceptions that can be handled by kamaki interfaces.

.. code-block:: python
    
    #  ${KAMAKI_PATH}/kamaki/clients/mynewclient.py

    from kamaki.clients import Client, ClientError

    class MyNewClient(Client):
        """MyNewClient Description Here"""

        def my_first_method(self, **args):
            """Method description"""
            try:
                ...
                method code
                ...
            except SomeKnownException as e1:
                raise ClientError('MyError: %s' % e1)
            except SomeOtherException as e2:
                raise ClientError('MyError: %s' % e2)

        def my_second_method(self, **params):
            """Method description"""
            ...

Custom clients can use a set of convenience methods for easy HTTP requests

.. code-block:: python

    def get(self, path, **kwargs)
    def head(self, path, **kwargs)
    def post(self, path, **kwargs)
    def put(self, path, **kwargs)
    def delete(self, path, **kwargs)
    def copy(self, path, **kwargs)
    def move(self, path, **kwargs)

How to use your client
----------------------

External applications must instantiate a MyNewClient object.

.. code-block:: python

    from kamaki.clients import ClientError
    from kamaki.clients.mynewclient import MyNewClient

    ...
    try:
        cl = MyNewClient(args)
        cl.my_first_method(other_args)
    except ClientError as cle:
        print('Client Error: %s' % cle)
    ...

Concurrency control
-------------------

Kamaki clients may handle multiple requests at once, using threads. In that case, users might implement their own thread handling mechanism, use an external solution or take advantage of the mechanism featured in kamaki.clients

.. code-block:: python

    from threading import enumerate
    from kamaki.clients import SilentEvent
    ...

    class MyNewClient(Client):
        ...

        def _single_threaded_method(self, **args):
            ...
            request code
            ...

        def multithread_method(self):
            thread_list = []
            self._init_thread_limit()
            while some_condition or thread_list:
                ...
                event = SilentEvent(self._single_threaded_method, **args)
                event.start()
                thread_list.append(event)
                thread_list = self._watch_thread_limit(thread_list)