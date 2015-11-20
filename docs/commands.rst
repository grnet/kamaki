List of commands
================

Kamaki commands follow this scheme::

    [kamaki] <object> <action> [identifiers] [non-positional arguments]

In this context, objects are not services, but virtual objects like a server, a
file or an image. The action concerns objects of the specified type. Some
actions (e.g. "delete" or "info") need to operate on an existing object. The
identifiers strictly identify this object and they should have the form of an id
(e.g., `server delete <SERVER_ID>`).

The examples bellow showcase some commands. The kamaki-shell (check
`Usage section <usage.html#interactive-shell>`_ for details) is chosen as the
execution environment.


user (Identity/Astakos)
-----------------------

.. code-block:: text

    info          Get info for (current) session user
    uuid2name     Get user name(s) from uuid(s)
    authenticate  Authenticate a user and get all authentication information
    list          List (cached) session users
    add           Authenticate user by token and add to kamaki session (cache)
    name2uuid     Get user uuid(s) from name(s)
    select        Select user from the (cached) list as current session user
    delete        Delete user (token) from the (cached) list of session users

Showcase: get user information
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In the following, cloud URL and TOKEN were set in a previous step (see
`setup section <setup.html>`_ or the
`quick setup guide <usage.html#quick-setup>`_)

.. code-block:: console
    :emphasize-lines: 1,4

    * Enter user context *
    [kamaki]: user

    * Authenticate user *
    [user]: info
    ...
    name:  My Real Name
    id:  ab1cde23-45fg-6h7i-8j9k-10l1m11no2pq

    [user]: exit
    [kamaki]:

project (Astakos)
-----------------

.. code-block:: text

    info          Get details for a project
    unsuspend     Resume a suspended project (special privileges needed)
    suspend       Suspend a project (special privileges needed)
    list          List all projects
    create        Apply for a new project
    modify        Modify a project
    terminate     Terminate a project (special privileges needed)
    application   Application management commands
    reinstate     Reinstate a terminated project (special privileges needed)
    join          Join a project
    dismiss       Dismiss your denied application
    deny          Deny an application (special privileges needed)
    enroll        Enroll a user to a project
    cancel        Cancel your application
    approve       Approve an application (special privileges needed)

membership (Astakos)
--------------------

.. code-block:: text

    info    Details on a membership
    list    List all memberships
    accept  Accept a membership for a project you manage
    leave   Leave a project you have membership to
    remove  Remove a membership for a project you manage
    reject  Reject a membership for a project you manage
    cancel  Cancel your (probably pending) membership to a project

quota (Account/Astakos)
-----------------------

.. code-block:: text

    list          Get user quotas

resource (Astakos)
------------------

.. code-block:: text

    list          List user resources

flavor (Compute/Cyclades)
-------------------------

.. code-block:: text

    info:  Get flavor details
    list:  List flavors

Showcase: show details for flavor with id 43
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console
    :emphasize-lines: 1,4

    * Enter flavor context *
    [kamaki]: flavor

    * Get details about flavor with id 43 *
    [flavor]: info 43
    SNF:disk_template:  drbd
    cpu:  4
    disk:  10
    id:  43
    name:  C4R2048D10
    ram:  2048

image (Image/Plankton)
----------------------

.. code-block:: text

    info          Get image metadata
    list          List images accessible by user
    register      (Re)Register an image file to an Image service
    modify        Add / update metadata and properties for an image
    unregister    Unregister an image (does not delete the image file)

Showcase: Pick an image and list the properties
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console
    :emphasize-lines: 1,4,18

    * Enter image context *
    [kamaki]: image

    * list all available images *
    [image]: list
    926ab1c5-2d85-49d4-aebe-0fce712789b9 Windows Server 2008
     container_format:  bare
     disk_format:  diskdump
     id:  926ab1c5-2d85-49d4-aebe-0fce712789b9
     size:  11917066240
     status:  available
    78262ee7-949e-4d70-af3a-85360c3de57a Windows Server 2012
     container_format:  bare
     disk_format:  diskdump
     id:  78262ee7-949e-4d70-af3a-85360c3de57a
     size:  11697913856
     status:  available
    5ed5a29b-292c-4fe0-b32c-2e2b65628635 ubuntu
     container_format:  bare
     disk_format:  diskdump
     id:  5ed5a29b-292c-4fe0-b32c-2e2b65628635
     size:  2578100224
     status:  available
    1f8454f0-8e3e-4b6c-ab8e-5236b728dffe Debian_Wheezy_Base
     container_format:  bare
     disk_format:  diskdump
     id:  1f8454f0-8e3e-4b6c-ab8e-5236b728dffe
     size:  795107328
     status:  available

    * Get details for image with id 1f8454f0-8e3e-4b6c-ab8e-5236b728dffe *
    [image]: info 1f8454f0-8e3e-4b6c-ab8e-5236b728dffe
     name: Debian_Wheezy_Base
     container_format:  bare
     disk_format:  diskdump
     id:  1f8454f0-8e3e-4b6c-ab8e-5236b728dffe
     size:  795107328
     status:  available
     owner:  s0m3-u53r-1d (user@example.com)
        DESCRIPTION:  Debian Wheezy Base (Stable)
        GUI:  No GUI
        KERNEL:  2.6.32
        OS:  debian
        OSFAMILY:  linux
        ROOT_PARTITION:  1
        SORTORDER:  1
        USERS:  root

imagecompute (Compute/Cyclades)
-------------------------------

.. code-block:: text

    info      Get detailed information on an image
    list      List images
    modify    Modify image properties (metadata)
    delete    Delete an image (WARNING: image file is also removed)

server (Compute/Cyclades)
-------------------------

.. code-block:: text

    info      Detailed information on a Virtual Machine
    modify    Modify attributes of a virtual server
    create    Create a server (aka Virtual Machine)
    list      List virtual servers accessible by user
    reboot    Reboot a virtual server
    start     Start an existing virtual server
    shutdown  Shutdown an active virtual server
    delete    Delete a virtual server
    console   Create a VNC console and show connection information
    wait      Wait for server to finish [BUILD, STOPPED, REBOOT, ACTIVE]
    attachment  Details on a volume attachment
    attachments List of all volume attachments for a server
    attach      Attach a volume on a server
    detach      Delete an attachment/detach a volume from a server

Showcase: Create a server
^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console
    :emphasize-lines: 1,4,21,35,44,62

    [kamaki]: server

    [server]: create -h
    usage: create --name NAME --flavor-id FLAVOR_ID --image-id IMAGE_ID
            [--personality PERSONALITY] [-h] [--config CONFIG] [--cloud CLOUD]

    Create a server

    optional arguments:
      -v, --verbose         More info at response
      --personality PERSONALITY
                            add a personality file
      -d, --debug           Include debug output
      -h, --help            Show help message
      -i, --include         Include protocol headers in the output
      --config CONFIG       Path to configuration file
      -s, --silent          Do not output anything
      --cloud CLOUD         Chose a cloud to connect to

    * List all available images *
    [server]: /image compute list
    1395fdfb-51b4-419f-bb02-f7d632860611 Ubuntu Desktop LTS
    1580deb4-edb3-4496-a27f-7a246c4c0528 Ubuntu Desktop
    18a82962-43eb-4b32-8e28-8f8880af89d7 Kubuntu LTS
    6aa6eafd-dccb-422d-a904-67fe2bdde87e Debian Desktop
    6b5681e4-7502-46ae-b1e9-9fd837932095 maelstrom
    78262ee7-949e-4d70-af3a-85360c3de57a Windows Server 2012
    86bc2414-0fb3-4898-a637-240292243302 Fedora
    926ab1c5-2d85-49d4-aebe-0fce712789b9 Windows Server 2008
    b2dffe52-64a4-48c3-8a4c-8214cc3165cf Debian Base
    baf2321c-57a0-4a69-825d-49f49cea163a CentOS
    c1d27b46-d875-4f5c-b7f1-f39b5af62905 Kubuntu

    * See details of flavor with id 1 *
    [server]: /flavor info 1
    SNF:disk_template:  drbd
    cpu              :  1
    disk             :  20
    id               :  1
    name             :  C1R1024D20
    ram              :  1024

    * Create a debian server named 'My Small Debian Server'
    [server]: create --name='My Small Debian Server' --flavor-id=1 --image-id=b2dffe52-64a4-48c3-8a4c-8214cc3165cf
    adminPass:  L8gu2wbZ94
    created  :  2012-11-23T16:56:04.190813+00:00
    flavorRef:  1
    hostId   :  
    id       :  11687
    imageRef :  b2dffe52-64a4-48c3-8a4c-8214cc3165cf
    metadata : 
               os   :  debian
               users:  root
    name     :  My Small Debian Server
    progress :  0
    status   :  BUILD
    suspended:  False
    updated  :  2012-11-23T16:56:04.761962+00:00

    * wait for server to build (optional) *
    [server]: wait 11687
    Server 11687 still in BUILD mode |||||||||||||||||    | 80%
    Server 11687 is now in ACTIVE mode

.. Note:: In kamaki shell, / is used to access commands from top-level

ip (Network/Cyclades)
---------------------

.. code-block:: text

    info      Get details on a floating IP
    create    Reserve an IP on a network
    list      List reserved floating IPs
    delete    Unreserve an IP (also delete the port, if attached)
    attach    Attach an IP on a virtual server
    detach    Detach an IP from a virtual server

port (Network/Cyclades)
-----------------------

.. code-block:: text

    info      Get details about a port
    list      List all ports
    create    Create a new port (== connect server to network)
    modify    Modify the attributes of a port
    delete    Delete a port (== disconnect server from network)
    wait      Wait for port to finish [ACTIVE, DOWN, BUILD, ERROR]

Showcase: Reserve and attach IP to server
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: text

    * Enter port context *
    [kamaki]: port

    * Reserve an IP and see servers and networks*
    [port]: /ip create
    123.456.78.9
    [port]: /server list
    42   My Windows Server
    43   My Linux Server
    [port]: /network list
    101  My Network 1
    102  My Network 2

    * Attach IP to server
    [port]: port create --device-id=43 --network-id=101 --ip-address=123.456.78.9 --wait
    Creating new port 7 between server 43 and network 101
    Port 7 still in BUILD mode |||||||||||||||||    | 80%
    Port 7 is now in ACTIVE mode

.. Note:: In kamaki shell, / is used to access top-level command groups while
    working in command group contexts

network (Network/Cyclades)
--------------------------

.. code-block:: text

    info        Get details about a network
    disconnect  Disconnect a network from a device
    modify      Modify network attributes
    create      Create a new network
    list        List networks
    connect     Connect a network with a device (server or router)
    delete      Delete a network

Showcase: Connect a network to a VM
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console
    :emphasize-lines: 1,4,9,24,27,44

    * Enter network context *
    [kamaki]: network

    * List user-owned VMs *
    [network]: /server list
    11687 (My Small Debian Server)
    11688 (An Ubuntu server)

    * Try network-connect (to get help) *
    [network]: connect
    Syntax error
    usage: connect <network id> --device-id <DEVICE_ID> [-s] [-h] [-i] [--config CONFIG]

    Connect a server to a network

    Syntax: connect  <server id> <network id>
      --config    :  Path to configuration file
      -d,--debug  :  Include debug output
      -h,--help   :  Show help message
      -i,--include:  Include protocol headers in the output
      -s,--silent :  Do not output anything
      -v,--verbose:  More info at response

    * Connect VM with id 11687 to network with id 1409
    [network]: connect 1409 --device-id=11687 --wait
    Creating port between network 1409 and server 11687
    New port: 8

    * Get details on network with id 1409
    [network]: info 1409
      attachments:
                8
      cidr    :  192.168.1.0/24
      cidr6   :  None
      created :  2012-11-23T17:17:20.560098+00:00
      dhcp    :  True
      gateway :  None
      gateway6:  None
      id      :  1409
      name    :  my network
      public  :  False
      status  :  ACTIVE
      type    :  MAC_FILTERED
      updated :  2012-11-23T17:18:25.095225+00:00

    * Get connectivity details on VM with id 11687 *
    [network]: /server info 11687 --nics
    nic-11687-1
        ipv4           :  192.168.1.1
        ipv6           :  None
        mac_address    :  aa:0f:c2:0b:0e:85
        network_id     :  1409
        firewallProfile:  DISABLED
    nic-11687-0
        ipv4           :  83.212.106.111
        ipv6           :  2001:648:2ffc:1116:a80c:f2ff:fe12:a9e
        mac_address    :  aa:0c:f2:12:0a:9e
        network_id     :  1369

.. Note:: In kamaki shell, / is used to access top-level command groups while working in command group contexts

volume (Block Storage)
----------------------

.. code-block:: text

    info        Get details about a volume
    list        List volumes
    create      Create a new volume
    modify      Modify a volumes' properties
    reassign    Reassign volume to a different project
    type        Get volume type details
    types       List volume types
    delete      Delete a volume

Showcase: Create a volume
^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

    $ kamaki volume create --server-id=11687 --name='Small Volume' --size=2
    id: v0lum31d
    name: Small Volume
    size: 2
    ...
    $ kamaki volume list
    v0lum31d   Small Volume

snapshot (Block Storage)
------------------------

.. code-block:: text

    info    Get details about a snapshot
    list    List snapshots
    create  Create a new snapshot
    modify  Modify a snapshots' properties
    delete  Delete a snapshot

Showcase: Create a snapshot
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

    $ kamaki snapshot create --volume-id=v0lum31d --name='Small Snapshot'
    id: sn4p5h071d
    name: Small Snapshot
    ...
    $ kamaki snapshot list
    sn4p5h071d   Small Snapshot
    ...

container (Storage/Pithos+)
---------------------------

.. code-block:: text

    info      Get information about a container
    modify    Modify the properties of a container
    create    Create a new container
    list      List all containers, or their contents
    empty     Empty a container
    delete    Delete a container

group (Storage/Pithos+)
-----------------------

.. code-block:: text

    create    Create a group of users
    list      List all groups and group members
    delete    Delete a user group

sharer (Storage/Pithos+)
------------------------

.. code-block:: text

    info      Details on a Pithos+ sharer account (default: current account)
    list      List accounts who share file objects with current user

file (Storage/Pithos+)
----------------------

.. code-block:: text

    info      Get information/details about a file
    truncate  Truncate remote file up to size
    mkdir     Create a directory
    create    Create an empty file
    move      Move objects, even between different accounts or containers
    list      List all objects in a container or a directory object
    upload    Upload a file
    cat       Fetch remote file contents
    modify    Modify the attributes of a file or directory object
    append    Append local file to (existing) remote object
    download  Download a remove file or directory object to local file system
    copy      Copy objects, even between different accounts or containers
    overwrite Overwrite part of a remote file
    delete    Delete a file or directory object

Showcase: Upload and download a file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console
    :emphasize-lines: 1,7,11,16,21,29,33,37,41,44,51,55,60,64

    * Create a random binarry file at current OS path *
    [kamaki]: !dd bs=4M if=/dev/zero of=rndm_local.file count=5
    5+0 records in
    5+0 records out
    20971520 bytes (21 MB) copied, 0.016162 s, 1.3 GB/s

    * Enter file context *
    [kamaki]: file


    * Check local file *
    [file]: !ls -lh rndm_local.file
    -rw-rw-r-- 1 ******** ******** 20M Nov 26 15:36 rndm_local.file


    * Create two containers *
    [file]: /container create mycont1
    [file]: /container create mycont2


    * List accessible containers *
    [file]: /container list
    1. mycont1 (0B, 0 objects)
    2. mycont2 (0B, 0 objects)
    3. pithos (0B, 0 objects)
    4. trash (0B, 0 objects)


    * Upload local file to 1st container *
    [file]: upload /mycont1/rndm_local.file


    * Check if file has been uploaded *
    [file]: list /mycont1
    1.    20M rndm_local.file

    * Create directory mydir on second container *
    [file]: mkdir /mycont2/mydir

    * Move file from 1st to 2nd container (and in the directory) *
    [file]: move /mycont1/rndm_local.file /mycont2/mydir/rndm_local.file

    * Check contents of both containers *
    [file]: list /mycont1
    [file]: list /mycont2
    1.      D mydir/
    2.    20M mydir/rndm_local.file

    * Copy file from 2nd to 1st container, with a new name *
    [file]: copy /mycont2/mydir/rndm_local.file /mycont1/rndm_remote.file

    * Check pasted file *
    [file]: list /mycont1
    1.    20M rndm_remote.file

    * Download pasted file to local file system *
    [file]: download /mycont1/rndm_remote.file
    Downloading: |||||||||||||||||   | 72%

    * Check if file is downloaded and if it is the same to original *
    [file]: !ls -lh *.file
    -rw-rw-r-- 1 ******** ******** 20M Nov 26 15:36 rndm_local.file
    -rw-rw-r-- 1 ******** ******** 20M Nov 26 15:42 rndm_remote.file
    [file]: !diff rndm_local.file rndm_remote.file

.. Note:: In kamaki shell, ! is used to execute OS shell commands (e.g., bash)
