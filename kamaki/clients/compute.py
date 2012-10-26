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
import json


class ComputeClient(Client):
    """OpenStack Compute API 1.1 client"""

    def raise_for_status(self, r):
        try:
            d = r.json
            key = d.keys()[0]
            val = d[key]
            message = '%s: %s' % (key, val.get('message', ''))
            details = val.get('details', '')
        except AttributeError:
            message = 'Request responded with error code '+unicode(r.status_code)
            details = unicode(r.request.method)+' '+unicode(r.request.url)
        raise ClientError(message, r.status_code, details)
    
    def servers_get(self, server_id='', command='', **kwargs):
        """GET base_url/servers[/server_id][/command] request
        @param server_id or ''
        @param command: can be 'ips', 'stats', or ''
        """
        path = path4url('servers', server_id, command)
        success = kwargs.pop('success', 200)
        return self.get(path, success=success, **kwargs)

    def servers_delete(self, server_id='', command='', **kwargs):
        """DEL ETE base_url/servers[/server_id][/command] request
        @param server_id or ''
        @param command: can be 'ips', 'stats', or ''
        """
        path = path4url('servers', server_id, command)
        success = kwargs.pop('success', 204)
        return self.delete(path, success=success, **kwargs)

    def servers_post(self, server_id='', command='', json_data=None, **kwargs):
        """POST base_url/servers[/server_id]/[command] request
        @param server_id or ''
        @param command: can be 'action' or ''
        @param json_data: a json valid dict that will be send as data
        """
        data = json_data
        if json_data is not None:
            data = json.dumps(json_data)
            self.set_header('Content-Type', 'application/json')
            self.set_header('Content-Length', len(data))

        path = path4url('servers', server_id, command)
        success = kwargs.pop('success', 202)
        return self.post(path, data=data, success=success, **kwargs)

    def servers_put(self, server_id='', command='', json_data=None, **kwargs):
        """PUT base_url/servers[/server_id]/[command] request
        @param server_id or ''
        @param command: can be 'action' or ''
        @param json_data: a json valid dict that will be send as data
        """
        data = json_data
        if json_data is not None:
            data = json.dumps(json_data)
            self.set_header('Content-Type', 'application/json')
            self.set_header('Content-Length', len(data))

        path = path4url('servers', server_id, command)
        success = kwargs.pop('success', 204)
        return self.put(path, data=data, success=success, **kwargs)

    def list_servers(self, detail=False):
        """List servers, returned detailed output if detailed is True"""
        detail = 'detail' if detail else ''
        r = self.servers_get(command=detail)
        return r.json['servers']['values']
    
    def get_server_details(self, server_id, **kwargs):
        """Return detailed output on a server specified by its id"""
        r = self.servers_get(server_id, **kwargs)
        return r.json['server']
    
    def create_server(self, name, flavor_id, image_id, personality=None):
        """Submit request to create a new server

        The flavor_id specifies the hardware configuration to use,
        the image_id specifies the OS Image to be deployed inside the new
        server.

        The personality argument is a list of (file path, file contents)
        tuples, describing files to be injected into the server upon creation.

        The call returns a dictionary describing the newly created server.
        """
        req = {'server': {'name': name,
                          'flavorRef': flavor_id,
                          'imageRef': image_id}}
        if personality:
            req['server']['personality'] = personality
        
        try:
            r = self.servers_post(json_data=req)
        except ClientError as err:
            try:
                err.message = err.details.split(',')[0].split(':')[2].split('"')[1]
            finally:
                raise err
        return r.json['server']
    
    def update_server_name(self, server_id, new_name):
        """Update the name of the server as reported by the API.

        This call does not modify the hostname actually used by the server
        internally.
        """
        req = {'server': {'name': new_name}}
        r = self.servers_put(server_id, json_data=req)
        r.release()
    
    def delete_server(self, server_id):
        """Submit a deletion request for a server specified by id"""
        r = self.servers_delete(server_id)
        r.release()

    def reboot_server(self, server_id, hard=False):
        """Submit a reboot request for a server specified by id"""
        type = 'HARD' if hard else 'SOFT'
        req = {'reboot': {'type': type}}
        r = self.servers_post(server_id, 'action', json_data=req)
        r.release()
    
    def get_server_metadata(self, server_id, key=''):
        command = path4url('meta', key)
        r = self.servers_get(server_id, command)
        return r.json['meta'] if key != '' else r.json['metadata']['values']
    
    def create_server_metadata(self, server_id, key, val):
        req = {'meta': {key: val}}
        r = self.servers_put(server_id, 'meta/'+key, json_data=req, success=201)
        return r.json['meta']
    
    def update_server_metadata(self, server_id, **metadata):
        req = {'metadata': metadata}
        r = self.servers_post(server_id, 'meta', json_data=req, success=201)
        return r.json['metadata']
    
    def delete_server_metadata(self, server_id, key):
        r = self.servers_delete(server_id, 'meta/'+key)
        r.release()

   
    def flavors_get(self, flavor_id='', command='', **kwargs):
        """GET base_url[/flavor_id][/command]
        @param flavor_id
        @param command
        """
        path = path4url('flavors', flavor_id, command)
        success=kwargs.pop('success', 200)
        return self.get(path, success=success, **kwargs)

    def list_flavors(self, detail=False):
        detail = 'detail' if detail else ''
        r = self.flavors_get(command='detail')
        return r.json['flavors']['values']

    def get_flavor_details(self, flavor_id):
        r = self.flavors_get(flavor_id)
        return r.json['flavor']
    

    def images_get(self, image_id='', command='', **kwargs):
        """GET base_url[/image_id][/command]
        @param image_id
        @param command
        """
        path = path4url('images', image_id, command)
        success=kwargs.pop('success', 200)
        return self.get(path, success=success, **kwargs)

    def images_delete(self, image_id='', command='', **kwargs):
        """DEL ETE base_url[/image_id][/command]
        @param image_id
        @param command
        """
        path = path4url('images', image_id, command)
        success=kwargs.pop('success', 204)
        return self.delete(path, success=success, **kwargs)

    def images_post(self, image_id='', command='', json_data=None, **kwargs):
        """POST base_url/images[/image_id]/[command] request
        @param image_id or ''
        @param command: can be 'action' or ''
        @param json_data: a json valid dict that will be send as data
        """
        data = json_data
        if json_data is not None:
            data = json.dumps(json_data)
            self.set_header('Content-Type', 'application/json')
            self.set_header('Content-Length', len(data))

        path = path4url('images', image_id, command)
        success = kwargs.pop('success', 201)
        return self.post(path, data=data, success=success, **kwargs)

    def images_put(self, image_id='', command='', json_data=None, **kwargs):
        """PUT base_url/images[/image_id]/[command] request
        @param image_id or ''
        @param command: can be 'action' or ''
        @param json_data: a json valid dict that will be send as data
        """
        data = json_data
        if json_data is not None:
            data = json.dumps(json_data)
            self.set_header('Content-Type', 'application/json')
            self.set_header('Content-Length', len(data))

        path = path4url('images', image_id, command)
        success = kwargs.pop('success', 201)
        return self.put(path, data=data, success=success, **kwargs)

    def list_images(self, detail=False):
        detail = 'detail' if detail else ''
        r = self.images_get(command=detail)
        return r.json['images']['values']
    
    def get_image_details(self, image_id, **kwargs):
        r = self.images_get(image_id, **kwargs)
        try:
            return r.json['image']
        except KeyError:
            raise ClientError('Image not available', 404,
                details='Image %d not found or not accessible')
    
    def delete_image(self, image_id):
        r = self.images_delete(image_id)
        r.release()

    def get_image_metadata(self, image_id, key=''):
        command = path4url('meta', key)
        r = self.images_get(image_id, command)
        return r.json['meta'] if key != '' else r.json['metadata']['values']
    
    def create_image_metadata(self, image_id, key, val):
        req = {'meta': {key: val}}
        r = self.images_put(image_id, 'meta/'+key, json_data=req)
        return r.json['meta']

    def update_image_metadata(self, image_id, **metadata):
        req = {'metadata': metadata}
        r - self.images_post(image_id, 'meta', json_data=req)
        return r.json['metadata']

    def delete_image_metadata(self, image_id, key):
        command = path4url('meta', key)
        r = self.images_delete(image_id, command)
        r.release()
