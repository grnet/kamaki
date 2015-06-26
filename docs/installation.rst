Installation
============

This guide describes the standard installation process for kamaki, with the
aspiration of covering as much cases as possible. Although kamaki was initially
targeted to Linux/Unix-like users, it is quite straightforward to install and
have it up and running in all platforms running Python 2.6 or 2.7.


* Kamaki repository: `http://github.com/grnet/kamaki <http://github.com/grnet/kamaki>`_

* Kamaki at PyPI: `http://pypi.python.org/pypi/kamaki <https://pypi.python.org/pypi/kamaki>`_

* Synnefo APT repositories: `http://apt.dev.grnet.gr <http://apt.dev.grnet.gr>`_

Linux and Unix-like environments
--------------------------------

Debian
^^^^^^

For Debian 8.0 (jessie):

* As root, append the following to */etc/apt/sources.list* ::

    deb http://apt.dev.grnet.gr jessie/

* Make sure the GPG public key for the Synnefo repository is added:

    .. code-block:: console

        # curl https://dev.grnet.gr/files/apt-grnetdev.pub|apt-key add -

    otherwise *apt-get update* will produce GPG warnings.

* Update and install:

    .. code-block:: console

        # apt-get update
        # apt-get install kamaki

Ubuntu
^^^^^^

For Ubuntu 12.04 LTS and 14.04 LTS:

.. code-block:: console

    $ sudo apt-get install python-software-properties
    $ sudo add-apt-repository ppa:grnet/synnefo
    $ sudo apt-get update
    $ sudo apt-get install kamaki

Fedora
^^^^^^

For Fedora 21:

.. code-block:: console

    # cd /etc/yum.repos.d
    # wget http://download.opensuse.org/repositories/home:/GRNET:/synnefo/Fedora_21/home:GRNET:synnefo.repo
    # yum install kamaki

CentOS
^^^^^^

For CentOS 7:

.. code-block:: console

    # cd /etc/yum.repos.d
    # wget http://download.opensuse.org/repositories/home:/GRNET:/synnefo/CentOS_7/home:GRNET:synnefo.repo
    # yum install kamaki

OpenSUSE
^^^^^^^^

For OpenSUSE 13.2:

.. code-block:: console

    # zypper ar -f http://download.opensuse.org/repositories/home:/GRNET:/synnefo/openSUSE_13.2/home:GRNET:synnefo.repo
    # zypper in kamaki


.. _installing-from-pypi-ref:


Enabling terminal colors (optional but recommended)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The python ansicolors library enables colorful terminal outputs. To
install it under Debian use the following command as root:

.. code-block:: console

    # apt-get install python-ansicolors

After the installation, tell kamaki to use the feature by executing:

.. code-block:: console

    $ kamaki config set colors on

Adding support for unit tests (developers only)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To make the unit tests work, install the python mock library. Under Debian you
can do this by executing the following command as root:

.. code-block:: console

    # apt-get install python-mock


Installing from pypi
--------------------

Requirements:

 * Python 2.7 [http://www.python.org]
 * Python setuptools [http://pypi.python.org/pypi/setuptools]

Installation:

.. code-block:: console

    $ pip install kamaki

Optional packages:
The ansicolors package enables terminal output coloring. The mock package
allows unit testing while hacking the code.

.. code-block:: console

    $ pip install ansicolors
    $ pip install mock

Mac OS X
--------

Kamaki can be installed on Mac OS X systems, by following the steps
at :ref:`installing-from-pypi-ref`.

Windows
-------

Kamaki can be installed on Windows by following the pypi method. Installing the
requirements is a bit different than in other systems. 

**Requirements**

* Python 2.7 (`Official versions <http://www.python.org/download>`_)

* Setuptools (`Official versions and workarounds <http://pypi.python.org/pypi/setuptools>`_)

Install Python
^^^^^^^^^^^^^^

.. note:: Skip this step if python 2.7 is already installed

Download and run the Windows installer from
`the download page <http://www.python.org/download>`_
pick the one that fits your windows version and architecture.

**Add Python to windows path**

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

Install Setuptools
^^^^^^^^^^^^^^^^^^

.. note:: Skip this step if setuptools are already installed

See `here <http://pypi.python.org/pypi/setuptools>`_ for installation
instructions.

.. note:: Users with 64-bit platforms should download the
    `ez_setup.py <https://bootstrap.pypa.io/ez_setup.py>`_ script and install
    it from a command shell. In the following example, the script was
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
