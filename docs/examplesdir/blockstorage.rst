Volumes and Snapshots
=====================

In this section we will snapshot a virtual server, backup the snapshot image to
a local storage and then we will destroy and recreate the server.

**List existing virtual servers and volumes**

.. code-block:: console

    $ kamaki server list
    1 My test server
    2 My very important server

    $ kamaki volume list
    v0lum31 Volume for test server
    v0lum32 Volume for important server

.. note:: Usually each virtual server corresponds to one volume, but new
    volumes can also been created:

    .. code-block:: console

        $ kamaki volume create --name='extra volume' --server-id=2 --size=20

**Take a snapshot**

.. code-block:: console

    $ kamaki snapshot create --name='Important server backup' --volume-id=2
    id: imp0r74n7-s3rv3r-1m4g3
    display_name: Important server backup
    status: ACTIVE
    size: 10
    descrtiption: null
    created_at: 2014-05-19T19:52:04.949734
    metadata:
    volume_id: v0lum32

The new snapshot appears as a loaded image as well as a file stored in
Pithos+

.. code-block:: console

    $ kamaki snapshot list
    imp0r74n7-s3rv3r-1m4g3 Important server backup

    $ kamaki file list /snapshots
    20GB  v0lum31-snap-0

    $ kamaki image list --id=imp0r74n7-s3rv3r-1m4g3
    imp0r74n7-s3rv3r-1m4g3 Important server backup

**Backup snapshot image to local storage**

This is optional, but better safe than sorry.

.. code-block:: console

    $ kamaki file download /snapshots/v0lum31-snap-0 local.backup
    ...

**Destroy and reload**

For demonstration purposes, let's destroy the server. The snapshot image will
be used to recreate it afterwards.

.. code-block:: console

    $ kamaki server delete 2 -w
    ...
    Server status is now DELETED

    $ kamaki server create --name='Important server' --flavor-id=1 --image-id=imp0r74n7-s3rv3r-1m4g3 -w
    id: 3
    name: Important server
    ...
    Server status is now ACTIVE

**Reload from local backup**

If both the server and the snapshot are lost, the local backup can be used to
restore the server. To do this, we need to register the backup as an image (see
`Image register <imageregister.html>`_ for more details).

.. code-block:: console

    $ kamaki image register --name='Image from BackUp' --location=/snapshots/reloaded.diskdump --upload-image-file=local.backup
    id: r3l04d3d-5n4p5h07-1m4g3
    name: Image from BackUp
    ...

    $ kamaki server create --name='Server from local BackUp' --flavor-id=1 --image-id=r3l04d3d-5n4p5h07-1m4g3 -w
    id: 4
    name: Server from local BackUp
    ...
    Server is now ACTIVE
