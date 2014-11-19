Examples
========
This is a collection of python scripts that demonstrate the usage of the kamaki
clients API library

Initial steps
-------------

Initialize clients
""""""""""""""""""
Initialize the identity (`auth`), storage (`store`), `compute`,
`network`, block storage (`volume`) and `image` clients, given an
authentication URL and TOKEN.

.. literalinclude:: scripts/000_init.py
    :language: python
    :linenos:
    :lines: 48-

.. warning:: Line 4 sets the CA certificates bundle to support secure
    connections. Secure connections are enabled by default and must be managed
    before setting any clients. See :ref:`clients-ssl` for more details.

Authentication URL and TOKEN from config file
"""""""""""""""""""""""""""""""""""""""""""""
Drag the URL and TOKEN information from the kamaki configuration file, using
the "Config" class from kamaki CLI.

.. literalinclude:: scripts/000_init.py
    :language: python
    :linenos:
    :lines: 34-39

.. note:: The cloud URL and TOKEN are stored under a cloud name. Kamaki can be
    configured to `use multiple clouds <../setup.html#multiple-clouds>`_. It is
    common practice to
    `set the value of the default cloud <../setup.html#quick-setup>`_ using the
    **global.default_cloud** configuration option. Here it was assumed that the
    value **global.default_cloud** is the name of the preferred cloud

Log HTTP
""""""""
Instruct kamaki to output the HTTP logs on the console.

.. literalinclude:: scripts/000_init.py
    :language: python
    :linenos:
    :lines: 42-45

Containers and files
--------------------

Information on object
"""""""""""""""""""""
List all objects in the storage_client's default container and ask user to pick
one of them for more information.

.. literalinclude:: scripts/001_file_info.py
    :language: python
    :linenos:
    :lines: 48-

Backup container
""""""""""""""""
Back up the contents of the default container to a new container.

.. literalinclude:: scripts/002_container_backup.py
    :language: python
    :linenos:
    :lines: 48-

Empty and delete containers
"""""""""""""""""""""""""""
Delete all containers if their names start with "backup".

.. literalinclude:: scripts/003_container_cleanup.py
    :language: python
    :linenos:
    :lines: 48-

.. note:: The "del_container" method will empty the container. The
    "purge_container" method will destroy an empty container. If the container
    is not empty, it cannot be destroyed.

.. note:: The "try-finally" clause is used to preserve the original container
    settings of the client (usually "pithos")

Upload and Download
"""""""""""""""""""
Upload a local file

.. literalinclude:: scripts/004_upload_files.py
    :language: python
    :linenos:
    :lines: 56-

Download a remote object as local file

.. literalinclude:: scripts/005_download_files.py
    :language: python
    :linenos:
    :lines: 56-

.. note:: The _gen callback function is used to show upload/download progress.
    It is optional. It must be a python generator, for example:

    .. literalinclude:: scripts/004_upload_files.py
        :language: python
        :linenos:
        :lines: 48-54

Asynchronous batch upload
"""""""""""""""""""""""""
Upload all files in a directory asynchronously

.. literalinclude:: scripts/006_async_upload.py
    :language: python
    :linenos:
    :lines: 48-

Reassign container
""""""""""""""""""
Each resource is assigned to a project, where the resource quotas are defined.
With this script, users are prompted to choose a project to assign the default
container.

.. literalinclude:: scripts/007_container_reassign.py
    :language: python
    :linenos:
    :lines: 48-

Download and stream in parallel
"""""""""""""""""""""""""""""""
Download an object in chunks. Stream them as they are being downloaded.

.. literalinclude:: scripts/008_stream.py
    :language: python
    :linenos:
    :lines: 48-

.. note:: The ``kamaki.clients.SilentEvent`` class extends ``threading.Thread``
    in order to simplify thread handling.

Images
------

Register image
""""""""""""""
Upload an image to container "images" and register it to Plankton.

.. literalinclude:: scripts/009_register_image.py
    :language: python
    :linenos:
    :lines: 53-

.. note:: Properties are mandatory in order to create a working image. In this
    example it is assumed a Debian Linux image. The suggested method for
    creating, uploading and registering custom images is by using the
    `snf-image-creator tool <https://www.synnefo.org/docs/snf-image-creator/latest/>`_.

Find image
""""""""""
Find images belonging to current user, by its name.

.. literalinclude:: scripts/010_find_image.py
    :language: python
    :linenos:
    :lines: 48-

Modify image
""""""""""""
Change the name and add a properties to an image. Use the image created
`above <#register-image>`_. One of the properties (description) is new, the
other (users) exists and will be updated with a new value.

.. literalinclude:: scripts/011_modify_image.py
    :language: python
    :linenos:
    :lines: 52-

Unregister image
""""""""""""""""
Unregister the image created `above <#register-image>`_.

.. literalinclude:: scripts/012_unregister_image.py
    :language: python
    :linenos:
    :lines: 52-

Virtual Machines (Servers)
--------------------------

Find flavors
""""""""""""
Find all flavors with 2048 MB of RAM, 2 CPU cores and disk space between 20 GB
and 40 GB.

.. literalinclude:: scripts/013_find_flavors.py
    :language: python
    :linenos:
    :lines: 49-

Create server
"""""""""""""
To create a server, pick a name, a flavor id and an image id. In this example,
assume the image from `a previous step <#register-image>`_.

.. literalinclude:: scripts/014_create_server.py
    :language: python
    :linenos:
    :lines: 50-54

.. note:: To access the virtual server, a password is returned by the creation
    method. This password is revealed only once, when the server is created and
    it's not stored anywhere on the service side.

A popular access method is to inject the user ssh keys, as shown bellow.

.. literalinclude:: scripts/014_create_server.py
    :language: python
    :linenos:
    :lines: 56-

Connection information
""""""""""""""""""""""
There are many ways to connect to a server: using a password or ssh keys,
through a VNC console, the IP address or the qualified domain name.

Credentials for connection through a VNC console:

.. literalinclude:: scripts/015_connect_server.py
    :language: python
    :linenos:
    :lines: 52-56

The following script collects all network information available: the F.Q.D.N.
(fully qualified domain name) and the IP addresses (v4 as well as v6).

.. literalinclude:: scripts/015_connect_server.py
    :language: python
    :linenos:
    :lines: 59-

Update server
"""""""""""""
Rename the server and then add/change some metadata.

.. literalinclude:: scripts/016_update_server.py
    :language: python
    :linenos:
    :lines: 51-

Start, Shutdown, Reboot or Delete server
""""""""""""""""""""""""""""""""""""""""
First, get the current status of the server, and write a method for handling
the wait results.

.. literalinclude:: scripts/017_server_actions.py
    :language: python
    :linenos:
    :lines: 52-56

Shutdown a server, assuming it is currently active.

.. literalinclude:: scripts/017_server_actions.py
    :language: python
    :linenos:
    :lines: 58-62

Start the stopped server.

.. literalinclude:: scripts/017_server_actions.py
    :language: python
    :linenos:
    :lines: 64-68

Reboot the active server.

.. literalinclude:: scripts/017_server_actions.py
    :language: python
    :linenos:
    :lines: 70-74

Destroy the server.

.. literalinclude:: scripts/017_server_actions.py
    :language: python
    :linenos:
    :lines: 76-

Server snapshots
----------------

Lookup volume
"""""""""""""
Each virtual server has at least one volume. This information is already stored
in the "srv" object retrieved in `a previous step <#create-server>`_.

.. literalinclude:: scripts/023_lookup_volume.py
    :language: python
    :linenos:
    :lines: 55

Retrieve this information using the Block Storage client and check if it
matches.

.. literalinclude:: scripts/023_lookup_volume.py
    :language: python
    :linenos:
    :lines: 57-

Create and delete volume
""""""""""""""""""""""""
Create an extra volume. A server can have multiple volumes attached.

.. note:: In this example, the size of the volume is retrieved from the size of
    the server flavor. This is the safest method to set a fitting size.

.. literalinclude:: scripts/024_volume.py
    :language: python
    :linenos:
    :lines: 55-57

Destroy the volume.

.. literalinclude:: scripts/024_volume.py
    :language: python
    :linenos:
    :lines: 65

.. warning:: volume creation and deletion may take some time to complete.

Lookup snapshot
"""""""""""""""
Find the snapshots of the server's first volume.

.. literalinclude:: scripts/025_lookup_snapshot.py
    :language: python
    :linenos:
    :lines: 55-

Create and delete snapshot
""""""""""""""""""""""""""
Create a snapshot of the first server volume.

.. literalinclude:: scripts/026_snapshot.py
    :language: python
    :linenos:
    :lines: 55

Delete the snapshot.

.. literalinclude:: scripts/026_snapshot.py
    :language: python
    :linenos:
    :lines: 57

Backup and restore snapshot
"""""""""""""""""""""""""""
A snapshot can be thought as a backup, stored at users "snapshots" container.

Restore server from snapshot (assume the one created in the
`previous step <#create-and-delete-snapshot>`_).

.. literalinclude:: scripts/027_backup_snapshot.py
    :language: python
    :linenos:
    :lines: 69-70

To be safer, download the snapshot to local disk.

.. literalinclude:: scripts/027_backup_snapshot.py
    :language: python
    :linenos:
    :lines: 72-75

If the snapshot has been removed from the system, the server can be restored by
uploading it from the local copy.

.. literalinclude:: scripts/027_backup_snapshot.py
    :language: python
    :linenos:
    :lines: 77-

.. note:: By uploading from a local copy, we must register the snapshot as an
    image. Use the "exclude_all_taks" to register such images.

Networks
--------

=========== ===========
Term        Description
=========== ===========
network     A public or private network
sunet       A subnet of a network
port        A connection between a device (e.g., vm) and a network
floating_ip An external IP v4, reserved by the current user for a network
=========== ===========

Public and private networks
"""""""""""""""""""""""""""
Public networks are created by the system. Private networks are created and
managed by users.

Separate public from private networks.

.. literalinclude:: scripts/018_separate_networks.py
    :language: python
    :linenos:
    :lines: 49-54

Create and destroy virtual private network
""""""""""""""""""""""""""""""""""""""""""
Create a VPN.

.. literalinclude:: scripts/019_vpn.py
    :language: python
    :linenos:
    :lines: 49-51

.. note:: The "type" of the network is a Cyclades-specific parameter. To see
    all network types:

    .. literalinclude:: scripts/019_vpn.py
        :language: python
        :linenos:
        :lines: 56

Delete the VPN.

.. literalinclude:: scripts/019_vpn.py
    :language: python
    :linenos:
    :lines: 53

Lookup IP
"""""""""
Find the ID of an IP.

.. literalinclude:: scripts/020_lookup_from_ip.py
    :language: python
    :linenos:
    :lines: 49-54

Lookup server from IP
"""""""""""""""""""""
Find the server ID from an IP ID.

.. literalinclude:: scripts/020_lookup_from_ip.py
    :language: python
    :linenos:
    :lines: 56-58

Reserve and release IP
""""""""""""""""""""""
Reserve an IP.

.. literalinclude:: scripts/021_ip_pool.py
    :language: python
    :linenos:
    :lines: 49-50

.. note:: Reserving an IP means "make it available for use". A freshly reserved
    IP is not used by any servers.

Release an IP.

.. literalinclude:: scripts/021_ip_pool.py
    :language: python
    :linenos:
    :lines: 52-

Attach and dettach IP
"""""""""""""""""""""
Attach IP to server,  by creating a connection (port) between the server and
the network related to the IP.

.. note:: The "srv" object and the "assert_status" method from
    `an earlier script <#start-shutdown-reboot-or-delete-server>`_ are used
    here too.

.. literalinclude:: scripts/022_handle_ip.py
    :language: python
    :linenos:
    :lines: 56-64

Detach IP from server.

.. literalinclude:: scripts/022_handle_ip.py
    :language: python
    :linenos:
    :lines: 66-

