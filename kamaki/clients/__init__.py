# Copyright 2011-2012 GRNET S.A. All rights reserved.
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

from json import dumps, loads
import logging
from kamaki.clients.connection.kamakicon import KamakiHTTPConnection

sendlog = logging.getLogger('clients.send')
recvlog = logging.getLogger('clients.recv')


class ClientError(Exception):
    def __init__(self, message, status=0, details=[]):
        try:
            json_msg = loads(message)
            key = json_msg.keys()[0]
            json_msg = json_msg[key]
            message = '%s (%s)\n' % (key, json_msg['message'])\
                if 'message' in json_msg else '%s' % key
            if 'code' in json_msg:
                status = json_msg['code']
            if 'details' in json_msg:
                if not details:
                    details = []
                elif not isinstance(details, list):
                    details = [details]
                if json_msg['details']:
                    details.append(json_msg['details'])
        except:
            pass

        super(ClientError, self).__init__(message)
        self.status = status
        self.details = details



class Client(object):
    def __init__(self, base_url, token, http_client=KamakiHTTPConnection()):
        self.base_url = base_url
        self.token = token
        self.headers = {}
        self.DATE_FORMATS = ["%a %b %d %H:%M:%S %Y",
            "%A, %d-%b-%y %H:%M:%S GMT",
            "%a, %d %b %Y %H:%M:%S GMT"]
        self.http_client = http_client

    def _raise_for_status(self, r):
        try:
            message = r.text
        except:
            message = '%s' % r
        raise ClientError(message, status=r.status)

    def set_header(self, name, value, iff=True):
        """Set a header 'name':'value'"""
        if value is not None and iff:
            self.http_client.set_header(name, value)

    def set_param(self, name, value=None, iff=True):
        if iff:
            self.http_client.set_param(name, value)

    def set_default_header(self, name, value):
        self.http_client.headers.setdefault(name, value)

    def request(self,
        method,
        path,
        async_headers={},
        async_params={},
        **kwargs):
        """In threaded/asynchronous requests, headers and params are not safe
        Therefore, the standard self.set_header/param system can be used only
        for headers and params that are common for all requests. All other
        params and headers should passes as
        @param async_headers
        @async_params
        E.g. in most queries the 'X-Auth-Token' header might be the same for
        all, but the 'Range' header might be different from request to request.
        """

        try:
            success = kwargs.pop('success', 200)

            data = kwargs.pop('data', None)
            self.set_default_header('X-Auth-Token', self.token)

            if 'json' in kwargs:
                data = dumps(kwargs.pop('json'))
                self.set_default_header('Content-Type', 'application/json')
            if data:
                self.set_default_header('Content-Length', unicode(len(data)))

            self.http_client.url = self.base_url
            self.http_client.path = path
            r = self.http_client.perform_request(method,
                data,
                async_headers,
                async_params)

            req = self.http_client
            sendlog.info('%s %s', method, req.url)
            headers = dict(req.headers)
            headers.update(async_headers)

            for key, val in headers.items():
                sendlog.info('\t%s: %s', key, val)
            sendlog.info('')
            if data:
                sendlog.info('%s', data)

            recvlog.info('%d %s', r.status_code, r.status)
            for key, val in r.headers.items():
                recvlog.info('%s: %s', key, val)
            if r.content:
                recvlog.debug(r.content)

        except Exception as err:
            print('WTF? !!!!!!!')
            from traceback import print_stack
            recvlog.debug(print_stack)
            self.http_client.reset_headers()
            self.http_client.reset_params()
            raise ClientError('%s' % err, status=getattr(err, 'status', 0))

        self.http_client.reset_headers()
        self.http_client.reset_params()

        if success is not None:
            # Success can either be an in or a collection
            success = (success,) if isinstance(success, int) else success
            if r.status_code not in success:
                r.release()
                self._raise_for_status(r)
        return r

    def delete(self, path, **kwargs):
        return self.request('delete', path, **kwargs)

    def get(self, path, **kwargs):
        return self.request('get', path, **kwargs)

    def head(self, path, **kwargs):
        return self.request('head', path, **kwargs)

    def post(self, path, **kwargs):
        return self.request('post', path, **kwargs)

    def put(self, path, **kwargs):
        return self.request('put', path, **kwargs)

    def copy(self, path, **kwargs):
        return self.request('copy', path, **kwargs)

    def move(self, path, **kwargs):
        return self.request('move', path, **kwargs)
