For Developers
==============

Creating applications with kamaki API
-------------------------------------

Kamaki features a clients API for building third-party client applications that communicate with OpenStack and / or Synnefo cloud services. The package is called kamaki.clients and contains a number of 

A good example of an application build on kamaki.clients is kamaki.cli, the command line interface of kamaki. 

Since synnefo services are build as OpenStack extensions, an inheritance approach has been chosen for implementing clients for both. In specific, the *compute*, *storage* and *image* modules are clients of the OS compute, OS storage and Glance APIs, respectively. On the contrary, all the other modules are Synnefo extensions (*cyclades* extents *compute*, *pithos* and *pithos_rest_api* extent *storage*) or novel synnefo services (e.g. *astakos*).

Setup a client instance
^^^^^^^^^^^^^^^^^^^^^^^

External applications may instantiate one or more kamaki clients.

.. code-block:: python
    :emphasize-lines: 1

    Example 1.1: Instantiate a Cyclades client


    from kamaki.clients.cyclades import CycladesClient
    from kamaki.clients.pithos import PithosClient

    my_cyclades_client = CycladesClient(base_url, token)
    my_pithos_client = PithosClient(base_url, token, account, container)

.. note:: *cyclades* and *pithos* clients inherit all methods of *compute* and *storage* clients respectively. Separate compute or storage objects should be used only when implementing applications for strict OS Compute or OS Storage services.

Use client methods
^^^^^^^^^^^^^^^^^^

Client methods can now be called. Developers are advised to consult :ref:`the-client-api-ref` for details on the available methods and how to use them.

In the following example, the *cyclades* and *pithos* clients of example 1.1 are used to extract some information, that is then printed to the standard output.


.. code-block:: python
    :emphasize-lines: 1,2

    Example 1.2: Print server name and OS for server with server_id
                Print objects in container mycont


    srv = my_cyclades_client.get_server_info(server_id)
    print("Server Name: %s (with OS %s" % (srv['name'], srv['os']))

    obj_list = my_pithos_client.list_objects(mycont)
    for obj in obj_list:
        print('  %s of %s bytes' % (obj['name'], obj['bytes']))

.. code-block:: console
    :emphasize-lines: 1

    Run of examples 1.1 + 1.2


    $ python test_script.py
    Server Name: A Debian Server (with OS Debian Base)
      lala.txt of 34 bytes
      test.txt of 1232 bytes
      testDir/ of 0 bytes
    $ 

Error handling
^^^^^^^^^^^^^^

The kamaki.clients standard error is ClientError. A ClientError is raised for any kind of kamaki.clients errors (errors reported by servers, type errors in arguments, etc.).

A ClientError contains::

    message     The error message.
    status      An optional error code, e.g. after a server error.
    details     Optional list of messages with error details.

The following example concatenates examples 1.1 and 1.2 plus error handling

.. code-block:: python

    Example 1.3: Error handling


    from kamaki.clients.cyclades import CycladesClient
    from kamaki.clients.pithos import PithosClient

    try:
        my_cyclades_client = CycladesClient(base_url, token)
    except ClientError:
        print('Failed to initialize Cyclades client')

    try:
        my_pithos_client = PithosClient(base_url, token, account, container)
    except ClientError:
        print('Failed to initialize Pithos+ client')

    try:
        srv = my_cyclades_client.get_server_info(server_id)
        print("Server Name: %s (with OS %s" % (srv['name'], srv['os']))

        obj_list = my_pithos_client.list_objects(mycont)
        for obj in obj_list:
            print('  %s of %s bytes' % (obj['name'], obj['bytes']))
    except ClientError as e:
        print('Error: %s' % e)
        if e.status:
            print('- error code: %s' % e.status)
        if e.details:
            for detail in e.details:
                print('- %s' % detail)

Adding Commands
---------------

Architecture
^^^^^^^^^^^^

Kamaki commands are implemented as python classes, decorated with a special decorator called *command*. This decorator is a method of kamaki.cli that adds a new command in a CommandTree structure (kamaki.cli.commant_tree). The later is used by interfaces to manage kamaki commands.

The CommandTree structure
"""""""""""""""""""""""""

CommandTree manages a command by its path. Each command is stored in multiple nodes on the tree, so that the last term is a leaf and the route from root to that leaf represents the command path. For example the commands *store upload*, *store list* and *store info* are stored together as shown bellow::

    - store
    ''''''''|- info
            |- list
            |- upload

Each command group should be stored on a different CommandTree. For that reason, command specification modules should contain a list of CommandTree objects, named *_commands*

A command group information (name, description) is provided at CommandTree structure initialization::

    _mygrp_commands = CommandTree('mygrp', 'My Group Commands')

The command decorator
"""""""""""""""""""""

The *command* decorator mines all the information necessary to build a command specification which is inserted in a CommanTree instance::

    class code  --->  command()  -->  updated CommandTree structure

Kamaki interfaces make use of this CommandTree structure. Optimizations are possible by using special parameters on the command decorator method.

.. code-block:: python

    def command(cmd_tree, prefix='', descedants_depth=None):
    """Load a class as a command
        @cmd_tree is the CommandTree to be updated with a new command
        @prefix of the commands allowed to be inserted ('' for all)
        @descedants_depth is the depth of the tree descedants of the
            prefix command.
    """

Creating a new command specification set
""""""""""""""""""""""""""""""""""""""""

A command specification developer should create a new module (python file) with as many classes as the command specifications to be offered. Each class should be decorated with *command*.

A list of CommandTree structures must exist in the module scope, with the name _commands. Different CommandTree objects correspond to different command groups.

Declare run-time argument
"""""""""""""""""""""""""

The argument mechanism allows the definition of run-time arguments. Some basic argument types are defined at the `argument module <cli.html#module-kamaki.cli.argument>`_, but it is not uncommon to extent these classes in order to achieve specialized type checking and syntax control (e.g. at `pithos_cli module <cli.html#module-kamaki.cli.commands.pithos_cli>`_).

Putting them all together
"""""""""""""""""""""""""

The information that can be mined by *command* for each individual command are presented in the following, for a sample command:

.. code-block:: python

    @command(_mygrp_commands)
    class mygrp_cmd1_cmd2(object):
        """Command Description"""

        def __init__(self, arguments={}):
            arguments['arg1'] = FlagArgument(
                'Run with arg1 on',
                --arg1',
                False)

            self.arguments = arguments

        def main(self, obligatory_param1, obligatory_param2,
            optional_param1=None, optional_param2=None):
            ...
            command code here
            ...

This will load the following information on the CommandTree::

    Syntax: mygrp cmd1 cmd2 <objigatory param1> <obligatory param2>
        [optional_param1] [optional_param2] [--arg1]
    Description: Command Description
    Arguments help: --arg1: Run with arg1 on

Letting kamaki know
"""""""""""""""""""

Kamaki will load a command specification *only* if it is set as a configurable option. To demonstrate this, let a commands module grps be implemented in the file *grps.py* where there are two command groups defined: mygrp1 mygrp2.

Move grps.py to kamaki/cli/commands, the default place for command specifications

In the configuration file, add:

.. code-block:: console

    [mygrp1]
    cli=grps

    [mygrp2]
    cli=grps

or alternatively

.. code-block:: console

    $ kamaki config set mygrp1.cli = grps
    $ kamaki config set mygrp2.cli = grps

Command modules don't have to live in kamaki/cli/commands, although this is suggested for uniformity. If a command module exist in another path::

    [mygrp]
    cli=/another/path/grps.py

Developing a Command Specification Set
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

TODO

Extending kamaki.clients
------------------------

By default, kamaki clients are REST clients (they manage HTTP requests and responses to communicate with services). This is achieved by importing the connection module, which is an httplib rapper.

Connection
^^^^^^^^^^

The connection module features an error handling and logging system, a lazy response mechanism, a pooling mechanism as well as concurrency control for thread-demanding client functions (e.g. store upload).

How to build a client
^^^^^^^^^^^^^^^^^^^^^

All service clients consist of a subclass of the Client class and implement separate client functionalities as member methods. There is also an error class to raise exceptions that can be handled by kamaki interfaces.

.. code-block:: python
    
    #  ${KAMAKI_PATH}/kamaki/clients/mynewclient.py

    from kamaki.clients import Client, ClientError

    class MyNewClient(Client):
        """MyNewClient Description Here"""

        def my_first_method(self, **args):
            """Method description"""
            try:
                ...
                method code
                ...
            except SomeKnownException as e1:
                raise ClientError('MyError: %s' % e1)
            except SomeOtherException as e2:
                raise ClientError('MyError: %s' % e2)

        def my_second_method(self, **params):
            """Method description"""
            ...

Custom clients can use a set of convenience methods for easy HTTP requests

.. code-block:: python

    def get(self, path, **kwargs)
    def head(self, path, **kwargs)
    def post(self, path, **kwargs)
    def put(self, path, **kwargs)
    def delete(self, path, **kwargs)
    def copy(self, path, **kwargs)
    def move(self, path, **kwargs)

How to use your client
^^^^^^^^^^^^^^^^^^^^^^

External applications must instantiate a MyNewClient object.

.. code-block:: python

    from kamaki.clients import ClientError
    from kamaki.clients.mynewclient import MyNewClient

    ...
    try:
        cl = MyNewClient(args)
        cl.my_first_method(other_args)
    except ClientError as cle:
        print('Client Error: %s' % cle)
    ...

Concurrency control
^^^^^^^^^^^^^^^^^^^

Kamaki clients may handle multiple requests at once, using threads. In that case, users might implement their own thread handling mechanism, use an external solution or take advantage of the mechanism featured in kamaki.clients

.. code-block:: python

    from threading import enumerate
    from kamaki.clients import SilentEvent
    ...

    class MyNewClient(Client):
        ...

        def _single_threaded_method(self, **args):
            ...
            request code
            ...

        def multithread_method(self):
            thread_list = []
            self._init_thread_limit()
            while some_condition or thread_list:
                ...
                event = SilentEvent(self._single_threaded_method, **args)
                event.start()
                thread_list.append(event)
                thread_list = self._watch_thread_limit(thread_list)

The CLI API
-----------

.. toctree::

    cli

.. _the-client-api-ref:

The clients API
---------------

Imports
^^^^^^^

.. toctree::
    connection

Modules list
^^^^^^^^^^^^

compute
^^^^^^^

.. automodule:: kamaki.clients.compute
    :members:
    :show-inheritance:
    :undoc-members:


cyclades
^^^^^^^^

.. automodule:: kamaki.clients.cyclades
    :members:
    :show-inheritance:
    :undoc-members:


storage
^^^^^^^

.. automodule:: kamaki.clients.storage
    :members:
    :show-inheritance:
    :undoc-members:


pithos
^^^^^^

.. automodule:: kamaki.clients.pithos
    :members:
    :show-inheritance:
    :undoc-members:

pithos_rest_api
^^^^^^^^^^^^^^^

.. automodule:: kamaki.clients.pithos_rest_api
    :members:
    :show-inheritance:
    :undoc-members:


image
^^^^^

.. automodule:: kamaki.clients.image
    :members:
    :show-inheritance:
    :undoc-members:


astakos
^^^^^^^

.. automodule:: kamaki.clients.astakos
    :members:
    :show-inheritance:
    :undoc-members:


utils
^^^^^

.. automodule:: kamaki.clients.utils
    :members:
    :show-inheritance:
    :undoc-members:
