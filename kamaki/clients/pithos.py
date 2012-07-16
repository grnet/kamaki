# Copyright 2011-2012 GRNET S.A. All rights reserved.
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

import hashlib
import os

from time import time

from .storage import StorageClient, ClientError
from .utils import path4url, params4url, prefix_keys, filter_in, filter_out


def pithos_hash(block, blockhash):
    h = hashlib.new(blockhash)
    h.update(block.rstrip('\x00'))
    return h.hexdigest()


class PithosClient(StorageClient):
    """GRNet Pithos API client"""

    def purge_container(self, container):
        self.assert_account()
        path = path4url(self.account, container)+params4url({'until': unicode(time())})
        self.delete(path, success=204)

    def put_block(self, data, hash):
        path = path4url(self.account, self.container)+params4url({'update':None})
        self.set_header('Content-Type', 'application/octet-stream')
        self.set_header('Content-Length', len(data))
        r = self.post(path, data=data, success=202)
        assert r.text.strip() == hash, 'Local hash does not match server'

    def create_object(self, object, f, size=None, hash_cb=None,
                      upload_cb=None):
        """Create an object by uploading only the missing blocks
        hash_cb is a generator function taking the total number of blocks to
        be hashed as an argument. Its next() will be called every time a block
        is hashed.

        upload_cb is a generator function with the same properties that is
        called every time a block is uploaded.
        """
        self.assert_container()

        meta = self.get_container_info(self.container)
        blocksize = int(meta['x-container-block-size'])
        blockhash = meta['x-container-block-hash']

        size = size if size is not None else os.fstat(f.fileno()).st_size
        nblocks = 1 + (size - 1) // blocksize
        hashes = []
        map = {}

        offset = 0

        if hash_cb:
            hash_gen = hash_cb(nblocks)
            hash_gen.next()

        for i in range(nblocks):
            block = f.read(min(blocksize, size - offset))
            bytes = len(block)
            hash = pithos_hash(block, blockhash)
            hashes.append(hash)
            map[hash] = (offset, bytes)
            offset += bytes
            if hash_cb:
                hash_gen.next()

        assert offset == size

        path = path4url(self.account, self.container, object)+params4url(dict(format='json', hashmap=''))
        hashmap = dict(bytes=size, hashes=hashes)
        self.set_header('Content-Type', 'application/octet-stream')
        r = self.put(path, json=hashmap, success=(201, 409))

        if r.status_code == 201:
            return

        missing = r.json

        if upload_cb:
            upload_gen = upload_cb(len(missing))
            upload_gen.next()

        for hash in missing:
            offset, bytes = map[hash]
            f.seek(offset)
            data = f.read(bytes)
            self.put_block(data, hash)
            if upload_cb:
                upload_gen.next()

        self.put(path, json=hashmap, success=201)

    def account_post(self,
        update=True, groups={}, metadata={}, quota=None, versioning=None):
        """ Full Pithos+ POST at account level
        --- request parameters ---
        @param update (bool): if True, Do not replace metadata/groups
        --- request headers ---
        @groups (dict): Optional user defined groups in the form
                    {   'group1':['user1', 'user2', ...], 
                        'group2':['userA', 'userB', ...], ...
                    }
        @metadata (dict): Optional user defined metadata in the form
                    {   'name1': 'value1',
                        'name2': 'value2', ...
                    }
        @param quota(integer): If supported, sets the Account quota
        @param versioning(string): If supported, sets the Account versioning
                    to 'auto' or some other supported versioning string
        """
        self.assert_account()
        path = path4url(self.account) + params4url({'update':None}) if update else ''
        for group, usernames in groups.items():
            userstr = ''
            dlm = ''
            for user in usernames:
                userstr = userstr + dlm + user
                dlm = ','
            self.set_header('X-Account-Group-'+group, userstr)
        for metaname, metaval in metadata.items():
            self.set_header('X-Account-Meta-'+metaname, metaval)
        if quota is not None:
            self.set_header('X-Account-Policy-Quota', quota)
        if versioning is not None:
            self.set_header('X-Account-Policy-Versioning', versioning)

        return self.post(path, success=202)

    def set_account_group(self, group, usernames):
        self.account_post(update=True, groups = {group:usernames})

    def del_account_group(self, group):
        return self.account_post(update=True, groups={group:[]})

    def get_account_info(self, until = None,
        if_modified_since=None, if_unmodified_since=None):
        """ --- Optional request parameters ---
        @param until (string): optional timestamp
        --- --- optional request headers ---
        @param if_modified_since (string): Retrieve if account has changed since provided timestamp
        @param if_unmodified_since (string): Retrieve if account has not changed since provided timestamp
        """
        self.assert_account()
        path = path4url(self.account)

        path += '' if until is None else params4url({'until':until})
        if if_modified_since is not None:
            self.set_header('If-Modified-Since', if_modified_since)
        if if_modified_since is not None:
            self.set_header('If-Unmodified-Since', if_unmodified_since)

        r = self.head(path, success=(204, 401))
        if r.status_code == 401:
            raise ClientError("No authorization")
        return r.headers

    def get_account_quota(self):
        return filter_in(self.get_account_info(), 'X-Account-Policy-Quota', exactMatch = True)

    def get_account_versioning(self):
        return filter_in(self.get_account_info(), 'X-Account-Policy-Versioning', exactMatch = True)

    def get_account_meta(self):
        return filter_in(self.get_account_info(), 'X-Account-Meta-')

    def get_account_group(self):
        return filter_in(self.get_account_info(), 'X-Account-Group-')

    def set_account_meta(self, metapairs):
        assert(type(metapairs) is dict)
        self.account_post(update=True, metadata=metapairs)

    def set_account_quota(self, quota):
        self.account_post(update=True, quota=quota)

    def set_account_versioning(self, versioning):
        self.account_post(update=True, versioning = versioning)

    def list_containers(self, 
        limit=None, marker=None, format='json', show_only_shared=False, until=None,
        if_modified_since=None, if_unmodified_since=None):
        """  Full Pithos+ GET at account level
        @param limit (integer): The amount of results requested (server qill use default value if None)
        @param marker (string): Return containers with name lexicographically after marker
        @param format (string): reply format can be json or xml (default: json)
        @param shared (bool): If true, only shared containers will be included in results
        @param until (string): optional timestamp
        --- --- optional request headers ---
        @param if_modified_since (string): Retrieve if account has changed since provided timestamp
        @param if_unmodified_since (string): Retrieve if account has not changed since provided timestamp
        """
        self.assert_account()

        param_dict = dict(format=format)
        if limit is not None:
            param_dict['limit'] = limit
        if marker is not None:
            param_dict['marker'] = marker
        if show_only_shared:
            param_dict['shared'] = None
        if until is not None:
            param_dict['until'] = until

        path = path4url(self.account)+params4url(param_dict)
        if if_modified_since is not None:
            self.set_header('If-Modified-Since', if_modified_since)
        if if_unmodified_since is not None:
            self.set_header('If-Unmodified-Since', if_unmodified_since)

        r = self.get(path, success = (200, 204))
        return r.json

    def get_container_versioning(self, container):
        return filter_in(self.get_container_info(container), 'X-Container-Policy-Versioning')

    def get_container_quota(self, container):
        return filter_in(self.get_container_info(container), 'X-Container-Policy-Quota')

    def get_container_meta(self, container):
        return filter_in(self.get_container_info(container), 'X-Container-Meta-')

    def get_container_object_meta(self, container):
        return filter_in(self.get_container_info(container), 'X-Container-Object-Meta')

    def set_container_meta(self, metapairs):
        assert(type(metapairs) is dict)
        self.assert_container()
        path=path4url(self.account, self.container)+params4url({'update':None})
        for key, val in metapairs.items():
            self.set_header('X-Container-Meta-'+key, val)
        self.post(path, success=202)

    def delete_container_meta(self, metakey):
        headers = self.get_container_info(self.container)
        self.headers = filter_out(headers, 'x-container-meta-'+metakey, exactMatch = True)
        if len(self.headers) == len(headers):
            raise ClientError('X-Container-Meta-%s not found' % metakey, 404)
        path = path4url(self.account, self.container)
        self.post(path, success = 202)

    def replace_container_meta(self, metapairs):
        self.assert_container()
        path=path4url(self.account, self.container)
        for key, val in metapairs.items():
            self.set_header('X-Container-Meta-'+key, val)
        self.post(path, success=202)

    def set_container_quota(self, quota):
        self.assert_container()
        path = path4url(self.account, self.container)+params4url({'update':None})
        self.set_header('X-Container-Policy-Quota', quota)
        self.post(path, success=202)

    def set_container_versioning(self, versioning):
        self.assert_container()
        path = path4url(self.account, self.container)+params4url({'update':None})
        self.set_header('X-Container-Policy-Versioning', versioning)
        self.post(path, success=202)

    def set_object_meta(self, object, metapairs):
        assert(type(metapairs) is dict)
        self.assert_container()
        path=path4url(self.account, self.container, object)+params4url({'update':None})
        for key, val in metapairs.items():
            self.set_header('X-Object-Meta-'+key, val)
        self.post(path, success=202)

    def delete_object_meta(self, metakey, object):
        self.assert_container()
        self.set_header('X-Object-Meta-'+metakey, '')
        path = path4url(self.account, self.container, object)+params4url({'update':None})
        self.post(path, success=202)

    def publish_object(self, object):
        self.assert_container()
        path = path4url(self.account, self.container, object)+params4url({'update':None})
        self.set_header('X-Object-Public', True)
        self.post(path, success=202)

    def unpublish_object(self, object):
        self.assert_container()
        path = path4url(self.account, self.container, object)+params4url({'update':None})
        self.set_header('X-Object-Public', False)
        self.post(path, success=202)

    def get_object_sharing(self, object):
        return filter_in(self.get_object_info(object), 'X-Object-Sharing', exactMatch = True)

    def set_object_sharing(self, object, read_permition = False, write_permition = False):
        """Give read/write permisions to an object.
           @param object is the object to change sharing permitions onto
           @param read_permition is a list of users and user groups that get read permition for this object
                False means all previous read permitions will be removed
           @param write_perimition is a list of users and user groups to get write permition for this object
                False means all previous read permitions will be removed
        """
        self.assert_container()
        perms = ''
        if read_permition:
            dlm = ''
            perms = 'read='
            for rperm in read_permition:
                perms = perms + dlm + rperm
                dlm = ','
        if write_permition:
            dlm = ''
            perms = 'write=' if not read_permition else perms + ';write='
            for wperm in write_permition:
                perms = perms + dlm + wperm
                dlm = ','
        path = path4url(self.account, self.container, object)+params4url({'update':None})
        self.set_header('X-Object-Sharing', perms)
        self.post(path, success=(202, 204))

    def del_object_sharing(self, object):
        self.set_object_sharing(object)

    def append_object(self, object, source_file, upload_cb = None):
        """@poaram upload_db is a generator for showing progress of upload
            to caller application, e.g. a progress bar. Its next is called
            whenever a block is uploaded
        """
        self.assert_container()
        meta = self.get_container_info(self.container)
        blocksize = int(meta['x-container-block-size'])
        filesize = os.fstat(source_file.fileno()).st_size
        nblocks = 1 + (filesize - 1)//blocksize
        offset = 0
        self.set_header('Content-Range', 'bytes */*')
        self.set_header('Content-Type', 'application/octet-stream')
        path=path4url(self.account, self.container, object)+params4url({'update':None})
        if upload_cb is not None:
            upload_gen = upload_cb(nblocks)
        for i in range(nblocks):
            block = source_file.read(min(blocksize, filesize - offset))
            offset += len(block)
            self.set_header('Content-Length', len(block))
            self.post(path, data=block, success=(202, 204))
            if upload_cb is not None:
                upload_gen.next()

    def truncate_object(self, object, upto_bytes):
        self.assert_container()
        self.set_header('Content-Range', 'bytes 0-%s/*'%upto_bytes)
        self.set_header('Content-Type', 'application/octet-stream')
        self.set_header('X-Object-Bytes', upto_bytes)
        self.set_header('X-Source-Object', path4url(self.container, object))
        path=path4url(self.account, self.container, object)+params4url({'update':None})
        self.post(path, success=(202, 204))

    def overwrite_object(self, object, start, end, source_file, upload_cb=None):
        """Overwrite a part of an object with given source file
           @start the part of the remote object to start overwriting from, in bytes
           @end the part of the remote object to stop overwriting to, in bytes
        """
        self.assert_container()
        meta = self.get_container_info(self.container)
        blocksize = int(meta['x-container-block-size'])
        filesize = os.fstat(source_file.fileno()).st_size
        datasize = int(end) - int(start) + 1
        nblocks = 1 + (datasize - 1)//blocksize
        offset = 0
        self.set_header('Content-Range', 'bytes %s-%s/*' % (start, end) )
        self.set_header('Content-Type', 'application/octet-stream')
        path=path4url(self.account, self.container, object)+params4url({'update':None})
        if upload_cb is not None:
            upload_gen = upload_cb(nblocks)
        for i in range(nblocks):
            block = source_file.read(min(blocksize, filesize - offset, datasize - offset))
            offset += len(block)
            self.set_header('Content-Length', len(block))
            self.post(path, data=block, success=(202, 204))
            if upload_cb is not None:
                upload_gen.next()

