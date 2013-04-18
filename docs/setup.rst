Setup
=====

Kamaki is easy to install from source or as a package. Some ui features are optional and can be install separately. Kamaki behavior can be configured in the kamaki config file.

Quick Setup
-----------

Kamaki interfaces rely on a list of configuration options. Be default, they are configured to communicate with the `Okeanos IaaS <http://okeanos.grnet.gr>`_.

.. note:: It is essential for users to get a configuration token (okeanos.grnet.gr users go `here <https://accounts.okeanos.grnet.gr/im/>`_) and provide it to kamaki:


.. code-block:: console
    :emphasize-lines: 1

    Example 1.1: Set user token to myt0k3n==

    $ kamaki config set token myt0k3n==

Optional features
-----------------

For installing any or all of the following, consult the `kamaki installation guide <installation.html#install-ansicolors>`_

* ansicolors
    * Make command line / console user interface responses prettier with text formating (colors, bold, etc.)
    * Can be switched on/off in kamaki configuration file: colors=on/off
    * Has not been tested on non unix / linux based platforms

* mock 
    * For kamaki contributors only
    * Allow unittests to run on kamaki.clients package
    * Needs mock version 1.X or better

Any of the above features can be installed at any time before or after kamaki installation.

Configuration options
---------------------

Kamaki comes with preset default values to all configuration options. All vital configuration options are set to use the okeanos.grnet.gr cloud services. User information is not included and should be provided either through the kamaki config command or by editing the configuration file.

Kamaki configuration options are vital for correct Kamaki behavior. An incorrect option may render some command groups dysfunctional. There are two ways of managing configuration options: edit the config file or use the kamaki config command.

Using multiple setups
^^^^^^^^^^^^^^^^^^^^^

Kamaki setups are stored in configuration files. By default, a Kamaki installation stores options in *.kamakirc* file located at the user home directory.

If a user needs to switch between different setups, Kamaki can explicitly load configuration files with the --config option:

.. code-block:: console

    $ kamaki --config <custom_config_file_path> [other options]

Using many different configuration files for different cloud services is encouraged.

Modifying options at runtime
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

All kamaki commands can be used with the -o option in order to override configuration options at runtime. For example::

.. code-block:: console

    $ kamaki file list -o global.account=anotheraccount -o global.token=aT0k3n==

will invoke *kamaki file list* with the specified options, but the initial global.account and global.token values will be restored to initial values afterwards.

.. note:: on-the-fly calls to file require users to explicetely provide the account uuid corresponding to this token. The account is actually the uuid field at the response of the following call::

    $kamaki user authenticate aT0k3n==

Editing options
^^^^^^^^^^^^^^^

Kamaki config command allows users to see and manage all configuration options.

* kamaki config list
    lists all configuration options currently used by a Kamaki installation

* kamaki config get <group.option>
    show the value of a specific configuration option. Options must be of the form group.option

* kamaki config set <group.option> <value>
    set the group.option to value

* kamaki config delete <group.option>
    delete a configuration option

The above commands cause option values to be permanently stored in the Kamaki configuration file.

Editing the configuration file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The configuration file is a simple text file that can be created by the user.

A simple way to create the configuration file is to set a configuration option using the kamaki config command. For example:

.. code-block:: console

    $ kamaki config set token myT0k3N==

In the above example, if the kamaki configuration file does not exist, it will be created with all the default values plus the *global.token* option set to *myT0k3n==* value.

The configuration file is formatted so that it can be parsed by the python ConfigParser module. It consists of command sections that are denoted with brackets. Every section contains variables with values. For example::

    [file]
    url=https://okeanos.grnet.gr/pithos
    token=my0th3rT0k3n==

two configuration options are created: *file.url* and *file.token*. These values will be loaded at every future kamaki execution.

Available options
^^^^^^^^^^^^^^^^^

The [global] group is treated by kamaki as a generic group for arbitrary options, and it is used as a super-group for vital Kamaki options, namely token, url, cli. In case of conflict, the most specific options overrides the global ones.

* global.colors <on|off>
    enable / disable colors in command line based uis. Requires ansicolors, otherwise it is ignored

* global.token <user authentication token>

* global.log_file <logfile full path>
    set a custom location for kamaki logging. Default value is ~/.kamaki.log

* global.log_token <on|off>
    allow kamaki to log user tokens

* global.log_data <on|off>
    allow kamaki to log http data (by default, it logs only method, URL and headers)

* file.cli <UI command specifications for file>
    a special package that is used to load storage commands to kamaki UIs. Don't touch this unless if you know what you are doing.

* file.url <OOS storage or Pithos+ service url>
    the url of the OOS storage or Pithos+ service. Set to Okeanos.grnet.gr Pithos+ storage service by default. Users should set a different value if they need to use a different storage service.

* file.token <token>
    it set, it overrides possible global.token option for file level commands

* compute.url <OOS compute or Cyclades service url>
    the url of the OOS compute or Cyclades service. Set to Okeanos.grnet.gr Cyclades IaaS service by default. Users should set a different value if they need to use a different IaaS service.

* cyclades.cli <UI command specifications for cyclades>
    a special package that is used to load cyclades commands to kamaki UIs. Don't touch this unless you know what you are doing.

* flavor.cli <UI command specifications for VM flavors>
    a special package that is used to load cyclades VM flavor commands to kamaki UIs. Don't touch this unless you know what you are doing.

* network.cli <UI command specifications for virtual networks>
    a special package that is used to load cyclades virtual network commands to kamaki UIs. Don't touch this unless you know what you are doing.

* image.url <Plankton image service url>
    the url of the Plankton service. Set to Okeanos.grnet.gr Plankton service by default. Users should set a different value if they need to use a different service. Note that the *image compute* commands are depended on the compute.url instead.

* image.cli <UI command specifications for Plankton (and Compute) image service>
    a special package that is used to load image-related commands to kamaki UIs. Don't touch this unless you know what you are doing.

* user.url <Astakos authentication service url>
    the url of the Astakos authentication service. Set to the Okeanos.grnet.gr Astakos service by default. Users should set a different value if they need to use a different service.

* user.cli <UI command specifications for Astakos authentication service>
    a special package that is used to load astakos-related commands to kamaki UIs. Don't touch this unless you know what you are doing.

* history.file <history file path>
    the path of a simple file for inter-session kamaki history. Make sure kamaki is executed in a context where this file is accessible for reading and writing. Kamaki automatically creates the file if it doesn't exist

Additional features
^^^^^^^^^^^^^^^^^^^

Log file location
"""""""""""""""""

Kamaki log file path is set by the following command::

    $ kamaki config set log_file <logfile path>

By default, kamaki logs at ~/.kamaki.log

When initialized, kamaki attempts to open one of these locations for writing, in the order presented above and uses the first accessible for appending logs. If the log_file option is set, kamaki prepends the value of this option to the logfile list, so the custom location will be the first one kamaki will attetmpt to log at.

Kamaki will not crush if the logging location is not accessible.

Richer connection logs
""""""""""""""""""""""

Kamaki logs down the http requests and responses in /var/log/kamaki/clients.log (make sure it is accessible). The request and response data and user authentication information is excluded from the logs be default. The former may render the logs unreadable and the later are sensitive information. Users my activate data and / or token logging my setting the global options log_data and log_token respectively::

    $ kamaki config set log_data on
    $ kamaki config set log_token on

Either or both of these options may be switched off either by setting them to ``off`` or by deleting them.

    $ kamaki config set log_data off
    $ kamaki config delete log_token

Set custom thread limit
"""""""""""""""""""""""

Some operations (e.g. download and upload) may use threaded http connections for better performance. Kamaki.clients utilizes a sophisticated mechanism for dynamically adjusting the number of simultaneous threads running, but users may wish to enforce their own upper thread limit. In that case, the max_threads option may be set to the configuration file::

    $ kamaki config set max_threads 3

If the value is not a positive integer, kamaki will ignore it and a warning message will be logged.

The livetest suite
""""""""""""""""""

Kamaki contains a live test suite for the kamaki.clients API, where "live" means that the tests are performed against active services that up and running. The live test package is named "livetest", it is accessible as kamaki.clients.livetest and it is designed to check the actual relation between kamaki and synnefo services.

The livetest suite can be activated with the following option on the configuration file::

    [livetest]
    cli=livetest

In most tests, livetest will run as long as an Astakos identity manager service is accessible and kamaki is set up to authenticate a valid token on this server.

In specific, a setup file needs at least the following mandatory settings in the configuration file:

* If authentication information is used for default kamaki clients::

    [user]
    url=<Astakos Identity Manager URL>
    token=<A valid user token>

* else if this authentication information is only for testing add this under [livetest]::

    user_url=<Astakos Identity Manager URL>
    user_token=<A valid user token>

Each service tested in livetest might need some more options under the [livetest] label, as shown bellow:

* kamaki livetest astakos::

    astakos_email = <The valid email of testing user>
    astakos_name = <The exact "real" name of testing user>
    astakos_username = <The username of the testing user>
    astakos_uuid = <The valid unique user id of the testing user>

* kamaki livetest pithos::

    astakos_uuid = <The valid unique user id of the testing user>

* kamaki livetest cyclades / image::

    image_id = <A valid image id used for testing>
    image_local_path = <The local path of the testing image>
    image_details = <A text file containing testing image details in a python dict>

    - example image.details content:
    {
        u'id': u'b3e68235-3abd-4d60-adfe-1379a4f8d3fe',
        u'metadata': {
            u'values': {
                u'description': u'Debian 6.0.6 (Squeeze) Base System',
                u'gui': u'No GUI',
                u'kernel': u'2.6.32',
                u'os': u'debian',
                u'osfamily': u'linux',
                u'root_partition': u'1',
                u'sortorder': u'1',
                u'users': u'root'
            }
        },
        u'name': u'Debian Base',
        u'progress': u'100',
        u'status': u'ACTIVE',
        u'created': u'2012-11-19T14:54:57+00:00',
        u'updated': u'2012-11-19T15:29:51+00:00'
    }

    flavor_details = <A text file containing the testing images' flavor details in a python dict>

    - example flavor.details content:
    {
        u'name': u'C1R1drbd',
        u'ram': 1024,
        u'id': 1,
        u'SNF:disk_template': u'drbd',
        u'disk': 20,
        u'cpu': 1
    }

After setup, kamaki can run all tests::

    $ kamaki livetest all

a specific test (e.g. astakos)::

    $ kamaki livetest astakos

or a specific method from a service (e.g. astakos authenticate)::

    $ kamaki livetest astakos authenticate

The unit testing system
"""""""""""""""""""""""

Kamaki container a set of finegrained unit tests for the kamaki.clients package. This set is not used when kamaki is running. Instead, it is aimed to developers who debug or extent the kamaki clients library. For more information, check the `Going Agile <developers/extending-clients-api.html#going-agile>`_ entry at the `developers section <developers/extending-clients-api.html>`_.
