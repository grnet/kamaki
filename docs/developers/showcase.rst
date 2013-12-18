
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
    properties = dict(osfamily='linux', root_partition='1')
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
    personality = []
    if SSH_KEYS:
        with open(abspath(SSH_KEYS)) as f:
            personality.append(dict(
                contents=b64encode(f.read()),
                path='/root/.ssh/authorized_keys',
                owner='root', group='root', mode=0600)
            personality.append(dict(
                contents=b64encode('StrictHostKeyChecking no'),
                path='/root/.ssh/config',
                owner='root', group='root', mode=0600))

    create_params = [dict(
        name='%s%s' % (CLUSTER_PREFIX, i),
        flavor_id=FLAVOR_ID,
        image_id=IMAGE_ID,
        personality=personality) for i in range(1, CLUSTER_SIZE + 1)]
    ...

Save server passwords in a file
'''''''''''''''''''''''''''''''

A last touch: define a local file to store the created server information,
including the superuser password.

.. code-block:: python
        
    #  4.4 Store passwords in file 
    SERVER_INFO = 'servers.txt'
    with open(abspath(SERVER_INFO), 'w+') as f:
        from json import dump
        dump(servers, f, intend=2)

    #  4.5 Wait for 2 servers to built
    ...

Errors and logs
'''''''''''''''

Developers may use the kamaki tools for
`error handling <clients-api.html#error-handling>`_ and
`logging <logging.html>`_, or implement their own methods.

To demonstrate, we will modify the container creation code to warn users if the
container already exists. We need a stream logger for the warning and a
knowledge of the expected return values for the *create_container* method.

First, let's get the logger.

.. code-block:: python

    from kamaki.cli.logger import add_stream_logger, get_logger

    add_stream_logger(__name__)
    log = get_logger(__name__)

The *create_container* method makes an HTTP request to the pithos server. It
considers the request succesfull if the status code of the response is 201
(created) or 202 (accepted). These status codes mean that the container has
been created or that it was already there anyway, respectively.

We will force *create_container* to raise an error in case of a 202 response.
This can be done by instructing *create_container* to accept only 201 as a
successful status.

.. code-block:: python

    try:
        pithos.create_container(CONTAINER, success=(201, ))
    except ClientError as ce:
        if ce.status in (202, ):
            log.warning('Container %s already exists' % CONTAINER')
        else:
            log.debug('Failed to create container %s' % CONTAINER)
            raise
    log.info('Container %s is ready' % CONTAINER)

create a cluster from scratch
-----------------------------

We are ready to create a module that uses kamaki to create a cluster from
scratch. We revised the code by grouping functionality in methods and using
logging more. We also added some command line interaction candy.

.. code-block:: python

    #!/usr/bin/env python

    from sys import argv
    from os.path import abspath
    from base64 import b64encode
    from kamaki.clients import ClientError
    from kamaki.cli.logger import get_logger, add_file_logger
    from logging import DEBUG

    #  Define loggers
    log = get_logger(__name__)
    add_file_logger('kamaki.clients', DEBUG, '%s.log' % __name__)
    add_file_logger(__name__, DEBUG, '%s.log' % __name__)

    #  Create progress bar generator
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
        log.warning('Suggestion: install python-progress')
        def create_pb(msg):
            return None


    #  kamaki.config
    #  Identity,Account / Astakos

    def init_astakos():
        from kamaki.clients.astakos import AstakosClient
        from kamaki.cli.config import Config, CONFIG_PATH

        print(' Get the credentials')
        cnf = Config()

        #  Get default cloud name
        try:
            cloud_name = cnf.get('global', 'default_cloud')
        except KeyError:
            log.debug('No default cloud set in file %' % CONFIG_PATH)
            raise

        try:
            AUTH_URL = cnf.get_cloud(cloud_name, 'url')
        except KeyError:
            log.debug('No authentication URL in cloud %s' % cloud_name)
            raise
        try:
            AUTH_TOKEN = cnf.get_cloud(cloud_name, 'token')
        except KeyError:
            log.debug('No token in cloud %s' % cloud_name)
            raise

        print(' Test the credentials')
        try:
            auth = AstakosClient(AUTH_URL, AUTH_TOKEN)
            auth.authenticate()
        except ClientError:
            log.debug('Athentication failed with url %s and token %s' % (
                AUTH_URL, AUTH_TOKEN))
            raise

        return auth, AUTH_TOKEN


    def endpoints_and_user_id(auth):
        print(' Get the endpoints')
        try:
            endpoints = dict(
                astakos=auth.get_service_endpoints('identity')['publicURL'],
                cyclades=auth.get_service_endpoints('compute')['publicURL'],
                pithos=auth.get_service_endpoints('object-store')['publicURL'],
                plankton=auth.get_service_endpoints('image')['publicURL']
                )
            user_id = auth.user_info()['id']
        except ClientError:
            print('Failed to get endpoints & user_id from identity server')
            raise
        return endpoints, user_id


    #  Object-store / Pithos+

    def init_pithos(endpoint, token, user_id):
        from kamaki.clients.pithos import PithosClient

        print(' Initialize Pithos+ client and set account to user uuid')
        try:
            return PithosClient(endpoint, token, user_id)
        except ClientError:
            log.debug('Failed to initialize a Pithos+ client')
            raise


    def upload_image(pithos, container, image_path):

        print(' Create the container "images" and use it')
        try:
            pithos.create_container(container, success=(201, ))
        except ClientError as ce:
            if ce.status in (202, ):
                log.warning('Container %s already exists' % container)
            else:
                log.debug('Failed to create container %s' % container)
                raise
        pithos.container = container

        print(' Upload to "images"')
        with open(abspath(image_path)) as f:
            try:
                pithos.upload_object(
                    image_path, f,
                    hash_cb=create_pb('  Calculating hashes...'),
                    upload_cb=create_pb('  Uploading...'))
            except ClientError:
                log.debug('Failed to upload file %s to container %s' % (
                    image_path, container))
                raise


    #  Image / Plankton

    def init_plankton(endpoint, token):
        from kamaki.clients.image import ImageClient

        print(' Initialize ImageClient')
        try:
            return ImageClient(endpoint, token)
        except ClientError:
            log.debug('Failed to initialize the Image client')
            raise


    def register_image(plankton, name, user_id, container, path, properties):

        image_location = (user_id, container, path)
        print(' Register the image')
        try:
             return plankton.register(name, image_location, properties)
        except ClientError:
            log.debug('Failed to register image %s' % name)
            raise


    #  Compute / Cyclades

    def init_cyclades(endpoint, token):
        from kamaki.clients.cyclades import CycladesClient

        print(' Initialize a cyclades client')
        try:
            return CycladesClient(endpoint, token)
        except ClientError:
            log.debug('Failed to initialize cyclades client')
            raise


    class Cluster(object):

        def __init__(self, cyclades, prefix, flavor_id, image_id, size):
            self.client = cyclades
            self.prefix, self.size = prefix, int(size)
            self.flavor_id, self.image_id = flavor_id, image_id

        def list(self):
            return [s for s in self.client.list_servers(detail=True) if (
                s['name'].startswith(self.prefix))]

        def clean_up(self):
            to_delete = self.list()
            print('  There are %s servers to clean up' % len(to_delete))
            for server in to_delete:
                self.client.delete_server(server['id'])
            for server in to_delete:
                self.client.wait_server(
                    server['id'], server['status'],
                    wait_cb=create_pb(' Deleting %s...' % server['name']))

        def _personality(self, ssh_keys_path='', pub_keys_path=''):
            personality = []
            if ssh_keys_path:
                with open(abspath(ssh_keys_path)) as f:
                    personality.append(dict(
                        contents=b64encode(f.read()),
                        path='/root/.ssh/id_rsa',
                        owner='root', group='root', mode=0600))
            if pub_keys_path:
                with open(abspath(pub_keys_path)) as f:
                    personality.append(dict(
                        contents=b64encode(f.read()),
                        path='/root/.ssh/authorized_keys',
                        owner='root', group='root', mode=0600))
            if ssh_keys_path or pub_keys_path:
                    personality.append(dict(
                        contents=b64encode('StrictHostKeyChecking no'),
                        path='/root/.ssh/config',
                        owner='root', group='root', mode=0600))
            return personality

        def create(self, ssh_k_path='', pub_k_path='', server_log_path=''):
            print('\n Create %s servers prefixed as %s' % (
                self.size, self.prefix))
            servers = []
            for i in range(1, self.size + 1):
                try:
                    server_name = '%s%s' % (self.prefix, i)
                    servers.append(self.client.create_server(
                        server_name, self.flavor_id, self.image_id,
                        personality=self._personality(ssh_k_path, pub_k_path)))
                except ClientError:
                    log.debug('Failed while creating server %s' % server_name)
                    raise

            if server_log_path:
                print(' Store passwords in file %s' % server_log_path)
                with open(abspath(server_log_path), 'w+') as f:
                    from json import dump
                    dump(servers, f, indent=2)

            print(' Wait for %s servers to built' % self.size)
            for server in servers:
                new_status = self.client.wait_server(
                    server['id'],
                    wait_cb=create_pb(' Creating %s...' % server['name']))
                print(' Status for server %s is %s' % (
                    server['name'], new_status or 'not changed yet'))
            return servers


    def main(opts):

        print('1.  Credentials  and  Endpoints')
        auth, token = init_astakos()
        endpoints, user_id = endpoints_and_user_id(auth)

        print('2.  Upload  the  image  file')
        pithos = init_pithos(endpoints['pithos'], token, user_id)

        upload_image(pithos, opts.container, opts.imagefile)

        print('3.  Register  the  image')
        plankton = init_plankton(endpoints['plankton'], token)

        image = register_image(
            plankton, 'my image', user_id, opts.container, opts.imagefile,
            properties=dict(
                osfamily=opts.osfamily, root_partition=opts.rootpartition))

        print('4.  Create  virtual  cluster')
        cluster = Cluster(
            cyclades = init_cyclades(endpoints['cyclades'], token),
            prefix=opts.prefix,
            flavor_id=opts.flavorid,
            image_id=image['id'],
            size=opts.clustersize)
        if opts.delete_stale:
            cluster.clean_up()
        servers = cluster.create(
            opts.sshkeypath, opts.pubkeypath, opts.serverlogpath)

        #  Group servers
        cluster_servers = cluster.list()

        active = [s for s in cluster_servers if s['status'] == 'ACTIVE']
        print('%s cluster servers are ACTIVE' % len(active))

        attached = [s for s in cluster_servers if s['attachments']]
        print('%s cluster servers are attached to networks' % len(attached))

        build = [s for s in cluster_servers if s['status'] == 'BUILD']
        print('%s cluster servers are being built' % len(build))

        error = [s for s in cluster_servers if s['status'] in ('ERROR')]
        print('%s cluster servers failed (ERROR satus)' % len(error))


    if __name__ == '__main__':

        #  Add some interaction candy
        from optparse import OptionParser

        kw = {}
        kw['usage'] = '%prog [options]'
        kw['description'] = '%prog deploys a compute cluster on Synnefo w. kamaki'

        parser = OptionParser(**kw)
        parser.disable_interspersed_args()
        parser.add_option('--prefix',
                          action='store', type='string', dest='prefix',
                          help='The prefix to use for naming cluster nodes',
                          default='cluster')
        parser.add_option('--clustersize',
                          action='store', type='string', dest='clustersize',
                          help='Number of virtual cluster nodes to create ',
                          default=2)
        parser.add_option('--flavor-id',
                          action='store', type='int', dest='flavorid',
                          metavar='FLAVOR ID',
                          help='Choose flavor id for the virtual hardware '
                               'of cluster nodes',
                          default=42)
        parser.add_option('--image-file',
                          action='store', type='string', dest='imagefile',
                          metavar='IMAGE FILE PATH',
                          help='The image file to upload and register ',
                          default='my_image.diskdump')
        parser.add_option('--delete-stale',
                          action='store_true', dest='delete_stale',
                          help='Delete stale servers from previous runs, whose '
                               'name starts with the specified prefix, see '
                               '--prefix',
                          default=False)
        parser.add_option('--container',
                          action='store', type='string', dest='container',
                          metavar='PITHOS+ CONTAINER',
                          help='The Pithos+ container to store image file',
                          default='images')
        parser.add_option('--ssh-key-path',
                          action='store', type='string', dest='sshkeypath',
                          metavar='PATH OF SSH KEYS',
                          help='The ssh keys to inject to server (e.g., id_rsa) ',
                          default='')
        parser.add_option('--pub-key-path',
                          action='store', type='string', dest='pubkeypath',
                          metavar='PATH OF PUBLIC KEYS',
                          help='The public keys to inject to server',
                          default='')
        parser.add_option('--server-log-path',
                          action='store', type='string', dest='serverlogpath',
                          metavar='FILE TO LOG THE VIRTUAL SERVERS',
                          help='Where to store information on created servers '
                               'including superuser passwords',
                          default='')
        parser.add_option('--image-osfamily',
                          action='store', type='string', dest='osfamily',
                          metavar='OS FAMILY',
                          help='linux, windows, etc.',
                          default='linux')
        parser.add_option('--image-root-partition',
                          action='store', type='string', dest='rootpartition',
                          metavar='IMAGE ROOT PARTITION',
                          help='The partition where the root home is ',
                          default='1')

        opts, args = parser.parse_args(argv[1:])

        main(opts)

