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
import logging

from httplib import HTTPConnection, HTTPSConnection
from urllib import quote
from urlparse import urlparse


log = logging.getLogger('kamaki.client')


class ClientError(Exception):
    def __init__(self, message, status=0, details=''):
        self.message = message
        self.status = status
        self.details = details

    def __int__(self):
        return int(self.status)

    def __str__(self):
        r = self.message
        if self.status:
            r += "\nHTTP Status: %d" % self.status
        if self.details:
            r += "\nDetails: \n%s" % self.details
        return r


class Client(object):
    def __init__(self, url, token=''):
        self.url = url
        self.token = token
    
    def http_cmd(self, method, path, body=None, headers=None, success=200):
        p = urlparse(self.url)
        path = p.path + path
        if p.scheme == 'http':
            conn = HTTPConnection(p.netloc)
        elif p.scheme == 'https':
            conn = HTTPSConnection(p.netloc)
        else:
            raise ClientError('Unknown URL scheme')
        
        headers = headers or {}
        headers['X-Auth-Token'] = self.token
        if body:
            headers['Content-Type'] = 'application/json'
            headers['Content-Length'] = len(body)
        
        log.debug('>' * 50)
        log.debug('%s %s', method, path)
        for key, val in headers.items():
            log.debug('%s: %s', key, val)
        if body:
            log.debug('')
            log.debug(body)
        
        conn.request(method, path, body, headers)
        
        resp = conn.getresponse()
        buf = resp.read()
        
        log.debug('<' * 50)
        log.info('%d %s', resp.status, resp.reason)
        for key, val in resp.getheaders():
            log.info('%s: %s', key.capitalize(), val)
        log.info('')
        log.debug(buf)
        log.debug('-' * 50)
        
        try:
            reply = json.loads(buf) if buf else {}
        except ValueError:
            raise ClientError('Did not receive valid JSON reply',
                              resp.status, buf)
        
        if resp.status != success:
            if len(reply) == 1:
                key = reply.keys()[0]
                val = reply[key]
                message = '%s: %s' % (key, val.get('message', ''))
                details = val.get('details', '')
                raise ClientError(message, resp.status, details)
            else:
                raise ClientError('Invalid response from the server')

        return reply
    
    def http_get(self, path, success=200):
        return self.http_cmd('GET', path, success=success)
    
    def http_post(self, path, body=None, headers=None, success=202):
        return self.http_cmd('POST', path, body, headers, success)
    
    def http_put(self, path, body, success=204):
        return self.http_cmd('PUT', path, body, success=success)
    
    def http_delete(self, path, success=204):
        return self.http_cmd('DELETE', path, success=success)


class ComputeClient(Client):
    # Servers
    
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
    
    def start_server(self, server_id):
        """Submit a startup request for a server specified by id"""
        path = '/servers/%d/action' % server_id
        body = json.dumps({'start': {}})
        self.http_post(path, body)
    
    def shutdown_server(self, server_id):
        """Submit a shutdown request for a server specified by id"""
        path = '/servers/%d/action' % server_id
        body = json.dumps({'shutdown': {}})
        self.http_post(path, body)
    
    def get_server_console(self, server_id):
        """Get a VNC connection to the console of a server specified by id"""
        path = '/servers/%d/action' % server_id
        body = json.dumps({'console': {'type': 'vnc'}})
        reply = self.http_post(path, body, success=200)
        return reply['console']
    
    def set_firewall_profile(self, server_id, profile):
        """Set the firewall profile for the public interface of a server

        The server is specified by id, the profile argument
        is one of (ENABLED, DISABLED, PROTECTED).
        """
        path = '/servers/%d/action' % server_id
        body = json.dumps({'firewallProfile': {'profile': profile}})
        self.http_post(path, body)
    
    def list_server_addresses(self, server_id, network=None):
        path = '/servers/%d/ips' % server_id
        if network:
            path += '/%s' % network
        reply = self.http_get(path)
        return [reply['network']] if network else reply['addresses']['values']
    
    def get_server_metadata(self, server_id, key=None):
        path = '/servers/%d/meta' % server_id
        if key:
            path += '/%s' % key
        reply = self.http_get(path)
        return reply['meta'] if key else reply['metadata']['values']
    
    def create_server_metadata(self, server_id, key, val):
        path = '/servers/%d/meta/%s' % (server_id, key)
        body = json.dumps({'meta': {key: val}})
        reply = self.http_put(path, body, 201)
        return reply['meta']
    
    def update_server_metadata(self, server_id, **metadata):
        path = '/servers/%d/meta' % server_id
        body = json.dumps({'metadata': metadata})
        reply = self.http_post(path, body, success=201)
        return reply['metadata']
    
    def delete_server_metadata(self, server_id, key):
        path = '/servers/%d/meta/%s' % (server_id, key)
        reply = self.http_delete(path)
    
    def get_server_stats(self, server_id):
        path = '/servers/%d/stats' % server_id
        reply = self.http_get(path)
        return reply['stats']
    
    
    # Flavors
    
    def list_flavors(self, detail=False):
        path = '/flavors/detail' if detail else '/flavors'
        reply = self.http_get(path)
        return reply['flavors']['values']

    def get_flavor_details(self, flavor_id):
        path = '/flavors/%d' % flavor_id
        reply = self.http_get(path)
        return reply['flavor']
    
    
    # Images
    
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
        reply = self.http_put(path, body, 201)
        reply['meta']

    def update_image_metadata(self, image_id, **metadata):
        path = '/images/%d/meta' % image_id
        body = json.dumps({'metadata': metadata})
        reply = self.http_post(path, body, success=201)
        return reply['metadata']

    def delete_image_metadata(self, image_id, key):
        path = '/images/%d/meta/%s' % (image_id, key)
        reply = self.http_delete(path)
    
    
    # Networks
    
    def list_networks(self, detail=False):
        path = '/networks/detail' if detail else '/networks'
        reply = self.http_get(path)
        return reply['networks']['values']
    
    def create_network(self, name):
        body = json.dumps({'network': {'name': name}})
        reply = self.http_post('/networks', body)
        return reply['network']
    
    def get_network_details(self, network_id):
        path = '/networks/%s' % network_id
        reply = self.http_get(path)
        return reply['network']
    
    def update_network_name(self, network_id, new_name):
        path = '/networks/%s' % network_id
        body = json.dumps({'network': {'name': new_name}})
        self.http_put(path, body)
    
    def delete_network(self, network_id):
        path = '/networks/%s' % network_id
        self.http_delete(path)

    def connect_server(self, server_id, network_id):
        path = '/networks/%s/action' % network_id
        body = json.dumps({'add': {'serverRef': server_id}})
        self.http_post(path, body)
    
    def disconnect_server(self, server_id, network_id):
        path = '/networks/%s/action' % network_id
        body = json.dumps({'remove': {'serverRef': server_id}})
        self.http_post(path, body)


class GlanceClient(Client):
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
