Creating applications with kamaki API
=====================================

Kamaki features a clients API for building third-party client applications that
communicate with Synnefo and (in most cases) OpenStack cloud services. The package is
called *kamaki.clients* and serves as a library.

A showcase of an application built on *kamaki.clients* is *kamaki.cli*, the
command line interface of kamaki.

Since Synnefo services are build as OpenStack extensions, an inheritance
approach has been chosen for implementing clients for both APIs. In specific,
the *compute*, *storage* and *image* modules are client implementations for the
OpenStack compute, OpenStack object-store and Image APIs respectively. The rest
of the modules implement the Synnefo extensions (i.e., *cyclades* and
*cyclades_rest_api* extents *compute*, *pithos* and *pithos_rest_api* extent
*storage*).

Setup a client instance
-----------------------

There is a client for every API. An external applications should instantiate
the kamaki clients that fit their needs.

For example, to manage virtual servers and stored objects / files, an
application would probably need the CycladesClient and PithosClient
respectively.

.. code-block:: python
    :emphasize-lines: 1

    Example 1.1: Instantiate Cyclades and Pithos clients


    from kamaki.clients.cyclades import CycladesClient
    from kamaki.clients.pithos import PithosClient

    cyclades = CycladesClient(computeURL, token)
    pithos = PithosClient(object-storeURL, token, account, container)

.. note:: *cyclades* and *pithos* clients inherit ComputeClient from *compute*
    and StorageClient from *storage*, respectively. Separate ComputeClient or
    StorageClient objects should be used only when implementing applications for
    strict OpenStack Compute or Storage services.

Using endpoints to get the authentication url
---------------------------------------------

In OpenStack, each service (e.g., `compute`, `object-store`, etc.) has a number
of `endpoints`. These `endpoints` are URIs which are used by kamaki as prefixes
to form the corresponding API calls. Client applications need just one of these
`endpoints`, namely the `publicURL` (also referred to as `publicURL` in the
internals of kamaki client libraries).

Here are instructions for getting the publicURL for a service::

    1. From the deployment UI get the AUTHENTICATION_URL and TOKEN
        (Example 1.2)
    2. Use them to instantiate an AstakosClient
        (Example 1.2)
    3. Use AstakosClient instance to get endpoints for the service of interest
        (Example 1.3)
    4. The 'publicURL' endpoint is the URL we are looking for
        (Example 1.3)

The AstakosClient is a client for the Synnefo/Astakos server. Synnefo/Astakos
is an identity server that implements the OpenStack identity API and it
can be used to get the URLs needed for API calls URL construction. The astakos
kamaki client library simplifies this process.

Let's review with a few examples.

First, an astakos client must be initialized (Example 1.2). An
AUTHENTICATION_URL and a TOKEN can be acquired from the Synnefo deployment UI.

.. code-block:: python
    :emphasize-lines: 1

    Example 1.2: Initialize an astakos client

    from kamaki.clients.astakos import AstakosClient
    astakos = AstakosClient(AUTHENTICATION_URL, TOKEN)
        

Next, the astakos client can be used to retrieve the `publicURL` values for the
services of interest. In this case (Example 1.3) they are *cyclades* (compute)
and *pithos* (object-store). A number of endpoints is related to each service,
but kamaki clients only need the ones labeled ``publicURL``.

.. code-block:: python
    :emphasize-lines: 1

    Example 1.3: Retrieve cyclades and pithos publicURL values

    cyclades_endpoints = astakos.get_service_endpoints('compute')
    cyclades_URL = cyclades_endpoints['publicURL']

    pithos_endpoints = astakos.get_service_endpoints('object-store')
    pithos_URL = pithos_endpoints['publicURL']

The ``get_service_endpoints`` method is called with the service name as an
argument. Here are the service names for the kamaki clients::

    storage.StorageClient, pithos.PithosClient            --> object-store
    compute.ComputeClient, cyclades.CycladesClient        --> compute
    network.NetworkClient, cyclades.CycladesNetworkClient --> network
    image.ImageClient                                     --> image
    astakos.AstakosClient                                 --> identity, account

For example

.. code-block:: python
    :emphasize-lines: 1

    Example 1.3.1 Initialize cyclades and pithos clients

    from kamaki.clients.cyclades import CycladesClient
    from kamaki.clients.pithos import PithosClient

    cyclades = CycladesClient(cyclades_URL, TOKEN)
    pithos = PithosClient(pithos_URL, TOKEN)

    #  Also, setup the account UUID and container for pithos client
    pithos.account = astakos.user_info['id']
    pithos.container = 'pithos'

Use client methods
------------------

At this point we assume that we can initialize a client, so the initialization
step will be omitted in most of the examples that follow.

The next step is to take a look at the member methods of each particular client.
A detailed catalog of the member methods for all client classes can be found at
:ref:`the-client-api-ref`

In the following example, the *cyclades* and *pithos* clients of example 1.1
are used to extract some information through the remote service APIs. The
information is then printed to the standard output.


.. code-block:: python
    :emphasize-lines: 1,2

    Example 1.4: Print server name and OS for server with server_id
                Print objects in default container

    srv = cyclades.get_server_info(server_id)
    print("Server Name: %s (with OS %s" % (srv['name'], srv['os']))

    obj_list = pithos.list_objects()
    print("Objects in container '%s':" % pithos.container)
    for obj in obj_list:
        print('  %s of %s bytes' % (obj['name'], obj['bytes']))

.. code-block:: console
    :emphasize-lines: 1

    * A run of examples 1.1 + 1.4 *


    $ python test_script.py
    Server Name: A Debian Server (with OS Debian Base)
    Objects in container 'pithos':
      lala.txt of 34 bytes
      test.txt of 1232 bytes
      testDir/ of 0 bytes
    $ 

Error handling
--------------

The *kamaki.clients* error class is ClientError. A ClientError is raised for
any kind of *kamaki.clients* errors (errors reported by servers, type errors in
method arguments, etc.).

A ClientError contains::

    message     The error message.
    status      An optional error code, e.g., after a server error.
    details     Optional list of messages with error details.

The following example concatenates examples 1.1 to 1.4 plus error handling

.. code-block:: python

    Example 1.5: Error handling

    from kamaki.clients import ClientError

    from kamaki.clients.astakos import AstakosClient
    from kamaki.clients.cyclades import CycladesClient
    from kamaki.clients.pithos import PithosClient

    try:
        astakos = AstakosClient(AUTHENTICATION_URL, TOKEN)
    except ClientError:
        print('Failed to authenticate user token')
        return 1

    try:
        cyclades_endpoints = astakos.get_service_endpoints('compute')
        cyclades_publicURL = cyclades_endpoints['publicURL']
    except ClientError:
        print('Failed to get endpoints for cyclades')

    try:
        cyclades = CycladesClient(cyclades_publicURL, token)
    except ClientError:
        print('Failed to initialize Cyclades client')

    try:
        pithos_endpoints = astakos.get_service_endpoints('object-store')
        pithos_publicURL = pithos_endpoints['publicURL']
    except ClientError:
        print('Failed to get endpoints for pithos')

    try:
        pithos = PithosClient(pithos_publicURL, token, account, container)
    except ClientError:
        print('Failed to initialize Pithos+ client')

    try:
        srv = cyclades.get_server_info(server_id)
        print("Server Name: %s (with OS %s" % (srv['name'], srv['os']))

        obj_list = pithos.list_objects()
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

    astakos = AstakosClient(AUTHENTICATION_URL, TOKEN)

    CYCLADES_URL = astakos.get_service_endpoints('compute')['publicURL']
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

    astakos = AstakosClient(AUTHENTICATION_URL, TOKEN)

    CYCLADES_URL = astakos.get_service_endpoints('compute')['publicURL']
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
    USER_UUID = astakos.user_info['id']

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

.. note::

    In `plankton.register`, the `location` argument can be either `a triplet`,
    as shown above, or `a qualified URL` of the form
    ``pithos://USER_UUID/IMAGE_CONTAINER/IMAGE_PATH``.

Two servers and a private network
'''''''''''''''''''''''''''''''''

.. code-block:: python

    #! /user/bin/python

    from kamaki.clients.astakos import AstakosClient
    from kamaki.clients.cyclades import CycladesClient, CycladesNetworkClient

    AUTHENTICATION_URL = 'https://accounts.example.com/identity/v2.0'
    TOKEN = 'replace this with your token'

    astakos = AstakosClient(AUTHENTICATION_URL, TOKEN)

    NETWORK_URL = astakos.get_service_endpoints('network')['publicURL']
    network = CycladesNetworkClient(NETWORK_URL, TOKEN)

    net = network.create_network(type='MAC_FILTERED', name='My private network')

    CYCLADES_URL = astakos.get_service_endpoints('compute')['publicURL']
    cyclades = CycladesClient(CYCLADES_URL, TOKEN)

    FLAVOR_ID = 'put your flavor id here'
    IMAGE_ID = 'put your image id here'

    srv1 = cyclades.create_server(
        'server 1', FLAVOR_ID, IMAGE_ID,
        networks=[{'uuid': net['id']}])
    srv2 = cyclades.create_server(
        'server 2', FLAVOR_ID, IMAGE_ID,
        networks=[{'uuid': net['id']}])

    srv_state1 = cyclades.wait_server(srv1['id'])
    assert srv_state1 in ('ACTIVE', ), 'Server 1 built failure'

    srv_state2 = cyclades.wait_server(srv2['id'])
    assert srv_state2 in ('ACTIVE', ), 'Server 2 built failure'
