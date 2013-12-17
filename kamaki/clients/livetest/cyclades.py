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

from kamaki.clients import livetest, ClientError
from kamaki.clients.cyclades import CycladesClient
from kamaki.clients.astakos import AstakosClient


class Cyclades(livetest.Generic):
    """Set up a Cyclades test"""
    def setUp(self):
        print
        with open(self['cmpimage', 'details']) as f:
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
        self.flavorid = self._flavor_details['id']
        #servers have to be created at the begining...
        self.networks = {}
        self.netname1 = 'net' + unicode(self.now)
        self.netname2 = 'net' + unicode(self.now) + '_v2'

        self.cloud = 'cloud.%s' % self['testcloud']
        aurl, self.token = self[self.cloud, 'url'], self[self.cloud, 'token']
        self.auth_base = AstakosClient(aurl, self.token)
        curl = self.auth_base.get_service_endpoints('compute')['publicURL']
        self.client = CycladesClient(curl, self.token)

    def tearDown(self):
        """Destoy servers used in testing"""
        for net in self.networks.keys():
            self._delete_network(net)
        for server in self.servers.values():
            self._delete_server(server['id'])
            print('DEL VM %s (%s)' % (server['id'], server['name']))

    def test_000(self):
        "Prepare a full Cyclades test scenario"
        self.server1 = self._create_server(
            self.servname1, self.flavorid, self.img)
        self.server2 = self._create_server(
            self.servname2, self.flavorid, self.img)
        super(self.__class__, self).test_000()

    def _create_server(self, servername, flavorid, imageid, personality=None):
        server = self.client.create_server(
            servername, flavorid, imageid, personality=personality)
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
        if not netid in self.networks:
            return None
        print('Disconnect nics of network %s' % netid)
        self.client.disconnect_network_nics(netid)

        def netwait(wait):
            try:
                self.client.delete_network(netid)
            except ClientError:
                time.sleep(wait)
        self.do_with_progress_bar(
            netwait,
            'Delete network %s' % netid,
            self._waits[:7])
        return self.networks.pop(netid)

    def _wait_for_network(self, netid, status):

        def netwait(wait):
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

        def nicwait(wait):
            nics = self.client.list_server_nics(servid)
            for net in nics:
                found_nic = net['network_id'] == netid
                if (in_creation and found_nic) or not (
                        in_creation or found_nic):
                    return
            time.sleep(wait)
        self.do_with_progress_bar(
            nicwait,
            'Wait nic-%s-%s to %sconnect' % (
                netid,
                servid,
                '' if in_creation else 'dis'),
            self._waits[:5])
        for net in self.client.list_server_nics(servid):
            if netid == net['network_id']:
                return True
        return False

    def _has_status(self, servid, status):
        r = self.client.get_server_details(servid)
        #print 'MY ', servid, ' STATUS IS ', r['status']
        return r['status'] == status

    def _wait_for_status(self, servid, status):
        (wait_bar, wait_cb) = self._safe_progress_bar(
            'Server %s in %s' % (servid, status))
        self.client.wait_server(
            servid, status, wait_cb=wait_cb, delay=2, max_wait=198)
        self._safe_progress_bar_finish(wait_bar)

    def test_parallel_creation(self):
        """test create with multiple threads
        Do not use this in regular livetest
        """
        from kamaki.clients import SilentEvent
        c = []
        for i in range(8):
            sname = '%s_%s' % (self.servname1, i)
            c.append(SilentEvent(
                self._create_server, sname, self.flavorid, self.img))
        for i in range(8):
            c[i].start()

    def test_create_server(self):
        """Test create_server"""
        self.server1 = self._create_server(
            self.servname1, self.flavorid, self.img)
        self._wait_for_status(self.server1['id'], 'BUILD')
        self._test_0010_create_server()

    def _test_0010_create_server(self):
        self.assertEqual(self.server1["name"], self.servname1)
        self.assertEqual(self.server1["flavor"]["id"], self.flavorid)
        self.assertEqual(self.server1["image"]["id"], self.img)
        self.assertEqual(self.server1["status"], "BUILD")

    def test_list_servers(self):
        """Test list servers"""
        self.server1 = self._create_server(
            self.servname1, self.flavorid, self.img)
        self.server2 = self._create_server(
            self.servname2, self.flavorid, self.img)
        self._test_0020_list_servers()

    def _test_0020_list_servers(self):
        servers = self.client.list_servers()
        dservers = self.client.list_servers(detail=True)

        """detailed and simple are same size"""
        self.assertEqual(len(dservers), len(servers))
        fields = set([
            'created', 'flavor', 'hostId', 'image', 'progress', 'status',
            'updated'])
        for i, srv in enumerate(servers):
            self.assertTrue(fields.isdisjoint(srv))
            self.assertTrue(fields.issubset(dservers[i]))

        """detailed and simple contain same names"""
        names = sorted(map(lambda x: x["name"], servers))
        dnames = sorted(map(lambda x: x["name"], dservers))
        self.assertEqual(names, dnames)

    def _test_0030_wait_test_servers_to_build(self):
        """Pseudo-test to wait for VMs to load"""
        print('')
        self._wait_for_status(self.server1['id'], 'BUILD')
        self._wait_for_status(self.server2['id'], 'BUILD')

    def test_get_server_details(self):
        """Test get_server_details"""
        self.server1 = self._create_server(
            self.servname1, self.flavorid, self.img)
        self._wait_for_status(self.server1['id'], 'BUILD')
        self._test_0040_get_server_details()

    def _test_0040_get_server_details(self):
        r = self.client.get_server_details(self.server1['id'])
        self.assertEqual(r["name"], self.servname1)
        self.assertEqual(r["flavor"]["id"], self.flavorid)
        self.assertEqual(r["image"]["id"], self.img)
        self.assertEqual(r["status"], "ACTIVE")

    def test_update_server_name(self):
        """Test update_server_name"""
        self.server1 = self._create_server(
            self.servname1, self.flavorid, self.img)
        self._test_0050_update_server_name()

    def _test_0050_update_server_name(self):
        new_name = self.servname1 + '_new_name'
        self.client.update_server_name(self.server1['id'], new_name)
        r = self.client.get_server_details(
            self.server1['id'], success=(200, 400))
        self.assertEqual(r['name'], new_name)
        changed = self.servers.pop(self.servname1)
        changed['name'] = new_name
        self.servers[new_name] = changed

    def test_reboot_server(self):
        """Test reboot server"""
        self.server1 = self._create_server(
            self.servname1, self.flavorid, self.img)
        self._wait_for_status(self.server1['id'], 'BUILD')
        self.server2 = self._create_server(
            self.servname2, self.flavorid + 2, self.img)
        self._wait_for_status(self.server2['id'], 'BUILD')
        self._test_0060_reboot_server()
        self._wait_for_status(self.server1['id'], 'REBOOT')
        self._wait_for_status(self.server2['id'], 'REBOOT')

    def _test_0060_reboot_server(self):
        self.client.reboot_server(self.server1['id'])
        self.assertTrue(self._has_status(self.server1['id'], 'REBOOT'))
        self.client.reboot_server(self.server2['id'], hard=True)
        self.assertTrue(self._has_status(self.server2['id'], 'REBOOT'))

    def test_resize_server(self):
        """Modify the flavor of a server"""
        self.server1 = self._create_server(
            self.servname1, self.flavorid, self.img)
        self._test_0065_resize_server()
        self.delete_server(self.server1['id'])
        self.server1 = self._create_server(
            self.servname1, self.flavorid, self.img)

    def _test_0065_resize_server(self):
        self.client.resize_server(self.servname1, self.flavorid + 2)
        srv = self.client.get_flavor_details(self.server1['id'])
        self.assertEqual(srv['flavor']['id'], self.flavorid + 2)

    def _test_0070_wait_test_servers_to_reboot(self):
        """Pseudo-test to wait for VMs to load"""
        print('')
        self._wait_for_status(self.server1['id'], 'REBOOT')
        self._wait_for_status(self.server2['id'], 'REBOOT')

    def test_create_server_metadata(self):
        """Test create_server_metadata"""
        self.server1 = self._create_server(
            self.servname1, self.flavorid, self.img)
        self._test_0080_create_server_metadata()

    def _test_0080_create_server_metadata(self):
        r1 = self.client.create_server_metadata(
            self.server1['id'], 'mymeta', 'mymeta val')
        self.assertTrue('mymeta' in r1)
        r2 = self.client.get_server_metadata(self.server1['id'], 'mymeta')
        self.assert_dicts_are_equal(r1, r2)

    def test_get_server_metadata(self):
        """Test get server_metadata"""
        self.server1 = self._create_server(
            self.servname1, self.flavorid, self.img)
        self._test_0090_get_server_metadata()

    def _test_0090_get_server_metadata(self):
        self.client.update_server_metadata(
            self.server1['id'], mymeta_0='val_0')
        r = self.client.get_server_metadata(self.server1['id'], 'mymeta_0')
        self.assertEqual(r['mymeta_0'], 'val_0')

    def test_update_server_metadata(self):
        """Test update_server_metadata"""
        self.server1 = self._create_server(
            self.servname1, self.flavorid, self.img)
        self._test_0100_update_server_metadata()

    def _test_0100_update_server_metadata(self):
        r1 = self.client.update_server_metadata(
            self.server1['id'], mymeta3='val2')
        self.assertTrue('mymeta3'in r1)
        r2 = self.client.update_server_metadata(
            self.server1['id'], mymeta3='val3')
        self.assertTrue(r2['mymeta3'], 'val3')

    def test_delete_server_metadata(self):
        """Test delete_server_metadata"""
        self.server1 = self._create_server(
            self.servname1, self.flavorid, self.img)
        self._test_0110_delete_server_metadata()

    def _test_0110_delete_server_metadata(self):
        r1 = self.client.update_server_metadata(
            self.server1['id'], mymeta='val')
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
        self.assert_dicts_are_equal(self._flavor_details, r)

    #def test_list_images(self):
    #    """Test list_images"""
    #    self._test_0140_list_images()

    def _test_0140_list_images(self):
        r = self.client.list_images()
        self.assertTrue(len(r) > 1)
        r = self.client.list_images(detail=True)
        for detailed_img in r:
            if detailed_img['id'] == self.img:
                break
        self.assert_dicts_are_equal(detailed_img, self.img_details)

    def test_get_image_details(self):
        """Test image_details"""
        self._test_0150_get_image_details()

    def _test_0150_get_image_details(self):
        r = self.client.get_image_details(self.img)
        self.assert_dicts_are_equal(r, self.img_details)

    def test_get_image_metadata(self):
        """Test get_image_metadata"""
        self._test_0160_get_image_metadata()

    def _test_0160_get_image_metadata(self):
        r = self.client.get_image_metadata(self.img)
        self.assert_dicts_are_equal(
            self.img_details['properties'], r)
        for key, val in self.img_details['properties'].items():
            r = self.client.get_image_metadata(self.img, key)
            self.assertEqual(r[key], val)

    def test_shutdown_server(self):
        """Test shutdown_server"""
        self.server1 = self._create_server(
            self.servname1, self.flavorid, self.img)
        self._wait_for_status(self.server1['id'], 'BUILD')
        self._test_0170_shutdown_server()

    def _test_0170_shutdown_server(self):
        self.client.shutdown_server(self.server1['id'])
        self._wait_for_status(self.server1['id'], 'ACTIVE')
        r = self.client.get_server_details(self.server1['id'])
        self.assertEqual(r['status'], 'STOPPED')

    def test_start_server(self):
        """Test start_server"""
        self.server1 = self._create_server(
            self.servname1, self.flavorid, self.img)
        self._wait_for_status(self.server1['id'], 'BUILD')
        self.client.shutdown_server(self.server1['id'])
        self._wait_for_status(self.server1['id'], 'ACTIVE')
        self._test_0180_start_server()

    def _test_0180_start_server(self):
        self.client.start_server(self.server1['id'])
        self._wait_for_status(self.server1['id'], 'STOPPED')
        r = self.client.get_server_details(self.server1['id'])
        self.assertEqual(r['status'], 'ACTIVE')

    def test_get_server_console(self):
        """Test get_server_console"""
        self.server2 = self._create_server(
            self.servname2, self.flavorid, self.img)
        self._wait_for_status(self.server2['id'], 'BUILD')
        self._test_0190_get_server_console()

    def _test_0190_get_server_console(self):
        r = self.client.get_server_console(self.server2['id'])
        self.assertTrue('host' in r)
        self.assertTrue('password' in r)
        self.assertTrue('port' in r)
        self.assertTrue('type' in r)

    def test_get_firewall_profile(self):
        """Test get_firewall_profile"""
        self.server1 = self._create_server(
            self.servname1, self.flavorid, self.img)
        self._test_0200_get_firewall_profile()

    def _test_0200_get_firewall_profile(self):
        self._wait_for_status(self.server1['id'], 'BUILD')
        fprofile = self.client.get_firewall_profile(self.server1['id'])
        self.assertTrue(fprofile in self.PROFILES)

    def test_set_firewall_profile(self):
        """Test set_firewall_profile"""
        self.server1 = self._create_server(
            self.servname1, self.flavorid, self.img)
        self._test_0210_set_firewall_profile()

    def _test_0210_set_firewall_profile(self):

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
        self.server1 = self._create_server(
            self.servname1, self.flavorid, self.img)
        self._test_0220_get_server_stats()

    def _test_0220_get_server_stats(self):
        r = self.client.get_server_stats(self.server1['id'])
        it = ('cpuBar', 'cpuTimeSeries', 'netBar', 'netTimeSeries', 'refresh')
        for term in it:
            self.assertTrue(term in r)

    def test_create_network(self):
        """Test create_network"""
        self._test_0230_create_network()

    def _test_0230_create_network(self):
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
        full_args = dict(
                cidr='192.168.1.0/24',
                gateway='192.168.1.1',
                type='MAC_FILTERED',
                dhcp=True)
        try_args = dict(all=True)
        try_args.update(full_args)
        for param, val in try_args.items():
            print('\tdelete %s to avoid max net limit' % n1id)
            self._delete_network(n1id)
            kwargs = full_args if param == 'all' else {param: val}
            print('\twith %s=%s' % (param, val))
            self.network1 = self._create_network(self.netname1, **kwargs)
            n1id = self.network1['id']
            self._wait_for_network(n1id, 'ACTIVE')
            self.network1 = self.client.get_network_details(n1id)
            if param == 'all':
                for p, v in full_args.items():
                    self.assertEqual(self.network1[p], v)
            else:
                self.assertEqual(self.network1[param], val)

    def test_connect_server(self):
        """Test connect_server"""
        self.server1 = self._create_server(
            self.servname1, self.flavorid, self.img)
        self.network1 = self._create_network(self.netname1)
        self._wait_for_status(self.server1['id'], 'BUILD')
        self._wait_for_network(self.network1['id'], 'ACTIVE')
        self._test_0240_connect_server()

    def _test_0250_connect_server(self):
        self.client.connect_server(self.server1['id'], self.network1['id'])
        self.assertTrue(
            self._wait_for_nic(self.network1['id'], self.server1['id']))

    def test_disconnect_server(self):
        """Test disconnect_server"""
        self.test_connect_server()
        self._test_0250_disconnect_server()

    def _test_0250_disconnect_server(self):
        self.client.disconnect_server(self.server1['id'], self.network1['id'])
        self.assertTrue(self._wait_for_nic(
            self.network1['id'], self.server1['id'], in_creation=False))

    def _test_0260_wait_for_second_network(self):
        self.network2 = self._create_network(self.netname2)
        self._wait_for_network(self.network2['id'], 'ACTIVE')

    def test_list_server_nics(self):
        """Test list_server_nics"""
        self.server1 = self._create_server(
            self.servname1, self.flavorid, self.img)
        self.network2 = self._create_network(self.netname2)
        self._wait_for_status(self.server1['id'], 'BUILD')
        self._wait_for_network(self.network2['id'], 'ACTIVE')
        self._test_0280_list_server_nics()

    def _test_0280_list_server_nics(self):
        r = self.client.list_server_nics(self.server1['id'])
        len0 = len(r)
        self.client.connect_server(self.server1['id'], self.network2['id'])
        self.assertTrue(
            self._wait_for_nic(self.network2['id'], self.server1['id']))
        r = self.client.list_server_nics(self.server1['id'])
        self.assertTrue(len(r) > len0)

    def test_list_networks(self):
        """Test list_network"""
        self.network1 = self._create_network(self.netname1)
        self._wait_for_network(self.network1['id'], 'ACTIVE')
        self._test_0290_list_networks()

    def _test_0290_list_networks(self):
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

    def test_list_network_nics(self):
        """Test list_server_nics"""
        self.server1 = self._create_server(
            self.servname1, self.flavorid, self.img)
        self.network1 = self._create_network(self.netname1)
        self.network2 = self._create_network(self.netname2)
        self._wait_for_status(self.server1['id'], 'BUILD')
        self._wait_for_network(self.network1['id'], 'ACTIVE')
        self._wait_for_network(self.network2['id'], 'ACTIVE')
        self.client.connect_server(self.server1['id'], self.network1['id'])
        self.client.connect_server(self.server1['id'], self.network2['id'])
        self._wait_for_nic(self.network1['id'], self.server1['id'])
        self._wait_for_nic(self.network2['id'], self.server1['id'])
        self._test_0293_list_network_nics()

    def _test_0293_list_network_nics(self):
        netid1, netid2 = self.network1['id'], self.network2['id']
        r = self.client.list_network_nics(netid1)
        expected = ['nic-%s-1' % self.server1['id']]
        self.assertEqual(r, expected)
        r = self.client.list_network_nics(netid2)
        expected = ['nic-%s-2' % self.server1['id']]
        self.assertEqual(r, expected)

    def test_get_network_details(self):
        """Test get_network_details"""
        self.network1 = self._create_network(self.netname1)
        self._test_0300_get_network_details()

    def _test_0300_get_network_details(self):
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
        self.network2 = self._create_network(self.netname2)
        self._test_0310_update_network_name()

    def _test_0310_update_network_name(self):
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

    """ Don't have auth to test this
    def test_delete_image(self):
        ""Test delete_image""
        self._test_0330_delete_image()
    def _test_0330_delete_image(self):
        images = self.client.list_images()
        self.client.delete_image(images[2]['id'])
        try:
            r = self.client.get_image_details(images[2]['id'], success=(400))
        except ClientError as err:
            self.assertEqual(err.status, 404)

    def test_create_image_metadata(self):
        ""Test create_image_metadata""
        self._test_0340_create_image_metadata()
    def _test_0340_create_image_metadata(self):
        r = self.client.create_image_metadata(self.img, 'mykey', 'myval')
        self.assertEqual(r['mykey'], 'myval')

    def test_update_image_metadata(self):
        ""Test update_image_metadata""
        self._test_0350_update_image_metadata()
    def _test_0350_update_image_metadata(self):
        r = self.client.create_image_metadata(self.img, 'mykey0', 'myval')
        r = self.client.update_image_metadata(self.img, 'mykey0', 'myval0')
        self.assertEqual(r['mykey0'], 'myval0')

    def test_delete_image_metadata(self):
        ""Test delete_image_metadata""
        self._test_0360_delete_image_metadata()
    def _test_0360_delete_image_metadata(self):
        self.client.create_image_metadata(self.img, 'mykey1', 'myval1')
        self.client.delete_image_metadata(self.img, 'mykey1')
        r = self.client.get_image_metadata(self.img)
        self.assertNotEqual('mykey1' in r)
    """
