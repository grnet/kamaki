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

from . import ClientError
from .http import HTTPClient


class StorageClient(HTTPClient):
    """OpenStack Object Storage API 1.0 client"""
    
    @property
    def url(self):
        url = self.config.get('storage_url') or self.config.get('url')
        if not url:
            raise ClientError('No URL was given')
        return url

    @property
    def token(self):
        token = self.config.get('storage_token') or self.config.get('token')
        if not token:
            raise ClientError('No token was given')
        return token
    
    @property
    def account(self):
        account = self.config.get('storage_account')
        if not account:
            raise ClientError('No account was given')
        return account
    
    @property
    def container(self):
        container = self.config.get('storage_container')
        if not container:
            raise ClientError('No container was given')
        return container
    
    def get_container_meta(self):
        path = '/%s/%s' % (self.account, self.container)
        resp, reply = self.raw_http_cmd('HEAD', path, success=204)
        reply = {}
        prefix = 'x-container-'
        for key, val in resp.getheaders():
            key = key.lower()
            if key.startswith(prefix):
                reply[key[len(prefix):]] = val
        return reply
    
    def create_object(self, object, f):
        path = '/%s/%s/%s' % (self.account, self.container, object)
        data = f.read()
        self.http_put(path, data, success=201)

    def get_object(self, object):
        path = '/%s/%s/%s' % (self.account, self.container, object)
        resp, reply = self.raw_http_cmd('GET', path, success=200,
                skip_read=True)
        return resp.fp

    def delete_object(self, object):
        path = '/%s/%s/%s' % (self.account, self.container, object)
        self.http_delete(path)
