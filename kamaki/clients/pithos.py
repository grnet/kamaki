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

from .storage import StorageClient
from .utils import path4url, params4url, prefix_keys, filter_in, filter_out


def pithos_hash(block, blockhash):
    h = hashlib.new(blockhash)
    h.update(block.rstrip('\x00'))
    return h.hexdigest()


class PithosClient(StorageClient):
    """GRNet Pithos API client"""

    def purge_container(self, container):
        self.assert_account()
        path = '/%s/%s' % (self.account, container)
        params = {'until': int(time())}
        self.delete(path, params=params, success=204)

    def put_block(self, data, hash):
        path = '/%s/%s' % (self.account, self.container)
        params = {'update': ''}
        headers = {'Content-Type': 'application/octet-stream',
                   'Content-Length': str(len(data))}
        r = self.post(path, params=params, data=data, headers=headers,
                      success=202)
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
        print(unicode(meta))
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

        path = '/%s/%s/%s' % (self.account, self.container, object)
        params = dict(format='json', hashmap='')
        hashmap = dict(bytes=size, hashes=hashes)
        headers = {'Content-Type': 'application/octet-stream'}
        r = self.put(path, params=params, headers=headers, json=hashmap,
                     success=(201, 409))

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

        self.put(path, params=params, headers=headers, json=hashmap,
                 success=201)

    def get_account_policy(self):
        return filter_in(self.get_account_info(), 'X-Account-Policy-')

    def get_account_meta(self):
        return filter_in(self.get_account_info(), 'X-Account-Meta-')

    def set_account_meta(self, metapairs):
        assert(type(metapairs) is dict)
        self.assert_account()
        path = path4url(self.account)+params4url({'update':None})
        meta = prefix_keys(metapairs, 'X-Account-Meta-')
        self.post(path, meta=meta, success=202)

    def get_container_policy(self, container):
        return filter_in(self.get_container_info(container), 'X-Container-Policy-')

    def get_container_meta(self, container):
        return filter_in(self.get_container_info(container), 'X-Container-Meta-')

    def get_container_object_meta(self, container):
        return filter_in(self.get_container_info(container), 'X-Container-Object-Meta')

    def set_container_meta(self, metapairs):
        assert(type(metapairs) is dict)
        self.assert_container()
        path=path4url(self.account, self.container)+params4url({'update':None})
        meta = prefix_keys(metapairs, 'X-Container-Meta-')
        self.post(path, meta=meta, success=202)

    def delete_container_meta(self, metakey):
        headers = self.get_container_info(self.container)
        new_headers = filter_out(headers, 'x-container-meta-'+metakey, exactMatch = True)
        if len(new_headers) == len(headers):
            raise ClientError('X-Container-Meta-%s not found' % metakey, 404)
        path = path4url(self.account, self.container)
        self.post(path, headers=new_headers, success = 202)

    def replace_container_meta(self, metapairs):
        self.assert_container()
        path=path4url(self.account, self.container)
        meta = prefix_keys(metapairs, 'X-Container-Meta-')
        self.post(path, meta=meta, success=202)

    def set_object_meta(self, object, metapairs):
        assert(type(metapairs) is dict)
        self.assert_container()
        path=path4url(self.account, self.container, object)+params4url({'update':None})
        meta = prefix_keys(metapairs, 'X-Object-Meta-')
        self.post(path, meta=meta, success=202)
