Installation
============

This guide describes the standard installation process for kamaki, with the aspiration of covering as much cases as possible. Although kamaki was initially targeted to advanced Linux/Unix-like users, it should be quite straightforward to install and have it up and running in most popular platforms.


* Kamaki repository: `http://code.grnet.gr/git/kamaki <http://code.grnet.gr/git/kamaki>`_

* Synnefo Linux packages: `http://apt.dev.grnet.gr <http://apt.dev.grnet.gr>`_, `http://apt2.dev.grnet.gr <http://apt2.dev.grnet.gr>`_

Linux and Unix-like enviroments
-------------------------------

Ubuntu and Debian packages
^^^^^^^^^^^^^^^^^^^^^^^^^^

The following steps describe a command-line approach, but any graphic package manager can be used instead.

Add the following to apt sources list
"""""""""""""""""""""""""""""""""""""

As root, append one of the following to */etc/apt/sources.list*:

* Debian Sid (kamaki 0.6.2)::

    deb http://apt.dev.grnet.gr/ sid main

* Debian Stable (kamaki 0.6.1)::

    deb http://apt.dev.grnet.gr/ squeeze main
    deb http://apt2.dev.grnet.gr stable/

* Ubuntu (kamaki 0.6.1)::

    deb http://apt.dev.grnet.gr/ precise main


Update
""""""

.. note:: make sure the GPG public key for the GRNET dev team is added:

    .. code-block:: console

        $ curl https://dev.grnet.gr/files/apt-grnetdev.pub|apt-key add -

    otherwise *apt-get update* will produce GPG warnings.

.. code-block:: console

    $ sudo apt-get update


Install kamaki
""""""""""""""

.. note:: **versions 0.6.0 - 0.6.1:**

    The *snf-common* package (available at synnefo apt repository) will be automatically installed as a dependency.

.. note:: **versions 0.6.2 and on:**

    Since version 0.6.2, *objpool* replaces *snf-common*. The objpool package is also available at synnefo repository and is automatically installed as a dependency. The *snf-common* dependency is removed.

.. code-block:: console

    $ sudo apt-get install kamaki

Install ansicolors and/or progress (Optional)
"""""""""""""""""""""""""""""""""""""""""""""

.. code-block:: console

    $ sudo apt-get install python-ansicolors
    $ sudo apt-get install python-progress

.. _installing-from-source-ref:

Installing from source (git repos.)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Requirements
""""""""""""

Essential:

 * Python 2.6 or better [http://www.python.org]
 * Python setuptools [http://pypi.python.org/pypi/setuptools]

Optional:

 * VirtualEnv (python-virtualenv) [http://www.virtualenv.org]

Setup a virtual enviroment (optional)
"""""""""""""""""""""""""""""""""""""

With virtualenv users can setup kamaki and synnefo services in a sandbox environment.

.. code-block:: console

    $ virtualenv kamaki-env
    $ source kamaki-env/bin/activate

A more detailed example of using virtual env can be found at the `snf-image-creator setup guide <http://docs.dev.grnet.gr/snf-image-creator/latest/install.html#python-virtual-environment>`_

Install objpool (was: snf-common)
"""""""""""""""""""""""""""""""""

.. note:: **versions 0.6.0 - 0.6.1**

    Package snf-common is part of the synnefo project and used to be a kamaki dependency in versions from 0.6.0 to 0.6.1 to provide a connection pooling mechanism. Users who still run 0.6.0 or 0.6.1 may need to manually install the snf-common package:

    .. code-block:: console

        $ git clone http://code.grnet.gr/git/synnefo
        $ cd synnefo/snf-common
        $ ./setup build install
        $ cd -

**Version 0.6.2 and on:**

Since 0.6.2, kamaki is based on objpool (hence the snf-common dependency is now obsolete). The objpool package is easy to install from source, even on windows platforms:

.. code-block:: console

    $ git clone http://code.grnet.gr/git/objpool
    $ cd objpool
    $ ./setup build install
    $ cd -

Install kamaki
""""""""""""""

.. code-block:: console

    $ git clone http://code.grnet.gr/git/kamaki
    $ cd kamaki
    $ ./setup build install

Install progress and/or ansicolors (optional)
"""""""""""""""""""""""""""""""""""""""""""""

progress: command-line progress bars (in some commands)

ansicolors: color kamaki output (can switched on and off in `setup <setup.html>`_)

.. code-block:: console

    $ pip install progress
    $ pip install ansicolors

Mac OS X
--------

Kamaki can be installed on Mac OS X systems from source, by following the steps at :ref:`installing-from-source-ref`.

Windows
-------

Since version 0.6.2 kamaki can run on Windows, either on standard Windows console, or inside an improved command line shell. The present guide presents a tested method for using kamaki in windows

Requirements
^^^^^^^^^^^^

* Python 2.7 or better (`Official versions <http://www.python.org/getit>`_)

* Git (download `windows version <http://git-scm.com/download/win>`_)

* Setuptools (`Official versions and workarounds <http://pypi.python.org/pypi/setuptools>`_)

Installation from source
^^^^^^^^^^^^^^^^^^^^^^^^

Install python
""""""""""""""

Download and run the Windows installer from `here <http://www.python.org/getit>`_

Users should pick the installer that fits their windows version and architecture.

Add python to windows path
""""""""""""""""""""""""""

The following will allow users to run python and python scripts from command line.

* Select **System** from the Control Panel, select the **Advanced** tab, the **Environment Variables** button and then find the **PATH** (user or system) and **edit**

* Without removing existing values, append the following to PATH::

    C:\Python;C:\Python\Scripts

.. note:: Path values are separated by semicolons

.. warning:: C:\\Python should be replaced with the actual python path in the system, e.g. C:\\Python27

Install setuptools
""""""""""""""""""

According to the corresponding `python org page <http://pypi.python.org/pypi/setuptools>`_, the setuptools installer doesn't currently work on 64bit machines.

* Users with 32-bit operating systems should download and run the graphic installer

* Users with 64-bit machines should download the `ez_setup.py <http://peak.telecommunity.com/dist/ez_setup.py>`_ script and install it from a command shell. In the following example, the script was downloaded at C:\\Downloads::

    C:\> cd Downloads
    C:\Downloads\> python ez_setup.py
    ...
    Installation finished
    C:\Downloads\>

Install GIT
"""""""""""

`Download GIT <http://git-scm.com/download/win>`_ and run the graphic installer. During the installation, users will be able to modify some installation options. The present guide is tested with the default selections.

After the installation is completed, a GIT standalone shell will be installed (a desktop shortcut is created, by default). Users are advised to run kamaki through this shell.

Install kamaki
""""""""""""""

* Run the GIT standalone shell

* Enter the location where kamaki will be installed, e.g. **C:\\**

    .. code-block:: console

        $ cd /c/

* Download source from GRNET repository

    .. code-block:: console

        $ git clone http://code.grnet.gr/git/kamaki
        Cloning into 'kamaki'...
        Receiving objects: ...
        Resolving Deltas: ...

* Enter source and install kamaki

    .. code-block:: console

        $ cd kamaki
        $ python setup.py install
        running install
        ...
        Finished processing dependencies for kamaki==0.6.2

.. warning:: kamaki version should be 0.6.2 or better, otherwise it will not function. Users can test that by running::

    $ kamaki --version
