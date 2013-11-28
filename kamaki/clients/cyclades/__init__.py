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
                {"network": <network_uuid>},
                {"network": <network_uuid>, "fixed_ip": address},
                {"port": <port_id>}, ...]

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
            metadata=metadata, personality=personality)

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

    def get_firewall_profile(self, server_id):
        """
        :param server_id: integer (str or int)

        :returns: (str) ENABLED | DISABLED | PROTECTED

        :raises ClientError: 520 No Firewall Profile
        """
        r = self.get_server_details(server_id)
        try:
            return r['attachments'][0]['firewallProfile']
        except KeyError:
            raise ClientError(
                'No Firewall Profile',
                details='Server %s is missing a firewall profile' % server_id)

    def set_firewall_profile(self, server_id, profile):
        """Set the firewall profile for the public interface of a server

        :param server_id: integer (str or int)

        :param profile: (str) ENABLED | DISABLED | PROTECTED

        :returns: (dict) response headers
        """
        req = {'firewallProfile': {'profile': profile}}
        r = self.servers_action_post(server_id, json_data=req, success=202)
        return r.headers

    def list_server_nics(self, server_id):
        """
        :param server_id: integer (str or int)

        :returns: (dict) network interface connections
        """
        r = self.servers_ips_get(server_id)
        return r.json['attachments']

    def get_server_stats(self, server_id):
        """
        :param server_id: integer (str or int)

        :returns: (dict) auto-generated graphs of statistics (urls)
        """
        r = self.servers_stats_get(server_id)
        return r.json['stats']

    def list_networks(self, detail=False):
        """
        :param detail: (bool)

        :returns: (list) id,name if not detail else full info per network
        """
        detail = 'detail' if detail else ''
        r = self.networks_get(command=detail)
        return r.json['networks']

    def list_network_nics(self, network_id):
        """
        :param network_id: integer (str or int)

        :returns: (list)
        """
        r = self.networks_get(network_id=network_id)
        return r.json['network']['attachments']

    def create_network(
            self, name,
            cidr=None, gateway=None, type=None, dhcp=False):
        """
        :param name: (str)

        :param cidr: (str)

        :param geteway: (str)

        :param type: (str) if None, will use MAC_FILTERED as default
            Valid values: CUSTOM, IP_LESS_ROUTED, MAC_FILTERED, PHYSICAL_VLAN

        :param dhcp: (bool)

        :returns: (dict) network detailed info
        """
        net = dict(name=name)
        if cidr:
            net['cidr'] = cidr
        if gateway:
            net['gateway'] = gateway
        net['type'] = type or 'MAC_FILTERED'
        net['dhcp'] = True if dhcp else False
        req = dict(network=net)
        r = self.networks_post(json_data=req, success=202)
        return r.json['network']

    def get_network_details(self, network_id):
        """
        :param network_id: integer (str or int)

        :returns: (dict)
        """
        r = self.networks_get(network_id=network_id)
        return r.json['network']

    def update_network_name(self, network_id, new_name):
        """
        :param network_id: integer (str or int)

        :param new_name: (str)

        :returns: (dict) response headers
        """
        req = {'network': {'name': new_name}}
        r = self.networks_put(network_id=network_id, json_data=req)
        return r.headers

    def delete_network(self, network_id):
        """
        :param network_id: integer (str or int)

        :returns: (dict) response headers

        :raises ClientError: 421 Network in use
        """
        try:
            r = self.networks_delete(network_id)
            return r.headers
        except ClientError as err:
            if err.status == 421:
                err.details = [
                    'Network may be still connected to at least one server']
            raise

    def connect_server(self, server_id, network_id):
        """ Connect a server to a network

        :param server_id: integer (str or int)

        :param network_id: integer (str or int)

        :returns: (dict) response headers
        """
        req = {'add': {'serverRef': server_id}}
        r = self.networks_post(network_id, 'action', json_data=req)
        return r.headers

    def disconnect_server(self, server_id, nic_id):
        """
        :param server_id: integer (str or int)

        :param nic_id: (str)

        :returns: (int) the number of nics disconnected
        """
        vm_nets = self.list_server_nics(server_id)
        num_of_disconnections = 0
        for (nic_id, network_id) in [(
                net['id'],
                net['network_id']) for net in vm_nets if nic_id == net['id']]:
            req = {'remove': {'attachment': '%s' % nic_id}}
            self.networks_post(network_id, 'action', json_data=req)
            num_of_disconnections += 1
        return num_of_disconnections

    def disconnect_network_nics(self, netid):
        """
        :param netid: integer (str or int)
        """
        for nic in self.list_network_nics(netid):
            req = dict(remove=dict(attachment=nic))
            self.networks_post(netid, 'action', json_data=req)

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

    def wait_network(
            self, net_id,
            current_status='PENDING', delay=1, max_wait=100, wait_cb=None):
        """Wait for network while its status is current_status

        :param net_id: integer (str or int)

        :param current_status: (str) PENDING | ACTIVE | DELETED

        :param delay: time interval between retries

        :max_wait: (int) timeout in secconds

        :param wait_cb: if set a progressbar is used to show progress

        :returns: (str) the new mode if succesfull, (bool) False if timed out
        """

        def get_status(self, net_id):
            r = self.get_network_details(net_id)
            return r['status'], None

        return self._wait(
            net_id, current_status, get_status, delay, max_wait, wait_cb)

    def wait_firewall(
            self, server_id,
            current_status='DISABLED', delay=1, max_wait=100, wait_cb=None):
        """Wait while the public network firewall status is current_status

        :param server_id: integer (str or int)

        :param current_status: (str) DISABLED | ENABLED | PROTECTED

        :param delay: time interval between retries

        :max_wait: (int) timeout in secconds

        :param wait_cb: if set a progressbar is used to show progress

        :returns: (str) the new mode if succesfull, (bool) False if timed out
        """

        def get_status(self, server_id):
            return self.get_firewall_profile(server_id), None

        return self._wait(
            server_id, current_status, get_status, delay, max_wait, wait_cb)


class CycladesNetworkClient(NetworkClient, Waiter):
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

    def create_port(
            self, network_id, device_id,
            security_groups=None, name=None, fixed_ips=None):
        port = dict(network_id=network_id, device_id=device_id)
        if security_groups:
            port['security_groups'] = security_groups
        if name:
            port['name'] = name
        for fixed_ip in fixed_ips:
            diff = set(['subnet_id', 'ip_address']).difference(fixed_ip)
            if diff:
                raise ValueError(
                    'Invalid format for "fixed_ips", %s missing' % diff)
        if fixed_ips:
            port['fixed_ips'] = fixed_ips
        r = self.ports_post(json_data=dict(port=port), success=201)
        return r.json['port']

    def wait_network(
            self, net_id,
            current_status='PENDING', delay=1, max_wait=100, wait_cb=None):
        """Wait for network while its status is current_status

        :param net_id: integer (str or int)

        :param current_status: (str) PENDING | ACTIVE | DELETED

        :param delay: time interval between retries

        :max_wait: (int) timeout in secconds

        :param wait_cb: if set a progressbar is used to show progress

        :returns: (str) the new mode if succesfull, (bool) False if timed out
        """

        def get_status(self, net_id):
            r = self.get_network_details(net_id)
            return r['status'], None

        return self._wait(
            net_id, current_status, get_status, delay, max_wait, wait_cb)
