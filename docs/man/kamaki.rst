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


Hidden command groups
---------------------

quotaholder

    A client for quotaholder API. to enable:
    kamaki config set quotaholder.cli hotaholder_cli
    kamaki config set quotaholder.url <quotaholder server url>

livetest

    LIve tests that check kamaki against running services. To enable:
    kamaki config set livetest.cli livetest_cli


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

* show      show intersession history
* clean     clean up history
* run       run/show previously executed command(s)


astakos commands
****************

* authenticate      Authenticate a user, show user information


server commands
***************

* addr      List the addresses of all network interfaces on a server (VM)
* console   Get a VNC console to access an existing server (VM)
* create    Create a server (aka Virtual Machine)
* delete    Delete a server (VM)
* delmeta   Delete server (VM) metadata
* firewall  Set the server (VM) firewall profile on VMs public network
* info      Detailed information on a Virtual Machine
* list      List Virtual Machines accessible by user
* meta      Get a server's metadatum
* reboot    Reboot a server (VM)
* rename    Set/update a server (VM) name
* setmeta   set server (VM) metadata
* shutdown  Shutdown an active server (VM)
* start     Start an existing server (VM)
* stats     Get server (VM) statistics
* wait      Wait for server to finish [BUILD, STOPPED, REBOOT, ACTIVE]


flavor commands
***************

* list       list flavors
* info       get flavor details


image commands and options
**************************

* addmember     Add a member to an image
* addproperty   Add an OS-related property to an image
* delete        Delete an image (image file remains intact)
* delmember     Remove a member from an image
* delproperty   Delete a property of an image
* info          Get detailed information on an image
* list          List images
* members       Get image members
* meta          Get image metadata
* properties    Get properties related to OS installation in an image
* public        List public images
* register      (Re)Register an image
* setmembers    Set the members of an image
* setproperty   Update an existing property in an image
* shared        List images shared by a member


network commands
****************

* connect       Connect a server to a network
* create        Create an (unconnected) network
* delete        Delete a network
* disconnect    Disconnect a nic that connects a server to a network
* info          Detailed information on a network
* list          List networks
* rename        Set the name of a network


store commands
**************

* append            Append local file to (existing) remote object
* cat               Print remote file contents to console
* copy              Copy an object from container to (another) container
* create            Create a container
* delete            Delete a container [or an object]
* delgroup          Delete a user group
* delmeta           Delete metadata from account, container or object
* delpermissions    Delete all permissions set on object
* download          Download remote object as local file
* group             Get groups and group members
* hashmap           Get the hash-map of an object
* info              Get detailed info for account, containers or objects
* list              List containers, object trees or objects in a directory
* manifest          Create a remote file of uploaded parts by manifestation
* meta              Get metadata for account, containers or objects
* mkdir             Create a directory
* move              Copy an object
* overwrite         Overwrite part (from start to end) of a remote file
* permissions       Get read and write permissions of an object
* publish           Publish the object and print the public url
* purge             Delete a container and release related data blocks
* quota             Get quota (in KB) for account or container
* setgroup          Set a user group
* setmeta           Set a piece of metadata for account, container or object
* setpermissions    Set permissions for an object
* setquota          Set new quota (in KB) for account or container
* setversioning     Set versioning mode (auto, none) for account or container
* sharers           List the accounts that share objects with current user
* touch             Create an empty object (file)
* truncate          Truncate remote file up to a size
* unpublish         Unpublish an object
* upload            Upload a file
* versioning        Get  versioning for account or container
* versions          Get the list of object versions


quotaholder commands (hidden)
*****************************

accept, ack, add, create, get, init, issue, list, query, reject, release, reset, resolve, set


test commands (hidden)
**********************

* all         test all clients
* args        Test how arguments are treated by kamaki
* astakos     test Astakos client
* cyclades    test Cyclades client
* error       Create an error message with optional message
* image       test Image client
* pithos      test Pithos client
* prints      user-test print methods for lists and dicts


Author
------

GRNET development team <synnefo-devel@googlegroups.com>.

