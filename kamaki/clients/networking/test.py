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

from kamaki.clients import networking


class NetworkingRestClient(TestCase):

    """Set up a ComputesRest thorough test"""
    def setUp(self):
        self.url = 'http://networking.example.com'
        self.token = 'n2tw0rk70k3n'
        self.client = networking.NetworkingRestClient(self.url, self.token)

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
            self._assert(post, '/networks', data=dumps(json_data), **kwargs)

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
                put, '/networks/%s' % netid, data=dumps(json_data), **kwargs)

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
            self._assert(post, '/subnets', data=dumps(json_data), **kwargs)

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

    @patch('kamaki.clients.Client.set_param')
    @patch('kamaki.clients.Client.post', return_value='ret val')
    def test_ports_post(self, post, set_param):
        for params, kwargs in product(
                [p for p in product(
                    (
                        ('name', 'port name', 'port name'),
                        ('name', None, None)),
                    (
                        ('mac_address', 'max address', 'max address'),
                        ('mac_address', None, None)),
                    (
                        ('fixed_ips', 'fixed ip', 'fixed ip'),
                        ('fixed_ips', None, None)),
                    (
                        ('security_groups', 'sec groups', 'sec groups'),
                        ('security_groups', None, None))
                )],
                (dict(), dict(k1='v1'), dict(k2='v2', k3='v3'))):

            callargs = dict()
            for p in params:
                callargs[p[0]] = p[2]
            callargs.update(kwargs)

            self.assertEqual(self.client.ports_post(**callargs), 'ret val')
            self._assert(
                post, '/ports', set_param,
                params=params, data=None, **kwargs)

            json_data = dict(id='some id', other_param='other val')
            callargs['json_data'] = json_data
            self.assertEqual(self.client.ports_post(**callargs), 'ret val')
            self._assert(
                post, '/ports', set_param, params,
                data=dumps(json_data), **kwargs)

    @patch('kamaki.clients.Client.set_param')
    @patch('kamaki.clients.Client.put', return_value='ret val')
    def test_ports_put(self, put, set_param):
        port_id = 'portid'
        for params, kwargs in product(
                [p for p in product(
                    (
                        ('name', 'port name', 'port name'),
                        ('name', None, None)),
                    (
                        ('mac_address', 'max address', 'max address'),
                        ('mac_address', None, None)),
                    (
                        ('fixed_ips', 'fixed ip', 'fixed ip'),
                        ('fixed_ips', None, None)),
                    (
                        ('security_groups', 'sec groups', 'sec groups'),
                        ('security_groups', None, None))
                )],
                (dict(), dict(k1='v1'), dict(k2='v2', k3='v3'))):

            callargs = dict()
            for p in params:
                callargs[p[0]] = p[2]
            callargs.update(kwargs)

            self.assertEqual(
                self.client.ports_put(port_id, **callargs), 'ret val')
            self._assert(
                put, '/ports/%s' % port_id, set_param,
                params=params, data=None, **kwargs)

            json_data = dict(id='some id', other_param='other val')
            callargs['json_data'] = json_data
            self.assertEqual(
                self.client.ports_put(port_id, **callargs), 'ret val')
            self._assert(
                put, '/ports/%s' % port_id, set_param, params,
                data=dumps(json_data), **kwargs)


class FakeObject(object):

    json = None
    headers = None


class NetworkingClient(TestCase):

    """Set up a ComputesRest thorough test"""
    def setUp(self):
        self.url = 'http://network.example.com'
        self.token = 'n2tw0rk70k3n'
        self.client = networking.NetworkingClient(self.url, self.token)

    def tearDown(self):
        FakeObject.json, FakeObject.headers = None, None
        del self.client

    @patch(
        'kamaki.clients.networking.NetworkingClient.networks_get',
        return_value=FakeObject())
    def test_list_networks(self, networks_get):
        FakeObject.json = dict(networks='ret val')
        self.assertEqual(self.client.list_networks(), 'ret val')
        networks_get.assert_called_once_with(success=200)

    @patch(
        'kamaki.clients.networking.NetworkingClient.networks_post',
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
        'kamaki.clients.networking.NetworkingClient.networks_post',
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
        'kamaki.clients.networking.NetworkingClient.networks_get',
        return_value=FakeObject())
    def test_get_network_details(self, networks_get):
        netid, FakeObject.json = 'netid', dict(network='ret val')
        self.assertEqual(self.client.get_network_details(netid), 'ret val')
        networks_get.assert_called_once_with(netid, success=200)

    @patch(
        'kamaki.clients.networking.NetworkingClient.networks_put',
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
        'kamaki.clients.networking.NetworkingClient.networks_delete',
        return_value=FakeObject())
    def test_delete_network(self, networks_delete):
        netid, FakeObject.headers = 'netid', 'ret headers'
        self.assertEqual(self.client.delete_network(netid), 'ret headers')
        networks_delete.assert_called_once_with(netid, success=204)

    @patch(
        'kamaki.clients.networking.NetworkingClient.subnets_get',
        return_value=FakeObject())
    def test_list_subnets(self, subnets_get):
        FakeObject.json = dict(subnets='ret val')
        self.assertEqual(self.client.list_subnets(), 'ret val')
        subnets_get.assert_called_once_with(success=200)


if __name__ == '__main__':
    from sys import argv
    from kamaki.clients.test import runTestCase
    not_found = True
    if not argv[1:] or argv[1] == 'NetworkingClient':
        not_found = False
        runTestCase(NetworkingClient, 'Networking Client', argv[2:])
    if not argv[1:] or argv[1] == 'NetworkingRest':
        not_found = False
        runTestCase(NetworkingRestClient, 'NetworkingRest Client', argv[2:])
    if not_found:
        print('TestCase %s not found' % argv[1])
