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
from mock import patch, Mock, call
from unittest import TestCase
from json import loads

from kamaki.clients import Client, ClientError
from kamaki.clients.cyclades import CycladesClient
from kamaki.clients.cyclades_rest_api import CycladesClientApi

img_ref = "1m4g3-r3f3r3nc3"
vm_name = "my new VM"
fid = 42
vm_send = dict(server=dict(
    flavorRef=fid,
    name=vm_name,
    imageRef=img_ref,
    metadata=dict(os="debian", users="root")))
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
    metadata=dict(values=dict(os="debian", users="root"))))
img_recv = dict(image=dict(
    status="ACTIVE",
    updated="2013-02-26T11:10:14+00:00",
    name="Debian Base",
    created="2013-02-26T11:03:29+00:00",
    progress=100,
    id=img_ref,
    metadata=dict(values=dict(
        partition_table="msdos",
        kernel="2.6.32",
        osfamily="linux",
        users="root",
        gui="No GUI",
        sortorder="1",
        os="debian",
        root_partition="1",
        description="Debian 6.0.7 (Squeeze) Base System"))))
vm_list = dict(servers=dict(values=[
    dict(name='n1', id=1),
    dict(name='n2', id=2)]))
flavor_list = dict(flavors=dict(values=[
        dict(id=41, name="C1R1024D20"),
        dict(id=42, name="C1R1024D40"),
        dict(id=43, name="C1R1028D20")]))
img_list = dict(images=dict(values=[
    dict(name="maelstrom", id="0fb03e45-7d5a-4515-bd4e-e6bbf6457f06"),
    dict(name="edx_saas", id="1357163d-5fd8-488e-a117-48734c526206"),
    dict(name="Debian_Wheezy_Base", id="1f8454f0-8e3e-4b6c-ab8e-5236b728dffe"),
    dict(name="CentOS", id="21894b48-c805-4568-ac8b-7d4bb8eb533d"),
    dict(name="Ubuntu Desktop", id="37bc522c-c479-4085-bfb9-464f9b9e2e31"),
    dict(name="Ubuntu 12.10", id="3a24fef9-1a8c-47d1-8f11-e07bd5e544fd"),
    dict(name="Debian Base", id="40ace203-6254-4e17-a5cb-518d55418a7d"),
    dict(name="ubuntu_bundled", id="5336e265-5c7c-4127-95cb-2bf832a79903")]))
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
    attachments=dict(values=[dict(name='att1'), dict(name='att2')])))
net_list = dict(networks=dict(values=[
    dict(id=1, name='n1'),
    dict(id=2, name='n2'),
    dict(id=3, name='n3')]))


class FR(object):
    """FR stands for Fake Response"""
    json = vm_recv
    headers = {}
    content = json
    status = None
    status_code = 200

    def release(self):
        pass

khttp = 'kamaki.clients.connection.kamakicon.KamakiHTTPConnection'
cyclades_pkg = 'kamaki.clients.cyclades.CycladesClient'


class Cyclades(TestCase):

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
        self.client = CycladesClient(self.url, self.token)
        from kamaki.clients.connection.kamakicon import KamakiHTTPConnection
        self.C = KamakiHTTPConnection

    def tearDown(self):
        FR.status_code = 200
        FR.json = vm_recv

    def test_list_servers(self):
        FR.json = vm_list
        with patch.object(
                self.C,
                'perform_request',
                return_value=FR()) as perform_req:
            r = self.client.list_servers()
            self.assertEqual(self.client.http_client.url, self.url)
            self.assertEqual(self.client.http_client.path, '/servers')
            (method, data, a_headers, a_params) = perform_req.call_args[0]
            self.assert_dicts_are_equal(dict(values=r), vm_list['servers'])
            r = self.client.list_servers(detail=True)
            self.assertEqual(self.client.http_client.url, self.url)
            self.assertEqual(self.client.http_client.path, '/servers/detail')
        with patch.object(
                CycladesClientApi,
                'servers_get',
                return_value=FR()) as servers_get:
            self.client.list_servers(changes_since=True)
            self.assertTrue(servers_get.call_args[1]['changes_since'])

    @patch('%s.perform_request' % khttp, return_value=FR())
    def test_shutdown_server(self, PR):
        vm_id = vm_recv['server']['id']
        FR.status_code = 202
        self.client.shutdown_server(vm_id)
        self.assertEqual(self.client.http_client.url, self.url)
        self.assertEqual(
            self.client.http_client.path,
            '/servers/%s/action' % vm_id)
        self.assertEqual(
            PR.call_args[0],
            ('post',  '{"shutdown": {}}', {}, {}))

    @patch('%s.perform_request' % khttp, return_value=FR())
    def test_start_server(self, PR):
        vm_id = vm_recv['server']['id']
        FR.status_code = 202
        self.client.start_server(vm_id)
        self.assertEqual(self.client.http_client.url, self.url)
        self.assertEqual(
            self.client.http_client.path,
            '/servers/%s/action' % vm_id)
        self.assertEqual(PR.call_args[0], ('post',  '{"start": {}}', {}, {}))

    @patch('%s.perform_request' % khttp, return_value=FR())
    def test_get_server_console(self, PR):
        cnsl = dict(console=dict(info1='i1', info2='i2', info3='i3'))
        FR.json = cnsl
        vm_id = vm_recv['server']['id']
        r = self.client.get_server_console(vm_id)
        self.assertEqual(self.client.http_client.url, self.url)
        self.assertEqual(
            self.client.http_client.path,
            '/servers/%s/action' % vm_id)
        self.assert_dicts_are_equal(cnsl['console'], r)
        self.assertEqual(
            PR.call_args[0],
            ('post',  '{"console": {"type": "vnc"}}', {}, {}))

    def test_get_firewall_profile(self):
        vm_id = vm_recv['server']['id']
        v = 'Some profile'
        ret = {'attachments': {'values': [{'firewallProfile': v, 1:1}]}}
        with patch.object(
                CycladesClient,
                'get_server_details',
                return_value=ret) as GSD:
            r = self.client.get_firewall_profile(vm_id)
            self.assertEqual(r, v)
            self.assertEqual(GSD.call_args[0], (vm_id,))
            ret['attachments']['values'][0].pop('firewallProfile')
            self.assertRaises(
                ClientError,
                self.client.get_firewall_profile,
                vm_id)

    @patch('%s.perform_request' % khttp, return_value=FR())
    def test_set_firewall_profile(self, PR):
        vm_id = vm_recv['server']['id']
        v = 'Some profile'
        FR.status_code = 202
        self.client.set_firewall_profile(vm_id, v)
        self.assertEqual(self.client.http_client.url, self.url)
        self.assertEqual(
            self.client.http_client.path,
            '/servers/%s/action' % vm_id)
        self.assertEqual(PR.call_args[0], (
            'post',
            '{"firewallProfile": {"profile": "%s"}}' % v,
            {},
            {}))

    @patch('%s.perform_request' % khttp, return_value=FR())
    def test_get_server_stats(self, PR):
        vm_id = vm_recv['server']['id']
        stats = dict(stat1='v1', stat2='v2', stat3='v3', stat4='v4')
        FR.json = dict(stats=stats)
        r = self.client.get_server_stats(vm_id)
        self.assertEqual(self.client.http_client.url, self.url)
        self.assertEqual(
            self.client.http_client.path,
            '/servers/%s/stats' % vm_id)
        self.assert_dicts_are_equal(stats, r)

    @patch('%s.perform_request' % khttp, return_value=FR())
    def test_create_network(self, PR):
        net_name = net_send['network']['name']
        FR.json = net_recv
        FR.status_code = 202
        full_args = dict(
                cidr='192.168.0.0/24',
                gateway='192.168.0.1',
                type='MAC_FILTERED',
                dhcp=True)
        test_args = dict(full_args)
        test_args.update(dict(empty=None, full=None))
        for arg, val in test_args.items():
            kwargs = {} if arg == 'empty' else full_args if (
                arg == 'full') else {arg: val}
            r = self.client.create_network(net_name, **kwargs)
            self.assertEqual(self.client.http_client.url, self.url)
            self.assertEqual(
                self.client.http_client.path,
                '/networks')
            self.assert_dicts_are_equal(r, net_recv['network'])
            data = PR.call_args[0][1]
            expected = dict(network=dict(net_send['network']))
            expected['network'].update(kwargs)
            self.assert_dicts_are_equal(loads(data), expected)

    @patch('%s.perform_request' % khttp, return_value=FR())
    def test_connect_server(self, PR):
        vm_id = vm_recv['server']['id']
        net_id = net_recv['network']['id']
        FR.status_code = 202
        self.client.connect_server(vm_id, net_id)
        self.assertEqual(self.client.http_client.url, self.url)
        self.assertEqual(
            self.client.http_client.path,
            '/networks/%s/action' % net_id)
        self.assertEqual(
            PR.call_args[0],
            ('post', '{"add": {"serverRef": %s}}' % vm_id, {}, {}))

    @patch('%s.networks_post' % cyclades_pkg, return_value=FR())
    def test_disconnect_server(self, NP):
        vm_id = vm_recv['server']['id']
        net_id = net_recv['network']['id']
        nic_id = 'nic-%s-%s' % (net_id, vm_id)
        vm_nics = [
            dict(id=nic_id, network_id=net_id),
            dict(id='another-nic-id', network_id='another-net-id'),
            dict(id=nic_id * 2, network_id=net_id * 2)]
        with patch.object(
                CycladesClient,
                'list_server_nics',
                return_value=vm_nics) as LSN:
            r = self.client.disconnect_server(vm_id, nic_id)
            self.assertEqual(r, 1)
            self.assertEqual(LSN.call_args[0], (vm_id,))
            self.assertEqual(NP.call_args[0], (net_id, 'action'))
            self.assertEqual(
                NP.call_args[1],
                dict(json_data=dict(remove=dict(attachment=nic_id))))

    @patch('%s.perform_request' % khttp, return_value=FR())
    def test_list_server_nics(self, PR):
        vm_id = vm_recv['server']['id']
        nics = dict(addresses=dict(values=[dict(id='nic1'), dict(id='nic2')]))
        FR.json = nics
        r = self.client.list_server_nics(vm_id)
        self.assertEqual(self.client.http_client.url, self.url)
        self.assertEqual(
            self.client.http_client.path,
            '/servers/%s/ips' % vm_id)
        expected = nics['addresses']['values']
        for i in range(len(r)):
            self.assert_dicts_are_equal(r[i], expected[i])

    @patch('%s.perform_request' % khttp, return_value=FR())
    def test_list_networks(self, PR):
        FR.json = net_list
        r = self.client.list_networks()
        self.assertEqual(self.client.http_client.url, self.url)
        self.assertEqual(self.client.http_client.path, '/networks')
        expected = net_list['networks']['values']
        for i in range(len(r)):
            self.assert_dicts_are_equal(expected[i], r[i])
        self.client.list_networks(detail=True)
        self.assertEqual(self.client.http_client.url, self.url)
        self.assertEqual(self.client.http_client.path, '/networks/detail')

    @patch('%s.perform_request' % khttp, return_value=FR())
    def test_list_network_nics(self, PR):
        net_id = net_recv['network']['id']
        FR.json = net_recv
        r = self.client.list_network_nics(net_id)
        self.assertEqual(self.client.http_client.url, self.url)
        self.assertEqual(
            self.client.http_client.path,
            '/networks/%s' % net_id)
        expected = net_recv['network']['attachments']['values']
        for i in range(len(r)):
            self.assert_dicts_are_equal(r[i], expected[i])

    @patch('%s.networks_post' % cyclades_pkg, return_value=FR())
    def test_disconnect_network_nics(self, NP):
        net_id = net_recv['network']['id']
        nics = ['nic1', 'nic2', 'nic3']
        with patch.object(
                CycladesClient,
                'list_network_nics',
                return_value=nics) as lnn:
            self.client.disconnect_network_nics(net_id)
            lnn.assert_called_once_with(net_id)
            for i in range(len(nics)):
                expected = call(net_id, 'action', json_data=dict(
                    remove=dict(attachment=nics[i])))
                self.assertEqual(expected, NP.mock_calls[i])

    @patch('%s.perform_request' % khttp, return_value=FR())
    def test_get_network_details(self, PR):
        FR.json = net_recv
        net_id = net_recv['network']['id']
        r = self.client.get_network_details(net_id)
        self.assertEqual(self.client.http_client.url, self.url)
        self.assertEqual(
            self.client.http_client.path,
            '/networks/%s' % net_id)
        self.assert_dicts_are_equal(r, net_recv['network'])

    @patch('%s.perform_request' % khttp, return_value=FR())
    def test_update_network_name(self, PR):
        net_id = net_recv['network']['id']
        new_name = '%s_new' % net_id
        FR.status_code = 204
        self.client.update_network_name(net_id, new_name)
        self.assertEqual(self.client.http_client.url, self.url)
        self.assertEqual(self.client.http_client.path, '/networks/%s' % net_id)
        (method, data, a_headers, a_params) = PR.call_args[0]
        self.assert_dicts_are_equal(
            dict(network=dict(name=new_name)),
            loads(data))

    @patch('%s.perform_request' % khttp, return_value=FR())
    def test_delete_network(self, PR):
        net_id = net_recv['network']['id']
        FR.status_code = 204
        self.client.delete_network(net_id)
        self.assertEqual(self.client.http_client.url, self.url)
        self.assertEqual(self.client.http_client.path, '/networks/%s' % net_id)

    @patch('%s.images_post' % cyclades_pkg, return_value=FR())
    def test_update_image_metadata(self, images_post):
        metadata = dict(m1='v1', m2='v2', m3='v3')
        FR.json = dict(metadata=metadata)
        r = self.client.update_image_metadata(img_ref, **metadata)
        self.assert_dicts_are_equal(r, metadata)
        (called_id, cmd) = images_post.call_args[0]
        self.assertEqual(called_id, img_ref)
        self.assertEqual(cmd, 'meta')
        data = images_post.call_args[1]['json_data']
        self.assert_dicts_are_equal(data, dict(metadata=metadata))

    @patch('%s.images_delete' % cyclades_pkg, return_value=FR())
    def test_delete_image_metadata(self, images_delete):
        key = 'metakey'
        self.client.delete_image_metadata(img_ref, key)
        self.assertEqual(
            (img_ref, '/meta/' + key),
            images_delete.call_args[0])

if __name__ == '__main__':
    from sys import argv
    from kamaki.clients.test import runTestCase
    runTestCase(Cyclades, 'Cyclades (multi) Client', argv[1:])
