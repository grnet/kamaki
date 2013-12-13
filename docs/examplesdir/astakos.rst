Astakos
=======

`Astakos <http://www.synnefo.org/docs/synnefo/latest/astakos-api-guide.html>`_
is the synnefo implementation of a variant of OpenStack Keystone with custom
extentions. Kamaki offer tools for managing Astakos information.

.. node:: The underlying library that calls the API is part of the synnefo
    and it is called 'astakosclient'

User
----

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
        id: some-u53r-1d
        roles:
            id: 1
            name: default
        name: Example User

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

    $ kamaki user select z01db3rgs-u53r-1d
    Are you sure? [y/N]: y

    $ kamaki user uuid2name z01db3rgs-u53r-1d s0m3-u53r-1d
    z01db3rgs-u53r-1d: zoidberg@planetexpress.com
    s0m3-u53r-1d: someuser@example.com

Quotas and resources
--------------------

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

