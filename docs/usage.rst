Usage
=====

Kamaki offers command-line interfaces that implement specific command
specifications. A detailed list of the command specifications can be found in
`Commands <commands.html>`_ section. This guide covers the generic usage of
both interfaces.

What's more, kamaki offers a clients library for the development of external
client applications for Synnefo. The clients library API is detailed in the
`Clients lib <developers/code.html#the-clients-api>`_ section.

Quick Setup
-----------

Kamaki interfaces rely on a list of configuration options. A detailed guide for
setting up kamaki can be found in the `Setup <setup.html>`_ section.

As rule of the thump, it is enough to set the authentication URL and user token
for the cloud kamaki should communicate with by default:

.. code-block:: console
    :emphasize-lines: 1

    Example 1.1: Set authentication URL, user token and cloud alias "default"

    $ kamaki config set cloud.default.url <authentication URL>
    $ kamaki config set cloud.default.token myt0k3n==

.. note:: The term *default* can be replaced by any arbitary term chosen by
    the user. This term will serve as a cloud alias for kamaki users, and can
    be easily modified.

Shell vs one-command
--------------------
Kamaki users can access Synnefo services through either the interactive shell
or the one-command interface. In practice, both systems rely on the same
command set implementations and API clients, with identical responses and error
messages. Still, there are some differences.

In favor of interactive shell:

* tab completion for commands (if supported by the user shell)
* session history with ↑ or ↓ keys (if supported by the user shell)
* shorter commands with command context switching
* re-run old commands with /history

In favor of one-command:

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

* with any kind of '-' prefixed arguments, except '-h', '--help', '-V',
    '- - version'.

.. code-block:: console
    :emphasize-lines: 1

    Example 2.2.2: Run kamaki shell with custom configuration file

    $ kamaki -c myconfig.file


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

    Example 2.3.2: List servers managed by user

    $ kamaki server list

One-command interface
---------------------

Using help
^^^^^^^^^^

Kamaki help provides information on available commands (description, syntax and
corresponding optional arguments).

To see the command groups, use -h or --help (example 1.3.1). The
following examples demonstrate the help messages of kamaki, in the context of a
command group (server) and of a command in that group (list).

.. code-block:: console
    :emphasize-lines: 1

    Example 3.1.1: kamaki help shows available parameters and command groups


    $ kamaki -h
    usage: kamaki <cmd_group> [<cmd_subbroup> ...] <cmd>
        [-v] [-s] [-V] [-d] [-i] [-c CONFIG] [-o OPTIONS] [--cloud CLOUD] [-h]

    optional arguments:
      -v, --verbose         More info at response
      -s, --silent          Do not output anything
      -V, --version         Print current version
      -d, --debug           Include debug output
      -i, --include         Include protocol headers in the output
      -c CONFIG, --config CONFIG
                            Path to configuration file
      -o OPTIONS, --options OPTIONS
                            Override a config value
      --cloud CLOUD         Chose a cloud to connect to
      -h, --help            Show help message

    Options:
     - - - -
    network: Cyclades/Compute API network commands
    user: Astakos API commands
    livetest: Client func. tests on live servers
    server: Cyclades/Compute API server commands
    project: Synnefo project management CLI
    file: Pithos+/Storage API commands
    flavor: Cyclades/Compute API flavor commands
    config: Kamaki configurations
    image: Cyclades/Plankton API image commands
    image compute:  Cyclades/Compute API image commands
    history: Kamaki command history


.. code-block:: console
    :emphasize-lines: 1,2

    Example 3.1.2: Cyclades help contains all first-level commands of Cyclades
    command group

    $ kamaki server -h
    usage: kamaki server <...> [-v] [-s] [-V] [-d] [-i] [-c CONFIG]
                               [-o OPTIONS] [--cloud CLOUD] [-h]

    optional arguments:
      -v, --verbose         More info at response
      -s, --silent          Do not output anything
      -V, --version         Print current version
      -d, --debug           Include debug output
      -i, --include         Include protocol headers in the output
      -c CONFIG, --config CONFIG
                            Path to configuration file
      -o OPTIONS, --options OPTIONS
                            Override a config value
      --cloud CLOUD         Chose a cloud to connect to
      -h, --help            Show help message

    Options:
     - - - -
    info: Detailed information on a Virtual Machine
    rename: Set/update a virtual server name
    delete: Delete a virtual server
    console: Get a VNC console to access an existing virtual server
    addr: List the addresses of all network interfaces on a virtual server
    firewall: Manage virtual server firewall profiles for public networks
    create: Create a server (aka Virtual Machine)
    list: List Virtual Machines accessible by user
    reboot: Reboot a virtual server
    start: Start an existing virtual server
    shutdown: Shutdown an active virtual server
    stats: Get virtual server statistics
    metadata: Manage Server metadata (key:value pairs of server attributes)
    resize: Set a different flavor for an existing server
    wait: Wait for server to finish [BUILD, STOPPED, REBOOT, ACTIVE]

.. code-block:: console
    :emphasize-lines: 1,2

    Example 3.1.3: Help for command "server list" with syntax, description and
    available user options

    $ kamaki server list -h
    usage: kamaki server list [-v] [-s] [-V] [-d] [-i] [-c CONFIG] [-o OPTIONS]
                              [--cloud CLOUD] [-h] [--since SINCE] [--enumerate]
                              [-l] [--more] [-n LIMIT] [-j]

    List Virtual Machines accessible by user

    optional arguments:
      -v, --verbose         More info at response
      -s, --silent          Do not output anything
      -V, --version         Print current version
      -d, --debug           Include debug output
      -i, --include         Include raw connection data in the output
      -c CONFIG, --config CONFIG
                            Path to config file
      -o OPTIONS, --options OPTIONS
                            Override a config value
      --cloud CLOUD         Chose a cloud to connect to
      -h, --help            Show help message
      --status STATUS       filter by status (ACTIVE, STOPPED, REBOOT, ERROR,
                            etc.)
      --enumerate           Enumerate results
      --name-suffix NAME_SUFF
                            filter by name suffix (case insensitive)
      --image-id IMAGE_ID   filter by image id
      --metadata META       filter by metadata key=values
      -j, --json            show headers in json
      --id ID               filter by id
      --user-id USER_ID     filter by user id
      --id-like ID_LIKE     print only if id contains this (case insensitive)
      --id-suffix ID_SUFF   filter by id suffix (case insensitive)
      --since SINCE         show only items since date (' d/m/Y H:M:S ')
      -l, --details         show detailed output
      --name NAME           filter by name
      --more                output results in pages (-n to set items per page,
                            default 10)
      --name-prefix NAME_PREF
                            filter by name prefix (case insensitive)
      -n LIMIT, --number LIMIT
                            limit number of listed virtual servers
      --id-prefix ID_PREF   filter by id prefix (case insensitive)
      --user-name USER_NAME
                            filter by user name
      --name-like NAME_LIKE
                            print only if name contains this (case insensitive)
      --metadata-like META_LIKE
                            print only if in key=value, the value is part of
                            actual value
      --flavor-id FLAVOR_ID
                            filter by flavor id

    Details:
    Use filtering arguments (e.g., --name-like) to manage long server lists

.. _using-history-ref:

Using history
^^^^^^^^^^^^^

Kamaki command history is stored in a file at user home (".kamaki.history" by default). To set a custom history file path users must set the history.file config option (see `available config options <setup.html#editing-options>`_).

Every command is appended at the end of that file. In order to see how to use
history, use the kamaki help system:

.. code-block:: console
    :emphasize-lines: 1

    Example 3.2.1: Available history options


    $ kamaki history -h
    Options:
     - - - -
    clean:  Clean up history (permanent)
    run  :  Run previously executed command(s)
    show :  Show intersession command history

The following example showcases how to use history in kamaki

.. code-block:: console
    :emphasize-lines: 1

    Example 3.2.2: Clean up everything, run a kamaki command, show full and filtered history
    

    $ kamaki history clean
    $ kamaki server list
    ...
    $ kamaki history show
    1.  kamaki server list
    2.  kamaki history show
    $ kamaki history show --match server
    1. kamaki server list
    3. kamaki history show --match server

Debug and logging
^^^^^^^^^^^^^^^^^

Debug
"""""

When in debug mode, kamaki outputs some useful debug information (stack trace
and http logs). Kamaki in debug mode cancels suppression of warning messages.

To run kamaki in debug mode use the -d or --debug option.


Verbose
"""""""

Most kamaki commands are translated into http requests. Kamaki clients API
translated the semantics to REST and handles the response. Users who need to
have access to these commands can use the verbose mode that presents the HTTP
Request details as well as the full server response.

To run kamaki in verbose mode use the *-v/- - verbose* option

Verbose mode outputs the request and response mode, address and
headers as well as the size of the data block, if any. Sensitive information
(x-auth-token header and data body) are omitted by default,. Users who need
this information may enable it through the log_token and log_data configuration
options (see next section)

.. tip:: Use the -o runtime option to enable config options on the fly, e.g, to
    include http data:

    .. code-block:: console

        $ kamaki server list -v -o log_data=on


Logging
"""""""

Kamaki keeps its logs in a file specified by the *log_file* option and it
defaults to *${HOME}/.kamaki.log*. This configuration option can be modified::

    kamaki config set log_file /new/log/file/path

Kamaki logs http request and response information, namely the method, URL,
headers and data size. Sensitive information (data and token header) are
omitted by default. There are some configuration options that can switch them
on, though:

* HTTP data blocks are not logged by default
    to enable logging the full http bodies, set log_data to `on`::

        kamaki config set log_data on

    to disable it, set it to `off`::

        kamaki config set log_data off

    or delete it::

        kamaki config delete log_data

* X-Auth-Token header is not logged by default
    to enable logging the X-Auth-Token header, set log_token to `on`::

        kamaki config set log_token on

    to disable it, set it to `off`::

        kamaki config set log_token off

    or delete it::

        kamaki config delete log_token

* The information (pid, name, date) of the processes that handle http requests
    is not logged by default, because if they are, logs are difficult to read.
    Still, they are useful for resolving race condition problems, so to enable
    logging proccess information::

        kamaki config set log_pid on

    to disable it, set if to off::

        kamaki config set log_pid off

    or delete it::

        kamaki config delete log_pid

One-command features
^^^^^^^^^^^^^^^^^^^^

Kamaki commands can be used along with advanced shell features.

.. code-block:: console
    :emphasize-lines: 1

    Example 3.4.1: List the trash container contents, containing c1_
    

    $ kamaki file list -o cloud.default.pithos_container=trash| grep c1_
    c1_1370859409.0 20KB
    c1_1370859414.0 9MB
    c1_1370859409.1 110B

The -o argument can be used to temporarily override various (set or unset)
options. In one command, all -o option sets are forgotten just after the
command has been completed, and the previous settings are restored (the
configuration file is not modified).

The file-list command in example 3.4.1 runs with an explicitly provided
pithos_account, which temporarily overrides the one probably provided in the
configuration file (it works even if the user has not set the optional
pithos_account config option).

.. tip:: There are better ways to list the contents of a container. Example
    3.4.1 is using this method for demonstration purposes only. The suggested
    method for listing container contents is *- - container=<container>*

Interactive shell
-----------------

Command Contexts
^^^^^^^^^^^^^^^^

The kamaki interactive shell implements the notion of command contexts. Each
command group is also a context where the users can **enter** by typing the
group name. If the context switch is successful, the kamaki shell prompt
changes to present the new context ("*file*" in example 4.1.1).

.. code-block:: console
    :emphasize-lines: 1

    Example 4.1.1: Start kamaki and switch to file context


    $ kamaki
    [kamaki]: file
    [file]:

Type **exit** (alternatively **ctrl-D** in (X)nix systems or **ctrl-Z** in
Windows) to exit a context and return to the context of origin. If already at
the top context (kamaki), an exit is equivalent to exiting the program.

.. code-block:: console
    :emphasize-lines: 1

    Example 4.1.2: Exit file context and then exit kamaki

    [file]: exit
    [kamaki]: exit
    $

A user might **browse** through different contexts during one session.

.. code-block:: console
    :emphasize-lines: 1

    Example 4.1.3: Execute list command in different contexts

    $ kamaki
    [kamaki]: config
    [config]: list
    ... (configuration options listing) ...
    [config]: exit
    [kamaki]: file
    [file]: list
    ... (storage containers listing) ...
    [file]: exit
    [kamaki]: server
    [server]: list
    ... (servers listing) ...
    [server]: exit
    [kamaki]:

Users have the option to avoid switching between contexts: all commands can run
from the **top context**. As a result, examples 4.1.3 and 4.1.4 are equivalent.

.. code-block:: console
    :emphasize-lines: 1

    Example 4.1.4: Execute different "list" commands from top context


    [kamaki]: config list
    ... (configuration options listing) ...
    [kamaki]: file list
    ... (storage container listing) ...
    [kamaki]: server list
    ... (servers listing) ...
    [kamaki]:

Using Help
^^^^^^^^^^

There are two help mechanisms: a context-level and a command-level.

**Context-level help** lists the available commands in a context and can also
offer a short description for each command.

Context-level help syntax::

    * Show available commands in current context *
    [context]: help
    ...
    [context]: ?
    ...

    * Show help for command cmd *
    [context]: help cmd
    ...
    [context]: ?cmd
    ...

The context-level help results may change from context to context

.. code-block:: console
    :emphasize-lines: 1

    Example 4.2.1: Get available commands and then get help in a context


    [kamaki]: help

    kamaki commands:
    ================
    user  config  flavor  history  image  network  server  file ...

    interactive shell commands:
    ===========================
    exit  help  shell

    [kamaki]: ?config
    Configuration commands (config -h for more options)

    [kamaki]: config

    [config]: ?

    config commands:
    ================
    delete  get  list  set

    interactive shell commands:
    ===========================
    exit  help  shell

    [config]: help set
    Set a configuration option (set -h for more options)

In context-level, there is a distinction between kamaki-commands and
interactive shell commands. The former are available in one-command mode and
are related to the cloud client setup and use, while the later are
context-shell functions.

**Command-level help** prints the syntax, arguments and description of a
specific (terminal) command

Command-level help syntax::

    * Get help for command cmd1 cmd2 ... cmdN *
    [context]: cmd1 cmd2 ... cmdN -h
    <syntax>

    <description>

    <arguments and possible extensions>

Command-level help mechanism is exactly the same as the one used in
one-command mode. For example, it is invoked by using the -h or --help
parameter at any point.

.. code-block:: console
    :emphasize-lines: 1

    Example 4.2.2: Get command-level help for config and config-set


    [kamaki]: config --help
    config: Configuration commands
    delete:  Delete a configuration option (and use the default value)
    get   :  Show a configuration option
    list  :  List configuration options
    set   :  Set a configuration option

    [kamaki]: config

    [config]: set -h
    usage: set <option> <value> [-v] [-d] [-h] [-i] [--config CONFIG] [-s]

    Set a configuration option

    optional arguments:
      -v, --verbose    More info at response
      -d, --debug      Include debug output
      -h, --help       Show help message
      -i, --include    Include protocol headers in the output
      --config CONFIG  Path to configuration file
      -s, --silent     Do not output anything

There are many ways of producing a help message, as shown in example 4.2.3

.. code-block:: console
    :emphasize-lines: 1

    Example 4.2.3: Equivalent calls of command-level help for config-set


    [config]: set -h
    [config]: set --help
    [kamaki]: config set -h
    [kamaki]: config set --help
    [file]: /config set -h
    [server]: /config set --help

.. _accessing-top-level-commands-ref:

Accessing top-level commands
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When working in a context, it is often useful to access other contexts or
top-level commands. Kamaki offers access to top-level commands by using the
`/` prefix, as shown bellow::

    * access a command "anothercontext cmd1 cmd2 ... cmdN"
    [context]: /anothercontext cmd1 cmd2 ... cmdN

An example (4.3.1) that showcases how top-level access improves user experience
is the creation of a server. A server is created with the command server-create. This
command is called with three parameters:

* the name of the new server
* the flavor id
* the image id

An average user would enter the server context and type *create -h* to check the
syntax of the command. In that point, it would be nice to have some easy way of
accessing the *flavor* and *image* contexts, to list and pick a flavor id and an
image id. This is achieved with the / notation, as demonstrated in the following
example:

.. code-block:: console
    :emphasize-lines: 1

    Example 4.3.1: Create a server from server context

    [server]: create -h
    create <name> <flavor id> <image id> ...
    ...
    
    [server]: /flavor list
    ...
    43 AFLAVOR
        SNF:disk_template:  drbd
        cpu              :  4
        disk             :  10
        ram              :  2048
    
    [server]: /image compute list
    1580deb4-edb3-7a246c4c0528 (Ubuntu Desktop)
    18a82962-43eb-8f8880af89d7 (Windows 7)
    531aa018-9a40-a4bfe6a0caff (Windows XP)
    6aa6eafd-dccb-67fe2bdde87e (Debian Desktop)
    
    [server]: create 'my debian' 43 6aa6eafd-dccb-67fe2bdde87e
    ...

An other example (4.3.2) showcases how to acquire and modify configuration
settings from a different context. In this scenario, the user token expires at
server side while the user is working. When that happens, the system responds
with an *(401) UNAUTHORIZED* message. The user can acquire a new token (valid
for the Astakos identity manager of preference) which has to be set to kamaki.

.. code-block:: console
    :emphasize-lines: 1

    Example 4.3.2: Token suddenly expires. Set a new token from file context


    [file]: list
    (401) UNAUTHORIZED Access denied

    [file]: /user authenticate
    (401) UNAUTHORIZED Invalid X-Auth-Token

    [file]: /config get cloud.default.token
    my3xp1r3dt0k3n==

    [file]: /config set cloud.default.token myfr35ht0k3n==

    [file]: /config get cloud.default
    cloud.default.url = https://astakos.example.com/astakos/identity/2.0/
    cloud.default.token = myfr35ht0k3n==

    [file]: list
    1.  pithos (10MB, 2 objects)
    2.  trash (0B, 0 objects)

.. note:: The error messages on examples are shortened for clarity. Actual error
    messages are more helpful and descriptive.

The following example compares some equivalent calls that run
*user-authenticate* after a *file-list* 401 failure.

.. code-block:: console
    :emphasize-lines: 1,3,10,17,26

    Example 4.3.3: Equivalent user-authenticate calls after a file-list 401

    * I. without kamaki interactive shell *
    $ kamaki file list
    (401) UNAUTHORIZED Access denied
    $ kamaki user authenticate
    ...
    $

    * II. from top-level context *
    [kamaki]: file list
    (401) UNAUTHORIZED Access denied
    [kamaki]: user authenticate
    ...
    [kamaki]

    * III. maximum typing *
    [file]: list
    (401) UNAUTHORIZED Access denied
    [file]: exit
    [kamaki]: user
    [user]: authenticate
    ...
    [user]:

    * IV. minimum typing *
    [file]: list
    (401) UNAUTHORIZED Access denied
    [file]: /user authenticate
    ...
    [file]:

.. hint:: To exit kamaki shell while in a context, try */exit*

Using config
^^^^^^^^^^^^

The configuration mechanism of kamaki is detailed in the
`setup section <setup.html>`_, it is accessible as *config* and it is common for
both interaction modes. In specific, the configuration mechanism is implemented
as  `config`. Using the config commands is as straightforward as in any other
group of commands.

It is often useful to set, delete or update a value. This can be managed either
inside the config context or from any command context by using the / prefix.

.. Note:: config updates in kamaki shell persist even after the session is over

All setting changes affect the physical kamaki config file. The config file is
created automatically at callers' home firectory the first time a config option
is set, and lives there as *.kamakirc* . It can be edited with any text editor
or managed with kamaki config commands.

In example 4.4.1 the user is going to work with only one storage container. The
file commands use the container:path syntax, but if the user sets a container
name as default, the container name can be omitted.

.. code-block:: console
    :emphasize-lines: 1

    Example 4.4.1: Set default storage container (cloud alias: default)


    [file]: list
      mycontainer (32MB, 2 objects)
      pithos (0B, 0 objects)
      trash (2MB, 1 objects)

    [file]: list mycontainer
      D mydir/
      20M mydir/rndm_local.file
    
    [file]: /config set cloud.default.pithos_container mycontainer

    [file]: list
      D mydir/
      20M mydir/rndm_local.file

After a while, the user needs to work with multiple containers, therefore a
default container is no longer needed. The *pithos_container* setting can be
deleted, as shown in example 4.4.2

.. code-block:: console
    :emphasize-lines: 1

    Example 4.4.2: Delete a setting option (cloud: default)


    [file]: /config delete cloud.default.pithos_container

    [file]: list
      mycontainer (32MB, 2 objects)
      pithos (0B, 0 objects)
      trash (2MB, 1 objects)

History modes
^^^^^^^^^^^^^

There are two history modes: session and permanent. Session history keeps
record of all actions in a kamaki shell session, while permanent history
appends all commands to an accessible history file.

Session history is only available in interactive shell mode. Users can iterate
through past commands in the same session with the ↑ and ↓ keys. Session
history is not stored, although commands are recorded through the permanent
history mechanism.

Permanent history is implemented as a command group and is common to both the
one-command and shell interfaces. In specific, every command is appended in a
history file (configured as `history_file` in settings, see
`setup section <setup.html>`_ for details). Commands executed in one-command
mode are mixed with the ones run in kamaki shell (also see
:ref:`using-history-ref` section on this guide).

Scripting
^^^^^^^^^

The history-run feature allows the sequential run of previous command
executions in kamaki shell.

The following sequence copies and downloads a file from *mycontainer1* ,
uploads it to *mycontainer2* , then undo the proccess and repeats it with
history-run

.. code-block:: console
    :emphasize-lines: 1,12,19,32

    * Download mycontainer1:myfile and upload it to mycontainer2:myfile *
    [kamaki]: file
    [file]: copy mycontainer1:somefile mycontainer1:myfile
    [file]: download mycontainer1:myfile mylocalfile
    ...
    Download completed
    [file]: upload mylocalfile mycontainer2:myfile -f
    ...
    Upload completed

    * undo the process *
    [file]: !rm mylocalfile
    [file]: delete mycontainer1:myfile
    [file]: delete mycontainer2:myfile

    * check history entries *
    [file]: exit
    [kamaki]: history
    [history]: show
    1.  file
    2.  file copy mycontainer1:somefile mycontainer1:myfile
    3.  file download mycontainer1:myfile mylocalfile
    4.  file upload mylocalfile mycontainer2:myfile -f
    5.  file delete mycontainer1:myfile
    6.  file delete mycontainer2:myfile
    7.  history
    8.  history show

    *repeat the process *
    [history]: run 2-4
    <file copy mycontainer1:somefile mycontainer1:myfile>
    <file download mycontainer1:myfile mylocalfile>
    Download completed
    <file upload mylocalfile mycontainer2:myfile>
    Upload completed

For powerfull scripting, users are advised to take advantage of their os shell
scripting capabilities and combine them with kamaki one-command. Still, the
history-run functionality might prove handy in many occasions.

OS Shell integration
^^^^^^^^^^^^^^^^^^^^

Kamaki shell features the ability to execute OS-shell commands from any
context. This can be achieved by typing *!* or *shell*::

    [kamaki_context]: !<OS shell command>
    ... OS shell command output ...

    [kamaki_context]: shell <OS shell command>
    ... OS shell command output ...

.. code-block:: console
    :emphasize-lines: 1

    Example 4.7.1: Run unix-style shell commands from kamaki shell


    [kamaki]: !ls -al
    total 16
    drwxrwxr-x 2 username username 4096 Nov 27 16:47 .
    drwxrwxr-x 7 username username 4096 Nov 27 16:47 ..
    -rw-rw-r-- 1 username username 8063 Jun 28 14:48 kamaki-logo.png

    [kamaki]: shell cp kamaki-logo.png logo-copy.png

    [kamaki]: shell ls -al
    total 24
    drwxrwxr-x 2 username username 4096 Nov 27 16:47 .
    drwxrwxr-x 7 username username 4096 Nov 27 16:47 ..
    -rw-rw-r-- 1 username username 8063 Jun 28 14:48 kamaki-logo.png
    -rw-rw-r-- 1 username username 8063 Jun 28 14:48 logo-copy.png


Kamaki shell commits command strings to the outside shell and prints the
results, without interacting with it. After a command is finished, kamaki shell
returns to its initial state, which involves the current directory, as shown in
example 4.8.2

.. code-block:: console
    :emphasize-lines: 1

    Example 4.8.2: Attempt (and fail) to change working directory


    [kamaki]: !pwd
    /home/username

    [kamaki]: !cd ..

    [kamaki]: shell pwd
    /home/username
