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

    $ kamaki set token myt0k3n==

To use the storage service, a user should also provide the corresponding user-name:

.. code-block:: console
    :emphasize-lines: 1

    Example 1.2: Set user name to user@domain.com

    $ kamaki set store.account user@domain.com

Optional features
-----------------

For installing any all of the following, consult the `kamaki installation guide <installation.html#install-progress-and-or-ansicolors-optional>`_

* ansicolors
    * Make command line / console user interface responses prettier with text formating (colors, bold, etc.)
    * Can be switched on/off in kamaki configuration file: colors=on/off

* progress 
    * Attach progress bars to various kamaki commands (e.g. kamaki store upload)
    * Since version 0.6.1 kamaki "requires" progress version 1.0.2 or better

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

    $ kamaki store list -o global.account=anotheraccount -o global.token=aT0k3n==

will invoke *kamaki store list* with the specified options, but the initial global.account and global.token values will be restored to initial values afterwards.

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

    $ kamaki config set account myusername@mydomain.com

In the above example, if the kamaki configuration file does not exist, it will be created with all the default values plus the *global.account* option set to *myusername@mydomain.com* value.

The configuration file is formatted so that it can be parsed by the python ConfigParser module. It consists of command sections that are denoted with brackets. Every section contains variables with values. For example::

    [store]
    url=https://okeanos.grnet.gr/pithos
    account=myaccount@mydomain.com

two configuration options are created: *store.url* and *store.account*. These values will be loaded at every future kamaki execution.

Available options
^^^^^^^^^^^^^^^^^

The [global] group is treated by kamaki as a generic group for arbitrary options, and it is used as a super-group for vital Kamaki options, namely account, token, url, cli. This feature does not work for types of configuration options. For example if global.account option is set and store.account option is not set, store services will use the global.account option instead. In case of conflict, the most specific options override the global ones.

* global.colors <on|off>
    enable / disable colors in command line based uis. Requires ansicolors, otherwise it is ignored

* global.account <account name>
    the username or user email that is user to connect to the cloud service. It can be omitted if provided as a service-specific option

* global.token <user authentication token>

* store.cli <UI command specifications for store>
    a special package that is used to load storage commands to kamaki UIs. Don't touch this unless if you know what you are doing.

* store.url <OOS storage or Pithos+ service url>
    the url of the OOS storage or Pithos+ service. Set to Okeanos.grnet.gr Pithos+ storage service by default. Users should set a different value if they need to use a different storage service.

* store.account <account name>
    if set, it overrides possible global.account option for store level commands.

* store.token <token>
    it set, it overrides possible global.token option for store level commands

* compute.url <OOS compute or Cyclades service url>
    the url of the OOS compute or Cyclades service. Set to Okeanos.grnet.gr Cyclades IaaS service by default. Users should set a different value if they need to use a different IaaS service.

* cyclades.cli <UI command specifications for cyclades>
    a special package that is used to load cyclades commands to kamaki UIs. Don't touch this unless you know what you are doing.

* flavor.cli <UI command specifications for VM flavors>
    a special package that is used to load cyclades VM flavor commands to kamaki UIs. Don't touch this unless you know what you are doing.

* network.cli <UI command specifications for virtual networks>
    a special package that is used to load cyclades virtual network commands to kamaki UIs. Don't touch this unless you know what you are doing.

* image.url <Plankton image service url>
    the url of the Plankton service. Set to Okeanos.grnet.gr Plankton service be default. Users should set a different value if they need to use a different service.

* image.cli <UI command specifications for Plankton and Cyclades image service>
    a special package that is used to load image-related commands to kamaki UIs. Don't touch this unless you know what you are doing.

* astakos.url <Astakos authentication service url>
    the url of the Astakos authentication service. Set to the Okeanos.grnet.gr Astakos service by default. Users should set a different value if they need to use a different service.

* astakos.cli <UI command specifications for Astakos authentication service>
    a special package that is used to load astakos-related commands to kamaki UIs. Don't touch this unless you know what you are doing.

* history.file <history file path>
    the path of a simple file for inter-session kamaki history. Make sure kamaki is executed in a context where this file is accessible for reading and writing. Kamaki automatically creates the file if it doesn't exist

Hidden features
^^^^^^^^^^^^^^^

Since version 0.6.1 kamaki contains a test suite for the kamaki.clients API. The test suite can be activated with the following option on the configuration file::

    [test]
    cli=test_cli

After that, users can run "kamaki test" commands to unit-test the prepackaged client APIs. Unit-tests are still experimental and there is a high probability of false alarms due to some of the expected values being hard-coded in the testing code.

Since version 0.6.3, a quotaholder client is introduced as an advanced feature. Quotaholder client is mostly used as a client library for accessing a synnefo quota service, but it can also be allowed as a kamaki command set, but setting the quotaholder.cli and quotaholder.url methods:

    [quotaholder]
    cli=quotaholder_cli
    url=<URL of quotaholder service>
