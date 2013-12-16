The Configuration module
========================

Kamaki CLI offers a configuration module named *config*. It features:

* The global dict *DEFAULTS* with all the configuration settings and default
    values for running a kamaki CLI

* The class *Config* is a ConfigParser extension adjusted to offer
    kamaki-specific functionalities (e.g., cloud management)

Instances of *kamaki.cli.config.Config* always store data at a local file,
the path of which, is usually given by user as a constructor parameter. If the
path of the configuration file is not specified explicitly, the value at
*kamaki.cli.config.CONFIG_PATH* is used instead.

Types of configuration options
------------------------------

There are at least two sections of configuration options i.e., the *global*
and the *cloud*. The *global* section is not special, but is used as the
default kamaki section by convention. The *Config* class is semantically
aware of the *cloud* types and handles them in a special way. Other
configuration types can also be created and managed in the same fashion as the
*global* ones.

Kamaki preset global options, as they appear in the configuration file::

    [global]
    project_cli = astakos
        default_cloud = my_cloud
        quota_cli = astakos
        file_cli = pithos
        subnet_cli = network
        history_cli = history
        group_cli = pithos
        server_cli = cyclades
        container_cli = pithos
        imagecompute_cli = image
        user_cli = astakos
        network_cli = network
        resource_cli = astakos
        config_cli = config
        flavor_cli = cyclades
        sharer_cli = pithos
        image_cli = image
        port_cli = network
        ip_cli = network
        history_file = /home/someuser/.kamaki.history
        colors = off
        log_pid = off
        log_token = off
        log_data = off
        log_file = /home/someuser/.kamaki.log

A cloud configuration is required to make kamaki run. The
`setup guide <../setup.html>`_ can help when setting one or more cloud
configurations.

Suppose that a cloud service is available with *https://main.example.com* as
the authentication URL and *s0m3-t0k3n* as the user token. In this example, the
user has already configured kamaki to refer to the service by the name "main"::

    [cloud "main"]
        url=https://main.example.com
        token=s0m3-t0k3n

Suppose that a different cloud service is also available with
*https://alternative.example.com* as the authentication URL and
*s0m3-0th3r-t0k3n* as the user token. Again, the user configured kamaki to
refer to this service as "alternative"::

    [cloud "alternative"]
        url=https://alternative.example.com
        token=s0m3-0th3r-t0k3n

If the user picks one of these clouds to be the default, the configuration file
will contain the following::


    [global]
        default_cloud=main
        ... <omitted for clarity>

    [cloud "main"]
        url=https://main.example.com
        token=s0m3-t0k3n

    [cloud "alternative"]
        url=https://alternative.example.com
        token=s0m3-0th3r-t0k3n

The Config class
----------------

The *kamaki.cli.config.Config* class (extends *RawConfigParser* which extends
`ConfigParser <http://docs.python.org/release/2.7/library/configparser.html>`_
) offers the methods of the RawConfigParser class (e.g., *get*, *set*), as well
as some default settings for kamaki and some additional functionality for
managing cloud configurations.

.. code-block:: python

    # Initialize two Config instances. Only the first will contain kamaki
    # default values

    from kamaki.cli.config import Config

    my_config = Config('/some/local/file.cnf')
    config_without_default_values = Config(with_defaults=False)

.. note:: If no file path is given, the Config instance is initialized
.. note:: The *with_defaults* flag can be used to omit all default settings
    from a kamaki Config instance e.g., in case of an external application that
    does not need any of the kamaki globals.

Here are the general purpose accessors offered by Config:

* get(section, option): get the *value* of an *option* in the specified
    *section* e.g.,

    .. code-block:: python

        # Example: get the default cloud (global.default_cloud option)

        thread_limit = my_config.get('global', 'default_cloud')

* set(section, option, value): set the *value* for an *option* in the specified
    *section* e.g.,

    .. code-block:: python

        # Example: set the default_cloud to "main"

        my_config.set('global', 'default_cloud', 'main')

* remove_option(section, option): remove an option from a section e.g.,

    .. code-block:: python

        # Example: remove the default_cloud option - Config will resort to the
        # default value for this option

        my_config.remove_option('global', 'default_cloud')

Global options
--------------

The global options are used to specify the kamaki CLI and client behavior. A
detailed catalog can be found at the
`setup section <../setup.html#available-options>`_ .

In the Config context, the global options are just the options under the
*global* section.

Cloud options
-------------

Cloud options are used to configure one or more cloud services.

The following methods are cloud-specific:

* get_cloud(cloud, option): Get the value of a cloud option e.g.,

    .. code-block:: python

        # Get the Auth URL and token for the cloud "main"
        auth_url = my_config.get_cloud('main', 'url')
        auth_token = my_config.get_cloud('main', 'token')

* set_cloud(cloud, option, value): Set the value of a cloud option e.g.,

    .. code-block:: python

        # Example: set a new authenticate URL and token for cloud "main"
        my_config.set_cloud('main', 'url', 'https://new.example.com')
        my_config.set_cloud('main', 'token', 'n3e-t0k3n-f0r-m41n')

* remove_from_cloud(cloud, option): Remove an option from the specified cloud
    e.g.,

    .. code-block:: python

        # Example: remove the token of the main cloud, for safety reasons
        my_config.remove_from_cloud('main', 'url')

.. warning:: A get/set/remove_option with a "cloud" section is not valid. There
    is a way of using the general purpose accessors for cloud configuration,
    and it is presented bellow, but programmers are discouraged from using it::

        my_config.get('cloud.main', 'url')
        my_config.set('cloud.main', 'url', 'https://new.example.com')
        my_config.remove_option('cloud.main', 'url')

Examples
--------

Get the default cloud values from a configuration file
""""""""""""""""""""""""""""""""""""""""""""""""""""""

.. code-block:: python

    from kamaki.cli.config import Config

    CONFIG_FILE_PATH = '/home/user/my.cnf'

    cnf = Config(CONFIG_FILE_PATH)
    try:
        CLOUD_NAME = cnf.get('global', 'default_cloud')
        AUTH_URL = cnf.get_cloud(CLOUD_NAME, 'url')
        AUTH_TOKEN = cnf.get_cloud(CLOUD_NAME, 'token')
    except KeyError:
        print 'Error: no valid configuration of a default cloud'

Set a new cloud, name it "new_cloud" and set it as default
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

.. code-block:: python

    from kamaki.cli.config import Config

    CONFIG_FILE_PATH = '/home/user/my.cnf'
    CLOUD_NAME = 'new_cloud'
    AUTH_URL = 'https://new.cloud.example.com'
    AUTH_TOKEN = 'n3w-cl0ud-t0k3n'

    cnf = Config(CONFIG_FILE_PATH)
    cnf.set_cloud(CLOUD_NAME, 'url', AUTH_URL)
    cnf.set_cloud(CLOUD_NAME, 'token', AUTH_TOKEN)
    cnf.set('global', 'default_cloud', CLOUD_NAME)

    # Push the changes to the configuration file
    cnf.write()

List all clouds with their URLs, let the user pick one
""""""""""""""""""""""""""""""""""""""""""""""""""""""

.. code-block:: python

    from kamaki.cli.config import Config

    cnf = Config()
    for name, cloud in cnf.items('cloud'):
        print 'Cloud', name, cloud['url']

    choice = raw_input('Type your cloud name, pls: ')
    if choice in cnf.keys('cloud'):
        cnf.set('global', 'default_cloud', choice)
    else:
        print 'No such cloud configured'
