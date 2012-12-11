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

astakos

    Get information from astakos API

server

    Manage compute API virtual machines.

flavor

    Manage compute API flavors.

network

    Manage compute API networks.

image 

    Manage compute API and Plankton images.

store

    Manage store API.


Options
-------

.. code-block:: console

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

Command user history, as stored in ~/.kamaki.history

* all       show user history
* clean     clean up history


astakos commands
****************

* admin userinfo    Get user info, provided you have admin privileges
* authenticate      Authenticate a user, show user information
* service list      List cloud services associated with astakos
* service userinfo  Get user info with service token


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
* wait       wait for server to finish [BUILD, STOPPED, REBOOT, ACTIVE]


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
* reregister  re-register an image (preserve and update properties)
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

* append    Append local file to (existing) remote object
* cat       Print a file to console
* copy      Copy an object
* create    Create a container or a directory object
* delete    Delete a container [or an object]
* delgroup  Delete a user group on an account
* delmeta   Delete an existing metadatum of account [, container [or object]]
* delpermissions    Delete all sharing permissions
* download  Download a file
* group     Get user groups details for account
* hashmap   Get the hashmap of an object
* info      Get information for account [, container [or object]]
* list      List containers, object trees or objects in a directory
* manifest  Create a remote file with uploaded parts by manifestation
* meta      Get custom meta-content for account [, container [or object]]
* mkdir     Create a directory
* move      Copy an object
* overwrite Overwrite part (from start to end) of a remote file
* permissions   Get object read/write permissions
* publish   Publish an object
* purge     Purge a container
* quota     Get quota for account [or container]
* setgroup  Create/update a new user group on account
* setmeta   Set a new metadatum for account [, container [or object]]
* setpermissions    Set sharing permissions
* setquota  Set new quota (in KB) for account [or container]
* setversioning Set new versioning (auto, none) for account [or container]
* sharers   List the accounts that share objects with default account
* truncate  Truncate remote file up to a size
* unpublish Unpublish an object
* upload    Upload a file
* versioning    Get  versioning for account [or container ]
* versions  Get the version list of an object



Author
------

GRNET development team <synnefo-devel@googlegroups.com>.

