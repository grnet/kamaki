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
    name=vm_name, imageRef=img_ref,
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
        from kamaki.clients.cyclades import CycladesClient
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
        from kamaki.clients.cyclades_rest_api import CycladesClientApi
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

    """
    def _test_0050_update_server_name(self):
        new_name = self.servname1 + '_new_name'
        self.client.update_server_name(self.server1['id'], new_name)
        r = self.client.get_server_details(
            self.server1['id'],
            success=(200, 400))
        self.assertEqual(r['name'], new_name)
        changed = self.servers.pop(self.servname1)
        changed['name'] = new_name
        self.servers[new_name] = changed

    def test_reboot_server(self):
        print('')
        self._wait_for_status(self.server1['id'], 'REBOOT')
        self._wait_for_status(self.server2['id'], 'REBOOT')

    def test_create_server_metadata(self):
        r1 = self.client.create_server_metadata(
            self.server1['id'],
            'mymeta',
            'mymeta val')
        self.assertTrue('mymeta' in r1)
        r2 = self.client.get_server_metadata(self.server1['id'], 'mymeta')
        self.assert_dicts_are_equal(r1, r2)

    def test_get_server_metadata(self):
        self.client.create_server_metadata(
            self.server1['id'],
            'mymeta_0',
            'val_0')
        r = self.client.get_server_metadata(self.server1['id'], 'mymeta_0')
        self.assertEqual(r['mymeta_0'], 'val_0')

    def test_update_server_metadata(self):
        r1 = self.client.create_server_metadata(
            self.server1['id'],
            'mymeta3',
            'val2')
        self.assertTrue('mymeta3'in r1)
        r2 = self.client.update_server_metadata(
            self.server1['id'],
            mymeta3='val3')
        self.assertTrue(r2['mymeta3'], 'val3')

    def test_delete_server_metadata(self):
        r1 = self.client.create_server_metadata(
            self.server1['id'],
            'mymeta',
            'val')
        self.assertTrue('mymeta' in r1)
        self.client.delete_server_metadata(self.server1['id'], 'mymeta')
        try:
            self.client.get_server_metadata(self.server1['id'], 'mymeta')
            raise ClientError('Wrong Error', status=100)
        except ClientError as err:
            self.assertEqual(err.status, 404)

    def test_list_flavors(self):
        r = self.client.list_flavors()
        self.assertTrue(len(r) > 1)
        r = self.client.list_flavors(detail=True)
        self.assertTrue('SNF:disk_template' in r[0])

    def test_get_flavor_details(self):
        r = self.client.get_flavor_details(self.flavorid)
        self.assert_dicts_are_equal(self._flavor_details, r)

    def test_list_images(self):
        r = self.client.list_images()
        self.assertTrue(len(r) > 1)
        r = self.client.list_images(detail=True)
        for detailed_img in r:
            if detailed_img['id'] == self.img:
                break
        self.assert_dicts_are_equal(detailed_img, self.img_details)

    def test_get_image_details(self):
        r = self.client.get_image_details(self.img)
        self.assert_dicts_are_equal(r, self.img_details)

    def test_get_image_metadata(self):
        r = self.client.get_image_metadata(self.img)
        self.assert_dicts_are_equal(
            self.img_details['metadata']['values'], r)
        for key, val in self.img_details['metadata']['values'].items():
            r = self.client.get_image_metadata(self.img, key)
            self.assertEqual(r[key], val)

    def test_shutdown_server(self):
        self.client.shutdown_server(self.server1['id'])
        self._wait_for_status(self.server1['id'], 'ACTIVE')
        r = self.client.get_server_details(self.server1['id'])
        self.assertEqual(r['status'], 'STOPPED')

    def test_start_server(self):
        self.client.start_server(self.server1['id'])
        self._wait_for_status(self.server1['id'], 'STOPPED')
        r = self.client.get_server_details(self.server1['id'])
        self.assertEqual(r['status'], 'ACTIVE')

    def test_get_server_console(self):
        r = self.client.get_server_console(self.server2['id'])
        self.assertTrue('host' in r)
        self.assertTrue('password' in r)
        self.assertTrue('port' in r)
        self.assertTrue('type' in r)

    def test_get_firewall_profile(self):
        self._wait_for_status(self.server1['id'], 'BUILD')
        fprofile = self.client.get_firewall_profile(self.server1['id'])
        self.assertTrue(fprofile in self.PROFILES)

    def test_set_firewall_profile(self):
        self._wait_for_status(self.server1['id'], 'BUILD')
        PROFILES = ['DISABLED', 'ENABLED', 'DISABLED', 'PROTECTED']
        fprofile = self.client.get_firewall_profile(self.server1['id'])
        print('')
        count_success = 0
        for counter, fprofile in enumerate(PROFILES):
            npos = counter + 1
            try:
                nprofile = PROFILES[npos]
            except IndexError:
                nprofile = PROFILES[0]
            print('\tprofile swap %s: %s -> %s' % (npos, fprofile, nprofile))
            self.client.set_firewall_profile(self.server1['id'], nprofile)
            time.sleep(0.5)
            self.client.reboot_server(self.server1['id'], hard=True)
            time.sleep(1)
            self._wait_for_status(self.server1['id'], 'REBOOT')
            time.sleep(0.5)
            changed = self.client.get_firewall_profile(self.server1['id'])
            try:
                self.assertEqual(changed, nprofile)
            except AssertionError as err:
                if count_success:
                    print('\tFAIL in swap #%s' % npos)
                    break
                else:
                    raise err
            count_success += 1

    def test_get_server_stats(self):
        r = self.client.get_server_stats(self.server1['id'])
        it = ('cpuBar', 'cpuTimeSeries', 'netBar', 'netTimeSeries', 'refresh')
        for term in it:
            self.assertTrue(term in r)

    def test_create_network(self):
        print('\twith no params')
        self.network1 = self._create_network(self.netname1)
        self._wait_for_network(self.network1['id'], 'ACTIVE')
        n1id = self.network1['id']
        self.network1 = self.client.get_network_details(n1id)
        nets = self.client.list_networks(self.network1['id'])
        chosen = [net for net in nets if net['id'] == n1id][0]
        chosen.pop('updated')
        net1 = dict(self.network1)
        net1.pop('updated')
        self.assert_dicts_are_equal(chosen, net1)
        for param, val in dict(
                cidr='192.168.0.0/24',
                gateway='192.168.0.1',
                type='MAC_FILTERED',
                dhcp=True).items():
            print('\tdelete %s to avoid max net limit' % n1id)
            self._delete_network(n1id)
            kwargs = {param: val}
            print('\twith %s=%s' % (param, val))
            self.network1 = self._create_network(self.netname1, **kwargs)
            n1id = self.network1['id']
            self._wait_for_network(n1id, 'ACTIVE')
            self.network1 = self.client.get_network_details(n1id)
            self.assertEqual(self.network1[param], val)

    def test_connect_server(self):
        self.client.connect_server(self.server1['id'], self.network1['id'])
        self.assertTrue(self._wait_for_nic(
            self.network1['id'],
            self.server1['id']))

    def test_disconnect_server(self):
        self.client.disconnect_server(self.server1['id'], self.network1['id'])
        self.assertTrue(self._wait_for_nic(
            self.network1['id'],
            self.server1['id'],
            in_creation=False))

    def _test_0260_wait_for_second_network(self):
        self.server1 = self._create_server(
            self.servname1,
            self.flavorid,
            self.img)
        self.network2 = self._create_network(self.netname2)
        self._wait_for_status(self.server1['id'], 'BUILD')
        self._wait_for_network(self.network2['id'], 'ACTIVE')
        self._test_0280_list_server_nics()

    def _test_0280_list_server_nics(self):
        r = self.client.list_server_nics(self.server1['id'])
        len0 = len(r)
        self.client.connect_server(self.server1['id'], self.network2['id'])
        self.assertTrue(self._wait_for_nic(
            self.network2['id'],
            self.server1['id']))
        r = self.client.list_server_nics(self.server1['id'])
        self.assertTrue(len(r) > len0)

    def test_list_networks(self):
        r = self.client.list_networks()
        self.assertTrue(len(r) > 1)
        ids = [net['id'] for net in r]
        names = [net['name'] for net in r]
        self.assertTrue('1' in ids)
        #self.assertTrue('public' in names)
        self.assertTrue(self.network1['id'] in ids)
        self.assertTrue(self.network1['name'] in names)

        r = self.client.list_networks(detail=True)
        ids = [net['id'] for net in r]
        names = [net['name'] for net in r]
        for net in r:
            self.assertTrue(net['id'] in ids)
            self.assertTrue(net['name'] in names)
            for term in ('status', 'updated', 'created'):
                self.assertTrue(term in net.keys())

    def test_get_network_details(self):
        r = self.client.get_network_details(self.network1['id'])
        net1 = dict(self.network1)
        net1.pop('status')
        net1.pop('updated', None)
        net1.pop('attachments')
        r.pop('status')
        r.pop('updated', None)
        r.pop('attachments')
        self.assert_dicts_are_equal(net1, r)

    def test_update_network_name(self):
        updated_name = self.netname2 + '_upd'
        self.client.update_network_name(self.network2['id'], updated_name)

        def netwait(wait):
            r = self.client.get_network_details(self.network2['id'])
            if r['name'] == updated_name:
                return
            time.sleep(wait)
        self.do_with_progress_bar(
            netwait,
            'Network %s name is changing:' % self.network2['id'],
            self._waits[:5])

        r = self.client.get_network_details(self.network2['id'])
        self.assertEqual(r['name'], updated_name)

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
