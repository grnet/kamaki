Networks
========

Users can create private networks to connect Virtual Machines, and can also
manage network-related objects and properties e.i., connection to public
networks, IPs and subnets.

In the following we assume that there are two active virtual servers (ids 141
and 142) connected to one public network with id 1 (default set up).

.. code-block:: console

    $ kamaki server info 141 --nics
    10
        firewallProfile: DISABLED
        ipv4:            10.0.0.1
        ipv6:            None
        mac_address:     aa:00:00:23:0d:59
        network_id:      1
    $ kamaki server info 142 --nics
    20
        firewallProfile: DISABLED
        ipv4:            10.0.0.3
        ipv6:            None
        mac_address:     aa:00:00:70:21:65
        network_id:      1

Let's load kamaki for networks and have a look at the current network state. We
expect to find at least one public network (id: 1)

.. code-block:: console

    $ kamaki network list
    1 public_network

Create a private network
------------------------

The new network will be named 'My Private Net'

.. code-block:: console

    $ kamaki network create --name='My Private Net'
    attachments:
    cidr:        192.168.1.0/24
    cidr6:       None
    created:     2013-06-19T13:52:02.268886+00:00
    dhcp:        False
    gateway:     None
    gateway6:    None
    id:          3
    name:        My Private Net
    public:      False
    status:      ACTIVE
    tenant_id:   s0m3-u53r-1d
    type:        MAC_FILTERED
    updated:     2013-06-19T13:52:02.388779+00:00
    user_id:     s0m3-u53r-1d

Let's create two more networks, one for virtual server 141 and one for virtual
server 142

.. code-block:: console

    $ kamaki network create --name='For virtual server 141'
    ...
    id:         4
    ...
    $ kamaki network create --name='For virtual server 142'
    ...
    id:         5
    ...

Connect and disconnect
----------------------

Lets connect the networks to some virtual servers:

.. code-block:: console

    $ kamaki network connect 4 141
    $ kamaki network connect 5 142

.. note:: **network connect** is a shortcut for **port create**:

    .. code-block:: console

        $ kamaki port create --network-id=4 --device-id=141
        $ kamaki port create --network-id=5 --device-id=142

Now, let's check the current network state. We expect to see the servers
connected to networks with ids 4 and 5, but not 3.

.. code-block:: console

    $ kamaki network list -l
    1 public_network
     attachments:
                10
                . . . . . . .
                20
     cidr:        10.0.0.0/24
     cidr6:       None
     created:     2013-05-29T17:30:03.040929+00:00
     dhcp:        True
     gateway:     10.0.0.254
     gateway6:    None
     public:      True
     status:      ACTIVE
     tenant_id:   None
     type:        CUSTOM
     updated:     2013-06-19T13:36:51.932214+00:00
     user_id:     None
    3 My Private Net
     attachments:
     cidr:        192.168.1.0/24
     cidr6:       None
     created:     2013-06-19T13:52:02.268886+00:00
     dhcp:        False
     gateway:     None
     gateway6:    None
     public:      False
     status:      ACTIVE
     tenant_id:   s0m3-u53r-1d
     type:        MAC_FILTERED
     updated:     2013-06-19T13:54:57.672744+00:00
     user_id:     s0m3-u53r-1d
    4 For virtual server 141
     attachments:
                11
     cidr:        192.168.2.0/24
     cidr6:       None
     created:     2013-06-19T13:53:02.268886+00:00
     dhcp:        False
     gateway:     None
     gateway6:    None
     public:      False
     status:      ACTIVE
     tenant_id:   s0m3-u53r-1d
     type:        MAC_FILTERED
     updated:     2013-06-19T13:54:57.672744+00:00
     user_id:     s0m3-u53r-1d
    5 For virtual server 142
     attachments:
                12
     cidr:        192.168.3.0/24
     cidr6:       None
     created:     2013-06-19T13:54:02.268886+00:00
     dhcp:        False
     gateway:     None
     gateway6:    None
     public:      False
     status:      ACTIVE
     tenant_id:   s0m3-u53r-1d
     type:        MAC_FILTERED
     updated:     2013-06-19T13:54:57.672744+00:00
     user_id:     s0m3-u53r-1d
    $ kamaki network

It is time to make a meaningful connection: connect two servers to a private
network

.. code-block:: console

    $ kamaki network connect 141 3
    $ kamaki network connect 142 3

Now the servers can communicate with each other through their shared private
network. Let's see the network details to confirm that

.. code-block:: console

    $ kamaki network info 3
    attachments:
                12
                . . . . . . .
                22
    cidr:        192.168.1.0/24
    cidr6:       None
    created:     2013-06-19T13:52:02.268886+00:00
    dhcp:        False
    gateway:     None
    gateway6:    None
    name:        My Private Net
    public:      False
    status:      ACTIVE
    tenant_id:   s0m3-u53r-1d
    type:        MAC_FILTERED
    updated:     2013-06-19T13:54:57.672744+00:00
    user_id:     s0m3-u53r-1d

Destroy a private network
-------------------------

Attempt to destroy the public network

.. code-block:: console

    $ kamaki network delete 1
    (403) Network with id 1 is in use
    |  FORBIDDEN forbidden (Can not delete the public network.)

.. warning:: Public networks cannot be destroyed

Attempt to destroy the `For virtual server 141` network

.. code-block:: console

    $ kamaki network delete 4
    (403) Network with id 4 is in use

The attached virtual servers should be disconnected first (recall that the
11 connects network with id 4 to virtual server with id 141)

.. code-block:: console

    $ kamaki network disconnect 4 141
    $ kamaki network delete 4

.. note:: **network disconnect** is a shortcut for **port delete**

    .. code-block:: console

        $ kamaki port delete 11
        $ kamaki network delete 4

Attempt to delete the common network, after disconnecting the respective ports
(12, 22):

.. code-block:: console

    $ kamaki port delete 22
    $ kamaki port delete 12
    $ kamaki network delete 3
