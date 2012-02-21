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

from .compute import ComputeClient


class CycladesClient(ComputeClient):
    """GRNet Cyclades API client"""
    
    def start_server(self, server_id):
        """Submit a startup request for a server specified by id"""
        
        path = '/servers/%s/action' % (server_id,)
        req = {'start': {}}
        self.post(path, json=req, success=202)
    
    def shutdown_server(self, server_id):
        """Submit a shutdown request for a server specified by id"""
        
        path = '/servers/%s/action' % (server_id,)
        req = {'shutdown': {}}
        self.post(path, json=req, success=202)
    
    def get_server_console(self, server_id):
        """Get a VNC connection to the console of a server specified by id"""
        
        path = '/servers/%s/action' % (server_id,)
        req = {'console': {'type': 'vnc'}}
        r = self.post(path, json=req, success=200)
        return r.json['console']
    
    def set_firewall_profile(self, server_id, profile):
        """Set the firewall profile for the public interface of a server

        The server is specified by id, the profile argument
        is one of (ENABLED, DISABLED, PROTECTED).
        """
        path = '/servers/%s/action' % (server_id,)
        req = {'firewallProfile': {'profile': profile}}
        self.post(path, json=req, success=202)
    
    def list_server_addresses(self, server_id, network=None):
        path = '/servers/%s/ips' % (server_id,)
        if network:
            path += '/%s' % network
        r = self.get(path, success=200)
        if network:
            return [r.json['network']]
        else:
            return r.json['addresses']['values']
    
    def get_server_stats(self, server_id):
        path = '/servers/%s/stats' % (server_id,)
        r = self.get(path, success=200)
        return r.json['stats']
    
    
    def list_networks(self, detail=False):
        path = '/networks/detail' if detail else '/networks'
        r = self.get(path, success=200)
        return r.json['networks']['values']

    def create_network(self, name):
        req = {'network': {'name': name}}
        r = self.post('/networks', json=req, success=202)
        return r.json['network']

    def get_network_details(self, network_id):
        path = '/networks/%s' % (network_id,)
        r = self.get(path, success=200)
        return r.json['network']

    def update_network_name(self, network_id, new_name):
        path = '/networks/%s' % (network_id,)
        req = {'network': {'name': new_name}}
        self.put(path, json=req, success=204)

    def delete_network(self, network_id):
        path = '/networks/%s' % (network_id,)
        self.delete(path, success=204)

    def connect_server(self, server_id, network_id):
        path = '/networks/%s/action' % (network_id,)
        req = {'add': {'serverRef': server_id}}
        self.post(path, json=req, success=202)

    def disconnect_server(self, server_id, network_id):
        path = '/networks/%s/action' % (network_id,)
        req = {'remove': {'serverRef': server_id}}
        self.post(path, json=req, success=202)
