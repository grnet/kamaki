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

from kamaki.clients import ClientError, cyclades

img_ref = "1m4g3-r3f3r3nc3"
vm_name = "my new VM"
fid = 42
vm_recv = dict(server=dict(
    status="BUILD",
    updated="2013-03-01T10:04:00.637152+00:00",
    hostId="",
    name=vm_name,
    imageRef=img_ref,
    created="2013-03-01T10:04:00.087324+00:00",
    flavorRef=fid,
    adminPass="n0n3sh@11p@55",
    suspended=False,
    progress=0,
    id=31173,
    metadata=dict(os="debian", users="root")))
vm_list = dict(servers=[
    dict(name='n1', id=1),
    dict(name='n2', id=2)])
net_send = dict(network=dict(dhcp=False, name='someNet'))
net_recv = dict(network=dict(
    status="PENDING",
    updated="2013-03-05T15:04:51.758780+00:00",
    name="someNet",
    created="2013-03-05T15:04:51.758728+00:00",
    cidr6=None,
    id="2130",
    gateway6=None,
    public=False,
    dhcp=False,
    cidr="192.168.1.0/24",
    type="MAC_FILTERED",
    gateway=None,
    attachments=[dict(name='att1'), dict(name='att2')]))
net_list = dict(networks=[
    dict(id=1, name='n1'),
    dict(id=2, name='n2'),
    dict(id=3, name='n3')])
firewalls = dict(attachments=[
    dict(firewallProfile='50m3_pr0f1L3', otherStuff='57uff')])


class FR(object):
    """FR stands for Fake Response"""
    json = vm_recv
    headers = {}
    content = json
    status = None
    status_code = 200

rest_pkg = 'kamaki.clients.cyclades.CycladesRestClient'
cyclades_pkg = 'kamaki.clients.cyclades.CycladesClient'


class CycladesRestClient(TestCase):

    """Set up a Cyclades thorough test"""
    def setUp(self):
        self.url = 'http://cyclades.example.com'
        self.token = 'cyc14d3s70k3n'
        self.client = cyclades.CycladesRestClient(self.url, self.token)

    def tearDown(self):
        FR.json = vm_recv

    @patch('%s.get' % rest_pkg, return_value=FR())
    def test_networks_get(self, get):
        for args in product(
                ('', 'net_id'),
                ('', 'cmd'),
                (200, 204),
                ({}, {'k': 'v'})):
            (srv_id, command, success, kwargs) = args
            self.client.networks_get(*args[:3], **kwargs)
            srv_str = '/%s' % srv_id if srv_id else ''
            cmd_str = '/%s' % command if command else ''
            self.assertEqual(get.mock_calls[-1], call(
                '/networks%s%s' % (srv_str, cmd_str),
                success=success,
                **kwargs))

    @patch('%s.delete' % rest_pkg, return_value=FR())
    def test_networks_delete(self, delete):
        for args in product(
                ('', 'net_id'),
                ('', 'cmd'),
                (202, 204),
                ({}, {'k': 'v'})):
            (srv_id, command, success, kwargs) = args
            self.client.networks_delete(*args[:3], **kwargs)
            srv_str = '/%s' % srv_id if srv_id else ''
            cmd_str = '/%s' % command if command else ''
            self.assertEqual(delete.mock_calls[-1], call(
                '/networks%s%s' % (srv_str, cmd_str),
                success=success,
                **kwargs))

    @patch('%s.set_header' % rest_pkg)
    @patch('%s.post' % rest_pkg, return_value=FR())
    def test_networks_post(self, post, SH):
        for args in product(
                ('', 'net_id'),
                ('', 'cmd'),
                (None, [dict(json="data"), dict(data="json")]),
                (202, 204),
                ({}, {'k': 'v'})):
            (srv_id, command, json_data, success, kwargs) = args
            self.client.networks_post(*args[:4], **kwargs)
            vm_str = '/%s' % srv_id if srv_id else ''
            cmd_str = '/%s' % command if command else ''
            if json_data:
                json_data = dumps(json_data)
                self.assertEqual(SH.mock_calls[-2:], [
                    call('Content-Type', 'application/json'),
                    call('Content-Length', len(json_data))])
            self.assertEqual(post.mock_calls[-1], call(
                '/networks%s%s' % (vm_str, cmd_str),
                data=json_data, success=success,
                **kwargs))

    @patch('%s.set_header' % rest_pkg)
    @patch('%s.put' % rest_pkg, return_value=FR())
    def test_networks_put(self, put, SH):
        for args in product(
                ('', 'net_id'),
                ('', 'cmd'),
                (None, [dict(json="data"), dict(data="json")]),
                (202, 204),
                ({}, {'k': 'v'})):
            (srv_id, command, json_data, success, kwargs) = args
            self.client.networks_put(*args[:4], **kwargs)
            vm_str = '/%s' % srv_id if srv_id else ''
            cmd_str = '/%s' % command if command else ''
            if json_data:
                json_data = dumps(json_data)
                self.assertEqual(SH.mock_calls[-2:], [
                    call('Content-Type', 'application/json'),
                    call('Content-Length', len(json_data))])
            self.assertEqual(put.mock_calls[-1], call(
                '/networks%s%s' % (vm_str, cmd_str),
                data=json_data, success=success,
                **kwargs))

    @patch('%s.get' % rest_pkg, return_value=FR())
    def test_floating_ip_pools_get(self, get):
        for args in product(
                (200, 204),
                ({}, {'k': 'v'})):
            success, kwargs = args
            r = self.client.floating_ip_pools_get(success, **kwargs)
            self.assertTrue(isinstance(r, FR))
            self.assertEqual(get.mock_calls[-1], call(
                '/os-floating-ip-pools', success=success, **kwargs))

    @patch('%s.get' % rest_pkg, return_value=FR())
    def test_floating_ips_get(self, get):
        for args in product(
                ('fip', ''),
                (200, 204),
                ({}, {'k': 'v'})):
            fip, success, kwargs = args
            r = self.client.floating_ips_get(fip, success, **kwargs)
            self.assertTrue(isinstance(r, FR))
            expected = '' if not fip else '/%s' % fip
            self.assertEqual(get.mock_calls[-1], call(
                '/os-floating-ips%s' % expected, success=success, **kwargs))

    @patch('%s.set_header' % rest_pkg)
    @patch('%s.post' % rest_pkg, return_value=FR())
    def test_floating_ips_post(self, post, SH):
        for args in product(
                (None, [dict(json="data"), dict(data="json")]),
                ('fip', ''),
                (202, 204),
                ({}, {'k': 'v'})):
            json_data, fip, success, kwargs = args
            self.client.floating_ips_post(*args[:3], **kwargs)
            if json_data:
                json_data = dumps(json_data)
                self.assertEqual(SH.mock_calls[-2:], [
                    call('Content-Type', 'application/json'),
                    call('Content-Length', len(json_data))])
            expected = '' if not fip else '/%s' % fip
            self.assertEqual(post.mock_calls[-1], call(
                '/os-floating-ips%s' % expected,
                data=json_data, success=success,
                **kwargs))

    @patch('%s.delete' % rest_pkg, return_value=FR())
    def test_floating_ips_delete(self, delete):
        for args in product(
                ('fip1', 'fip2'),
                (200, 204),
                ({}, {'k': 'v'})):
            fip, success, kwargs = args
            r = self.client.floating_ips_delete(fip, success, **kwargs)
            self.assertTrue(isinstance(r, FR))
            self.assertEqual(delete.mock_calls[-1], call(
                '/os-floating-ips/%s' % fip, success=success, **kwargs))


class CycladesClient(TestCase):

    def assert_dicts_are_equal(self, d1, d2):
        for k, v in d1.items():
            self.assertTrue(k in d2)
            if isinstance(v, dict):
                self.assert_dicts_are_equal(v, d2[k])
            else:
                self.assertEqual(unicode(v), unicode(d2[k]))

    """Set up a Cyclades thorough test"""
    def setUp(self):
        self.url = 'http://cyclades.example.com'
        self.token = 'cyc14d3s70k3n'
        self.client = cyclades.CycladesClient(self.url, self.token)

    def tearDown(self):
        FR.status_code = 200
        FR.json = vm_recv

    @patch('%s.servers_action_post' % cyclades_pkg, return_value=FR())
    def test_shutdown_server(self, SP):
        vm_id = vm_recv['server']['id']
        self.client.shutdown_server(vm_id)
        SP.assert_called_once_with(
            vm_id, json_data=dict(shutdown=dict()), success=202)

    @patch('%s.servers_action_post' % cyclades_pkg, return_value=FR())
    def test_start_server(self, SP):
        vm_id = vm_recv['server']['id']
        self.client.start_server(vm_id)
        SP.assert_called_once_with(
            vm_id, json_data=dict(start=dict()), success=202)

    @patch('%s.servers_action_post' % cyclades_pkg, return_value=FR())
    def test_get_server_console(self, SP):
        cnsl = dict(console=dict(info1='i1', info2='i2', info3='i3'))
        FR.json = cnsl
        vm_id = vm_recv['server']['id']
        r = self.client.get_server_console(vm_id)
        SP.assert_called_once_with(
            vm_id, json_data=dict(console=dict(type='vnc')), success=200)
        self.assert_dicts_are_equal(r, cnsl['console'])

    def test_get_firewall_profile(self):
        vm_id = vm_recv['server']['id']
        v = firewalls['attachments'][0]['firewallProfile']
        with patch.object(
                cyclades.CycladesClient, 'get_server_details',
                return_value=firewalls) as GSD:
            r = self.client.get_firewall_profile(vm_id)
            GSD.assert_called_once_with(vm_id)
            self.assertEqual(r, v)
        with patch.object(
                cyclades.CycladesClient, 'get_server_details',
                return_value=dict()):
            self.assertRaises(
                ClientError,
                self.client.get_firewall_profile,
                vm_id)

    @patch('%s.servers_action_post' % cyclades_pkg, return_value=FR())
    def test_set_firewall_profile(self, SP):
        vm_id = vm_recv['server']['id']
        v = firewalls['attachments'][0]['firewallProfile']
        self.client.set_firewall_profile(vm_id, v)
        SP.assert_called_once_with(vm_id, json_data=dict(
            firewallProfile=dict(profile=v)), success=202)

    @patch('%s.networks_post' % cyclades_pkg, return_value=FR())
    def test_create_network(self, NP):
        net_name = net_send['network']['name']
        FR.json = net_recv
        full_args = dict(
                cidr='192.168.0.0/24',
                gateway='192.168.0.1',
                type='MAC_FILTERED',
                dhcp=True)
        test_args = dict(full_args)
        test_args.update(dict(empty=None, full=None))
        net_exp = dict(dhcp=False, name=net_name, type='MAC_FILTERED')
        for arg, val in test_args.items():
            kwargs = {} if arg == 'empty' else full_args if (
                arg == 'full') else {arg: val}
            expected = dict(network=dict(net_exp))
            expected['network'].update(kwargs)
            r = self.client.create_network(net_name, **kwargs)
            self.assertEqual(
                NP.mock_calls[-1],
                call(json_data=expected, success=202))
            self.assert_dicts_are_equal(r, net_recv['network'])

    @patch('%s.networks_post' % cyclades_pkg, return_value=FR())
    def test_connect_server(self, NP):
        vm_id = vm_recv['server']['id']
        net_id = net_recv['network']['id']
        self.client.connect_server(vm_id, net_id)
        NP.assert_called_once_with(
            net_id, 'action',
            json_data=dict(add=dict(serverRef=vm_id)))

    @patch('%s.networks_post' % cyclades_pkg, return_value=FR())
    def test_disconnect_server(self, NP):
        net_id, vm_id = net_recv['network']['id'], vm_recv['server']['id']
        nic_id = 'nic-%s-%s' % (net_id, vm_id)
        vm_nics = [
            dict(id=nic_id, network_id=net_id),
            dict(id='another-nic-id', network_id='another-net-id'),
            dict(id=nic_id * 2, network_id=net_id * 2)]
        with patch.object(
                cyclades.CycladesClient,
                'list_server_nics',
                return_value=vm_nics) as LSN:
            r = self.client.disconnect_server(vm_id, nic_id)
            LSN.assert_called_once_with(vm_id)
            NP.assert_called_once_with(
                net_id, 'action',
                json_data=dict(remove=dict(attachment=nic_id)))
            self.assertEqual(r, 1)

    @patch('%s.servers_ips_get' % cyclades_pkg, return_value=FR())
    def test_list_server_nics(self, SG):
        vm_id = vm_recv['server']['id']
        nics = dict(attachments=[dict(id='nic1'), dict(id='nic2')])
        FR.json = nics
        r = self.client.list_server_nics(vm_id)
        SG.assert_called_once_with(vm_id)
        expected = nics['attachments']
        for i in range(len(r)):
            self.assert_dicts_are_equal(r[i], expected[i])
        self.assertEqual(i + 1, len(r))

    @patch('%s.networks_get' % cyclades_pkg, return_value=FR())
    def test_list_networks(self, NG):
        FR.json = net_list
        expected = net_list['networks']
        for detail in ('', 'detail'):
            r = self.client.list_networks(detail=True if detail else False)
            self.assertEqual(NG.mock_calls[-1], call(command=detail))
            for i, net in enumerate(expected):
                self.assert_dicts_are_equal(r[i], net)
            self.assertEqual(i + 1, len(r))

    @patch('%s.networks_get' % cyclades_pkg, return_value=FR())
    def test_list_network_nics(self, NG):
        net_id = net_recv['network']['id']
        FR.json = net_recv
        r = self.client.list_network_nics(net_id)
        NG.assert_called_once_with(network_id=net_id)
        expected = net_recv['network']['attachments']
        for i in range(len(r)):
            self.assert_dicts_are_equal(r[i], expected[i])

    @patch('%s.networks_post' % cyclades_pkg, return_value=FR())
    def test_disconnect_network_nics(self, NP):
        net_id = net_recv['network']['id']
        nics = ['nic1', 'nic2', 'nic3']
        with patch.object(
                cyclades.CycladesClient,
                'list_network_nics',
                return_value=nics) as LNN:
            self.client.disconnect_network_nics(net_id)
            LNN.assert_called_once_with(net_id)
            for i in range(len(nics)):
                expected = call(net_id, 'action', json_data=dict(
                    remove=dict(attachment=nics[i])))
                self.assertEqual(expected, NP.mock_calls[i])

    @patch('%s.networks_get' % cyclades_pkg, return_value=FR())
    def test_get_network_details(self, NG):
        FR.json = net_recv
        net_id = net_recv['network']['id']
        r = self.client.get_network_details(net_id)
        NG.assert_called_once_with(network_id=net_id)
        self.assert_dicts_are_equal(r, net_recv['network'])

    @patch('%s.networks_put' % cyclades_pkg, return_value=FR())
    def test_update_network_name(self, NP):
        net_id = net_recv['network']['id']
        new_name = '%s_new' % net_id
        self.client.update_network_name(net_id, new_name)
        NP.assert_called_once_with(
            network_id=net_id,
            json_data=dict(network=dict(name=new_name)))

    def test_delete_network(self):
        net_id = net_recv['network']['id']
        with patch.object(
                cyclades.CycladesClient, 'networks_delete',
                return_value=FR()) as ND:
            self.client.delete_network(net_id)
            ND.assert_called_once_with(net_id)
        with patch.object(
                cyclades.CycladesClient, 'networks_delete',
                side_effect=ClientError('A 421 Error', 421)):
            try:
                self.client.delete_network(421)
            except ClientError as err:
                self.assertEqual(err.status, 421)
                self.assertEqual(err.details, [
                    'Network may be still connected to at least one server'])

    @patch('%s.floating_ip_pools_get' % cyclades_pkg, return_value=FR())
    def test_get_floating_ip_pools(self, get):
        r = self.client.get_floating_ip_pools()
        self.assert_dicts_are_equal(r, FR.json)
        self.assertEqual(get.mock_calls[-1], call())

    @patch('%s.floating_ips_get' % cyclades_pkg, return_value=FR())
    def test_get_floating_ips(self, get):
        r = self.client.get_floating_ips()
        self.assert_dicts_are_equal(r, FR.json)
        self.assertEqual(get.mock_calls[-1], call())

    @patch('%s.floating_ips_post' % cyclades_pkg, return_value=FR())
    def test_alloc_floating_ip(self, post):
        FR.json = dict(floating_ip=dict(
            fixed_ip='fip',
            id=1,
            instance_id='lala',
            ip='102.0.0.1',
            pool='pisine'))
        for args in product(
                (None, 'pisine'),
                (None, 'Iwannanip')):
            r = self.client.alloc_floating_ip(*args)
            pool, address = args
            self.assert_dicts_are_equal(r, FR.json['floating_ip'])
            json_data = dict()
            if pool:
                json_data['pool'] = pool
            if address:
                json_data['address'] = address
            self.assertEqual(post.mock_calls[-1], call(json_data))

    @patch('%s.floating_ips_get' % cyclades_pkg, return_value=FR())
    def test_get_floating_ip(self, get):
        FR.json = dict(floating_ip=dict(
            fixed_ip='fip',
            id=1,
            instance_id='lala',
            ip='102.0.0.1',
            pool='pisine'))
        self.assertRaises(AssertionError, self.client.get_floating_ip, None)
        fip = 'fip'
        r = self.client.get_floating_ip(fip)
        self.assert_dicts_are_equal(r, FR.json['floating_ip'])
        self.assertEqual(get.mock_calls[-1], call(fip))

    @patch('%s.floating_ips_delete' % cyclades_pkg, return_value=FR())
    def test_delete_floating_ip(self, delete):
        self.assertRaises(AssertionError, self.client.delete_floating_ip, None)
        fip = 'fip'
        r = self.client.delete_floating_ip(fip)
        self.assert_dicts_are_equal(r, FR.headers)
        self.assertEqual(delete.mock_calls[-1], call(fip))

    @patch('%s.servers_action_post' % cyclades_pkg, return_value=FR())
    def test_attach_floating_ip(self, spost):
        vmid, addr = 42, 'anIpAddress'
        for err, args in {
                ValueError: ['not a server id', addr],
                TypeError: [None, addr],
                AssertionError: [vmid, None],
                AssertionError: [vmid, '']}.items():
            self.assertRaises(
                err, self.client.attach_floating_ip, *args)
        r = self.client.attach_floating_ip(vmid, addr)
        self.assert_dicts_are_equal(r, FR.headers)
        expected = dict(addFloatingIp=dict(address=addr))
        self.assertEqual(spost.mock_calls[-1], call(vmid, json_data=expected))

    @patch('%s.servers_action_post' % cyclades_pkg, return_value=FR())
    def test_detach_floating_ip(self, spost):
        vmid, addr = 42, 'anIpAddress'
        for err, args in {
                ValueError: ['not a server id', addr],
                TypeError: [None, addr],
                AssertionError: [vmid, None],
                AssertionError: [vmid, '']}.items():
            self.assertRaises(
                err, self.client.detach_floating_ip, *args)
        r = self.client.detach_floating_ip(vmid, addr)
        self.assert_dicts_are_equal(r, FR.headers)
        expected = dict(removeFloatingIp=dict(address=addr))
        self.assertEqual(spost.mock_calls[-1], call(vmid, json_data=expected))


if __name__ == '__main__':
    from sys import argv
    from kamaki.clients.test import runTestCase
    not_found = True
    if not argv[1:] or argv[1] == 'CycladesClient':
        not_found = False
        runTestCase(CycladesClient, 'Cyclades Client', argv[2:])
    if not argv[1:] or argv[1] == 'CycladesRestClient':
        not_found = False
        runTestCase(CycladesRestClient, 'CycladesRest Client', argv[2:])
    if not_found:
        print('TestCase %s not found' % argv[1])
