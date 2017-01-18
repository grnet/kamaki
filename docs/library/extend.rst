Extending kamaki.clients
========================

All service client classes are subclasses of the ``kamaki.clients.Client``
class. They implement specific client functionalities as member methods. This,
along with the ``kamaki.clients.ClientError`` error class are enough to
implement your own client or extend an existing one.

Add a new client
----------------

First, create a new python file under ``${KAMAKI_ROOT/kamaki/clients`` the name
of which will be the name of your client module.

Custom clients can use a set of convenient methods which simplify calling the
API.

.. code-block:: python

    def get(self, path, **kwargs)
    def head(self, path, **kwargs)
    def post(self, path, **kwargs)
    def put(self, path, **kwargs)
    def delete(self, path, **kwargs)
    def copy(self, path, **kwargs)
    def move(self, path, **kwargs)

In the following example, we will create a client that makes a "GET" and a
"POST" to a cloud endpoint at
``https://www.example.org/some/api/endpoint/my/content``:

.. note:: The API endpoint ``https://www.example.org/some/api/endpoint is
    provided by the caller. The suffix ``/my/content`` is call-specific

.. code-block:: python

    #  ${KAMAKI_PATH}/kamaki/clients/mynewclient.py

    import logging
    from kamaki.clients import Client, ClientError

    logger = getLogger(__name__)


    class MyNewClient(Client):
        """MyNewClient Description Here"""

        def list(self, **params):
            """
            :returns: a list of content objects [{...}, {...}, ...]
            """
            r = self.get('/my/contents', **params)
            return r.json

        def create(self, data, **args):
            """
            :returns: True if new content is created, False if already there
            """
            logger.info("Create new content")
            try:
                r = self.post(json=data, **args, success=202)
            except ClientError as ce:
                if ce.status in (201, ):
                    logger.debug("Content was already there")
                    return False
                raise

            logger.debug("New content was added")
            return True

The above script showcases some of the conveniences provided by the kamaki
library. The "r.json" attribute parses the response data and extracts a dict or
list. The "json=data" parameter in "post" tells kamaki that this is a json piece
of data, so kamaki will format it and update the request headers accordingly.

How to use your client
----------------------

.. code-block:: python

    from kamaki.clients import ClientError
    from kamaki.clients.mynewclient import MyNewClient

    apiendpoint = "https://www.example.org/some/api/endpoint"
    TOKEN = 'Some-token'

    try:
        cl = MyNewClient(apiendpoint, TOKEN)
        print cl.list(other_args)
    except ClientError as cle:
        print("Client Error: {0}".format(cle))

Concurrency control
-------------------

Kamaki clients may handle multiple requests with threads. The easiest way is
using the `async_run` method, fed with a list of argument dictionaries (one for
each call of the single method).

.. code-block:: python

    class MyNewClient(Client):
        ...

        def _single_threaded_method(self, **args):
            ...

        def multithread_method(self):
            kwarg_list = [kwarg for each run]
            self.async_run(self._single_threaded_method, kwarg_list)

Testing
-------

The kamaki.clients package contains a set of fine-grained unit-tests for all
APIs.

.. note:: unit tests require the optional python-mock package, version 1.X or
    greater

Using the tests
^^^^^^^^^^^^^^^

First, the source code of kamaki must be accessible. If this is not the case,
the source code can be obtained from here:

`https://code.grnet.gr/projects/kamaki/files <https://code.grnet.gr/projects/kamaki/files>`_

In each package under kamaki.clients, there is a test module (`test.py`). To
run all tests, run the test.py file from kamaki.clients

.. code-block:: console

    $ cd ${KAMAKI_SOURCE_LOCATION}/kamaki/clients
    $ python test.py

To test a specific class, add the class name as an argument. e.g., for the
Client class:

.. code-block:: console

    $ python test.py Client

To test a specific method in a class, apply an extra argument, e.g., for the
request method in the Client class:

.. code-block:: console

    $ python test.py Client request

Each package contains a test module (test.py) which is also runnable from the
command line. e.g., in the pithos package there is a test module which
contains, among others, the **download** sub-test:

.. code-block:: console

    $ cd pithos

    # Run all kamaki.clients.pithos tests
    $ python test.py

    # Run all kamaki.clients.pithos.PithoClient tests
    $ python test.py Pithos

    # Test kamaki.clients.pithos.PithosClient.download
    $ python test.py Pithos download

To fully test a specific package, run test.py from the package location. e.g.,
to test everything in kamaki.clients.pithos package:

.. code-block:: console

    $ cd pithos
    $ python test.py

Mechanism
^^^^^^^^^

Each folder / package contains a test.py file, where its test module lives. All
test modules contain a set of classes that extend the TestCase class. They also
contain a main method to run the tests.

By convention, testing classes have the same name as the class they test.
Methods not grouped in classes are tested by classes named after their
respective module.

For example, the *kamaki.clients.pithos.PithosClient* class is tested by the
*kamaki.clients.pithos.test.PithosClient* class, while the methods in
*kamaki.clients.utils* module are tested by *kamaki.clients.utils.test.Utils*.

Adding unit tests
^^^^^^^^^^^^^^^^^

After modifying or extending *kamaki.clients* method, classes, modules or
packages, it is a good practice to also modify or extend the corresponding
unit tests. What's more, it is recommended to modify or implement the testing
of new behavior before implementing the behavior itself. The goal is to
preserve an 1 to 1 mapping between methods and their tests.

Modifying an existing method
""""""""""""""""""""""""""""

In case of an existing method modification, the programmer has to modify the
corresponding test as well. By convention, the test method is located in the
test module under the same package, in a TestCase subclass that is named with a
name similar to the package or class that contains the tested method.

Example: to modify *kamaki.clients.pithos.PithosRestClient.object_get*, the
programmer has to also adjust the
*kamaki.clients.pithos.test.PithosRestClient.test.object_get* method.

Adding a new method
"""""""""""""""""""

To implement a new method in an existing class, developers are encouraged to
implement the corresponding unit test first. In order to do that, they should
find the testing class that is mapped to the class or module they work on.

Example: Adding **list_special** to *kamaki.clients.astakos.AstakosClient*,
requires changes to *kamaki.clients.astakos.test.AstakosClient* too, as shown
bellow:

.. code-block:: python

    # file: ${kamaki}/kamaki/clients/astakos/__init__.py

    class AstakosClient(TestCase):
        ...
        def test_list_special(self):
            """Test the list_special method"""
            ...

Implementing a new class or module
""""""""""""""""""""""""""""""""""

Each class or module needs a separate test sub-module. By convention, each
class or module under *kamaki.clients*, should be located in a separate
directory.

Example 1: To add a NewService class that implements *kamaki.clients.Client*:

* Create a new_service package and implement the unit tests in
    *kamaki.clients.new_service.test*:

.. code-block:: console

    $ mkdir new_service && touch new_service/test.py

* Create the package file for the package implementation:

.. code-block:: console

    $ touch new_service/__init__.py

* Create the test class and methods in *kamaki.clients.new_service.test*

.. code-block:: python

    # file: ${kamaki}/kamaki/clients/new_service/test.py
    from unittest import TestCase

    class NewService(TestCase):

        def test_method1(self):
            ...

* Create the NewService and its actual functionality in
    kamaki.clients.new_service

.. code-block:: python

    # file: ${kamaki}/kamaki/clients/new_service/__init__.py
    from kamaki.clients import Client

    class NewService(Client):

        def method1(self, ...):
            ...

* Import the test class to *kamaki.clients.test*:

.. code-block:: python

    # file: ${kamaki}/kamaki/clients/test.py
    from kamaki.clients.new_service.test import NewService

.. note:: If the new class or module is part of an existing sub-package, it is
    acceptable to append its testing class in the existing test.py file of the
    sub-package it belongs to. For example, the
    kamaki.clients.pithos.PithosClient and
    kamaki.clients.pithos.rest_api.PithosRestClient classes are tested by two
    different classes (PithosClient and PithosRestClient respectively) in the
    same module (kamaki.clients.pithos.test).

