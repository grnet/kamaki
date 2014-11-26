.. _clients-ssl:

SSL authentication
==================

Kamaki supports SSL authenticated connections since version 0.13.

In order to establish secure connections, the https connection module uses a CA
certificates file (see the discussion on
`Certificates <https://docs.python.org/2/library/ssl.html#ssl-certificates>`_
at docs.python.org, for more information).

The CA certificates file location depends on the platform (e.g.,
`/etc/ssl/certs/ca-certifications.crt` on Debian Linux), but developers can
also `provide a custom path <#set-ca-certificates-path>`_.

If the CA certificates path (a) is not set, (b) the file is invalid or (c) the
server fails to authenticate against it, a KamakiSSLError ensues. Developers
can `deactivate SSL errors <#ignore-ssl-errors>`_ and connect insecurely
instead.

Set CA certificates path
------------------------

To set the CA certificates path for all connections, use the following piece of
code before any kamaki clients are initialized.

.. code-block:: python

    from kamaki.clients.utils import https

    https.patch_with_certs(CA_CERTS_PATH)

Ignore SSL Errors
-----------------

.. code-block:: python

    from kamaki.clients.utils import https

    https.patch_ignore_ssl()

.. note:: When the connection module is instructed not to use SSL, it won't
    attempt to connect securely, even if a certificate is provided.

System CA certificates
----------------------

The vast majority of systems is equipped with a CA certificates bundle. The
location of the file may be different across platforms.

Some copies of kamaki are packaged for specific operating systems, while others
are system-ignorant (i.e., installed through pypi, cloned from a GitHub
repository or installed from source code).

If a kamaki package is system-aware, the typical CA certifications path for the
system is set automatically when a kamaki client is initialized.

If the copy is system-ignorant, the caller has to
`provide a CA certificates path <#set-ca-certificates-path>`_.

To check if kamaki is equipped with a default path:

.. code-block:: python

    from kamaki import defaults

    assert defaults.CACERTS_DEFAULT_PATH, 'No default CA certificates'

CA certificates path from config
--------------------------------

The following concerns developers who have set a CA certificates path in kamaki
config. To check if kamaki config is aware of a CA path:

.. code-block:: console

    $ kamaki config get ca_certs

To extract the CA certificates path from config:

.. code-block:: python

    from kamaki.cli import config

    cnf = config.Config()
    ca_certs = cnf.get('global', 'ca_certs')

.. note:: If the configuration file does not contain a ca_certs field, config
    returns the value of CACERTS_DEFAULT_PATH from "kamaki.defaults".

Building packages with SSL support
----------------------------------

To build a kamaki package with SSL support, maintainers must explicitly set the
system provided CA certificates path of the target system to
CACERTS_DEFAULT_PATH in "kamaki.defaults" module.

The purpose of "kamaki.defaults" is to let package maintainers set constants,
the values of which are used at runtime.

In the following example, set the CA certificates path for a Debian system.

.. code-block:: console

    $ tar xvfz kamaki.tar.gz
    ...
    $ echo 'CACERTS_DEFAULT_PATH = /etc/ssl/certs/ca-certificates.crt' \
      >> kamaki/kamaki/defaults.py

.. warning:: editing the `kamaki/kamaki/defaults.py` file should be avoided.
    Maintainers should rather append their settings (in valid python code) at
    the end of the file.

The typical paths for CA certificates differ from system to system. Some of
them are listed bellow::

    *Debian / Ubuntu / Gentoo / Arch*
    `/etc/ssl/certs/ca-certificates.crt`

    *Fedora / RedHat*
    `/etc/pki/tls/certs/ca-bundle.crt`

    *OpenSuse*
    `/etc/ssl/ca-bundle.pem`
