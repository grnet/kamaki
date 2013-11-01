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

from kamaki.clients import ClientError, network


class NetworkRestClient(TestCase):

    """Set up a ComputesRest thorough test"""
    def setUp(self):
        self.url = 'http://network.example.com'
        self.token = 'n2tw0rk70k3n'
        self.client = network.NetworkRestClient(self.url, self.token)

    def tearDown(self):
        pass

    def _assert(self, method_call, path, set_param=None, params=(), **kwargs):
        """Assert the REST method call is called as expected"""
        x0 = - len(params)
        for i, (k, v, c) in enumerate(params):
            self.assertEqual(set_param.mock_calls[x0 + i], call(k, v, iff=c))

        self.assertEqual(method_call.mock_calls[-1], call(path, **kwargs))

    @patch('kamaki.clients.Client.get', return_value='ret val')
    def test_networks_get(self, get):
        for kwargs in (dict(), dict(k1='v1'), dict(k2='v2', k3='v3')):
            self.assertEqual(self.client.networks_get(**kwargs), 'ret val')
            self._assert(get, '/networks', **kwargs)

            netid = 'netid'
            self.assertEqual(
                self.client.networks_get(network_id=netid, **kwargs),
                'ret val')
            self._assert(get, '/networks/%s' % netid, **kwargs)

    @patch('kamaki.clients.Client.set_param')
    @patch('kamaki.clients.Client.post', return_value='ret val')
    def test_networks_post(self, post, set_param):
        for params, kwargs in product(
                (
                    (('shared', False, None), ),
                    (('shared', True, True), )),
                (dict(), dict(k1='v1'), dict(k2='v2', k3='v3'))):

            callargs = dict()
            for p in params:
                callargs[p[0]] = p[2]
            callargs.update(kwargs)

            self.assertEqual(self.client.networks_post(**callargs), 'ret val')
            self._assert(
                post, '/networks', set_param,
                params=params, data=None, **kwargs)

            json_data = dict(id='some id', other_param='other val')
            callargs['json_data'] = json_data
            self.assertEqual(self.client.networks_post(**callargs), 'ret val')
            self._assert(
                post, '/networks', set_param, params,
                data=dumps(json_data), **kwargs)

    @patch('kamaki.clients.Client.set_param')
    @patch('kamaki.clients.Client.put', return_value='ret val')
    def test_networks_put(self, put, set_param):
        netid = 'netid'
        for params, kwargs in product(
                [p for p in product(
                    (
                        ('admin_state_up', False, None),
                        ('admin_state_up', True, True)),
                    (('shared', False, None), ('shared', True, True)),
                )],
                (dict(), dict(k1='v1'), dict(k2='v2', k3='v3'))):

            callargs = dict()
            for p in params:
                callargs[p[0]] = p[2]
            callargs.update(kwargs)

            self.assertEqual(
                self.client.networks_put(netid, **callargs), 'ret val')
            self._assert(
                put, '/networks/%s' % netid, set_param, params,
                data=None, **kwargs)

            json_data = dict(id='some id', other_param='other val')
            callargs['json_data'] = json_data
            self.assertEqual(
                self.client.networks_put(netid, **callargs), 'ret val')
            self._assert(
                put, '/networks/%s' % netid, set_param, params,
                data=dumps(json_data), **kwargs)

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
            self.assertEqual(self.client.subnets_post(**kwargs), 'ret val')
            self._assert(post, '/subnets', **kwargs)

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


if __name__ == '__main__':
    from sys import argv
    from kamaki.clients.test import runTestCase
    not_found = True
    #if not argv[1:] or argv[1] == 'NetworkClient':
    #    not_found = False
    #    runTestCase(NetworkClient, 'Network Client', argv[2:])
    if not argv[1:] or argv[1] == 'NetworkRest':
        not_found = False
        runTestCase(NetworkRestClient, 'NetworkRest Client', argv[2:])
    if not_found:
        print('TestCase %s not found' % argv[1])
