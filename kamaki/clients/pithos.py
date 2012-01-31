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
import json

from . import ClientError
from .storage import StorageClient


class PithosClient(StorageClient):
    """GRNet Pithos API client"""
    
    def put_block(self, data, hash):
        path = '/%s/%s?update' % (self.account, self.container)
        headers = {'Content-Type': 'application/octet-stream',
                   'Content-Length': len(data)}
        resp, reply = self.raw_http_cmd('POST', path, data, headers,
                                        success=202)
        assert reply.strip() == hash, 'Local hash does not match server'
    
    def create_object(self, object, f):
        meta = self.get_container_meta()
        blocksize = int(meta['block-size'])
        blockhash = meta['block-hash']
        
        size = 0
        hashes = {}
        data = f.read(blocksize)
        while data:
            bytes = len(data)
            h = hashlib.new(blockhash)
            h.update(data.rstrip('\x00'))
            hash = h.hexdigest()
            hashes[hash] = (size, bytes)
            size += bytes
            data = f.read(blocksize)
                
        path = '/%s/%s/%s?hashmap&format=json' % (self.account, self.container,
                                                  object)
        hashmap = dict(bytes=size, hashes=hashes)
        req = json.dumps(hashmap)
        resp, reply = self.raw_http_cmd('PUT', path, req, success=None)
        
        if resp.status not in (201, 409):
            raise ClientError('Invalid response from the server')
        
        if resp.status == 201:
            return
        
        missing = json.loads(reply)
        
        for hash in missing:
            offset, bytes = hashes[hash]
            f.seek(offset)
            data = f.read(bytes)
            self.put_block(data, hash)
        
        self.http_put(path, req, success=201)
