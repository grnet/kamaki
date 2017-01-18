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

Create, update and use SSH keys
-------------------------------
SSH keys can provice safe and passwordless access to servers. Users maintain a
wallet of keypairs. A keypair is a key with a name. To use any of these keys
as access method for a server, users can name them on server creation
time.

To upload a public key:

.. code-block:: console

    $ kamaki keypair upload \
        --key-name "My Uploaded Key" \
        --public-key "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC4qiHrLE33kWpLTHplB6SZ2eU3oq/tYGaIdEJOByZHwOAcbC/lBIhwBnAkatyv9YJ27WxfT+JV1B/ugntk0hZmtewFovdylog53e5hgdzVrzZyvugPf6zZiqckMzrubNN3UGSC47PQbiFPvlRVp6sCVj8i4MILVo4ZlGjX7qptTMNJcZhvc7TUc8b0WbBo+lbJIjTSP/jwqxGyEAVDCJAHf1aBcqD1zNXRB0sXzjz41nv2tu512SS6Y2l5vGaPap1S3GWE1VkuqmtM+m8zzEXtJgvtpMhjOC5aMG4Q+OCq1EP176A8kIlLZAU1qaGrjhFtE3IFN/SCmgVOAPb76IDv"

    public key: ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC4qiHrLE33kWpLTHplB6SZ2eU3oq/tYGaIdEJOByZHwOAcbC/lBIhwBnAkatyv9YJ27WxfT+JV1B/ugntk0hZmtewFovdylog53e5hgdzVrzZyvugPf6zZiqckMzrubNN3UGSC47PQbiFPvlRVp6sCVj8i4MILVo4ZlGjX7qptTMNJcZhvc7TUc8b0WbBo+lbJIjTSP/jwqxGyEAVDCJAHf1aBcqD1zNXRB0sXzjz41nv2tu512SS6Y2l5vGaPap1S3GWE1VkuqmtM+m8zzEXtJgvtpMhjOC5aMG4Q+OCq1EP176A8kIlLZAU1qaGrjhFtE3IFN/SCmgVOAPb76IDv
    name: My Uploaded Key
    fingerprint: aa:b7:cf:74:42:92:e4:cf:73:0b:2a:3e:63:ef:7f:ea

You can also generate a new keypair. Just make sure to write down the private key, since it is not preserved by the service. In the following example we ask kamaki to format the response in json.

.. code-block:: console

    $ kamaki keypair generate --key-name "My Generated Key" \
        --output-format json

    {
      "public_key": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCsF8Ut3x1y46wiDJY4n2f12zxBh0Qrgj3BFxrP8LojNpsgnDJ5NAmLj7xAs3hvYTF1GIEmsq+kWXUevjLvaJsbVg168v01rZTN3seuY9r3vhNa3hDikGlhO8IJNDimYQSrw4UK1tvKtOVDQ/EcXfL7qfeZ5Wq3dOX/W50BHcQMkN+c1uL6Xzguv8263ysa+Q0UQXlPm0bWcJLnR/T9IXTsljsdkOSqynIUDDmDWhyI6PqAMzlkJtk0AlviCnePcBxVKKM9BR8CAewUHuJvk82IVlJfrXvJg8HtXxK3ZESJ5ryN0R8kHb0JFJ+b43L7PZXBKfZJ2pVHQsfF123sfLlz", 
      "private_key": "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEArBfFLd8dcuOsIgyWOJ9n9ds8QYdEK4I9wRcaz/C6IzabIJwy\neTQJi4+8QLN4b2ExdRiBJrKvpFl1Hr4y72ibG1YNevL9Na2Uzd7HrmPa974TWt4Q\n4pBpYTvCCTQ4pmEEq8OFCtbbyrTlQ0PxHF3y+6n3meVqt3Tl/1udAR3EDJDfnNbi\n+l84Lr/Nut8rGvkNFEF5T5tG1nCS50f0/SF07JY7HZDkqspyFAw5g1ociOj6gDM5\nZCbZNAJb4gp3j3AcVSijPQUfAgHsFB7ib5PNiFZSX617yYPB7V8St2REiea8jdEf\nJB29CRSfm+Ny+z2VwSn2SdqVR0LHxddt7Hy5cwIDAQABAoIBADiFBgluwak+BQaZ\nw6yNDgO9ISkUV9tCRy3nfLLWiQuPn5syMZGE+a2QY2+Mgf1yml+u0Jv5C56aktCp\n/uiKHob32C2NKIQ8oiaLCGHKAdxj3M93J2yBqVp52dxT/lcGfhY7fLJ2pnEIwFM7\nOTDr2iW1SNCOfGIMTo1zdTksoXrOf3F+Xm1ecEc4He9BQ9eopBRRd1W4C3pzKEd4\nO0ofhQGIqI1frmRYCbF/RvqVusKkoIHpShCVkZkkWXhRx3MC7y3txp5d9M0xkW1z\n76DDMshHrLtOov3iMR9wk3e6nsay6qRW5/fZ9z5QzreCAIr8IHr9SqzOhsrQPdlr\nVjAJEyECgYEAv6lMVOslm+bJMs4PiytH/CNBuatqKOdoGp+ifL4qjHobGKZ9Js9/\n4woMpSYHpyedOB53QKZZ536rDrFfN9YQ5hLE0QjhURn6nAJ98G1+PE/9aGTWWufa\nvE/VJb5+a1r37LNlQcgsblzOmASt+vMDju/2pDYRk3MlsPkXhB0+ka0CgYEA5dzT\nlUtBD2R0tlXpzTdtwD49+wZAO0H44WOREytIXc074gZScrAo2f+pv7sJOZL4p/7B\n3wdbBi5M8lyjEZ1enXBV+GePtr9fGsv2hQGG/bJlIPDbbi8xbkKywgIymrOxqZB4\nwPjGEpUmzuzh7UrSy7E1iW3s1fLbws9+sWSvG58CgYEAucM9WJERQqnNGJDgP+MT\nQi5p5atemYawQB25P26RjtZKrPmxE4zKRyPWXbseb8TVfS8KJn8VZGpBIVyJDXVN\nq7FFUdVpjVHAtLU1m3KEh7B/zE7v8+wE9b/qt0qK/UKOSb0Wx0tcxRruoijm9/PR\n3xh11XMSVfek8IJ9aG9v1YECgYBUJE+3WMLKFaW7kRtyqZWdR6t8lj8w8ede6gmT\nEMb+vz/qbxIDNYTet/21V4v67VfkdxcUwyaIzq4QEeUHb6nQy+xMb+xlowv3TS5C\nZdq6R3FJa6GHZfMcP4IcDp3jj1+7iE0LpoUrDDoWiRPyvu8G7SmB0yFc9/eGClqA\nKTEIVQKBgB5IejX91BlPf/68HBnf1Way5h44uPy6YIL6PnRLA4aPbMdE0BlIDXQP\ngE/GmLWSeFFSszLjrV+ePCLvdkjlYZaPcwKzAiqgHTn1x2aFtwOSvChb2kL/yFts\nXcFoA/2/Ups88CnpmVZHbc3Nsx7h/xleh4W+nDCNSmamAwjomq1s\n-----END RSA PRIVATE KEY-----", 
      "name": "My Generated Key", 
      "fingerprint": "5a:a1:b4:18:bf:5e:d0:e4:09:3b:44:01:41:0d:49:07"
    }

Now our cloud key wallet looks like this:

.. code-block:: console

    $ kamaki keypair list

    My Generated Key
        fingerprint: 5a:a1:b4:18:bf:5e:d0:e4:09:3b:44:01:41:0d:49:07
    My Uploaded Key
        fingerprint: aa:b7:cf:74:42:92:e4:cf:73:0b:2a:3e:63:ef:7f:ea

We are going to create a server with the uploaded key and another server with the generated key.

.. code-block:: console

    $ kamaki server create --name "My Client's Server" \
        --flavor-id=1 --image-id=f1r57-1m4g3-1d \
        --key-name "My Generated Key"

    ...(ommited for clarity) ...

    $ kamaki server create --name "My Personal Server" \
        --flavor-id=1 --image-id=f1r57-1m4g3-1d \
        --key-name "My Uploaded Key" --network 1,123.456.78.90

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
    name:           My Personal Server
    progress:        0
    status:          BUILD
    suspended:       False
    tenant_id:       s0m3-u53r-1d
    updated:         2013-06-19T12:34:48.512867+00:00
    user_id:         s0m3-u53r-1d

When the personal server is ready, we can connect through the public network 1
and the IP 123.456.78.90 :

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

You can now log to your remote virtual server as root, without a password. Well
done!


Inject ssh keys to a debian server
----------------------------------

Another method to install ssh keys is by injecting prepared local files to the
server file system on creation. These injections are called `personalities
<http://docs.openstack.org/api/openstack-compute/2/content/createServers.html>`_.
For instance, to setup root PPK authentication on a Debian server, we have to
inject a file with our public key(s) as `/root/.ssh/authorized_keys` with
restricted permissions.

Assume that the public key file of the current user is located at
`/home/someuser/.ssh/id_rsa.pub`, we can use the **-p** kamaki argument (p
stands for `PERSONALITY` and is the term used in the respective)::

    -p <local file path>[,<remote path>[,<remote owner>[,<remote group>[,<mode>]]]]

    e.g.,

    -p /home/someuser/.ssh/id_rsa.pub,/root/.ssh/authorized_keys,root,root,0777

.. note:: In case of omitting an optional part of the personality string, the
    default behavior depends on the remote server, e.g., for a debian image we
    expect the file to have root ownership, if the ownership is not specified.

Create a virtual server while injecting current user public key to root account

.. code-block:: console

    $ kamaki server create --name='My Personal Server' \
        --flavor-id=1 --image-id=f1r57-1m4g3-1d \
        -p /home/someuser/.ssh/id_rsa.pub,/root/.ssh/authorized_keys,root,root,0600

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
It would be far more convenient, though, if we could add an ssh key to all of
them. Let's do that!

.. code-block:: console

    $ kamaki server create --name="my new cluster " --flavor-id=1 --image-id=f1r57-1m4g3-1d --cluster-size=4 --wait --key-name "My Uploaded Key"

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
