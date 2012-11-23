Usage
=====

Kamaki offers two command line interfaces: an one-command tool and an interactive shell. Both systems implement the exact same command specifications. A detailed list of the command specifications can be found in `Commands <commands.html>`_ section. This guide covers the generic usage of both interfaces.

What's more, kamaki offers a clients API that allows the developement of external applications for synnefo. The clients API is listed in the `Clients lib <clients.html>`_ section. The recomended method of utilizing this API is explained in the present.

Setup
-----

Kamaki interfaces rely on a list of configuration options. In the initial state, kamaki is configured to communicate with the Okenos IaaS. A detailed guide for setting up kamaki can be found in the `Setup <setup.rst>`_ section.

Quick guide
^^^^^^^^^^^

It is essential for users to get a configuration token (to get in Okeanos.grnet.gr log `here <https://accounts.okeanos.grnet.gr/im/>`_) and provide it to kamaki:

.. code-block:: console

    $ kamaki set token myt0k3n==


    Example 1.1.1: Set user token to myt0k3n==

To use the storage service, a user should also provide the username:

.. code-block:: console

    $ kamaki set account user@domain.com


    Example 1.1.2: Set user name to user@domain.com

Run as shell
""""""""""""
Call kamaki

* without any parameters or arguments

.. code-block:: console

    $ kamaki


    Example 1.2.1: Running kamaki shell


* with any kind of '-' prefixed arguments, except '-h', '--help'.

.. code-block:: console

    $ kamaki --config myconfig.file

   
    Example 1.2.2: Running kamaki shell with custom configuration file


Run as one-command
""""""""""""""""""
Call kamaki:

* with the '-h' or '--help' arguments (help for kamaki one-command)

.. code-block:: console

    $kamaki -h


    Example 1.3.1: Kamaki help

* with one or more command parameters:

.. code-block:: console

    $ kamaki server list


    Example 1.3.2: List VMs managed by user

Command parameters
""""""""""""""""""

Typically, commands consist of a group name (e.g. store for storage commands) one or more terms (e.g. list for listing) and the command specific parameters (e.g. the name of the container), if any.

.. code-block:: console

    $ kamaki store list mycontainer


    Example 1.4.1: List stored files in container mycontainer

E.g. in example 1.3.2, the group is "server", the command is "list" and there are no parameters. Example 6 is another example using the "server" command group.

.. code-block:: console

    $ kamaki server info 42


    Example 1.4.2: Show information about a user-managed VM with id 42

One-command interface
---------------------


Interactive shell
-----------------

Creating applications over the Clients API
------------------------------------------
