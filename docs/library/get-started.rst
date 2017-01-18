Get started with kamaki API library
===================================

Kamaki is the de facto python API library for Synnefo. It provides full coverage
of the Synnefo API as well as convenient methods for complex activities (e.g.,
block and wait for a server-side action, optimized upload and download). The
principal functionality of kamaki is to make REST API calls to a Synnefo cloud.

Setup
-----

The library part of kamaki is called `kamaki.clients`. In the following we
assume kamaki is installed successfully.

First, check if kamaki is patched with SSL certificates or provide them yourself
by using the patch_with_certs method.

.. code-block:: python

    from kamaki import defaults
    from kamaki.clients.utils import https

    if not defaults.CACERTS_DEFAULT_PATH:
        https.patch_with_certs(CA_CERTS_PATH)

For more information on kamaki SSL support, check :ref:`clients-ssl`.

Kamaki needs two things in order to function: (a) a Synnefo cloud and (b) a user
of that cloud. Therefore, you need to provide the following credentials::

    AUTHENTICATION_URL: single point for all Synnefo APIs in a cloud
    TOKEN: unique per user, authenticates user access to all APIs of the cloud

Visit the cloud UI and log in to get ``AUTHENTICATION_URL`` and ``TOKEN``.

We will initialize `astakos`, a kamaki API client which is used in all
applications, because it provides authentication and initialization information
required by the other clients in the library.

.. code-block:: python

    # Credentials to access your cloud
    AUTHENTICATION_URL = "https://www.example.com/astakos/identity/v2.0"
    TOKEN = "User-Token"

    # Initialize an astakos Client
    from kamaki.clients.astakos import AstakosClient
    astakos = AstakosClient(AUTHENTICATION_URL, TOKEN)

Endpoints
---------

Kamaki consists of multiple classes, which we call "clients". Each client
"speaks" the dialect of a specific Synnefo/OpenStack API e.g., Account and
Identity, Compute, Network, Image, BlockStorage, Pithos, etc.

To initialize a client, you need at least two parameters: the `API endpoint`
(an API-specific URL) and the user `token`. The token is common for all clients
and we already have one. We can get the endpoint of a client with the
``get_endpoint_url`` method of `astakos` client.

In the following example we will retrieve the endpoints for Cyclades/Compute and
Pithos. Cyclades/Compute API provides compute services, while Pithos is the
storage service. We will use these endpoints to initialize the respective
API clients.

.. code-block:: python

    # Import client classes
    from kamaki.clients.cyclades import CycladesComputeClient
    from kamaki.clients.pithos import PithosClient

    # Retrieve service types
    cyclades_compute_type = CycladesComputeClient.service_type
    pithos_type = PithosClient.service_type

    # Retrieve endpoints
    cyclades_endpoint = astakos.get_endpoint_url(cyclades_compute_type)
    pithos_endpoint = astakos.get_endpoint_url(pithos_type)

    # Initialize client instances
    cyclades_compute = CycladesComputeClient(cyclades_endpoint, TOKEN)
    pithos = PithosClient(pithos_endpoint, TOKEN)

The `service_type` of a client identifies the OpenStack API dialect it speaks.
The values of `service_type` per client are shown bellow::

    StorageClient, PithosClient          --> object-store
    ComputeClient, CycladesComputeClient --> compute
    NetworkClient, CycladesNetworkClient --> network
    ImageClient                          --> image
    AstakosClient                        --> identity
