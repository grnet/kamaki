Creating Servers (Virtual Machines)
===================================

A `server` (also known as `virtual machine`), is created based on a registered
`image` and a hardware setup (also known as `flavor`).

Create a virtual server
-----------------------

List available flavors

.. code-block:: console

    $ kamaki flavor list -l
    1 C1R128D1drbd
        SNF:disk_template: drbd
        disk:              1
        id:                1
        links:
                href: https://example.com/cyclades/compute/v2.0/flavors/1
                rel:  bookmark
                . . . . . . .
                href: https://example.com/cyclades/compute/v2.0/flavors/1
                rel:  self
        name:              C1R128D1drbd
        ram:               128
        vcpus:             1
    2 C1R128D1plain
        SNF:disk_template: plain
        disk:              1
        id:                2
        links:
                href: https://example.com/cyclades/compute/v2.0/flavors/2
                rel:  bookmark
                . . . . . . .
                href: https://example.com/cyclades/compute/v2.0/flavors/2
                rel:  self
        name:             C1R128D1plain
        ram:              128
        vcpus:            1

List available images

.. code-block:: console

    $ kamaki image list
    f1r57-1m4g3-1d Debian Base Alpha
    53c0nd-1m4g3-1d Beta Debian Base

Pick the `C1R128D1drbd` (id: 1) flavor and the `Debian Base Alpha` (id:
f1r57-1m4g3-1d) image to create a new virtual server called 'My First Server'

.. code-block:: console

    $ kamaki server create --name='My First Server' --flavor-id=1 --image-id=f1r57-1m4g3-1d
    accessIPv4:
    accessIPv6:
    addresses:
    adminPass:       Y0uW0nt5eeMeAg4in
    attachments:
    config_drive:
    created:         2013-06-19T12:34:47.362078+00:00
    diagnostics:
    flavor:
            id:    1
    hostId:
    id:              141
    image:
            id:    f1r57-1m4g3-1d
    key_name:        None
    metadata:
                   os:    debian
                   users: root
    name:            My First Server
    progress:        0
    security_groups:
                      name: default
    status:          BUILD
    suspended:       False
    tenant_id:       s0m3-u53r-1d
    updated:         2013-06-19T12:34:48.512867+00:00
    user_id:         s0m3-u53r-1d

.. note:: The adminPass field is not stored anywhere, therefore users would
    rather write it down and change it the first time they use the virtual
    server

Wait for the virtual server with id 141 to build (optional)

.. code-block:: console

    $ kamaki server wait 141
    <bar showing build progress, until 100%>
    Server 141 is now in ACTIVE mode

Destroy the virtual server (wait is still optional)

.. code-block:: console

    $ kamaki server delete 141 --wait
    <bar showing destruction progress, until 100%>
    Server 141 is now in DELETED mode

Create Servers with networks
----------------------------

First, check the available IPs:

.. code-block:: console

    $ kamaki ip list
    42042
        instance_id: 424242
        floating_network_id: 1
        fixed_ip_address: None
        floating_ip_address: 123.456.78.90
        port_id: 24024

So, there is an ip (123.456.78.90) on network 1. We can use it:

.. code-block:: console

    $ kamaki server create --network=1,123.456.78.90 --name='Extrovert Server' --flavor-id=1 --image-id=f1r57-1m4g3-1d
    ...

Another case it the connection to a private network (so, no IP):

.. code-block:: console

    $ kamaki network list
    1   Public network
    7   A custom private network
    9   Another custom private network

    $ kamaki server create --network=7 --name='Introvert Server' --flavor-id=1 --image-id=f1r57-1m4g3-1d

.. note:: Multiple *- -network* args will create a corresponding number of
    connections (nics) to the specified networks.

.. note:: Ommiting *- -network* will let the cloud apply the default network
    policy. To create a server without any connections (nics), use the
    *- -no-network argument*


Inject ssh keys to a debian server
----------------------------------

Assume that the servers build from the image `Debian Base Alpha` accept ssh
connections. We need to build servers that can log us as root without a
password. This can be achieved if the `/root/.ssh/authorized_keys` file exists
and contains the public key of the current user.

Assume that the public key file of the current user is located at
`/home/someuser/.ssh/id_rsa.pub` . We need to inject this file as
`/root/.ssh/authorized_keys` while creating the virtual server.

Luckily, Synnefo fully supports the OpenStack suggestion for file injections on
virtual servers and kamaki features the **-p** argument (p stands for
`PERSONALITY` and is the term used in the respective
`respective OpenStack <http://docs.openstack.org/api/openstack-compute/2/content/CreateServers.html>`_ description).

The syntax of the -p argument is something called "the personality string"::

    -p <local file path>[,<remote path>[,<remote owner>[,<remote group>[,<mode>]]]]

    e.g.,

    -p /home/someuser/.ssh/id_rsa.pub,/root/.ssh/authorized_keys,root,root,0777

.. note:: In case of omitting an optional part of the personality string, the
    default behavior depends on the remote server, e.g., for a debian image we
    expect the file to have root ownership, if the ownership is not specified.

Create a virtual server while injecting current user public key to root account

.. code-block:: console

    $ kamaki server create --name='NoPassword Server' --flavor-id=1 --image-id=f1r57-1m4g3-1d \
        --network=1,123.456.78.90 \
        -p /home/someuser/.ssh/id_rsa.pub,/root/.ssh/authorized_keys

    accessIPv4:
    accessIPv6:
    addresses:
    adminPass:       Th1s1s4U5elessTh1ngN0w
    attachments:
    config_drive:
    created:         2013-06-19T12:34:47.362078+00:00
    diagnostics:
    flavor-id:    1
    hostId:
    id:              142
    image-id:     f1r57-1m4g3-1d
    key_name:        None
    metadata:
                    os:    debian
                    users: root
    name:           No Password Server
    progress:        0
    status:          BUILD
    suspended:       False
    tenant_id:       s0m3-u53r-1d
    updated:         2013-06-19T12:34:48.512867+00:00
    user_id:         s0m3-u53r-1d

When the server is ready, we can connect through the public network 1 and the
IP 123.456.78.90 :

.. code-block:: console

    $ ssh root@123.456.78.90
    Linux remote-virtual server-4241 2.6.32-5-amd64 #1 SMP XXXX x86_64

    The programs included with the Debian GNU/Linux system are free software;
    the exact distribution terms for each program are described in the
    individual files in /usr/share/doc/*/copyright.

    Debian GNU/Linux comes with ABSOLUTELY NO WARRANTY, to the extent
    permitted by applicable law.
    root@remote-virtual server-4241:~# ls -l .ssh/
    total 4
    -rw-r--r-- 1 root root 399 Jun 19 12:34 authorized_keys
    root@remote-virtual server-4241:~#

You can now log to your remote virtual server as root, without a password. Well done!

.. note:: There is no reason to limit injections to ssh keys. Users with an
    adequate understanding of the remote OS are encouraged to prepare and
    inject all kinds of useful files, e.g., **lists of package sources**,
    **default user profiles**, **device mount configurations**, etc.

Clusters of virtual servers
---------------------------

A virtual cluster is a number of virtual servers which have names starting with
the same prefix e.g., *cluster1*, *cluster2*, etc. This prefix acts as the
cluster name. Still, users must be careful not to confuse cluster servers with
other servers that coincidentally have the same prefix (e.g.,
*cluster_of_stars*).

First, let's create a cluster of 4 servers. Each server will run the image with
id *f1r57-1m4g3-1d* on the hardware specified by the flavor with id *1*. The
prefix of the cluster will be "my cluster "

.. code-block:: console

    $ kamaki
    $ kamaki server
    $ kamaki server create --name="my cluster " --flavor-id=1 --image=if1r57-1m4g3-1d --cluster-size=4 --wait
    ... <omitted for clarity>
    adminPass:       S0mePassw0rd0n3
    flavor-id: 1
    id: 322
    image-id: f1r57-1m4g3-1d
    name: my cluster 1
    [progress bar waiting server to build]
    Server 321: status is now ACTIVE

    ... <omitted for clarity>
    adminPass: S0mePassw0rdTwo
    flavor-id: 1
    id: 321
    image-id: f1r57-1m4g3-1d
    name: my cluster 2
    [progress bar waiting server to build]
    Server 322: status is now ACTIVE

    ... <omitted for clarity>
    adminPass: S0mePassw0rdThree
    created: 2013-06-19T12:34:55.362078+00:00
    flavor0id: 1
    id: 323
    image-id: f1r57-1m4g3-1d
    name: my cluster 3
    [progress bar waiting server to build]
    Server 323: status is now ACTIVE

    ... <omitted for clarity>
    adminPass:  S0mePassw0rdFour
    created: 2013-06-19T12:34:59.362078+00:00
    flavor-id: 1
    id: 324
    image-id: f1r57-1m4g3-1d
    name: my cluster 4
    [progress bar waiting server to build]
    Server 324: status is now ACTIVE

.. note:: The virtual servers can be created asynchronously. To activate
    asynchronous operations, set max_theads to some value greater than 1.
    Default is 1, though.

    .. code-block:: console

        # Create a cluster using multithreading (4 threads)

        $ kamaki server create --name="my cluster " --flavor-id=1 --image=if1r57-1m4g3-1d --cluster-size=4 --wait --threads=4

.. note:: the *- - wait* argument is optional, but if not used, the *create*
    call will terminate as long as the servers are spawned, even if they are
    not built yet.

.. warning:: The server details (password, etc.) are printed in
    **standard output** while the progress bar and notification messages are
    printed in **standard error**

Now, let's see our clusters:

.. code-block:: console

    $ kamaki server list --name-prefix 'my cluster '
    321 my cluster 2
    322 my cluster 1
    323 my cluster 3
    324 my cluster 4

For demonstration purposes, let's suppose that the maximum resource limit is
reached if we create 2 more servers. We will attempt to expand "my cluster" by
4 servers, expecting kamaki to raise a quota error.

.. code-block:: console

    $ kamaki server create --name="my cluster " --flavor-id=1 --image-id=f1r57-1m4g3-1d --cluster-size=4 --wait
    Failed to build 4 servers
    Found 2 matching servers:
    325 my cluster 1
    326 my cluster 2
    Check if any of these servers should be removed

    (413) REQUEST ENTITY TOO LARGE overLimit (Resource Limit Exceeded for your
    account.)
    |  Limit for resource 'Virtual Machine' exceeded for your account.
    Available: 0, Requested: 1

The cluster expansion has failed, but 2 of the attempted 4 servers are being
created right now. It's up to the users judgment to destroy or keep them.

First, we need to list all servers:

.. code-block:: console

    $ kamaki server list --name-prefix="my cluster "
    321 my cluster 2
    322 my cluster 1
    323 my cluster 3
    324 my cluster 4
    325 my cluster 1
    326 my cluster 2

.. warning:: Kamaki will always create clusters by attaching an increment at
    the right of the prefix. The increments always start from 1.

Now, our cluster seems messed up. Let's destroy it and rebuilt it.

.. code-block:: console

    $ kamaki server delete --cluster "my cluster " --wait
    [progress bar waiting server to be deleted]
    Server 321: status is now DELETED

    [progress bar waiting server to be deleted]
    Server 322: status is now DELETED

    [progress bar waiting server to be deleted]
    Server 323: status is now DELETED

    [progress bar waiting server to be deleted]
    Server 324: status is now DELETED

    [progress bar waiting server to be deleted]
    Server 325: status is now DELETED

    [progress bar waiting server to be deleted]
    Server 326: status is now DELETED

.. note:: *delete* performs a single deletion if fed with a server id, but it
    performs a mass deletion based on the name, if called with --cluster

While creating the first cluster, we had to write down all passwords 

The passwords for each server are printed on the console while creating them.
It would be far more convenient, though, if we could massively inject an ssh
key into all of them. Let's do that!

.. code-block:: console

    $ kamaki server create --name="my new cluster " --flavor-id=1 --image-id=f1r57-1m4g3-1d --cluster-size=4 --wait --personality=/home/someuser/.ssh/id_rsa.pub,/root/.ssh/authorized_keys,root,root,0777

    ... <output omitted for clarity>

Now, let's check if the cluster has been created.

.. code-block:: console

    $ kamaki server list --name-prefix="my new cluster "
    321 my new cluster 1
    322 my new cluster 2
    323 my new cluster 3
    324 my new cluster 4

We now have a cluster of 4 virtual servers and we can ssh in all of them
without a password.
