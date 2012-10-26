# Copyright 2012 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#      copyright notice, self.list of conditions and the following
#      disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, self.list of conditions and the following
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

from urlparse import urlparse
#from .pool.http import get_http_connection
from synnefo.lib.pool.http import get_http_connection
from kamaki.clients.connection import HTTPConnection, HTTPResponse, HTTPConnectionError

from json import loads

from time import sleep
from httplib import ResponseNotReady

class KamakiHTTPResponse(HTTPResponse):

    def _get_response(self):
        if self.prefetched:
            return

        ready = False
        while not ready:
            try:
                r = self.request.getresponse()
            except ResponseNotReady:
                sleep(0.001)
                continue
            break
        self.prefetched = True
        headers = {}
        for k,v in r.getheaders():
            headers.update({k:v})
        self.headers = headers
        self.content = r.read()
        self.status_code = r.status
        self.status = r.reason
        self.request.close()

    @property 
    def text(self):
        self._get_response()
        return self._content
    @text.setter
    def test(self, v):
        pass

    @property 
    def json(self):
        self._get_response()
        try:
            return loads(self._content)
        except ValueError as err:
            HTTPConnectionError('Response not formated in JSON', details=unicode(err), status=702)
    @json.setter
    def json(self, v):
        pass

    def release(self):
        if not self.prefetched:
            self.request.close()


class KamakiHTTPConnection(HTTPConnection):

    def _retrieve_connection_info(self, extra_params={}):
        """ return (scheme, netloc, url?with&params) """
        url = self.url
        params = dict(self.params)
        for k,v in extra_params.items():
            params[k] = v
        for i,(key, val) in enumerate(params.items()):
            param_str = ('?' if i == 0 else '&') + unicode(key) 
            if val is not None:
                param_str+= '='+unicode(val)
            url += param_str

        parsed = urlparse(self.url)
        self.url = url
        return (parsed.scheme, parsed.netloc)

    def perform_request(self, method=None, data=None, async_headers={}, async_params={}):
        (scheme, netloc) = self._retrieve_connection_info(extra_params=async_params)
        headers = dict(self.headers)
        for k,v in async_headers.items():
            headers[k] = v

        #de-unicode headers to prepare them for http
        http_headers = {}
        for k,v in headers.items():
            http_headers[str(k)] = str(v)

        #get connection from pool
        conn = get_http_connection(netloc=netloc, scheme=scheme)
        try:
            #Be carefull, all non-body variables should not be unicode
            conn.request(method = str(method.upper()),
                url=str(self.url),
                headers=http_headers,
                body=data)
        except:
            conn.close()
            raise
        return KamakiHTTPResponse(conn)
