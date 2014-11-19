Overview
========

History
-------

Kamaki was created in 2011 by the `Synnefo <http://www.synnefo.org>`_
development team at the *Greek Research and Technology Network (GRNET)*,
initially as an internal project and later as a multipurpose tool for all
users.

Synnefo is open source cloud software used to create massively scalable IaaS
clouds. It uses Google Ganeti for the low level VM management. It talks to
the outside world through the OpenStack APIs with extensions for advanced
operations. Synnefo is used by GRNET to power its
`~okeanos <http://okeanos.grnet.gr>`_ service, providing cloud services to the
whole Greek research and academic community. 

Kamaki was originally conceived as a handy tool for the developers of *Synnefo*
and the administrators of *~okeanos*. The initial purpose of kamaki was to
provide an easy to use command-line client for accessing the various ReST APIs
of Synnefo.

Kamaki has been designed to act as a command line client as well as a python
library for client developers. It is widely used in various Synnefo and okeanos
components. Third parties are also encouraged to use the kamaki library for
developing their own python-based cloud applications.

As Synnefo became a full, scalable and stable cloud solution, kamaki also
evolved to an intuitive, multipurpose tool, available to a wider user base.
For example, it is used as the main Pithos+ client in Linux and other Unix-like
environments. It can be easily set up in all popular platforms, including
recent Linux, OS X and Windows releases.

Who uses *kamaki*?
------------------

Kamaki is targeted to new and advanced users who need an intuitive
command-line tool for managing a local or remote Synnefo deployment.

*kamaki* is currently used

* internally by the Synnefo development team to test the Synnefo software,

* by the deployment team which operates `GRNET ~okeanos` service

* as the main `Pithos+` client in Linux and other Unix-like environments, as
    well as in windows and osx by users with a preference for command line

* by third-party `Synnefo` deployers for testing and debugging their setup

* as an API library for Synnefo-related components (`burnin`, `image-creator`)
    or external applications

Community & Support
-------------------

The *kamaki* development team values your help and depends on community
feedback for the evolution of new features. Any contributions and bug reports
are highly appreciated.

For any problems you may bump into while using *kamaki* or for help from the
development team please contact us at::

* Users list: synnefo@googlegroups.com
* Developers list: synnefo-devel@googlegroups.com
