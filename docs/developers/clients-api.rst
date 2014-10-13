Creating applications with kamaki API
=====================================

Kamaki features a clients API for building third-party client applications that
communicate with Synnefo and (in most cases) OpenStack cloud services. The
package is called *kamaki.clients* and serves as a library.

A showcase of an application built on *kamaki.clients* is *kamaki.cli*, the
command line interface of kamaki.

Since Synnefo services are build as OpenStack extensions, an inheritance
approach has been chosen for implementing clients for both APIs. In specific,
the *compute*, *storage* and *image* modules are client implementations for the
OpenStack compute, OpenStack object-store and Image APIs respectively. The rest
of the modules implement the Synnefo extensions (i.e., *cyclades* and
*cyclades_rest_api* extents *compute*, *pithos* and *pithos_rest_api* extent
*storage*).

Secure connections
------------------

Before setting up any clients, developers are advised to check whether a CA
certificates chain file is set, or set one themselves.

.. code-block:: python

    from kamaki import defaults
    from kamaki.clients.utils import https

    if not defaults.CACERTS_DEFAULT_PATH:
        https.patch_with_certs(CA_CERTS_PATH)

Check the :ref:`clients-ssl` section for more details on the subject.

Setup a client instance
-----------------------

There is a client for every API. An external applications should instantiate
the kamaki clients that fit their needs.

For example, to manage virtual servers and stored objects / files, an
application would probably need the CycladesComputeClient and PithosClient
respectively.

.. code-block:: python
    :emphasize-lines: 1

    Example 1.1: Instantiate Cyclades and Pithos clients


    from kamaki.clients.cyclades import CycladesComputeClient
    from kamaki.clients.pithos import PithosClient

    cyclades = CycladesComputeClient(computeURL, token)
    pithos = PithosClient(object-storeURL, token, account, container)

.. note:: *cyclades* and *pithos* clients inherit ComputeClient from *compute*
    and StorageClient from *storage*, respectively. Separate ComputeClient or
    StorageClient objects should be used only when implementing applications
    for strict OpenStack Compute or Storage services.

Using endpoints to get the authentication url
---------------------------------------------

Each client is initialized with a URL called ``the endpoint URL``. To get one,
an AstakosClient should be initialized first. The AstakosClient is an Astakos
client class. Astakos implements the OpenStack Identity API and the Synnefo
Account API. The astakos library features a simple call (``get_endpoint_url``)
which returns the initialization URL for a given service type (e.g., 'compute',
'object-store', 'network', 'image')

Kamaki features a library of clients. Each client abides to a service type,
stored in ``service_type`` attribute in the client class.

The values of ``service_type`` for each client are shown bellow::

    storage.StorageClient, pithos.PithosClient            --> object-store
    compute.ComputeClient, cyclades.CycladesComputeClient        --> compute
    network.NetworkClient, cyclades.CycladesNetworkClient --> network
    image.ImageClient                                     --> image
    astakos.AstakosClient                                 --> identity

Let's review with a few examples.

First, an astakos client must be initialized (Example 1.2). An
AUTHENTICATION_URL and a TOKEN can be acquired from the service web UI.

.. code-block:: python
    :emphasize-lines: 1

    Example 1.2: Initialize an astakos client

    from kamaki.clients.astakos import AstakosClient
    astakos = AstakosClient(AUTHENTICATION_URL, TOKEN)
        

Next, the astakos client can be used to retrieve the URL for each service. In
this case (Example 1.3) we need a *compute* and an *object-store* URL. They
will be used to initialize a *cyclades* and a *pithos* client respectively.

.. code-block:: python
    :emphasize-lines: 1

    Example 1.3: Retrieve cyclades and pithos URLs

    cyclades_URL = astakos.get_endpoint_url(CycladesComputeClient.service_type)
    pithos_URL = astakos.get_endpoint_url(PithosClent.service_type)

It's time to initialize both clients.

.. code-block:: python
    :emphasize-lines: 1

    Example 1.3.1 Initialize cyclades and pithos clients

    from kamaki.clients.cyclades import CycladesComputeClient
    from kamaki.clients.pithos import PithosClient

    cyclades = CycladesComputeClient(cyclades_URL, TOKEN)
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
    print("Server Name: %s (OS: %s)" % (srv['name'], srv['metadata']['os']))

    obj_list = pithos.list_objects()
    print("Objects in container '%s':" % pithos.container)
    for obj in obj_list:
        print('  %s of %s bytes' % (obj['name'], obj['bytes']))

.. code-block:: console
    :emphasize-lines: 1

    * A run of examples 1.1 + 1.4 *


    $ python test_script.py
    Server Name: A Debian Server (OS: debian)
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
    from kamaki.clients.cyclades import CycladesComputeClient
    from kamaki.clients.pithos import PithosClient

    try:
        astakos = AstakosClient(AUTHENTICATION_URL, TOKEN)
    except ClientError:
        print('Failed to authenticate user token')
        raise

    try:
        CYCLADES_URL = astakos.get_endpoint_url(CycladesComputeClient.service_type)
    except ClientError:
        print('Failed to get endpoints for cyclades')

    try:
        cyclades = CycladesComputeClient(CYCLADES_URL, TOKEN)
    except ClientError:
        print('Failed to initialize Cyclades client')

    try:
        PITHOS_URL = astakos.get_endpoint_url(PithosClient.service_type)
    except ClientError:
        print('Failed to get endpoints for pithos')

    try:
        account, container = astakos.user_info['id'], 'pithos'
        pithos = PithosClient(PITHOS_URL, TOKEN, account, container)
    except ClientError:
        print('Failed to initialize Pithos+ client')

    try:
        server_id = SERVER_ID
        srv = cyclades.get_server_info(server_id)
        print("Server Name: %s (OS: %s)" % (srv['name'], srv['metadata']['os']))

        obj_list = pithos.list_objects()
        print('Objects in container %s:' % pithos.container)
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
    from kamaki.clients.cyclades import CycladesComputeClient

    AUTHENTICATION_URL = 'https://accounts.example.com/identity/v2.0'
    TOKEN = 'replace this with your token'

    astakos = AstakosClient(AUTHENTICATION_URL, TOKEN)

    CYCLADES_URL = astakos.get_endpoint_url(CycladesComputeClient.service_type)
    cyclades = CycladesComputeClient(CYCLADES_URL, TOKEN)

    #  (name, flavor-id, image-id)
    servers = [
        ('My Debian Server', 1, 'my-debian-base-image-id'),
        ('My Windows Server', 3, 'my-windows-8-image-id'),
        ('My Ubuntu Server', 3, 'my-ubuntu-12-image-id'),
    ]

    created = []
    for name, flavor_id, image_id in servers:
        new_vm = cyclades.create_server(name, flavor_id, image_id, networks=[])
        created.append(new_vm)

    for vm in created:
        print 'Wait while vm "%s" (%s) is being build' % (vm['name'], vm['id'])
        cyclades.wait_server(vm['id'])

.. note:: The `networks=[]` argument explicitly instructs `cyclades` to create
    a virtual server without any network connections. If not used, `cyclades`
    will apply the default policy (e.g., assign a public IP to the new virtual
    server).

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

    PITHOS_URL = astakos.get_endpoint_url(PithosClient.service_type)
    pithos = PithosClient(
        PITHOS_URL, TOKEN, account=USER_UUID, container=IMAGE_CONTAINER)

    IMAGE_URL = astakos.get_endpoint_url(ImageClient.service_type)
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

.. note:: In `plankton.register`, the `location` argument can be either
    `a triplet`, as shown above, or `a qualified URL` of the form
    ``pithos://USER_UUID/IMAGE_CONTAINER/IMAGE_PATH``.

Two servers and a private network
'''''''''''''''''''''''''''''''''

.. code-block:: python

    #! /usr/bin/python

    from kamaki.clients.astakos import AstakosClient
    from kamaki.clients.cyclades import (
        CycladesComputeClient, CycladesNetworkClient)

    AUTHENTICATION_URL = 'https://accounts.example.com/identity/v2.0'
    TOKEN = 'replace this with your token'

    astakos = AstakosClient(AUTHENTICATION_URL, TOKEN)

    NETWORK_URL = astakos.get_endpoint_url(CycladesNetworkClient.service_type)
    network = CycladesNetworkClient(NETWORK_URL, TOKEN)

    net = network.create_network(type='MAC_FILTERED', name='My private network')

    CYCLADES_URL = astakos.get_endpoint_url(CycladesComputeClient.service_type)
    cyclades = CycladesComputeClient(CYCLADES_URL, TOKEN)

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

Snapshot server and backup
''''''''''''''''''''''''''

.. code-block:: python

    #! /usr/bin/python

    from kamaki.clients.astakos import AstakosClient
    from kamaki.clients.cyclades import (
        CycladesClient, CycladesBlockStorageClient)
    from kamaki.clients.image import ImageClient

    AUTHENTICATION_URL = 'https://accounts.example.com/identity/v2.0'
    TOKEN = 'replace this with your token'

    astakos = AstakosClient(AUTHENTICATION_URL, TOKEN)

    CYCLADES_URL = astakos.get_endpoint_url(CycladesClient.service_type)
    compute = CycladesClient(CYCLADES_URL, TOKEN)

    SERVER_ID = 'your server ID here'

    srv = compute.get_server_details(SERVER_ID)
    volume_id = srv['volumes'][0]

    BS_URL = astakos.get_endpoint_url(CycladesBlockStorageClient.service_type)
    block_storage = CycladesBlockStorageClient(BS_URL, TOKEN)

    snp = block_storage.create_snapshot(volume_id, 'Srv %s BackUp' % srv['id'])

    IMAGE_URL = astakos.get_endpoint_url(ImageClient.service_type)
    plankton = ImageClient(IMAGE_URL, TOKEN)

    #  Get location in the form pithos://UUID/CONTAINER/PATH
    snp_location = plankton.get_meta(snp['id'])['location']

    #  Optional: download to local storage
    from kamaki.clients.pithos import PithosClient

    PITHOS_URL = astakos.get_endpoint_url(PithosClient.service_type)
    pref_len = len('pithos://')
    ACCOUNT, sep, rel_path = snp_location[pref_len:].partition('/')
    CONTAINER, sep, PATH = rel_path.partition('/')
    pithos = PithosClient(PITHOS_URL, TOKEN, ACCOUNT, CONTAINER)

    LOCAL_DESTINATION_PATH = 'local path for backup image file'

    pithos.download_object(PATH, LOCAL_DESTINATION_PATH)

Restore server from local snapshot image
''''''''''''''''''''''''''''''''''''''''

.. code-block:: python

    #! /usr/bin/python

    from kamaki.clients.astakos import AstakosClient
    from kamaki.clients.cyclades import CycladesClient
    from kamaki.clients.image import ImageClient
    from kamaki.clients.pithos import PithosClient

    AUTHENTICATION_URL = 'https://accounts.example.com/identity/v2.0'
    TOKEN = 'replace this with your token'

    astakos = AstakosClient(AUTHENTICATION_URL, TOKEN)

    ACCOUNT, CONTAINER = astakos.user_info['id'], 'snapshots'
    PITHOS_URL = astakos.get_endpoint_url(PithosClient.service_type)
    pithos = PithosClient(PITHOS_URL, TOKEN, ACCOUNT, CONTAINER)

    LOCAL_BACKUP_IMAGE = 'local backup image file here'
    PATH = 'server_backup.diskdump'

    with open(LOCAL_BACKUP_IMAGE) as f:
        obj = pithos.upload_object(PATH, f)

    IMAGE_URL = astakos.get_endpoint_url(ImageClient.service_type)
    plankton = ImageClient(IMAGE_URL, TOKEN)

    LOCATION = 'pithos://%s/%s/%s' % (ACCOUNT)
    img = plankton.register('Backup Snapshot', LOCATION)

    CYCLADES_URL = astakos.get_endpoint_url(CycladesClient.service_type)
    compute = CycladesClient(CYCLADES_URL, TOKEN)

    FLAVOR_ID = 'make sure to pick a flavor with enough resources'
    restored_server = compute.create('Restored server', FLAVOR_ID, img['id'])
