:orphan:

kamaki tool manual page
=======================

Synopsis
--------

**kamaki** [*group*] [*command*] [...] [*options*] [*arguments*]

Description
-----------

:program:`kamaki` is a simple, yet intuitive, command-line tool for managing
clouds. It can be used in three forms: as an interactive shell
(`kamaki-shell`), as a command line tool (`kamaki`) or as a clients API for
other applications (`kamaki.clients`).

To run `kamaki`

    kamaki <group> <command> [...] [options]

The kamaki clients API can be imported in python applications as
`kamaki.clients`

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

Kamaki Management Commands
**************************

config
    get
        Show a configuration option
    set
        Set a configuration option
    list
        List all configuration options
    delete
        Delete a configuration option

help
    List available commands or show help message for selected commands

history
    clean
        Clean up history (permanent)
    show
        Show history

scripts verifyfs
        Verify/Fix the structure of directory objects inside a container

Astakos/Account/Identity API
****************************

membership
    info
        Details on a  project membership
    list
        List all project memberships
    remove
        Remove a project membership for a project you manage
    leave
        Leave a project you have membership to
    accept
        Accept a membership for a project you manage
    reject
        Reject a membership for a project you manage
    cancel
        Cancel your (probably pending) membership to a project


project
    info
        Get details for a project
    unsuspend
        Resume a suspended project (special privileges needed)
    suspend
        Suspend a project (special privileges needed)
    join
        Join a project
    modify
        Modify properties of a project
    create
        Apply for a new project
    dismiss
        Dismiss your denied application
    list
        List all projects
    deny
        Deny an application (special privileges needed)
    terminate
        Terminate a project (special privileges needed)
    enroll
        Enroll a user to a project
    cancel
        Cancel your application
    approve
        Approve an application (special privileges needed)
    reinstate
        Reinstate a terminated project (special privileges needed)

quota list
     Show user quotas

resource list
    Show user resources and usage

user
    info
        Get info for (current) session user
    uuid2name
        Get user name(s) from uuid(s)
    authenticate
        Authenticate a user and get all authentication information
    list
        List (cached) session users
    add
        Authenticate a user by token and add to session user list (cache)
    name2uuid
        Get user uuid(s) from name(s)
    select
        Select a user from the (cached) list as the current session user
    delete
        Delete a user (token) from the list of session users


Pithos+/Object Storage API
**************************

container
    info
        Get information about a container
    modify
        Modify the properties of a container
    create
        Create a new container
    list
        List all containers, or their contents
    reassign
        Assign a container to a different project
    empty
        Empty a container
    delete
        Delete a container

file
    info
        Get information/details about a file
    copy
        Copy objects, even between different accounts or containers
    truncate
        Truncate remote file up to size
    mkdir
        Create a directory object
    create
        Create an empty object
    move
        Move objects, even between different accounts or containers
    list
        List all objects in a container or a directory
    upload
        Upload a file
    publish
        Publish an object (creates a public URL)
    unpublish
        Unpublish an object
    modify
        Modify the attributes of a file or directory object
    append
        Append local file to (existing) remote object
    download
        Download a remote file or directory object to local file system
    cat
        Fetch remote file contents
    overwrite
        Overwrite part of a remote file
    delete
        Delete a file or directory object

group
    create
        Create a group of users
    list
        list all groups and group members
    delete
        Delete a user group


sharer
    info
        Details on a Pithos+ sharer account (default: current account)
    list
        List accounts who share file objects with current user

Cyclades/Compute API
********************

flavor
    info
        Detailed information on a hardware flavor
    list
        List available hardware flavors


imagecompute
    info
        Get detailed information on an image
    list
        List images
    modify
        Modify image properties (metadata)
    delete
        Delete an image (WARNING: image file is also removed)


server
    info
        Detailed information on a Virtual Machine
    console
        Create a VNC console and show connection information
    modify
        Modify attributes of a virtual server
    create
        Create a server (aka Virtual Machine)
    list
        List virtual servers accessible by user
    reboot
        Reboot a virtual server
    start
        Start an existing virtual server
    shutdown
        Shutdown an active virtual server
    reassign
        Assign a virtual server to a different project
    delete
        Delete a virtual server
    wait
        Wait for server to change its status (default: --while BUILD)


Cyclades/Block Storage API
**************************

snapshot
    info
        Get details about a snapshot
    list
        List snapshots
    create
        Create a new snapshot
    modify
        Modify a snapshot's properties
    delete
        Delete a snapshot

volume
    info
        Get details about a volume
    list
        List volumes
    create
        Create a new volume
    modify
        Modify a volume's properties
    reassign
        Reassign volume to a different project
    delete
        Delete a volume
    type
        Get volume type details
    types
        List volume types
    wait
        Wait for volume to finish (default: --while creating)

Cyclades/Network API
********************

ip
    info
        Get details on a floating IP
    create
        Reserve an IP on a network
    list
        List reserved floating IPs
    attach
        Attach an IP on a virtual server
    reassign
        Assign a floating IP to a different project
    detach
        Detach an IP from a virtual server
    delete
        Unreserve an IP (also delete the port, if attached)

network
    info
        Get details about a network
    disconnect
        Disconnect a network from a device
    list
        List networks
    create
        Create a new network (default type: MAC_FILTERED)
    modify
        Modify network attributes
    connect
        Connect a network with a device (server or router)
    reassign
        Assign a network to a different project
    delete
        Delete a network


port
    info
        Get details about a port
    list
        List all ports
    create
        Create a new port (== connect server to network)
    modify
        Modify the attributes of a port
    delete
        Delete a port (== disconnect server from network)
    wait
        Wait for port to finish (default: --while BUILD)

subnet
    info
        Get details about a subnet
    list
        List subnets
    create
        Create a new subnet
    modify
        Modify the attributes of a subnet

Plankton/Image API
******************

image
    info
        Get image metadata
    list
        List images accessible by user
    register
        (Re)Register an image file to an Image service
    modify
        Add / update metadata and properties for an image
    unregister
        Unregister an image (does not delete the image file)


Hidden commands
***************

service
    list
        List available services
    uuid2username
        Get service username(s) from uuid(s)
    quotas
        Get service quotas
    username2uuid
        Get service uuid(s) from username(s)
    * to enable: $ kamaki config set service_cli astakos
    * to disable: $ kamaki config delete service_cli

endpoint list:
     Get endpoints service endpoints
    * to enable: $ kamaki config set endpoint_cli astakos
    * to disable: $ kamaki config delete endpoint_cli

commission
    info
        Get commission info (special privileges required)
    resolve
        Resolve multiple commissions (special privileges required)
    accept
        Accept a pending commission  (special privileges required)
    reject
        Reject a pending commission (special privileges required)
    issue
        Issue commissions as a json string (special privileges required)
    pending
        List pending commissions (special privileges required)
    * to enable: $ kamaki config set commission_cli astakos
    * to disable: $ kamaki config delete commission_cli


Author
------

Synnefo development team <synnefo-devel@googlegroups.com>.

