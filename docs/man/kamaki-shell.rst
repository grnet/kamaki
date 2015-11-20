:orphan:

kamaki shell manual page
========================

Synopsis
--------

**kamaki-shell** [*group*] [*command*] [...] [*arguments*]

Description
-----------

:program:`kamaki` is a simple, yet intuitive, command-line tool for managing
clouds. It can be used in three forms: as an interactive shell
(`kamaki-shell`), as a command line tool (`kamaki`) or as a clients API for
other applications (`kamaki.clients`).

Launch options
--------------

.. code-block:: console

    -v                      Verbose output, without HTTP data
    -vv                     Verbose output, including HTTP data
    -d                      Use debug output.
    -o KEY=VAL              Override a config value (can be repeated)
    --cloud CLOUD           Cloud to be used for this shell session

Commands
--------

:manpage: `kamaki(1)`

Shell Management Commands
*************************

exit
    Exit the interactive shell or a command namespace inside the shell

shell
    Execute commands on host system shell (e.g. bash)

Kamaki and API commands
***********************
The Kamaki and API commands are the same in both the CLI and the shell. For a
complete list of the common commands, check the "COMMANDS" section at the
following manpage:

:manpage: `kamaki(1)`

Author
------

Synnefo development team <synnefo-devel@googlegroups.com>.

