Adding Commands
===============

Kamaki commands are implemented as python classes, which wear a decorator
called *command*. The decorator lives in *kamaki.cli* and its purpose is to
update the *CommandTree* structure. The *CommandTree* class (
*kamaki.cli.cmdtree*) manages command namespaces for kamaki.

For demonstration purposes, the following set of kamaki commands will be
implemented in this document::

    mygrp1 list all                             //show a list
    mygrp1 list details [--match=<>]            //show list of details
    mygrp2 list all [regular expression] [-l]   //list all subjects
    mygrp2 info <id> [--filter]                 //information on a subject

.. note:: By convention, the names of the groups describe subjects e.g.,
    "server", "network", "container", etc.

Here we get two command groups to implement i.e., *mygrp1* and *mygrp2*,
containing two commands each (*list_all*, *list_details* and *list_all*, *info*
respectively). The underscore is used to separate command namespaces and should
be considered as a special character in this context.

The first command (*mygrp1_list_all*) has the simplest possible syntax: no
parameters, no runtime arguments. The second one defines one optional runtime
argument with a value. The third features an optional parameter and an optional
runtime flag argument. The last one is an example of a command with an
obligatory and an optional parameter.

Some examples:

.. code-block:: console

    $kamaki mygrp1
        mygrp1 description

        Options
         - - - -
        list
    $ kamaki mygrp1 list

        Options
         - - - -
        all        show a list
        details     show a list of details
    $ kamaki mygrp1 list all
        ... (a mygrp1_list_all instance runs) ...
    $ kamaki mygrp2 list all 'Z[.]' -l
        ... (a mygrp2_list_all instance runs) ...
    $

The CommandTree structure
-------------------------

CommandTree manages commands and their namespaces. Each command is stored in
a tree, where each node is a name. A leaf is the rightmost term of a namespace
and contains a pointer to the executable command class.

Here is an example from the actual kamaki command structure, featuring the
commands *file upload*, *file list* and *file info* ::

    - file
    ''''''''|- info
            |- list
            |- upload

Now, let's load the showcase example on CommandTrees::

    - mygrp1
    ''''''''|- list
            '''''''|- all
                   |- details

    - mygrp2
    ''''''''|- list
            '''''''|- all
            |- info

Each command group should be stored on a different CommandTree.

For that reason, command specification modules should contain a list of
CommandTree objects, named *_commands*. This mechanism allows any interface
application to load the list of commands from the *_commands* array.

.. code-block:: python

    _mygrp1_commands = CommandTree('mygrp', 'mygrp1 description')
    _mygrp2_commands = CommandTree('mygrp', 'mygrp2 description')

    _commands = [_mygrp1_commands, _mygrp2_commands]

.. note:: The name and the description, will later appear in automatically
    created help messages

The command decorator
---------------------

All commands are specified by subclasses of *kamaki.cli.cmds.CommandInit*
These classes are called "command specifications".

The *command* decorator mines all the information needed to build namespaces
from a command specification::

    class code  --->  command()  -->  updated CommandTree structure

Kamaki interfaces make use of the CommandTree structure. Optimizations are
possible by using special parameters on the command decorator method.

.. code-block:: python

    def command(cmd_tree, prefix='', descedants_depth=None):
    """Load a class as a command

        :param cmd_tree: is the CommandTree to be updated with a new command

        :param prefix: of the commands allowed to be inserted ('' for all)

        :param descedants_depth: is the depth of the tree descendants of the
            prefix command.
    """

Creating a new command specification set
----------------------------------------

A command specification developer should create a new module (python file) with
one command specification class per command. Each class should be decorated
with *command*.

.. code-block:: python

    ...
    _commands = [_mygrp1_commands, _mygrp2_commands]

    @command(_mygrp1_commands)
    class mygrp1_list_all():
        ...

    ...

A list of CommandTree structures must exist in the module scope, with the name
*_commands*. Different CommandTree objects correspond to different command
groups.

Set command description
-----------------------

The first line of the class commend is used as the command short description.
The rest is used as the detailed description.

.. code-block:: python

    ...
    @command(_mygrp2_commands)
    class mygrp2_info():
        """get information for subject with id
        Anything from this point and bellow constitutes the long description
        Please, mind the indentation, pep8 is not forgiving.
        """
        ...

Description placeholders
------------------------

There is possible to create an empty command, that can act as a description
placeholder. For example, the *mygrp1_list* namespace does not correspond to an
executable command, but it can have a helpful description. In that case, create
a command specification class with a command and no code:

.. code-block:: python

    @command(_mygrp1_commands)
    class mygrp1_list():
        """List mygrp1 objects.
        There are two versions: short and detailed
        """

.. warning:: A command specification class with no description is invalid and
    will cause an error.

Declare run-time argument
-------------------------

The argument mechanism is based on the standard argparse module.

Some basic argument types are defined at the
`argument module <code.html#module-kamaki.cli.argument>`_, but it is not
a bad idea to extent these classes in order to achieve specialized type
checking and syntax control with respect to the semantics of each command.
Still, in most cases, the argument types of the argument package are enough for
most cases.

To declare a run-time argument on a specific command, the specification class
should contain a dict called *arguments* , where Argument objects are stored.
Each argument object is a run-time argument. Syntax checking happens at the
command specification level, while the type checking is implemented in the
Argument subclasses.

.. code-block:: python

    from kamaki.cli.argument import ValueArgument
    ...

    @command(_mygrp1_commands)
    class mygrp1_list_details():
        """list of details"""

        def __init__(self, global_args={}):
            global_args['match'] = ValueArgument(
                'Filter results to match string',
                ('-m', '--match'))
            self.arguments = global_args

or more usually and elegantly:

.. code-block:: python

    from kamaki.cli.argument import ValueArgument
    
    @command(_mygrp1_commands)
    class mygrp1_list_details():
    """List of details"""

        arguments = dict(
            match=ValueArgument(
                'Filter output to match string', ('-m', --match'))
        )

Accessing run-time arguments
----------------------------

To access run-time arguments, command classes extend the *CommandInit*
interface, which implements *__item__* accessors to handle run-time argument
values. In other words, one may get the runtime value of an argument by calling
*self[<argument>]*.

.. code-block:: python

    from kamaki.cli.argument import ValueArgument
    from kamaki.cli.commands import CommandInit
    
    @command(_mygrp1_commands)
    class mygrp1_list_details(CommandInit):
        """List of details"""

        arguments = dict(
            match=ValueArgument(
                'Filter output to match string', ('-m', --match'))
        )

        def check_runtime_arguments(self):
            ...
            assert self['match'] == self.arguments['match'].value
            ...

Non-positional required arguments
---------------------------------

By convention, kamaki uses positional arguments for identifiers and
non-positional arguments for everything else. By default, non-positional
arguments are optional. A non-positional argument can explicitly set to be
required at command specification level:

.. code-block:: python

    ...

    @command(_mygrp1_commands)
    class mygrp1_list_details(CommandInit):
        """List of details"""

        arguments = dict(
            match=ValueArgument(
                'Filter output to match string', ('-m', --match'))
        )
        required = (match, )

A tupple means "all required", while a list notation means "at least one".


The main method and command parameters
--------------------------------------

The command behavior for each command class is coded in *main*. The
parameters of *main* method affect the syntax of the command. In specific::

    main(self, param)                   - obligatory parameter <param>
    main(self, param=None)              - optional parameter [param]
    main(self, param1, param2=42)       - <param1> [param2]
    main(self, param1____param2)        - <param1:param2>
    main(self, param1____param2=[])     - [param1:param2]
    main(self, param1____param2__)      - <param1[:param2]>
    main(self, param1____param2__='')   - [param1[:param2]]
    main(self, *args)                   - arbitary number of params [...]
    main(self, param1____param2, *args) - <param1:param2> [...]

Let's have a look at the command specification class again, and highlight the
parts that affect the command syntax:

.. code-block:: python
    :linenos:

    from kamaki.cli.argument import FlagArgument
    ...

    _commands = [_mygrp1_commands, _mygrp2_commands]
    ...

    @command(_mygrp2_commands)
    class mygrp2_list_all():
        """List all subjects
        Refers to the subject accessible by current user
        """

        arguments = dict(FlagArgument('detailed list', '-l'))

        def main(self, reg_exp=None):
            ...

The above lines contain the following information:

* Namespace and name (line 8): mygrp2 list all
* Short (line 9) and long (line 10) description
* Parameters (line 15): [reg exp]
* Runtime arguments (line 13): [-l]
* Runtime arguments help (line 13): detailed list

.. tip:: By convention, the main functionality is implemented in a member
    method called *_run*. This allows the separation between syntax and logic.
    For example, an external library may need to call a command without caring
    about its command line behavior.

Letting kamaki know
-------------------

Assume that the command specifications presented so far be stored in a file
named *grps.py*.

The developer should move the file *grps.py* to *kamaki/cli/cmds*, the
default place for command specifications

These lines should be contained in the kamaki configuration file for a new
command specification module to work:
::

    [global]
    mygrp1_cli = grps
    mygrp2_cli = grps

or equivalently:

.. code-block:: console

    $ kamaki config set mygrp1_cli grps
    $ kamaki config set mygrp2_cli grps

.. note:: running a command specification from a different path is supported.
    To achieve this, add a *<group>_cli = </path/to/module>* line in the
    configure file under the *global* section

An example::

    [global]
    mygrp_cli = /another/path/grps.py

Summary: create a command set
-----------------------------

.. code-block:: python

    #  File: grps.py

    from kamaki.cli.cmds import CommandInit
    from kamaki.cli.cmdtree import CommandTree
    from kamaki.cli.argument import ValueArgument, FlagArgument
    ...


    #  Initiallize command trees

    _mygrp1_commands = CommandTree('mygrp', 'mygrp1 description')
    _mygrp2_commands = CommandTree('mygrp', 'mygrp2 description')

    _commands = [_mygrp1_commands, _mygrp2_commands]


    #  Define command specifications


    @command(_mygrp1_commands)
    class mygrp1_list(CommandInit):
        """List mygrp1 objects.
        There are two versions: short and detailed
        """


    @command(_mygrp1_commands)
    class mygrp1_list_all(CommandInit):
        """show a list"""

        def _run():
            ...

        def main(self):
            self._run()


    @command(_mygrp1_commands)
    class mygrp1_list_details(CommandInit):
        """show list of details"""

        arguments = dict(
            match=ValueArgument(
                'Filter output to match string', ('-m', --match'))
        )

        def _run(self):
            match_value = self['match']
            ...

        def main(self):
        self._run()


    #The following will also create a mygrp2_list command with no description


    @command(_mygrp2_commands)
    class mygrp2_list_all(CommandInit):
        """list all subjects"""

        arguments = dict(
            list=FlagArgument('detailed listing', '-l')
        )

        def _run(self, regexp):
            ...
            if self['list']:
                ...
            else:
                ...

        def main(self, regular_expression=None):
            self._run(regular_expression)


    @command(_mygrp2_commands)
    class mygrp2_info(CommandInit):
        """get information for subject with id"""

        def _run(self, grp_id, grp_name):
            ...

        def main(self, id, name=''):
            self._run(id, name) 
