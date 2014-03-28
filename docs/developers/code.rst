APIs code
=========

.. the-cli-api-ref

Command Specifications
----------------------

astakos
^^^^^^^
Features: user, project, quota, resource, commission, endpoint, service

.. automodule:: kamaki.cli.cmds.astakos
    :members:
    :undoc-members:

cyclades
^^^^^^^^

Features server, flavor

.. automodule:: kamaki.cli.cmds.cyclades
    :members:
    :undoc-members:

pithos
^^^^^^

Features file, container, sharer, group

.. automodule:: kamaki.cli.cmds.pithos
    :members:
    :undoc-members:

image
^^^^^

Features (image, imagecompute)

.. automodule:: kamaki.cli.cmds.image
    :members:
    :undoc-members:


network
^^^^^^^

Features network, port, subnet, ip

.. automodule:: kamaki.cli.cmds.network
    :members:
    :undoc-members:

Kamaki commands
^^^^^^^^^^^^^^^

config
""""""

.. automodule:: kamaki.cli.cmds.config
    :members:
    :undoc-members:


errors
^^^^^^

.. automodule:: kamaki.cli.cmds.errors
    :members:
    :show-inheritance:
    :undoc-members:

.. _the-client-api-ref:

The clients API
---------------

compute
^^^^^^^

.. automodule:: kamaki.clients.compute.rest_api
    :members:
    :show-inheritance:
    :undoc-members:

.. automodule:: kamaki.clients.compute
    :members:
    :show-inheritance:
    :undoc-members:


cyclades
^^^^^^^^

.. automodule:: kamaki.clients.cyclades.rest_api
    :members:
    :show-inheritance:
    :undoc-members:

.. automodule:: kamaki.clients.cyclades
    :members:
    :show-inheritance:
    :undoc-members:


storage
^^^^^^^

.. automodule:: kamaki.clients.storage
    :members:
    :show-inheritance:
    :undoc-members:

pithos
^^^^^^

.. automodule:: kamaki.clients.pithos.rest_api
    :members:
    :show-inheritance:
    :undoc-members:

.. automodule:: kamaki.clients.pithos
    :members:
    :show-inheritance:
    :undoc-members:

image
^^^^^

.. automodule:: kamaki.clients.image
    :members:
    :show-inheritance:
    :undoc-members:

network
^^^^^^^

.. warning:: For synnefo, the suggested network implementation is in
    kamaki.clients.cyclades.CycladesNetworkClient extension

.. automodule:: kamaki.clients.network
    :members:
    :show-inheritance:
    :undoc-members:

astakos
^^^^^^^

.. automodule:: kamaki.clients.astakos
    :members:
    :show-inheritance:
    :undoc-members:
