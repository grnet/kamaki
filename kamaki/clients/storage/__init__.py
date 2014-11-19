# Copyright 2011-2013 GRNET S.A. All rights reserved.
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

from kamaki.clients import Client, ClientError
from kamaki.clients.utils import filter_in, filter_out, path4url


class StorageClient(Client):
    """OpenStack Object Storage API 1.0 client"""

    def __init__(self, endpoint_url, token, account=None, container=None):
        super(StorageClient, self).__init__(endpoint_url, token)
        self.account = account
        self.container = container

    def _assert_account(self):
        if not self.account:
            raise ClientError("No account provided")

    def _assert_container(self):
        self._assert_account()
        if not self.container:
            raise ClientError("No container provided")

    def get_account_info(self):
        """
        :returns: (dict)
        """
        self._assert_account()
        path = path4url(self.account)
        r = self.head(path, success=(204, 401))
        if r.status_code == 401:
            raise ClientError("No authorization", status=401)
        reply = r.headers
        return reply

    def replace_account_meta(self, metapairs):
        """
        :param metapais: (dict) key:val metadata pairs
        """
        self._assert_account()
        path = path4url(self.account)
        for key, val in metapairs.items():
            self.set_header('X-Account-Meta-' + key, val)
        self.post(path, success=202)

    def del_account_meta(self, metakey):
        """
        :param metakey: (str) metadatum key
        """
        headers = self.get_account_info()
        self.headers = filter_out(
            headers,
            'X-Account-Meta-' + metakey,
            exactMatch=True)
        if len(self.headers) == len(headers):
            raise ClientError('X-Account-Meta-%s not found' % metakey, 404)
        path = path4url(self.account)
        self.post(path, success=202)

    def create_container(self, container):
        """
        :param container: (str)

        :raises ClientError: 202 Container already exists
        """
        self._assert_account()
        path = path4url(self.account, container)
        r = self.put(path, success=(201, 202))
        if r.status_code == 202:
            raise ClientError("Container already exists", r.status_code)

    def get_container_info(self, container):
        """
        :param container: (str)

        :returns: (dict)

        :raises ClientError: 404 Container does not exist
        """
        self._assert_account()
        path = path4url(self.account, container)
        r = self.head(path, success=(204, 404))
        if r.status_code == 404:
            raise ClientError("Container does not exist", r.status_code)
        reply = r.headers
        return reply

    def delete_container(self, container):
        """
        :param container: (str)

        :raises ClientError: 404 Container does not exist
        :raises ClientError: 409 Container not empty
        """
        self._assert_account()
        path = path4url(self.account, container)
        r = self.delete(path, success=(204, 404, 409))
        if r.status_code == 404:
            raise ClientError("Container does not exist", r.status_code)
        elif r.status_code == 409:
            raise ClientError("Container is not empty", r.status_code)

    def list_containers(self):
        """
        :returns: (dict)
        """
        self._assert_account()
        self.set_param('format', 'json')
        path = path4url(self.account)
        r = self.get(path, success=(200, 204))
        reply = r.json
        return reply

    def upload_object(self, obj, f, size=None):
        """ A simple (naive) implementation.

        :param obj: (str)

        :param f: an open for reading file descriptor

        :param size: (int) number of bytes to upload
        """
        self._assert_container()
        path = path4url(self.account, self.container, obj)
        data = f.read(size) if size else f.read()
        self.put(path, data=data, success=201)

    def create_object(
            self, obj,
            content_type='application/octet-stream', content_length=0):
        """
        :param obj: (str) directory-object name

        :param content_type: (str) explicitly set content_type

        :param content_length: (int) explicitly set content length

        :returns: (dict) object creation headers
        """
        self._assert_container()
        path = path4url(self.account, self.container, obj)
        self.set_header('Content-Type', content_type)
        self.set_header('Content-length', str(content_length))
        r = self.put(path, success=201)
        return r.headers

    def create_directory(self, obj):
        """
        :param obj: (str) directory-object name

        :returns: (dict) request headers
        """
        self._assert_container()
        assert obj, 'Remote directory path is missing'
        path = path4url(self.account, self.container, obj)
        self.set_header('Content-Type', 'application/directory')
        self.set_header('Content-length', '0')
        r = self.put(path, success=201)
        return r.headers

    def get_object_info(self, obj):
        """
        :param obj: (str)

        :returns: (dict)
        """
        self._assert_container()
        path = path4url(self.account, self.container, obj)
        r = self.head(path, success=200)
        reply = r.headers
        return reply

    def get_object_meta(self, obj):
        """
        :param obj: (str)

        :returns: (dict)
        """
        r = filter_in(self.get_object_info(obj), 'X-Object-Meta-')
        reply = {}
        for (key, val) in r.items():
            metakey = key.split('-')[-1]
            reply[metakey] = val
        return reply

    def del_object_meta(self, obj, metakey):
        """
        :param obj: (str)

        :param metakey: (str) the metadatum key
        """
        self._assert_container()
        self.set_header('X-Object-Meta-' + metakey, '')
        path = path4url(self.account, self.container, obj)
        self.post(path, success=202)

    def replace_object_meta(self, metapairs):
        """
        :param metapairs: (dict) key:val metadata
        """
        self._assert_container()
        path = path4url(self.account, self.container)
        for key, val in metapairs.items():
            self.set_header('X-Object-Meta-' + key, val)
        self.post(path, success=202)

    def copy_object(
            self, src_container, src_object, dst_container,
            dst_object=False):
        """Copy an objects from src_contaier:src_object to
            dst_container[:dst_object]

        :param src_container: (str)

        :param src_object: (str)

        :param dst_container: (str)

        :param dst_object: (str)
        """
        self._assert_account()
        dst_object = dst_object or src_object
        dst_path = path4url(self.account, dst_container, dst_object)
        self.set_header('X-Copy-From', path4url(src_container, src_object))
        self.set_header('Content-Length', 0)
        self.put(dst_path, success=201)

    def move_object(
            self, src_container, src_object, dst_container,
            dst_object=False):
        """Move an objects from src_contaier:src_object to
            dst_container[:dst_object]

        :param src_container: (str)

        :param src_object: (str)

        :param dst_container: (str)

        :param dst_object: (str)
        """
        self._assert_account()
        dst_object = dst_object or src_object
        dst_path = path4url(self.account, dst_container, dst_object)
        self.set_header('X-Move-From', path4url(src_container, src_object))
        self.set_header('Content-Length', 0)
        self.put(dst_path, success=201)

    def delete_object(self, obj):
        """
        :param obj: (str)

        :raises ClientError: 404 Object not found
        """
        self._assert_container()
        path = path4url(self.account, self.container, obj)
        r = self.delete(path, success=(204, 404))
        if r.status_code == 404:
            raise ClientError("Object %s not found" % obj, r.status_code)

    def list_objects(
            self,
            limit=None,
            marker=None,
            prefix=None,
            format=None,
            delimiter=None,
            path=None):
        """
        :param limit: (integer) The amount of results requested

        :param marker: (string) Return containers with name lexicographically
            after marker

        :param prefix: (string) Return objects starting with prefix

        :param format: (string) reply format can be json or xml (default:json)

        :param delimiter: (string) Return objects up to the delimiter

        :param path: (string) assume prefix = path and delimiter = /
            (overwrites prefix and delimiter)

        :returns: (dict)

        :raises ClientError: 404 Invalid account
        """
        self._assert_container()
        restpath = path4url(self.account, self.container)

        self.set_param('format', format or 'json')

        self.set_param('limit', limit, iff=limit)
        self.set_param('marker', marker, iff=marker)
        if path:
            self.set_param('path', path)
        else:
            self.set_param('prefix', prefix, iff=prefix)
            self.set_param('delimiter', delimiter, iff=delimiter)

        r = self.get(restpath, success=(200, 204, 304, 404), )
        if r.status_code == 404:
            raise ClientError(
                "Invalid account (%s) for that container" % self.account,
                r.status_code)
        elif r.status_code == 304:
            return []
        return r.json

    def list_objects_in_path(self, path_prefix):
        """
        :param path_prefix: (str)

        :raises ClientError: 404 Invalid account

        :returns: (dict)
        """
        self._assert_container()
        path = path4url(self.account, self.container)
        self.set_param('format', 'json')
        self.set_param('path', path_prefix)
        r = self.get(path, success=(200, 204, 404))
        if r.status_code == 404:
            raise ClientError(
                "Invalid account (%s) for that container" % self.account,
                r.status_code)
        reply = r.json
        return reply
