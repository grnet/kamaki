Installation
============

This guide describes the standard installation process for kamaki, with the aspiration of covering as much cases as possible. Although kamaki was initially targeted to advanced Linux/Unix-like users, it should be quite straightforward to install and have it up and running in most popular platforms.

* Kamaki repository: `http://code.grnet.gr/git/kamaki <http://code.grnet.gr/git/kamaki>`_

* Synnefo Linux packages: `http://apt.dev.grnet.gr <http://apt.dev.grnet.gr>`_

Linux and Unix-like enviroments
-------------------------------

Installing from source (git repos.)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Setup a virtual enviroment (optional)
"""""""""""""""""""""""""""""""""""""

.. code-block:: console

    $ virtualenv kamaki-env

    $ source kamaki-env/bin/activate

.. hint:: More about virtualenv: `<http://www.virtualenv.org>`_

Install snf-common from synnefo project (required since v0.6.1)
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

.. code-block:: console

    $ git clone http://code.grnet.gr/git/synnefo

    $ cd synnefo/snf-common

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

|Progress: Allows command-line progress bars in some commands
|Ansicolors: Colors at kamaki output (can switched on and off in `setup <setup.html>`_)

.. code-block:: console

    $ pip install progress

    $ pip install ansicolors

Ubuntu and Debian packages
^^^^^^^^^^^^^^^^^^^^^^^^^^

Mac OS
------

Windows
-------

Installing from source (git repos.)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
