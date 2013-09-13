Creating Servers (Virtual Machines)
===================================

A `server` (also known as `virtual machine`), is created based on a registered
`image` and a reconfigured hardware setup (also known as `flavor`).

Create a virtual server
-----------------------

List available flavors

.. code-block:: console

    [kamaki]: flavor list -l
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
    [kamaki]:

List available images

.. code-block:: console

    [kamaki]: image compute list
    f1r57-1m4g3-1d Debian Base Alpha
    53c0nd-1m4g3-1d Beta Debian Base
    [kamaki]:

Let's pick the `C1R128D1drbd` (id: 1) flavor and the `Debian Base Alpha` (id:
f1r57-1m4g3-1d) image to create a new VM called 'My First Server'

.. code-block:: console

    [kamaki]: server create 'My First Server' 1 f1r57-1m4g3-1d
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
    [kamaki]:

.. note:: The adminPass field is not stored anywhere, therefore users would
    rather write it down and change it the first time they use the VM

Wait for the VM with id 141 to build (optional)

.. code-block:: console

    [kamaki]: server wait 141
    <bar showing build progress, until 100%>
    Server 141 is not in ACTIVE mode
    [kamaki]:

Destroy the VM (wait is still optional)

.. code-block:: console

    [kamaki]: server delete 141
    [kamaki]: server wait 141 ACTIVE
    <bar showing destruction progress, until 100%>
    Server 141 is not in DELETED mode
    [kamaki]:

Inject ssh keys to a debian server
----------------------------------

Assume that the servers build from the image `Debian Base Alpha` accept ssh
connections. We need to build servers that can log us as roots without a
password. This can be achieved if the `/root/.ssh/authorized_keys` file exists
and contains the public key of the current user.

Assume that the public key file of the current user is located at
`/home/someuser/.ssh/id_rsa.pub` . We need a method of injecting this file as
`/root/.ssh/authorized_keys` while creating the virtual server.

Luckily, Synnefo fully supports the OpenStack suggestion for file injections on
VMs and kamaki allows it by using the **-p** argument (p stands for 
`PERSONALITY` and is the term used in the
`respective OpenStack <http://docs.openstack.org/api/openstack-compute/2/content/CreateServers.html>`_ description).

The syntax of the -p argument is something called "the personlity string"::

    -p <local file path>[,<remote path>[,<remote owner>[,<remote group>[,<mode>]]]]

    e.g.

    -p /home/someuser/.ssh/id_rsa.pub,/root/.ssh/authorized_keys,root,root,0777

.. note:: In case of omitting an optional part of the personality string, the
    default behavior depends on the remote server, e.g. for a debian image we
    expect the file to have root ownership, if the ownership is not specified.

Create a vm while injecting current users public key to root account

.. code-block:: console

    [kamaki]: server
    [server]: create 'NoPassword Server' 1 f1r57-1m4g3-1d -p /home/someuser/.ssh/id_rsa.pub,/root/.ssh/authorized_keys
    accessIPv4:      
    accessIPv6:      
    addresses:      
    adminPass:       Th1s1s4U5elessTh1ngN0w
    attachments:    
    config_drive:    
    created:         2013-06-19T12:34:47.362078+00:00
    diagnostics:    
    flavor:         
            id:    1
    hostId:          
    id:              142
    image:          
            id:     f1r57-1m4g3-1d
    key_name:        None
    metadata:       
                    os:    debian
                    users: root
    name:           No Password Server
    progress:        0
    security_groups:
                    name: default
    status:          BUILD
    suspended:       False
    tenant_id:       s0m3-u53r-1d
    updated:         2013-06-19T12:34:48.512867+00:00
    user_id:         s0m3-u53r-1d
    [server]:

When the VM is ready, get the VMs external IP from the web UI. Let's assume the
IP is 123.456.78.90 .

.. code-block:: console

    [server]: /exit
    $ ssh 123.456.78.90
    Linux remote-vm-4241 2.6.32-5-amd64 #1 SMP XXXX x86_64

    The programs included with the Debian GNU/Linux system are free software;
    the exact distribution terms for each program are described in the
    individual files in /usr/share/doc/*/copyright.

    Debian GNU/Linux comes with ABSOLUTELY NO WARRANTY, to the extent
    permitted by applicable law.
    root@remote-vm-4241:~# ls -l .ssh/
    total 4
    -rw-r--r-- 1 root root 399 Jun 19 12:34 authorized_keys
    root@remote-vm-4241:~#

You can now log to your remote VM as root, without a password. Well done!

.. note:: There is no reason to limit injections to ssh keys. Users with an
    adequate understanding of the remote OS are encouraged to prepare and
    inject all kinds of useful files, e.g. **lists of package sources**,
    **default user profiles**, **device mount configurations**, etc.
