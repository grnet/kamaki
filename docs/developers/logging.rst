Logging
=======

Kamaki uses the standard Python logger.

All kamaki loggers are named or prefixed after the package they log, e.g.,
a logger at `kamaki/cli/argument/__init__.py` should be called
`kamaki.cli.argument` whereas a logger at `kamaki/clients/conf.py` should be
named `kamaki.clients.conf`. In `kamaki/clients/__init__.py` there are two
loggers that use the package name as prefix, and they detailed bellow.

Monitor requests and responses
------------------------------

The `kamaki.clients` logger contains two subloggers that monitor the HTTP
API calls::

	kamaki.clients.send   for kamaki requests to the server
	kamaki.clients.recv   for server responses to kamaki

These are the only loggers used for purposes other than mere debugging. Both
loggers are defined in the CLI code and are used to (a) log HTTP communication
to the log file as well as to (b) show users the HTTP requests and responses in
"verbose" or "debug" modes.

Logger in external code
-----------------------

When a logger is known to be in kamaki code, the script developer may use this
logger to log some needed information. This can be happen either by directly
using the Python `logger` package, or the corresponding kamaki wraper
`kamaki.cli.logger` which allows the definition, activation and deactivation
of stream (usually console) or file loggers.

We will use
`this script <clients-api.html#register-a-banch-of-pre-uploaded-images>`_
as an example to work on. The script registers images from a set of
pre-uploaded image files.

First, we shall add a logger to track HTTP communication in `/tmp/my_kamaki.log`
To do this, append the following at the top of the file:

.. code-block:: python

	from kamaki.cli.logger import add_file_logger
	add_file_logger('kamaki.clients.send', filename='/tmp/my_kamaki.log')
	add_file_logger('kamaki.clients.recv', filename='/tmp/my_kamaki.log')

After a run of the script, a new file will be created at `/tmp/my_kamaki.log`
that will contain logs of the form::

	> POST https://accounts.okeanos.grnet.gr/identity/v2.0/tokens
	>   Content-Length: 74
	>   Content-Type: application/json
	> data size:74

	< 200 OK
	<   content-length: 2425
	<   content-language: en-us
	<   expires: Wed, 31 Jul 2013 14:27:47 GMT
	<   vary: X-Auth-Token,Accept-Language
	<   server: gunicorn/0.14.5	
	<   last-modified: Wed, 31 Jul 2013 14:27:47 GMT
	<   connection: close
	<   etag: "43af...36"
	<   cache-control: no-cache, no-store, must-revalidate, max-age=0
	<   date: Wed, 31 Jul 2013 14:27:47 GMT
	<   content-type: application/json; charset=UTF-8
	< data size: 2425

.. note:: user token and http body content are not logged by default. This can
	be switched on and off by modifing the *kamaki.client.Client.LOG_TOKEN* and
	*kamaki.client.Client.LOG_DATA* flags

As a second example, let's suppose that we need to see only the http requests
of the `pithos.list_objects()` method and print these to stdout. To achieve
that goal, we should get a stream logger and deactivate it when we do not need
it anymore.

.. code-block:: python

	#! /usr/bin/python

	[...]	

	from kamaki.cli.logger import add_stream_logger, deactivate
	add_stream_logger('kamaki.clients')

	for img in pithos.list_objects():
		deactivate('kamaki.clients')
		[...]

Logger in kamaki code
---------------------

When implementing kamaki code, either as part of the main kamaki project or as
an extension, it is often useful to use loggers. Developers may also directly
use the Python logger module with respect to the naming conventions.

In this example, we want to log the arguments of the `register` method found in
`kamaki/clients/image/__init__.py`. We will use the Python logger module.

First, we should add a logger initializer at the top of the file.

.. code-block:: python

	from logging import getLogger

	log = getLogger(__name__)

Now, we should use the `log` biding to actually log what we need.

.. code-block:: python

	[...]

    def register(self, name, location, params={}, properties={}):
    	log.debug('name: %s' % name)
    	log.debug('location: %s' % location)
    	log.debug('params: %s' % params)
    	log.debug('properties: %s' % properties)
    	[...]

Loggers defined in higher levels of the package hierarchy are inherited. This
may cause duplication in logs. Use either a high level loger (e.g. 'kamaki' or
'kamaki.clients') to log everything, or a specific logger (e.g.
'kamaki.clients.image').

.. code-block:: python

	add_file_logger('kamaki.clients.image', filename='/tmp/kamaki_image.log')

