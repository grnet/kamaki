# Copyright 2013-2015 GRNET S.A. All rights reserved.
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

from kamaki.clients import ClientError, wait, Waiter
from kamaki.clients.network.rest_api import NetworkRestClient


class NetworkClient(NetworkRestClient, Waiter):
    """OpenStack Network API 2.0 client"""

    def list_networks(self):
        r = self.networks_get(success=200)
        return r.json['networks']

    def create_network(self, name, admin_state_up=None, shared=None):
        req = dict(network=dict(
            name=name, admin_state_up=bool(admin_state_up)))
        if shared not in (None, ):
            req['network']['shared'] = bool(shared)
        r = self.networks_post(json_data=req, success=201)
        return r.json['network']

    def create_networks(self, networks):
        """Atomic operation for batch network creation (all or nothing)

        :param networks: (list) [
            {name: ..(str).., admin_state_up: ..(bool).., shared: ..(bool)..},
            {name: ..(str).., admin_state_up: ..(bool).., shared: ..(bool)..}]
            name is mandatory, the rest is optional
            e.g., create_networks([
            {name: 'net1', admin_state_up: True},
            {name: 'net2'}])
        :returns: (list of dicts) created networks details
        :raises ValueError: if networks is misformated
        :raises ClientError: if the request failed or didn't return 201
        """
        try:
            msg = 'The networks parameter must be list or tuple'
            assert (
                isinstance(networks, list) or isinstance(networks, tuple)), msg
            for network in networks:
                msg = 'Network specification %s is not a dict' % network
                assert isinstance(network, dict), msg
                err = set(network).difference(
                    ('name', 'admin_state_up', 'shared'))
                if err:
                    raise ValueError(
                        'Invalid key(s): %s in network specification %s' % (
                            err, network))
                msg = 'Name is missing in network specification: %s' % network
                assert network.get('name', None), msg
                network.setdefault('admin_state_up', False)
        except AssertionError as ae:
            raise ValueError('%s' % ae)

        req = dict(networks=list(networks))
        r = self.networks_post(json_data=req, success=201)
        return r.json['networks']

    def get_network_details(self, network_id):
        r = self.networks_get(network_id, success=200)
        return r.json['network']

    def update_network(
            self, network_id, name=None, admin_state_up=None, shared=None):
        network = dict()
        if name:
            network['name'] = name
        if admin_state_up not in (None, ):
            network['admin_state_up'] = admin_state_up
        if shared not in (None, ):
            network['shared'] = shared
        network = dict(network=network)
        r = self.networks_put(network_id, json_data=network, success=200)
        return r.json['network']

    def delete_network(self, network_id):
        r = self.networks_delete(network_id, success=204)
        return r.headers

    def list_subnets(self):
        r = self.subnets_get(success=200)
        return r.json['subnets']

    def create_subnet(
            self, network_id, cidr,
            name=None, allocation_pools=None, gateway_ip=None, subnet_id=None,
            ipv6=None, enable_dhcp=None):
        """
        :param network_id: (str)
        :param cidr: (str)

        :param name: (str) The subnet name
        :param allocation_pools: (list of dicts) start/end addresses of
            allocation pools: [{'start': ..., 'end': ...}, ...]
        :param gateway_ip: (str) Special cases:
            None: server applies the default policy
            empty iterable: no gateway IP on this subnet
        :param ipv6: (bool) ip_version == 6 if true else 4 (default)
        :param enable_dhcp: (bool)
        """
        subnet = dict(
            network_id=network_id, cidr=cidr, ip_version=6 if ipv6 else 4)
        if name:
            subnet['name'] = name
        if allocation_pools:
            subnet['allocation_pools'] = allocation_pools
        if gateway_ip is not None:
            subnet['gateway_ip'] = gateway_ip or None
        if subnet_id:
            subnet['id'] = subnet_id
        if enable_dhcp not in (None, ):
            subnet['enable_dhcp'] = bool(enable_dhcp)
        r = self.subnets_post(json_data=dict(subnet=subnet), success=201)
        return r.json['subnet']

    def create_subnets(self, subnets):
        """Atomic operation for batch subnet creation (all or nothing)

        :param subnets: (list of dicts) {key: ...} with all parameters in the
            method create_subnet, where method mandatory / optional paramteres
            respond to mandatory / optional paramters in subnets items
        :returns: (list of dicts) created subnetss details
        :raises ValueError: if subnets parameter is incorrectly formated
        :raises ClientError: if the request failed or didn't return 201
        """
        try:
            msg = 'The subnets parameter must be list or tuple'
            assert (
                isinstance(subnets, list) or isinstance(subnets, tuple)), msg
            for subnet in subnets:
                msg = 'Subnet specification %s is not a dict' % subnet
                assert isinstance(subnet, dict), msg
                err = set(subnet).difference((
                    'network_id', 'cidr', 'name', 'allocation_pools',
                    'gateway_ip', 'subnet_id', 'ipv6', 'enable_dhcp'))
                if err:
                    raise ValueError(
                        'Invalid key(s): %s in subnet specification %s' % (
                            err, subnet))
                msg = 'network_id is missing in subnet spec: %s' % subnet
                assert subnet.get('network_id', None), msg
                msg = 'cidr is missing in subnet spec: %s' % subnet
                assert subnet.get('cidr', None), msg
                subnet['ip_version'] = 6 if subnet.pop('ipv6', None) else 4
                if 'subnet_id' in subnet:
                    subnet['id'] = subnet.pop('subnet_id')
        except AssertionError as ae:
            raise ValueError('%s' % ae)

        r = self.subnets_post(
            json_data=dict(subnets=list(subnets)), success=201)
        return r.json['subnets']

    def get_subnet_details(self, subnet_id):
        r = self.subnets_get(subnet_id, success=200)
        return r.json

    def update_subnet(
            self, subnet_id,
            name=None, allocation_pools=None, gateway_ip=None, ipv6=None,
            enable_dhcp=None):
        """
        :param subnet_id: (str)

        :param name: (str) The subnet name
        :param allocation_pools: (list of dicts) start/end addresses of
            allocation pools: [{'start': ..., 'end': ...}, ...]
        :param gateway_ip: (str)
        :param ipv6: (bool) ip_version == 6 if true, 4 if false, used as filter
        :param enable_dhcp: (bool)
        """
        subnet = dict()
        if name not in (None, ):
            subnet['name'] = name
        if allocation_pools not in (None, ):
            subnet['allocation_pools'] = allocation_pools
        if gateway_ip not in (None, ):
            subnet['gateway_ip'] = gateway_ip
        if ipv6 not in (None, ):
            subnet['ip_version'] = 6 if ipv6 else 4
        if enable_dhcp not in (None, ):
            subnet['enable_dhcp'] = enable_dhcp
        r = self.subnets_put(
            subnet_id, json=dict(subnet=subnet), success=200)
        return r.json['subnet']

    def delete_subnet(self, subnet_id):
        r = self.subnets_delete(subnet_id, success=204)
        return r.headers

    def list_ports(self):
        r = self.ports_get(success=200)
        return r.json['ports']

    def create_port(
            self, network_id,
            name=None, status=None, admin_state_up=None, mac_address=None,
            fixed_ips=None, security_groups=None):
        """
        :param network_id: (str)

        :param name: (str)
        :param status: (str)
        :param admin_state_up: (bool) Router administrative status (UP / DOWN)
        :param mac_address: (str)
        :param fixed_ips: (str)
        :param security_groups: (list)
        """
        port = dict(network_id=network_id)
        if name:
            port['name'] = name
        if status:
            port['status'] = status
        if admin_state_up not in (None, ):
            port['admin_state_up'] = bool(admin_state_up)
        if mac_address:
            port['mac_address'] = mac_address
        if fixed_ips:
            port['fixed_ips'] = fixed_ips
        if security_groups:
            port['security_groups'] = security_groups
        r = self.ports_post(json_data=dict(port=port), success=201)
        return r.json['port']

    def create_ports(self, ports):
        """Atomic operation for batch port creation (all or nothing)

        :param ports: (list of dicts) {key: ...} with all parameters in the
            method create_port, where method mandatory / optional paramteres
            respond to mandatory / optional paramters in ports items
        :returns: (list of dicts) created portss details
        :raises ValueError: if ports parameter is incorrectly formated
        :raises ClientError: if the request failed or didn't return 201
        """
        try:
            msg = 'The ports parameter must be list or tuple'
            assert (
                isinstance(ports, list) or isinstance(ports, tuple)), msg
            for port in ports:
                msg = 'Subnet specification %s is not a dict' % port
                assert isinstance(port, dict), msg
                err = set(port).difference((
                    'network_id', 'status', 'name', 'admin_state_up',
                    'mac_address', 'fixed_ips', 'security_groups'))
                if err:
                    raise ValueError(
                        'Invalid key(s): %s in port specification %s' % (
                            err, port))
                msg = 'network_id is missing in port spec: %s' % port
                assert port.get('network_id', None), msg
        except AssertionError as ae:
            raise ValueError('%s' % ae)
        r = self.ports_post(json_data=dict(ports=list(ports)), success=201)
        return r.json['ports']

    def get_port_details(self, port_id):
        r = self.ports_get(port_id, success=200)
        return r.json['port']

    def delete_port(self, port_id):
        r = self.ports_delete(port_id, success=204)
        return r.headers

    def update_port(
            self, port_id, network_id,
            name=None, status=None, admin_state_up=None, mac_address=None,
            fixed_ips=None, security_groups=None):
        """
        :param network_id: (str)

        :param name: (str)
        :param status: (str)
        :param admin_state_up: (bool) Router administrative status (UP / DOWN)
        :param mac_address: (str)
        :param fixed_ips: (str)
        :param security_groups: (list)
        """
        port = dict(network_id=network_id)
        if name:
            port['name'] = name
        if status:
            port['status'] = status
        if admin_state_up not in (None, ):
            port['admin_state_up'] = bool(admin_state_up)
        if mac_address:
            port['mac_address'] = mac_address
        if fixed_ips:
            port['fixed_ips'] = fixed_ips
        if security_groups:
            port['security_groups'] = security_groups
        r = self.ports_put(port_id, json_data=dict(port=port), success=200)
        return r.json['port']

    def list_floatingips(self):
        r = self.floatingips_get(success=200)
        return r.json['floatingips']

    def get_floatingip_details(self, floatingip_id):
        r = self.floatingips_get(floatingip_id, success=200)
        return r.json['floatingip']

    def create_floatingip(
            self, floating_network_id,
            floating_ip_address='', port_id='', fixed_ip_address=''):
        floatingip = dict(floating_network_id=floating_network_id)
        if floating_ip_address:
            floatingip['floating_ip_address'] = floating_ip_address
        if port_id:
            floatingip['port_id'] = port_id
        if fixed_ip_address:
            floatingip['fixed_ip_address'] = fixed_ip_address
        r = self.floatingips_post(
            json_data=dict(floatingip=floatingip), success=200)
        return r.json['floatingip']

    def update_floatingip(
            self, floatingip_id,
            floating_ip_address='', port_id='', fixed_ip_address=''):
        """To nullify something optional, use None"""
        floatingip = dict()
        if floating_ip_address != '':
            floatingip['floating_ip_address'] = floating_ip_address
        if port_id != '':
            floatingip['port_id'] = port_id
        if fixed_ip_address != '':
            floatingip['fixed_ip_address'] = fixed_ip_address
        r = self.floatingips_put(
            floatingip_id, json_data=dict(floatingip=floatingip), success=200)
        return r.json['floatingip']

    def delete_floatingip(self, floatingip_id):
        r = self.floatingips_delete(floatingip_id, success=204)
        return r.headers

    def get_port_status(self, port_id):
        """Deprecated, will be removed in version 0.15"""
        r = self.get_port_details(port_id)
        return r['status'], None

    #  Wait methods

    def wait_port_while(
            self, port_id,
            current_status='BUILD', delay=1, max_wait=100, wait_cb=None):
        """Wait for port while in current_status"""
        return wait(
            self.get_port_details, (port_id, ),
            lambda i: i['status'] != current_status,
            delay, max_wait, wait_cb)

    def wait_port_until(
            self, port_id,
            target_status='BUILD', delay=1, max_wait=100, wait_cb=None):
        """Wait for port while in current_status"""
        return wait(
            self.get_port_details, (port_id, ),
            lambda i: i['status'] == target_status,
            delay, max_wait, wait_cb)

    # Backwards compatibility - deprecated, will be replaced in version 0.15
    wait_port = wait_port_while
