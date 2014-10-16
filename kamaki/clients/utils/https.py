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

    def __init__(self, *args, **kwargs):
        """ Extent HTTPSConnection to support SSL authentication
            :param ca_file: path to CA certificates bundle (default: None)
            :param raise_ssl_error: flag (default: True)
        """
        self.ca_file = kwargs.pop('ca_file', self.ca_file)
        self.raise_ssl_error = kwargs.pop(
            'raise_ssl_error', self.raise_ssl_error)

        httplib.HTTPSConnection.__init__(self, *args, **kwargs)

    def connect(self):
        """Connect to a host on a given (SSL) port.
        If ca_file is pointing somewhere, use it to check Server Certificate.

        Redefined/copied and extended from httplib.py:1105 (Python 2.6.x).
        This is needed to pass cert_reqs=ssl.CERT_REQUIRED as parameter to
        ssl.wrap_socket(), which forces SSL to check server certificate against
        our client certificate.
        """
        source_address = getattr(self, 'source_address', None)
        socket_args = [(self.host, self.port), self.timeout] + (
            [source_address, ] if source_address else [])
        sock = socket.create_connection(*socket_args)
        if self._tunnel_host:
            self.sock = sock
            self._tunnel()

        # If there's no CA File, let the flag decide if there should be a check
        if self.raise_ssl_error:
            self.sock = ssl.wrap_socket(
                sock, self.key_file, self.cert_file,
                ca_certs=self.ca_file, cert_reqs=ssl.CERT_REQUIRED)
        else:
            self.sock = ssl.wrap_socket(
                sock, self.key_file, self.cert_file,
                cert_reqs=ssl.CERT_NONE)


http.HTTPConnectionPool._scheme_to_class['https'] = HTTPSClientAuthConnection
PooledHTTPConnection = http.PooledHTTPConnection


def patch_with_certs(ca_file):
    HTTPSClientAuthConnection.ca_file = ca_file


def patch_to_raise_ssl_errors(ssl_errors=True):
    HTTPSClientAuthConnection.raise_ssl_error = ssl_errors
