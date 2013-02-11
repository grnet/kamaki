Creating applications with kamaki API
=====================================


Kamaki features a clients API for building third-party client applications that communicate with OpenStack and / or Synnefo cloud services. The package is called kamaki.clients and contains a number of 

A good example of an application build on kamaki.clients is kamaki.cli, the command line interface of kamaki. 

Since synnefo services are build as OpenStack extensions, an inheritance approach has been chosen for implementing clients for both. In specific, the *compute*, *storage* and *image* modules are clients of the OS compute, OS storage, respectively. On the contrary, all the other modules are Synnefo extensions (*cyclades* extents *compute*, *pithos* and *pithos_rest_api* extent *storage*) or novel synnefo services (e.g. *astakos*, *image* for *plankton*).

Setup a client instance
-----------------------

External applications may instantiate one or more kamaki clients.

.. code-block:: python
    :emphasize-lines: 1

    Example 1.1: Instantiate Cyclades and Pithos client


    from kamaki.clients.cyclades import CycladesClient
    from kamaki.clients.pithos import PithosClient

    my_cyclades_client = CycladesClient(base_url, token)
    my_pithos_client = PithosClient(base_url, token, account, container)

.. note:: *cyclades* and *pithos* clients inherit all methods of *compute* and *storage* clients respectively. Separate compute or storage objects should be used only when implementing applications for strict OS Compute or OS Storage services.

.. note:: *account* variable is usually acquired by the following astakos call

    .. code-block:: python

        from kamaki.clients.astakos import AstakosClient
        astakos = AstakosClient(astakos_base_url, token)
        account = astakos.term('uuid')

Use client methods
------------------

Client methods can now be called. Developers are advised to consult :ref:`the-client-api-ref` for details on the available methods and how to use them.

In the following example, the *cyclades* and *pithos* clients of example 1.1 are used to extract some information, that is then printed to the standard output.


.. code-block:: python
    :emphasize-lines: 1,2

    Example 1.2: Print server name and OS for server with server_id
                Print objects in container mycont


    srv = my_cyclades_client.get_server_info(server_id)
    print("Server Name: %s (with OS %s" % (srv['name'], srv['os']))

    obj_list = my_pithos_client.list_objects(mycont)
    for obj in obj_list:
        print('  %s of %s bytes' % (obj['name'], obj['bytes']))

.. code-block:: console
    :emphasize-lines: 1

    Run of examples 1.1 + 1.2


    $ python test_script.py
    Server Name: A Debian Server (with OS Debian Base)
      lala.txt of 34 bytes
      test.txt of 1232 bytes
      testDir/ of 0 bytes
    $ 

Error handling
--------------

The kamaki.clients standard error is ClientError. A ClientError is raised for any kind of kamaki.clients errors (errors reported by servers, type errors in arguments, etc.).

A ClientError contains::

    message     The error message.
    status      An optional error code, e.g. after a server error.
    details     Optional list of messages with error details.

The following example concatenates examples 1.1 and 1.2 plus error handling

.. code-block:: python

    Example 1.3: Error handling


    from kamaki.clients.cyclades import CycladesClient
    from kamaki.clients.pithos import PithosClient

    try:
        my_cyclades_client = CycladesClient(base_url, token)
    except ClientError:
        print('Failed to initialize Cyclades client')

    try:
        my_pithos_client = PithosClient(base_url, token, account, container)
    except ClientError:
        print('Failed to initialize Pithos+ client')

    try:
        srv = my_cyclades_client.get_server_info(server_id)
        print("Server Name: %s (with OS %s" % (srv['name'], srv['os']))

        obj_list = my_pithos_client.list_objects(mycont)
        for obj in obj_list:
            print('  %s of %s bytes' % (obj['name'], obj['bytes']))
    except ClientError as e:
        print('Error: %s' % e)
        if e.status:
            print('- error code: %s' % e.status)
        if e.details:
            for detail in e.details:
                print('- %s' % detail)
