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

user

    Get information from Astakos API

server

    Manage compute API virtual machines.

flavor

    Manage compute API flavors.

network

    Manage compute API networks.

image 

    Manage images on Plankton (and Compute).

file

    Manage Pithos+ API.


Hidden command groups
---------------------

livetest

    LIve tests that check kamaki against running services. To enable:
    kamaki config set livetest.cli livetest


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


user commands
*************

* authenticate      Authenticate a user, show user information


server commands
***************

* addr      List the addresses of all network interfaces on a server (VM)
* console   Get a VNC console to access an existing server (VM)
* create    Create a server (aka Virtual Machine)
* delete    Delete a server (VM)
* firewall  Set the server (VM) firewall profile for public networks
    * set   Set the firewall profile
    * get   Get the firewall profile
* ip        Manage floating IPs for the servers
    * attach    Attach a floating ip to a server with server_id
    * info      A floating IPs' details
    * detach    Detach floating ip from server
    * list      List all floating ips
    * create    Create a new floating IP
    * delete    Delete a floating ip
    * pools     List all floating pools of floating ips
* info      Detailed information on a Virtual Machine
* list      List Virtual Machines accessible by user
* metadata  Manage a server metadata
    * list      List server metadata
    * set       Add or update server metadata
    * delete    Delete a piece of server metadata
* reboot    Reboot a server (VM)
* rename    Set/update a server (VM) name
* shutdown  Shutdown an active server (VM)
* start     Start an existing server (VM)
* stats     Get server (VM) statistics
* resize    Set a different flavor for an existing server
* wait      Wait for server to finish [BUILD, STOPPED, REBOOT, ACTIVE]


flavor commands
***************

* list       list flavors
* info       get flavor details


image commands
**************

* list           List images accessible by user
* info           Get image metadata
* meta           Manage image metadata
    * set       Add / update metadata and properties for an image
    * delete    Remove/empty image metadata and/or custom properties
* register       (Re)Register an image
* unregister     Unregister an image (does not delete the image file)
* shared         List shared images
    * compute        Compute Image API commands
    * list       List images
    * delete     Delete image
    * info       Get image details
    * properties Manage properties related to OS installation in an image
        * delete Delete a property from an image
        * get    Get an image property
        * list   List all image properties
        * set    Add / update a set of properties for an image
* members        Manage members (users who can modify an image)
    * add        Add a member to an image
    * delete     Remove a member from an image
    * list       List members of an image
    * set        Set the members of an image


network commands
****************

* connect       Connect a server to a network
* create        Create an (unconnected) network
* delete        Delete a network
* disconnect    Disconnect a nic that connects a server to a network
* info          Detailed information on a network
* list          List networks
* rename        Set the name of a network


file commands
**************

* append         Append local file to remote file
* cat            Print a file to console
* copy           Copy an object
* containerlimit Container size limit commands
    * set        Set container data limit
    * get        Get container data limit
* create         Create a container
* delete         Delete a container [or an object]
* download       Download a file or directory
* group          Manage access groups and group members
    * delete     Delete a user group
    * list       List groups and group members
    * set        Set a user group
* hashmap        Get the hashmap of an object
* info           Get information for account [, container [or object]]
* list           List containers, object trees or objects in a directory
* manifest       Create a remote file with uploaded parts by manifestation
* metadata       Metadata are attached on objects (key:value pairs)
    * delete     Delete metadata with given key
    * get        Get metadatum
    * set        Set a piece of metadata
* mkdir          Create a directory
* move           Copy an object
* overwrite      Overwrite part (from start to end) of a remote file
* permissions    Manage user and group accessibility for objects
    * delete     Delete all permissions set on object
    * get        Get read and write permissions of an object
    * set        Set permissions for an object
* publish        Publish an object
* purge          Purge a container
* quota          Get  quota for account
* sharers        List the accounts that share objects with default account
* touch          Create an empty object (file)
* truncate       Truncate remote file up to a size
* unpublish      Unpublish an object
* upload         Upload a file or directory
* versioning     Manage the versioning scheme of current pithos user account
    * get        Get  versioning for account or container
    * set        Set versioning mode (auto, none) for account or container
    * versions   Get the version list of an object


test commands (hidden)
**********************

* all         test all clients
* args        test how arguments are treated by kamaki
* astakos     test Astakos client
* cyclades    test Cyclades client
* error       Create an error message with optional message
* image       test Image client
* pithos      test Pithos client
* prints      user-test print methods for lists and dicts


Author
------

Synnefo development team <synnefo-devel@googlegroups.com>.

