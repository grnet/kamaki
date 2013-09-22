Networks
========

Users can create private networks between Virtual Machines.

In the following we assume that there are two active VMs (ids 141 and 142)
connected to one public network with id 1 (default set up).

.. code-block:: console

    $ kamaki server addr 141
    nic-141-0
        firewallProfile: DISABLED
        ipv4:            10.0.0.1
        ipv6:            None
        mac_address:     aa:00:00:23:0d:59
        network_id:      1
    $ kamaki server addr 142
    nic-142-0
        firewallProfile: DISABLED
        ipv4:            10.0.0.3
        ipv6:            None
        mac_address:     aa:00:00:70:21:65
        network_id:      1
    $

.. note:: In Synnefo, each VM connects to a network through a NIC. The id of a
    nic is nic-<server id>-<increment> by convention.

Let's load kamaki for networks and have a look at the current network state. We
expect to find at least one public network (id: 1)

.. code-block:: console

    $ kamaki
    kamaki v0.9 - Interactive Shell

    /exit       terminate kamaki
    exit or ^D  exit context
    ? or help   available commands
    ?command    help on command
    !<command>  execute OS shell command

    [kamaki]: network
    [network]: list
    1 public_network
    [network]:

Create a private network
------------------------

The new network will be named 'My Private Net'

.. code-block:: console

    [network]: create 'My Private Net'
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
    [network]:

Let's create two more networks, one for VM 141 and one for Vm 142

.. code-block:: console

    [network]: create 'For VM 141'
    ...
    id:         4
    ...
    [network]: create 'For VM 142'
    ...
    id:         5
    ...
    [network]:

Connect and disconnect
----------------------

To make a points, the networks should be connected to their respecting VMs

.. code-block:: console

    [network]: connect 141 4
    [network]: connect 142 5
    [network]:

Now, let's check the current network state. We expect to see the servers
connected to netowkrd with ids 4 and 5, but not 3.

.. code-block:: console

    [network]: list -l
    1 public_network
     attachments:
                nic-141-0
                . . . . . . .
                nic-142-0
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
    4 For VM 141
     attachments:
                nic-141-1
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
    5 For VM 142
     attachments:
                nic-141-2
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
    [network]:

It is time to make meaningful connections: connect two servers to a private
network

.. code-block:: console

    [network]: connect 141 3
    [network]: connect 142 3
    [network]:

Now the servers can communicate with eachother through their shared private
network. Let's see the network details to confirm that

.. code-block:: console

    [network]: info 3
    attachments:
                nic-141-2
                . . . . . . .
                nic-142-2
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
    [network]:

Destroy a private network
-------------------------

Attempt to destroy the public network

.. code-block:: console

    [network]: delete 1
    (403) Network with id 1 is in use
    |  FORBIDDEN forbidden (Can not delete the public network.)
    [kamaki]:

.. warning:: Public networks cannot be destroyed in Synnefo

Attempt to destroy the useless `For VM 141` network

.. code-block:: console

    [network]: delete 4
    (403) Network with id 4 is in use
    [network]:

The attached VMs should be disconnected first (recall that the nic-141-1
connects network with id 4 to VM with id 141)

.. code-block:: console

    [network]: disconnect nic-141-1
    [network]: delete 4
    [network]:

Attempt to delete the common network. Now we know that we should disconnect the
respective nics (nic-141-2, nic-142-2) first

.. code-block:: console

    [network]: disconnect nic-142-2
    [network]: disconnect nic-141-2
    (404) No nic nic-141-2 on server(VM) with id 141
    |  * check server(VM) with id 142: /server info 141
    |  * list nics for server(VM) with id 141:
    |        /server addr 141
    |  Network Interface nic-141-2 not found on server 141
    [network]:

Strangely, kamaki did not find any nic-141-2 nics. Why?

Answer: A listing of the 141 nics shows that the network connection to network
with id 3 is now renamed as nic-141-1

.. code-block:: console

    [network]: /server addr 141
    nic-142-0
     firewallProfile: DISABLED
     ipv4:            10.0.0.1
     ipv6:            None
     mac_address:     aa:00:00:23:0d:59
     network_id:      1
    nic-142-1
     firewallProfile: DISABLED
     ipv4:            192.168.1.0/24
     ipv6:            None
     mac_address:     aa:00:00:23:0d:60
     network_id:      1
     [network]:

.. warning:: Synnefo network server renames the nics of a VM whenever another
    nic is of the same server is deleted

Let's remove the correct nic, then, and check if any other nics are related to
the network with id 3.

.. code-block:: console

    [network]: delete nic-141-1
    [network]: info 3
    attachments:
    cidr:        192.168.1.0/24
    cidr6:       None
    ...
    [network]:

So, we are ready to destroy the network

.. code-block:: console

    [network]: delete 3
    [network]:
