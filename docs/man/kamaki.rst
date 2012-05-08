:orphan:

kamaki tool manual page
=======================

Synopsis
--------

**kamaki** <*group*> <*command*> [*options*]


Description
-----------

:program:`kamaki` is a simple, yet intuitive, command-line tool for managing 
clouds.

List of available groups:

config

    Edit configuration options. Config options are stored in ~/.kamakirc file.

server

    Manage compute API virtual machines.

flavor

    Manage compute API flavors.

image

    Manage compute API images.

network

    Manage compute API networks.

glance

    Manage Glance API images.

store

    Manage store API.


Options
-------

--help                  Show help message and exit.
-v                      Use verbose output.
-d                      Use debug output.
-o KEY=VAL              Override a config value (can be used multiple times)


Commands
--------

config commands
***************

* list       list configuration options
* get        get a configuration option
* set        set a configuration option
* del        delete a configuration option



server commands
***************

* list       list servers
* info       get server details
* create     create server
* rename     update server name
* delete     delete server
* reboot     reboot server
* start      start server
* shutdown   shutdown server
* console    get a VNC console
* firewall   set the firewall profile
* addr       list server addresses
* meta       get server metadata
* addmeta    add server metadata
* setmeta    update server metadata
* delmeta    delete server metadata
* stats      get server statistics


flavor commands
***************

* list       list flavors
* info       get flavor details


image commands and options
**************************

* list       list images
* info       get image details
* delete     delete image
* meta       get image metadata
* addmeta    add image metadata
* setmeta    update image metadata
* delmeta    delete image metadata


network commands
****************

* list       list networks
* create     create a network
* info       get network details
* rename     update network name
* delete     delete a network
* connect    connect a server to a network
* disconnect disconnect a server from a network


glance commands
***************

* list       list images
* meta       get image metadata
* register   register an image
* members    get image members
* shared     list shared images
* addmember  add a member to an image
* delmember  remove a member from an image
* setmembers set the members of an image


store commands
**************

* create     create a container
* container  get container info
* upload     upload a file
* download   download a file
* delete     delete a file


Author
------

GRNET development team <synnefo@lists.grnet.gr>.

