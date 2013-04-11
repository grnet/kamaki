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

from kamaki.clients import ClientError
from kamaki.clients.compute.rest_api import ComputeRestClient
from kamaki.clients.utils import path4url


class ComputeClient(ComputeRestClient):
    """OpenStack Compute API 1.1 client"""

    def list_servers(self, detail=False):
        """
        :param detail: if true, append full server details to each item

        :returns: list of server ids and names
        """
        detail = 'detail' if detail else ''
        r = self.servers_get(command=detail)
        return r.json['servers']['values']

    def get_server_details(self, server_id, **kwargs):
        """Return detailed info for a server

        :param server_id: integer (int or str)

        :returns: dict with server details
        """
        r = self.servers_get(server_id, **kwargs)
        return r.json['server']

    def create_server(self, name, flavor_id, image_id, personality=None):
        """Submit request to create a new server

        :param name: (str)

        :param flavor_id: integer id denoting a preset hardware configuration

        :param image_id: (str) id denoting the OS image to run on the VM

        :param personality: a list of (file path, file contents) tuples,
            describing files to be injected into VM upon creation.

        :returns: a dict with the new VMs details

        :raises ClientError: wraps request errors
        """
        req = {'server': {'name': name,
                          'flavorRef': flavor_id,
                          'imageRef': image_id}}

        image = self.get_image_details(image_id)
        metadata = {}
        for key in ('os', 'users'):
            try:
                metadata[key] = image['metadata']['values'][key]
            except KeyError:
                pass
        if metadata:
            req['server']['metadata'] = metadata

        if personality:
            req['server']['personality'] = personality

        try:
            r = self.servers_post(json_data=req)
        except ClientError as err:
            try:
                if isinstance(err.details, list):
                    tmp_err = err.details
                else:
                    errd = '%s' % err.details
                    tmp_err = errd.split(',')
                tmp_err = tmp_err[0].split(':')
                tmp_err = tmp_err[2].split('"')
                err.message = tmp_err[1]
            finally:
                raise err
        return r.json['server']

    def update_server_name(self, server_id, new_name):
        """Update the name of the server as reported by the API (does not
            modify the hostname used inside the VM)

        :param server_id: integer (str or int)

        :param new_name: (str)
        """
        req = {'server': {'name': new_name}}
        self.servers_put(server_id, json_data=req)

    def delete_server(self, server_id):
        """Submit a deletion request for a server specified by id

        :param server_id: integer (str or int)
        """
        self.servers_delete(server_id)

    def reboot_server(self, server_id, hard=False):
        """
        :param server_id: integer (str or int)

        :param hard: perform a hard reboot if true, soft reboot otherwise
        """
        boot_type = 'HARD' if hard else 'SOFT'
        req = {'reboot': {'type': boot_type}}
        self.servers_post(server_id, 'action', json_data=req)

    def get_server_metadata(self, server_id, key=''):
        """
        :param server_id: integer (str or int)

        :param key: (str) the metadatum key (all metadata if not given)

        :returns: a key:val dict of requests metadata
        """
        command = path4url('meta', key)
        r = self.servers_get(server_id, command)
        return r.json['meta'] if key else r.json['metadata']['values']

    def create_server_metadata(self, server_id, key, val):
        """
        :param server_id: integer (str or int)

        :param key: (str)

        :param val: (str)

        :returns: dict of updated key:val metadata
        """
        req = {'meta': {key: val}}
        r = self.servers_put(
            server_id,
            'meta/' + key,
            json_data=req,
            success=201)
        return r.json['meta']

    def update_server_metadata(self, server_id, **metadata):
        """
        :param server_id: integer (str or int)

        :param metadata: dict of key:val metadata

        :returns: dict of updated key:val metadata
        """
        req = {'metadata': metadata}
        r = self.servers_post(server_id, 'meta', json_data=req, success=201)
        return r.json['metadata']

    def delete_server_metadata(self, server_id, key):
        """
        :param server_id: integer (str or int)

        :param key: (str) the meta key
        """
        self.servers_delete(server_id, 'meta/' + key)

    def list_flavors(self, detail=False):
        """
        :param detail: (bool) detailed flavor info if set, short if not

        :returns: (dict) flavor info
        """
        r = self.flavors_get(command='detail' if detail else '')
        return r.json['flavors']['values']

    def get_flavor_details(self, flavor_id):
        """
        :param flavor_id: integer (str or int)

        :returns: dict
        """
        r = self.flavors_get(flavor_id)
        return r.json['flavor']

    def list_images(self, detail=False):
        """
        :param detail: (bool) detailed info if set, short if not

        :returns: dict id,name + full info if detail
        """
        detail = 'detail' if detail else ''
        r = self.images_get(command=detail)
        return r.json['images']['values']

    def get_image_details(self, image_id, **kwargs):
        """
        :param image_id: integer (str or int)

        :returns: dict

        :raises ClientError: 404 if image not available
        """
        r = self.images_get(image_id, **kwargs)
        try:
            return r.json['image']
        except KeyError:
            raise ClientError('Image not available', 404, details=[
                'Image %d not found or not accessible'])

    def delete_image(self, image_id):
        """
        :param image_id: (str)
        """
        self.images_delete(image_id)

    def get_image_metadata(self, image_id, key=''):
        """
        :param image_id: (str)

        :param key: (str) the metadatum key

        :returns (dict) metadata if key not set, specific metadatum otherwise
        """
        command = path4url('meta', key)
        r = self.images_get(image_id, command)
        return r.json['meta'] if key else r.json['metadata']['values']

    def create_image_metadata(self, image_id, key, val):
        """
        :param image_id: integer (str or int)

        :param key: (str) metadatum key

        :param val: (str) metadatum value

        :returns: (dict) updated metadata
        """
        req = {'meta': {key: val}}
        r = self.images_put(image_id, 'meta/' + key, json_data=req)
        return r.json['meta']

    def update_image_metadata(self, image_id, **metadata):
        """
        :param image_id: (str)

        :param metadata: dict

        :returns: updated metadata
        """
        req = {'metadata': metadata}
        r = self.images_post(image_id, 'meta', json_data=req)
        return r.json['metadata']

    def delete_image_metadata(self, image_id, key):
        """
        :param image_id: (str)

        :param key: (str) metadatum key
        """
        command = path4url('meta', key)
        self.images_delete(image_id, command)
