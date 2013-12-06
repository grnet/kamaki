Configuration
=============

The following refers to the configuration version 0.12 or better. There is also
information on how to convert from older configuration files.

In this scenario, we start with an old configuration file at
*${HOME}/.kamakirc* that we need to convert. We also create a new one from scratch. In both cases, the second step is the same: set up one or more clouds
in a single configuration. Then we examine a case of multiple configuration
files.

Convert old configuration file
------------------------------

First, back up the old file

.. code-block:: console

    $ cp ~/.kamakirc ~/backups/.kamakirc

Now, let kamaki do the conversion

.. code-block:: console

    $ kamaki user info
    . Config file format version >= 0.12 is required
    . Configuration file: /home/someuser/.kamakirc
    . Attempting to fix this:
    . Calculating changes while preserving information
    . ... rescue global.token => cloud.default.token
    . ... rescue user.cli => global.user_cli
    . ... rescue network.cli => global.network_cli
    . ... rescue file.cli => global.file_cli
    . ... rescue flavor.cli => global.flavor_cli
    . ... rescue config.cli => global.config_cli
    . ... rescue image.cli => global.image_cli
    . ... rescue server.cli => global.server_cli
    . ... rescue history.file => global.history_file
    . ... rescue history.cli => global.history_cli
    . ... change network_cli value: cyclades => network
    . ... DONE
    . The following information will NOT be preserved:
    .     global.account = AccountName
    .     user.url = https://accounts.example.com
    .     user.account = UserAccountName
    .     compute.url = https://cyclades.example.com/api/v1.1
    .     file.url = https://pithos.example.com/v1
    .     image.url = https://cyclades.example.com/plankton
    .     store.account = OldForgotenAccountName
    . Kamaki is ready to convert the config file
    . Create (overwrite) file .kamakirc ? [y/N]
    .
    <y is pressed>
    .
    . No cloud "default" is configured
    . |  To configure a new cloud "default", find and set the
    . |  single authentication URL and token:
    . |    kamaki config set cloud.default.url <URL>
    . |    kamaki config set cloud.default.token <t0k3n>
    $

.. warning:: A new cloud configuration with the name "default" is created. The
    global token that was set in the old configuration file, is preserved as
    the token of the "default" cloud. Still, kamaki needs a url for the cloud
    and it encourages you to reset the token as well.

.. note:: Some options are discarded. Among them, are the service urls, like
    user.url, compute.url, image.url and file.url . These settings are obsolete
    since Synnefo 0.14 and kamaki 0.9 so you do not need to recover them. The
    same is true for user accounts (retrieved automatically)

.. note:: You can safely remove the global.XXX_cli options from kamaki
    configuration file. Kamaki can automatically resolve the default values for
    these internal options. These options are usefull when overloading the
    default command behaviors, but are not needed otherwise.

Attempt to create a new configuration
-------------------------------------

Ask kamaki to load from a non-existing configuration file

.. code-block:: console

    $ kamaki -c nonexisting.cnf user info
    . No cloud is configured
    . |  To configure a new cloud "<cloud name>", find and set the
    . |  single authentication URL and token:
    . |    kamaki config set cloud.<cloud name>.url <URL>
    . |    kamaki config set cloud.<cloud name>.token <t0k3n>
    $ ls -l nonexisting.cnf
    . ls: cannot access nonexisting.cnf: No such file or directory
    $

.. note:: configuration file is not created, but it will be when we set the
    first configuration value in it, as shown in the following subsection.

Configure a cloud and create a new configuration
------------------------------------------------

Set the URL for new cloud "mytest"

.. code-block:: console

    $ kamaki -c nonexisting.cnf config set cloud.mytest.url https://accounts.example.com/identity/v2.0/

Try to connect

.. code-block:: console

    $ kamaki -c nonexisting.cnf user info
    . No authentication token provided for cloud "mytest"
    . |  Set a token for cloud mytest:
    . |    kamaki config set cloud.mytest.token <token>

Set token to cloud "mytest"

.. code-block:: console

    $ kamaki -c nonexisting.cnf config set cloud.mytest.token myt35t70k3n==

Check that the file is created, everything is set up correctly and working

.. code-block:: console

    $ ls -l nonexisting.cnf
    . -rw======- 1 someuser someuser 491 Jun 17 13:39 nonexisting.cnf
    $ kamaki -c nonexisting.cnf config get cloud
    . cloud.mytest.url = https://accounts.example.com/identity/v2.0/
    . cloud.mytest.token = myt35t70k3n==
    $ kamaki -c nonexisting.cnf user autenticate
    . ...
    . user:
    .     id:          s0me-3x4mp13-u53r-1d
    .     name:        Some User
    .     roles:
    .          id:   1
    .          name: default
    .     roles_links:
    $

Failed or incomplete cloud configurations
-----------------------------------------

Now let kamaki use the default configuration (*${HOME}/.kamakirc*). Let the old
token be `my0ld70k3n==` and let it be invalid.

Check for clouds and attempt to authenticate

.. code-block:: console

    $ kamaki config get cloud
    . cloud.default.token = my0ld70k3n==
    $ kamaki user info
    . No authentication URL provided for cloud "mytest"
    . |  Set a URL for cloud mytest:
    . |    kamaki config set cloud.mytest.url <URL>
    $

Set a non-existing URL for cloud.default and attempt authentication

.. code-block:: console

    $ kamaki config set cloud.default.url https://nonexisting.example.com
    $ kamaki user info
    . Failed while http-connecting to https://nonexisting.example.com
    $

Set the URL from the previous example and attempt authentication

.. code-block:: console

    $ kamaki config set cloud.default.url https://accounts.example.com/identity/v2.0/
    $ kamaki user info
    . (401) Authorization failed for token gZH99orgkfYHmGksZKvHJw==
    . |  UNAUTHORIZED unauthorized (Invalid token)
    $

After some searching at the deployments UI, you find out that the URL/token
pair you need is::

    URL: https://accounts.deploymentexample.com/identity/v2.0
    TOKEN: myd3pl0ym3nt70k3n==

Set up the correct values and attempt authentication

.. code-block:: console

    $ kamaki config set cloud.default.url https://accounts.deploymentexample.com/identity/v2.0
    $ kamaki config set cloud.default.token myd3pl0ym3nt70k3n==
    $ kamaki user info
    . ...
    . user:
    .     id: my-d3pl0ym3nt-u53r-1d
    .     name: Example Username
    $

Multiple clouds in a single configuration
-----------------------------------------

We now have two configurations::

    Configuration file: ${HOME}/.kamakirc    (default)
      Clouds:
        ALIAS: default
        URL: https://accounts.deploymentexample.com/identity/v2.0
        TOKEN: myd3pl0ym3nt70k3n==

    Copnfiguration file: nonexisting.cnf
      Clouds:
        ALIAS: mytest
        URL: https://accounts.example.com/identity/v2.0/
        TOKEN: myt35t70k3n==

Obviously the default configuration handles only one cloud, aliased as
"default". We will add the second cloud as well.

.. code-block:: console

    $ kamaki config set cloud.mytest.url https://accounts.example.com/identity/v2.0/
    $ kamaki config set cloud.mytest.token myt35t70k3n==
    $

Check all clouds

.. code-block:: console

    $ kamaki config get cloud
    . cloud.default.url = https://accounts.deploymentexample.com/identity/v2.0/
    . cloud.default.token = myd3pl0ym3nt70k3n==
    . cloud.mytest.url = https://accounts.example.com/identity/v2.0/
    . cloud.mytest.token = myt35t70k3n==
    $

Check if kamaki is confused (is there a default cloud setup?)

.. code-block:: console

    $ kamaki config get default_cloud
    . default
    $

Authenticate against different clouds

.. code-block:: console

    $ kamaki user info
    . ...
    . <response from deploymentexample.com>
    . ...
    $ kamaki --cloud=mytest user info
    . ...
    . <response from example.com>
    . ...
    $ kamaki --cloud=default user info
    . ...
    . <response from deploymentexample.com, same as default behavior>
    . ...
    $ kamaki --cloud=nonexistingcloud user info
    . No cloud "nonexistingcloud" is configured
    . |  To configure a new cloud "nonexistingcloud", find and set the
    . |  single authentication URL and token:
    . |    kamaki config set cloud.nonexistingcloud.url <URL>
    . |    kamaki config set cloud.nonexistingcloud.token <t0k3n>
    $

Confuse kamaki by removing the default_cloud option, set mytest as default

.. code-block:: console

    $ kamaki config delete default_cloud
    $ kamaki user info
    . Found 2 clouds but none of them is set as default
    . |  Please, choose one of the following cloud names:
    . |  default, mytest
    . |  To set a default cloud:
    . |    kamaki config set default_cloud <cloud name>
    $ kamaki config set default_cloud mytest
    $ kamaki user info
    . ...
    . <response from example.com>
    . ...
    $

`Question`: What will happen if the "default" cloud alias **and** the
default_cloud option are removed?

.. code-block:: console

    $ kamaki config delete cloud.default
    $ kamaki config delete default_cloud
    $ kamaki user info
    . ...
    . <response from example.com>
    . ...
    $

`Answer`: kamaki doesn't have a default_cloud option, but there is only one
cloud configuration (`mytest`), therefore there is no ambiguity in resolving
the default cloud.
