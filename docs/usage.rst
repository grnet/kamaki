Usage
=====

Kamaki features commands of the form::

  kamaki <object> <action> [identifier(s)] <non-positional arguments>
  e.g., 
  kamaki user info --username=user@example.com

A detailed list of the command specifications can be found in
`Commands <commands.html>`_ section.

All commands can run either from the host shell or through the kamaki
interactive shell:

.. code-block:: console

  #  Run from host shell
  $ kamaki user info
  ... RESULTS ...

  #  Run from kamaki interactive shell
  $ kamaki-shell
  [kamaki]: user info
  ... RESULTS ...

In the following, the term "one-command" refer to running kamaki commands from
host shell, while the term "shell" will refer to the interactive shell.

.. note:: This section refers to the kamaki CLI. Developers and people who write
  scripts, should rather use the the
  `Clients library <developers/code.html#the-clients-api>`_ instead.

Quick Setup
-----------

Kamaki interfaces rely on a list of configuration options. Check the
`Setup <setup.html>`_ guide for a full list.

As rule of the thump, it is enough to set a cloud authentication URL and TOKEN:

.. code-block:: console
    :emphasize-lines: 1

    Example 1.1: Set authentication URL, user token for cloud alias CLOUD_NAME

    $ kamaki config set cloud.CLOUD_NAME.url <authentication URL>
    $ kamaki config set cloud.CLOUD_NAME.token myt0k3n==

.. note:: The term CLOUD_NAME is arbitrary and can be chosen by the user

Shell vs one-command
--------------------

Kamaki users can access Synnefo services through either the kamaki shell or the
one-command interface. Both systems feature identical responses and error
messages, since they rely on the same internal command and library API
implementation. However, there are some minor differences.

In favor of interactive shell:

* shorter commands
* tab completion for commands (if supported by host shell)
* kamaki-specific history with ↑ or ↓ keys (if supported by host shell)

In favor of one-command:

* users take advantage of host shell features (pipelines, redirection, etc.)
* can be used in shell scripts

Run as shell
^^^^^^^^^^^^
To use kamaki as a shell, run:

.. code-block:: console
    :emphasize-lines: 1

    Example 2.2.1: Run kamaki shell

    $ kamaki-shell

* with any kind of '-' prefixed arguments, except '-h', '- - help', '-V',
    '- - version'.

.. code-block:: console
    :emphasize-lines: 1

    Example 2.2.2: Run kamaki shell with custom configuration file

    $ kamaki-shell -c myconfig.file

    Example 2.2.3: Run kamaki shell so as to use a specific cloud

    $ kamaki-shell --cloud=example_cloud

    Example 2.2.4: Run kamaki shell with verbosity (prints HTTP communication)

    $ kamaki-shell -v

.. note:: Valid arguments can be combined e.g., to run a shell with verbosity
    and a specific cloud::

    $ kamaki-shell -v --cloud=example_cloud

Run as one-command
^^^^^^^^^^^^^^^^^^
To use kamaki as an one-command tool, run:

* with the '-h' or '--help' arguments (help for kamaki one-command)

.. code-block:: console

    $kamaki -h

* with one or more command parameters (object and, maybe, action):

.. code-block:: console
    :emphasize-lines: 1

    Example 2.3.2: List virtual servers

    $ kamaki server list

One-command interface
---------------------

Using help
^^^^^^^^^^

Kamaki help provides information on commands (description, syntax).

To see the command groups (objects), use -h or --help (example 1.3.1). The
following examples demonstrate the help messages of kamaki, in the context of a
command group (server) and of a command in that group (list).

.. code-block:: console
    :emphasize-lines: 1

    Example 3.1.1: kamaki help shows available parameters and command groups


    $ kamaki -h
    usage: kamaki <cmd_group> [<cmd_subbroup> ...] <cmd>
        [-v] [-s] [-V] [-d] [-c CONFIG] [-o OPTIONS] [--cloud CLOUD] [-h]

    optional arguments:
      -v, --verbose         More info at response
      -s, --silent          Do not output anything
      -V, --version         Print current version
      -d, --debug           Include debug output
      -c CONFIG, --config CONFIG
                            Path to configuration file
      -o OPTIONS, --options OPTIONS
                            Override a config value
      --cloud CLOUD         Chose a cloud to connect to
      -h, --help            Show help message

    Options:
     - - - -
    resource: Astakos/Account API commands for resources
    group: Pithos+/Storage user groups
    network: Networking API network commands
    subnet: Networking API network commands
    ip: Networking API floatingip commands
    image: Cyclades/Plankton API image commands
    imagecompute: Cyclades/Compute API image commands
    quota: Astakos/Account API commands for quotas
    sharer: Pithos+/Storage sharers
    project: Astakos project API commands
    user: Astakos/Identity API commands
    file: Pithos+/Storage object level API commands
    container: Pithos+/Storage container level API commands
    flavor: Cyclades/Compute API flavor commands
    server: Cyclades/Compute API server commands
    config: Kamaki configurations
    port: Networking API network commands
    history: Kamaki command history
    kamaki-shell: An interactive command line shell

.. code-block:: console
    :emphasize-lines: 1,2

    Example 3.1.2: Cyclades help contains all first-level commands of Cyclades
    command group

    $ kamaki server -h
    usage: kamaki server <...> [-v] [-s] [-V] [-d] [-c CONFIG]
                               [-o OPTIONS] [--cloud CLOUD] [-h]

    optional arguments:
      -v, --verbose         More info at response
      -s, --silent          Do not output anything
      -V, --version         Print current version
      -d, --debug           Include debug output
      -c CONFIG, --config CONFIG
                            Path to configuration file
      -o OPTIONS, --options OPTIONS
                            Override a config value
      --cloud CLOUD         Chose a cloud to connect to
      -h, --help            Show help message

    Options:
     - - - -
    info: Detailed information on a Virtual Machine
    modify: Modify attributes of a virtual server
    create: Create a server (aka Virtual Machine)
    list: List virtual servers accessible by user
    reboot: Reboot a virtual server
    start: Start an existing virtual server
    shutdown: Shutdown an active virtual server
    delete: Delete a virtual server
    attachment: Details on a volume attachment
    attachments: List of all volume attachments for a server
    attach: Attach a volume on a server
    detach: Delete an attachment/detach a volume from a server

.. code-block:: console
    :emphasize-lines: 1,2

    Example 3.1.3: Help for command "server list" with syntax, description and
    available user options

    $ kamaki server list -h
    usage: kamaki server list [-v] [-s] [-V] [-d] [-c CONFIG] [-o OPTIONS]
                              [--cloud CLOUD] [-h] [--since SINCE] [--enumerate]
                              [-l] [--more] [-n LIMIT] [-j]

    List Virtual Machines accessible by user

    optional arguments:
      -v, --verbose         More info at response
      -s, --silent          Do not output anything
      -V, --version         Print current version
      -d, --debug           Include debug output
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

Kamaki command history is stored in '${HOME}/.kamaki.history' by default). To
set a custom history file path users must set the history.file config option
(more on config options `here <setup.html#editing-options>`_).

Every command is appended at the end of that file. In order to see how to use
history, use the kamaki help system:

.. code-block:: console
    :emphasize-lines: 1

    Example 3.2.1: Available history options

    $ kamaki history -h
    Options:
     - - - -
    clean:  Clean up history (permanent)
    show :  Show intersession command history


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
and http logs). Kamaki in debug mode cancels the suppression of warning
messages too.

To run kamaki in debug mode use the -d or --debug option.


Verbose
"""""""

Most kamaki commands are translated into http requests. Kamaki clients API
translates command semantics to REST and handles the response. Users who need
to have access to these commands can use the verbose mode that outputs the
HTTP Request and Response details along with the (possibly modified) regular
command output.

To run kamaki in verbose mode use the *-v/- - verbose* argument, it goes with
everything.

Verbose mode outputs the request and response mode, address and
headers as well as the size of the data block, if any. Sensitive information
(x-auth-token header and data body) are omitted by default,. Users who need
this information may enable it through the log_token and log_data configuration
options

.. tip:: Use the -o argument to include http data in the output:

    .. code-block:: console

        $ kamaki server list -v -o log_data=on


Logging
"""""""

Kamaki logs in a file specified by the *log_file* option which defaults to
*${HOME}/.kamaki.log*. This configuration option can be modified::

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

.. code-block:: console
    :emphasize-lines: 1

    Example 3.4.1: List the trash container contents, containing c1_
    
    $ kamaki file list -v -o log_token=on
    ...
    X-Auth-Token: s0m3-3x4mp1e-70k3n
    ...

The -o argument can be used to temporarily override various (set or unset)
options. In one command, all -o option sets are forgotten just after the
command has been completed, and the previous settings are restored (the
configuration file is not modified).

For security reasons, all commands hide the authentication token from outputs
and the logs. In example 3.4.1 the token is not hided, because of the
*log_token=on* config option.

.. warning:: Complimentary output i.e., http logs and informative messages are
  printed to standard error stream

Interactive shell
-----------------

Command Contexts
^^^^^^^^^^^^^^^^

The command namespaces in kamaki interactive shell are called **contexts**.

Each command group is also a context where the users can **enter** by typing
the group name. If the context switch is successful, the kamaki shell prompt
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
    ... (file listing) ...
    [file]: exit
    [kamaki]: server
    [server]: list
    ... (servers listing) ...
    [server]: exit
    [kamaki]:

Users can avoid switching between contexts: all commands can run from the
**top context** e.g., examples 4.1.3 and 4.1.4 are equivalent.

.. code-block:: console
    :emphasize-lines: 1

    Example 4.1.4: Execute different "list" commands from top context

    [kamaki]: config list
    ... (configuration options listing) ...
    [kamaki]: file list
    ... (file listing) ...
    [kamaki]: server list
    ... (servers listing) ...
    [kamaki]:

While in a context, other contexts are accessible by using a **/** as shown in
the following example:

.. code-block:: console

  Example 4.1.5: Execute different "list" commands from the config context

  [kamaki]: config
  [config]: list
  ... (configuration option listing) ...
  [config]: /file list
  ... (file listing) ...
  [config]: /server list
  ... (servers listing) ...
  [config]:

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
are the main functionality of kamaki, while the later are used to manage the
kamaki-shell.

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
