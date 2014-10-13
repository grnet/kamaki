# Copyright 2014 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.

import logging
import httplib
import socket
import ssl
from objpool import http

log = logging.getLogger(__name__)


class HTTPSClientAuthConnection(httplib.HTTPSConnection):
    """HTTPS connection, with full client-based SSL Authentication support"""

    ca_file, raise_ssl_error = None, True

    def __init__(
            self, host,
            port=None,
            key_file=None,
            cert_file=None,
            timeout=None,
            source_address=None,
            ca_file=None,
            raise_ssl_error=None):
        kwargs = dict()
        if port is not None:
            kwargs['port'] = port
        if key_file is not None:
            kwargs['key_file'] = key_file
        if port is not None:
            kwargs['cert_file'] = cert_file
        if key_file is not None:
            kwargs['key_file'] = key_file
        if timeout is not None:
            kwargs['timeout'] = timeout
        if source_address is not None:
            kwargs['source_address'] = source_address

        httplib.HTTPSConnection.__init__(self, host, **kwargs)

        self.ca_file = ca_file or getattr(self, 'ca_file')
        self.raise_ssl_error = raise_ssl_error if (
            raise_ssl_error is not None) else getattr(self, 'raise_ssl_error')

    def connect(self):
        """Connect to a host on a given (SSL) port.
        If ca_file is pointing somewhere, use it to check Server Certificate.

        Redefined/copied and extended from httplib.py:1105 (Python 2.6.x).
        This is needed to pass cert_reqs=ssl.CERT_REQUIRED as parameter to
        ssl.wrap_socket(), which forces SSL to check server certificate against
        our client certificate.
        """
        sock = socket.create_connection(
            (self.host, self.port), self.timeout, self.source_address)
        if self._tunnel_host:
            self.sock = sock
            self._tunnel()

        # If there's no CA File, let the flag decide if there should be a check
        if self.ca_file:
            try:
                self.sock = ssl.wrap_socket(
                    sock, self.key_file, self.cert_file,
                    ca_certs=self.ca_file, cert_reqs=ssl.CERT_REQUIRED)
                return
            except ssl.SSLError as ssle:
                if self.raise_ssl_error:
                    raise
                log.debug('Ignored SSL error: %s' % ssle)
        self.sock = ssl.wrap_socket(
            sock, self.key_file, self.cert_file, cert_reqs=(
                ssl.CERT_REQUIRED if self.raise_ssl_error else ssl.CERT_NONE))


http.HTTPConnectionPool._scheme_to_class['https'] = HTTPSClientAuthConnection
PooledHTTPConnection = http.PooledHTTPConnection


def patch_with_certs(ca_file):
    HTTPSClientAuthConnection.ca_file = ca_file


def patch_to_raise_ssl_errors(ssl_errors=True):
    HTTPSClientAuthConnection.raise_ssl_error = ssl_errors
