Connection
==========

An http connection package with connection pooling.

Since version 0.6 it is safe to use threaded connections.

The Connection package uses httplib, standard python threads and a connection pooling mechanism.

.. note:: in versions 0.6.0 to 0.6.1 the GRNET Synnefo *snf-common* package is used for its connection pooling module. Since version 0.6.2 the underlying pooling mechanism is packed in a new GRNET package called *objpool*, which is now used instead of snf-common.

.. automodule:: kamaki.clients.connection
    :members:
    :show-inheritance:
    :undoc-members: