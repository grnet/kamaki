# Copyright 2011 GRNET S.A. All rights reserved.
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

import json
import logging

import requests

from requests.auth import AuthBase


sendlog = logging.getLogger('clients.send')
recvlog = logging.getLogger('clients.recv')


# Add a convenience json property to the responses
def _json(self):
    try:
        return json.loads(self.content) if self.content else {}
    except ValueError:
        raise ClientError("Invalid JSON reply", self.status_code)
requests.Response.json = property(_json)

# Add a convenience status property to the responses
def _status(self):
    return requests.status_codes._codes[self.status_code][0].upper()
requests.Response.status = property(_status)


class XAuthTokenAuth(AuthBase):
    def __init__(self, token):
        self.token = token
    
    def __call__(self, r):
        r.headers['X-Auth-Token'] = self.token
        return r


class ClientError(Exception):
    def __init__(self, message, status=0, details=''):
        self.message = message
        self.status = status
        self.details = details


class Client(object):
    def __init__(self, base_url, token, include=False, verbose=False):
        self.base_url = base_url
        self.auth = XAuthTokenAuth(token)
        self.include = include
        self.verbose = verbose
    
    def raise_for_status(self, r):
        if 400 <= r.status_code < 500:
            message, sep, details = r.text.partition('\n')
        elif 500 <= r.status_code < 600:
            message = '%d Server Error' % (r.status_code,)
            details = r.text
        else:
            message = '%d Unknown Error' % (r.status_code,)
            details = r.text
        
        message = message or "HTTP Error %d" % (r.status_code,)
        raise ClientError(message, r.status_code, details)

    def request(self, method, path, **kwargs):
        raw = kwargs.pop('raw', False)
        success = kwargs.pop('success', 200)
        if 'json' in kwargs:
            data = json.dumps(kwargs.pop('json'))
            kwargs['data'] = data
            headers = kwargs.setdefault('headers', {})
            headers['content-type'] = 'application/json'

        url = self.base_url + path
        kwargs.setdefault('auth', self.auth)
        r = requests.request(method, url, **kwargs)
        
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
        if not raw and r.text:
            recvlog.debug(r.text)
        
        if success is not None:
            # Success can either be an in or a collection
            success = (success,) if isinstance(success, int) else success
            if r.status_code not in success:
                self.raise_for_status(r)

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


from .compute import ComputeClient as compute
from .image import ImageClient as image
from .storage import StorageClient as storage
from .cyclades import CycladesClient as cyclades
from .pithos import PithosClient as pithos
