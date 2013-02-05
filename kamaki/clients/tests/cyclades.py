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
from progress.bar import ShadyBar

from kamaki.clients import tests, ClientError
from kamaki.clients.cyclades import CycladesClient


class Cyclades(tests.Generic):
    """Set up a Cyclades thorough test"""
    def setUp(self):

        """okeanos"""
        self.img = 'b2dffe52-64a4-48c3-8a4c-8214cc3165cf'
        self.img_details = {
            u'status': u'ACTIVE',
            u'updated': u'2012-11-19T13:52:16+00:00',
            u'name': u'Debian Base',
            u'created': u'2012-10-16T09:03:12+00:00',
            u'progress': 100,
            u'id': self.img,
            u'metadata': {
                u'values': {
                    u'kernel': u'2.6.32',
                    u'osfamily': u'linux',
                    u'users': u'root',
                    u'gui': u'No GUI',
                    u'sortorder': u'1',
                    u'os': u'debian',
                    u'root_partition': u'1',
                    u'description': u'Debian 6.0.6 (Squeeze) Base System'}
                }
            }
        self.flavor_details = {u'name': u'C1R1024D20',
            u'ram': 1024,
            u'id': 1,
            u'SNF:disk_template': u'drbd',
            u'disk': 20,
            u'cpu': 1}
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
        pass

    def tearDown(self):
        """Destoy servers used in testing"""
        self.do_with_progress_bar(
            self._delete_network,
            'Delete %s networks' % len(self.networks),
            self.networks.keys())
        server_list = [server['id'] for server in self.servers.values()]
        self.do_with_progress_bar(
            self._delete_server,
            'Delete %s servers %s' % (len(server_list), server_list),
            server_list)

    def _create_server(self, servername, flavorid, imageid, personality=None):
        server = self.client.create_server(servername,
            flavorid,
            imageid,
            personality)
        self.servers[servername] = server
        return server

    def _delete_server(self, servid):
        try:
            current_state = self.client.get_server_details(servid)
            current_state = current_state['status']
            if current_state == 'DELETED':
                return
        except:
            return
        self._wait_for_status(servid, current_state)
        self.client.delete_server(servid)

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

    def test_list_servers(self):
        """Test list servers"""
        self.server1 = self._create_server(
            self.servname1,
            self.flavorid,
            self.img)
        return
        self.server2 = self._create_server(
            self.servname2,
            self.flavorid + 2,
            self.img)
        self._test_list_servers()

    def _test_list_servers(self):
        servers = self.client.list_servers()
        dservers = self.client.list_servers(detail=True)

        """detailed and simple are same size"""
        self.assertEqual(len(dservers), len(servers))
        for i in range(len(servers)):
            for field in ('created',
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
