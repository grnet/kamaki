Errors
======

The class ``kamaki.clients.ClientError`` is raised when the response of an API
call is not as expected. In most cases, it is the only error type you will need
while working with kamaki library.

A ClientError contains::

    message     The error message.
    status      Typically, the API response code (usually an error code)
    details     Optional list of messages with error details.

Here is an error-conscious version of the AstakosCLient initialization

.. code-block:: python

    # Initialize an astakos Client
    from kamaki.clients.astakos import AstakosClient, ClientError
    try:
        astakos = AstakosClient(AUTHENTICATION_URL, TOKEN)
    except ClientError as ce:
        if ce in (404, ):
            print "Invalid URL for this cloud"
        elif ce in (401, ):
            print "Authentication failed"
        print "Status: {code}, Message: {msg}, Details: {details})".format(
                code=ce.status, msg=ce.message, details=', '.join(ce.details))
        exit(1)

Some clients or methods can produce specialized errors i.e.,
``AstakosClientError`` is raised by AstakosClient, ``KamakiSSLError`` is raised
in case of an SSL-related problem. Both errors are subclasses of ``ClientError``
and can be handled as such.
