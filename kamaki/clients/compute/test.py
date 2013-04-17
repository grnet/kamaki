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

from kamaki.clients import ClientError, compute


rest_pkg = 'kamaki.clients.compute.rest_api.ComputeRestClient'
compute_pkg = 'kamaki.clients.compute.ComputeClient'

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


class FR(object):
    """FR stands for Fake Response"""
    json = vm_recv
    headers = {}
    content = json
    status = None
    status_code = 200


class ComputeRestClient(TestCase):

    """Set up a ComputesRest thorough test"""
    def setUp(self):
        self.url = 'http://cyclades.example.com'
        self.token = 'cyc14d3s70k3n'
        self.client = compute.ComputeRestClient(self.url, self.token)

    def tearDown(self):
        FR.json = vm_recv

    @patch('%s.get' % rest_pkg, return_value=FR())
    def _test_get(self, service, get):
        for args in product(
                ('', '%s_id' % service),
                ('', 'cmd'),
                (200, 204),
                ({}, {'k': 'v'})):
            (srv_id, command, success, kwargs) = args
            method = getattr(self.client, '%s_get' % service)
            method(*args[:3], **kwargs)
            srv_str = '/%s' % srv_id if srv_id else ''
            cmd_str = '/%s' % command if command else ''
            self.assertEqual(get.mock_calls[-1], call(
                '/%s%s%s' % (service, srv_str, cmd_str),
                success=success,
                **kwargs))

    def test_servers_get(self):
        self._test_get('servers')

    def test_flavors_get(self):
        self._test_get('flavors')

    def test_images_get(self):
        self._test_get('images')

    @patch('%s.delete' % rest_pkg, return_value=FR())
    def _test_delete(self, service, delete):
        for args in product(
                ('', '%s_id' % service),
                ('', 'cmd'),
                (204, 208),
                ({}, {'k': 'v'})):
            (srv_id, command, success, kwargs) = args
            method = getattr(self.client, '%s_delete' % service)
            method(*args[:3], **kwargs)
            vm_str = '/%s' % srv_id if srv_id else ''
            cmd_str = '/%s' % command if command else ''
            self.assertEqual(delete.mock_calls[-1], call(
                '/%s%s%s' % (service, vm_str, cmd_str),
                success=success,
                **kwargs))

    def test_servers_delete(self):
        self._test_delete('servers')

    def test_images_delete(self):
        self._test_delete('images')

    @patch('%s.set_header' % rest_pkg)
    @patch('%s.post' % rest_pkg, return_value=FR())
    def _test_post(self, service, post, SH):
        for args in product(
                ('', '%s_id' % service),
                ('', 'cmd'),
                (None, [dict(json="data"), dict(data="json")]),
                (202, 204),
                ({}, {'k': 'v'})):
            (srv_id, command, json_data, success, kwargs) = args
            method = getattr(self.client, '%s_post' % service)
            method(*args[:4], **kwargs)
            vm_str = '/%s' % srv_id if srv_id else ''
            cmd_str = '/%s' % command if command else ''
            if json_data:
                json_data = dumps(json_data)
                self.assertEqual(SH.mock_calls[-2:], [
                    call('Content-Type', 'application/json'),
                    call('Content-Length', len(json_data))])
            self.assertEqual(post.mock_calls[-1], call(
                '/%s%s%s' % (service, vm_str, cmd_str),
                data=json_data, success=success,
                **kwargs))

    def test_servers_post(self):
        self._test_post('servers')

    def test_images_post(self):
        self._test_post('images')

    @patch('%s.set_header' % rest_pkg)
    @patch('%s.put' % rest_pkg, return_value=FR())
    def _test_put(self, service, put, SH):
        for args in product(
                ('', '%s_id' % service),
                ('', 'cmd'),
                (None, [dict(json="data"), dict(data="json")]),
                (204, 504),
                ({}, {'k': 'v'})):
            (server_id, command, json_data, success, kwargs) = args
            method = getattr(self.client, '%s_put' % service)
            method(*args[:4], **kwargs)
            vm_str = '/%s' % server_id if server_id else ''
            cmd_str = '/%s' % command if command else ''
            if json_data:
                json_data = dumps(json_data)
                self.assertEqual(SH.mock_calls[-2:], [
                    call('Content-Type', 'application/json'),
                    call('Content-Length', len(json_data))])
            self.assertEqual(put.mock_calls[-1], call(
                '/%s%s%s' % (service, vm_str, cmd_str),
                data=json_data, success=success,
                **kwargs))

    def test_servers_put(self):
        self._test_put('servers')

    def test_images_put(self):
        self._test_put('images')


class ComputeClient(TestCase):

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
        self.client = compute.ComputeClient(self.url, self.token)

    def tearDown(self):
        FR.status_code = 200
        FR.json = vm_recv

    @patch(
        '%s.get_image_details' % compute_pkg,
        return_value=img_recv['image'])
    def test_create_server(self, GID):
        with patch.object(
                compute.ComputeClient, 'servers_post',
                side_effect=ClientError(
                    'REQUEST ENTITY TOO LARGE',
                    status=403)):
            self.assertRaises(
                ClientError,
                self.client.create_server,
                vm_name, fid, img_ref)

        with patch.object(
                compute.ComputeClient, 'servers_post',
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
            self.assertEqual(SG.mock_calls[-1], call(
                command='detail' if detail else ''))
            for i, vm in enumerate(vm_list['servers']['values']):
                self.assert_dicts_are_equal(r[i], vm)
            self.assertEqual(i + 1, len(r))

    @patch('%s.servers_get' % compute_pkg, return_value=FR())
    def test_get_server_details(self, SG):
        vm_id = vm_recv['server']['id']
        r = self.client.get_server_details(vm_id)
        SG.assert_called_once_with(vm_id)
        self.assert_dicts_are_equal(r, vm_recv['server'])

    @patch('%s.servers_put' % compute_pkg, return_value=FR())
    def test_update_server_name(self, SP):
        vm_id = vm_recv['server']['id']
        new_name = vm_name + '_new'
        self.client.update_server_name(vm_id, new_name)
        SP.assert_called_once_with(vm_id, json_data=dict(
            server=dict(name=new_name)))

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
        SG.assert_called_once_with(vm_id, '/meta')
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
        SP.assert_called_once_with(
            vm_id, 'meta',
            json_data=dict(metadata=metadata), success=201)

    @patch('%s.servers_delete' % compute_pkg, return_value=FR())
    def test_delete_server_metadata(self, SD):
        vm_id = vm_recv['server']['id']
        key = 'metakey'
        self.client.delete_server_metadata(vm_id, key)
        SD.assert_called_once_with(vm_id, 'meta/' + key)

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
        FG.assert_called_once_with(fid)
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
        IG.assert_called_once_with(img_ref)
        self.assert_dicts_are_equal(r, img_recv['image'])

    @patch('%s.images_get' % compute_pkg, return_value=FR())
    def test_get_image_metadata(self, IG):
        for key in ('', '50m3k3y'):
            FR.json = dict(meta=img_recv['image']) if (
                key) else dict(metadata=dict(values=img_recv['image']))
            r = self.client.get_image_metadata(img_ref, key)
            self.assertEqual(IG.mock_calls[-1], call(
                '%s' % img_ref,
                '/meta%s' % (('/%s' % key) if key else '')))
            self.assert_dicts_are_equal(img_recv['image'], r)

    @patch('%s.servers_delete' % compute_pkg, return_value=FR())
    def test_delete_server(self, SD):
        vm_id = vm_recv['server']['id']
        self.client.delete_server(vm_id)
        SD.assert_called_once_with(vm_id)

    @patch('%s.images_delete' % compute_pkg, return_value=FR())
    def test_delete_image(self, ID):
        self.client.delete_image(img_ref)
        ID.assert_called_once_with(img_ref)

    @patch('%s.images_put' % compute_pkg, return_value=FR())
    def test_create_image_metadata(self, IP):
        (key, val) = ('k1', 'v1')
        FR.json = dict(meta=img_recv['image'])
        r = self.client.create_image_metadata(img_ref, key, val)
        IP.assert_called_once_with(
            img_ref, 'meta/%s' % key,
            json_data=dict(meta={key: val}))
        self.assert_dicts_are_equal(r, img_recv['image'])

    @patch('%s.images_post' % compute_pkg, return_value=FR())
    def test_update_image_metadata(self, IP):
        metadata = dict(m1='v1', m2='v2', m3='v3')
        FR.json = dict(metadata=metadata)
        r = self.client.update_image_metadata(img_ref, **metadata)
        IP.assert_called_once_with(
            img_ref, 'meta',
            json_data=dict(metadata=metadata))
        self.assert_dicts_are_equal(r, metadata)

    @patch('%s.images_delete' % compute_pkg, return_value=FR())
    def test_delete_image_metadata(self, ID):
        key = 'metakey'
        self.client.delete_image_metadata(img_ref, key)
        ID.assert_called_once_with(img_ref, '/meta/%s' % key)


if __name__ == '__main__':
    from sys import argv
    from kamaki.clients.test import runTestCase
    not_found = True
    if not argv[1:] or argv[1] == 'ComputeClient':
        not_found = False
        runTestCase(ComputeClient, 'Compute Client', argv[2:])
    if not argv[1:] or argv[1] == 'ComputeRest':
        not_found = False
        runTestCase(ComputeRestClient, 'ComputeRest Client', argv[2:])
    if not_found:
        print('TestCase %s not found' % argv[1])
