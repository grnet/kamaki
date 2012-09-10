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
from .pool.http import get_http_connection
from . import HTTPConnection, HTTPResponse, HTTPConnectionError


from time import sleep
from httplib import ResponseNotReady

class KamakiHTTPResponse(HTTPResponse):

    def _get_response(self):
        print('KamakiHTTPResponse:should I get response?')
        if self.prefetched:
            print('\tKamakiHTTPResponse: no, I have already done that before')
            return
        print('\tKamakiHTTPResponse: yes, pls')
        r = self.request.getresponse()
        self.prefetched = True
        headers = {}
        for k,v in r.getheaders():
            headers.update({k:v})
        self.headers = headers
        self.content = r.read(r.length)
        self.status_code = r.status
        self.status = r.reason
        print('KamakiHTTPResponse: Niiiiice')

    @property 
    def text(self):
        _get_response()
        return self._content
    @text.setter
    def test(self, v):
        pass

    @property 
    def json(self):
        _get_response()
        from json import loads
        try:
            return loads(self._content)
        except ValueError as err:
            HTTPConnectionError('Response not formated in JSON', details=unicode(err), status=702)
    @json.setter
    def json(self, v):
        pass

class KamakiHTTPConnection(HTTPConnection):

    url         =   None
    scheme      =   None
    netloc      =   None
    method      =   None
    data        =   None
    headers     =   None

    scheme_ports = {
            'http':     '80',
            'https':    '443',
    }

    def _load_connection_settings(self, url=None, scheme=None, params=None, headers=None, host=None,
        port=None, method=None):
        if params is not None:
            self.params = params
        if headers is not None:
            self.headers = headers

        if url is None:
            url = self.url
        if host is None or scheme is None:
            p = urlparse(url)
            netloc = p.netloc
            if not netloc:
                netloc = 'localhost'
            scheme = p.scheme
            if not scheme:
                scheme = 'http'
            param_str = ''
            for i,(key, val) in enumerate(self.params.items()):
                param_str = ('?' if i == 0 else '&') + unicode(key) 
                if val is not None:
                    param_str+= '='+unicode(val)
            url = p.path + param_str
        else:
            host = host
            port = port if port is not None else self.scheme_ports[scheme]
            #NOTE: we force host:port as canonical form,
            #      lest we have a cache miss 'host' vs 'host:80'
            netloc = "%s%s" % (host, port)

        self.netloc = netloc
        self.url = url #if url in (None, '') or url[0] != '/' else url[1:]
        self.scheme = scheme

        if method is not None:
            self.method = method

    def perform_request(self, url=None, params=None, headers=None, method=None, host=None,
        port=None, data=None):
        self._load_connection_settings(url=url, params=params, headers=headers, host=host,
            port=port, method=method)
        print('---> %s %s %s %s %s'%(self.method, self.scheme, self.netloc, self.url, self.headers))
        conn = get_http_connection(netloc=self.netloc, scheme=self.scheme)
        try:
            conn.request(self.method, self.url, headers=self.headers, body=data)
        except:
            conn.close()
            raise
        return KamakiHTTPResponse(conn)
