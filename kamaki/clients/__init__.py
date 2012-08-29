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

import requests

from requests.auth import AuthBase

sendlog = logging.getLogger('clients.send')
recvlog = logging.getLogger('clients.recv')

# Add a convenience status property to the responses
def _status(self):
    return requests.status_codes._codes[self.status_code][0].upper()
requests.Response.status = property(_status)

class ClientError(Exception):
    def __init__(self, message, status=0, details=''):
        super(ClientError, self).__init__(message, status, details)
        self.message = message
        self.status = status
        self.details = details

class Client(object):

    def __init__(self, base_url, token, http_client=None):
        self.base_url = base_url
        self.token = token
        self.headers = {}
        self.DATE_FORMATS = ["%a %b %d %H:%M:%S %Y",
            "%A, %d-%b-%y %H:%M:%S GMT",
            "%a, %d %b %Y %H:%M:%S GMT"]
        self.http_client = http_client

    def raise_for_status(self, r):
        message = "%d %s" % (r.status_code, r.status)
        try:
            details = r.text
        except:
            details = ''
        raise ClientError(message, r.status_code, details)

    def set_header(self, name, value, iff=True):
        """Set a header 'name':'value' provided value is not None and iff is True"""
        #if value is not None and iff:
        #    self.headers[unicode(name)] = unicode(value)
        if value is not None and iff:
            self.http_client.set_header(name, value)

    def set_param(self, name, value=None, iff=True):
        if iff:
            self.http_client.set_param(name, value)

    def set_default_header(self, name, value):
        self.http_client.headers.setdefault(name, value)

    def request(self, method, path, reset_headers = True, **kwargs):
        try:
            #r = self._request(method, path, **kwargs)
            success = kwargs.pop('success', 200)

            data = kwargs.pop('data', None)
            self.set_default_header('X-Auth-Token', self.token)

            if 'json' in kwargs:
                data = json.dumps(kwargs.pop('json'))
                self.set_default_header('Content-Type', 'application/json')
            if data:
                self.set_default_header('Content-Length', unicode(len(data)))

            #kwargs.setdefault('verify', False)  # Disable certificate verification
            self.http_client.url = self.base_url + path
            self.http_client.perform_request(method=method, data=data)
            #r = requests.request(method, url, headers=self.headers, data=data, **kwargs)

            req = self.http_client
            sendlog.info('%s %s', req.method, req.url)
            for key, val in req.headers.items():
                sendlog.info('%s: %s', key, val)
            sendlog.info('')
            if data:
                sendlog.info('%s', data)

            r = self.http_client.response
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
                    self.raise_for_status(r)
        except:
            if reset_headers:
                self.http_client.reset_headers()
                self.http_client.reset_params()
            raise
        if reset_headers:
            self.http_client.reset_headers()
            self.http_client.reset_params()
        return r
    """    
    def _request(self, method, path, **kwargs):
        raw = kwargs.pop('raw', False)
        success = kwargs.pop('success', 200)

        data = kwargs.pop('data', None)
        self.headers.setdefault('X-Auth-Token', self.token)

        if 'json' in kwargs:
            data = json.dumps(kwargs.pop('json'))
            self.headers.setdefault('Content-Type', 'application/json')
        if data:
            self.headers.setdefault('Content-Length', unicode(len(data)))

        url = self.base_url + path
        kwargs.setdefault('verify', False)  # Disable certificate verification
        r = requests.request(method, url, headers=self.headers, data=data, **kwargs)

        url = self.base_url + path
        req = r.request
        sendlog.info('%s %s', req.method, req.url)
        for key, val in req.headers.items():
            sendlog.info('%s: %s', key, val)
        sendlog.info('')
        if req.data:
            sendlog.info('%s', req.data)

        recvlog.info('%d %s', r.status_code, r.status)
        for key, val in r.headers.items():
            recvlog.info('%s: %s', key, val)
        recvlog.info('')
        if not raw and r.content:
            recvlog.debug(r.content)

        if success is not None:
            # Success can either be an in or a collection
            success = (success,) if isinstance(success, int) else success
            if r.status_code not in success:
                self.raise_for_status(r)
        return r
    """

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

