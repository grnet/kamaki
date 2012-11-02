:orphan:

kamaki tool manual page
=======================

Synopsis
--------

**kamaki** [*group*] [*command*] [...] [*options*]


Description
-----------

:program:`kamaki` is a simple, yet intuitive, command-line tool for managing 
clouds. It can be used in three forms: as an interactive shell, as a command line tool or as a clients API for other applications.

To run kamaki as an interactive shell, type

    kamaki

To run kamaki as tool type

    kamaki <group> <command> [...] [options]

The kamaki clients API can be imported in python applications as kamaki.clients


List of available command groups:

config

    Edit configuration options. Config options are stored in ~/.kamakirc file.

history

    Access kamaki user history, which is stored in ~/.kamaki.history file.

server

    Manage compute API virtual machines.

flavor

    Manage compute API flavors.

network

    Manage compute API networks.

image 

    Manage compute API and glance images.

store

    Manage store API.


Options
-------

--help, -h              Show help message and exit.
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


history commands
****************

Show command user history, as stored in ~/.kamaki.history

* clean     clean up history


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

* list        list images
* info        get image details
* public      list public images
* shared      list shared images
* delete      delete image
* register    register an image
* meta        get image metadata
* members     get image members
* addmember   add a member to an image
* delmember   remove a member from an image
* setmembers  set the members of an image
* properties  get image properties
* setproperty update an image property
* addproperty add an image property
* delproperty delete an image property

network commands
****************

* list       list networks
* create     create a network
* info       get network details
* rename     update network name
* delete     delete a network
* connect    connect a server to a network
* disconnect disconnect a server from a network


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

