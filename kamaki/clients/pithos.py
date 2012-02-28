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

import hashlib
import os

from ..utils import OrderedDict

from .storage import StorageClient


def pithos_hash(block, blockhash):
    h = hashlib.new(blockhash)
    h.update(block.rstrip('\x00'))
    return h.hexdigest()


class PithosClient(StorageClient):
    """GRNet Pithos API client"""
    
    def put_block(self, data, hash):
        path = '/%s/%s' % (self.account, self.container)
        params = {'update': ''}
        headers = {'Content-Type': 'application/octet-stream',
                   'Content-Length': str(len(data))}
        r = self.post(path, params=params, data=data, headers=headers,
                      success=202)
        assert r.text.strip() == hash, 'Local hash does not match server'
    
    def create_object(self, object, f, hash_cb=None, upload_cb=None):
        """Create an object by uploading only the missing blocks
        
        hash_cb is a generator function taking the total number of blocks to
        be hashed as an argument. Its next() will be called every time a block
        is hashed.
        
        upload_cb is a generator function with the same properties that is
        called every time a block is uploaded.
        """
        self.assert_container()
        
        meta = self.get_container_meta(self.container)
        blocksize = int(meta['block-size'])
        blockhash = meta['block-hash']
        
        file_size = os.fstat(f.fileno()).st_size
        nblocks = 1 + (file_size - 1) // blocksize
        hashes = OrderedDict()
        
        size = 0
        
        if hash_cb:
            hash_gen = hash_cb(nblocks)
            hash_gen.next()
        for i in range(nblocks):
            block = f.read(blocksize)
            bytes = len(block)
            hash = pithos_hash(block, blockhash)
            hashes[hash] = (size, bytes)
            size += bytes
            if hash_cb:
                hash_gen.next()
        
        assert size == file_size
                
        path = '/%s/%s/%s' % (self.account, self.container, object)
        params = dict(format='json', hashmap='')
        hashmap = dict(bytes=size, hashes=hashes.keys())
        r = self.put(path, params=params, json=hashmap, success=(201, 409))
        
        if r.status_code == 201:
            return
        
        missing = r.json
        
        if upload_cb:
            upload_gen = upload_cb(len(missing))
            upload_gen.next()
        for hash in missing:
            offset, bytes = hashes[hash]
            f.seek(offset)
            data = f.read(bytes)
            self.put_block(data, hash)
            if upload_cb:
                upload_gen.next()
        
        self.put(path, params=params, json=hashmap, success=201)
