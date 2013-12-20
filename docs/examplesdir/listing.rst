Listing
=======

The listing of various synnefo objects (e.g, server, file, network) is
showcased in this section.

Simple listing
--------------

List configuration options, whether in the file or from defaults list

.. code-block:: console

    $ kamaki config list
    global.default_cloud = mycloud
    global.colors = off
    global.config_cli = config
    global.container_cli = pithos
    global.file_cli = pithos
    global.flavor_cli = cyclades
    global.group_cli = pithos
    global.history_cli = history
    global.history_file = /home/someuser/.kamaki.history
    global.image_cli = image
    global.imagecompute_cli = image
    global.ip_cli = network
    global.log_data = off
    global.log_file = /home/someuser/.kamaki.log
    global.log_pid = off
    global.log_token = off
    global.network_cli = network
    global.port_cli = network
    global.project_cli = astakos
    global.quota_cli = astakos
    global.resource_cli = astakos
    global.server_cli = cyclades
    global.sharer_cli = pithos
    global.subnet_cli = network
    global.user_cli = astakos

List stored containers and file or directory objects in container "pithos"

.. code-block:: console

    $ kamaki container list
    pithos (36MB, 4 objects)
    trash (0B, 0 objects)
    $ kamaki file list /pithos
    2KB  info.txt
    D    video/
    11MB video/tk1.mpg
    12MB video/tk2.mpg
    13MB video/tk3.mpg
    $ kamaki file list /pithos/video
    11MB video/tk1.mpg
    12MB video/tk2.mpg
    13MB video/tk3.mpg

.. note:: In file list, the default container is "pithos"

    .. code-block:: console

        $ kamaki file list
        2KB  info.txt
        D    video/
        11MB video/tk1.mpg
        12MB video/tk2.mpg
        13MB video/tk3.mpg
        $ kamaki file list video
        11MB video/tk1.mpg
        12MB video/tk2.mpg

List virtual machines (servers)

.. code-block:: console

    $ kamaki server list
    4201 example server 1
    4202 example server 2
    4203 example server 3
    4204 example server 4
    4205 example server 5
    4206 example server 6

List networks

.. code-block:: console

    $ kamaki network list
    1 public_network
    42 my_private_network

List flavors

.. code-block:: console

    $ kamaki flavor list
    1 C1R1024D20drbd
    2 C1R1024D30drbd

List images from Image API and from Compute APIs

.. code-block:: console

    $ kamaki image list
    f1r57-1m4g3-1d Debian Base Alpha
     container_format: bare
     disk_format:      diskdump
     size:             474066944
     status:           available
    53c0nd-1m4g3-1d Beta Debian Base
     container_format: bare
     disk_format:      diskdump
     size:             474066944
     status:           available
    $ kamaki imagecompute list
    f1r57-1m4g3-1d Debian Base Alpha
    53c0nd-1m4g3-1d Beta Debian Base

Detailed pithos listing
-----------------------

List pithos containers with details

.. code-block:: console

    $ kamaki container list -l
    pithos
    bytes:    0 (0B)
    count:    3
    modified: 2013-06-17T12:35:11.613124+00:00
    policy:
            quota:      0
            versioning: auto
    trash
    bytes:    0 (0B)
    count:    0
    modified: 2013-06-06T14:24:23.675891+00:00
    policy:
            quota:      0
            versioning: auto

Create some more containers to experiment with

.. code-block:: console

    $ kamaki container create cont1
    $ kamaki container create cont2
    $ kamaki container create cont3
    $ kamaki container create cont4
    $ kamaki container list
    cont1 (0B, 0 objects)
    cont2 (0B, 0 objects)
    cont3 (0B, 0 objects)
    cont4 (0B, 0 objects)
    pithos (36B, 5 objects)
    trash (0B, 0 objects)

List contents of container `pithos`

.. code-block:: console

    $ kamaki file list -l /pithos
    info.txt
    by:        s0m3-u53r-1d
    bytes:     2000 (2ΚB)
    hash:      427ae41e4649b934ca495991b7852b855e3b0c44298fc1c149afbf4c8996fb92
    modified:  2013-06-17T13:09:44.529579+00:00
    timestamp: 1371474584.5295789
    type:      plan-text/unicode
    uuid:      0493f1d9-9410-4f4b-a81f-fe42f9cefa70
    version:   1085
     
    video
    by:        s0m3-u53r-1d
    bytes:     0
    hash:      e3b0c44298fc1c149afbf44ca495991b7852b855c8996fb92427ae41e4649b93
    modified:  2013-06-17T13:11:39.050090+00:00
    timestamp: 1371474699.0500901
    type:      application/directory
    uuid:      80e719f5-9d68-4333-9846-9943972ef1fd
    version:   1086
     
    video/tk1.mpg
    by:        s0m3-u53r-1d
    bytes:     11000000 (11ΜΒB)
    hash:      fbf4c8996fb92427ae41e464e3b0c44298fc1c5991b7852b855149a9b934ca49
    modified:  2013-06-17T13:09:15.866515+00:00
    timestamp: 1371474555.8665149
    type:      video/mpeg
    uuid:      b0b46b39-c59a-4adc-a386-6a169cb9f8a5
    version:   1079
     
    video/tk2.mpg
    by:        s0m3-u53r-1d
    bytes:     12000000 (12MB)
    hash:      44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b78e3b0c52b855
    modified:  2013-06-17T13:09:23.898652+00:00
    timestamp: 1371474563.8986521
    type:      video/mpeg
    uuid:      12a81309-db3c-4e30-ae9a-4ac2b8289def
    version:   1081
     
    video/tk3.mpg
    by:        s0m3-u53r-1d
    bytes:     13000000 (13MB)
    hash:      1e4649b934ca495991b7852b855e3b0c44298fc1c149afbf4c8996fb92427ae4
    modified:  2013-06-17T13:09:28.222536+00:00
    timestamp: 1371474568.2225361
    type:      video/mpeg
    uuid:      4195e8c3-9b9a-4e97-8c20-fdfef34892fe
    version:   1083
    $ kamaki

List only objects starting with "video" and exit "file" context. Remember that
"pithos" is the default container, so there is no need to refer to it.

.. code-block:: console

    $ kamaki file list -l video/
    video/tk1.mpg
    by:        s0m3-u53r-1d
    bytes:     11000000 (11ΜΒB)
    hash:      fbf4c8996fb92427ae41e464e3b0c44298fc1c5991b7852b855149a9b934ca49
    modified:  2013-06-17T13:09:15.866515+00:00
    timestamp: 1371474555.8665149
    type:      video/mpeg
    uuid:      b0b46b39-c59a-4adc-a386-6a169cb9f8a5
    version:   1079
     
    video/tk2.mpg
    by:        s0m3-u53r-1d
    bytes:     12000000 (12MB)
    hash:      44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b78e3b0c52b855
    modified:  2013-06-17T13:09:23.898652+00:00
    timestamp: 1371474563.8986521
    type:      video/mpeg
    uuid:      12a81309-db3c-4e30-ae9a-4ac2b8289def
    version:   1081
     
    video/tk3.mpg
    by:        s0m3-u53r-1d
    bytes:     13000000 (13MB)
    hash:      1e4649b934ca495991b7852b855e3b0c44298fc1c149afbf4c8996fb92427ae4
    modified:  2013-06-17T13:09:28.222536+00:00
    timestamp: 1371474568.2225361
    type:      video/mpeg
    uuid:      4195e8c3-9b9a-4e97-8c20-fdfef34892fe
    version:   1083

Detailed Server Listing
-----------------------

List only 3, then list three by three, all with enumeration

.. code-block:: console

    $ kamaki server list --enumerate
    1. 4201 example server 1
    2. 4202 example server 2
    3. 4203 example server 3
    4. 4204 example server 4
    5. 4205 example server 5
    6. 4206 example server 6
    $ kamaki server list -n 3 --more
    1. 4201 example server 1
    2. 4202 example server 2
    3. 4203 example server 3
    (3 listed - 3 more - "enter" to continue)
    <press "enter">
    4. 4204 example server 4
    5. 4205 example server 5
    6. 4206 example server 6

List in json output

.. code-block:: console

    $ kamaki server list -output-format=json
    [
        {
            "name": "example server 1",
            "links": [
              {
                "href": "https://example.com/compute/v2.0/servers/4201",
                "rel": "self"
              },
              {
                "href": "https://example.com/compute/v2.0/servers/4201",
                "rel": "bookmark"
              }
            ],
            "id": 4201
          },
          {
            "name": "example server 2",
            "links": [
              {
                "href": "https://example.com/compute/v2.0/servers/4202",
                "rel": "self"
              },
              {
                "href": "https://example.com/compute/v2.0/servers/4202",
                "rel": "bookmark"
              }
            ],
            "id": 4202
          }
        ...
    ]

Server details

.. code-block:: console

    $ kamaki server list -l
    4201 my example server 1
        accessIPv4:
        accessIPv6:
        addresses:
                    42:
                           OS-EXT-IPS:type: fixed
                           addr:            192.168.12.4
                           version:         4
                        
                           OS-EXT-IPS:type: fixed
                           addr:            2001:648:2ffc:1222:a800:2ff:fee3:49f1
                           version:         6
        attachments:
                       firewallProfile: DISABLED
                       id:              nic-37231-0
                       ipv4:            192.168.12.4
                       ipv6:            2001:648:2ffc:1222:a800:2ff:fee3:49f1
                       mac_address:     aa:00:02:e3:49:f8
                       network_id:      4161
        config_drive:
        created:         2013-05-11T18:03:41.471605+00:00
        diagnostics:
                       created:     2013-05-11T18:04:23.298132+00:00
                       details:     None
                       level:       DEBUG
                       message:     Image customization finished successfully.
                       source:      image-info
                       source_date: 2013-05-11T18:04:23.286869+00:00
        flavor:
                    id:    1
                    links:
                            href: https://example.com/compute/v2.0/flavors/1
                            rel:  bookmark
                        
                            href: https://example.com/compute/v2.0/flavors/1
                            rel:  self
        hostId:
        image:
                    id:    f1r57-1m4g3-1d
                    links:
                            href: https://example.com/compute/v2.0/images/f1r57-1m4g3-1d
                            rel:  bookmark

                            href: https://example.com/compute/v2.0/images/f1r57-1m4g3-1d
                            rel:  self

                            href: https:/example.com/image/v1.0/images/f1r57-1m4g3-1d
                            rel:  alternate
        key_name:        None
        links:
                       href: https://example.com/compute/v2.0/servers/4201
                       rel:  bookmark

                       href: https://example.com/compute/v2.0/servers/4201
                       rel:  self
        metadata:
                    os:    ubuntu
                    users: user
        progress:        100
        security_groups:
                       name: default
        status:          ACTIVE
        suspended:       False
        tenant_id:       s0m3-u53r-1d
        updated:         2013-06-17T07:57:50.054550+00:00
        user_id:         s0m3-u53r-1d
    4202 my example server 2
        accessIPv4:
        accessIPv6:
        addresses:
                    42:
                           OS-EXT-IPS:type: fixed
                           addr:            192.168.12.4
                           version:         4

                           OS-EXT-IPS:type: fixed
                           addr:            2002:648:2ffc:1222:a800:2ff:fee3:49f1
                           version:         6
        attachments:
                       firewallProfile: DISABLED
                       id:              nic-37231-0
                       ipv4:            192.168.12.4
                       ipv6:            2002:648:2ffc:1222:a800:2ff:fee3:49f1
                       mac_address:     aa:00:02:e3:49:f8
                       network_id:      42
        config_drive:
        created:         2013-05-11T18:03:41.471605+00:00
        diagnostics:
                       created:     2013-05-11T18:04:23.298132+00:00
                       details:     None
                       level:       DEBUG
                       message:     Image customization finished successfully.
                       source:      image-info
                       source_date: 2013-05-11T18:04:23.286869+00:00
        flavor:
                    id:    2
                    links:
                            href: https://example.com/compute/v2.0/flavors/2
                            rel:  bookmark

                            href: https://example.com/compute/v2.0/flavors/2
                            rel:  self
        hostId:
        image:
                    id:    53c0nd-1m4g3-1d
                    links:
                            href: https://example.com/compute/v2.0/images/53c0nd-1m4g3-1d
                            rel:  bookmark
                        
                            href: https://example.com/compute/v2.0/images/53c0nd-1m4g3-1d
                            rel:  self
                        
                            href: https:/example.com/image/v1.0/images/53c0nd-1m4g3-1d
                            rel:  alternate
        key_name:        None
        links:
                       href: https://example.com/compute/v2.0/servers/4202
                       rel:  bookmark
                   
                       href: https://example.com/compute/v2.0/servers/4202
                       rel:  self
        metadata:
                    os:    ubuntu
                    users: user
        progress:        100
        security_groups:
                       name: default
        status:          ACTIVE
        suspended:       False
        tenant_id:       s0m3-u53r-1d
        updated:         2013-06-17T07:57:50.054550+00:00
        user_id:         s0m3-u53r-1d
    ...

Detailed image listing
----------------------

Detailed listing

.. code-block:: console

    $ kamaki image list -l
    f1r57-1m4g3-1d Debian Base Alpha
        checksum:         9344d77620cde1dd77da...7b70badda34b26d782
        container_format: bare
        created_at:       2013-06-03 16:44:16
        deleted_at:
        disk_format:      diskdump
        is_public:        True
        location:         pithos://s0m3-5up3r-u53r-1d/pithos/debian_base1.diskdump
        owner:            s0m3-5up3r-u53r-1d
        properties:
                    description:    Debian 6.0.6 (Squeeze) Base System
                    gui:            No GUI
                    kernel:         2.6.32
                    os:             debian
                    osfamily:       linux
                    root_partition: 1
                    sortorder:      1
                    users:          root
        size:             474066944
        status:           available
        updated_at:       2013-06-03 16:44:16
    53c0nd-1m4g3-1d Beta Debian Base
        checksum:         9344d77620cde1dd77da...7b70badda34b26d782
        container_format: bare
        created_at:       2013-06-03 16:44:16
        deleted_at:
        disk_format:      diskdump
        is_public:        True
        location:         pithos://s0m3-5up3r-u53r-1d/pithos/debian_base2.diskdump
        owner:            s0m3-5up3r-u53r-1d
        properties:
                    description:    Debian 6.0.6 (Squeeze) Base System
                    gui:            No GUI
                    kernel:         2.6.32
                    os:             debian
                    osfamily:       linux
                    root_partition: 1
                    sortorder:      1
                    users:          root
        size:             474066944
        status:           available
        updated_at:       2013-06-03 16:44:16
    $ kamaki imagecompute list
    f1r57-1m4g3-1d Debian Base Alpha
        created:   2013-06-03T16:21:53+00:00
        links:
             href: https://example.com/cyclades/compute/v2.0/images/f1r57-1m4g3-1d
             rel:  bookmark
         
             href: https://example.com/cyclades/compute/v2.0/images/f1r57-1m4g3-1d
             rel:  self
         
             href: https://example.com/cyclades/image/v1.0/images/f1r57-1m4g3-1d
             rel:  alternate
        metadata:
          description:    Debian 6.0.6 (Squeeze) Base System
          gui:            No GUI
          kernel:         2.6.32
          os:             debian
          osfamily:       linux
          root_partition: 1
          sortorder:      1
          users:          root
        progress:  100
        status:    ACTIVE
        tenant_id: s0m3-5up3r-u53r-1d
        updated:   2013-06-03T16:21:53+00:00
        user_id:   s0m3-5up3r-u53r-1d
    53c0nd-1m4g3-1d Beta Debian Base
        created:   2013-06-03T16:21:53+00:00
        links:
             href: https://example.com/cyclades/compute/v2.0/images/53c0nd-1m4g3-1d
             rel:  bookmark
         
             href: https://example.com/cyclades/compute/v2.0/images/53c0nd-1m4g3-1d
             rel:  self
         
             href: https://example.com/cyclades/image/v1.0/images/53c0nd-1m4g3-1d
             rel:  alternate
        metadata:
          description:    Debian 6.0.6 (Squeeze) Base System
          gui:            No GUI
          kernel:         2.6.32
          os:             debian
          osfamily:       linux
          root_partition: 1
          sortorder:      1
          users:          root
        progress:  100
        status:    ACTIVE
        tenant_id: s0m3-5up3r-u53r-1d
        updated:   2013-06-03T16:21:53+00:00
        user_id:   s0m3-5up3r-u53r-1d

Filter listing by prefix, suffix or words in image names

.. code-block:: console

    $ kamaki image list --name-prefix=Debian
    f1r57-1m4g3-1d Debian Base Alpha
    $ kamaki image list --name-suffix=Base
    53c0nd-1m4g3-1d Beta Debian Base
    $ kamaki image list --name-like=Alpha
    f1r57-1m4g3-1d Debian Base Alpha
    $ kamaki image list --name-like=Beta
    53c0nd-1m4g3-1d Beta Debian Base
    $ kamaki image list --name-like="Debian Base"
    f1r57-1m4g3-1d Debian Base Alpha
    53c0nd-1m4g3-1d Beta Debian Base

Filter by owner and container format

.. code-block:: console

    $ kamaki image list --owner=s0m3-u53r-1d
    f1r57-1m4g3-1d Debian Base Alpha
    53c0nd-1m4g3-1d Beta Debian Base
    $ kamaki image list --container-format=bare
    f1r57-1m4g3-1d Debian Base Alpha
    53c0nd-1m4g3-1d Beta Debian Base
