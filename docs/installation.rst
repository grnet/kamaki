Installation
============

This guide describes the standard installation process for kamaki, with the
aspiration of covering as much cases as possible. Although kamaki was initially
targeted to Linux/Unix-like users, it is quite straightforward to install and
have it up and running in all platforms running Python 2.6 or 2.7.


* Kamaki repository: `http://code.grnet.gr/git/kamaki <http://code.grnet.gr/git/kamaki>`_

* Kamaki at pypi: `http://pypi.python.org/pypi/kamaki <https://pypi.python.org/pypi/kamaki>`_

* Synnefo Linux packages: `http://apt.dev.grnet.gr <http://apt.dev.grnet.gr>`_

Linux and Unix-like environments
--------------------------------

Debian:
^^^^^^^

The following steps describe a command-line approach, but any graphic package manager can be used instead.

* As root, append the following to */etc/apt/sources.list* ::

    deb http://apt.dev.grnet.gr wheezy/

.. warning:: Debian Squeeze users may replace "wheezy" with "squeeze"

* Make sure the GPG public key for the Synnefo repository is added:

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

The following steps describe a command-line approach, but any graphic package
manager can be used instead.

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

Install ansicolors (optional but recommended)
"""""""""""""""""""""""""""""""""""""""""""""

.. code-block:: console

    $ sudo apt-get install python-ansicolors

Install mock (for developers only)
""""""""""""""""""""""""""""""""""

.. code-block:: console

    $ sudo apt-get install python-mock

.. warning:: kamaki.clients unit-tests need python-mock 1.X or better. e.g.,::

    $ sudo apt-get install python-mock=1.0.1

.. hint:: To activate functional tests in kamaki enable the preconfigured
    *livetest* command group:

    .. code-block:: console

        $ kamaki config set livetest_cli livetest


.. _installing-from-pypi-ref:

Installing from pypi
^^^^^^^^^^^^^^^^^^^^

Requirements
""""""""""""

Essential:

 * Python 2.6 or 2.7 [http://www.python.org]
 * Python setuptools [http://pypi.python.org/pypi/setuptools]

Optional:

 * VirtualEnv (python-virtualenv) [http://www.virtualenv.org]

Setup a virtual enviroment (optional)
"""""""""""""""""""""""""""""""""""""

Use virtualenv to setup kamaki and Synnefo services in a sandbox environment.

.. code-block:: console

    $ virtualenv kamaki-env
    $ source kamaki-env/bin/activate

A more detailed example of using virtual env can be found at the 
`snf-image-creator setup guide <http://www.synnefo.org/docs/snf-image-creator/latest/install.html#python-virtual-environment>`_

Install kamaki
""""""""""""""

.. code-block:: console

    $ pip install kamaki

Install ansicolors
""""""""""""""""""

The **ansicolors** package is not required for running kamaki, but it is
recommended as a user experience improvement. In specific, ansicolors
adds colors to kamaki responses.

.. code-block:: console

    $ pip install ansicolors

Install mock (developers only)
""""""""""""""""""""""""""""""

The **mock** package is needed for running the prepared unit-tests in the
kamaki.clients package. This feature is useful when extending / debugging
kamaki functionality and is aimed to kamaki developers and contributors.
Therefore, users can enjoy the full kamaki user experience without installing
mock.

.. code-block:: console

    $ pip install mock

.. warning:: mock version >= 1.X

.. hint:: To activate functional tests in kamaki. enable the preconfigured
    *livetest* command group:

    .. code-block:: console

        $ kamaki config set livetest_cli livetest


Mac OS X
--------

Kamaki can be installed on Mac OS X systems, by following the steps
at :ref:`installing-from-pypi-ref`.

Windows
-------

Kamaki can be installed on Windows by following the pypi method. Installing the
requirements is a bit different than in other systems. 

The full process is detailed in the following:

Requirements
^^^^^^^^^^^^

* Python 2.7 (`Official versions <http://www.python.org/getit>`_)

* Setuptools (`Official versions and workarounds <http://pypi.python.org/pypi/setuptools>`_)

Users who have already set up python and setuptools (e.g., for
another project) may skip Python and / or setuptools installation.

Install Python
^^^^^^^^^^^^^^

Download and run the Windows installer from
`here <http://www.python.org/getit>`_

Users should pick the installer that fits their windows version and machine
architecture.

Add Python to windows path
^^^^^^^^^^^^^^^^^^^^^^^^^^

The following will allow users to run Python and Python scripts from command
line.

* Select **System** from the Control Panel, select the **Advanced** tab, the
    **Environment Variables** button and then find the **PATH** (user or
    system) and **edit**

* Without removing existing values, append the following to PATH::

    ;C:\Python27;C:\Python27\Scripts

.. note:: Path values are separated by semicolons

.. warning:: In case of a different version, C:\\Python27 should be replaced
    with the actual python path in the system

Install setuptools
^^^^^^^^^^^^^^^^^^

According to the corresponding
`python org page <http://pypi.python.org/pypi/setuptools>`_, the setuptools
installer doesn't currently work on 64bit machines.

* Users with 32-bit platforms should download and run the graphic
    installer

* Users with 64-bit platforms should download the
    `ez_setup.py <http://peak.telecommunity.com/dist/ez_setup.py>`_ script and
    install it from a command shell. In the following example, the script was
    downloaded at C:\\Downloads::

        C:\> cd Downloads
        C:\Downloads\> python ez_setup.py
        ...
        Installation finished
        C:\Downloads\>

Install kamaki
^^^^^^^^^^^^^^

.. code-block:: console

    $ easy_install kamaki
