List of commands
================

The commands described bellow are grouped by service. The examples showcase a
sample set of group commands. The kamaki interactive shell (check
`Usage section <usage.html#interactive-shell>`_ for details) is chosen as the
execution environment.


user (Identity Manager)
-----------------------

.. code-block:: text

    authenticate:  Authenticate a user

Showcase: get user information
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In the following, the token has been set in a previous step (see
`setup section <setup.html>`_ or the
`quick setup guide <usage.html#quick-setup>`_)

.. code-block:: console
    :emphasize-lines: 1,4

    * Enter user context *
    [kamaki]: user

    * Authenticate user *
    [user]: authenticate
    ...
    user:
        name:  My Real Name
        uuid:  ab1cde23-45fg-6h7i-8j9k-10l1m11no2pq

.. note:: actual call returns a full list of service endpoints accessible to
    the user with a specific token

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
    cpu :  4
    disk:  10
    id  :  43
    name:  C4R2048D10
    ram :  2048

image (Plankton commands + Compute Image subcommands)
-----------------------------------------------------

.. code-block:: text

    list      :  List images accessible by user
    info      :  Get image metadata
    meta      :  Manage image metadata
        set     :   Add / update metadata and properties for an image
        delete  :   Remove/empty image metadata and/or custom properties
    register  :  (Re)Register an image
    unregister:  Unregister an image (does not delete the image file)
    shared    :  List shared images
    compute   :  Compute Image API commands
        list      :  List images
        delete    :  Delete image
        info      :  Get image details
        properties:  Manage properties related to OS installation in an image
            delete:  Delete a property from an image
            get   :  Get an image property
            list  :  List all image properties
            set   :  Add / update a set of properties for an image
    members   :  Manage members (users who can modify an image)
        add   :  Add a member to an image
        delete:  Remove a member from an image
        list  :  List members of an image
        set   :  Set the members of an image

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
     disk_format     :  diskdump
     id              :  926ab1c5-2d85-49d4-aebe-0fce712789b9
     size            :  11917066240
     status          :  available
    78262ee7-949e-4d70-af3a-85360c3de57a Windows Server 2012
     container_format:  bare
     disk_format     :  diskdump
     id              :  78262ee7-949e-4d70-af3a-85360c3de57a
     size            :  11697913856
     status          :  available
    5ed5a29b-292c-4fe0-b32c-2e2b65628635 ubuntu
     container_format:  bare
     disk_format     :  diskdump
     id              :  5ed5a29b-292c-4fe0-b32c-2e2b65628635
     size            :  2578100224
     status          :  available
    1f8454f0-8e3e-4b6c-ab8e-5236b728dffe Debian_Wheezy_Base
     container_format:  bare
     disk_format     :  diskdump
     id              :  1f8454f0-8e3e-4b6c-ab8e-5236b728dffe
     size            :  795107328
     status          :  available

    * Get properties of image with id 1f8454f0-8e3e-4b6c-ab8e-5236b728dffe *
    [image]: compute properties 1f8454f0-8e3e-4b6c-ab8e-5236b728dffe
    description   :  Debian 6.0.6 (Squeeze) Base System
    gui           :  No GUI
    kernel        :  2.6.32
    os            :  debian
    osfamily      :  linux
    root_partition:  1
    sortorder     :  1
    users         :  root

server (Compute/Cyclades)
-------------------------

.. code-block:: text

    addr    :  List a server's nic address
    console :  Get a VNC console
    create  :  Create a server
    delete  :  Delete a server
    firewall:  Manage server's firewall profile
        set :  Set the server's firewall profile
        get :  Get the server's firewall profile
    ip      :  Manage floating IPs for the servers
        attach:  Attach a floating ip to a server with server_id
        info  :  A floating IPs' details
        detach:  Detach floating ip from server
        list  :  List all floating ips
        create:  Create a new floating IP
        delete:  Delete a floating ip
        pools :  List all floating pools of floating ips
    info    :  Get server details
    list    :  List servers
    metadata:  Manage Server Metadata
        list  :  List server metadata
        set   :  Add / update server metadata
        delete:  Delete a piece of server metadata
    reboot  :  Reboot a server
    rename  :  Update a server's name
    shutdown:  Shutdown a server
    start   :  Start a server
    stats   :  Get server statistics
    resize  :  Set a different flavor for an existing server
    wait    :  Wait for server to finish

Showcase: Create a server
^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console
    :emphasize-lines: 1,4,21,35,44,62

    * Enter server context *
    [kamaki]: server

    * See server-create help *
    [server]: create -h
    usage: create <name> <flavor id> <image id>
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
    [server]: create 'My Small Debian Server' 1 b2dffe52-64a4-48c3-8a4c-8214cc3165cf
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

.. Note:: In kamaki shell, / is used to access top-level command groups while working in command group contexts

network (Compute/Cyclades)
--------------------------

.. code-block:: text

    connect   :  Connect a server to a network
    create    :  Create a network
    delete    :  Delete a network
    disconnect:  Disconnect a nic of a server to a network
    info      :  Get network details
    list      :  List networks
    rename    :  Update network name

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
    usage: connect <server id> <network id> [-s] [-h] [-i] [--config CONFIG]

    Connect a server to a network

    Syntax: connect  <server id> <network id>
      --config    :  Path to configuration file
      -d,--debug  :  Include debug output
      -h,--help   :  Show help message
      -i,--include:  Include protocol headers in the output
      -s,--silent :  Do not output anything
      -v,--verbose:  More info at response

    * Connect VM with id 11687 to network with id 1409
    [network]: connect 11687 1409

    * Get details on network with id 1409
    [network]: info 1409
      attachments: 
                 nic-11687-1
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
    [network]: /server addr 11687
    id:  nic-11687-1
        ipv4       :  192.168.1.1
        ipv6       :  None
        mac_address:  aa:0f:c2:0b:0e:85
        network_id :  1409
        firewallProfile:  DISABLED
    id:  nic-11687-0
        ipv4           :  83.212.106.111
        ipv6           :  2001:648:2ffc:1116:a80c:f2ff:fe12:a9e
        mac_address    :  aa:0c:f2:12:0a:9e
        network_id     :  1369

.. Note:: In kamaki shell, / is used to access top-level command groups while working in command group contexts

file (Storage/Pithos+)
----------------------

.. code-block:: text

    append        :  Append local file to remote
    cat           :  Print a file to console
    copy          :  Copy an object
    containerlimit:  Container size limit commands
        set       :  Set container data limit
        get       :  Get container data limit
    create        :  Create a container
    delete        :  Delete a container [or an object]
    download      :  Download a file or directory
    group         :  Manage access groups and group members
        delete:  Delete a user group
        list  :  List groups and group members
        set   :  Set a user group
    hashmap       :  Get the hashmap of an object
    info          :  Get information for account [, container [or object]]
    list          :  List containers, object trees or objects in a directory
    manifest      :  Create a remote file with uploaded parts by manifestation
    metadata      :  Metadata are attached on objects (key:value pairs)
        delete:  Delete metadata with given key
        get   :  Get metadatum
        set   :  Set a piece of metadata
    mkdir         :  Create a directory
    move          :  Copy an object
    overwrite     :  Overwrite part (from start to end) of a remote file
    permissions   :  Manage user and group accessibility for objects
        delete:  Delete all permissions set on object
        get   :  Get read and write permissions of an object
        set   :  Set permissions for an object
    publish       :  Publish an object
    purge         :  Purge a container
    quota         :  Get  quota for account
    sharers       :  List the accounts that share objects with default account
    touch         :  Create an empty object (file)
    truncate      :  Truncate remote file up to a size
    unpublish     :  Unpublish an object
    upload        :  Upload a file or directory
    versioning    :  Manage the versioning scheme of current pithos user account
        get:  Get  versioning for account or container
        set:  Set versioning mode (auto, none) for account or container
    versions      :  Get the version list of an object

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
    [file]: create mycont1
    [file]: create mycont2


    * List accessible containers *    
    [file]: list
    1. mycont1 (0B, 0 objects)
    2. mycont2 (0B, 0 objects)
    3. pithos (0B, 0 objects)
    4. trash (0B, 0 objects)


    * Upload local file to 1st container *
    [file]: upload rndm_local.file mycont1


    * Check if file has been uploaded *
    [file]: list mycont1
    1.    20M rndm_local.file

    * Create directory mydir on second container *
    [file]: mkdir mycont2:mydir


    * Move file from 1st to 2nd container (and in the directory) *
    [file]: move mycont1:rndm_local.file mycont2:mydir/rndm_local.file

    * Check contents of both containers *
    [file]: list mycont1
    [file]: list mycont2
    1.      D mydir/
    2.    20M mydir/rndm_local.file


    * Copy file from 2nd to 1st container, with a new name *
    [file]: copy mycont2:mydir/rndm_local.file mycont1:rndm_remote.file


    * Check pasted file *
    [file]: list mycont1
    1.    20M rndm_remote.file


    * Download pasted file to local file system *
    [file]: download mycont1:rndm_remote.file rndm_remote.file


    * Check if file is downloaded and if it is the same to original *
    [file]: !ls -lh *.file
    -rw-rw-r-- 1 ******** ******** 20M Nov 26 15:36 rndm_local.file
    -rw-rw-r-- 1 ******** ******** 20M Nov 26 15:42 rndm_remote.file
    [file]: !diff rndm_local.file rndm_remote.file

.. Note:: In kamaki shell, ! is used to execute OS shell commands (e.g. bash)

.. warning:: The container:object/path syntax does not function if the
    container and / or the object path contain one or more : characters. To use
    containers and objects with : use the --container and --dst-container
    arguments, e.g. to copy test.py object from grnet:dev container to
    grnet:deploy ::

        $ kamaki file copy --container=grnet:dev test.py --dst-container=grnet:deploy
