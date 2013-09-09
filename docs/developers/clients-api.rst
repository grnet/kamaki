Creating applications with kamaki API
=====================================

Kamaki features a clients API for building third-party client applications that
communicate with OpenStack and / or Synnefo cloud services. The package is
called kamaki.clients and servers as a lib.

A showcase of an application built on kamaki.clients is kamaki.cli, the command
line interface of kamaki.

Since synnefo services are build as OpenStack extensions, an inheritance
approach has been chosen for implementing clients for both. In specific,
the *compute*, *storage* and *image* modules are clients of the OS compute, OS
object-store, respectively. On the contrary, all the other modules are Synnefo
extensions (*cyclades* extents *compute*, *pithos* and *pithos_rest_api*
extent *storage*) or novel synnefo services (e.g. *astakos* for IM, *image*
for *plankton*).

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

.. note:: *cyclades* and *pithos* clients inherit all methods of *compute*
    and *storage* clients respectively. Separate compute or storage objects
    should be used only when implementing applications for strict OS Compute or
    OS Storage services.

Using endpoints to get the base_url
-----------------------------------

In OpenStack, each service (e.g. `compute`, `object-store`, etc.) has a number
of `endpoints`. These `endpoints` are actually URIs that are needed as prefixes
for the API calls the kamaki client generates. In this context, we need just
one of these these `endpoints`, the `publicURL`, which is also referred to as
`base_url` in kamaki client libraries.

In general, this is the suggested way of getting the base_url::

    1. From the deployment UI get the AUTHENTICATION_URL and TOKEN
        (Example 1.2)
    2. Use them to instantiate an AstakosClient
        (Example 1.2)
    3. Use AstakosClient instance to get the endpoints of the service of interest
        (Example 1.3)
    4. The 'publicURL' endpoint is the base_url we are looking for
        (Example 1.3)

The AstakosClient is a client for the Synnefo/Astakos server. Synnefo/Astakos
is an advanced identity server based on OpenStack identity specifications.
Therefore, it can be used to get the `base_url` values needed for initializing
kamaki clients. Kamaki simplifies this process with the astakos client library.

Let's review the process with examples.

First, an astakos client must be initialized (Example 1.2). An
AUTHENTICATION_URL and a TOKEN can be acquired from the synnefo deployment UI.

.. code-block:: python
    :emphasize-lines: 1

    Example 1.2: Initialize an astakos client

    from kamaki.clients.astakos import AstakosClient
    my_astakos_client = AstakosClient(AUTHENTICATION_URL, TOKEN)
        

Next, the astakos client can be used to retrieve the base_url values for the
servers of interest. In this case (Example 1.3) they are *cyclades*
and *pithos*. A number of endpoints is assigned to each service, but kamaki
clients only need the one labeled as ``publicURL``.

.. code-block:: python
    :emphasize-lines: 1

    Example 1.3: Retrieve cyclades and pithos base_url values

    cyclades_endpoints = my_astakos_client.get_service_endpoints('compute')
    cyclades_base_url = cyclades_endpoints['publicURL']

    pithos_endpoints = my_astakos_client.get_service_endpoints('object-store')
    pithos_base_url = pithos_endpoints['publicURL']

The ``get_service_endpoints`` method gets the service name as an argument. Here
are the service names for the most popular kamaki clients::

    storage, pithos     -->     object-store
    compute, cyclades   -->     compute
    image               -->     image
    astakos             -->     identity

Use client methods
------------------

Client methods can now be called. Developers are advised to
consult :ref:`the-client-api-ref` for details on the available methods and how
to use them.

In the following example, the *cyclades* and *pithos* clients of example 1.1
are used to extract some information, that is then printed to the standard
output.


.. code-block:: python
    :emphasize-lines: 1,2

    Example 1.4: Print server name and OS for server with server_id
                Print objects in container mycont


    srv = my_cyclades_client.get_server_info(server_id)
    print("Server Name: %s (with OS %s" % (srv['name'], srv['os']))

    obj_list = my_pithos_client.list_objects(mycont)
    for obj in obj_list:
        print('  %s of %s bytes' % (obj['name'], obj['bytes']))

.. code-block:: console
    :emphasize-lines: 1

    Run of examples 1.1 + 1.4


    $ python test_script.py
    Server Name: A Debian Server (with OS Debian Base)
      lala.txt of 34 bytes
      test.txt of 1232 bytes
      testDir/ of 0 bytes
    $ 

Error handling
--------------

The kamaki.clients standard error is ClientError. A ClientError is raised for
any kind of kamaki.clients errors (errors reported by servers, type errors in
arguments, etc.).

A ClientError contains::

    message     The error message.
    status      An optional error code, e.g. after a server error.
    details     Optional list of messages with error details.

The following example concatenates examples 1.1 to 1.4 plus error handling

.. code-block:: python

    Example 1.5: Error handling

    from kamaki.clients.astakos import AstakosClient
    from kamaki.clients.cyclades import CycladesClient
    from kamaki.clients.pithos import PithosClient

    try:
        my_astakos_client = AstakosClient(AUTHENTICATION_URL, TOKEN)
    except ClientError:
        print('Failed to authenticate user token')
        return 1

    try:
        cyclades_endpoints = my_astakos_client.get_service_endpoints('compute')
        cyclades_base_url = cyclades_endpoints['publicURL']
    except ClientError:
        print('Failed to get endpoints for cyclades')

    try:
        my_cyclades_client = CycladesClient(cyclades_base_url, token)
    except ClientError:
        print('Failed to initialize Cyclades client')

    try:
        pithos_endpoints = my_astakos_client.get_service_endpoints('object-store')
        pithos_base_url = pithos_endpoints['publicURL']
    except ClientError:
        print('Failed to get endpoints for pithos')

    try:
        my_pithos_client = PithosClient(pithos_base_url, token, account, container)
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


Scripts
-------

Batch-create servers
''''''''''''''''''''

.. code-block:: python

    #! /usr/bin/python

    from kamaki.clients.astakos import AstakosClient
    from kamaki.clients.cyclades import CycladesClient

    AUTHENTICATION_URL = 'https://accounts.example.com/identity/v2.0'
    TOKEN = 'replace this with your token'

    user = AstakosClient(AUTHENTICATION_URL, TOKEN)

    cyclades_endpoints = user.get_service_endpoints('compute')
    CYCLADES_URL = cyclades_endpoints['publicURL']
    cyclades = CycladesClient(CYCLADES_URL, TOKEN)

    #  (name, flavor-id, image-id)
    servers = [
        ('My Debian Server', 1, 'my-debian-base-image-id'),
        ('My Windows Server', 3, 'my-windows-8-image-id'),
        ('My Ubuntu Server', 3, 'my-ubuntu-12-image-id'),
    ]

    for name, flavor_id, image_id in servers:
        cyclades.create_server(name, flavor_id, image_id)


Batch-create 4 servers of the same kind
'''''''''''''''''''''''''''''''''''''''

.. code-block:: python

    #! /usr/bin/python

    from kamaki.clients.astakos import AstakosClient
    from kamaki.clients.cyclades import CycladesClient

    AUTHENTICATION_URL = 'https://accounts.example.com/identity/v2.0'
    TOKEN = 'replace this with your token'

    user = AstakosClient(AUTHENTICATION_URL, TOKEN)

    cyclades_endpoints = user.get_service_endpoints('compute')
    CYCLADES_URL = cyclades_endpoints['publicURL']
    cyclades = CycladesClient(CYCLADES_URL, TOKEN)

    for i in range(4):
        name, flavor_id, image_id = 'Server %s' % (i + 1), 3, 'some-image-id'
        cyclades.create_server(name, flavor_id, image_id)

Register a banch of pre-uploaded images
'''''''''''''''''''''''''''''''''''''''

.. code-block:: python

    #! /usr/bin/python

    from kamaki.clients import ClientError
    from kamaki.clients.astakos import AstakosClient
    from kamaki.clients.pithos import PithosClient
    from kamaki.clients.image import ImageClient

    AUTHENTICATION_URL = 'https://accounts.example.com/identity/v2.0'
    TOKEN = 'replace this with your token'
    IMAGE_CONTAINER = 'images'

    astakos = AstakosClient(AUTHENTICATION_URL, TOKEN)
    USER_UUID = astakos.user_term('uuid')

    PITHOS_URL = astakos.get_service_endpoints('object-store')['publicURL']
    pithos = PithosClient(PITHOS_URL, TOKEN, USER_UUID, IMAGE_CONTAINER)

    IMAGE_URL = astakos.get_service_endpoints('image')['publicURL']
    plankton = ImageClient(IMAGE_URL, TOKEN)

    for img in pithos.list_objects():
        IMAGE_PATH = img['name']
        try:
            r = plankton.register(
                name='Image %s' % img,
                location=(USER_UUID, IMAGE_CONTAINER, IMAGE_PATH))
            print 'Image %s registered with id %s' % (r['name'], r['id'])
        except ClientError:
            print 'Failed to register image %s' % IMAGE_PATH
