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

from .http import HTTPClient


class ComputeClient(HTTPClient):
    """OpenStack Compute API 1.1 client"""
    
    @property
    def url(self):
        url = self.config.get('compute_url') or self.config.get('url')
        if not url:
            raise ClientError('No URL was given')
        return url
    
    @property
    def token(self):
        token = self.config.get('compute_token') or self.config.get('token')
        if not token:
            raise ClientError('No token was given')
        return token
    
    def list_servers(self, detail=False):
        """List servers, returned detailed output if detailed is True"""
        path = '/servers/detail' if detail else '/servers'
        reply = self.http_get(path)
        return reply['servers']['values']
    
    def get_server_details(self, server_id):
        """Return detailed output on a server specified by its id"""
        path = '/servers/%d' % server_id
        reply = self.http_get(path)
        return reply['server']
    
    def create_server(self, name, flavor_id, image_id, personality=None):
        """Submit request to create a new server

        The flavor_id specifies the hardware configuration to use,
        the image_id specifies the OS Image to be deployed inside the new
        server.

        The personality argument is a list of (file path, file contents)
        tuples, describing files to be injected into the server upon creation.

        The call returns a dictionary describing the newly created server.
        """
        req = {'name': name, 'flavorRef': flavor_id, 'imageRef': image_id}
        if personality:
            req['personality'] = personality
        
        body = json.dumps({'server': req})
        reply = self.http_post('/servers', body)
        return reply['server']
    
    def update_server_name(self, server_id, new_name):
        """Update the name of the server as reported by the API.

        This call does not modify the hostname actually used by the server
        internally.
        """
        path = '/servers/%d' % server_id
        body = json.dumps({'server': {'name': new_name}})
        self.http_put(path, body)
    
    def delete_server(self, server_id):
        """Submit a deletion request for a server specified by id"""
        path = '/servers/%d' % server_id
        self.http_delete(path)
    
    def reboot_server(self, server_id, hard=False):
        """Submit a reboot request for a server specified by id"""
        path = '/servers/%d/action' % server_id
        type = 'HARD' if hard else 'SOFT'
        body = json.dumps({'reboot': {'type': type}})
        self.http_post(path, body)
        
    def get_server_metadata(self, server_id, key=None):
        path = '/servers/%d/meta' % server_id
        if key:
            path += '/%s' % key
        reply = self.http_get(path)
        return reply['meta'] if key else reply['metadata']['values']
    
    def create_server_metadata(self, server_id, key, val):
        path = '/servers/%d/meta/%s' % (server_id, key)
        body = json.dumps({'meta': {key: val}})
        reply = self.http_put(path, body, success=201)
        return reply['meta']
    
    def update_server_metadata(self, server_id, **metadata):
        path = '/servers/%d/meta' % server_id
        body = json.dumps({'metadata': metadata})
        reply = self.http_post(path, body, success=201)
        return reply['metadata']
    
    def delete_server_metadata(self, server_id, key):
        path = '/servers/%d/meta/%s' % (server_id, key)
        reply = self.http_delete(path)
        
        
    def list_flavors(self, detail=False):
        path = '/flavors/detail' if detail else '/flavors'
        reply = self.http_get(path)
        return reply['flavors']['values']

    def get_flavor_details(self, flavor_id):
        path = '/flavors/%d' % flavor_id
        reply = self.http_get(path)
        return reply['flavor']
    
    
    def list_images(self, detail=False):
        path = '/images/detail' if detail else '/images'
        reply = self.http_get(path)
        return reply['images']['values']

    def get_image_details(self, image_id):
        path = '/images/%d' % image_id
        reply = self.http_get(path)
        return reply['image']

    def create_image(self, server_id, name):
        req = {'name': name, 'serverRef': server_id}
        body = json.dumps({'image': req})
        reply = self.http_post('/images', body)
        return reply['image']

    def delete_image(self, image_id):
        path = '/images/%d' % image_id
        self.http_delete(path)

    def get_image_metadata(self, image_id, key=None):
        path = '/images/%d/meta' % image_id
        if key:
            path += '/%s' % key
        reply = self.http_get(path)
        return reply['meta'] if key else reply['metadata']['values']
    
    def create_image_metadata(self, image_id, key, val):
        path = '/images/%d/meta/%s' % (image_id, key)
        body = json.dumps({'meta': {key: val}})
        reply = self.http_put(path, body, success=201)
        reply['meta']

    def update_image_metadata(self, image_id, **metadata):
        path = '/images/%d/meta' % image_id
        body = json.dumps({'metadata': metadata})
        reply = self.http_post(path, body, success=201)
        return reply['metadata']

    def delete_image_metadata(self, image_id, key):
        path = '/images/%d/meta/%s' % (image_id, key)
        reply = self.http_delete(path)
