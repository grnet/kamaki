Usage
=====

Kamaki offers command line interfaces that implement specific command specifications. A detailed list of the command specifications can be found in `Commands <commands.html>`_ section. This guide covers the generic usage of both interfaces.

What's more, kamaki offers a clients API that allows the development of external applications for synnefo. The clients API is listed in the `Clients lib <clients.html>`_ section. The recommended method of utilizing this API is explained in the present.

Setup
-----

Kamaki interfaces rely on a list of configuration options. In the initial state, kamaki is configured to communicate with the Okeanos IaaS. A detailed guide for setting up kamaki can be found in the `Setup <setup.html>`_ section.

Quick guide
^^^^^^^^^^^

It is essential for users to get a configuration token (to get in Okeanos.grnet.gr log `here <https://accounts.okeanos.grnet.gr/im/>`_) and provide it to kamaki:

.. code-block:: console
    :emphasize-lines: 1

    Example 1.1.1: Set user token to myt0k3n==

    $ kamaki set token myt0k3n==

To use the storage service, a user should also provide the corresponding user-name:

.. code-block:: console
    :emphasize-lines: 1

    Example 1.1.2: Set user name to user@domain.com

    $ kamaki set account user@domain.com

Shell vs one-command
--------------------
Kamaki users can access synnefo services through either the interactive shell or the one-command behaviors. In practice, both systems rely on the same command set implementations and API clients, with identical responses and error messages. Still, there are some differences.

In favor of interactive shell behavior:

* tab completion for commands
* session history with "up" / "down" keys
* shorter commands with command context switching

In favor of one-command behavior:

* can be used along with advanced shell features (pipelines, redirection, etc.)
* can be used in shell scripts
* prints debug and verbose messages if needed

Run as shell
^^^^^^^^^^^^
To use kamaki as a shell, run:

* without any parameters or arguments

.. code-block:: console
    :emphasize-lines: 1

    Example 2.2.1: Run kamaki shell

    $ kamaki

* with any kind of '-' prefixed arguments, except '-h', '--help'.

.. code-block:: console
    :emphasize-lines: 1

    Example 2.2.2: Run kamaki shell with custom configuration file

    $ kamaki --config myconfig.file


Run as one-command
^^^^^^^^^^^^^^^^^^
To use kamaki as an one-command tool, run:

* with the '-h' or '--help' arguments (help for kamaki one-command)

.. code-block:: console
    :emphasize-lines: 1

    Example 2.3.1: Kamaki help

    $kamaki -h

* with one or more command parameters:

.. code-block:: console
    :emphasize-lines: 1

    Example 2.3.2: List VMs managed by user

    $ kamaki server list

Commands
--------

Client commands are grouped by service (see example 3.1.1 on how to list available groups). Commands behavior is as uniform as possible, but there are still differences between groups due to the special nature of each service and server-side implementation.

Typically, commands consist of a group name (e.g. store for storage commands) one or more terms (e.g. list for listing) and the command specific parameters (e.g. the name of the container), if any.

.. code-block:: console
    :emphasize-lines: 1

    Example 3.1.1: List stored files in container mycontainer.

    $ kamaki store list mycontainer

Example 2.3.2 showcases a command without parameters (the group is "server", the command is "list").

The "server" command group is also referred in the following example.

.. code-block:: console
    :emphasize-lines: 1

    Example 3.1.2 Show information about a user-managed VM with id 42

    $ kamaki server info 42

Client commands can feature an arbitrary number of terms:

.. code-block:: text

    kamaki <group> <cmd term 1> <cmd term 2> ... <cmd term N> [arguments]

Although there are no multi-termed client commands until version 0.6.1 , the feature is supported and might be used in feature extensions.

The following pattern applies to all client commands up to version 0.6.1:

.. code-block:: text

    kamaki <group> <command> [arguments]

The commands supported in version 0.6.1 are described bellow, grouped by service. The examples showcase a sample set of group commands. The kamaki interactive shell has been chosen as the execution environment:

astakos (Identity Manager)
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: text

    authenticate:  Authenticate a user

Showcase: get user information, provided the token was set

.. code-block:: console
    :emphasize-lines: 1,4

    * Enter astakos context *
    [kamaki]:astakos

    * Authenticate user *
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

flavor (Compute/Cyclades)
^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: text

    info:  Get flavor details
    list:  List flavors

Showcase: show details for flavor with id 43

.. code-block:: console
    :emphasize-lines: 1,4

    * Enter flavor context *
    [kamaki]: flavor

    * Get details about flavor with id 43 *
    [flavor]: info 43
    SNF:disk_template:  drbd
    cpu              :  4
    disk             :  10
    id               :  43
    name             :  C4R2048D10
    ram              :  2048

image (Compute/Cyclades + Glance)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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

Showcase: Pick an image and list the properties

.. code-block:: console
    :emphasize-lines: 1,4,18

    * Enter image context *
    [kamaki]:image

    * list all available images *
    [image]:list
    1395fdfb-51b4-419f-bb02-f7d632860611 (Ubuntu Desktop LTS)
    1580deb4-edb3-4496-a27f-7a246c4c0528 (Ubuntu Desktop)
    18a82962-43eb-4b32-8e28-8f8880af89d7 (Kubuntu LTS)
    6aa6eafd-dccb-422d-a904-67fe2bdde87e (Debian Desktop)
    6b5681e4-7502-46ae-b1e9-9fd837932095 (maelstrom)
    78262ee7-949e-4d70-af3a-85360c3de57a (Windows Server 2012)
    86bc2414-0fb3-4898-a637-240292243302 (Fedora)
    926ab1c5-2d85-49d4-aebe-0fce712789b9 (Windows Server 2008)
    b2dffe52-64a4-48c3-8a4c-8214cc3165cf (Debian Base)
    baf2321c-57a0-4a69-825d-49f49cea163a (CentOS)
    c1d27b46-d875-4f5c-b7f1-f39b5af62905 (Kubuntu)

    * Get properties of image with id b2dffe52-64a4-48c3-8a4c-8214cc3165cf *
    [image]:properties b2dffe52-64a4-48c3-8a4c-8214cc3165cf
    description   :  Debian 6.0.6 (Squeeze) Base System
    gui           :  No GUI
    kernel        :  2.6.32
    os            :  debian
    osfamily      :  linux
    root_partition:  1
    sortorder     :  1
    users         :  root

server (Compute/Cyclades)
^^^^^^^^^^^^^^^^^^^^^^^^^

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

Showcase: Create a server.

.. code-block:: console
    :emphasize-lines: 1,4,21,35,44,62

    * Enter server context *
    [kamaki]:server

    * See server-create help *
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

    * List all available images *
    [server]:/image list
    1395fdfb-51b4-419f-bb02-f7d632860611 (Ubuntu Desktop LTS)
    1580deb4-edb3-4496-a27f-7a246c4c0528 (Ubuntu Desktop)
    18a82962-43eb-4b32-8e28-8f8880af89d7 (Kubuntu LTS)
    6aa6eafd-dccb-422d-a904-67fe2bdde87e (Debian Desktop)
    6b5681e4-7502-46ae-b1e9-9fd837932095 (maelstrom)
    78262ee7-949e-4d70-af3a-85360c3de57a (Windows Server 2012)
    86bc2414-0fb3-4898-a637-240292243302 (Fedora)
    926ab1c5-2d85-49d4-aebe-0fce712789b9 (Windows Server 2008)
    b2dffe52-64a4-48c3-8a4c-8214cc3165cf (Debian Base)
    baf2321c-57a0-4a69-825d-49f49cea163a (CentOS)
    c1d27b46-d875-4f5c-b7f1-f39b5af62905 (Kubuntu)

    * See details of flavor with id 1 *
    [server]:/flavor info 1
    SNF:disk_template:  drbd
    cpu              :  1
    disk             :  20
    id               :  1
    name             :  C1R1024D20
    ram              :  1024

    * Create a debian server named 'My Small Debian Server'
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

    * wait for server to build (optional) *
    [server]:wait 11687
    Server 11687 still in BUILD mode |||||||||||||||||    | 80% - 3s
    Server 11687 is now in ACTIVE mode

.. Note:: In kamaki shell, / is used to access top-level command groups while working in command group contexts

network (Compute/Cyclades)
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: text

    connect   :  Connect a server to a network
    create    :  Create a network
    delete    :  Delete a network
    disconnect:  Disconnect a nic of a server to a network
    info      :  Get network details
    list      :  List networks
    rename    :  Update network name

Showcase: Connect a network to a VM

.. code-block:: console
    :emphasize-lines: 1,4,9,24,27,44

    * Enter network context *
    [kamaki]:network

    * List user-owned VMs *
    [network]:/server list
    11687 (My Small Debian Server)
    11688 (An Ubuntu server)

    * Try network-connect (to get help) *
    [network]:connect 
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

    * Get connectivity details on VM with id 11687 *
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

.. Note:: In kamaki shell, / is used to access top-level command groups while working in command group contexts

store (Storage/Pithos+)
^^^^^^^^^^^^^^^^^^^^^^^

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

Showcase: Upload and download a file.

.. code-block:: console
    :emphasize-lines: 1,7,11,16,21,29,33,37,41,44,51,55,60,64

    * Create a random binarry file at current OS path *
    [kamaki]:!dd bs=4M if=/dev/zero of=rndm_local.file count=5
    5+0 records in
    5+0 records out
    20971520 bytes (21 MB) copied, 0.016162 s, 1.3 GB/s

    * Enter store context *
    [kamaki]:store


    * Check local file *
    [store]:!ls -lh rndm_local.file
    -rw-rw-r-- 1 ******** ******** 20M Nov 26 15:36 rndm_local.file


    * Create two containers *
    [store]:create mycont1
    [store]:create mycont2


    * List accessible containers *    
    [store]:list
    1. mycont1 (0B, 0 objects)
    2. mycont2 (0B, 0 objects)
    3. pithos (0B, 0 objects)
    4. trash (0B, 0 objects)


    * Upload local file to 1st container *
    [store]:upload rndm_local.file mycont1


    * Check if file has been uploaded *
    [store]:list mycont1
    1.    20M rndm_local.file

    * Create director mydir on second container *
    [store]:mkdir mycont2:mydir


    * Move file from 1st to 2nd container (and in the directory) *
    [store]:move mycont1:rndm_local.file mycont2:mydir/rndm_local.file

    * Check the container of both containers *
    [store]:list mycont1
    [store]:list mycont2
    1.      D mydir/
    2.    20M mydir/rndm_local.file


    * Copy file from 2nd to 1st container, with a new name *
    [store]:copy mycont2:mydir/rndm_local.file mycont1:rndm_remote.file


    * Check pasted file *
    [store]:list mycont1
    1.    20M rndm_remote.file


    * Download pasted file to local file system *
    [store]:download mycont1:rndm_remote.file rndm_remote.file


    * Check if file is downloaded and if it is the same to original *
    [store]:!ls -lh *.file
    -rw-rw-r-- 1 ******** ******** 20M Nov 26 15:36 rndm_local.file
    -rw-rw-r-- 1 ******** ******** 20M Nov 26 15:42 rndm_remote.file
    [store]:!diff rndm_local.file rndm_remote.file

.. Note:: In kamaki shell, ! is used to execute OS shell commands (bash in the above)

One-command interface
---------------------

Kamaki usage as a one-command tool is detailed in this section

Using help
^^^^^^^^^^

Kamaki help is used to see available commands, with description, syntax and their corresponding optional arguments.

To see the command groups, users should use -h or --help like in example 1.3.1. In the same way, help information for command groups and commands is printed. In the following examples, the help messages of kamaki, of a command group (server) and of a command in that group (list) are shown.

.. code-block:: console
    :emphasize-lines: 1

    Example 4.1.1: kamaki help shows available parameters and command groups


    $ kamaki -h
    usage: kamaki <cmd_group> [<cmd_subbroup> ...] <cmd>
        [-s] [-V] [-i] [--config CONFIG] [-o OPTIONS] [-h]

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

.. code-block:: console
    :emphasize-lines: 1

    Example 4.1.2: Cyclades help contains all first-level commands of Cyclades command group


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

.. code-block:: console
    :emphasize-lines: 1

    Example 4.1.3: Help for command "server list" with syntax, description and available user options


    $ kamaki server list -h
    usage: kamaki server list [-V] [-i] [--config CONFIG] [-h] [-l]

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

.. _using-history-ref:

Using history
^^^^^^^^^^^^^

Kamaki command history is stored in a file at user home (".kamaki.history" by default). To set a custom history file path users must set the history.file config option (see `available config options <setup.html#editing-options>`_).

Every syntactically correct command is appended at the end of that file. In order to see how to use history, use the kamaki help system:

.. code-block:: console
    :emphasize-lines: 1

    Example 4.2.1: Available history options


    $ kamaki history -h
    ...
    clean:  Clean up history
    show :  Show history

The following example showcases how to use history in kamaki

.. code-block:: console
    :emphasize-lines: 1

    Example 4.2.2: Clean up everything, run a kamaki command, show full and filtered history
    

    $ kamaki history clean
    $ kamaki server list
    ...
    $ kamaki history show
    1.  kamaki server list
    2.  kamaki history show
    $ kamaki history show --match server
    1. kamaki server list
    3. kamaki history show --match server

Debug
^^^^^

In case of errors, kamaki in debug mode shows useful debug information, like the stack trace, instead of a user-friendly error message. Kamaki also suppresses various warning messages that are also allowed in debug mode.

To run kamaki in debug mode use the -d or --debug option

Verbose
"""""""

Most kamaki commands are translated into http requests. Kamaki clients API translated the semantics to REST and handles the response. Users who need to have access to these commands can use the verbose mode that presents the HTTP Request details as well as the full server response.

To run kamaki in verbose mode use the -v or --verbose option

One-command features
^^^^^^^^^^^^^^^^^^^^

Kamaki commands can be used along with advanced shell features.

.. code-block:: console
    :emphasize-lines: 1

    Example 4.4.1: Print username for token us3rt0k3n== using grep
    

    $ kamaki astakos authenticate -o token=us3rt0k3n== | grep uniq
    uniq        : user@synnefo.org

The -o argument can be used to override temporarily various (set or unset) options. In one command, all -o options are forgotten just after the command had been completed, and the previous settings are restored (the configuration file is not modified).

The astakos-authenticate command in example 4.4.1 run against an explicitly provided token, which temporarily overrode the token provided in the configuration file.

Interactive shell
-----------------

Kamaki interactive shell is details in this section

Command Contexts
^^^^^^^^^^^^^^^^

The kamaki interactive shell implements the notion of command contexts. Each command group is also a context where the users can **enter** by typing the group name. If the context switch is successful, the kamaki shell prompt changes to present the new context ("store" in example 5.1.1).

.. code-block:: console
    :emphasize-lines: 1

    Example 5.1.1: Enter store commands context / group


    $ kamaki
    [kamaki]:store
    [store]:

Type **exit** or **ctrl-D** to exit a context and return to the context of origin. If already at the top context (kamaki), an exit is equivalent to exiting the program.

.. code-block:: console
    :emphasize-lines: 1

    Example 5.1.2: Exit store context and then exit kamaki

    [store]: exit
    [kamaki]: exit
    $

A user might **browse** through different contexts during one session.

.. code-block:: console
    :emphasize-lines: 1

    Example 5.1.3: Execute list command in different contexts

    $ kamaki
    [kamaki]:config
    [config]:list
    ... (configuration options listing) ...
    [config]:exit
    [kamaki]:store
    [store]:list
    ... (storage containers listing) ...
    [store]:exit
    [kamaki]:server
    [server]:list
    ... (VMs listing) ...
    [server]: exit
    [kamaki]:

Users have the option to avoid switching between contexts: all commands can run from the **top context**. As a result, examples 5.1.3 and 5.1.4 are equivalent.

.. code-block:: console
    :emphasize-lines: 1

    Example 5.1.4: Execute different "list" commands from top context


    [kamaki]:config list
    ... (configuration options listing) ...
    [kamaki]:store list
    ... (storage container listing) ...
    [kamaki]:server list
    ... (VMs listing) ...
    [kamaki]:

Using Help
^^^^^^^^^^

There are two help mechanisms: a context-level and a command-level.

**Context-level help** lists the available commands in a context and can also offer a short description for each command.

Context-level help syntax::

    * Show available commands in current context *
    [context]:help
    [context]:?

    * Show help for command cmd *
    [context]:help cmd
    [context]:?cmd

The context-level help results change from context to context

.. code-block:: console
    :emphasize-lines: 1

    Example 5.2.1: Get available commands, pick a context and get help there as well


    [kamaki]:help

    kamaki commands:
    ================
    astakos  config  flavor  history  image  network  server  store

    interactive shell commands:
    ===========================
    exit  help  shell

    [kamaki]:?config
    Configuration commands (config -h for more options)

    [kamaki]:config

    [config]:?

    config commands:
    ================
    delete  get  list  set

    interactive shell commands:
    ===========================
    exit  help  shell

    [config]:help set
    Set a configuration option (set -h for more options)

In context-level, there is a distinction between kamaki-commands and interactive shell commands. The former are available in one-command mode and are related to the cloud client setup and use, while the later are context-shell functions.

**Command-level help** prints the syntax, arguments and description of a specific (terminal) command

Command-level help syntax::

    * Get help for command cmd1 cmd2 ... cmdN *
    [context]:cmd1 cmd2 ... cmdN -h
    <syntax>

    <description>

    <arguments and possible extensions>

Command-level help mechanism is exactly the same as the one used in one-command mode. For example, it is invoked by using the -h or --help parameter at any point.

.. code-block:: console
    :emphasize-lines: 1

    Example 5.2.2: Get command-level help for config and config-set


    [kamaki]:config --help
    config: Configuration commands
    delete:  Delete a configuration option (and use the default value)
    get   :  Show a configuration option
    list  :  List configuration options
    set   :  Set a configuration option

    [kamaki]:config

    [config]:set -h
    usage: set <option> <value> [-v] [-d] [-h] [-i] [--config CONFIG] [-s]

    Set a configuration option

    optional arguments:
      -v, --verbose    More info at response
      -d, --debug      Include debug output
      -h, --help       Show help message
      -i, --include    Include protocol headers in the output
      --config CONFIG  Path to configuration file
      -s, --silent     Do not output anything

There are many ways of producing a help message, as shown in example 5.2.3

.. code-block:: console
    :emphasize-lines: 1

    Example 5.2.3: Equivalent calls of command-level help for config-set


    [config]:set -h
    [config]:set -help
    [kamaki]:config set -h
    [kamaki]:config set --help
    [store]:/config set -h
    [server]:/config set --help

.. _accessing-top-level-commands-ref:

Accessing top-level commands
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When working in a context, it is often useful to access other contexts or top-level commands. Kamaki offers access to top-level commands by using the / prefix, as shown bellow::

    * access a command "anothercontext cmd1 cmd2 ... cmdN"
    [context]:/anothercontext cmd1 cmd2 ... cmdN

An example (5.3.1) that showcases how top-level access improves user experience is the creation of a VM. A VM is created with the command server-create. This command is called with three parameters:

* the name of the new VM
* the flavor id
* the image id

It is often the case that a user who works in the context command, needs to create a new VM, but doesn't know the flavor or image id of preference. Therefore, it is necessary to list all available flavors (flavor-list) or images (image-list. Both commands belong to different contexts.

.. code-block:: console
    :emphasize-lines: 1

    Example 5.3.1: Create a VM from server context

    [server]:create -h
    create <name> <flavor id> <image id> ...
    ...
    
    [server]:/flavor list
    ...
    20. AFLAVOR
        SNF:disk_template:  drbd
        cpu              :  4
        disk             :  10
        id               :  43
        ram              :  2048
    
    [server]:/image list
    1580deb4-edb3-7a246c4c0528 (Ubuntu Desktop)
    18a82962-43eb-8f8880af89d7 (Windows 7)
    531aa018-9a40-a4bfe6a0caff (Windows XP)
    6aa6eafd-dccb-67fe2bdde87e (Debian Desktop)
    
    [server]:create 'my debian' 43 6aa6eafd-dccb-67fe2bdde87e
    ...

An other example (5.3.2) showcases how to acquire and modify configuration settings from a different context. In this scenario, the user token expires at server side while the user is working. When that happens, the system responds with an *(401) UNAUTHORIZED* message. The user can acquires a new token (with a browser) which has to be set to kamaki.

.. code-block:: console
    :emphasize-lines: 1

    Example 5.3.2: Set a new token from store context


    [store]:list
    (401) UNAUTHORIZED Access denied

    [store]:/astakos authenticate
    (401) UNAUTHORIZED Invalid X-Auth-Token

    [store]:/config get token
    my3xp1r3dt0k3n==

    [store]:/config set token myfr35ht0k3n==

    [store]:/config get token
    myfr35ht0k3n==

    [store]:list
    1.  pithos (10MB, 2 objects)
    2.  trash (0B, 0 objects)

The following example compares some equivalent calls that run *astakos-authenticate* after a *store-list* 401 failure.

.. code-block:: console
    :emphasize-lines: 1,3,10,17,26

    Example 5.3.3: Equivalent astakos-authenticate calls after a store-list 401 failure

    * without kamaki interactive shell *
    $ kamaki store list
    (401) UNAUTHORIZED Access denied
    $ kamaki astakos authenticate
    ...
    $

    * from top-level context *
    [kamaki]:store list
    (401) UNAUTHORIZED Access denied
    [kamaki]:astakos authenticate
    ...
    [kamaki]

    * maximum typing *
    [store]:list
    (401) UNAUTHORIZED Access denied
    [store]:exit
    [kamaki]:astakos
    [astakos]:authenticate
    ...
    [astakos]:

    * minimum typing *
    [store]: list
    (401) UNAUTHORIZED Access denied
    [store]:/astakos authenticate
    ...
    [store]:

.. hint:: To exit kamaki shell while in a context, try */exit*

Using config
^^^^^^^^^^^^

The configuration mechanism of kamaki is detailed at the `setup section <setup.html>`_ and it is common for both interaction modes. In specific, the configuration mechanism is implemented as a command group, namely *config*. Using the config commands is as straightforward as any other kamaki commands.

It is often useful to set, delete or update a value. This can be managed either inside the config context or from any command context by using the / detour.

.. Note:: config updates in kamaki shell persist even after the session is over. All setting changes affects the physical kamaki config file (automatically created, if not set manually)

In example 5.4.1 the user is going to work with only one storage container. The store commands use the container:path syntax, but if the user could set a container as a default, the container name could be omitted in most cases. This is possible by setting a store.container setting.

.. code-block:: console
    :emphasize-lines: 1

    Example 5.4.1: Set default storage container


    [store]:list
    1.  mycontainer (32MB, 2 objects)
    2.  pithos (0B, 0 objects)
    3.  trash (2MB, 1 objects)

    [store]:list mycontainer
    1.  D mydir/
    2.  20M mydir/rndm_local.file
    
    [store]:/config set store.container mycontainer

    [store]: list
    1.  D mydir/
    2.  20M mydir/rndm_local.file

After a while, the user needs to work with multiple containers, therefore a default container is not longer needed. The store.container setting can be deleted, as shown in example 5.4.2 .

.. code-block:: console
    :emphasize-lines: 1

    Example 5.4.2: Delete a setting option


    [store]:/config delete store.container

    [store]:list
    1.  mycontainer (32MB, 2 objects)
    2.  pithos (0B, 0 objects)
    3.  trash (2MB, 1 objects)

.. warning:: In some cases, the config setting updates are not immediately effective. If that is the case, they will be after the next command run, whatever that command is.

Using history
^^^^^^^^^^^^^

There are two history modes: session and permanent. Session history keeps record of all actions in a kamaki shell session, while permanent history appends all commands to an accessible history file.

Session history is only available in interactive shell mode. Users can iterate through past commands in the same session by with the *up* and *down* keys. Session history is not stored, although syntactically correct commands are recorded through the permanent history mechanism

Permanent history is implemented as a command group and is common to both the one-command and shell interfaces. In specific, every syntactically correct command is appended in a history file (configured as *history.file* in settings, see `setup section <setup.html>`_ for details). Commands executed in one-command mode are mixed with the ones run in kamaki shell (also see :ref:`using-history-ref` section on this guide).

Tab completion
^^^^^^^^^^^^^^

Kamaki shell features tab completion for the first level of command terms of the current context. Tab completion pool changes dynamically when the context is switched. Currently, tab completion is not supported when the / detour is used (see :ref:accessing-top-level-commands-ref ).

OS Shell integration
^^^^^^^^^^^^^^^^^^^^

Kamaki shell features the ability to execute OS-shell commands from any context. This can be achieved by typing *!* or *shell*::

    [kamaki_context]:!<OS shell command>
    ... OS shell command output ...

    [kamaki_context]:shell <OS shell command>
    ... OS shell command output ...

.. code-block:: console
    :emphasize-lines: 1

    Example 5.7.1: Run unix-style shell commands from kamaki shell


    [kamaki]:!ls -al
    total 16
    drwxrwxr-x 2 saxtouri saxtouri 4096 Nov 27 16:47 .
    drwxrwxr-x 7 saxtouri saxtouri 4096 Nov 27 16:47 ..
    -rw-rw-r-- 1 saxtouri saxtouri 8063 Jun 28 14:48 kamaki-logo.png

    [kamaki]:shell cp kamaki-logo.png logo-copy.png

    [kamaki]:shell ls -al
    total 24
    drwxrwxr-x 2 saxtouri saxtouri 4096 Nov 27 16:47 .
    drwxrwxr-x 7 saxtouri saxtouri 4096 Nov 27 16:47 ..
    -rw-rw-r-- 1 saxtouri saxtouri 8063 Jun 28 14:48 kamaki-logo.png
    -rw-rw-r-- 1 saxtouri saxtouri 8063 Jun 28 14:48 logo-copy.png


Kamaki shell commits command strings to the outside shell and prints the results, without interacting with it. After a command is finished, kamaki shell returns to its initial state, which involves the current directory, as show in example 5.7.2 .

.. code-block:: console
    :emphasize-lines: 1

    Example 5.7.2: Attempt (and fail) to change working directory


    [kamaki]:!pwd
    /home/username

    [kamaki]:!cd ..

    [kamaki]:shell pwd
    /home/username
