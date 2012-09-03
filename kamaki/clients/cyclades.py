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

from .compute import ComputeClient, ClientError
from .utils import path4url
import json

class CycladesClient(ComputeClient):
    """GRNet Cyclades API client"""



    def networks_get(self, network_id = '', command='', **kwargs):
        """GET base_url/networks[/network_id][/command] request
        @param network_id or ''
        @param command can be 'detail', or ''
        """
        path=path4url('networks', network_id, command)
        success = kwargs.pop('success', (200, 203))
        return self.get(path, success=success, **kwargs)

    def networks_delete(self, network_id = '', command='', **kwargs):
        """DEL ETE base_url/networks[/network_id][/command] request
        @param network_id or ''
        @param command can be 'detail', or ''
        """
        path=path4url('networks', network_id, command)
        success = kwargs.pop('success', 204)
        return self.delete(path, success=success, **kwargs)

    def networks_post(self, network_id = '', command='', json_data=None, **kwargs):
        """POST base_url/servers[/server_id]/[command] request
        @param server_id or ''
        @param command: can be 'action' or ''
        @param json_data: a json valid dict that will be send as data
        """
        data= json_data
        if json_data is not None:
            data = json.dumps(json_data)
            self.set_header('Content-Type', 'application/json')
            self.set_header('Content-Length', len(data))

        path = path4url('networks', network_id, command)
        success = kwargs.pop('success', 202)
        return self.post(path, data=data, success=success, **kwargs)

    def networks_put(self, network_id = '', command='', json_data=None, **kwargs):
        """PUT base_url/servers[/server_id]/[command] request
        @param server_id or ''
        @param command: can be 'action' or ''
        @param json_data: a json valid dict that will be send as data
        """
        data= json_data
        if json_data is not None:
            data = json.dumps(json_data)
            self.set_header('Content-Type', 'application/json')
            self.set_header('Content-Length', len(data))

        path = path4url('networks', network_id, command)
        success = kwargs.pop('success', 204)
        return self.put(path, data=data, success=success, **kwargs)

    def start_server(self, server_id):
        """Submit a startup request for a server specified by id"""
        req = {'start': {}}
        self.servers_post(server_id, 'action', json_data=req, success=202)

    def shutdown_server(self, server_id):
        """Submit a shutdown request for a server specified by id"""
        req = {'shutdown': {}}
        self.servers_post(server_id, 'action', json_data=req, success=202)
    
    def get_server_console(self, server_id):
        """Get a VNC connection to the console of a server specified by id"""
        req = {'console': {'type': 'vnc'}}
        r = self.servers_post(server_id, 'action', json_data=req, success=200)
        return r.json['console']
    
    def set_firewall_profile(self, server_id, profile):
        """Set the firewall profile for the public interface of a server
           The server is specified by id, the profile argument
           is one of (ENABLED, DISABLED, PROTECTED).
        """
        req = {'firewallProfile': {'profile': profile}}
        self.servers_post(server_id, 'action', json_data=req, success=202)
    
    def list_server_nics(self, server_id):
        r = self.servers_get(server_id, 'ips')
        return r.json['addresses']['values']

    def get_server_stats(self, server_id):
        r = self.servers_get(server_id, 'stats')
        return r.json['stats']
    
    def list_networks(self, detail=False):
        detail = 'detail' if detail else ''
        r = self.networks_get(command=detail)
        return r.json['networks']['values']

    def create_network(self, name, cidr=False, gateway=False, type=False, dhcp=False):
        """@params cidr, geteway, type and dhcp should be strings
        """
        print('cidr[%s], type[%s]'%(cidr, type))
        net = dict(name=name)
        if cidr:
            net['cidr']=cidr
        if gateway:
            net['gateway']=gateway
        if type:
            net['type']=type
        if dhcp:
            net['dhcp']=dhcp
        req = dict(network=net)
        r = self.networks_post(json_data=req, success=202)
        return r.json['network']

    def get_network_details(self, network_id):
        r = self.networks_get(network_id=network_id)
        return r.json['network']

    def update_network_name(self, network_id, new_name):
        req = {'network': {'name': new_name}}
        self.networks_put(network_id=network_id, json_data=req)

    def delete_network(self, network_id):
        self.networks_delete(network_id)

    def connect_server(self, server_id, network_id):
        req = {'add': {'serverRef': server_id}}
        self.networks_post(network_id, 'action', json_data=req)

    def disconnect_server(self, server_id, nic_id):
        server_nets = self.list_server_nics(server_id)
        nets = [(net['id'],net['network_id'])  for net in server_nets if nic_id == net['id']]
        if len(nets) == 0:
            return
        for (nic_id, network_id) in nets:
            req={'remove':{'attachment':unicode(nic_id)}}
            self.networks_post(network_id, 'action', json_data=req)
