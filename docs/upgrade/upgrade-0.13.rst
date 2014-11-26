Upgrade to v0.13
^^^^^^^^^^^^^^^^

.. warning:: kamaki-depended code or scripts may or may not break, depending
    on the system and installation details. To avoid that, read carefully the
    upgrade instructions bellow.

Secure connections
==================

Starting with version 0.13, kamaki supports secure connections with SSL
certificates. Although the CA certificates bundle file is set automatically in
some systems, most of the users will have to provide its location manually.
Alternatively, they can set kamaki to use insecure connections. The default
behavior, though, is that the CA bundle is required.

It is safe to upgrade kamaki **through the package management system** in::

    * Debian Wheezy

In other cases (e.g., other systems, installation through pipy), the code or
scripts may break.

Upgrade
=======

* Shell users should read :ref:`ssl-setup` in the setup section,  before
    upgrading to v0.13.

* Developers using the "kamaki.clients" library in their  programs are
    **required** to read :ref:`clients-ssl` before upgrading to v0.13.
