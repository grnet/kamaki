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


compute_pkg_pkg = 'kamaki.clients.connection.kamakicon.KamakiHTTPConnection'
compute_pkg = 'kamaki.clients.cyclades.CycladesClient'

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

    @patch(
        '%s.get_image_details' % compute_pkg,
        return_value=img_recv['image'])
    def test_create_server(self, GID):
        with patch.object(
                CycladesClient, 'servers_post',
                side_effect=ClientError(
                    'REQUEST ENTITY TOO LARGE',
                    status=403)):
            self.assertRaises(
                ClientError,
                self.client.create_server,
                vm_name, fid, img_ref)
        self.assertEqual(GID.mock_calls[-1], call(img_ref))

        with patch.object(
                CycladesClient, 'servers_post',
                return_value=FR()) as post:
            r = self.client.create_server(vm_name, fid, img_ref)
            self.assertEqual(r, FR.json['server'])
            self.assertEqual(GID.mock_calls[-1], call(img_ref))
            self.assertEqual(post.mock_calls[-1], call(json_data=vm_send))
            prsn = 'Personality string (does not work with real servers)'
            self.client.create_server(vm_name, fid, img_ref, prsn)
            expected = dict(server=dict(vm_send['server']))
            expected['server']['personality'] = prsn
            self.assertEqual(post.mock_calls[-1], call(json_data=expected))

    @patch('%s.servers_get' % compute_pkg, return_value=FR())
    def test_list_servers(self, SG):
        FR.json = vm_list
        for detail in (False, True):
            r = self.client.list_servers(detail)
            for i, vm in enumerate(vm_list['servers']['values']):
                self.assert_dicts_are_equal(r[i], vm)
            self.assertEqual(i + 1, len(r))
            self.assertEqual(SG.mock_calls[-1], call(
                changes_since=None,
                command='detail' if detail else ''))

    @patch('%s.servers_get' % compute_pkg, return_value=FR())
    def test_get_server_details(self, SG):
        vm_id = vm_recv['server']['id']
        r = self.client.get_server_details(vm_id)
        self.assert_dicts_are_equal(r, vm_recv['server'])
        self.assertEqual(SG.mock_calls[-1], call(vm_id))

    @patch('%s.servers_put' % compute_pkg, return_value=FR())
    def test_update_server_name(self, SP):
        vm_id = vm_recv['server']['id']
        new_name = vm_name + '_new'
        self.client.update_server_name(vm_id, new_name)
        self.assertEqual(SP.mock_calls[-1], call(vm_id, json_data=dict(
            server=dict(name=new_name))))

    @patch('%s.servers_post' % compute_pkg, return_value=FR())
    def test_reboot_server(self, SP):
        vm_id = vm_recv['server']['id']
        for hard in (None, True):
            self.client.reboot_server(vm_id, hard=hard)
            self.assertEqual(SP.mock_calls[-1], call(
                vm_id, 'action',
                json_data=dict(reboot=dict(type='HARD' if hard else 'SOFT'))))

    @patch('%s.servers_put' % compute_pkg, return_value=FR())
    def test_create_server_metadata(self, SP):
        vm_id = vm_recv['server']['id']
        metadata = dict(m1='v1', m2='v2', m3='v3')
        FR.json = dict(meta=vm_recv['server'])
        for k, v in metadata.items():
            r = self.client.create_server_metadata(vm_id, k, v)
            self.assert_dicts_are_equal(r, vm_recv['server'])
            self.assertEqual(SP.mock_calls[-1], call(
                vm_id, 'meta/%s' % k,
                json_data=dict(meta={k: v}), success=201))

    @patch('%s.servers_get' % compute_pkg, return_value=FR())
    def test_get_server_metadata(self, SG):
        vm_id = vm_recv['server']['id']
        metadata = dict(m1='v1', m2='v2', m3='v3')
        FR.json = dict(metadata=dict(values=metadata))
        r = self.client.get_server_metadata(vm_id)
        self.assertEqual(SG.mock_calls[-1], call(vm_id, '/meta'))
        self.assert_dicts_are_equal(r, metadata)

        for k, v in metadata.items():
            FR.json = dict(meta={k: v})
            r = self.client.get_server_metadata(vm_id, k)
            self.assert_dicts_are_equal(r, {k: v})
            self.assertEqual(SG.mock_calls[-1], call(vm_id, '/meta/%s' % k))

    @patch('%s.servers_post' % compute_pkg, return_value=FR())
    def test_update_server_metadata(self, SP):
        vm_id = vm_recv['server']['id']
        metadata = dict(m1='v1', m2='v2', m3='v3')
        FR.json = dict(metadata=metadata)
        r = self.client.update_server_metadata(vm_id, **metadata)
        self.assert_dicts_are_equal(r, metadata)
        self.assertEqual(SP.mock_calls[-1], call(
            vm_id, 'meta',
            json_data=dict(metadata=metadata), success=201))

    @patch('%s.servers_delete' % compute_pkg, return_value=FR())
    def test_delete_server_metadata(self, SD):
        vm_id = vm_recv['server']['id']
        key = 'metakey'
        self.client.delete_server_metadata(vm_id, key)
        self.assertEqual(SD.mock_calls[-1], call(vm_id, 'meta/' + key))

    @patch('%s.flavors_get' % compute_pkg, return_value=FR())
    def test_list_flavors(self, FG):
        FR.json = flavor_list
        for cmd in ('', 'detail'):
            r = self.client.list_flavors(detail=(cmd == 'detail'))
            self.assertEqual(FG.mock_calls[-1], call(command=cmd))
            self.assert_dicts_are_equal(dict(values=r), flavor_list['flavors'])

    @patch('%s.flavors_get' % compute_pkg, return_value=FR())
    def test_get_flavor_details(self, FG):
        FR.json = dict(flavor=flavor_list['flavors'])
        r = self.client.get_flavor_details(fid)
        self.assertEqual(FG.mock_calls[-1], call(fid))
        self.assert_dicts_are_equal(r, flavor_list['flavors'])

    @patch('%s.images_get' % compute_pkg, return_value=FR())
    def test_list_images(self, IG):
        FR.json = img_list
        for cmd in ('', 'detail'):
            r = self.client.list_images(detail=(cmd == 'detail'))
            self.assertEqual(IG.mock_calls[-1], call(command=cmd))
            expected = img_list['images']['values']
            for i in range(len(r)):
                self.assert_dicts_are_equal(expected[i], r[i])

    @patch('%s.images_get' % compute_pkg, return_value=FR())
    def test_get_image_details(self, IG):
        FR.json = img_recv
        r = self.client.get_image_details(img_ref)
        self.assertEqual(IG.mock_calls[-1], call(img_ref))
        self.assert_dicts_are_equal(r, img_recv['image'])

    @patch('%s.images_get' % compute_pkg, return_value=FR())
    def test_get_image_metadata(self, IG):
        FR.json = dict(metadata=dict(values=img_recv['image']))
        r = self.client.get_image_metadata(img_ref)
        self.assertEqual(IG.mock_calls[-1], call('%s' % img_ref, '/meta'))
        self.assert_dicts_are_equal(img_recv['image'], r)
        FR.json = dict(meta=img_recv['image'])
        key = 'somekey'
        r = self.client.get_image_metadata(img_ref, key)
        self.assertEqual(
            IG.mock_calls[-1],
            call('%s' % img_ref, '/meta/%s' % key))
        self.assert_dicts_are_equal(img_recv['image'], r)

    @patch('%s.servers_delete' % compute_pkg, return_value=FR())
    def test_delete_server(self, SD):
        vm_id = vm_recv['server']['id']
        self.client.delete_server(vm_id)
        self.assertEqual(SD.mock_calls[-1], call(vm_id))

    """
    @patch('%s.perform_request' % compute_pkg, return_value=FR())
    def test_delete_image(self, PR):
        FR.status_code = 204
        self.client.delete_image(img_ref)
        self.assertEqual(self.client.http_client.url, self.url)
        self.assertEqual(self.client.http_client.path, '/images/%s' % img_ref)

    @patch('%s.perform_request' % compute_pkg, return_value=FR())
    def test_delete_network(self, PR):
        net_id = net_recv['network']['id']
        FR.status_code = 204
        self.client.delete_network(net_id)
        self.assertEqual(self.client.http_client.url, self.url)
        self.assertEqual(self.client.http_client.path, '/networks/%s' % net_id)

    @patch('%s.perform_request' % compute_pkg, return_value=FR())
    def test_create_image_metadata(self, PR):
        metadata = dict(m1='v1', m2='v2', m3='v3')
        FR.json = dict(meta=img_recv['image'])
        self.assertRaises(
            ClientError,
            self.client.create_image_metadata,
            img_ref, 'key', 'value')
        FR.status_code = 201
        for k, v in metadata.items():
            r = self.client.create_image_metadata(img_ref, k, v)
            self.assertEqual(self.client.http_client.url, self.url)
            self.assertEqual(
                self.client.http_client.path,
                '/images/%s/meta/%s' % (img_ref, k))
            (method, data, a_headers, a_params) = PR.call_args[0]
            self.assertEqual(dict(meta={k: v}), loads(data))
            self.assert_dicts_are_equal(r, img_recv['image'])

    @patch('%s.images_post' % compute_pkg, return_value=FR())
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

    @patch('%s.images_delete' % compute_pkg, return_value=FR())
    def test_delete_image_metadata(self, images_delete):
        key = 'metakey'
        self.client.delete_image_metadata(img_ref, key)
        self.assertEqual(
            (img_ref, '/meta/' + key),
            images_delete.call_args[0])
    """

if __name__ == '__main__':
    from sys import argv
    from kamaki.clients.test import runTestCase
    runTestCase(Cyclades, 'Cyclades (multi) Client', argv[1:])
