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

from . import Client, ClientError


class StorageClient(Client):
    """OpenStack Object Storage API 1.0 client"""

    def __init__(self, base_url, token, account=None, container=None):
        super(StorageClient, self).__init__(base_url, token)
        self.account = account
        self.container = container

    def assert_account(self):
        if not self.account:
            raise ClientError("Please provide an account")

    def assert_container(self):
        self.assert_account()
        if not self.container:
            raise ClientError("Please provide a container")

    def get_account_info(self):
        self.assert_account()
        path = '/%s' % self.account
        r = self.head(path, success=(204, 401))
        if r.status_code == 401:
            raise ClientError("No authorization")
        return r.headers

    def create_container(self, container):
        self.assert_account()
        path = '/%s/%s' % (self.account, container)
        r = self.put(path, success=(201, 202))
        if r.status_code == 202:
            raise ClientError("Container already exists", r.status_code)

    def get_container_info(self, container):
        self.assert_account()
        path = '/%s/%s' % (self.account, container)
        r = self.head(path, success=(204, 404))
        if r.status_code == 404:
            raise ClientError("Container does not exist", r.status_code)

        reply = {}
        prefix = 'x-container-'
        for key, val in r.headers.items():
            key = key.lower()
            if key.startswith(prefix):
                reply[key[len(prefix):]] = val

        return reply

    def delete_container(self, container):
        #Response codes
        #   Success             204
        #   NotFound            404
        #   Conflict(not empty) 409
        self.assert_account()
        path = '/%s/%s' % (self.account, container)
        r = self.delete(path, success=(204, 404, 409))
        if r.status_code == 404:
            raise ClientError("Container does not exist", r.status_code)
        elif r.status_code == 409:
            raise ClientError("Container is not empty", r.status_code)

    def list_containers(self):
        self.assert_account()
        path = '/%s' % (self.account) 
        params = dict(format='json')
        r = self.get(path, params = params, success = (200, 204))
        return r.json

    def create_object(self, object, f, size=None, hash_cb=None,
                      upload_cb=None):
        # This is a naive implementation, it loads the whole file in memory
        self.assert_container()
        path = '/%s/%s/%s' % (self.account, self.container, object)
        data = f.read(size) if size is not None else f.read()
        self.put(path, data=data, success=201)

    def create_directory(self, object):
        self.assert_container()
        path = '/%s/%s/%s' % (self.account, self.container, object)
        self.put(path, data='', directory=True, success=201)

    def get_object_info(self, object):
        self.assert_container()
        path = '/%s/%s/%s' % (self.account, self.container, object)
        r = self.head(path, success=200)
        return r.headers

    def get_object(self, object):
        self.assert_container()
        path = '/%s/%s/%s' % (self.account, self.container, object)
        r = self.get(path, raw=True, success=200)
        size = int(r.headers['content-length'])
        return r.raw, size

    def delete_object(self, object):
        self.assert_container()
        path = '/%s/%s/%s' % (self.account, self.container, object)
        r = self.delete(path, success=(204, 404))
        if r.status_code == 404:
            raise ClientError("Object %s not found" % object, r.status_code)
       
    def list_objects(self):
        self.assert_container()
        path = '/%s/%s' % (self.account, self.container)
        params = dict(format='json')
        r = self.get(path, params=params, success=(200, 204, 404))
        if r.status_code == 404:
            raise ClientError("Incorrect account (%s) for that container"%self.account, r.status_code)
        return r.json

    def list_objects_in_path(self, path_prefix):
        self.assert_container()
        path = '/%s/%s' % (self.account, self.container)
        params = dict(format='json', path=path_prefix)
        r = self.get(path, params=params, success=(200, 204, 404))
        if r.status_code == 404:
            raise ClientError("Incorrect account (%s) for that container"%self.account, r.status_code)
        return r.json
