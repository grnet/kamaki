# Copyright 2011-2015 GRNET S.A. All rights reserved.
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

from kamaki.clients import Client, ClientError, quote
from kamaki.clients.utils import path4url


def _format_image_headers(headers):
    reply = dict(properties=dict())
    meta_prefix = 'x-image-meta-'
    property_prefix = 'x-image-meta-property-'

    for key, val in headers.items():
        key = key.lower()
        if key.startswith(property_prefix):
            key = key[len(property_prefix):].replace('-', '_')
            reply['properties'][key] = val
        elif key.startswith(meta_prefix):
            key = key[len(meta_prefix):]
            reply[key] = val
    return reply


class ImageClient(Client):
    """Synnefo Plankton API client"""
    service_type = 'image'

    def __init__(self, endpoint_url, token):
        super(ImageClient, self).__init__(endpoint_url, token)
        self.request_headers_to_quote = ['X-Image-Meta-Name', ]
        self.request_header_prefices_to_quote = ['X-Image-Meta-Property-', ]
        self.response_headers = [
            'X-Image-Meta-Name', 'X-Image-Meta-Location',
            'X-Image-Meta-Description']
        self.response_header_prefices = ['X-Image-Meta-Property-', ]

    def list_public(self, detail=False, filters={}, order=''):
        """
        :param detail: (bool)

        :param filters: (dict) request filters

        :param order: (str) order listing by field (default is ascending, - for
            descending)

        :returns: (list) id,name + full image info if detail
        """
        path = path4url('images', 'detail') if detail else (
            '%s/' % path4url('images'))

        async_params = {}
        if isinstance(filters, dict):
            for key, value in filters.items():
                if value:
                    async_params[key] = value
        if order and order.startswith('-'):
            async_params['sort_dir'] = 'desc'
            order = order[1:]
        else:
            async_params['sort_dir'] = 'asc'
        if order:
            async_params['sort_key'] = order

        r = self.get(path, async_params=async_params, success=200)
        return r.json

    def get_meta(self, image_id):
        """
        :param image_id: (string)

        :returns: (list) image metadata (key:val)
        """
        path = path4url('images', image_id)
        r = self.head(path, success=200)

        return _format_image_headers(r.headers)

    def register(self, name, location, params={}, properties={}):
        """Register an image that is uploaded at location

        :param name: (str)

        :param location: (str or iterable) if iterable, then
            (user_uuid, container, image_path) else if string
            pithos://<user_uuid>/<container>/<image object>

        :param params: (dict) image metadata (X-Image-Meta) can be id, store,
            disc_format, container_format, size, checksum, is_public, owner

        :param properties: (dict) image properties (X-Image-Meta-Property)

        :returns: (dict) metadata of the created image
        """
        path = '%s/' % path4url('images')
        self.set_header('X-Image-Meta-Name', name)
        location = location if (
            isinstance(location, str) or isinstance(location, unicode)) else (
                'pithos://%s' % '/'.join(location))
        prefix = 'pithos://'
        if location.startswith(prefix):
            lvalues = (location[len(prefix):]).split('/')
            location = '%s%s' % (prefix, '/'.join([
                quote(s.encode('utf-8')) for s in lvalues]))
        else:
            lvalues = location.split('/')
            location = '.'.join([quote(s.encode('utf-8')) for s in lvalues])
        self.set_header('X-Image-Meta-Location', location)

        async_headers = {}
        for key, val in params.items():
            if key in ('store', 'disk_format', 'container_format',
                       'size', 'checksum', 'is_public', 'owner') and val:
                key = 'x-image-meta-' + key.replace('_', '-')
                async_headers[key] = val

        for key, val in properties.items():
            async_headers['x-image-meta-property-%s' % key] = val

        r = self.post(path, success=200, async_headers=async_headers)

        return _format_image_headers(r.headers)

    def unregister(self, image_id):
        """Unregister an image

        :param image_id: (str)

        :returns: (dict) response headers
        """
        path = path4url('images', image_id)
        r = self.delete(path, success=204)
        return r.headers

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
        r = self.get(path, success=200)
        return r.json['shared_images']

    def add_member(self, image_id, member):
        """
        :param image_id: (str)

        :param member: (str) user to allow access to current user's images
        """
        path = path4url('images', image_id, 'members', member)
        self.set_header('Content-Length', 0)
        r = self.put(path, success=204)
        return r.headers

    def remove_member(self, image_id, member):
        """
        :param image_id: (str)

        :param member: (str) user to deprive from current user's images
        """
        path = path4url('images', image_id, 'members', member)
        r = self.delete(path, success=204)
        return r.headers

    def set_members(self, image_id, members):
        """
        :param image_id: (str)

        :param members: (list) user to deprive from current user's images
        """
        path = path4url('images', image_id, 'members')
        req = {'memberships': [{'member_id': member} for member in members]}
        r = self.put(path, json=req, success=204)
        return r.headers

    def update_image(
            self, image_id,
            name=None, disk_format=None, container_format=None,
            status=None, public=None, owner_id=None, **properties):
        path = path4url('images', image_id)
        if name is not None:
            self.set_header('X-Image-Meta-Name', name)
        if disk_format is not None:
            self.set_header('X-Image-Meta-Disk-Format', disk_format)
        if container_format is not None:
            self.set_header('X-Image-Meta-Container-Format', container_format)
        if status is not None:
            self.set_header('X-Image-Meta-Status', status)
        if public is not None:
            self.set_header('X-Image-Meta-Is-Public', bool(public))
        if owner_id is not None:
            self.set_header('X-Image-Meta-Owner', owner_id)
        for k, v in properties.items():
            self.set_header('X-Image-Meta-Property-%s' % k, v)
        self.set_header('Content-Length', 0)
        r = self.put(path, success=200)
        return r.headers
