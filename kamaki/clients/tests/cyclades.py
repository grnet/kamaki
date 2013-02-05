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

import time

from kamaki.clients import tests, ClientError
from kamaki.clients.cyclades import CycladesClient


class Cyclades(tests.Generic):
    """Set up a Cyclades thorough test"""
    def setUp(self):
        print
        with open(self['image', 'details']) as f:
            self.img_details = eval(f.read())
        self.img = self.img_details['id']
        with open(self['flavor', 'details']) as f:
            self._flavor_details = eval(f.read())
        self.PROFILES = ('ENABLED', 'DISABLED', 'PROTECTED')

        self.servers = {}
        self.now = time.mktime(time.gmtime())
        self.servname1 = 'serv' + unicode(self.now)
        self.servname2 = self.servname1 + '_v2'
        self.servname1 += '_v1'
        self.flavorid = 1
        #servers have to be created at the begining...
        self.networks = {}
        self.netname1 = 'net' + unicode(self.now)
        self.netname2 = 'net' + unicode(self.now) + '_v2'

        self.client = CycladesClient(self['compute', 'url'], self['token'])

    def tearDown(self):
        """Destoy servers used in testing"""
        self.do_with_progress_bar(
            self._delete_network,
            'Delete %s networks' % len(self.networks),
            self.networks.keys())
        for server in self.servers.values():
            self._delete_server(server['id'])
            print('DEL VM %s (%s)' % (server['id'], server['name']))

    def test_000(self):
        "Prepare a full Cyclades test scenario"
        self.server1 = self._create_server(self.servname1,
            self.flavorid,
            self.img)
        self.server2 = self._create_server(self.servname2,
            self.flavorid + 2,
            self.img)
        super(self.__class__, self).test_000()

    def _create_server(self, servername, flavorid, imageid, personality=None):
        server = self.client.create_server(servername,
            flavorid,
            imageid,
            personality)
        print('CREATE VM %s (%s)' % (server['id'], server['name']))
        self.servers[servername] = server
        return server

    def _delete_server(self, servid):
        try:
            current_state = self.client.get_server_details(servid)
            current_state = current_state['status']
            if current_state == 'DELETED':
                return
            self.client.delete_server(servid)
            self._wait_for_status(servid, current_state)
            self.client.delete_server(servid)
        except:
            return

    def _create_network(self, netname, **kwargs):
        net = self.client.create_network(netname, **kwargs)
        self.networks[net['id']] = net
        return net

    def _delete_network(self, netid):
        print('Disconnect nics of network %s' % netid)
        self.client.disconnect_network_nics(netid)

        def netwait(self, wait):
            try:
                self.client.delete_network(netid)
            except ClientError:
                time.sleep(wait)
        self.do_with_progress_bar(
            netwait,
            'Delete network %s' % netid,
            self._waits[:5])

    def _wait_for_network(self, netid, status):

        def netwait(self, wait):
            r = self.client.get_network_details(netid)
            if r['status'] == status:
                return
            time.sleep(wait)
        self.do_with_progress_bar(
            netwait,
            'Wait network %s to reach status %s' % (netid, status),
            self._waits[:5])

    def _wait_for_nic(self, netid, servid, in_creation=True):
        self._wait_for_network(netid, 'ACTIVE')

        def nicwait(self, wait):
            nics = self.client.list_server_nics(servid)
            for net in nics:
                found_nic = net['network_id'] == netid
                if (in_creation and found_nic)\
                or not (in_creation or found_nic):
                    return
            time.sleep(wait)
        self.do_with_progress_bar(
            nicwait,
            'Wait nic-%s-%s to %sconnect' % (
                netid,
                servid,
                '' if in_creation else 'dis'),
            self._waits[:5])

    def _has_status(self, servid, status):
        r = self.client.get_server_details(servid)
        return r['status'] == status

    def _wait_for_status(self, servid, status):
        (wait_bar, wait_cb) = self._safe_progress_bar(
            'Server %s in %s' % (servid, status))
        self.client.wait_server(servid, status, wait_cb=wait_cb)
        self._safe_progress_bar_finish(wait_bar)

    def test_parallel_creation(self):
        """test create with multiple threads
        Do not use this in regular tests
        """
        from kamaki.clients import SilentEvent
        c1 = SilentEvent(self._create_server,
            self.servname1,
            self.flavorid,
            self.img)
        c2 = SilentEvent(self._create_server,
            self.servname2,
            self.flavorid + 2,
            self.img)
        c3 = SilentEvent(self._create_server,
            self.servname1,
            self.flavorid,
            self.img)
        c4 = SilentEvent(self._create_server,
            self.servname2,
            self.flavorid + 2,
            self.img)
        c5 = SilentEvent(self._create_server,
            self.servname1,
            self.flavorid,
            self.img)
        c6 = SilentEvent(self._create_server,
            self.servname2,
            self.flavorid + 2,
            self.img)
        c7 = SilentEvent(self._create_server,
            self.servname1,
            self.flavorid,
            self.img)
        c8 = SilentEvent(self._create_server,
            self.servname2,
            self.flavorid + 2,
            self.img)
        c1.start()
        c2.start()
        c3.start()
        c4.start()
        c5.start()
        c6.start()
        c7.start()
        c8.start()

    def test_create_server(self):
        """Test create_server"""
        self.server1 = self._create_server(self.servname1,
            self.flavorid,
            self.img)
        self._wait_for_status(self.server1['id'], 'BUILD')
        self._test_0010_create_server()

    def _test_0010_create_server(self):
        self.assertEqual(self.server1["name"], self.servname1)
        self.assertEqual(self.server1["flavorRef"], self.flavorid)
        self.assertEqual(self.server1["imageRef"], self.img)
        self.assertEqual(self.server1["status"], "BUILD")

    def test_list_servers(self):
        """Test list servers"""
        self.server1 = self._create_server(
            self.servname1,
            self.flavorid,
            self.img)
        self.server2 = self._create_server(
            self.servname2,
            self.flavorid + 2,
            self.img)
        self._test_0020_list_servers()

    def _test_0020_list_servers(self):
        servers = self.client.list_servers()
        dservers = self.client.list_servers(detail=True)

        """detailed and simple are same size"""
        self.assertEqual(len(dservers), len(servers))
        for i in range(len(servers)):
            for field in (
                'created',
                'flavorRef',
                'hostId',
                'imageRef',
                'progress',
                'status',
                'updated'):
                self.assertFalse(field in servers[i])
                self.assertTrue(field in dservers[i])

        """detailed and simple contain same names"""
        names = sorted(map(lambda x: x["name"], servers))
        dnames = sorted(map(lambda x: x["name"], dservers))
        self.assertEqual(names, dnames)

    def _test_0030_wait_test_servers_to_build(self):
        """Pseudo-test to wait for VMs to load"""
        from sys import stdout
        stdout.write('')
        stdout.flush()
        self._wait_for_status(self.server1['id'], 'BUILD')
        self._wait_for_status(self.server2['id'], 'BUILD')

    def test_get_server_details(self):
        """Test get_server_details"""
        self.server1 = self._create_server(self.servname1,
            self.flavorid,
            self.img)
        self._wait_for_status(self.server1['id'], 'BUILD')
        self._test_0040_get_server_details()

    def _test_0040_get_server_details(self):
        r = self.client.get_server_details(self.server1['id'])
        self.assertEqual(r["name"], self.servname1)
        self.assertEqual(r["flavorRef"], self.flavorid)
        self.assertEqual(r["imageRef"], self.img)
        self.assertEqual(r["status"], "ACTIVE")

    def test_update_server_name(self):
        """Test update_server_name"""
        self.server1 = self._create_server(self.servname1,
            self.flavorid,
            self.img)
        self._test_0050_update_server_name()

    def _test_0050_update_server_name(self):
        new_name = self.servname1 + '_new_name'
        self.client.update_server_name(self.server1['id'], new_name)
        r = self.client.get_server_details(self.server1['id'],
         success=(200, 400))
        self.assertEqual(r['name'], new_name)
        changed = self.servers.pop(self.servname1)
        changed['name'] = new_name
        self.servers[new_name] = changed

    def test_reboot_server(self):
        """Test reboot server"""
        self.server1 = self._create_server(self.servname1,
            self.flavorid,
            self.img)
        self._wait_for_status(self.server1['id'], 'BUILD')
        self.server2 = self._create_server(self.servname2,
            self.flavorid + 1,
            self.img)
        self._wait_for_status(self.server2['id'], 'BUILD')
        self._test_0060_reboot_server()
        self._wait_for_status(self.server1['id'], 'REBOOT')
        self._wait_for_status(self.server2['id'], 'REBOOT')

    def _test_0060_reboot_server(self):
        self.client.reboot_server(self.server1['id'])
        self.assertTrue(self._has_status(self.server1['id'], 'REBOOT'))
        self.client.reboot_server(self.server2['id'], hard=True)
        self.assertTrue(self._has_status(self.server2['id'], 'REBOOT'))

    def _test_0070_wait_test_servers_to_reboot(self):
        """Pseudo-test to wait for VMs to load"""
        from sys import stdout
        stdout.write('')
        stdout.flush()
        self._wait_for_status(self.server1['id'], 'REBOOT')
        self._wait_for_status(self.server2['id'], 'REBOOT')

    def test_create_server_metadata(self):
        """Test create_server_metadata"""
        self.server1 = self._create_server(self.servname1,
            self.flavorid,
            self.img)
        self._test_0080_create_server_metadata()

    def _test_0080_create_server_metadata(self):
        r1 = self.client.create_server_metadata(self.server1['id'],
            'mymeta',
            'mymeta val')
        self.assertTrue('mymeta' in r1)
        r2 = self.client.get_server_metadata(self.server1['id'], 'mymeta')
        self.assert_dicts_are_deeply_equal(r1, r2)

    def test_get_server_metadata(self):
        """Test get server_metadata"""
        self.server1 = self._create_server(self.servname1,
            self.flavorid,
            self.img)
        self._test_0090_get_server_metadata()

    def _test_0090_get_server_metadata(self):
        self.client.create_server_metadata(self.server1['id'],
            'mymeta_0',
            'val_0')
        r = self.client.get_server_metadata(self.server1['id'], 'mymeta_0')
        self.assertEqual(r['mymeta_0'], 'val_0')

    def test_update_server_metadata(self):
        """Test update_server_metadata"""
        self.server1 = self._create_server(self.servname1,
            self.flavorid,
            self.img)
        self._test_0100_update_server_metadata()

    def _test_0100_update_server_metadata(self):
        r1 = self.client.create_server_metadata(self.server1['id'],
            'mymeta3',
            'val2')
        self.assertTrue('mymeta3'in r1)
        r2 = self.client.update_server_metadata(self.server1['id'],
            mymeta3='val3')
        self.assertTrue(r2['mymeta3'], 'val3')

    def test_delete_server_metadata(self):
        """Test delete_server_metadata"""
        self.server1 = self._create_server(self.servname1,
            self.flavorid,
            self.img)
        self._test_0110_delete_server_metadata()

    def _test_0110_delete_server_metadata(self):
        r1 = self.client.create_server_metadata(self.server1['id'],
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
        """Test flavors_get"""
        self._test_0120_list_flavors()

    def _test_0120_list_flavors(self):
        r = self.client.list_flavors()
        self.assertTrue(len(r) > 1)
        r = self.client.list_flavors(detail=True)
        self.assertTrue('SNF:disk_template' in r[0])

    def test_get_flavor_details(self):
        """Test test_get_flavor_details"""
        self._test_0130_get_flavor_details()

    def _test_0130_get_flavor_details(self):
        r = self.client.get_flavor_details(self.flavorid)
        self.assert_dicts_are_deeply_equal(self._flavor_details, r)

    def test_list_images(self):
        """Test list_images"""
        self._test_0140_list_images()

    def _test_0140_list_images(self):
        r = self.client.list_images()
        self.assertTrue(len(r) > 1)
        r = self.client.list_images(detail=True)
        for detailed_img in r:
            if detailed_img['id'] == self.img:
                break
        self.assert_dicts_are_deeply_equal(detailed_img, self.img_details)

    def test_get_image_details(self):
        """Test image_details"""
        self._test_0150_get_image_details()

    def _test_0150_get_image_details(self):
        r = self.client.get_image_details(self.img)
        r.pop('updated')
        self.assert_dicts_are_deeply_equal(r, self.img_details)

    def test_get_image_metadata(self):
        """Test get_image_metadata"""
        self._test_0160_get_image_metadata()

    def _test_0160_get_image_metadata(self):
        r = self.client.get_image_metadata(self.img)
        self.assert_dicts_are_deeply_equal(
            self.img_details['metadata']['values'], r)
        for key, val in self.img_details['metadata']['values'].items():
            r = self.client.get_image_metadata(self.img, key)
            self.assertEqual(r[key], val)

    def test_shutdown_server(self):
        """Test shutdown_server"""
        self.server1 = self._create_server(self.servname1,
            self.flavorid,
            self.img)
        self._wait_for_status(self.server1['id'], 'BUILD')
        self._test_0170_shutdown_server()

    def _test_0170_shutdown_server(self):
        self.client.shutdown_server(self.server1['id'])
        self._wait_for_status(self.server1['id'], 'ACTIVE')
        r = self.client.get_server_details(self.server1['id'])
        self.assertEqual(r['status'], 'STOPPED')

    def test_start_server(self):
        """Test start_server"""
        self.server1 = self._create_server(self.servname1,
            self.flavorid,
            self.img)
        self._wait_for_status(self.server1['id'], 'BUILD')
        self.client.shutdown_server(self.server1['id'])
        self._wait_for_status(self.server1['id'], 'ACTIVE')
        self._test_0180_start_server()

    def _test_0180_start_server(self):
        self.client.start_server(self.server1['id'])
        self._wait_for_status(self.server1['id'], 'STOPPED')
        r = self.client.get_server_details(self.server1['id'])
        self.assertEqual(r['status'], 'ACTIVE')
