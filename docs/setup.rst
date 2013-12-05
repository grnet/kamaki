Setup
=====

Kamaki is easy to install from the official repository or with the pypi mechanism.

Quick Setup
-----------

.. warning:: Users of kamaki 0.8.X or older should consult the
    `migration guide <#migrating-from-kamaki-0-8-x-to-0-9-or-better>`_ first.

To set up Kamaki for a specific Synnefo deployment, users need an
**authentication URL** and a **user token**. Users should also pick an alias to
name the cloud configuration. This can be any single word, e.g., "default",
"mycloud" or whatever suits the user.

.. code-block:: console

    $ kamaki config set cloud.<cloud alias>.url <cloud-authentication-URL>
    $ kamaki config set cloud.<cloud alias>.token myt0k3n==

If only one cloud is configured, it is automatically considered the default.
Otherwise, a default cloud should be specified:

.. code-block:: console

    $ kamaki config set default_cloud <cloud alias>

The endpoints (URLs) for each service are resolved automatically from a single
URL. This mechanism works for Synnefo v0.14 deployments or later. The
authentication URL is retrieved from the Synnefo Web UI and should be set as
the cloud URL for kamaki. Users of Synnefo clouds >=0.14 are advised against
using any service-specific URLs.

Migrating configuration file to latest version
----------------------------------------------

Each new version of kamaki might demand some changes to the configuration file.
Kamaki features a mechanism of automatic migration of the configration file to
the latest version, which involves heuristics for guessing and translating the
file.

Quick migration
^^^^^^^^^^^^^^^

The easiest way is to backup and remove the configuration file. The default
configuration file location is '${HOME}/.kamakirc'.

To reset kamaki, a user needs the authentication URL and TOKEN:

.. code-block:: console

    $ kamaki config set cloud.default.url URL
    $ kamaki config set cloud.default.token TOKEN

After that, a new configuration file will be created. In most cases, this is
enough, since kamaki automatically sets the correct options for every
functionality.

Automatic migration
^^^^^^^^^^^^^^^^^^^

Another way is to let kamaki change the file automatically. Kamaki always
inspects the configuration file and, if understood as an older version, it
suggests some necessary modifications (user permission is required).

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
match the latest configuration file version specifications.

Lets take a look at the discarded options:

* `global.account` and `user.account` are not used since version 0.9
    The same is true for the synonyms `store.account` and `pithos.account`.
    These options were used to explicitly set a user account or uuid to a
    pithos call. In the latest Synnefo version (>= 0.14), these features are
    meaningless and therefore omitted.

* `global.data_log` option has never been a valid kamaki config option.
    In this scenario, the user wanted to set the `log_data` option, but he or
    she typed `data_log` instead. To fix this, the user should manually set the
    correct option after the conversion is complete (Example 2.2).

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

Multiple clouds
---------------

The following refers to users of multiple Synnefo and/or Open Stack
deployments. In the following, a Synnefo (or Open Stack) cloud deployment will
be called **a cloud**.

Multiple clouds can be configured and manager in a single  kamaki setup, since
version 0.9. Each cloud corresponds to a Synnefo (or Open Stack) cloud
deployment, with each deployment offering a single point of authentication (an
**authentication URL** and **token** pair). Users can retrieve this information
through the cloud UI.

Once a user has retrieved one URL/token pair per cloud, it is time to assign a
name to each cloud and configure kamaki accordingly.

For example, let the user have access to two clouds with the following authentication information ::

    cloud alias: devel
    authentication URL: https://devel.example.com/astakos/identity/v2.0/
    authentication token: myd3v3170k3n==

    cloud alias: testing
    autentication URL: https://testing.example.com/astakos/identity/v2.0/
    authentication token: my73571ng70k3n==

.. note:: the cloud alias is arbitrary and decided by the user. It is just a
    reference label for the cloud setup in the kamaki context.

The user should let kamaki know about these setups:

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
     cloud.default.url = https://example.com/astakos.identity/v2.0/
     cloud.default.token = myd3f4u1770k3n==
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
the **- - cloud** option is omitted, kamaki will query the `default` cloud.

One way to test this, is the `user info` command:

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
    $ kamaki --cloud=default user info
     ...
    id         :  4d3f4u17-u53r-4u7h-451n-4u7h3n7ic473
    name       :  Default User
    $
    $ kamaki user info
     ...
    id         :  4d3f4u17-u53r-4u7h-451n-4u7h3n7ic473
    name       :  Default User
    $

In interactive cell, the cloud option should be passed when calling the shell.

.. code-block:: console

    $ kamaki-shell --cloud=devel
    kamaki v0.10 - Interactive Shell

    /exit       terminate kamaki
    exit or ^D  exit context
    ? or help   available commands
    ?command    help on command
    !<command>  execute OS shell command

    Session user is Devel User
    (uuid: 725d5de4-1bab-45ac-9e98-38a60a8c543c)
    [kamaki]: 


Optional features
-----------------

For installing any or all of the following, consult the
`kamaki installation guide <installation.html#install-ansicolors>`_

* ansicolors
    * Add colors to command line / console output
    * Can be switched on/off in kamaki configuration file: `colors = on/off`
    * Has not been tested on non unix / linux based platforms

* mock
    * For kamaki contributors only
    * Allow unit tests to run on kamaki.clients package
    * Needs mock version 1.X or better

Any of the above features can be installed at any time before or after kamaki
installation.

Configuration options
---------------------

There are two kinds of configuration options:

* kamaki-related (global)
    interface settings and constants of the kamaki internal mechanism, e.g.,
    terminal colors, maximum threads per connection, custom logging, history
    file path, etc.

* cloud-related
    information needed to connect and use one or more clouds. There are some
    mandatory options (URL, token) and some advanced / optional (e.g.,
    service-specific URL overrides or versions)

Kamaki comes with preset default values to all kamaki-related configuration
options. Cloud-related information is not included in presets and should be
provided by the user. Kamaki-related options can also be modified.

There are two ways of managing configuration options: edit the config file or
use the kamaki config command.

Using multiple configuration files
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Kamaki setups are stored in configuration files. By default, a Kamaki
installation stores options in *.kamakirc* file located at the user home
directory.

If a user needs to switch between different kamaki-related setups, Kamaki can
explicitly load configuration files with the **- - config** (or **- c**) option

.. code-block:: console

    $ kamaki --config <custom_config_file_path> [other options]

.. note:: For accessing multiple clouds, users do NOT need to create multiple
    configuration files. Instead, we suggest using a single configuration file
    with multiple cloud setups. More details can be found at the
    `multiple clouds guide <#multiple-clouds>`_.

Modifying options at runtime
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

All kamaki commands can be used with the -o option in order to override configuration options at runtime. For example:

.. code-block:: console

    $ kamaki file list -o global.pithos_container=anothercontainer

will invoke *kamaki file list* with the specified options, but the initial
global.pithos_container values will not be modified.


Editing options
^^^^^^^^^^^^^^^

Kamaki config command allows users to see and manage all configuration options.

* kamaki config list
    lists all configuration options

* kamaki config get <group>[.option] | <option>
    show the value of a configuration option.A single *option* is equivalent to
    *global.option*, except if this group exist (*global*, *cloud*)

* kamaki config set <group.option> <value>
    set the group.option to value. If no group is given, it defaults to
    *global*.

* kamaki config delete <group>[.option] | <option>
    delete a configuration option, group, or global option.

The above commands cause option values to be permanently stored in the Kamaki configuration file.

The commands above can also be used for **clouds** handling, using the `cloud.`
prefix. The cloud handling cases are similar but with slightly different
semantics:

* kamaki config get cloud[.<cloud alias>[.option]]
    * cloud
        list all clouds and their settings
    * cloud.<cloud alias>
        list settings of the cloud aliased as <cloud alias>. If no
        special is configured, use the term `cloud.default`
    * cloud.<cloud alias>.<option>
        show the value of the specified option. If no special alias is
        configured, use `cloud.default.<option>`

* kamaki config set cloud.<cloud alias>.<option> <value>
    If the cloud alias <cloud alias> does not exist, create it. Then, create
    (or update) the option <option> of this cloud, by setting its value
    to <value>.

* kamaki config delete cloud.<cloud alias>[.<option>]
    * cloud.<cloud alias>
        delete the cloud alias <cloud alias> and all its options
    * cloud.<cloud alias>.<option>
        delete the <option> and its value from the cloud cloud aliased as
        <cloud alias>

To see if a default cloud is configured, get the default_cloud value

    .. code-block:: console

        $ kamaki config get default_cloud

If no default_cloud value is set, the first cloud alias is picked as default.
To pick a cloud alias as default:

    .. code-block:: console

        $ kamaki config set default_cloud <cloud alias>


Editing the configuration file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The configuration file is a simple text file that can be created by the user.

.. note:: users of kamaki < 0.9 can use the latest versions to automatically
    convert their old configuration files to the new configuration file(s). See
    `these instructions <#mMigrating-configuration-file-to-latest-version>`_
    for more.

A simple way to create the configuration file is to set a configuration option
using the kamaki config command. For example:

.. code-block:: console

    $ kamaki config set log_file /home/exampleuser/logs/kamaki.log

In the above example, if the kamaki configuration file does not exist, it will
be created with all the default values plus the *global.log_file* option set to
`/home/exampleuser/logs/kamaki.log`

The configuration file is formatted so that it can be parsed by the python ConfigParser module. It consists of command sections that are denoted with brackets. Every section contains variables with values. For example::

    [global]
    log_file = /home/exampleuser/logs/kamaki.log
    max_threads = 7
    colors = off

    [cloud "default"]
    url =
    token =

In this scenario, a bunch of configuration options are created and set to their
default options, except the log_file option which is set to whatever the
specified value.

The *[cloud "default"]* section is special and is used to configure the default
cloud. Kamaki will not be able to do anything useful without proper url and
token values set in the cloud section.

Available options
^^^^^^^^^^^^^^^^^

The [*global*] group is treated by kamaki as a generic group for kamaki
settings, namely command cli specifications, the thread limit, console colors,
history and log files, log detail options and pithos-specific options.

* global.default_cloud <cloud name>
    pick a cloud configuration as default. It must refer to an existing cloud.

* global.colors <on|off>
    enable / disable colors in command line based uis. Requires ansicolors,
    otherwise it is ignored

* global.log_file <logfile full path>
    set a custom location for kamaki logging. Default value is ~/.kamaki.log

* global.log_token <on|off>
    allow kamaki to log user tokens

* global.log_data <on|off>
    allow kamaki to log http data (by default, it logs only method, URL and
    headers)

* global.log_pid <on|off>
    attach the process name and id that produces each log line. Useful for
    resolving race condition problems.

* global.file_cli <UI command specifications for file>
    a special package that is used to load storage commands to kamaki UIs.
    Don't touch this unless if you know what you are doing.

* global.cyclades_cli <UI command specifications for cyclades>
    a special package that is used to load cyclades commands to kamaki UIs.
    Don't touch this unless you know what you are doing.

* global.flavor_cli <UI command specifications for VM flavors>
    a special package that is used to load cyclades VM flavor commands to
    kamaki UIs. Don't touch this unless you know what you are doing.

* global.network_cli <UI command specifications for virtual networks>
    a special package that is used to load cyclades virtual network commands.
    Don't touch this unless you know what you are doing.

* global.ip_cli <UI command specifications for floating IPs>
    a special package that is used to load cyclades floating IP commands. Don't
    touch this unless you know what you are doing.

* global.image_cli <UI command specs for Plankton or Compute image service>
    a special package that is used to load image-related commands to kamaki UIs.
    Don't touch this unless you know what you are doing.

* global.user_cli <UI command specs for Astakos authentication service>
    a special package that is used to load astakos-related commands to kamaki
    UIs. Don't touch this unless you know what you are doing.

* global.history_file <history file path>
    the path of a simple file for inter-session kamaki history. Make sure
    kamaki is executed in a context where this file is accessible for reading
    and writing. Kamaki automatically creates the file if it doesn't exist

Additional features
^^^^^^^^^^^^^^^^^^^

Functional tests
""""""""""""""""

Kamaki contains a set of functional tests for *kamaki.clients*, called
"livetest". The term "live" means that the tests are performed against an
on-line functional cloud deployment. The package is accessible as
*kamaki.clients.livetest* .

The livetest commands can be activated by setting the following option in the
configuration file::

    [global]
    livetest_cli=livetest

or with this kamaki command::

    $ kamaki config set livetest_cli livetest

In most cases, it is enough to have the default cloud configured correctly.
Some commands, though, require some extra settings specific to actual contents
of the cloud or the example files used in kamaki.

Here is a list of settings needed:

* for all tests::
    * livetest.testcloud = <the cloud alias this test will run against>

* for astakos client::
    * livetest.astakos_details = <A file with an authentication output>
        To create this file, pipeline the output of an authentication command
        with the -j option for raw json output

        .. code-block:: console

            $ kamaki user authenticate -j > astakos.details

    * livetest.astakos_name = <The exact "real" name of the testing user>
    * livetest.astakos_id = <The valid unique user id of the testing user>

* for image client:
    * livetest.image_details = <A file with the image metadata>
        To create this file, pipeline the output of an image metadata command
        with the -j option for raw json output

        .. code-block:: console

            $ kamaki image info <img id> -j > img.details

    * livetest.image_id = <A valid image id used for testing>
    * livetest.image_local_path = <The local path of the testing image>

* for flavors (part of the compute client):
    * livetest.flavor_details = <A file with the flavor details>
        To create this file, pipeline the output of a flavor info command
        with the -j option for raw json output

        .. code-block:: console

            $ kamaki flavor info <flavor id> -j > flavor.details


After setup, kamaki can run all tests::

    $ kamaki livetest all

a specific test (e.g., pithos scenario)::

    $ kamaki livetest pithos

or a specific method from a service (e.g., create_server @ cyclades)::

    $ kamaki livetest cyclades create_server


Unit tests
""""""""""

Kamaki features a set of unit tests for the kamaki.clients package. This set is
not used when kamaki is running. Instead, it is aimed to developers who debug
or extent kamaki. For more information, check the
`Going Agile <developers/extending-clients-api.html#going-agile>`_ entry at the
`developers section <developers/extending-clients-api.html>`_.
