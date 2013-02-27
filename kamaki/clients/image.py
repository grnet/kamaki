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

from kamaki.clients import Client, ClientError
from kamaki.clients.utils import path4url


class ImageClient(Client):
    """OpenStack Image Service API 1.0 and GRNET Plankton client"""

    def __init__(self, base_url, token):
        super(ImageClient, self).__init__(base_url, token)

    def list_public(self, detail=False, filters={}, order=''):
        """
        :param detail: (bool)

        :param filters: (dict) request filters

        :param order: (str) order listing by field (default is ascending, - for
            descending)

        :returns: (list) id,name + full image info if detail
        """
        path = path4url('images', 'detail') if detail else (
            path4url('images') + '/')

        async_params = {}
        if isinstance(filters, dict):
            for key, value in filters.items():
                if value:
                    async_params[key] = value
        if order.startswith('-'):
            self.set_param('sort_dir', 'desc')
            order = order[1:]
        else:
            self.set_param('sort_dir', 'asc')
        self.set_param('sort_key', order, iff=order)

        r = self.get(path, async_params=async_params, success=200)
        return r.json

    def get_meta(self, image_id):
        """
        :param image_id: (string)

        :returns: (list) image metadata (key:val)
        """
        path = path4url('images', image_id)
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
        """Register image put at location

        :param name: (str)

        :param location: (str) pithos://<account>/<container>/<path>

        :param params: (dict) image metadata (X-Image-Meta) can be id, store,
            disc_format, container_format, size, checksum, is_public, owner

        :param properties: (dict) image properties (X-Image-Meta-Property)
        """
        path = path4url('images') + '/'
        self.set_header('X-Image-Meta-Name', name)
        self.set_header('X-Image-Meta-Location', location)

        for key, val in params.items():
            if key in ('id', 'store', 'disk_format', 'container_format',
                       'size', 'checksum', 'is_public', 'owner'):
                key = 'x-image-meta-' + key.replace('_', '-')
                self.set_header(key, val)

        for key, val in properties.items():
            self.set_header('X-Image-Meta-Property-%s' % key, val)

        r = self.post(path, success=200)
        r.release()

    def reregister(self, location, name=None, params={}, properties={}):
        """Update existing image (key: location)

        :param location: (str) pithos://<account>/<container>/<path>

        :param name: (str)

        :param params: (dict) image metadata (X-Image-Meta) can be id, store,
            disc_format, container_format, size, checksum, is_public, owner

        :param properties: (dict) image properties (X-Image-Meta-Property)
        """
        path = path4url('images', 'detail')
        r = self.get(path, success=200)
        imgs = [img for img in r.json if img['location'] == location]
        for img in imgs:
            img_name = name if name else img['name']
            img_properties = img['properties']
            for k, v in properties.items():
                img_properties[k] = v
            self.register(img_name, location, params, img_properties)
        r.release()

    def list_members(self, image_id):
        """
        :param image_id: (str)

        :returns: (list) users who can use current user's images
        """
        path = path4url('images', image_id, 'members')
        r = self.get(path, success=200)
        return r.json['members']

    def list_shared(self, member):
        """
        :param member: (str) sharers account

        :returns: (list) images shared by member
        """
        path = path4url('shared-images', member)
        #self.set_param('format', 'json')
        r = self.get(path, success=200)
        return r.json['shared_images']

    def add_member(self, image_id, member):
        """
        :param image_id: (str)

        :param member: (str) user to allow access to current user's images
        """
        path = path4url('images', image_id, 'members', member)
        r = self.put(path, success=204)
        r.release()

    def remove_member(self, image_id, member):
        """
        :param image_id: (str)

        :param member: (str) user to deprive from current user's images
        """
        path = path4url('images', image_id, 'members', member)
        r = self.delete(path, success=204)
        r.release()

    def set_members(self, image_id, members):
        """
        :param image_id: (str)

        :param members: (list) user to deprive from current user's images
        """
        path = path4url('images', image_id, 'members')
        req = {'memberships': [{'member_id': member} for member in members]}
        r = self.put(path, json=req, success=204)
        r.release()
