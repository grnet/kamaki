Clients reference
=================

Kamaki library API consists of clients corresponding to the Synnefo API, which
is equivalent to the OpenStack API with some extensions. In some cases, kamaki
implements the corresponding OpenStack libraries as separate clients and the
Synnefo extensions as class extensions of the former.

The kamaki library API consists of the following clients:

In ``kamaki.clients.astakos``::

    AstakosClient           An Identity and Account client for Synnefo API
    OriginalAstakosClient   The client of the Synnefo astakosclient package
    LoggedAstakosClient     The original client with kamaki-style logging
    CachedAstakosClient     Some calls are cached to speed things up

.. note:: Use ``AstakosClient`` if you are not sure

TO BE COMPLETED

Astakos / Identity
------------------

Synnefo API: https://www.synnefo.org/docs/synnefo/latest/identity-api-guide.html

The core functionality of this module is to authenticate a user and provide user data
(e.g., email, unique user id)

Authenticate user
^^^^^^^^^^^^^^^^^
**Example:** Authenticate user, get name and uuid

.. literalinclude:: examples/astakos-authenticate.py
    :language: python
    :lines: 34-
    :linenos:

.. note:: the ``authenticate`` method returns a dict, which is defined by the
    Synnefo API (not by kamaki)

Astakos / Resources and Quotas
------------------------------

Synnefo API: https://www.synnefo.org/docs/synnefo/latest/api-guide.html#resource-and-quota-service-api-astakos

This API provides information on available resources, resource usage and quota
limits.

Resource quotas
^^^^^^^^^^^^^^^

**Example**: Resource usage and limits for number of VMs and IPs

.. literalinclude:: examples/astakos-quotas.py
    :language: python
    :lines: 34-
    :linenos:

.. note:: Quotas are defined by projects (see next section). Every user is
    member to a personal project (the "system" project) which is identified by
    the uuid of the user, but they may draw resources from other projects as
    well. In this script we only got the quota information related to the system
    project and we did that with this line of code
    ``my_resources = all_resources[uuid]``

Astakos / Projects
------------------

Synnefo API: https://www.synnefo.org/docs/synnefo/latest/api-guide.html#project-service-api

The relation between projects, users and resources::

    cloud resources: VMs, CPUs, RAM, Volumes, IPs, VPNs, Storage space
    a cloud user --- is member to --- projects
    a cloud resource --- must be registered to --- a project
    A user creates a resource: registers a resource to a project he is member of

What information is found in a project:

    * members: cloud users who can use the project resources
    * project limit: usage limits per resource for the whole project
    * member limit: usage limits per resource per cloud user
    * usage: current usage per resource per cloud user

.. note:: By default, every user has a personal (system) project. By default
    when a user creates a resource, it is registered to this project, except if
    they explicitly request to register a resource to another project.

Query my projects
^^^^^^^^^^^^^^^^^
**Example:** Get information for all projects I am member to

.. literalinclude:: examples/astakos-project-info.py
    :language: python
    :lines: 34-
    :linenos:

The results should look like this::

    system:a1234567-a890-1234-56ae-78f90bb1c2db (a1234567-a890-1234-56ae-78f90bb1c2db)
        System project for user user@example.com

    CS333 lab assignments (a9f87654-3af2-1e09-8765-43a2df1098765)
        Virtual clusters for CS333 assignments
        https://university.example.com/courses/cs333


Quotas per project
^^^^^^^^^^^^^^^^^^
**Example:** Get usage and total limits per resource per project

.. literalinclude:: examples/astakos-project-quotas.py
    :language: python
    :lines: 34-
    :linenos:

The results should look like this::

    a1234567-a890-1234-56ae-78f90bb1c2db
      cyclades.cpu: 1/2
      cyclades.disk: 40/40
      cyclades.floating_ip: 1/1
      cyclades.network.private: 0/2
      cyclades.ram: 2147483648/2147483648
      cyclades.vm: 1/2
      pithos.diskspace: 20522192022/20522192022
    a9f87654-3af2-1e09-8765-43a2df1098765
      cyclades.cpu: 4/8
      cyclades.disk: 80/120
      cyclades.floating_ip: 1/4
      cyclades.network.private: 1/5
      cyclades.ram: 4294967296/53687091200
      cyclades.vm: 3/4
      pithos.diskspace: 20522192022/53687091200

Allocate resource to a project
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
**Example:** Create an IP assigned to a specific project

.. literalinclude:: examples/astakos-resource-allocation.py
    :language: python
    :lines: 34-
    :linenos:

.. note:: All "create_something" methods take an optional "project_id" argument
    which instructs Synnefo to register this resource to a specific project

Reassign resource to another project
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
**Example:** Reassign a storage container to different project

In the following scenario we assume that ``course_container`` is a storage
container on Pithos, which is assigned to the system (personal) project and
suffers from low quota limits. Fortunately, we have an extra project with enough
storage available. We will reassign the container to benefit from this option.

We will check the quota limits of the project of this container and, if they are
used up, we will reassign it to a different project.


.. literalinclude:: examples/astakos-project-reassign.py
    :language: python
    :lines: 34-
    :linenos:

.. note:: All quotable resources can be reassigned to different projects,
    including composite resources (aka: depended on other cloud resources) like
    VMs.

Cyclades / Compute
------------------
Synnefo API: https://www.synnefo.org/docs/synnefo/latest/compute-api-guide.html

A server or VM (Virtual Machine) is a complex resource: you need other resources
to built it, namely CPU cores, RAM memory, Volume space and, optionally, VPNs
and IPs.

List server quotas
^^^^^^^^^^^^^^^^^^
**Example:** Check server-related resources and report to user

.. literalinclude:: examples/compute-quotas.py
    :language: python
    :lines: 34-
    :linenos:

Create server
^^^^^^^^^^^^^
**Example:** Create a server with an IP and a server without networking (assume
the IP is reserved for use by current user)

.. literalinclude:: examples/compute-create.py
    :language: python
    :lines: 34-
    :linenos:

.. note:: The "networks" parameter sets the connectivity attributes of the new
    server. If it is None (default), networking is configured according to the
    default policy of the cloud (e.g., automatically assign the first available
    public IP). To set up a server without networking: ``networks=[]``.

Wait server to built
^^^^^^^^^^^^^^^^^^^^
**Example:** Create a new server (default settings) and wait until it is built.
Then, print the server id and its IP (assume that the default networking policy
of the cloud is to automatically set an IP to every new server).

.. literalinclude:: examples/compute-wait.py
    :language: python
    :lines: 34-
    :linenos:

.. note:: The ``wait_server_while`` and ``wait_server_until`` methods work for
    all valid server states (`ACTIVE`, `BUILD`, `STOPPED`, `ERROR`, etc.) and
    can be used to block a program under some conditions. These blockers are
    based on the ``kamaki.clients.wait``, which blocks for as long as a
    user-provided method returns true.

Query images and flavors
^^^^^^^^^^^^^^^^^^^^^^^^
**Example:** Find the appropriate image and flavor for a server

.. literalinclude:: examples/compute-image-flavor.py
    :language: python
    :lines: 34-
    :linenos:

Reboot server
^^^^^^^^^^^^^
**Example:** Reboot a server.

.. literalinclude:: examples/compute-reboot.py
    :language: python
    :lines: 34-
    :linenos:

.. note:: Similarly you can ``start_server``, ``shutdown_server`` as well as
    ``resize_server`` and ``delete_server``.

Reassign and resize a server
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
**Example:** We need to make our server more powerful, but it's assigned to a
    project which is out of resources. We will shutdown the server, reassign it
    to another project and resize it to another flavor.

.. literalinclude:: examples/compute-reassign-resize.py
    :language: python
    :lines: 34-
    :linenos:

.. note:: Servers must be stopped in order to resize or reassign it.

Cyclades / Network
------------------
Synnefo API: https://www.synnefo.org/docs/synnefo/latest/network-api-guide.html

The Synnefo approach to the Network API diverges from the OpenStack semantics.
Check the Synnefo documentation for more details.

Create private network
^^^^^^^^^^^^^^^^^^^^^^
**Example:** Create a new private network between two servers.

.. literalinclude:: examples/network-vpn.py
    :language: python
    :lines: 34-
    :linenos:

.. note:: In Synnefo, ports are the connections between a network and a server.

Reserve IP
^^^^^^^^^^
**Example:** Check if there are free IPs, reserve one if not and use it with a
server.

.. literalinclude:: examples/network-ip.py
    :language: python
    :lines: 34-
    :linenos:

.. note:: IPs are connected to networks, which are connected to servers.

Create cluster
^^^^^^^^^^^^^^
**Example:** Create a cluster of three servers, where only one has a public IP.

.. literalinclude:: examples/network-cluster.py
    :language: python
    :lines: 34-
    :linenos:

Cyclades / BlockStorage
-----------------------
Synnefo API: https://www.synnefo.org/docs/synnefo/latest/blockstorage-api-guide.html

Unplug and plug volume
^^^^^^^^^^^^^^^^^^^^^^
**Example:** Create a volume for server_1, then unplug it and plug it on
server_2, as you would do with a USB stick.

.. literalinclude:: examples/volume-plug-unplug.py
    :language: python
    :lines: 34-
    :linenos:

Image
-----

Synnefo API: https://www.synnefo.org/docs/synnefo/latest/image-api-guide.html

In Synnefo, an image is loaded as a file to the storage service (Pithos+), and
then is registered to the image service (Plankton). The image location is unique
and can be used as an image identifier.

Image location formats::

    pithos://<user_uuid>/<container>/<object path>
    e.g., pithos://user-uuid/images/debian_base.diskdump

    or, if the user uuid os implied
    /<container>/<object path>
    e.g., /images/debian_base.diskdump

Register
^^^^^^^^

**Example:** Register the image file ``my-image.diskdump``, currently stored
locally. It will be uploaded to ``images``.

.. literalinclude:: examples/image-register.py
    :language: python
    :lines: 34-
    :linenos:

It is a common practice to keep the image registration details in a json meta
file (e.g., to register images in the future). This metafile is typically
uploaded along with the image.

.. code-block:: console

    kamaki file cat /images/my-image.diskdump.meta
    {
      "name": "Debian Base With Extras",
      "checksum": "3cb03556ec971f...e8dd6190443b560cb7",
      "updated-at": "2013-06-19 08:01:00",
      "created-at": "2013-06-19 08:00:22",
      "properties": {
        "OS": "linux",
        "USER": "root"
      },
      "location": "pithos://user-uuid/images/my-image.diskdump",
      "is-public": "False",
      "owner": "user-uuid",
      "disk-format": "diskdump",
      "size": "903471104",
      "deleted-at": "",
      "container-format": "bare"
    }

List
^^^^
**Example:** List the names and Pithos locations of the images registered by me

.. literalinclude:: examples/image-list.py
    :language: python
    :lines: 34-
    :linenos:

Unresgister
^^^^^^^^^^^
**Example:** Unregister and delete an image.

.. literalinclude:: examples/image-unregister.py
    :language: python
    :lines: 34-
    :linenos:

.. note:: Unregistering an image does not delete the image dump from pithos. In
    order to do that, you need to have the appropriate permissions (aka, the
    image file must by stored on your Pithos account), so that you can delete it
    as a file.


Pithos
------

Synnefo API: https://www.synnefo.org/docs/synnefo/latest/object-api-guide.html
Pithos+ is the storage service of Synnefo.

Each user has their own storage space, organized in containers. Each
container contains objects. In most cases we can think of objects as files, but
in reality they are not the same thing. Typically, it is the responsibility of
the application to simulate the functionality of folders and files, if they need
it.

Here is an example, where the containers are ``pithos``, ``images``, ``music``
and ``trash``::

    user-uuid
        pithos
            myfile.txt
            myfolder/
            myfolder/anotherfile.txt
            my-linux-distro.diskdump
        images
            debian-stable.disckdump
            my-special-image.diskdump
        music
            The Beatles - White Album/
            The Beatles - White Album/Back in the U.S.S.R.
            BoC - Music has the right to children/
            BoC - Music has the right to children/Wildlife Analysis
            BoC - Music has the right to children/An eagle in your mind
        trash
            my deleted folder/
            my deleted folder/some old file.txt
            my deleted folder/removed by accident.png

Quotas are applied at project level. Each container is registered to a project
(by default, the personal/system project of the owner). Objects ("files")
inherit the project policy of the container they are in.

Initialize pithos client
^^^^^^^^^^^^^^^^^^^^^^^^
**Example:** Initialize a pithos client to handle the objects in the container
``pithos``

.. literalinclude:: examples/pithos-init.py
    :language: python
    :lines: 34-
    :linenos:

.. note:: To access the objects of another user, set the ``account`` parameter
    to their uuid and Pithos will have access to the objects the other user
    allows you to see or edit.

List and information
^^^^^^^^^^^^^^^^^^^^
**Example** Recursively list the contents of all my containers.

.. literalinclude:: examples/pithos-list.py
    :language: python
    :lines: 34-
    :linenos:

The results should look like this::

    Listing contents of pithos (project: a1234567-a890-1234-56ae-78f90bb1c2db)
        myfile.txt  text/plain     202 bytes
        myfolder/   application/directory   0 bytes
        myfolder/anotherfile.txt    text/plain   333 bytes
        my-linux-distro.diskdump    applcation/octet-stream    539427293 bytes
    Listing contents of images (project: a9f87654-3af2-1e09-8765-43a2df1098765)
        debian-stable.disckdump     application/octet-stream    309427093 bytes
        my-special-image.diskdump   applcation/octet-stream    339427293 bytes
    Listing contents of music (project: a9f87654-3af2-1e09-8765-43a2df1098765)
        The Beatles - White Album/  application/directory   0 bytes
        The Beatles - White Album/Back in the U.S.S.R.mp3  media/mpeg   3442135 bytes
        BoC - Music has the right to children/     application/directory   0 bytes
        BoC - Music has the right to children/Wildlife Analysis.mp3   media/mpeg   4442135 bytes
        BoC - Music has the right to children/An eagle in your mind.mp3    media/mpeg   23442135 bytes
    Listing contents of trash (project: a1234567-a890-1234-56ae-78f90bb1c2db)
        my deleted folder/     application/directory   0 bytes
        my deleted folder/some old file.txt      text/plain   10 bytes
        my deleted folder/removed by accident.png   image/png   20 bytes

.. note:: In the above example, half of the projects (pithos, trash) are
    registered to the user's system (personal) project, while the rest (
    images, music) at another project, probably one offering more storage
    resources.

Upload and download
^^^^^^^^^^^^^^^^^^^

**Example:** Download ``my-linux-distro.diskdump`` from container "pithos" to a
    local file as ``local.diskdump`` and upload it to container "images" as
    ``recovered.diskdump``

.. literalinclude:: examples/pithos-download-upload.py
    :language: python
    :lines: 34-
    :linenos:

.. note:: The file is now stored at three locations: the container "pithos", the
    container "images" and, with a different name, at the local hard disk.

.. note:: The ``upload_object`` and ``download_object`` methods are optimized in
    many ways: they feature dynamic simultaneous connections and automatic
    resume. In this case for instance, the data of the uploaded file will not
    be uploaded, as they are already on the server.

Move / Copy / Delete
^^^^^^^^^^^^^^^^^^^^
**Example:** Move ``/pithos/my-linux-distro.diskdump`` to ``trash``, delete
    ``/images/my-pithos-distro.diskdump`` and then copy it from trash.

.. literalinclude:: examples/pithos-move-copy-delete.py
    :language: python
    :lines: 34-
    :linenos:

This is the status after the execution of the script above::

    user-uuid
        pithos
            myfile.txt
            myfolder/
            myfolder/anotherfile.txt
        images
            debian-stable.disckdump
            my-special-image.diskdump
            recovered.diskdump
        music
            The Beatles - White Album/
            The Beatles - White Album/Back in the U.S.S.R.
            BoC - Music has the right to children/
            BoC - Music has the right to children/Wildlife Analysis
            BoC - Music has the right to children/An eagle in your mind
        trash
            my deleted folder/
            my deleted folder/some old file.txt
            my deleted folder/removed by accident.png
            my-linux-distro.diskdump

Reassign container
^^^^^^^^^^^^^^^^^^

**Example:** Reassign container "images" to the same project as the one of "pithos".

.. literalinclude:: examples/pithos-reassign.py
    :language: python
    :lines: 34-
    :linenos:
