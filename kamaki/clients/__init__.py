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

import json
import logging
from .connection import HTTPConnectionError
#from .connection.request import HTTPRequest
from .connection.kamakicon import KamakiHTTPConnection

sendlog = logging.getLogger('clients.send')
recvlog = logging.getLogger('clients.recv')


class ClientError(Exception):
    def __init__(self, message, status=0, details=''):
        super(ClientError, self).__init__(message, status, details)
        self.message = message
        self.status = status
        self.details = details

class Client(object):

    def __init__(self, base_url, token, http_client=KamakiHTTPConnection()):
    #def __init__(self, base_url, token, http_client=HTTPRequest()):
        self.base_url = base_url
        self.token = token
        self.headers = {}
        self.DATE_FORMATS = ["%a %b %d %H:%M:%S %Y",
            "%A, %d-%b-%y %H:%M:%S GMT",
            "%a, %d %b %Y %H:%M:%S GMT"]
        self.http_client = http_client

    def _raise_for_status(self, r):
        message = "%d %s" % (r.status_code, r.status)
        try:
            details = r.text
        except:
            details = ''
        raise ClientError(message, r.status_code, details)

    def set_header(self, name, value, iff=True):
        """Set a header 'name':'value' provided value is not None and iff is True"""
        if value is not None and iff:
            self.http_client.set_header(name, value)

    def set_param(self, name, value=None, iff=True):
        if iff:
            self.http_client.set_param(name, value)

    def set_default_header(self, name, value):
        self.http_client.headers.setdefault(name, value)

    def request(self, method, path, **kwargs):
        try:
            success = kwargs.pop('success', 200)

            binary = kwargs.pop('binary', False)
            data = kwargs.pop('data', None)
            self.set_default_header('X-Auth-Token', self.token)

            if 'json' in kwargs:
                data = json.dumps(kwargs.pop('json'))
                self.set_default_header('Content-Type', 'application/json')
            if data:
                self.set_default_header('Content-Length', unicode(len(data)))

            self.http_client.url = self.base_url + path
            r = self.http_client.perform_request(method=method, data=data)

            req = self.http_client
            sendlog.info('%s %s', method, req.url)
            for key, val in req.headers.items():
                sendlog.info('%s: %s', key, val)
            sendlog.info('')
            if data:
                sendlog.info('%s', data)

            recvlog.info('%d %s', r.status_code, r.status)
            for key, val in r.headers.items():
                recvlog.info('%s: %s', key, val)
            recvlog.info('')
            if r.content:
                recvlog.debug(r.content)

            if success is not None:
                # Success can either be an in or a collection
                success = (success,) if isinstance(success, int) else success
                if r.status_code not in success:
                    self._raise_for_status(r)
        except Exception as err:
            self.http_client.reset_headers()
            self.http_client.reset_params()
            if isinstance(err, HTTPConnectionError):
                raise ClientError(message=err.message, status=err.status, details=err.details)
            raise

        self.http_client.reset_headers()
        self.http_client.reset_params()
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

