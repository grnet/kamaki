#a Copyright 2011 GRNET S.A. All rights reserved.
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
from .utils import filter_in, filter_out, prefix_keys, path4url
#from .connection.kamakicon import KamakiHTTPConnection

class StorageClient(Client):
    """OpenStack Object Storage API 1.0 client"""

    def __init__(self, base_url, token, account=None, container=None):
        super(StorageClient, self).__init__(base_url, token)
        #super(StorageClient, self).__init__(base_url, token, http_client=KamakiHTTPConnection())
        self.account = account
        self.container = container

    def assert_account(self):
        if not self.account:
            raise ClientError("No account provided")

    def assert_container(self):
        self.assert_account()
        if not self.container:
            raise ClientError("No container provided")

    def get_account_info(self):
        self.assert_account()
        path = path4url(self.account)
        r = self.head(path, success=(204, 401))
        if r.status_code == 401:
            r.release()
            raise ClientError("No authorization")
        reply = r.headers
        r.release()
        return reply

    def replace_account_meta(self, metapairs):
        self.assert_account()
        path = path4url(self.account)
        for key, val in  metapairs:
            self.set_header('X-Account-Meta-'+key, val)
        r = self.post(path, success=202)
        r.release()

    def del_account_meta(self, metakey):
        headers = self.get_account_info()
        self.headers = filter_out(headers, 'X-Account-Meta-'+metakey, exactMatch = True)
        if len(self.headers) == len(headers):
            raise ClientError('X-Account-Meta-%s not found' % metakey, 404)
        path = path4url(self.account)
        r = self.post(path, success = 202)
        r.release()

    def create_container(self, container):
        self.assert_account()
        path = path4url(self.account, container)
        r = self.put(path, success=(201, 202))
        if r.status_code == 202:
            r.release()
            raise ClientError("Container already exists", r.status_code)
        r.release()

    def get_container_info(self, container):
        self.assert_account()
        path = path4url(self.account, container)
        r = self.head(path, success=(204, 404))
        if r.status_code == 404:
            r.release()
            raise ClientError("Container does not exist", r.status_code)
        reply = r.headers
        r.release()
        return reply

    def delete_container(self, container):
        self.assert_account()
        path = path4url(self.account, container)
        r = self.delete(path, success=(204, 404, 409))
        if r.status_code == 404:
            r.release()
            raise ClientError("Container does not exist", r.status_code)
        elif r.status_code == 409:
            r.release()
            raise ClientError("Container is not empty", r.status_code)
        r.release()

    def list_containers(self):
        self.assert_account()
        self.set_param('format', 'json')
        path = path4url(self.account)
        r = self.get(path, success = (200, 204))
        reply = r.json
        r.release()
        return reply

    def upload_object(self, object, f, size=None):
        # This is a naive implementation, it loads the whole file in memory
        #Look in pithos for a nice implementation
        self.assert_container()
        path = path4url(self.account, self.container, object)
        data = f.read(size) if size is not None else f.read()
        r = self.put(path, data=data, success=201)
        r.release()

    def create_directory(self, object):
        self.assert_container()
        path = path4url(self.account, self.container, object)
        self.set_header('Content-Type', 'application/directory')
        self.set_header('Content-length', '0')
        r = self.put(path, success=201)
        r.release()

    def get_object_info(self, object):
        self.assert_container()
        path = path4url(self.account, self.container, object)
        r = self.head(path, success=200)
        reply = r.headers
        r.release()
        return reply

    def get_object_meta(self, object):
        r = filter_in(self.get_object_info(object), 'X-Object-Meta-')
        reply = {}
        for (key, val) in r.items():
            metakey = key.split('-')[-1]
            reply[metakey] = val
        return reply

    def del_object_meta(self, metakey, object):
        self.assert_container()
        self.set_header('X-Object-Meta-'+metakey, '')
        path = path4url(self.account, self.container, object)
        r = self.post(path, success = 202)
        r.release()

    def replace_object_meta(self, metapairs):
        self.assert_container()
        path=path4url(self.account, self.container)
        for key, val in metapairs:
            self.set_header('X-Object-Meta-'+key, val)
        r = self.post(path, success=202)
        r.release()

    def get_object(self, object):
        self.assert_container()
        path = path4url(self.account, self.container, object)
        r = self.get(path, success=200)
        size = int(r.headers['content-length'])
        cnt = r.content
        r.release()
        return cnt, size

    def copy_object(self, src_container, src_object, dst_container, dst_object=False):
        self.assert_account()
        dst_object = dst_object or src_object
        dst_path = path4url(self.account, dst_container, dst_object)
        self.set_header('X-Copy-From', path4url(src_container, src_object))
        self.set_header('Content-Length', 0)
        r = self.put(dst_path, success=201)
        r.release()

    def move_object(self, src_container, src_object, dst_container, dst_object=False):
        self.assert_account()
        dst_object = dst_object or src_object
        dst_path = path4url(self.account, dst_container, dst_object)
        self.set_header('X-Move-From', path4url(src_container, src_object))
        self.set_header('Content-Length', 0)
        r = self.put(dst_path, success=201)
        r.release()

    def delete_object(self, object):
        self.assert_container()
        path = path4url(self.account, self.container, object)
        r = self.delete(path, success=(204, 404))
        if r.status_code == 404:
            r.release()
            raise ClientError("Object %s not found" %object, r.status_code)
        r.release()
       
    def list_objects(self):
        self.assert_container()
        path = path4url(self.account, self.container)
        self.set_param('format', 'json')
        r = self.get(path, success=(200, 204, 304, 404), )
        if r.status_code == 404:
            r.release()
            raise ClientError("Incorrect account (%s) for that container"%self.account, r.status_code)
        elif r.status_code == 304:
            r.release()
            return []
        reply = r.json
        r.release()
        return reply

    def list_objects_in_path(self, path_prefix):
        self.assert_container()
        path = path4url(self.account, self.container)
        self.set_param('format', 'json')
        self.set_param('path', 'path_prefix')
        r = self.get(path, success=(200, 204, 404))
        if r.status_code == 404:
            r.release()
            raise ClientError("Incorrect account (%s) for that container"%self.account, r.status_code)
        reply = r.json
        r.release()
        return reply

