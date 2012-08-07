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
from .utils import path4url


class ImageClient(Client):
    """OpenStack Image Service API 1.0 and GRNET Plankton client"""

    def raise_for_status(self, r):
        if r.status_code == 404:
            raise ClientError("Image not found", r.status_code)

        # Fallback to the default
        super(ImageClient, self).raise_for_status(r)

    def list_public(self, detail=False, filters={}, order=''):
        path = path4url('images','detail') if detail else path4url('images/')
        params = {}
        params.update(filters)

        if order.startswith('-'):
            params['sort_dir'] = 'desc'
            order = order[1:]
        else:
            params['sort_dir'] = 'asc'

        if order:
            params['sort_key'] = order

        r = self.get(path, params=params, success=200)
        return r.json

    def get_meta(self, image_id):
        path=path4url('images', image_id)
        r = self.head(path, success=200)

        reply = {}
        properties = {}
        meta_prefix = 'x-image-meta-'
        property_prefix = 'x-image-meta-property-'

        for key, val in r.headers.items():
            key = key.lower()
            if key.startswith(property_prefix):
                key = key[len(property_prefix):]
                properties[key] = val
            elif key.startswith(meta_prefix):
                key = key[len(meta_prefix):]
                reply[key] = val

        if properties:
            reply['properties'] = properties
        return reply

    def register(self, name, location, params={}, properties={}):
        path = path4url('images/')
        self.set_header('X-Image-Meta-Name', name)
        self.set_header('X-Image-Meta-Location', location)

        for key, val in params.items():
            if key in ('id', 'store', 'disk_format', 'container_format',
                       'size', 'checksum', 'is_public', 'owner'):
                key = 'x-image-meta-' + key.replace('_', '-')
                self.set_header(key, val)

        for key, val in properties.items():
            self.set_header('X-Image-Meta-Property-'+key, val)

        self.post(path, success=200)

    def list_members(self, image_id):
        path = path4url('images',image_id,'members')
        r = self.get(path, success=200)
        return r.json['members']

    def list_shared(self, member):
        path = path4url('shared-images', member)
        r = self.get(path, success=200)
        return r.json['shared_images']

    def add_member(self, image_id, member):
        path = path4url('images', image_id, 'members', member)
        self.put(path, success=204)

    def remove_member(self, image_id, member):
        path = path4url('images', image_id, 'members', member)
        self.delete(path, success=204)

    def set_members(self, image_id, members):
        path = path4url('images', image_id, 'members')
        req = {'memberships': [{'member_id': member} for member in members]}
        self.put(path, json=req, success=204)
