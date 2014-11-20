Setup
=====

The term "setup" refers to the configuration of kamaki after the
`installation <installation.html>`_.

Quick Setup
-----------

.. warning:: Users of kamaki 0.8.X or older should consult the
    `migration guide <#migrating-from-kamaki-0-8-x-to-0-9-or-better>`_ first.

To set up Kamaki for a specific Synnefo deployment (*cloud*), users need an
**authentication URL** and a **user token**. Users should also pick an alias to
name the cloud configuration. This can be any arbitrary word, e.g., "default",
"mycloud" or whatever suits the user.

.. code-block:: console

    $ kamaki config set cloud.CLOUD_NAME.url AUTHENTICATION_URL
    $ kamaki config set cloud.CLOUD_NAME.token TOKEN

If only one cloud is configured, it is automatically considered the default.
Otherwise, a default cloud should be specified:

.. code-block:: console

    $ kamaki config set default_cloud CLOUD_NAME

The endpoints (URLs) for each service are resolved automatically from this
single authentication URL (Synnefo clouds v0.14 or later).

.. _ssl-setup:

SSL Authentication
------------------

HTTPS connections are authenticated with SSL since version 0.13, as long as a
file of CA Certificates is provided. The file can be set with the
`ca_certs configuration option <#available-options>`_ or with the *- -ca-certs*
runtime argument. Packages for various operating systems are built with a
default value for the 'ca_certs' configuration option, which is specific for
each platform.

If the CA Certificates are not provided or fail to authenticate a particular
cloud, ``kamaki`` will exit with an SSL error and instructions.

Users have the option to ignore SSL authentication errors with the
`ignore_ssl configuration option <#available-options>`_ or the *- -ignore-ssl*
runtime argument and connect to the cloud insecurely.

To check the SSL settings on an installation:

.. code-block:: console

    $ kamaki config get ca_certs
    $ kamaki config get ignore_ssl

To set a CA certificates path:

.. code-block:: console

    $ kamaki config set ca_certs CA_FILE

To connect to clouds even when SSL authentication fails:

.. code-block:: console

    $ kamaki config set ignore_ssl on

Migrating configuration file to latest version
----------------------------------------------

Each new version of kamaki might demand some changes to the configuration file.
Kamaki features a mechanism of automatic migration of the configuration file to
the latest version, which involves heuristics for guessing and translating the
file.

Configuration options
---------------------

There are two kinds of configuration options:

* kamaki-related (global)
    interface settings and constants that affect kamaki as an application e.g.,
    terminal colors, maximum threads per connection, logging options, default
    behavior, etc.

* cloud-related
    access settings for one or more clouds. The (authentication) URL and token
    settings are mandatory. There are also a few optional settings for
    overriding some service-specific operations (e.g., endpoint URLs).

All kamaki-related options default to a set of values. Cloud-related
information does not default to anything and should be provided by the user.

Options can be set with the `kamaki config` command (suggested) or by editing
the configuration file.

Global options
^^^^^^^^^^^^^^

* global.default_cloud CLOUD_NAME
    The name of the default cloud to be used. See cloud settings bellow.

* global.colors < on | **off** >
    enable / disable colors in command line based uis. Requires the ansicolors
    optional package, otherwise it is ignored

* global.log_file < path (default: $HOME/.kamaki.log) >
    The kamaki log file location

* global.log_token < on | **off** >
    allow kamaki to log user tokens

* global.log_data < on | **off** >
    allow kamaki to log http data (body)

* global.log_pid < on | **off** >
    attach the process name and id that produces each log line. Useful for
    resolving race condition problems.

* global.history_file < path (default: $HOME/.kamaki.history) >
    the path of a simple file for inter-session kamaki history. Make sure
    kamaki is executed in a context where this file is accessible for reading
    and writing. Kamaki automatically creates the file if it doesn't exist

* global.history_limit POSSITIVE_INTEGER (default: 0 (unlimited))
    the maximum number of lines stored in history. If there is a finite limit,
    old lines will be deleted automatically.

* global.<command group>_cli <command definition package>
    options that help kamaki locate the command definitions for each command
    group. Some command groups are defined automatically (can be overridden),
    others are optional and are not set by default.

    The following command groups are defined automatically::

        user, quota, resource, project, membership, file, container, sharer,
        group, server, flavor, network, subnet, port, ip, volume, sdnapshot,
        image, imagecompute, config, history

    The following command groups are optional::

        service, endpoint, commission

    For example, the "endpoint" commands are defined in the "astakos" package,
    but are not enabled by default. To enable them:

    .. code-block:: console

        $ kamaki config set endpoint_cli astakos


Using multiple configuration files
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Kamaki allows users to pick the configuration file at runtime with the
**- - config** (or **- c**) option

.. code-block:: console

    $ kamaki --config CONFIGUDATION_FILE [...]

.. note:: Multiple clouds can be configured in the same file (suggested). More
    details can be found at the `multiple clouds guide <#multiple-clouds>`_.

Modifying options at runtime
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

All kamaki commands can be used with the -o option in order to override
configuration options at runtime. For example:

.. code-block:: console

    $ kamaki file list -o global.pithos_container=anothercontainer

will invoke *kamaki file list* with the specified options, but the initial
global.pithos_container values will not be modified.

Editing options
^^^^^^^^^^^^^^^

Use the `kamaki config` commands to control the configuration settings.

* kamaki config list
    lists all configuration options

* kamaki config get GROUP
    list the options in a group
* kamaki config get [GROUP.]OPTION
    show the value of an option. GROUP defaults to "global".

* kamaki config set [GROUP.]OPTION VALUE
    set an OPTION to VALUE. GROUP defaults to "global".

* kamaki config delete GROUP
    delete a whole group of settings

* kamaki config delete [GROUP.]OPTION
    delete a configuration option. GROUP defaults to "global".

.. note:: The terms "global" and "cloud" are always group names.

The above commands cause option values to be permanently stored in the Kamaki
configuration file. They can also be used for **cloud** handling, with the
`cloud.` prefix.

* kamaki config get cloud
    list all clouds and their settings

* kamaki config get cloud.CLOUD_NAME
    list settings of the cloud with CLOUD_NAME. If no
    special is configured, use the term `cloud.default`

* kamaki config get cloud.CLOUD_NAME.OPTION
    show the value of an option option

* kamaki config set cloud.CLOUD_NAME.OPTION VALUE
    Set the value of CLOUD_NAME.OPTION to VALUE

* kamaki config delete cloud.CLOUD_NAME
    delete the cloud with CLOUD_NAME and all its options

* kamaki config delete cloud.CLOUD_NAME.OPTION
    delete the OPTION and its value from the cloud with CLOUD_NAME

The [global.]default_cloud option is optional, but very useful if there are
more than one clouds configured:

    .. code-block:: console

        $ kamaki config get default_cloud
        $ kamaki config set default_cloud CLOUD_NAME

Configuration file
^^^^^^^^^^^^^^^^^^

The configuration file is a simple text file. Its default location is at
$HOME/.kamakirc

To create the configuration file, `setup a cloud <#quick-setup>`_ and the file
will be updated or created at the default location.

The configuration file format is dictated by the python ConfigParser module
with some extentions for handling clouds. An example::

    [global]
    log_file = /home/exampleuser/logs/kamaki.log
    max_threads = 7
    colors = off

    [cloud "default"]
    url = https:://www.example.org/authentication
    token = s0m370k3n

.. note:: Most options do not appear in the file, except to be overridden.

Additional features
^^^^^^^^^^^^^^^^^^^

For installing any or all of the following, consult the
`kamaki installation guide <installation.html>`_

* ansicolors
    * Add colors to command line / console output
    * Can be switched with global.colors
    * Has not been tested on non unix / linux based platforms

* mock
    * For kamaki contributors only
    * Allow unit tests to run on kamaki.clients package
    * Needs mock version 1.X or better

Any of the above features can be installed at any time before or after kamaki
installation.

Functional tests
""""""""""""""""

Kamaki does not include functional tests in its native code. The synnefo tool
snf-burnin can be used instead.

Unit tests
""""""""""

Kamaki features a set of unit tests for the kamaki.clients package. This set is
not used when kamaki is running. Instead, it is aimed to developers who debug
or extent kamaki. For more information, check the
`Going Agile <developers/extending-clients-api.html#going-agile>`_ entry at the
`developers section <developers/extending-clients-api.html>`_.


Multiple clouds
---------------

Kamaki can be used to "poke" different Synnefo (or other OpenStack-compatible)
deployments (clouds).

Multiple clouds can be configured and managed in a single  kamaki setup. Each
cloud is configured through a single point of authentication (an
**authentication URL** and **token** pair). Users can retrieve this information
through the cloud UI.

For example, let the user have access to two clouds with the following
authentication information ::

    cloud name: devel
    authentication URL: https://devel.example.com/astakos/identity/v2.0/
    authentication token: myd3v3170k3n==

    cloud name: testing
    autentication URL: https://testing.example.com/astakos/identity/v2.0/
    authentication token: my73571ng70k3n==

.. note:: the cloud names are arbitrary and decided by the user

Kamaki should be configured for these clouds:

.. code-block:: console

    $ kamaki config set cloud.devel.url https://devel.example.com/astakos/identity/v2.0/
    $ kamaki config set cloud.devel.token myd3v3170k3n==
    $
    $ kamaki config set cloud.testing.url https://testing.example.com/astakos/identity/v2.0/
    $ kamaki config set cloud.testing.token my73571ng70k3n==
    $

To check if all settings are loaded, a user may list all clouds, as shown
bellow:

.. code-block:: console

    $ kamaki config get cloud
     cloud.devel.url = https://devel.example.com/astakos/identity/v2.0/
     cloud.devel.token = myd3v3170k3n==
     cloud.testing.url = https://testing.example.com/astakos/identity/v2.0/
     cloud.testing.token = my73571ng70k3n==
    $

or query kamaki for a specific cloud:

.. code-block:: console

    $ kamaki config get cloud.devel
     cloud.devel.url = https://devel.example.com/astakos/identity/v2.0/
     cloud.devel.token = myd3v3170k3n==
    $

Now kamaki can use any of these clouds, with the **- - cloud** attribute. If
the **- - cloud** option is omitted, kamaki will query the default cloud, if
set:

.. code-block:: console

    $ kamaki --cloud=devel user info
     ...
    id         :  725d5de4-1bab-45ac-9e98-38a60a8c543c
    name       :  Devel User
    $
    $ kamaki --cloud=testing user info
     ...
    id         :  4ed5d527-bab1-ca54-89e9-c345c8a06a83
    name       :  Testing User
    $

If the default_cloud option is not set, kamaki will be confused. This happens
only if there are two or more clouds configured.

.. code-block:: console

    $ kamaki user info
    Found 2 clouds but none of them is set as default
    |  Please, choose one of the following cloud names:
    |  devel, testing 
    |  To see all cloud settings:
    |    kamaki config get cloud.CLOUD_NAME
    |  To set a default cloud:
    |    kamaki config set default_cloud CLOUD_NAME
    |  To pick a cloud for the current session, use --cloud:
    |    kamaki --cloud=CLOUD_NAME ...
    $

Pick a cloud as the default:

.. code-block:: console

    $ kamaki config set default_cloud devel

Test if the default cloud:

.. code-block:: console

    $ kamaki user info
     ...
    id         :  725d5de4-1bab-45ac-9e98-38a60a8c543c
    name       :  Devel User
    $

In interactive shell, the cloud option could be passed when invoking the shell

.. code-block:: console

    $ kamaki-shell --cloud=devel
    kamaki v0.13 - Interactive Shell

    /exit       terminate kamaki
    exit or ^D  exit context
    ? or help   available commands
    ?command    help on command
    !<command>  execute OS shell command

    Session user is Devel User (uuid: 725d5de4-1bab-45ac-9e98-38a60a8c543c)
    [kamaki]: 


Migrating configuration file to latest version
----------------------------------------------

The following is helpful to users who have an old configuration file or
experience other configuration-file related problems.

As kamaki has been evolving, the configuration file has evolved too. In version
0.9 and later in 0.12, the compatibility with older configuration files was
broken. To make thinks easier, kamaki can automatically adjust old
configuration files or it can create a new one if it is removed.

Quick migration
^^^^^^^^^^^^^^^

The easiest way is to backup and remove the configuration file. The default
configuration file location is '${HOME}/.kamakirc'.

Then, reset kamaki in order to create a new configuration file. To reset use
the authentication URL and TOKEN, as described in `Quick Setup <#quick-setup>`_

* global.ca_certs <CA Certificates>
    set the path of the file with the CA Certificates for SSL authentication

* global.ignore_ssl <on|off>
    ignore / don't ignore SSL errors

* global.colors <on|off>
    enable / disable colors in command line based uis. Requires ansicolors,
    otherwise it is ignored

Automatic migration
^^^^^^^^^^^^^^^^^^^

Another way is to let kamaki change the file automatically. Kamaki always
inspects the configuration file format to identify its version. In case of an
old file, kamaki suggests some necessary modifications.

On example 2.1 we suggest using the `user info` command to invoke the migration
mechanism.

.. code-block:: console
    :emphasize-lines: 1

    Example 2.1: Convert config file while authenticating user "exampleuser"

    $ kamaki user info
    Config file format version >= 0.12 is required
    Configuration file: "/home/exampleuser/.kamakirc"
    but kamaki can fix this:
    Calculating changes while preserving information
    ... rescue global.token => cloud.default.token
    ... rescue config.cli => global.config_cli
    ... rescue history.file => global.history_file
    ... change global.network_cli value: `cyclades` => `network`
    ... DONE
    The following information will NOT be preserved:
        global.account =
        global.data_log = on
        user.account = exampleuser@example.com
        user.url = https://accounts.okeanos.grnet.gr
        compute.url = https://cyclades.okeanos.grnet.gr/api/v1.1
        file.url = https://pithos.okeanos.grnet.gr/v1
        image.url = https://cyclades.okeanos.grnet.gr/plankton

    Kamaki is ready to convert the config file to version 0.12
    Overwrite file /home/exampleuser/.kamakirc ? [Y, y]

At this point, we should examine the kamaki output. Most options are renamed to
match the latest configuration specification while others are discarded.

Lets take a look at the discarded options:

* `global.account` and `user.account` are not used since version 0.9
    The same is true for the synonyms `store.account` and `pithos.account`.
    These options were used to explicitly set a user account or uuid to a
    pithos call. In the latest Synnefo versions (since 0.14), these features
    were rendered meaningless due to service improvements.

* `global.data_log` option has never been a valid kamaki config option.
    In this scenario, the user wanted to set the `log_data` option, but he or
    she mistyped `data_log` instead. To fix this, the user should manually set
    the correct option after the conversion is complete (Example 2.2).

Users should press *y* when they are ready, which will cause the default config
file to be modified.

.. code-block:: console
    :emphasize-lines: 1

    Example 2.2: Rescue misspelled log_data option

    $ kamaki config set log_data on

In order to convert more files, users may run kamaki with the -c option, which
runs kamaki with a different configuration file (Example 2.3) and apply the
steps described above.

.. code-block:: console
    :emphasize-lines: 1

    Example 2.3: Use kamaki to update a configuration file called ".myfilerc"

    $ kamaki -c .myfilerc user authenticate
