Clients reference
=================

Kamaki library API consists of clients corresponding to the Synnefo API, which
is equivalent to the OpenStack API with some extensions. In some cases, kamaki
implements the corresponding OpenStack libraries as separate clients and the
Synnefo extensions as class extensions of the former.

The kamaki library API consists of the following clients:

In ``kamaki.clients.astakos``::

    AstakosClient           An Identity and Account client for Synnefo API
    OriginalAstakosClient   The client of the Synnefo astakosclient package
    LoggedAstakosClient     The original client with kamaki-style logging 
    CachedAstakosClient     Some calls are cached to speed thinks up

.. note:: Use ``AstakosClient`` if you are not sure

TO BE COMPLETED

Astakos / Identity
------------------

Synnefo API: https://www.synnefo.org/docs/synnefo/latest/identity-api-guide.html

The core functionality of this module is to authenticate a user and provide user
(e.g., email, unique user id)

Authenticate user
^^^^^^^^^^^^^^^^^
**Example:** Authenticate user, get name and uuid

.. literalinclude:: examples/astakos-authenticate.py
    :language: python
    :lines: 34-
    :linenos:

.. note:: the ``authenticate`` method returns a dict, which is defined by the
    Synnefo API (not by kamaki)

Astakos / Resources and Quotas
------------------------------

Synnefo API: https://www.synnefo.org/docs/synnefo/latest/api-guide.html#resource-and-quota-service-api-astakos

This API provides information on available resources, resource usage and quota
limits.

Resource quotas
^^^^^^^^^^^^^^^

**Example**: Resource usage and limits for number of VMs and IPs

.. literalinclude:: examples/astakos-quotas.py
    :language: python
    :lines: 34-
    :linenos:

.. note:: Quotas are defined by projects (see next section). Every user is
    member to a personal project (the "system" project) which is identitified by
    the uuid of the user, but they may draw resources from other projects as
    well. In this script we only got the quota information related to the system
    project and we did that with this line of code
    ``my_resources = all_resources[uuid]``

Astakos / Projects
------------------

Synnefo API: https://www.synnefo.org/docs/synnefo/latest/api-guide.html#project-service-api

The relation between projects, users and resources::

    cloud resources: VMs, CPUs, RAM, Volumes, IPs, VPNs, Storage space
    a cloud user --- is member to --- projects
    a cloud resource --- must be registered to --- a project
    A user creates a resource: registers a resource to a project he is member of

What information is found in a project:

    * members: cloud users who can use the project resources
    * project limit: usage limits per resource for the whole project
    * member limit: usage limits per resource per cloud user
    * usage: current usage per resource per cloud user

.. note:: By default, every user has a personal (system) project. By default
    when a user creates a resource, it is registered to this project, except if
    they explicitly request to register a resource to another project.

Query my projects
^^^^^^^^^^^^^^^^^
**Example:** Get information for all projects I am member to

.. literalinclude:: examples/astakos-project-info.py
    :language: python
    :lines: 34-
    :linenos:

The results should look like this::

    system:a1234567-a890-1234-56ae-78f90bb1c2db (a1234567-a890-1234-56ae-78f90bb1c2db)
        System project for user user@example.com

    CS333 lab assignments (a9f87654-3af2-1e09-8765-43a2df1098765)
        Virtual clusters for CS333 assignments
        https://university.example.com/courses/cs333


Quotas per project
^^^^^^^^^^^^^^^^^^
**Example:** Get usage and total limits per resource per project

.. literalinclude:: examples/astakos-project-quotas.py
    :language: python
    :lines: 34-
    :linenos:

The results should look like this::

    a1234567-a890-1234-56ae-78f90bb1c2db
      cyclades.cpu: 1/2
      cyclades.disk: 40/40
      cyclades.floating_ip: 1/1
      cyclades.network.private: 0/2
      cyclades.ram: 2147483648/2147483648
      cyclades.vm: 1/2
      pithos.diskspace: 20522192022/20522192022
    a9f87654-3af2-1e09-8765-43a2df1098765
      cyclades.cpu: 4/8
      cyclades.disk: 80/120
      cyclades.floating_ip: 1/4
      cyclades.network.private: 1/5
      cyclades.ram: 4294967296/53687091200
      cyclades.vm: 3/4
      pithos.diskspace: 20522192022/53687091200

Allocate resource to a project
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
**Example:** Create an IP assigned to a specific project

.. literalinclude:: examples/astakos-resource-allocation.py
    :language: python
    :lines: 34-
    :linenos:

.. note:: All "create_something" methods take an optional "project_id" argument
    which instructs Synnefo to register this resource to a specific project

Reassign resource to another project
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
**Example:** Reassign a storage container to different project

In the following scenario we assume that ``course_container`` is a storage
container on Pithos, which is assigned to the system (personal) project and
suffers from low quota limits. Fortunately, we have an extra project with enough
storage available. We will reassign the container to benefit from this option.

We will check the quota limits of the project of this container and, if they are
used up, we will reassign it to a different project.


.. literalinclude:: examples/astakos-project-reassign.py
    :language: python
    :lines: 34-
    :linenos:

.. note:: All quotable resources can be reassigned to different projects,
    including composite resources (aka: depended on other cloud resources) like
    VMs.

Cyclades / Compute
------------------

Cyclades / Network
------------------

Cyclades / BlockStorage
-----------------------

Image
-----

Pithos
------
