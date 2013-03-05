# Copyright 2012-2013 GRNET S.A. All rights reserved.
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
from mock import patch, Mock
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


class Cyclades(TestCase):

    def assert_dicts_are_equal(self, d1, d2):
        for k, v in d1.items():
            self.assertTrue(k in d2)
            if isinstance(v, dict):
                self.assert_dicts_are_equal(v, d2[k])
            else:
                self.assertEqual(unicode(v), unicode(d2[k]))

    class FR(object):
        """FR stands for Fake Response"""
        json = vm_recv
        headers = {}
        content = json
        status = None
        status_code = 200

        def release(self):
            pass

    """Set up a Cyclades thorough test"""
    def setUp(self):
        self.url = 'http://cyclades.example.com'
        self.token = 'cyc14d3s70k3n'
        self.client = CycladesClient(self.url, self.token)
        from kamaki.clients.connection.kamakicon import KamakiHTTPConnection
        self.C = KamakiHTTPConnection

    def tearDown(self):
        self.FR.status_code = 200
        self.FR.json = vm_recv

    def test_create_server(self):
        self.client.get_image_details = Mock(return_value=img_recv['image'])
        with patch.object(Client, 'request', side_effect=ClientError(
                'REQUEST ENTITY TOO LARGE',
                status=403)):
            self.assertRaises(
                ClientError,
                self.client.create_server,
                vm_name, fid, img_ref)

        with patch.object(
                self.C,
                'perform_request',
                return_value=self.FR()) as perform_req:
            self.assertRaises(
                ClientError,
                self.client.create_server,
                vm_name, fid, img_ref)
            self.FR.status_code = 202
            r = self.client.create_server(vm_name, fid, img_ref)
            self.assertEqual(self.client.http_client.url, self.url)
            self.assertEqual(self.client.http_client.path, '/servers')
            (method, data, a_headers, a_params) = perform_req.call_args[0]
            self.assert_dicts_are_equal(loads(data), vm_send)
            self.assert_dicts_are_equal(r, vm_recv['server'])
            prsn = 'Personality string (does not work with real servers)'
            self.client.create_server(vm_name, fid, img_ref, prsn)
            (method, data, a_headers, a_params) = perform_req.call_args[0]
            data = loads(data)
            self.assertTrue('personality' in data['server'])
            self.assertEqual(prsn, data['server']['personality'])

    def test_list_servers(self):
        self.FR.json = vm_list
        with patch.object(
                self.C,
                'perform_request',
                return_value=self.FR()) as perform_req:
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
                return_value=self.FR()) as servers_get:
            self.client.list_servers(changes_since=True)
            self.assertTrue(servers_get.call_args[1]['changes_since'])

    def test_get_server_details(self):
        vm_id = vm_recv['server']['id']
        with patch.object(self.C, 'perform_request', return_value=self.FR()):
            r = self.client.get_server_details(vm_id)
            self.assertEqual(self.client.http_client.url, self.url)
            self.assertEqual(
                self.client.http_client.path,
                '/servers/%s' % vm_id)
            self.assert_dicts_are_equal(r, vm_recv['server'])

    def test_update_server_name(self):
        vm_id = vm_recv['server']['id']
        new_name = vm_name + '_new'
        self.FR.status_code = 204
        with patch.object(
                self.C,
                'perform_request',
                return_value=self.FR()) as perform_req:
            self.client.update_server_name(vm_id, new_name)
            self.assertEqual(self.client.http_client.url, self.url)
            self.assertEqual(
                self.client.http_client.path,
                '/servers/%s' % vm_id)
            (method, data, a_headers, a_params) = perform_req.call_args[0]
            self.assert_dicts_are_equal(
                dict(server=dict(name=new_name)),
                loads(data))

    def test_reboot_server(self):
        vm_id = vm_recv['server']['id']
        self.FR.status_code = 202
        with patch.object(
                self.C,
                'perform_request',
                return_value=self.FR()) as perform_req:
            self.client.reboot_server(vm_id)
            self.assertEqual(self.client.http_client.url, self.url)
            self.assertEqual(
                self.client.http_client.path,
                '/servers/%s/action' % vm_id)
            (method, data, a_headers, a_params) = perform_req.call_args[0]
            self.assert_dicts_are_equal(
                dict(reboot=dict(type='SOFT')),
                loads(data))

    def test_create_server_metadata(self):
        vm_id = vm_recv['server']['id']
        metadata = dict(m1='v1', m2='v2', m3='v3')
        self.FR.json = dict(meta=vm_recv['server'])
        with patch.object(
                self.C,
                'perform_request',
                return_value=self.FR()) as perform_req:
            self.assertRaises(
                ClientError,
                self.client.create_server_metadata,
                vm_id, 'key', 'value')
            self.FR.status_code = 201
            for k, v in metadata.items():
                r = self.client.create_server_metadata(vm_id, k, v)
                self.assertEqual(self.client.http_client.url, self.url)
                self.assertEqual(
                    self.client.http_client.path,
                    '/servers/%s/meta/%s' % (vm_id, k))
                (method, data, a_headers, a_params) = perform_req.call_args[0]
                self.assertEqual(dict(meta={k: v}), loads(data))
                self.assert_dicts_are_equal(r, vm_recv['server'])

    def test_get_server_metadata(self):
        vm_id = vm_recv['server']['id']
        metadata = dict(m1='v1', m2='v2', m3='v3')
        with patch.object(self.C, 'perform_request', return_value=self.FR()):
            self.FR.json = dict(metadata=dict(values=metadata))
            r = self.client.get_server_metadata(vm_id)
            self.assertEqual(self.client.http_client.url, self.url)
            self.assertEqual(
                self.client.http_client.path,
                '/servers/%s/meta' % vm_id)
            self.assert_dicts_are_equal(r, metadata)

            for k, v in metadata.items():
                self.FR.json = dict(meta={k: v})
                r = self.client.get_server_metadata(vm_id, k)
                self.assertEqual(self.client.http_client.url, self.url)
                self.assertEqual(
                    self.client.http_client.path,
                    '/servers/%s/meta/%s' % (vm_id, k))
                self.assert_dicts_are_equal(r, {k: v})

    def test_update_server_metadata(self):
        vm_id = vm_recv['server']['id']
        metadata = dict(m1='v1', m2='v2', m3='v3')
        self.FR.json = dict(metadata=metadata)
        with patch.object(
                CycladesClientApi,
                'servers_post',
                return_value=self.FR()) as servers_post:
            r = self.client.update_server_metadata(vm_id, **metadata)
            self.assert_dicts_are_equal(r, metadata)
            (called_id, cmd) = servers_post.call_args[0]
            self.assertEqual(called_id, vm_id)
            self.assertEqual(cmd, 'meta')
            data = servers_post.call_args[1]['json_data']
            self.assert_dicts_are_equal(data, dict(metadata=metadata))

    def test_delete_server_metadata(self):
        vm_id = vm_recv['server']['id']
        key = 'metakey'
        with patch.object(
                CycladesClientApi,
                'servers_delete',
                return_value=self.FR()) as servers_delete:
            self.client.delete_server_metadata(vm_id, key)
            self.assertEqual(
                (vm_id, 'meta/' + key),
                servers_delete.call_args[0])

    def test_list_flavors(self):
        self.FR.json = flavor_list
        with patch.object(
                self.C,
                'perform_request',
                return_value=self.FR()) as perform_req:
            r = self.client.list_flavors()
            self.assertEqual(self.client.http_client.url, self.url)
            self.assertEqual(self.client.http_client.path, '/flavors')
            (method, data, a_headers, a_params) = perform_req.call_args[0]
            self.assert_dicts_are_equal(dict(values=r), flavor_list['flavors'])
            r = self.client.list_flavors(detail=True)
            self.assertEqual(self.client.http_client.url, self.url)
            self.assertEqual(self.client.http_client.path, '/flavors/detail')

    def test_get_flavor_details(self):
        self.FR.json = dict(flavor=flavor_list['flavors'])
        with patch.object(self.C, 'perform_request', return_value=self.FR()):
            r = self.client.get_flavor_details(fid)
            self.assertEqual(self.client.http_client.url, self.url)
            self.assertEqual(
                self.client.http_client.path,
                '/flavors/%s' % fid)
            self.assert_dicts_are_equal(r, flavor_list['flavors'])

    def test_list_images(self):
        self.FR.json = img_list
        with patch.object(self.C, 'perform_request', return_value=self.FR()):
            r = self.client.list_images()
            self.assertEqual(self.client.http_client.url, self.url)
            self.assertEqual(self.client.http_client.path, '/images')
            expected = img_list['images']['values']
            for i in range(len(r)):
                self.assert_dicts_are_equal(expected[i], r[i])
            self.client.list_images(detail=True)
            self.assertEqual(self.client.http_client.url, self.url)
            self.assertEqual(self.client.http_client.path, '/images/detail')

    def test_get_image_details(self):
        self.FR.json = img_recv
        with patch.object(self.C, 'perform_request', return_value=self.FR()):
            r = self.client.get_image_details(img_ref)
            self.assertEqual(self.client.http_client.url, self.url)
            self.assertEqual(
                self.client.http_client.path,
                '/images/%s' % img_ref)
            self.assert_dicts_are_equal(r, img_recv['image'])

    def test_get_image_metadata(self):
        self.FR.json = dict(metadata=dict(values=img_recv['image']))
        with patch.object(
                CycladesClient,
                'images_get',
                return_value=self.FR()) as inner:
            r = self.client.get_image_metadata(img_ref)
            self.assertEqual(inner.call_args[0], ('%s' % img_ref, '/meta'))
            self.assert_dicts_are_equal(img_recv['image'], r)
            self.FR.json = dict(meta=img_recv['image'])
            key = 'somekey'
            self.client.get_image_metadata(img_ref, key)
            self.assertEqual(
                inner.call_args[0],
                ('%s' % img_ref, '/meta/%s' % key))

    def test_shutdown_server(self):
        vm_id = vm_recv['server']['id']
        self.FR.status_code = 202
        with patch.object(
                self.C,
                'perform_request',
                return_value=self.FR()) as perform_req:
            self.client.shutdown_server(vm_id)
            self.assertEqual(self.client.http_client.url, self.url)
            self.assertEqual(
                self.client.http_client.path,
                '/servers/%s/action' % vm_id)
            self.assertEqual(
                perform_req.call_args[0],
                ('post',  '{"shutdown": {}}', {}, {}))

    def test_start_server(self):
        vm_id = vm_recv['server']['id']
        self.FR.status_code = 202
        with patch.object(
                self.C,
                'perform_request',
                return_value=self.FR()) as perform_req:
            self.client.start_server(vm_id)
            self.assertEqual(self.client.http_client.url, self.url)
            self.assertEqual(
                self.client.http_client.path,
                '/servers/%s/action' % vm_id)
            self.assertEqual(
                perform_req.call_args[0],
                ('post',  '{"start": {}}', {}, {}))

    def test_get_server_console(self):
        cnsl = dict(console=dict(info1='i1', info2='i2', info3='i3'))
        self.FR.json = cnsl
        vm_id = vm_recv['server']['id']
        with patch.object(
                self.C,
                'perform_request',
                return_value=self.FR()) as perform_req:
            r = self.client.get_server_console(vm_id)
            self.assertEqual(self.client.http_client.url, self.url)
            self.assertEqual(
                self.client.http_client.path,
                '/servers/%s/action' % vm_id)
            self.assert_dicts_are_equal(cnsl['console'], r)
            self.assertEqual(
                perform_req.call_args[0],
                ('post',  '{"console": {"type": "vnc"}}', {}, {}))

    def test_get_firewall_profile(self):
        vm_id = vm_recv['server']['id']
        v = 'Some profile'
        ret = {'attachments': {'values': [{'firewallProfile': v, 1:1}]}}
        with patch.object(
                CycladesClient,
                'get_server_details',
                return_value=ret) as gsd:
            r = self.client.get_firewall_profile(vm_id)
            self.assertEqual(r, v)
            self.assertEqual(gsd.call_args[0], (vm_id,))
            ret['attachments']['values'][0].pop('firewallProfile')
            self.assertRaises(
                ClientError, self.client.get_firewall_profile,
                vm_id)

    def test_set_firewall_profile(self):
        vm_id = vm_recv['server']['id']
        v = 'Some profile'
        self.FR.status_code = 202
        with patch.object(
                self.C,
                'perform_request',
                return_value=self.FR()) as perform_req:
            self.client.set_firewall_profile(vm_id, v)
            self.assertEqual(self.client.http_client.url, self.url)
            self.assertEqual(
                self.client.http_client.path,
                '/servers/%s/action' % vm_id)
            self.assertEqual(perform_req.call_args[0], (
                'post',
                '{"firewallProfile": {"profile": "%s"}}' % v,
                {},
                {}))

    def test_get_server_stats(self):
        vm_id = vm_recv['server']['id']
        stats = dict(stat1='v1', stat2='v2', stat3='v3', stat4='v4')
        self.FR.json = dict(stats=stats)
        with patch.object(self.C, 'perform_request', return_value=self.FR()):
            r = self.client.get_server_stats(vm_id)
            self.assertEqual(self.client.http_client.url, self.url)
            self.assertEqual(
                self.client.http_client.path,
                '/servers/%s/stats' % vm_id)
            self.assert_dicts_are_equal(stats, r)

    def test_create_network(self):
        net_name = net_send['network']['name']
        self.FR.json = net_recv
        self.FR.status_code = 202
        with patch.object(
                self.C,
                'perform_request',
                return_value=self.FR()) as perform_req:
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
                data = perform_req.call_args[0][1]
                expected = dict(network=dict(net_send['network']))
                expected['network'].update(kwargs)
                self.assert_dicts_are_equal(loads(data), expected)

    def test_connect_server(self):
        vm_id = vm_recv['server']['id']
        net_id = net_recv['network']['id']
        self.FR.status_code = 202
        with patch.object(
            self.C,
            'perform_request',
            return_value=self.FR()) as perform_req:
            self.client.connect_server(vm_id, net_id)
            self.assertEqual(self.client.http_client.url, self.url)
            self.assertEqual(
                self.client.http_client.path,
                '/networks/%s/action' % net_id)
            self.assertEqual(
                perform_req.call_args[0],
                ('post', '{"add": {"serverRef": %s}}' % vm_id, {}, {}))

    def test_disconnect_server(self):
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
                return_value=vm_nics) as lsn:
            with patch.object(
                    CycladesClient,
                    'networks_post',
                    return_value=self.FR()) as np:
                r = self.client.disconnect_server(vm_id, nic_id)
                self.assertEqual(r, 1)
                self.assertEqual(lsn.call_args[0], (vm_id,))
                self.assertEqual(np.call_args[0], (net_id, 'action'))
                self.assertEqual(np.call_args[1], dict(json_data=dict(
                    remove=dict(attachment=nic_id))))

    def test_list_server_nics(self):
        vm_id = vm_recv['server']['id']
        nics = dict(addresses=dict(values=[dict(id='nic1'), dict(id='nic2')]))
        self.FR.json = nics
        with patch.object(self.C, 'perform_request', return_value=self.FR()):
            r = self.client.list_server_nics(vm_id)
            self.assertEqual(self.client.http_client.url, self.url)
            self.assertEqual(
                self.client.http_client.path,
                '/servers/%s/ips' % vm_id)
            expected = nics['addresses']['values']
            for i in range(len(r)):
                self.assert_dicts_are_equal(r[i], expected[i])

    def test_list_networks(self):
        self.FR.json = net_list
        with patch.object(self.C, 'perform_request', return_value=self.FR()):
            r = self.client.list_networks()
            self.assertEqual(self.client.http_client.url, self.url)
            self.assertEqual(self.client.http_client.path, '/networks')
            expected = net_list['networks']['values']
            for i in range(len(r)):
                self.assert_dicts_are_equal(expected[i], r[i])
            self.client.list_networks(detail=True)
            self.assertEqual(self.client.http_client.url, self.url)
            self.assertEqual(self.client.http_client.path, '/networks/detail')

    def test_get_network_details(self):
        self.FR.json = net_recv
        net_id = net_recv['network']['id']
        with patch.object(self.C, 'perform_request', return_value=self.FR()):
            r = self.client.get_network_details(net_id)
            self.assertEqual(self.client.http_client.url, self.url)
            self.assertEqual(
                self.client.http_client.path,
                '/networks/%s' % net_id)
            self.assert_dicts_are_equal(r, net_recv['network'])

    def test_update_network_name(self):
        net_id = net_recv['network']['id']
        new_name = '%s_new' % net_id
        self.FR.status_code = 204
        with patch.object(
                self.C,
                'perform_request',
                return_value=self.FR()) as perform_req:
            self.client.update_network_name(net_id, new_name)
            self.assertEqual(self.client.http_client.url, self.url)
            self.assertEqual(
                self.client.http_client.path,
                '/networks/%s' % net_id)
            (method, data, a_headers, a_params) = perform_req.call_args[0]
            self.assert_dicts_are_equal(
                dict(network=dict(name=new_name)),
                loads(data))

    """
    def test_delete_image(self):
        images = self.client.list_images()
        self.client.delete_image(images[2]['id'])
        try:
            r = self.client.get_image_details(images[2]['id'], success=(400))
        except ClientError as err:
            self.assertEqual(err.status, 404)

    def test_create_image_metadata(self):
        r = self.client.create_image_metadata(self.img, 'mykey', 'myval')
        self.assertEqual(r['mykey'], 'myval')

    def test_update_image_metadata(self):
        r = self.client.create_image_metadata(self.img, 'mykey0', 'myval')
        r = self.client.update_image_metadata(self.img, 'mykey0', 'myval0')
        self.assertEqual(r['mykey0'], 'myval0')

    def test_delete_image_metadata(self):
        self.client.create_image_metadata(self.img, 'mykey1', 'myval1')
        self.client.delete_image_metadata(self.img, 'mykey1')
        r = self.client.get_image_metadata(self.img)
        self.assertNotEqual('mykey1' in r)
    """
