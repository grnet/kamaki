# Copyright 2013 GRNET S.A. All rights reserved.
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

from mock import patch, call
from unittest import TestCase
from itertools import product
from json import dumps

from kamaki.clients import network


class NetworkRestClient(TestCase):

    """Set up a ComputesRest thorough test"""
    def setUp(self):
        self.url = 'http://network.example.com'
        self.token = 'n2tw0rk70k3n'
        self.client = network.NetworkRestClient(self.url, self.token)

    def tearDown(self):
        del self.client

    def _assert(self, method_call, path, set_param=None, params=(), **kwargs):
        """Assert the REST method call is called as expected"""
        x0 = - len(params)
        for i, (k, v, c) in enumerate(params):
            self.assertEqual(set_param.mock_calls[x0 + i], call(k, v, iff=c))

        self.assertEqual(method_call.mock_calls[-1], call(path, **kwargs))

    @patch('kamaki.clients.Client.get', return_value='ret val')
    def test_networks_get(self, get):
        netid = 'netid'
        for kwargs in (dict(), dict(k1='v1'), dict(k2='v2', k3='v3')):
            self.assertEqual(self.client.networks_get(**kwargs), 'ret val')
            self._assert(get, '/networks', **kwargs)
            self.assertEqual(
                self.client.networks_get(network_id=netid, **kwargs),
                'ret val')
            self._assert(get, '/networks/%s' % netid, **kwargs)

    @patch('kamaki.clients.Client.post', return_value='ret val')
    def test_networks_post(self, post):
        for kwargs in (
                dict(json_data=dict(k1='v1')),
                dict(json_data=dict(k2='v2'), k3='v3')):
            self.assertEqual(self.client.networks_post(**kwargs), 'ret val')
            json_data = kwargs.pop('json_data')
            self._assert(post, '/networks', json=json_data, **kwargs)

    @patch('kamaki.clients.Client.put', return_value='ret val')
    def test_networks_put(self, put):
        netid = 'netid'
        for kwargs in (
                dict(json_data=dict(k1='v1')),
                dict(json_data=dict(k2='v2'), k3='v3')):
            self.assertEqual(
                self.client.networks_put(netid, **kwargs), 'ret val')
            json_data = kwargs.pop('json_data')
            self._assert(
                put, '/networks/%s' % netid, json=json_data, **kwargs)

    @patch('kamaki.clients.Client.delete', return_value='ret val')
    def test_networks_delete(self, delete):
        netid = 'netid'
        for kwargs in (dict(), dict(k1='v1'), dict(k2='v2', k3='v3')):
            self.assertEqual(
                self.client.networks_delete(netid, **kwargs), 'ret val')
            self._assert(delete, '/networks/%s' % netid, **kwargs)

    @patch('kamaki.clients.Client.get', return_value='ret val')
    def test_subnets_get(self, get):
        for kwargs in (dict(), dict(k1='v1'), dict(k2='v2', k3='v3')):
            self.assertEqual(self.client.subnets_get(**kwargs), 'ret val')
            self._assert(get, '/subnets', **kwargs)

            subnet_id = 'subnet id'
            self.assertEqual(
                self.client.subnets_get(subnet_id=subnet_id, **kwargs),
                'ret val')
            self._assert(get, '/subnets/%s' % subnet_id, **kwargs)

    @patch('kamaki.clients.Client.post', return_value='ret val')
    def test_subnets_post(self, post):
        for kwargs in (dict(), dict(k1='v1'), dict(k2='v2', k3='v3')):
            json_data = dict(subnets='some data')
            self.assertEqual(self.client.subnets_post(
                json_data=json_data, **kwargs), 'ret val')
            self._assert(post, '/subnets', json=json_data, **kwargs)

    @patch('kamaki.clients.Client.put', return_value='ret val')
    def test_subnets_put(self, put):
        subnet_id = 'subid'
        for kwargs in (dict(), dict(k1='v1'), dict(k2='v2', k3='v3')):
            self.assertEqual(
                self.client.subnets_put(subnet_id, **kwargs), 'ret val')
            self._assert(put, '/subnets/%s' % subnet_id, **kwargs)

    @patch('kamaki.clients.Client.delete', return_value='ret val')
    def test_subnets_delete(self, delete):
        netid = 'netid'
        for kwargs in (dict(), dict(k1='v1'), dict(k2='v2', k3='v3')):
            self.assertEqual(
                self.client.subnets_delete(netid, **kwargs), 'ret val')
            self._assert(delete, '/subnets/%s' % netid, **kwargs)

    @patch('kamaki.clients.Client.get', return_value='ret val')
    def test_ports_get(self, get):
        for kwargs in (dict(), dict(k1='v1'), dict(k2='v2', k3='v3')):
            self.assertEqual(self.client.ports_get(**kwargs), 'ret val')
            self._assert(get, '/ports', **kwargs)

            port_id = 'port id'
            self.assertEqual(
                self.client.ports_get(port_id=port_id, **kwargs),
                'ret val')
            self._assert(get, '/ports/%s' % port_id, **kwargs)

    @patch('kamaki.clients.Client.post', return_value='ret val')
    def test_ports_post(self, post):
        for kwargs in (dict(), dict(k1='v1'), dict(k2='v2', k3='v3')):
            self.assertEqual(self.client.ports_post(**kwargs), 'ret val')
            self._assert(post, '/ports', json=None, **kwargs)

            json_data = dict(id='some id', other_param='other val')
            self.assertEqual(
                self.client.ports_post(json_data=json_data, **kwargs),
                'ret val')
            self._assert(post, '/ports', json=json_data, **kwargs)

    @patch('kamaki.clients.Client.put', return_value='ret val')
    def test_ports_put(self, put):
        port_id = 'portid'
        for kwargs in (dict(), dict(k1='v1'), dict(k2='v2', k3='v3')):
            self.assertEqual(
                self.client.ports_put(port_id, **kwargs), 'ret val')
            self._assert(put, '/ports/%s' % port_id, json=None, **kwargs)

            json_data = dict(id='some id', other_param='other val')
            self.assertEqual(
                self.client.ports_put(port_id, json_data=json_data, **kwargs),
                'ret val')
            self._assert(put, '/ports/%s' % port_id, json=json_data, **kwargs)

    @patch('kamaki.clients.Client.get', return_value='ret val')
    def test_floatingips_get(self, get):
        for kwargs in (dict(), dict(k1='v1'), dict(k2='v2', k3='v3')):
            self.assertEqual(self.client.floatingips_get(**kwargs), 'ret val')
            self._assert(get, '/floatingips', **kwargs)

            floatingip_id = 'port id'
            self.assertEqual(
                self.client.floatingips_get(
                    floatingip_id=floatingip_id, **kwargs),
                'ret val')
            self._assert(get, '/floatingips/%s' % floatingip_id, **kwargs)

    @patch('kamaki.clients.Client.post', return_value='ret val')
    def test_floatingips_post(self, post):
        for kwargs in (dict(), dict(k1='v1'), dict(k2='v2', k3='v3')):
            json_data = dict(id='some id', other_param='other val')
            self.assertEqual(
                self.client.floatingips_post(json_data=json_data, **kwargs),
                'ret val')
            self._assert(post, '/floatingips', json=json_data, **kwargs)

    @patch('kamaki.clients.Client.put', return_value='ret val')
    def test_floatingips_put(self, put):
        floatingip_id = 'portid'
        for kwargs in (dict(), dict(k1='v1'), dict(k2='v2', k3='v3')):
            json_data = dict(id='some id', other_param='other val')
            self.assertEqual(
                self.client.floatingips_put(
                    floatingip_id, json_data=json_data, **kwargs),
                'ret val')
            self._assert(
                put, '/floatingips/%s' % floatingip_id,
                json=json_data, **kwargs)


class FakeObject(object):

    json = None
    headers = None


class NetworkClient(TestCase):

    """Set up a ComputesRest thorough test"""
    def setUp(self):
        self.url = 'http://network.example.com'
        self.token = 'n2tw0rk70k3n'
        self.client = network.NetworkClient(self.url, self.token)

    def tearDown(self):
        FakeObject.json, FakeObject.headers = None, None
        del self.client

    @patch(
        'kamaki.clients.network.NetworkClient.networks_get',
        return_value=FakeObject())
    def test_list_networks(self, networks_get):
        FakeObject.json = dict(networks='ret val')
        self.assertEqual(self.client.list_networks(), 'ret val')
        networks_get.assert_called_once_with(success=200)

    @patch(
        'kamaki.clients.network.NetworkClient.networks_post',
        return_value=FakeObject())
    def test_create_network(self, networks_post):
        for admin_state_up, shared in product((None, True), (None, True)):
            FakeObject.json = dict(network='ret val')
            name = 'net name'
            self.assertEqual(
                self.client.create_network(
                    name, admin_state_up=admin_state_up, shared=shared),
                'ret val')
            req = dict(name=name, admin_state_up=bool(admin_state_up))
            if shared:
                req['shared'] = shared
            expargs = dict(json_data=dict(network=req), success=201)
            self.assertEqual(networks_post.mock_calls[-1], call(**expargs))

    @patch(
        'kamaki.clients.network.NetworkClient.networks_post',
        return_value=FakeObject())
    def test_create_networks(self, networks_post):
        for networks in (
                None, dict(name='name'), 'nets', [1, 2, 3], [{'k': 'v'}, ],
                [dict(admin_state_up=True, shared=True)],
                [dict(name='n1', invalid='mistake'), ],
                [dict(name='valid', shared=True), {'err': 'nop'}]):
            self.assertRaises(
                ValueError, self.client.create_networks, networks)

        FakeObject.json = dict(networks='ret val')
        for networks in (
                [
                    dict(name='net1'),
                    dict(name='net 2', admin_state_up=False, shared=True)],
                [
                    dict(name='net1', admin_state_up=True),
                    dict(name='net 2', shared=False),
                    dict(name='net-3')],
                (dict(name='n.e.t'), dict(name='net 2'))):
            self.assertEqual(self.client.create_networks(networks), 'ret val')

            networks = list(networks)
            expargs = dict(json_data=dict(networks=networks), success=201)
            self.assertEqual(networks_post.mock_calls[-1], call(**expargs))

    @patch(
        'kamaki.clients.network.NetworkClient.networks_get',
        return_value=FakeObject())
    def test_get_network_details(self, networks_get):
        netid, FakeObject.json = 'netid', dict(network='ret val')
        self.assertEqual(self.client.get_network_details(netid), 'ret val')
        networks_get.assert_called_once_with(netid, success=200)

    @patch(
        'kamaki.clients.network.NetworkClient.networks_put',
        return_value=FakeObject())
    def test_update_network(self, networks_put):
        netid, FakeObject.json = 'netid', dict(network='ret val')
        for name, admin_state_up, shared in product(
                ('net name', None), (True, None), (True, None)):
            kwargs = dict(
                name=name, admin_state_up=admin_state_up, shared=shared)
            self.assertEqual(
                self.client.update_network(netid, **kwargs), 'ret val')
            if name in (None, ):
                kwargs.pop('name')
            if admin_state_up in (None, ):
                kwargs.pop('admin_state_up')
            if shared in (None, ):
                kwargs.pop('shared')
            kwargs = dict(json_data=dict(network=kwargs), success=200)
            self.assertEqual(
                networks_put.mock_calls[-1], call(netid, **kwargs))

    @patch(
        'kamaki.clients.network.NetworkClient.networks_delete',
        return_value=FakeObject())
    def test_delete_network(self, networks_delete):
        netid, FakeObject.headers = 'netid', 'ret headers'
        self.assertEqual(self.client.delete_network(netid), 'ret headers')
        networks_delete.assert_called_once_with(netid, success=204)

    @patch(
        'kamaki.clients.network.NetworkClient.subnets_get',
        return_value=FakeObject())
    def test_list_subnets(self, subnets_get):
        FakeObject.json = dict(subnets='ret val')
        self.assertEqual(self.client.list_subnets(), 'ret val')
        subnets_get.assert_called_once_with(success=200)

    @patch(
        'kamaki.clients.network.NetworkClient.subnets_post',
        return_value=FakeObject())
    def test_create_subnet(self, subnets_post):
        for (
                name, allocation_pools, gateway_ip,
                subnet_id, ipv6, enable_dhcp) in product(
                    ('name', None), ('all pools', None), ('gip', None),
                    ('sid', None), (True, None), (True, None)):
            kwargs = dict(
                name=name, allocation_pools=allocation_pools,
                gateway_ip=gateway_ip, subnet_id=subnet_id,
                ipv6=ipv6, enable_dhcp=enable_dhcp)
            FakeObject.json, network_id, cidr = dict(subnet='rv'), 'name', 'cd'
            self.assertEqual(
                self.client.create_subnet(network_id, cidr, **kwargs), 'rv')
            req = dict(
                network_id=network_id, cidr=cidr,
                ip_version=6 if kwargs.pop('ipv6', None) else 4)
            for k, v in kwargs.items():
                if v:
                    req['id' if k == 'subnet_id' else k] = v
            expargs = dict(json_data=dict(subnet=req), success=201)
            self.assertEqual(subnets_post.mock_calls[-1], call(**expargs))

    @patch(
        'kamaki.clients.network.NetworkClient.subnets_post',
        return_value=FakeObject())
    def test_create_subnets(self, subnets_post):
        for subnets in (
                None, dict(network_id='name'), 'nets', [1, 2, 3], [{'k': 'v'}],
                [dict(ipv6=True, enable_dhcp=True)],
                [dict(network_id='n1', cidr='dr', invalid='mistake'), ],
                [dict(network_id='valid', cidr='valid'), {'err': 'nop'}]):
            self.assertRaises(
                ValueError, self.client.create_subnets, subnets)

        FakeObject.json = dict(subnets='ret val')
        for subnets in (
                [
                    dict(network_id='n1', cidr='c1'),
                    dict(network_id='n 2', cidr='c 2', name='name')],
                [
                    dict(network_id='n1', cidr='c 6', allocation_pools='a p'),
                    dict(network_id='n 2', cidr='c_4', gateway_ip='g ip'),
                    dict(network_id='n 2', cidr='c_4', subnet_id='s id'),
                    dict(network_id='n-4', cidr='c3', ipv6=True, name='w. 6'),
                    dict(network_id='n_5', cidr='c2', enable_dhcp=True)],
                (
                    dict(network_id='n.e.t', cidr='c-5'),
                    dict(network_id='net 2', cidr='c 2'))):
            self.assertEqual(self.client.create_subnets(subnets), 'ret val')

            for subnet in subnets:
                subnet['ip_version'] = 6 if subnet.pop('ipv6', None) else 4
                if 'subnet_id' in subnet:
                    subnet['id'] = subnet.pop('subnet_id')
            subnets = list(subnets)
            expargs = dict(json_data=dict(subnets=subnets), success=201)
            self.assertEqual(subnets_post.mock_calls[-1], call(**expargs))

    @patch(
        'kamaki.clients.network.NetworkClient.subnets_get',
        return_value=FakeObject())
    def test_get_subnet_details(self, subnets_get):
        subid, FakeObject.json = 'subid', 'ret val'
        self.assertEqual(self.client.get_subnet_details(subid), 'ret val')
        subnets_get.assert_called_once_with(subid, success=200)

    @patch(
        'kamaki.clients.network.NetworkClient.subnets_put',
        return_value=FakeObject())
    def test_update_subnet(self, subnets_put):
        for (
                name, allocation_pools, gateway_ip,
                ipv6, enable_dhcp) in product(
                    ('name', None), ('all pools', None), ('gip', None),
                    (True, False, None), (True, False, None)):
            kwargs = dict(
                name=name, allocation_pools=allocation_pools,
                gateway_ip=gateway_ip, ipv6=ipv6, enable_dhcp=enable_dhcp)
            FakeObject.json, subnet_id = dict(subnet='rv'), 'sid'
            self.assertEqual(
                self.client.update_subnet(subnet_id, **kwargs), 'rv')
            req = dict()
            for k, v in kwargs.items():
                if v not in (None, ):
                    if k in ('ipv6', ):
                        req['ip_version'] = 6 if v else 4
                    else:
                        req[k] = v
            expargs = dict(json=dict(subnet=req), success=200)
            self.assertEqual(
                subnets_put.mock_calls[-1], call(subnet_id, **expargs))

    @patch(
        'kamaki.clients.network.NetworkClient.subnets_delete',
        return_value=FakeObject())
    def test_delete_subnet(self, subnets_delete):
        netid, FakeObject.headers = 'netid', 'ret headers'
        self.assertEqual(self.client.delete_subnet(netid), 'ret headers')
        subnets_delete.assert_called_once_with(netid, success=204)

    @patch(
        'kamaki.clients.network.NetworkClient.ports_get',
        return_value=FakeObject())
    def test_list_ports(self, ports_get):
        FakeObject.json = dict(ports='ret val')
        self.assertEqual(self.client.list_ports(), 'ret val')
        ports_get.assert_called_once_with(success=200)

    @patch(
        'kamaki.clients.network.NetworkClient.ports_post',
        return_value=FakeObject())
    def test_create_port(self, ports_post):
        for (
                name, status, admin_state_up,
                mac_address, fixed_ips, security_groups
                ) in product(
                    ('name', None), ('status', None), (True, False, None),
                    ('maddr', None), ('some ips', None), ([1, 2, 3], None)):
            kwargs = dict(
                name=name, status=status, admin_state_up=admin_state_up,
                mac_address=mac_address, fixed_ips=fixed_ips,
                security_groups=security_groups)
            FakeObject.json, network_id = dict(port='ret val'), 'name'
            self.assertEqual(
                self.client.create_port(network_id, **kwargs), 'ret val')
            req = dict(network_id=network_id)
            for k, v in kwargs.items():
                if v not in (None, ):
                    req[k] = v
            expargs = dict(json_data=dict(port=req), success=201)
            self.assertEqual(ports_post.mock_calls[-1], call(**expargs))

    @patch(
        'kamaki.clients.network.NetworkClient.ports_post',
        return_value=FakeObject())
    def test_create_ports(self, ports_post):
        for ports in (
                None, dict(network_id='name'), 'nets', [1, 2, 3], [{'k': 'v'}],
                [dict(name=True, mac_address='mac')],
                [dict(network_id='n1', invalid='mistake'), ],
                [dict(network_id='valid', name='valid'), {'err': 'nop'}]):
            self.assertRaises(
                ValueError, self.client.create_ports, ports)

        FakeObject.json = dict(ports='ret val')
        for ports in (
                [dict(network_id='n1'), dict(network_id='n 2', name='name')],
                [
                    dict(network_id='n1', name='n 6', status='status'),
                    dict(network_id='n 2', admin_state_up=True, fixed_ips='f'),
                    dict(network_id='n 2', mac_address='mc', name='n.a.m.e.'),
                    dict(network_id='n-4', security_groups='s~G', name='w. 6'),
                    dict(network_id='n_5', admin_state_up=False, name='f a')],
                (
                    dict(network_id='n.e.t', name='c-5'),
                    dict(network_id='net 2', status='YEAH'))):
            self.assertEqual(self.client.create_ports(ports), 'ret val')
            expargs = dict(json_data=dict(ports=list(ports)), success=201)
            self.assertEqual(ports_post.mock_calls[-1], call(**expargs))

    @patch(
        'kamaki.clients.network.NetworkClient.ports_get',
        return_value=FakeObject())
    def test_get_port_details(self, ports_get):
        portid, FakeObject.json = 'portid', dict(port='ret val')
        self.assertEqual(self.client.get_port_details(portid), 'ret val')
        ports_get.assert_called_once_with(portid, success=200)

    @patch(
        'kamaki.clients.network.NetworkClient.ports_delete',
        return_value=FakeObject())
    def test_delete_port(self, ports_delete):
        portid, FakeObject.headers = 'portid', 'ret headers'
        self.assertEqual(self.client.delete_port(portid), 'ret headers')
        ports_delete.assert_called_once_with(portid, success=204)

    @patch(
        'kamaki.clients.network.NetworkClient.ports_put',
        return_value=FakeObject())
    def test_update_port(self, ports_put):
        for (
                name, status, admin_state_up, mac_address, fixed_ips,
                security_groups) in product(
                    ('name', None), ('st', None), (True, None), ('mc', None),
                    ('fps', None), ('sg', None)):
            FakeObject.json = dict(port='rv')
            port_id, network_id = 'pid', 'nid'
            kwargs = dict(
                network_id=network_id, name=name, status=status,
                admin_state_up=admin_state_up, mac_address=mac_address,
                fixed_ips=fixed_ips, security_groups=security_groups)
            self.assertEqual(
                self.client.update_port(port_id, **kwargs), 'rv')
            req = dict()
            for k, v in kwargs.items():
                if v:
                    req[k] = v
            expargs = dict(json_data=dict(port=req), success=200)
            self.assertEqual(
                ports_put.mock_calls[-1], call(port_id, **expargs))


if __name__ == '__main__':
    from sys import argv
    from kamaki.clients.test import runTestCase
    not_found = True
    if not argv[1:] or argv[1] == 'NetworkClient':
        not_found = False
        runTestCase(NetworkClient, 'Network Client', argv[2:])
    if not argv[1:] or argv[1] == 'NetworkRestClient':
        not_found = False
        runTestCase(NetworkRestClient, 'NetworkRest Client', argv[2:])
    if not_found:
        print('TestCase %s not found' % argv[1])
