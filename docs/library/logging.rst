Logging
=======

Kamaki uses the standard Python logger.

Kamaki features the following logger objects::

	* standard loggers for kamaki development. They are named after the package
		they log
	* logger for monitoring the HTTP connection (requests and responses)

Loggers defined in higher levels of the package hierarchy are inherited. This
may cause duplication in logs. Use either a high level logger (e.g. 'kamaki' or
'kamaki.clients') to log everything, or a specific logger (e.g.
'kamaki.clients.image').

Monitor requests and responses
------------------------------

It is strongly recommended to declare the following loggers in your own code::

	kamaki.clients.send   logs requests URL, headers and, maybe, data
	kamaki.clients.recv   logs responses headers and, maybe, data

For security reasons, some information is omitted from the above loggers:
	* X-Auth-Token header value.
	* HTTP request or response data

Developers can explicitly enable or disable these features by setting a flag
on their kamaki client. These flags work on all kamaki clients.

.. code-block:: python

	from kamaki.clients.pithos import PithosClient

	pithos = PithosClient(pithos_endpoint, TOKEN)
	pithos.LOG_TOKEN = True
	pithos.LOG_DATA = True

Logging in a file
-----------------

To set a log file, e.g., the `/tmp/my_kamaki.log`:

.. code-block:: python

	from kamaki.cli.logger import add_file_logger
	add_file_logger('kamaki.clients.send', filename='/tmp/my_kamaki.log')
	add_file_logger('kamaki.clients.recv', filename='/tmp/my_kamaki.log')

.. note:: If it doesn't exist, `/tmp/my_kamaki.log` will be created.

After a call, the contents of the log file will look like this::

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

The ">" symbol shows a request, a "<" shows a response. The "data size" is a
statistic calculated by kamaki and is not used in the actual connection.

Deactivate a logger
-------------------

A kamaki logger can be deactivated and re-activated. In this example, we will
use a stream logger (a logger that prints on stderr instead of a log file), so
we will have to deactivate the file logger:

.. code-block:: python

	from kamaki.cli.logger import add_stream_logger, deactivate
	deactivate('kamaki.clients')
	add_stream_logger('kamaki.clients')
