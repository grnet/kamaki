Listing
=======

In this section we present the ways of kamaki for listing, an operation that is
common to most command groups.

The examples of this section run in a kamaki interactive shell.

.. code-block:: console

    $ kamaki
    kamaki v0.9 - Interactive Shell
    .
    /exit       terminate kamaki
    exit or ^D  exit context
    ? or help   available commands
    ?command    help on command
    !<command>  execute OS shell command
    .
    [kamaki]:

Simple listing
--------------

List configuration options, whether in the file or in memory

.. code-block:: console

    [kamaki]: config list
    cloud.default.url = https://astakos.example.com/identity/v2.0/
    cloud.default.token = my70k3n==
    global.default_cloud = default
    global.colors = on
    global.config_cli = config
    global.file_cli = pithos
    global.flavor_cli = cyclades
    global.history_cli = history
    global.history_file = /home/saxtouri/.kamaki.history
    global.image_cli = image
    global.log_file = /home/saxtouri/.kamaki.log
    global.log_token = one
    global.max_threads = 5
    global.network_cli = cyclades
    global.server_cli = cyclades
    global.user_cli = astakos
    [kamaki]:

List stored containers and then objects in container "pithos"

.. code-block:: console

    [kamaki]: file list
    pithos (36MB, 4 objects)
    trash (0B, 0 objects)
    [kamaki]: file list pithos
    . 2KB  info.txt
    . D    video/
    . 11MB video/tk1.mpg
    . 12MB video/tk2.mpg
    . 13MB video/tk3.mpg
    [kamaki]:

List virtual machines (servers)

.. code-block:: console

    [kamaki]: server list
    4201 example server 1
    4202 example server 2

List networks

.. code-block:: console

    [kamaki]: network list
    1 public_network
    42 my_private)network
    [kamaki]:

List flavors

.. code-block:: console

    [kamaki]: flavor list
    1 C1R1024D20drbd
    2 C1R1024D30drbd
    [kamaki]:

List images from Image API and from Compute APIs

.. code-block:: console

    [kamaki]: image list
    cde9858c-0656-4da1-8cbd-33481b29a8bd Debian Base
    .container_format: bare
    .disk_format:      diskdump
    .size:             474066944
    .status:           available
    a5ca5997-c580-4d62-b012-05c5329f8e2d Debian Base
    .container_format: bare
    .disk_format:      diskdump
    .size:             474066944
    .status:           available
    [kamaki]: image compute list
    a5ca5997-c580-4d62-b012-05c5329f8e2d Debian Base
    cde9858c-0656-4da1-8cbd-33481b29a8bd Debian Base
    [kamaki]:

Detailed pithos listing
-----------------------

List pithos containers with details

.. code-block:: console

    [kamaki]: file
    [file]: list -l
    pithos
    bytes:    0 (0B)
    count:    3
    modified: 2013-06-17T12:35:11.613124+00:00
    policy:  
    .       quota:      0
    .       versioning: auto
    trash
    bytes:    0 (0B)
    count:    0
    modified: 2013-06-06T14:24:23.675891+00:00
    policy:  
    .       quota:      0
    .       versioning: auto
    [file]:

Create some more pithos container to experiment with

.. code-block:: console

    [file]: create cont1
    [file]: create cont2
    [file]: create cont3
    [file]: create cont4
    [file]: list
    cont1 (0B, 0 objects)
    cont2 (0B, 0 objects)
    cont3 (0B, 0 objects)
    cont4 (0B, 0 objects)
    pithos (36B, 5 objects)
    trash (0B, 0 objects)
    [file]:

List only 3, then list three by three

.. code-block:: console

    [file]: list -n 3
    cont1 (0B, 0 objects)
    cont2 (0B, 0 objects)
    cont3 (0B, 0 objects)
    [file]: list -n 3 --more
    cont1 (0B, 0 objects)
    cont2 (0B, 0 objects)
    cont3 (0B, 0 objects)
    (3 listed - 3 more - "enter" to continue)
    <enter is pressed>
    cont4 (0B, 0 objects)
    pithos (36B, 4 objects)
    trash (0B, 0 objects)
    [file]: 

List contents of container `pithos`

.. code-block:: console

    [file]: list -l pithos
    info.txt
    by:        s0m3-u53r-1d
    bytes:     2000 (2ΚB)
    hash:      427ae41e4649b934ca495991b7852b855e3b0c44298fc1c149afbf4c8996fb92
    modified:  2013-06-17T13:09:44.529579+00:00
    timestamp: 1371474584.5295789
    type:      plan-text/unicode
    uuid:      0493f1d9-9410-4f4b-a81f-fe42f9cefa70
    version:   1085
    .
    video
    by:        s0m3-u53r-1d
    bytes:     0
    hash:      e3b0c44298fc1c149afbf44ca495991b7852b855c8996fb92427ae41e4649b93
    modified:  2013-06-17T13:11:39.050090+00:00
    timestamp: 1371474699.0500901
    type:      application/directory
    uuid:      80e719f5-9d68-4333-9846-9943972ef1fd
    version:   1086
    .
    video/tk1.mpg
    by:        s0m3-u53r-1d
    bytes:     11000000 (11ΜΒB)
    hash:      fbf4c8996fb92427ae41e464e3b0c44298fc1c5991b7852b855149a9b934ca49
    modified:  2013-06-17T13:09:15.866515+00:00
    timestamp: 1371474555.8665149
    type:      video/mpeg
    uuid:      b0b46b39-c59a-4adc-a386-6a169cb9f8a5
    version:   1079
    .
    video/tk2.mpg
    by:        s0m3-u53r-1d
    bytes:     12000000 (12MB)
    hash:      44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b78e3b0c52b855
    modified:  2013-06-17T13:09:23.898652+00:00
    timestamp: 1371474563.8986521
    type:      video/mpeg
    uuid:      12a81309-db3c-4e30-ae9a-4ac2b8289def
    version:   1081
    .
    video/tk3.mpg
    by:        s0m3-u53r-1d
    bytes:     13000000 (13MB)
    hash:      1e4649b934ca495991b7852b855e3b0c44298fc1c149afbf4c8996fb92427ae4
    modified:  2013-06-17T13:09:28.222536+00:00
    timestamp: 1371474568.2225361
    type:      video/mpeg
    uuid:      4195e8c3-9b9a-4e97-8c20-fdfef34892fe
    version:   1083
    [kamaki]:

List only videos and exit "file" context

.. code-block:: console

    [file]: list -l pithos:video/
    video/tk1.mpg
    by:        s0m3-u53r-1d
    bytes:     11000000 (11ΜΒB)
    hash:      fbf4c8996fb92427ae41e464e3b0c44298fc1c5991b7852b855149a9b934ca49
    modified:  2013-06-17T13:09:15.866515+00:00
    timestamp: 1371474555.8665149
    type:      video/mpeg
    uuid:      b0b46b39-c59a-4adc-a386-6a169cb9f8a5
    version:   1079
    .
    video/tk2.mpg
    by:        s0m3-u53r-1d
    bytes:     12000000 (12MB)
    hash:      44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b78e3b0c52b855
    modified:  2013-06-17T13:09:23.898652+00:00
    timestamp: 1371474563.8986521
    type:      video/mpeg
    uuid:      12a81309-db3c-4e30-ae9a-4ac2b8289def
    version:   1081
    .
    video/tk3.mpg
    by:        s0m3-u53r-1d
    bytes:     13000000 (13MB)
    hash:      1e4649b934ca495991b7852b855e3b0c44298fc1c149afbf4c8996fb92427ae4
    modified:  2013-06-17T13:09:28.222536+00:00
    timestamp: 1371474568.2225361
    type:      video/mpeg
    uuid:      4195e8c3-9b9a-4e97-8c20-fdfef34892fe
    version:   1083
    [kamaki]:
