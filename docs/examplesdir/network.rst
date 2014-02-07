Networks
========

Users can create private networks to connect Virtual Machines, and can also
manage network-related objects and properties e.i., connection to public
networks, IPs and subnets.

In the following we assume that there are two active virtual servers (ids 141
and 142) connected to one public network with id 1 (default set up).

.. code-block:: console

    $ kamaki server list
     141 Server 1
     142 Server 1

A look at the current network state:

.. code-block:: console

    $ kamaki network list
    1 public_network

Create a private network
------------------------

The new network will be named 'My Private Net'

.. code-block:: console

    $ kamaki network create --name='My Private Net'
     id: 2
     status:      ACTIVE
     router:external: True
     user_id:     s0m3-u53r-1d
     updated:     2013-06-19T13:54:57.672744+00:00
     created:     2013-06-19T13:52:02.268886+00:00
     links: ...
     public:      False
     tenant_id:   s0m3-u53r-1d
     admin_state_up: True
     SNF:floating_ip_pool: False
     subnets:
     type:        MAC_FILTERED

Connect and disconnect
----------------------

Connect the network to the virtual servers:

.. code-block:: console

    $ kamaki network connect 2 --device-id=141 --device-id=142
     Creating a port to connect network 2 with device 141
     11
        status: BUILD
        network_id: 29729
        mac_address: None
        fixed_ips:
        device_id: 141
        ...
     Creating a port to connect network 2 with device 142
     12
        status: BUILD
        network_id: 2
        mac_address: None
        fixed_ips:
        device_id: 142
        ...

.. warning:: A port between a network and a server takes some time to be
    created. Use --wait to make "connect" wait for all ports to be created

.. note:: **network connect** is a shortcut for **port create**:

    .. code-block:: console

        $ kamaki port create --network-id=1 --device-id=141 --wait
        $ kamaki port create --network-id=1 --device-id=142 --wait

Check the current network state:

.. code-block:: console

    $ kamaki network list -l
    1 Public network
     status: ACTIVE
     router:external: True
     user_id: None
     updated: 2013-06-19T13:36:51.932214+00:00
     created: 2013-05-29T17:30:03.040929+00:00
     links: ...
     tenant_id: None
     admin_state_up: True
     SNF:floating_ip_pool: False
     public: True
     subnets:
        53
     type: IP_LESS_ROUTED
    2 My Private Net
     status:      ACTIVE
     router:external: True
     user_id:     s0m3-u53r-1d
     updated:     2013-06-19T13:54:57.672744+00:00
     created:     2013-06-19T13:52:02.268886+00:00
     links: ...
     public:      False
     tenant_id:   s0m3-u53r-1d
     admin_state_up: True
     SNF:floating_ip_pool: False
     subnets:
     type:        MAC_FILTERED

Now the servers can communicate with each other through their shared private
network.

Manage floating IPs
-------------------

A floating IP can be created (reserved from a pool) and attached to a device.

.. code-block:: console

    $ kamaki ip create --network-id=1
     instance_id: None
     deleted: False
     floating_network_id: 1
     fixed_ip_address: None
     floating_ip_address: 192.168.3.5
     port_id: None
     id: 8
    $ kamaki ip attach 8 --server-id=141 --wait
     13
        status: ACTIVE
        network_id: 1
        mac_address: None
        fixed_ips:
            subnet: 21
            ip_address: 192.168.3.5
        device_id: 141
        ...

.. note:: **ip attach** is also a shortcut for **port create** !!!

    .. code-block:: console

        ...
        $ kamaki port create \
          --network-id=1 --device-id=141 --ip-address=192.168.3.5 --wait

An attempt to attach a used IP to another virtual server, should fail:

.. code-block:: console

    $ kamaki ip attach 8 --server-id=142 --wait
     (409) IP address '192.168.3.5' is already in use

More than one IPs can be created and more than one can be attached on the same
virtual server.

.. code-block:: console

    $ kamaki ip create --network-id=1
     instance_id: None
     deleted: False
     floating_network_id: 1
     fixed_ip_address: None
     floating_ip_address: 192.168.3.5
     port_id: None
     id: 9
    $ kamaki ip attach 9 --server-id=141 --wait
     14
        status: ACTIVE
        network_id: 1
        mac_address: None
        fixed_ips:
            subnet: 22
            ip_address: 192.168.3.6
        device_id: 141
        ...

Since all connections exist as ports, we can monitor everything with "port"
commands:

.. code-block:: console

    $ kamaki port list -l
     11
        status: ACTIVE
        network_id: 2
        mac_address: None
        fixed_ips:
        device_id: 141
        ...
     12
        status: ACTIVE
        network_id: 2
        mac_address: None
        fixed_ips:
        device_id: 142
     13
        status: ACTIVE
        network_id: 1
        mac_address: None
        fixed_ips:
            subnet: 21
            ip_address: 192.168.3.5
        device_id: 141
        ...
     14
        status: ACTIVE
        network_id: 1
        mac_address: None
        fixed_ips:
            subnet: 22
            ip_address: 192.168.3.6
        device_id: 141
        ...

Virtual server 141 has two IPs while 142 has none. Detach 192.168.3.6 (id: 9)
and attach it to server 142:

.. code-block:: console

    $ detach 9 --wait
    $ attach 9 --server-id=142 --wait
     14
        status: ACTIVE
        network_id: 1
        mac_address: None
        fixed_ips:
            subnet: 22
            ip_address: 192.168.3.6
        device_id: 142
        ...

IP quota limits
---------------

It is always a good idea to check the resource quotas:

.. code-block:: console

    $ kamaki quota list
     cyclades.disk:
        usage: 80GiB
        limit: 500GiB
        pending: 0B
     cyclades.vm:
        usage: 2
        limit: 2
        pending: 0
     pithos.diskspace:
        usage: 1.43GiB
        limit: 20GiB
        pending: 0B
     cyclades.ram:
        usage: 9GiB
        limit: 40GiB
        pending: 0B
     cyclades.floating_ip:
        usage: 2
        limit: 3
        pending: 0
     cyclades.cpu:
        usage: 4
        limit: 8
        pending: 0
     cyclades.network.private:
        usage: 2
        limit: 5
        pending: 0

According to these results, there is only one IP left. We will attempt to
reserve two, and when we fail in the second, and then we will release the first

.. code-block:: console

    $ kamaki ip create --network-id=1
     instance_id: None
     deleted: False
     floating_network_id: 1
     fixed_ip_address: None
     floating_ip_address: 192.168.3.7
     port_id: None
     id: 10
    $ kamaki ip create --network-id=1
     (413) REQUEST ENTITY TOO LARGE
     |  Limit for resource 'Floating IP address' exceeded for your account.
     |  Available: 0, Requested: 1
    $ kamaki ip delete 10

Destroy a private network
-------------------------

Attempt to destroy the public network

.. code-block:: console

    $ kamaki network delete 1
    (403) Network with id 1 is in use
    |  FORBIDDEN forbidden (Can not delete the public network.)

.. warning:: Public networks cannot be destroyed with API calls

Attempt to destroy the private network

.. code-block:: console

    $ kamaki network delete 2
    (403) Network with id 2 is in use

The attached virtual servers should be disconnected first

.. code-block:: console

    $ kamaki network disconnect 2 --device-id=141 --device-id=142 --wait
    $ kamaki network delete 2

.. note:: **network disconnect** is a shortcut for **port delete**

    .. code-block:: console

        $ kamaki port delete 11 --wait
        $ kamaki port delete 12 --wait
        $ kamaki network delete 2
