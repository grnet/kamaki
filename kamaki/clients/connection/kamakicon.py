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
from urllib2 import quote
from objpool.http import get_http_connection
from traceback import format_stack

from kamaki.clients.connection import KamakiConnection, KamakiResponse
from kamaki.clients.connection.errors import KamakiConnectionError
from kamaki.clients.connection.errors import KamakiResponseError

from json import loads

from time import sleep
from httplib import ResponseNotReady


class KamakiHTTPResponse(KamakiResponse):

    def _get_response(self):
        if self.prefetched:
            return

        try:
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
            for k, v in r.getheaders():
                headers.update({k: v})
            self.headers = headers
            self.content = r.read()
            self.status_code = r.status
            self.status = r.reason
        finally:
            try:
                self.request.close()
            except Exception as err:
                from kamaki.clients import recvlog
                recvlog.debug('\n'.join(['%s' % type(err)] + format_stack()))
                raise

    @property
    def text(self):
        """
        :returns: (str) content
        """
        self._get_response()
        return '%s' % self._content

    @text.setter
    def text(self, v):
        pass

    @property
    def json(self):
        """
        :returns: (dict) the json-formated content

        :raises KamakiResponseError: if content is not json formated
        """
        self._get_response()
        try:
            return loads(self._content)
        except ValueError as err:
            KamakiResponseError('Response not formated in JSON - %s' % err)

    @json.setter
    def json(self, v):
        pass

    def release(self):
        """ Release the connection. Should always be called if the response
        content hasn't been used.
        """
        if not self.prefetched:
            try:
                self.request.close()
            except Exception as err:
                from kamaki.clients import recvlog
                recvlog.debug('\n'.join(['%s' % type(err)] + format_stack()))
                raise


class KamakiHTTPConnection(KamakiConnection):

    def _retrieve_connection_info(self, extra_params={}):
        """
        :param extra_params: (dict) key:val for url parameters

        :returns: (scheme, netloc, url?with&params)
        """
        if self.url:
            url = self.url if self.url[-1] == '/' else (self.url + '/')
        else:
            url = 'http://127.0.0.1'
        if self.path:
            url += self.path[1:] if self.path[0] == '/' else self.path
        params = dict(self.params)
        params.update(extra_params)
        for i, (key, val) in enumerate(params.items()):
            url += '%s%s' % ('&' if i else '?', key)
            if val:
                url += '=%s' % val

        parsed = urlparse(url)
        self.url = url
        self.path = parsed.path or '/'
        if parsed.query:
            self.path += '?%s' % parsed.query
        return (parsed.scheme, parsed.netloc)

    def perform_request(
            self,
            method=None, data=None, async_headers={}, async_params={}):
        """
        :param method: (str) http method ('get', 'post', etc.)

        :param data: (binary object)

        :param async_headers: (dict) key:val headers that are used only for one
            request instance as opposed to self.headers, which remain to be
            used by following or parallel requests

        :param async_params: (dict) key:val url parameters that are used only
            for one request instance as opposed to self.params, which remain to
            be used by following or parallel requests

        :returns: (KamakiHTTPResponse) a response object

        :raises KamakiConnectionError: Connection failures
        """
        (scheme, netloc) = self._retrieve_connection_info(async_params)
        headers = dict(self.headers)
        for k, v in async_headers.items():
            v = quote(v.encode('utf-8')) if isinstance(v, unicode) else str(v)
            headers[k] = v

        #de-unicode headers to prepare them for http
        http_headers = {}
        for k, v in headers.items():
            v = quote(v.encode('utf-8')) if isinstance(v, unicode) else str(v)
            http_headers[k] = v

        #get connection from pool
        try:
            conn = get_http_connection(
                netloc=netloc,
                scheme=scheme,
                pool_size=self.poolsize)
        except ValueError as ve:
            raise KamakiConnectionError(
                'Cannot establish connection to %s %s' % (self.url, ve),
                errno=-1)
        try:
            #Be carefull, all non-body variables should not be unicode
            conn.request(
                method=str(method.upper()),
                url=str(self.path),
                headers=http_headers,
                body=data)
        except IOError as ioe:
            raise KamakiConnectionError(
                'Cannot connect to %s: %s' % (self.url, ioe.strerror),
                errno=ioe.errno)
        except Exception as err:
            from kamaki.clients import recvlog
            recvlog.debug('\n'.join(['%s' % type(err)] + format_stack()))
            conn.close()
            raise
        return KamakiHTTPResponse(conn)
