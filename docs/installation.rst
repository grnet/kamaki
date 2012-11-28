Installation
============

This guide describes the standard installation process for kamaki, with the aspiration of covering as much cases as possible. Although kamaki was initially targeted to advanced Linux/Unix-like users, it should be quite straightforward to install and have it up and running in most popular platforms.


* Kamaki repository: `http://code.grnet.gr/git/kamaki <http://code.grnet.gr/git/kamaki>`_

* Synnefo Linux packages: `http://apt.dev.grnet.gr <http://apt.dev.grnet.gr>`_

Linux and Unix-like enviroments
-------------------------------

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

1. Setup a virtual enviroment (optional)
""""""""""""""""""""""""""""""""""""""""

With virtualenv users can setup kamaki and synnefo services in a sandbox environment.

.. code-block:: console

    $ virtualenv kamaki-env

    $ source kamaki-env/bin/activate

A more detailed example of using virtual env can be found at the `snf-image-creator setup guide <http://docs.dev.grnet.gr/snf-image-creator/latest/install.html#python-virtual-environment>`_

2. Install snf-common
"""""""""""""""""""""

Package snf-common is part of the synnefo project and is a kamaki dependency since version 0.6.0.

.. code-block:: console

    $ git clone http://code.grnet.gr/git/synnefo

    $ cd synnefo/snf-common

    $ ./setup build install

    $ cd -

3. Install kamaki
"""""""""""""""""

.. code-block:: console

    $ git clone http://code.grnet.gr/git/kamaki

    $ cd kamaki

    $ ./setup build install

4. Install progress and/or ansicolors (optional)
""""""""""""""""""""""""""""""""""""""""""""""""

progress: command-line progress bars (in some commands)

ansicolors: color kamaki output (can switched on and off in `setup <setup.html>`_)

.. code-block:: console

    $ pip install progress

    $ pip install ansicolors

Ubuntu and Debian packages
^^^^^^^^^^^^^^^^^^^^^^^^^^

The following steps describe a command-line approach, but any graphic package manager can be used instead.

1. Add the following to apt sources list
""""""""""""""""""""""""""""""""""""""""

* Debian::

    deb http://apt.dev.grnet.gr/ sid main

* Ubuntu::

    deb http://apt.dev.grnet.gr/ precise main

2. Update
"""""""""

.. code-block:: console

    $ sudo apt-get update

.. note:: Safely ignore a signature verification error like the following, if it emerges:

    .. warning:: GPG error: http://apt.dev.grnet.gr precise/sid InRelease: The following signatures couldn't be verified because the public key is not available: NO_PUBKEY XXXXXXXX

3. Install kamaki
"""""""""""""""""

Since version 0.6.0, the package snf-common (available at synnefo apt repository) will be automatically installed as a dependency.

.. code-block:: console

    $ sudo apt-get install kamaki

4. Install ansicolors and/or progress (Optional)
""""""""""""""""""""""""""""""""""""""""""""""""

.. code-block:: console

    $ sudo apt-get install python-ansicolors

    $ sudo apt-get install python-progress

Mac OS X
--------

Kamaki can be installed on Mac OS X systems from source, by following the steps at :ref:`installing-from-source-ref`.

Windows
-------

It has proven possible (and not too tricky) to install kamaki on Windows console using some auxiliary applications, but Windows users are not the target audience for the time being.
