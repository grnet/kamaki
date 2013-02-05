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

from kamaki.clients import tests
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
        print
        for netid in self.networks.keys():
            self._delete_network(netid)
        if 0 >= len(self.servers):
            return
        print('-> Found %s servers to delete' % len(self.servers))
        for server in self.servers.values():
            self._delete_server(server['id'])

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
        self.client.delete_server(servid)
        self._wait_for_status(servid, current_state)

    def _create_network(self, netname, **kwargs):
        net = self.client.create_network(netname, **kwargs)
        self.networks[net['id']] = net
        return net

    def _delete_network(self, netid):
        sys.stdout.write('\tDelete network %s ' % netid)
        self.client.disconnect_network_nics(netid)
        wait = 3
        while True:
            try:
                self.client.delete_network(netid)
                print('\n\tSUCCESFULL COMMIT delete network %s' % netid)
                break
            except ClientError as err:
                self.assertEqual(err.status, 421)
                time.sleep(wait)
                wait += 3
                sys.stdout.write('.')
