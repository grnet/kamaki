Overview
========

History
-------

Kamaki was created on 2011 by the Synnefo (http://www.synnefo.org) development
team of the *Greek Research and Technology Network (GRNET)*, initially as an
internal project and later as a multipurpose tool for all users.

Synnefo is an IaaS system which implements and extents OpenStack. Synnefo has
been deployed in many environments to cover multiple needs. The most notable
deployment is probably the GRNET's
`~okeanos <http://okeanos.grnet.gr>`_ IaaS service, running in GRNET data
centers, is used to offer cloud services to the Greek Research and Academic
Community.

Kamaki was originally conceived as a handy tool for the developers of *Synnefo*
and the administrators of *Okeanos*. The initial purpose of kamaki was to
provide an easy to use command line client for accessing the various ReST APIs
of Synnefo.

Kamaki has been designed to act as a command line client as well as a python
library for client developers. It is widely used in various synnefo and okeanos
components. Third parties are also encouraged to use the kamaki library for
developing their own python-based cloud-client applications.

As Synnefo became a full, scalable and stable cloud solution, kamaki also
evolved to an intuitive, multipurpose tool, available to a wider user base.
For example, it is used as the main Pithos+ client at Linux and other Unix-like
environments. It can be easily set up in all popular platforms, including
recent Linux, OS X and Windows releases.

Who uses *kamaki*?
------------------

Kamaki is targeted to new and advanced users who need an intuitive managerial console tool to manage a local or remote synnefo cloud installation, without
excluding users who need to use just parts of the cloud system (e.g. only
Pihtos+ storage service or only Image services)

*kamaki* is currently used

* internally by the Synnefo development team to test the synnefo software,

* by the deployment team which operates the GRNET ~okeanos service

* as the main Pithos+ client at Linux and other Unix-like environments

* by third party Synnefo deploys who need to test and debug their cloud setup

* as an API library for other components in the Synnefo universe.

Contributing and helping out
----------------------------

The *kamaki* development team values your help and depends on community feedback for feature evolution. Any contributions and bug reports will be
highly appreciated.

Community & Support
-------------------

For any problems you may bump into while using *kamaki* or for help from the development team please contact us at::

* Users list: synnefo@googlegroups.com
* Developers list: synnefo-devel@googlegroups.com

Bug reports and feedback are also highly appreciated.
