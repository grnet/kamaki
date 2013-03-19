Installation
============

This guide describes the standard installation process for kamaki, with the aspiration of covering as much cases as possible. Although kamaki was initially targeted to advanced Linux/Unix-like users, it should be quite straightforward to install and have it up and running in most popular platforms.


* Kamaki repository: `http://code.grnet.gr/git/kamaki <http://code.grnet.gr/git/kamaki>`_

* Kamaki at pypi: `http://pypi.python.org/pypi/kamaki <https://pypi.python.org/pypi/kamaki>`_

* Synnefo Linux packages: `http://apt2.dev.grnet.gr <http://apt2.dev.grnet.gr>`_

Linux and Unix-like enviroments
-------------------------------

Debian:
^^^^^^^

The following steps describe a command-line approach, but any graphic package manager can be used instead.

* As root, append the following to */etc/apt/sources.list* ::

    deb http://apt.dev.grnet.gr/ squeeze main
    deb http://apt2.dev.grnet.gr stable/

* Make sure the GPG public key for the GRNET dev team is added:

    .. code-block:: console

        $ sudo curl https://dev.grnet.gr/files/apt-grnetdev.pub|apt-key add -

    otherwise *apt-get update* will produce GPG warnings.

* Update the Debian sources:

    .. code-block:: console

        $ sudo apt-get update

* Install kamaki:

    .. code-block:: console

        $ sudo apt-get install kamaki

Ubuntu
^^^^^^

The following steps describe a command-line approach, but any graphic package manager can be used instead.

* Let ppa take care of the repository configuration:

    .. code-block:: console

        $ sudo apt-get install python-software-properties
        $ sudo add-apt-repository ppa:grnet/synnefo

* Update the Debian sources:

    .. code-block:: console

        $ sudo apt-get update

* Install kamaki:

    .. code-block:: console

        $ sudo apt-get install kamaki

Install ansicolors and/or progress (Optional but recommended)
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

.. code-block:: console

    $ sudo apt-get install python-ansicolors
    $ sudo apt-get install python-progress

.. _installing-from-pypi-ref:

Installing from pypi
^^^^^^^^^^^^^^^^^^^^

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

Install kamaki
""""""""""""""

.. code-block:: console

    $ pip install kamaki

Install ansicolors / progress
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Packages **ansicolors** and **progress** are not required for running kamaki, but
they are recommended as a user experience improvement. In specific, ansicolors
adds colors to kamaki responses and progress adds progressbars to the commands
that can make use of it (*/store download*, */store upload*, */server wait* etc.)

Debian and Ubuntu
"""""""""""""""""

Follow the `Debian <#debian>`_ or `Ubuntu <#ubuntu>`_ installation procedure described earlier
and then type:

.. code-block:: console

    #For ansicolors
    $ sudo apt-get install python-ansicolors

    # For progress
    $ sudo apt-get install python-progress

From source
"""""""""""

If setuptools is not installed, `install them <http://pypi.python.org/pypi/setuptools>`_ and then type:

.. code-block:: console

    #For ansicolors
    $ pip install ansicolors

    #For progress
    $ pip install progress

Mac OS X
--------

Kamaki can be installed on Mac OS X systems from source, by following the steps at :ref:`installing-from-pypi-ref`.

Windows
-------

Kamaki can be installed on Windows by following the pypi method. Installing the requirements is a bit different than in other systems. 

The full process is detailed in the following:

Requirements
^^^^^^^^^^^^

* Python 2.7 or better (`Official versions <http://www.python.org/getit>`_)

* Setuptools (`Official versions and workarounds <http://pypi.python.org/pypi/setuptools>`_)

Users who have already set up python and setuptools (e.g. for another project) may skip python and / or setup tools installation.

Install python
^^^^^^^^^^^^^^

Download and run the Windows installer from `here <http://www.python.org/getit>`_

Users should pick the installer that fits their windows version and architecture.

Add python to windows path
^^^^^^^^^^^^^^^^^^^^^^^^^^

The following will allow users to run python and python scripts from command line.

* Select **System** from the Control Panel, select the **Advanced** tab, the **Environment Variables** button and then find the **PATH** (user or system) and **edit**

* Without removing existing values, append the following to PATH::

    C:\Python;C:\Python\Scripts

.. note:: Path values are separated by semicolons

.. warning:: C:\\Python should be replaced with the actual python path in the system, e.g. C:\\Python27

Install setuptools
^^^^^^^^^^^^^^^^^^

According to the corresponding `python org page <http://pypi.python.org/pypi/setuptools>`_, the setuptools installer doesn't currently work on 64bit machines.

* Users with 32-bit operating systems should download and run the graphic installer

* Users with 64-bit machines should download the `ez_setup.py <http://peak.telecommunity.com/dist/ez_setup.py>`_ script and install it from a command shell. In the following example, the script was downloaded at C:\\Downloads::

    C:\> cd Downloads
    C:\Downloads\> python ez_setup.py
    ...
    Installation finished
    C:\Downloads\>

Install kamaki
^^^^^^^^^^^^^^

.. code-block:: console

    $ easy_setup kamaki

Install progress (optional)
^^^^^^^^^^^^^^^^^^^^^^^^^^^

progress: command-line progress bars (in some commands)

.. code-block:: console

    $ easy_setup progress

