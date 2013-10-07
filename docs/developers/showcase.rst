
Showcase: create a virtual cluster from scratch
===============================================

In this section we will create a virtual cluster, from scratch.

Requirements:

* A `synnefo <http://www.synnefo.org>`_ deployment with functional *Astakos*,
    *Pithos+*, *Plankton* and *Cyclades* services.

* A kamaki setup, configured with a default cloud (see how to do this with
    kamaki as a
    `shell command <../examplesdir/configuration.html#multiple-clouds-in-a-single-configuration>`_ ,
    or a
    `python library <config.html#set-a-new-cloud-name-it-new-cloud-and-set-it-as-default>`_.

* An image stored at file *./my_image.diskdump* that can run on a predefined
    hardware flavor, identifiable by the flavor id *42* (see how to create an
    image with the
    `synnefo image creator <http://www.synnefo.org/docs/snf-image-creator/latest/index.html>`_
    ).

This is the pseudocode:

#. Get credentials and service endpoints, with kamaki config and the
    **Astakos** *identity* and *account* services
#. Upload the image file to the **Pithos+** *object-store* service
#. Register the image file to the **Plankton** *image* service
#. Create a number of virtual servers to the **Cyclades** *compute* service


Credentials and endpoints
-------------------------

We assume that the kamaki configuration file contains at least one cloud
configuration, and this configuration is also set as the default cloud for
kamaki. A cloud configuration is basically a name for the cloud, an
authentication URL and an authentication TOKEN: the credentials we are looking
for!

This is the plan:

#. Get the credentials from the kamaki configuration
#. Initialize an AstakosClient and test the credentials
#. Get the endpoints for all services

.. code-block:: python

    from sys import stderr
    from kamaki.cli.config import Config, CONFIG_PATH
    from kamaki.clients.astakos import AstakosClient, ClientError

    #  Initialize Config with default values.
    cnf = Config()

    #  1. Get the credentials
    #  Get default cloud name 
    try:
        cloud_name = cnf.get('global', 'default_cloud')
    except KeyError:
        stderr.write('No default cloud set in file %s\n' % CONFIG_PATH)
        raise

    #  Get cloud authentication URL and TOKEN
    try:
        AUTH_URL = cnf.get_cloud(cloud_name, 'url')
    except KeyError:
        stderr.write('No authentication URL in cloud %s\n' % cloud_name)
        raise
    try:
        AUTH_TOKEN = cnf.get_cloud(cloud_name, 'token')
    except KeyError:
        stderr.write('No token in cloud %s\n' % cloud_name)
        raise

    #  2. Test the credentials
    #  Test authentication credentials
    try:
        auth = AstakosClient(AUTH_URL, AUTH_TOKEN)
        auth.authenticate()
    except ClientError:
        stderr.write('Athentication failed with url %s and token %s\n' % (
            AUTH_URL, AUTH_TOKEN))
        raise

    #  3. Get the endpoints
    #  Identity, Account --> astakos
    #  Compute --> cyclades
    #  Object-store --> pithos
    #  Image --> plankton
    try:
        endpoints = dict(
            astakos=AUTH_URL,
            cyclades=auth.get_service_endpoints('compute')['publicURL'],
            pithos=auth.get_service_endpoints('object-store')['publicURL'],
            plankton=auth.get_service_endpoints('image')['publicURL']
            )
        user_id = auth.user_info()['id']
    except ClientError:
        stderr.write(
            'Failed to get user id and endpoints from the identity server\n')
        raise

Upload the image
----------------

We assume there is an image file at the current local directory, at
*./my_image.diskdump* and we need to upload it to a Pithos+ container. We also
assume the contains does not currently exist. We will name it *images*.

This is the plan:

#. Initialize a Pithos+ client
#. Create the container *images*
#. Upload the local file to the container

.. code-block:: python

    from os.path import abspath
    from kamaki.clients.pithos import PithosClient

    CONTAINER = 'images'
    IMAGE_FILE = 'my_image.diskdump'

    #  1. Initialize Pithos+ client and set account to current user
    try:
        pithos = PithosClient(endpoints['pithos'], AUTH_TOKEN)
    except ClientError:
        stderr.write('Failed to initialize a Pithos+ client\n')
        raise
    pithos.account = user_id

    #  2. Create the container "images" and let pithos client work with that
    try:
        pithos.create_container('images')
    except ClientError:
        stderr.write('Failed to create container "image"\n')
        raise
    pithos.container = CONTAINER

    #  3. Upload
    with open(abspath(IMAGE_FILE)) as f:
        try:
            pithos.upload_object(IMAGE_FILE, f)
        except ClientError:
            stderr.write('Failed to upload file %s to container %s\n' % (
                IMAGE_FILE, CONTAINER))
            raise

Register the image
------------------

Now the image is located at *pithos://<user_id>/images/my_image.diskdump*
and we want to register it to the Plankton *image* service.

.. code-block:: python

    from kamaki.clients.image import ImageClient

    IMAGE_NAME = 'My image'
    IMAGE_LOCATION = (user_id, CONTAINER, IMAGE_FILE)

    #  3.1 Initialize ImageClient
    try:
        plankton = ImageClient(endpoints['plankton'], AUTH_TOKEN)
    except ClientError:
        stderr.write('Failed to initialize the Image client client\n')
        raise

    #  3.2 Register the image
    try:
        image = plankton.image_register(IMAGE_NAME, IMAGE_LOCATION)
    except ClientError:
        stderr.write('Failed to register image %s\n' % IMAGE_NAME)
        raise

Create the virtual cluster
--------------------------

In order to build a virtual cluster, we need some information:

* an image id. We can get them from *image['id']* (the id of the image we
    have just created)
* a hardware flavor. Assume we have picked the flavor with id *42*
* a set of names for our virtual servers. We will name them *cluster1*,
    *cluster2*, etc.

Here is the plan:

#. Initialize a Cyclades/Compute client
#. Create a number of virtual servers. Their name should be prefixed as
    "cluster"

.. code-block:: python

    #  4.  Create  virtual  cluster
    from kamaki.clients.cyclades import CycladesClient

    FLAVOR_ID = 42
    IMAGE_ID = image['id']
    CLUSTER_SIZE = 2
    CLUSTER_PREFIX = 'cluster'

    #  4.1 Initialize a cyclades client
    try:
        cyclades = CycladesClient(endpoints['cyclades'], AUTH_TOKEN)
    except ClientError:
        stderr.write('Failed to initialize cyclades client\n')
        raise

    #  4.2 Create 2 servers prefixed as "cluster"
    servers = []
    for i in range(1, CLUSTER_SIZE + 1):
        server_name = '%s%s' % (CLUSTER_PREFIX, i)
        try:
            servers.append(
                cyclades.create_server(server_name, FLAVOR_ID, IMAGE_ID))
        except ClientError:
            stderr.write('Failed while creating server %s\n' % server_name)
            raise

Some improvements
-----------------

Progress Bars
'''''''''''''

Uploading an image might take a while. You can wait patiently, or you can use a
progress generator. Even better, combine a generator with the progress bar
package that comes with kamaki. The upload_object method accepts two generators
as parameters: one for calculating local file hashes and another for uploading

.. code-block:: python

    from progress.bar import Bar

    def hash_gen(n):
        bar = Bar('Calculating hashes...')
        for i in bar.iter(range(int(n))):
            yield
        yield

    def upload_gen(n):
        bar = Bar('Uploading...')
        for i in bar.iter(range(int(n))):
            yield
        yield

    ...
    pithos.upload_object(
        IMAGE_FILE, f, hash_cb=hash_gen, upload_cb=upload_gen)

We can create a method to produce progress bar generators, and use it in other
methods as well:

.. code-block:: python

    try:
        from progress.bar import Bar

        def create_pb(msg):
            def generator(n):
                bar=Bar(msg)
                for i in bar.iter(range(int(n))):
                    yield
                yield
            return generator
    except ImportError:
        stderr.write('Suggestion: install python-progress\n')
        def create_pb(msg):
            return None

    ...
    pithos.upload_object(
        IMAGE_FILE, f,
        hash_cb=create_pb('Calculating hashes...'),
        upload_cb=create_pb('Uploading...'))

Wait for servers to built
'''''''''''''''''''''''''

When a create_server method is finished successfully, a server is being built.
Usually, it takes a while for a server to built. Fortunately, there is a wait
method in the kamaki cyclades client. It can use a progress bar too!

.. code-block:: python

    #  4.2 Create 2 servers prefixed as "cluster"
    ...

    # 4.3 Wait for servers to built
    for server in servers:
        cyclades.wait_server(server['id'])

Asynchronous server creation
''''''''''''''''''''''''''''

In case of a large virtual cluster, it might be faster to spawn the servers
with asynchronous requests. Kamaki clients offer an automated mechanism for
asynchronous requests.

.. code-block:: python

    #  4.2 Create 2 servers prefixed as "cluster"
    create_params = [dict(
        name='%s%s' % (CLUSTER_PREFIX, i),
        flavor_id=FLAVOR_ID,
        image_id=IMAGE_ID) for i in range(1, CLUSTER_SIZE + 1)]
    try:
        servers = cyclades.async_run(cyclades.create_server, create_params)
    except ClientError:
        stderr.write('Failed while creating servers\n')
        raise

Clean up virtual cluster
''''''''''''''''''''''''

We need to clean up Cyclades from servers left from previous cluster creations.
This clean up will destroy all servers prefixed with "cluster". It will run
before the cluster creation:

.. code-block:: python

    #  4.2 Clean up virtual cluster
    to_delete = [server for server in cyclades.list_servers(detail=True) if (
        server['name'].startswith(CLUSTER_PREFIX))]
    for server in to_delete:
        cyclades.delete_server(server['id'])
    for server in to_delete:
        cyclades.wait_server(
            server['id'], server['status'],
            wait_cb=create_pb('Deleting %s...' % server['name']))

    #  4.3 Create 2 servers prefixed as "cluster"
    ...

Inject ssh keys
'''''''''''''''

When a server is created, the returned value contains a filed "adminPass". This
field can be used to manually log into the server.

An easier way is to
`inject the ssh keys <../examplesdir/server.html#inject-ssh-keys-to-a-debian-server>`_
of the users who are going to use the virtual servers.

Assuming that we have collected the keys in a file named *rsa.pub*, we can
inject them into each server, with the personality argument

.. code-block:: python

    SSH_KEYS = 'rsa.pub'

    ...

    #  4.3 Create 2 servers prefixed as "cluster"
    personality = None
    if SSH_KEYS:
        with open(SSH_KEYS) as f:
            from base64 import b64encode
            personality=[dict(
                contents=b64encode(f.read()),
                path='/root/.ssh/authorized_keys',
                owner='root',
                group='root',
                mode='0777'), ]
    create_params = [dict(
        name='%s%s' % (CLUSTER_PREFIX, i),
        flavor_id=FLAVOR_ID,
        image_id=IMAGE_ID,
        personality=personality) for i in range(1, CLUSTER_SIZE + 1)]
    ...

