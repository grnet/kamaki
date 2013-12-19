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

from kamaki.clients.cyclades.rest_api import CycladesRestClient
from kamaki.clients.network import NetworkClient
from kamaki.clients.utils import path4url
from kamaki.clients import ClientError, Waiter


class CycladesClient(CycladesRestClient, Waiter):
    """Synnefo Cyclades Compute API client"""

    def create_server(
            self, name, flavor_id, image_id,
            metadata=None, personality=None, networks=None):
        """Submit request to create a new server

        :param name: (str)

        :param flavor_id: integer id denoting a preset hardware configuration

        :param image_id: (str) id denoting the OS image to run on virt. server

        :param metadata: (dict) vm metadata updated by os/users image metadata

        :param personality: a list of (file path, file contents) tuples,
            describing files to be injected into virtual server upon creation

        :param networks: (list of dicts) Networks to connect to, list this:
            "networks": [
            {"uuid": <network_uuid>},
            {"uuid": <network_uuid>, "fixed_ip": address},
            {"port": <port_id>}, ...]
            ATTENTION: Empty list is different to None. None means ' do not
            mention it', empty list means 'automatically get an ip'

        :returns: a dict with the new virtual server details

        :raises ClientError: wraps request errors
        """
        image = self.get_image_details(image_id)
        metadata = metadata or dict()
        for key in ('os', 'users'):
            try:
                metadata[key] = image['metadata'][key]
            except KeyError:
                pass

        return super(CycladesClient, self).create_server(
            name, flavor_id, image_id,
            metadata=metadata, personality=personality, networks=networks)

    def start_server(self, server_id):
        """Submit a startup request

        :param server_id: integer (str or int)

        :returns: (dict) response headers
        """
        req = {'start': {}}
        r = self.servers_action_post(server_id, json_data=req, success=202)
        return r.headers

    def shutdown_server(self, server_id):
        """Submit a shutdown request

        :param server_id: integer (str or int)

        :returns: (dict) response headers
        """
        req = {'shutdown': {}}
        r = self.servers_action_post(server_id, json_data=req, success=202)
        return r.headers

    def get_server_console(self, server_id):
        """
        :param server_id: integer (str or int)

        :returns: (dict) info to set a VNC connection to virtual server
        """
        req = {'console': {'type': 'vnc'}}
        r = self.servers_action_post(server_id, json_data=req, success=200)
        return r.json['console']

    def get_server_stats(self, server_id):
        """
        :param server_id: integer (str or int)

        :returns: (dict) auto-generated graphs of statistics (urls)
        """
        r = self.servers_stats_get(server_id)
        return r.json['stats']

    def get_server_diagnostics(self, server_id):
        """
        :param server_id: integer (str or int)

        :returns: (list)
        """
        r = self.servers_diagnostics_get(server_id)
        return r.json

    def wait_server(
            self, server_id,
            current_status='BUILD',
            delay=1, max_wait=100, wait_cb=None):
        """Wait for server while its status is current_status

        :param server_id: integer (str or int)

        :param current_status: (str) BUILD|ACTIVE|STOPPED|DELETED|REBOOT

        :param delay: time interval between retries

        :max_wait: (int) timeout in secconds

        :param wait_cb: if set a progressbar is used to show progress

        :returns: (str) the new mode if succesfull, (bool) False if timed out
        """

        def get_status(self, server_id):
            r = self.get_server_details(server_id)
            return r['status'], (r.get('progress', None) if (
                            current_status in ('BUILD', )) else None)

        return self._wait(
            server_id, current_status, get_status, delay, max_wait, wait_cb)


class CycladesNetworkClient(NetworkClient):
    """Cyclades Network API extentions"""

    network_types = (
        'CUSTOM', 'MAC_FILTERED', 'IP_LESS_ROUTED', 'PHYSICAL_VLAN')

    def list_networks(self, detail=None):
        path = path4url('networks', 'detail' if detail else '')
        r = self.get(path, success=200)
        return r.json['networks']

    def create_network(self, type, name=None, shared=None):
        req = dict(network=dict(type=type, admin_state_up=True))
        if name:
            req['network']['name'] = name
        if shared not in (None, ):
            req['network']['shared'] = bool(shared)
        r = self.networks_post(json_data=req, success=201)
        return r.json['network']

    def list_ports(self, detail=None):
        path = path4url('ports', 'detail' if detail else '')
        r = self.get(path, success=200)
        return r.json['ports']

    def create_port(
            self, network_id,
            device_id=None, security_groups=None, name=None, fixed_ips=None):
        """
        :param fixed_ips: (list of dicts) [{"ip_address": IPv4}, ...]
        """
        port = dict(network_id=network_id)
        if device_id:
            port['device_id'] = device_id
        if security_groups:
            port['security_groups'] = security_groups
        if name:
            port['name'] = name
        if fixed_ips:
            for fixed_ip in fixed_ips or []:
                if not 'ip_address' in fixed_ip:
                    raise ValueError('Invalid fixed_ip [%s]' % fixed_ip)
            port['fixed_ips'] = fixed_ips
        r = self.ports_post(json_data=dict(port=port), success=201)
        return r.json['port']

    def create_floatingip(self, floating_network_id, floating_ip_address=''):
        return super(CycladesNetworkClient, self).create_floatingip(
            floating_network_id, floating_ip_address=floating_ip_address)

    def update_floatingip(self, floating_network_id, floating_ip_address=''):
        """To nullify something optional, use None"""
        return super(CycladesNetworkClient, self).update_floatingip(
            floating_network_id, floating_ip_address=floating_ip_address)
