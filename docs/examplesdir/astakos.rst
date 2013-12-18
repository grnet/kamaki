Astakos
=======

`Astakos <http://www.synnefo.org/docs/synnefo/latest/astakos-api-guide.html>`_
is the synnefo implementation of a variant of OpenStack Keystone with custom
extentions. Kamaki offer tools for managing Astakos information.

.. note:: The underlying library that calls the API is part of the synnefo
    and it is called 'astakosclient'

User
----

The *authenticate* command will send a token to the server, for authentication.
Be default, the token provided in the cloud configuration (config file) will be
used:

.. code-block:: console

    $ kamaki user authenticate
    ...
    endpoints:
            SNF:uiURL: https://example.com/ui/
            versionId: 
            region: default
            publicURL: https://example.com/admin
        endpoints_links:
        type: admin
        name: cyclades_admin
    user:
        roles_links:
        id: s0m3-u53r-1d
        roles:
            id: 1
            name: default
        name: Example User

To authenticate other users, provide their token, as shown bellow:

.. code-block:: console

    $ kamaki user add z01db3rgs-u53r-t0k3n
    ...
    endpoints:
            SNF:uiURL: https://example.com/ui/
            versionId: 
            region: default
            publicURL: https://example.com/admin
        endpoints_links:
        type: admin
        name: cyclades_admin
    user:
        roles_links:
        id: z01db3rgs-u53r-1d
        roles:
            id: 1
            name: default
        name: Dr. Harold Zoidberg
    $ kamaki user list
    s0m5-u53r-1d       Example User
    z01db3rgs-u53r-1d  Dr. Harold Zoidberg

At any time, get the current user's information, or provide a user id for
information on any existing user. In the following example, "Example User" is
the current user, meaning that all kamaki commands will run for him/her.

.. code-block:: console

    $ kamaki user info
    roles_links:
    id: s0m3-u53r-1d
    roles:
        id: 1
        name: default
    name: Example User

    $ kamaki user info --uuid=z01db3rgs-u53r-1d
    roles_links:
    id: z01db3rgs-u53r-1d
    roles:
        id: 1
        name: default
    name: EDr. Harold Zoidberg

You can switch between authenticated users

.. code-block:: console

    $ kamaki user select z01db3rgs-u53r-1d
    Are you sure? [y/N]: y

Use the *uuid2name* and *name2uuid* commands to map uuids to usernames and vice
versa.

.. code-block:: console

    $ kamaki user uuid2name z01db3rgs-u53r-1d s0m3-u53r-1d
    z01db3rgs-u53r-1d: zoidberg@planetexpress.com
    s0m3-u53r-1d: someuser@example.com

Quotas and resources
--------------------

Each user is assigned a set of limits on various resources:

.. code-block:: console

    $ kamaki quota list
    system:
        cyclades.disk:
            usage: 0B
            limit: 100GiB
            pending: 0B
        cyclades.vm:
            usage: 0
            limit: 2
            pending: 0
        pithos.diskspace:
            usage: 5.11GiB
            limit: 50GiB
            pending: 0B
        cyclades.ram:
            usage: 0B
            limit: 8GiB
            pending: 0B
        cyclades.cpu:
            usage: 0
            limit: 8
            pending: 0
        cyclades.network.private:
            usage: 0
            limit: 5
            pending: 0

If the information above is not clear, use *resource list* for descriptions
fetched fresh from the server:

.. code-block:: console

    $ kamaki resource list
    cyclades.disk:
        service: cyclades_compute
        description: Virtual machine disk size
        unit: bytes
        allow_in_projects: True
    cyclades.vm:
        service: cyclades_compute
        description: Number of virtual machines
        unit: None
        allow_in_projects: True
    pithos.diskspace:
        service: pithos_object-store
        description: Pithos account diskspace
        unit: bytes
        allow_in_projects: True
    cyclades.ram:
        service: cyclades_compute
        description: Virtual machine memory size
        unit: bytes
        allow_in_projects: True
    cyclades.cpu:
        service: cyclades_compute
        description: Number of virtual machine processors
        unit: None
        allow_in_projects: True
    cyclades.network.private:
        service: cyclades_compute
        description: Number of private networks
        unit: None
        allow_in_projects: True

Projects
--------

If the standard policy of a synnefo deployment does not meet the needs of an
organization, they should make a request for a *synnefo project*.

First, create a file with the project specification. The specification should
be in json format, as described at the
`project API <http://www.synnefo.org/docs/synnefo/latest/project-api-guide.html#create-a-project>`_
(see "Example request").

Let's request a project of 48 CPUs, with an 8 CPU limit per member. Also 200GB
storage space per user, without a project limit.

.. code-block:: console

    $ cat > my_project.txt
    {
        "name": "My example project",
        "homepage": "http://www.exampleorganization.org",
        "description": "An example testing project",
        "comments": "We need more CPUs and more disk space",
        "end_date": "2031-02-13",
        "resources": {
            "cyclades.vm": {
                "project_capacity": 48,
                "member_capacity": 8
            },
            "pithos.diskspace": {
                "project_capacity": None,
                "member_capacity": 53687091200
            }
        }
    }
    $ cat my_project.txt | kamaki project create

List all the projects to see if our project is listed

.. code-block:: console

    $ kamaki project list
    1 newtitle.film.example.com
        end_date: 2014-03-31T00:00:00+00:00
        description: Our new film project
        join_policy: auto
        max_members: None
        applicant: s0m3-4pp1ic4n7
        leave_policy: auto
        creation_date: 2013-01-31T09:36:04.061130+00:00
        application: 4
        state: active
        start_date: 2013-01-31T00:00:00+00:00
        owner: s0m3-4pp1ic4n7
        homepage: http://example.com/film
        resources:
    29 many.quotas
        end_date: 2013-12-12T00:00:00+00:00
        description: I need more quotas
        join_policy: moderated
        max_members: 10
        applicant: s0m3-u53r-1d
        leave_policy: auto
        creation_date: 2013-02-14T09:26:23.034177+00:00
        application: 108
        state: active
        start_date: 2013-02-14T00:00:00+00:00
        owner: s0m3-u53r-1d
        homepage: http://example.com
        resources:
            cyclades.disk:
                member_capacity: 109951162777600
                project_capacity: None
            cyclades.vm:
                member_capacity: 1000
                project_capacity: None
            cyclades.cpu:
                member_capacity: 2000
                project_capacity: None
            cyclades.ram:
                member_capacity: 4398046511104
                project_capacity: None
            pithos.diskspace:
                member_capacity: 107374182400
                project_capacity: None
            cyclades.floating_ip:
                member_capacity: 1000
                project_capacity: None

No, our project is not in the list yet, probably because we wait for (manual)
authorization.

To get information on a project:

.. code-block:: console

    $ kamaki project info 29
    name: many.quotas
    id: 29
    end_date: 2013-12-12T00:00:00+00:00
    description: I need more quotas
    join_policy: moderated
    max_members: 10
    applicant: s0m3-u53r-1d
    leave_policy: auto
    creation_date: 2013-02-14T09:26:23.034177+00:00
    application: 108
    state: active
    start_date: 2013-02-14T00:00:00+00:00
    owner: s0m3-u53r-1d
    homepage: http://example.com
    resources:
        cyclades.disk:
            member_capacity: 109951162777600
            project_capacity: None
        cyclades.vm:
            member_capacity: 1000
            project_capacity: None
        cyclades.cpu:
            member_capacity: 2000
            project_capacity: None
        cyclades.ram:
            member_capacity: 4398046511104
            project_capacity: None
        pithos.diskspace:
            member_capacity: 107374182400
            project_capacity: None
        cyclades.floating_ip:
            member_capacity: 1000
            project_capacity: None

Project membership
------------------

Assuming that our project has been approved and assigned the id 42, we can now
see its details and assign users to benefit from it.

.. code-block:: console

    $ kamaki project info 42
        name: My example project
        id: 42
        end_date: 2031-02-13T00:00:00+00:00
        description: An example testing project
        commends: We need more CPUs and more disk space
        join_policy: moderated
        applicant: s0m3-u53r-1d
        leave_policy: auto
        creation_date: <NOW>
        application: 109
        state: active
        start_date: <NOW>
        owner: s0m3-u53r-1d
        homepage: http://example.com
        resources:
            cyclades.disk:
                member_capacity: 107374182400
                project_capacity: None
            cyclades.vm:
                member_capacity: 2
                project_capacity: None
            cyclades.cpu:
                member_capacity: 8
                project_capacity: 48
            cyclades.ram:
                member_capacity: 6442450944
                project_capacity: None
            pithos.diskspace:
                member_capacity: 53687091200
                project_capacity: None
            cyclades.floating_ip:
                member_capacity: 2
                project_capacity: None

Great! Now, we should allow some users to benefit from this project:

.. code-block:: console

    $ kamaki membership enroll 42 my_favorite@user.example.com
    Membership id: 128345
    $ kamaki membership enroll 42 that_guy@user.example.com
    Membership id: 128346
    $ kamaki membership list --with-project-id=42
    128345
        42 my_favorite@user.example.com OK
    238346
        42 that_guy@user.example.com OK

We changed our minds: we don't want the last user to be part of the project:

    .. code-block:: console

        $ kamaki membership remove 238346 "Our cooperation was not productive"

Later, the removed user attempts to apply for our project:

.. code-block:: console    

    that_guy$ kamaki membership join 42

We may reject his application:

.. code-block:: console

    $ kamaki memebrship list
    128345
        42 my_favorite@user.example.com OK
    238347
        42 that_guy@user.example.com PENDING
    $ kamaki membership reject 238347 "Not in need of a new partner"

or accept:

.. code-block:: console    

    $ kamaki membership accept 238347

In the later case, the user decided to leave the project:

.. code-block:: console    

    that_guy$ kamaki membership leave 42
