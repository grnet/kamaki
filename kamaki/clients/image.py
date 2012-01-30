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

"""
    OpenStack Image Service API 1.0 client
"""

from urllib import quote

from . import ClientError
from .http import HTTPClient


class ImageClient(HTTPClient):
    @property
    def url(self):
        url = self.config.get('image_url') or self.config.get('url')
        if not url:
            raise ClientError('No URL was given')
        return url
    
    @property
    def token(self):
        token = self.config.get('image_token') or self.config.get('token')
        if not token:
            raise ClientError('No token was given')
        return token
    
    def list_public(self, detail=False, filters={}, order=''):
        path = '/images/detail' if detail else '/images/'
        params = {}
        params.update(filters)
        
        if order.startswith('-'):
            params['sort_dir'] = 'desc'
            order = order[1:]
        else:
            params['sort_dir'] = 'asc'
        
        if order:
            params['sort_key'] = order
        
        if params:
            path += '?' + '&'.join('%s=%s' % item for item in params.items())
        return self.http_get(path)
    
    def get_meta(self, image_id):
        path = '/images/%s' % image_id
        resp, buf = self.raw_http_cmd('HEAD', path)
        reply = {}
        prefix = 'x-image-meta-'
        for key, val in resp.getheaders():
            key = key.lower()
            if not key.startswith(prefix):
                continue
            key = key[len(prefix):]
            reply[key] = val
        return reply
    
    def register(self, name, location, params={}, properties={}):
        path = '/images/'
        headers = {}
        headers['x-image-meta-name'] = quote(name)
        headers['x-image-meta-location'] = location
        for key, val in params.items():
            if key in ('id', 'store', 'disk_format', 'container_format',
                       'size', 'checksum', 'is_public', 'owner'):
                key = 'x-image-meta-' + key.replace('_', '-')
                headers[key] = val
        for key, val in properties.items():
            headers['x-image-meta-property-' + quote(key)] = quote(val)
        return self.http_post(path, headers=headers, success=200)
    
    def list_members(self, image_id):
        path = '/images/%s/members' % image_id
        reply = self.http_get(path)
        return reply['members']

    def list_shared(self, member):
        path = '/shared-images/%s' % member
        reply = self.http_get(path)
        return reply['shared_images']

    def add_member(self, image_id, member):
        path = '/images/%s/members/%s' % (image_id, member)
        self.http_put(path)
    
    def remove_member(self, image_id, member):
        path = '/images/%s/members/%s' % (image_id, member)
        self.http_delete(path)
    
    def set_members(self, image_id, members):
        path = '/images/%s/members' % image_id
        req = {'memberships': [{'member_id': member} for member in members]}
        body = json.dumps(req)
        self.http_put(path, body)
