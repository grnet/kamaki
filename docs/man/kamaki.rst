:orphan:

kamaki tool manual page
=======================

Synopsis
--------

**kamaki** [*group*] [*command*] [...] [*options*] [*arguments*]
**kamaki-shell** [*group*] [*command*] [...] [*arguments*]


Description
-----------

:program:`kamaki` is a simple, yet intuitive, command-line tool for managing 
clouds. It can be used in three forms: as an interactive shell
(`kamaki-shell`), as a command line tool (`kamaki`) or as a clients API for
other applications (`kamaki.clients`).

To run `kamaki` as an interactive shell, type

    kamaki-shell

To run `kamaki` as tool type

    kamaki <group> <command> [...] [options]

The kamaki clients API can be imported in python applications as
`kamaki.clients`


List of available command groups:

user
    Astakos/Identity API commands

project
    Astakos project API commands

membership
    Astakos project membership API commands

quota
    Astakos/Account API commands for quotas

resource
    Astakos/Account API commands for resources

file
    Pithos+/Storage object level API commands

container
    Pithos+/Storage container level API commands

group
    Pithos+/Storage user groups

sharer
    Pithos+/Storage sharer accounts

server
    Cyclades/Compute API server commands

flavor
    Cyclades/Compute API flavor commands

image
    Cyclades/Plankton API image commands

imagecompute
    Cyclades/Compute API image commands

network
    Networking API network commands

subnet
    Networking API network commands

ip
    Networking API floatingip commands

port
    Networking API network Commands

config
    Kamaki option and cloud configuration

history
    Kamaki command history


Hidden command groups
---------------------

livetest
    Live tests that check kamaki against running services. To enable:
    kamaki config set livetest.cli livetest

service
    Astakos API service commands

endpoint
    Astakos API endpoints commands

commission
    Astakos API commission commands


Options
-------

.. code-block:: console

    --help, -h              Show help message and exit.
    -v                      Use verbose output.
    -d                      Use debug output.
    -o KEY=VAL              Override a config value (can be repeated)
    --cloud CLOUD           Choose a cloud to connect to


Commands
--------

user
****

* authenticate  Authenticate a user, show user information
* info          Get info for (current) session user
* uuid2name     Get user name(s) from uuid(s)
* authenticate  Authenticate a user and get all authentication information
* list          List (cached) session users
* add           Authenticate a user by token and add to kamaki session (cache)
* name2uuid     Get user uuid(s) from name(s)
* select        Select a user from the (cached) list as the current session user
* delete        Delete a user (token) from the (cached) list of session users

project
*******

* info          Get details for a project
* unsuspend     Resume a suspended project (special privileges needed)
* suspend       Suspend a project (special privileges needed)
* list          List all projects
* create        Apply for a new project
* modify        Modify a project
* terminate     Terminate a project (special privileges needed)
* application   Application management commands
* membership    Project membership management commands
* reinstate     Reinstate a terminated project (special privileges needed)

membership
**********

* info      Details on a membership
* enroll    Enroll somebody to a project you manage
* join      Join a project
* list      List all memberships
* accept    Accept a membership for a project you manage
* leave     Leave a project you have membership to
* remove    Remove a membership for a project you manage
* reject    Reject a membership for a project you manage
* cancel    Cancel your (probably pending) membership to a project

quota
*****

* list          Get user quotas
* info          Get quota for a service (cyclades, pithos, astakos)

resource
********

* list          List user resources

file
****

* info      Get information/details about a file
* truncate  Truncate remote file up to size
* mkdir     Create a directory ( create --content-type='applcation/directory' )
* create    Create an empty file
* move      Move objects, even between different accounts or containers
* list      List all objects in a container or a directory object
* upload    Upload a file
* cat       Fetch remote file contents
* modify    Modify the attributes of a file or directory object
* append    Append local file to (existing) remote object
* download  Download a remove file or directory object to local file system
* copy      Copy objects, even between different accounts or containers
* overwrite Overwrite part of a remote file
* delete    Delete a file or directory object

container
*********

* info      Get information about a container
* modify    Modify the properties of a container
* create    Create a new container
* list      List all containers, or their contents
* empty     Empty a container
* delete    Delete a container

group
*****

* create    Create a group of users
* list      List all groups and group members
* delete    Delete a user group

sharer
******

* info      Details on a Pithos+ sharer account (default: current account)
* list      List accounts who share file objects with current user

server
******

* info      Detailed information on a Virtual Machine
* modify    Modify attributes of a virtual server
* create    Create a server (aka Virtual Machine)
* list      List virtual servers accessible by user
* reboot    Reboot a virtual server
* start     Start an existing virtual server
* shutdown  Shutdown an active virtual server
* delete    Delete a virtual server
* console   Create a VMC console and show connection information
* wait      Wait for server to finish [BUILD, STOPPED, REBOOT, ACTIVE]

flavor
******

* list       list flavors
* info       get flavor details

image
*****

* info          Get image metadata
* list          List images accessible by user
* register      (Re)Register an image file to an Image service
* modify        Add / update metadata and properties for an image
* unregister    Unregister an image (does not delete the image file)

imagecompute
************

* info      Get detailed information on an image
* list      List images
* modify    Modify image properties (metadata)
* delete    Delete an image (WARNING: image file is also removed)

network
*******

* info: Get details about a network
* disconnect: Disconnect a network from a device
* modify: Modify network attributes
* create: Create a new network
* list: List networks
* connect: Connect a network with a device (server or router)
* delete: Delete a network

subnet
******

* info      Get details about a subnet
* list      List subnets
* create    Create a new subnet
* modify    Modify the attributes of a subnet

ip
**

* info      Details for an IP
* list      List reserved floating IPs
* attach    Attach a floating IP to a server
* pools     List pools of floating IPs
* release   Release a floating IP
* detach    Detach a floating IP from a server
* reserve   Reserve a floating IP

port
****

* info      Get details about a port
* list      List all ports
* create    Create a new port (== connect server to network)
* modify    Modify the attributes of a port
* delete    Delete a port (== disconnect server from network)
* wait      Wait for port to finish [ACTIVE, DOWN, BUILD, ERROR]

config
******

* list       list configuration options
* get        get a configuration option
* set        set a configuration option
* del        delete a configuration option

history
*******

Command user history, as stored in ~/.kamaki.history

* show      show intersession history
* clean     clean up history
* run       run/show previously executed command(s)


livetest (hidden)
*****************

* all         test all clients
* args        test how arguments are treated by kamaki
* astakos     test Astakos client
* cyclades    test Cyclades client
* error       Create an error message with optional message
* image       test Image client
* pithos      test Pithos client
* prints      user-test print methods for lists and dicts

service (hidden)
****************

* list          List available services
* uuid2username Get service username(s) from uuid(s)
* quotas        Get service quotas
* username2uuid Get service uuid(s) from username(s)

endpoint (hidden)
*****************

* list      Get endpoints service endpoints

commission (hidden)
*******************

* info      Get commission info (special privileges required)
* resolve   Resolve multiple commissions (special privileges required)
* accept    Accept a pending commission  (special privileges required)
* reject    Reject a pending commission (special privileges required)
* issue     Issue commissions as a json string (special privileges required)
* pending   List pending commissions (special privileges required)


Author
------

Synnefo development team <synnefo-devel@googlegroups.com>.

