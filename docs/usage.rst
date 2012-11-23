Usage
=====

Kamaki offers command line interfaces that implement specific command specifications. A detailed list of the command specifications can be found in `Commands <commands.html>`_ section. This guide covers the generic usage of both interfaces.

What's more, kamaki offers a clients API that allows the developement of external applications for synnefo. The clients API is listed in the `Clients lib <clients.html>`_ section. The recomended method of utilizing this API is explained in the present.

Setup
-----

Kamaki interfaces rely on a list of configuration options. In the initial state, kamaki is configured to communicate with the Okenos IaaS. A detailed guide for setting up kamaki can be found in the `Setup <setup.html>`_ section.

Quick guide
^^^^^^^^^^^

It is essential for users to get a configuration token (to get in Okeanos.grnet.gr log `here <https://accounts.okeanos.grnet.gr/im/>`_) and provide it to kamaki:

.. code-block:: console

    $ kamaki set token myt0k3n==


    Example 1.1.1: Set user token to myt0k3n==

To use the storage service, a user should also provide the corresponding username:

.. code-block:: console

    $ kamaki set account user@domain.com


    Example 1.1.2: Set user name to user@domain.com

Command line interfaces
-----------------------
Kamaki users can access synnefo services through either the interactive shell or the one-command behaviors. In practice, both systems relly on the same command set implementations and API clients, with identical responses and error messages. Still, there are some differenses.

Shell vs one-command
^^^^^^^^^^^^^^^^^^^^
In favor of interactive shell behavior:

* tab completion for commands
* session history with "up"/"down" keys
* shorter commants with command namespace switching

In favor of one-command behavior:

* can be used along with advanced shell features (pipelines, redirection, etc.)
* can be used in shell scripts
* prints debug and verbose messages if needed

Run as shell
""""""""""""
To use kamaki as a shell, run:

* without any parameters or arguments

.. code-block:: console

    $ kamaki


    Example 2.2.1: Running kamaki shell


* with any kind of '-' prefixed arguments, except '-h', '--help'.

.. code-block:: console

    $ kamaki --config myconfig.file

   
    Example 2.2.2: Running kamaki shell with custom configuration file


Run as one-command
""""""""""""""""""
To use kamaki as an one-command tool, run:

* with the '-h' or '--help' arguments (help for kamaki one-command)

.. code-block:: console

    $kamaki -h


    Example 2.3.1: Kamaki help

* with one or more command parameters:

.. code-block:: console

    $ kamaki server list


    Example 2.3.2: List VMs managed by user

Commands
^^^^^^^^

Client commands are grouped by service (see example 3.1.1 on how to list available groups). Commands behavior is as uniform as possible, but there are still differences between groups due to the special nature of each service and server-side implementation.

Typically, commands consist of a group name (e.g. store for storage commands) one or more terms (e.g. list for listing) and the command specific parameters (e.g. the name of the container), if any.

.. code-block:: console

    $ kamaki store list mycontainer


    Example 3.1.1: List stored files in container mycontainer

Example 2.3.2 showcases a command without parameters (the group is "server", the command is "list").

The "server" command group is also refered in the following example.

.. code-block:: console

    $ kamaki server info 42


    Example 3.1.2: Show information about a user-managed VM with id 42

Client commands can feature an arbitarry number of terms:

.. code-block:: text

    kamaki <group> <cmd term 1> <cmd term 2> ... <cmd term N> [arguments]

Although there are no multi-termed client commands until version 0.6.1 , the feature is supported and might be used in feature extentions.

The following pattern applies to all client commands up to version 0.6.1:

.. code-block:: text

    kamaki <group> <command> [arguments]

The commands supported in version 0.6.1 are described bellow, grouped by service. The examples showcase a sample set of group commands and were run in the kamaki interactive shell:

astakos (Identity Manager)
""""""""""""""""""""""""""

.. code-block:: text

    authenticate:  Authenticate a user

Showcase: get user information, provided the token was set

.. code-block:: console
    :emphasize-lines: 1, 2, 12

    [kamaki]:astakos
    [astakos]:authenticate
    auth_token        :  s0m3t0k3nth@t1sr3m0v3d==
    auth_token_created:  2012-11-13T14:12:40.917034
    auth_token_expires:  2012-12-13T14:12:40.917035
    groups            : 
                      default
    has_credits       :  False
    has_signed_terms  :  True
    uniq              :  myaccount@grnet.gr
    username          :  4215th3b357num9323v32
    [astakos]:

flavor (Compute/Cyclades)
"""""""""""""""""""""""""

.. code-block:: text

    info:  Get flavor details
    list:  List flavors

Showcase: show details for flavor with id 43

.. code-block:: console
    :emphasize-lines: 1, 2, 9

    [kamaki]: flavor
    [flavor]: info 43
    SNF:disk_template:  drbd
    cpu              :  4
    disk             :  10
    id               :  43
    name             :  C4R2048D10
    ram              :  2048
    [flavor]:

image (Compute/Cyclades + Glance)
""""""""""""""""""""""""""""""""""

.. code-block:: text

    addmember  :  Add a member to an image
    addproperty:  Add an image property
    delete     :  Delete image
    delmember  :  Remove a member from an image
    delproperty:  Delete an image property
    info       :  Get image details
    list       :  List images
    members    :  Get image members
    meta       :  Get image metadata
    properties :  Get image properties
    public     :  List public images
    register   :  (Re)Register an image
    setmembers :  Set the members of an image
    setproperty:  Update an image property
    shared     :  List shared images

Showcase: show a list of public images, list the properties of Debian Base

.. code-block:: console
    :emphasize-lines: 1, 2, 14, 23

    [kamaki]:image
    [image]:list
    1395fdfb-51b4-419f-bb02-f7d632860611 (Ubuntu Desktop LTS (Long Term Support))
    1580deb4-edb3-4496-a27f-7a246c4c0528 (Ubuntu Desktop)
    18a82962-43eb-4b32-8e28-8f8880af89d7 (Kubuntu LTS (Long Term Support))
    6aa6eafd-dccb-422d-a904-67fe2bdde87e (Debian Desktop)
    6b5681e4-7502-46ae-b1e9-9fd837932095 (maelstrom)
    78262ee7-949e-4d70-af3a-85360c3de57a (Windows Server 2012)
    86bc2414-0fb3-4898-a637-240292243302 (Fedora)
    926ab1c5-2d85-49d4-aebe-0fce712789b9 (Windows Server 2008)
    b2dffe52-64a4-48c3-8a4c-8214cc3165cf (Debian Base)
    baf2321c-57a0-4a69-825d-49f49cea163a (CentOS)
    c1d27b46-d875-4f5c-b7f1-f39b5af62905 (Kubuntu)
    [image]:properties b2dffe52-64a4-48c3-8a4c-8214cc3165cf
    description   :  Debian 6.0.6 (Squeeze) Base System
    gui           :  No GUI
    kernel        :  2.6.32
    os            :  debian
    osfamily      :  linux
    root_partition:  1
    sortorder     :  1
    users         :  root
    [image]:

server (Compute/Cyclades)
"""""""""""""""""""""""""

.. code-block:: text

    addmeta :  Add server metadata
    addr    :  List a server's nic address
    console :  Get a VNC console
    create  :  Create a server
    delete  :  Delete a server
    delmeta :  Delete server metadata
    firewall:  Set the server's firewall profile
    info    :  Get server details
    list    :  List servers
    meta    :  Get a server's metadata
    reboot  :  Reboot a server
    rename  :  Update a server's name
    setmeta :  Update server's metadata
    shutdown:  Shutdown a server
    start   :  Start a server
    stats   :  Get server statistics
    wait    :  Wait for server to finish

Showcase: Create a server: Show create help, find a flavor and an image make a server. Wait for server to be build, get server details. Note that the progress bar feature is optional (see )

.. code-block:: console
    :emphasize-lines: 1, 2, 17, 34, 41, 57, 60, 67

    [kamaki]:server
    [server]:create -h
    usage: create <name> <flavor id> <image id>
            [--personality PERSONALITY] [-h] [--config CONFIG]

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
    [server]:/image list
    1395fdfb-51b4-419f-bb02-f7d632860611 (Ubuntu Desktop LTS (Long Term Support))

    1580deb4-edb3-4496-a27f-7a246c4c0528 (Ubuntu Desktop)

    18a82962-43eb-4b32-8e28-8f8880af89d7 (Kubuntu LTS (Long Term Support))

    6aa6eafd-dccb-422d-a904-67fe2bdde87e (Debian Desktop)

    6b5681e4-7502-46ae-b1e9-9fd837932095 (maelstrom)

    78262ee7-949e-4d70-af3a-85360c3de57a (Windows Server 2012)
    86bc2414-0fb3-4898-a637-240292243302 (Fedora)
    926ab1c5-2d85-49d4-aebe-0fce712789b9 (Windows Server 2008)
    b2dffe52-64a4-48c3-8a4c-8214cc3165cf (Debian Base)
    baf2321c-57a0-4a69-825d-49f49cea163a (CentOS)
    c1d27b46-d875-4f5c-b7f1-f39b5af62905 (Kubuntu)
    [server]:/flavor info 1
    SNF:disk_template:  drbd
    cpu              :  1
    disk             :  20
    id               :  1
    name             :  C1R1024D20
    ram              :  1024
    [server]:create 'My Small Debian Server' 1 b2dffe52-64a4-48c3-8a4c-8214cc3165cf
    adminPass:  L8gu2wbZ94
    created  :  2012-11-23T16:56:04.190813+00:00
    flavorRef:  1
    hostId   :  
    id       :  11687
    imageRef :  b2dffe52-64a4-48c3-8a4c-8214cc3165cf
    metadata : 
             values: 
                   os   :  debian
                   users:  root
    name     :  My Small Debian Server
    progress :  0
    status   :  BUILD
    suspended:  False
    updated  :  2012-11-23T16:56:04.761962+00:00
    [server]:wait 11687
    Server 11687 still in BUILD mode |||||||||||||||||    | 80% - 3s
    Server 11687 is now in ACTIVE mode
    [server]:

network (Compute/Cyclades)
""""""""""""""""""""""""""

.. code-block:: text

    connect   :  Connect a server to a network
    create    :  Create a network
    delete    :  Delete a network
    disconnect:  Disconnect a nic of a server to a network
    info      :  Get network details
    list      :  List networks
    rename    :  Update network name

Showcase: Connect a network to a VM: create a network, list available VMs, connect to 'My Small Debian Server', check network info and server connectivity.

.. code-block:: console
    :emphasize-lines: 1, 2, 5, 14, 15, 30, 42

    [kamaki]:network
    [network]:/server list
    11687 (My Small Debian Server)
    11688 (An Ubuntu server)
    [network]:connect 
    Connect a server to a network
    Syntax: connect  <server id> <network id>
      --config    :  Path to configuration file
      -d,--debug  :  Include debug output
      -h,--help   :  Show help message
      -i,--include:  Include protocol headers in the output
      -s,--silent :  Do not output anything
      -v,--verbose:  More info at response
    [network]: connect 11687 1409
    [network]:info 1409
      attachments: 
                 nic-11687-1
      cidr       :  192.168.1.0/24
      cidr6      :  None
      created    :  2012-11-23T17:17:20.560098+00:00
      dhcp       :  True
      gateway    :  None
      gateway6   :  None
      id         :  1409
      name       :  my network
      public     :  False
      status     :  ACTIVE
      type       :  PRIVATE_MAC_FILTERED
      updated    :  2012-11-23T17:18:25.095225+00:00
    [network]:/server addr 11687
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
    [network]:



store (Storage/Pithos+)
"""""""""""""""""""""""

.. code-block:: text

    append        :  Append local file to remote
    cat           :  Print a file to console
    copy          :  Copy an object
    create        :  Create a container or a directory object
    delete        :  Delete a container [or an object]
    delgroup      :  Delete a user group on an account
    delmeta       :  Delete an existing metadatum of account [, container [or object]]
    delpermissions:  Delete all sharing permissions
    download      :  Download a file
    group         :  Get user groups details for account
    hashmap       :  Get the hashmap of an object
    info          :  Get information for account [, container [or object]]
    list          :  List containers, object trees or objects in a directory
    manifest      :  Create a remote file with uploaded parts by manifestation
    meta          :  Get custom meta-content for account [, container [or object]]
    mkdir         :  Create a directory
    move          :  Copy an object
    overwrite     :  Overwrite part (from start to end) of a remote file
    permissions   :  Get object read/write permissions
    publish       :  Publish an object
    purge         :  Purge a container
    quota         :  Get  quota for account [or container]
    setgroup      :  Create/update a new user group on account
    setmeta       :  Set a new metadatum for account [, container [or object]]
    setpermissions:  Set sharing permissions
    setquota      :  Set new quota (in KB) for account [or container]
    setversioning :  Set new versioning (auto, none) for account [or container]
    sharers       :  List the accounts that share objects with default account
    truncate      :  Truncate remote file up to a size
    unpublish     :  Unpublish an object
    upload        :  Upload a file
    versioning    :  Get  versioning for account [or container ]
    versions      :  Get the version list of an object

One-command interface
^^^^^^^^^^^^^^^^^^^^^

Kamaki usage as a one-command tool is detailed in this section

Using help
""""""""""

Kamaki help is used to see available commands, with description, syntax and their corresponding optional arguments.

To see the command groups, users should use -h or --help like in example 1.3.1. In the same way, help information for command groups and commands is printed. In the following examples, the help messages of kamaki, of a command group (server) and of a command in that group (list) are shown.

.. code-block:: console

    $ kamaki -h
    usage: kamaki <cmd_group> [<cmd_subbroup> ...] <cmd> [-v] [-s] [-V] [-d] [-i]
                                                     [--config CONFIG]
                                                     [-o OPTIONS] [-h]

    optional arguments:
      -v, --verbose         More info at response
      -s, --silent          Do not output anything
      -V, --version         Print current version
      -d, --debug           Include debug output
      -i, --include         Include protocol headers in the output
      --config CONFIG       Path to configuration file
      -o OPTIONS, --options OPTIONS
                            Override a config value
      -h, --help            Show help message

    Options:
     - - - -
    astakos:  Astakos API commands
    config :  Configuration commands
    flavor :  Compute/Cyclades API flavor commands
    history:  Command history
    image  :  Compute/Cyclades or Glance API image commands
    network:  Compute/Cyclades API network commands
    server :  Compute/Cyclades API server commands
    store  :  Pithos+ storage commands


    Example 4.1.1: kamaki help shows available parameters and command groups

.. code-block:: console

    $ kamaki cyclades -h
    usage: kamaki server <...> [-v] [-s] [-V] [-d] [-i] [--config CONFIG]
                               [-o OPTIONS] [-h]

    optional arguments:
      -v, --verbose         More info at response
      -s, --silent          Do not output anything
      -V, --version         Print current version
      -d, --debug           Include debug output
      -i, --include         Include protocol headers in the output
      --config CONFIG       Path to configuration file
      -o OPTIONS, --options OPTIONS
                            Override a config value
      -h, --help            Show help message

    Options:
     - - - -
    addmeta :  Add server metadata
    addr    :  List a server's nic address
    console :  Get a VNC console
    create  :  Create a server
    delete  :  Delete a server
    delmeta :  Delete server metadata
    firewall:  Set the server's firewall profile
    info    :  Get server details
    list    :  List servers
    meta    :  Get a server's metadata
    reboot  :  Reboot a server
    rename  :  Update a server's name
    setmeta :  Update server's metadata
    shutdown:  Shutdown a server
    start   :  Start a server
    stats   :  Get server statistics
    wait    :  Wait for server to finish [BUILD, STOPPED, REBOOT, ACTIVE]


    Example 4.1.2: Cyclades help contains all first-level commands of cyclades command group

.. code-block:: console

    $ kamaki server list -h
    usage: kamaki server list  [-v] [-s] [-V] [-d] [-i] [--config CONFIG]
                               [-o OPTIONS] [-h] [-l]

    List servers

    optional arguments:
      -v, --verbose         More info at response
      -s, --silent          Do not output anything
      -V, --version         Print current version
      -d, --debug           Include debug output
      -i, --include         Include protocol headers in the output
      --config CONFIG       Path to configuration file
      -o OPTIONS, --options OPTIONS
                            Override a config value
      -h, --help            Show help message
      -l                    show detailed output


      Example 4.1.3: Help for command "server list" with syntax, description and avaiable user options

Using history
"""""""""""""

Kamaki command history is stored in a file at user home (".kamaki.history" by default). To set a custom history file path users must set the history.file config option (see `available config options <setup.html#editing-options>`_).

Every syntactically correct command is appended at the end of that file. In order to see how to use history, use the kamaki help system:

.. code-block:: console

    $ kamaki history -h
    ...
    clean:  Clean up history
    show :  Show history


    Example 4.2.1: Available history options

The following example showcases how to use history in kamaki

.. code-block:: console

    $ kamaki history clean --match clean
    $ kamaki server list
    ...
    $ kamaki history show
    1.  kamaki server list
    2.  kamaki history show
    $ kamaki history show --match server
    1. kamaki server list
    3. kamaki history show --match server


    Example 4.2.2: Clean up everything, run a kamaki command, show full and filtered history

Debug
"""""

In case of errors, kamaki in debug mode shows usefull debug information, like the stack trace, instead of a user-friendly error message. Kamaki also suppresses various warning messages that are also allowed in debug mode.

To run kamaki in debug mode use the -d or --debug option

Verbose
"""""""

Most kamaki commands are translated into http requests. Kamaki clients API translated the semantics to REST and handles the response. Users who need to have access to these commands can use the verbose mode that presentes the HTTP Request details as well as the full server response.

To run kamaki in verbose mode use the -v or --verbose option

Client commands
"""""""""""""""


Kamaki commands can be used along with advanced shell features.

.. code-block:: console

    $ kamaki server list -l > vmlist.txt


    Example 4.4.1: Store a vm list in file vmlist.txt in a unix shell

Interactive shell
^^^^^^^^^^^^^^^^^



Creating applications over the Clients API
------------------------------------------
