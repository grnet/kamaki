# Copyright 2011 GRNET S.A. All rights reserved.
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

from argparse import ArgumentParser
import unittest
import time
import datetime
import os
import sys
import tempfile
from logging import getLogger

kloger = getLogger('kamaki')

try:
    from progress.bar import FillingCirclesBar as IncrementalBar
except ImportError:
    kloger.warning('No progress bars in testing!')
    pass

from kamaki.clients import ClientError
from kamaki.clients.pithos import PithosClient as pithos
from kamaki.clients.cyclades import CycladesClient as cyclades
from kamaki.clients.image import ImageClient as image
from kamaki.clients.astakos import AstakosClient as astakos
from kamaki.cli.config import Config

TEST_ALL = False

cnf = Config()
global_username = None
token = None


def _init_cnf():
    global cnf
    global global_username
    global_username = cnf.get('test', 'account') or\
        cnf.get('global', 'account')
    global token
    token = cnf.get('test', 'token') or cnf.get('global', 'token')


class testAstakos(unittest.TestCase):
    def setUp(self):
        _init_cnf()
        global cnf
        url = cnf.get('test', 'astakos_url') or cnf.get('astakos', 'url')
        global token
        self.client = astakos(url, token)

    def tearDown(self):
        pass

    def test_authenticate(self):
        r = self.client.authenticate()
        for term in ('username',
            'auth_token_expires',
            'auth_token',
            'auth_token_created',
            'groups',
            'uniq',
            'has_credits',
            'has_signed_terms'):
            self.assertTrue(term in r)


class testImage(unittest.TestCase):
    def setUp(self):
        _init_cnf()
        global cnf
        cyclades_url = cnf.get('compute', 'url')
        url = cnf.get('image', 'url')
        global token
        self.token = token
        self.imgid = 'b2dffe52-64a4-48c3-8a4c-8214cc3165cf'
        self.now = time.mktime(time.gmtime())
        self.imgname = 'img_%s' % self.now
        global global_username
        self.imglocation = 'pithos://%s/pithos/my.img'\
        % global_username
        self.client = image(url, self.token)
        self.cyclades = cyclades(cyclades_url, self.token)
        self._imglist = {}

    def _prepare_img(self):
        global cnf
        global global_username
        username = global_username.split('@')[0]
        imglocalpath =\
        '/home/%s/src/kamaki-settings/files/centos.diskdump' % username
        f = open(imglocalpath, 'rb')
        pithcli = pithos(cnf.get('store', 'url'),
            self.token,
            global_username,
            'pithos')
        print('\t- Upload an image at %s...' % imglocalpath)
        pithcli.upload_object('my.img', f)
        print('\t- ok')
        f.close()

        self.client.register(self.imgname,
            self.imglocation,
            params=dict(is_public=True))
        img = self._get_img_by_name(self.imgname)
        self._imglist[self.imgname] = img

    def tearDown(self):
        for img in self._imglist.values():
            self.cyclades.delete_image(img['id'])

    def _get_img_by_name(self, name):
        r = self.cyclades.list_images()
        for img in r:
            if img['name'] == name:
                return img
        return None

    def assert_dicts_are_deeply_equal(self, d1, d2):
        for k, v in d1.items():
            self.assertTrue(k in d2)
            if isinstance(v, dict):
                self.assert_dicts_are_deeply_equal(v, d2[k])
            else:
                self.assertEqual(unicode(v), unicode(d2[k]))

    def test_list_public(self):
        """Test list_public"""
        r = self.client.list_public()
        r0 = self.client.list_public(order='-')
        self.assertTrue(len(r) > 0)
        for img in r:
            for term in ('status',
                'name',
                'container_format',
                'disk_format',
                'id',
                'size'):
                self.assertTrue(term in img)
        self.assertTrue(len(r), len(r0))
        r0.reverse()
        for i, img in enumerate(r):
            self.assert_dicts_are_deeply_equal(img, r0[i])
        r1 = self.client.list_public(detail=True)
        for img in r1:
            for term in ('status',
                'name',
                'checksum',
                'created_at',
                'disk_format',
                'updated_at',
                'id',
                'location',
                'container_format',
                'owner',
                'is_public',
                'deleted_at',
                'properties',
                'size'):
                self.assertTrue(term in img)
                for interm in (
                    'osfamily',
                    'users',
                    'os',
                    'root_partition',
                    'description'):
                    self.assertTrue(interm in img['properties'])
        size_max = 1000000000
        r2 = self.client.list_public(filters=dict(size_max=size_max))
        self.assertTrue(len(r2) <= len(r))
        for img in r2:
            self.assertTrue(int(img['size']) <= size_max)

    def test_get_meta(self):
        """Test get_meta"""
        r = self.client.get_meta(self.imgid)
        self.assertEqual(r['id'], self.imgid)
        for term in ('status',
            'name',
            'checksum',
            'updated-at',
            'created-at',
            'deleted-at',
            'location',
            'is-public',
            'owner',
            'disk-format',
            'size',
            'container-format'):
            self.assertTrue(term in r)
            for interm in ('kernel',
                'osfamily',
                'users',
                'gui', 'sortorder',
                'root-partition',
                'os',
                'description'):
                self.assertTrue(interm in r['properties'])

    def test_register(self):
        """Test register"""
        self._prepare_img()
        self.assertTrue(len(self._imglist) > 0)
        for img in self._imglist.values():
            self.assertTrue(img != None)

    def test_reregister(self):
        """Test reregister"""
        self._prepare_img()
        self.client.reregister(self.imglocation,
            properties=dict(my_property='some_value'))

    def test_set_members(self):
        """Test set_members"""
        self._prepare_img()
        members = ['%s@fake.net' % self.now]
        for img in self._imglist.values():
            self.client.set_members(img['id'], members)
            r = self.client.list_members(img['id'])
            self.assertEqual(r[0]['member_id'], members[0])

    def test_list_members(self):
        """Test list_members"""
        self.test_set_members()

    def test_remove_members(self):
        """Test remove_members - NO CHECK"""
        return
        self._prepare_img()
        members = ['%s@fake.net' % self.now, '%s_v2@fake.net' % self.now]
        for img in self._imglist.values():
            self.client.set_members(img['id'], members)
            r = self.client.list_members(img['id'])
            self.assertTrue(len(r) > 1)
            self.client.remove_member(img['id'], members[0])
            r0 = self.client.list_members(img['id'])
            self.assertEqual(len(r), 1 + len(r0))
            self.assertEqual(r0[0]['member_id'], members[1])

    def test_list_shared(self):
        """Test list_shared - NOT CHECKED"""
        #No way to test this, if I dont have member images
        pass


class testCyclades(unittest.TestCase):
    """Set up a Cyclades thorough test"""
    def setUp(self):
        """okeanos"""
        _init_cnf()
        global cnf
        url = cnf.get('compute', 'url')
        global token
        global global_username
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

        """okeanos.io """
        """
        self.img = 'b3e68235-3abd-4d60-adfe-1379a4f8d3fe'
        self.img_details = {
            u'status': u'ACTIVE',
            u'updated': u'2012-11-19T15:29:51+00:00',
            u'name': u'Debian Base',
            u'created': u'2012-11-19T14:54:57+00:00',
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
            """

        self.servers = {}
        self.now = time.mktime(time.gmtime())
        self.servname1 = 'serv' + unicode(self.now)
        self.servname2 = self.servname1 + '_v2'
        self.flavorid = 1
        #servers have to be created at the begining...
        self.networks = {}
        self.netname1 = 'net' + unicode(self.now)
        self.netname2 = 'net' + unicode(self.now) + '_v2'

        self.client = cyclades(url, token)
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

    def if_not_all(foo):
        global TEST_ALL
        if TEST_ALL:
            return None
        return foo

    def assert_dicts_are_deeply_equal(self, d1, d2):
        for k, v in d1.items():
            self.assertTrue(k in d2)
            if isinstance(v, dict):
                self.assert_dicts_are_deeply_equal(v, d2[k])
            else:
                self.assertEqual(unicode(v), unicode(d2[k]))

    def test_000(self):
        "Prepare a full Cyclades test scenario"
        global TEST_ALL
        TEST_ALL = True

        self.server1 = self._create_server(self.servname1,
            self.flavorid,
            self.img)
        self.server2 = self._create_server(self.servname2,
            self.flavorid + 2,
            self.img)

        print('testing')
        sys.stdout.write(' test create server')
        self._test_create_server()
        print('...ok')

        sys.stdout.write(' test list servers')
        self._test_list_servers()
        print('...ok')

        print('- wait for test servers to build')
        self._wait_for_status(self.server1['id'], 'BUILD')
        self._wait_for_status(self.server2['id'], 'BUILD')
        print('- ok')

        sys.stdout.write(' test get server details')
        self._test_get_server_details()
        print('...ok')

        sys.stdout.write(' test get image details')
        self._test_get_image_details()
        print('...ok')

        sys.stdout.write(' test update_server_name')
        self._test_update_server_name()
        print('...ok')

        sys.stdout.write(' test reboot_server')
        self._test_reboot_server()
        print('...ok')

        print('- wait for test servers to boot')
        self._wait_for_status(self.server1['id'], 'REBOOT')
        self._wait_for_status(self.server2['id'], 'REBOOT')
        print('- ok')

        sys.stdout.write(' test create_server_metadata')
        self._test_create_server_metadata()
        print('...ok')

        sys.stdout.write(' test get_server_metadata')
        self._test_get_server_metadata()
        print('...ok')

        sys.stdout.write(' test update_server_metadata')
        self._test_update_server_metadata()
        print('...ok')

        sys.stdout.write(' test delete_server_metadata')
        self._test_delete_server_metadata()
        print('...ok')

        sys.stdout.write(' test list_flavors')
        self._test_list_flavors()
        print('...ok')

        sys.stdout.write(' test get_flavor_details')
        self._test_get_flavor_details()
        print('...ok')

        sys.stdout.write(' test list_images')
        self._test_list_images()
        print('...ok')

        sys.stdout.write(' test get_image_details')
        self._test_get_image_details()
        print('...ok')

        sys.stdout.write(' test get_image_metadata')
        self._test_get_image_metadata()
        print('...ok')

        sys.stdout.write(' test shutdown_server')
        self._test_shutdown_server()
        print('...ok')

        sys.stdout.write(' test start_server')
        self._test_start_server()
        print('...ok')

        sys.stdout.write(' test get_server_console')
        self._test_get_server_console()
        print('...ok')

        sys.stdout.write(' test get_firewall_profile')
        self._test_get_firewall_profile()
        print('...ok')

        sys.stdout.write(' test set_firewall_profile')
        self._test_set_firewall_profile()
        print('...ok')

        sys.stdout.write(' test get_server_stats')
        self._test_get_server_stats()
        print('...ok')

        self.network1 = self._create_network(self.netname1)

        sys.stdout.write(' test create_network')
        self._test_create_network()
        print('...ok')

        print('- wait for network to be activated')
        self._wait_for_network(self.network1['id'], 'ACTIVE')
        print('- ok')

        sys.stdout.write(' test connect_server')
        self._test_connect_server()
        print('...ok')

        sys.stdout.write(' test disconnect_server')
        self._test_disconnect_server()
        print('...ok')

        self.network2 = self._create_network(self.netname2)
        print('- wait for network to be activated')
        self._wait_for_network(self.network2['id'], 'ACTIVE')
        print('- ok')

        sys.stdout.write(' test list_server_nics')
        self._test_list_server_nics()
        print('...ok')

        sys.stdout.write(' test list_networks')
        self._test_list_networks()
        print('...ok')

        sys.stdout.write(' test get_network_details')
        self._test_get_network_details()
        print('...ok')

        sys.stdout.write(' test update_network_name')
        self._test_update_network_name()
        print('...ok')

        """Don't have auth for these:
        sys.stdout.write(' test delete_image')
        self._test_delete_image()
        print('...ok')
        sys.stdout.write(' test create_image_metadata')
        self._test_create_image_metadata()
        print('...ok')
        sys.stdout.write(' test update_image_metadata')
        self._test_update_image_metadata()
        print('...ok')
        sys.stdout.write(' test delete_image_metadata')
        self._test_delete_image_metadata()
        print('...ok')
        """

    @if_not_all
    def test_parallel_creation(self):
        """test create with multiple threads"""
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

    def _wait_for_network(self, netid, status):
        wait = 3
        limit = 50
        c = ['|', '/', '-', '\\']
        sys.stdout.write('\t- make net %s %s  ' % (netid, status))
        while wait < limit:
            r = self.client.get_network_details(netid)
            if r['status'] == status:
                print('\tOK')
                return True
            sys.stdout.write('\tit is now %s, wait %ss  '\
                % (r['status'], wait))
            for i in range(wait * 4):
                sys.stdout.write('\b%s' % c[i % 4])
                sys.stdout.flush()
                time.sleep(0.25)
            print('\b ')
            wait += 3
        return False

    def _wait_for_nic(self, netid, servid, in_creation=True):
        self._wait_for_network(netid, 'ACTIVE')
        c = ['|', '/', '-', '\\']
        limit = 50
        wait = 3
        largetry = 0
        while wait < limit:
            nics = self.client.list_server_nics(servid)
            for net in nics:
                found_nic = net['network_id'] == netid
                if (in_creation and found_nic)\
                or not (in_creation or found_nic):
                    return True
            dis = '' if in_creation else 'dis'
            sys.stdout.write('\twait nic %s to %sconnect to %s: %ss  '\
                % (netid, dis, servid, wait))
            for i in range(wait * 4):
                sys.stdout.write('\b%s' % c[i % 4])
                sys.stdout.flush()
                time.sleep(0.25)
            print('\b ')
            wait += 3
            if wait >= limit and largetry < 3:
                wait = 3
                largetry += 1
        return False

    def _has_status(self, servid, status):
        r = self.client.get_server_details(servid)
        return r['status'] == status

    def _wait_for_status(self, servid, status):
        withbar = True
        try:
            wait_bar = IncrementalBar('\tServer[%s] in %s ' % (servid, status))
        except NameError:
            withbar = False

        wait_cb = None
        if withbar:
            wait_bar.start()

            def progress_gen(n):
                for i in wait_bar.iter(range(int(n))):
                    yield
                yield

            wait_cb = progress_gen

        time.sleep(0.5)
        self.client.wait_server(servid, status, wait_cb=wait_cb)
        if withbar:
            wait_bar.finish()

    @if_not_all
    def test_list_servers(self):
        """Test list servers"""
        self.server1 = self._create_server(self.servname1,
            self.flavorid,
            self.img)
        self.server2 = self._create_server(self.servname2,
            self.flavorid + 1,
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

    @if_not_all
    def test_create_server(self):
        """Test create_server"""
        self.server1 = self._create_server(self.servname1,
            self.flavorid,
            self.img)
        self._wait_for_status(self.server1['id'], 'BUILD')
        self._test_create_server()

    def _test_create_server(self):
        self.assertEqual(self.server1["name"], self.servname1)
        self.assertEqual(self.server1["flavorRef"], self.flavorid)
        self.assertEqual(self.server1["imageRef"], self.img)
        self.assertEqual(self.server1["status"], "BUILD")

    @if_not_all
    def test_get_server_details(self):
        """Test get_server_details"""
        self.server1 = self._create_server(self.servname1,
            self.flavorid,
            self.img)
        self._wait_for_status(self.server1['id'], 'BUILD')
        self._test_get_server_details()

    def _test_get_server_details(self):
        r = self.client.get_server_details(self.server1['id'])
        self.assertEqual(r["name"], self.servname1)
        self.assertEqual(r["flavorRef"], self.flavorid)
        self.assertEqual(r["imageRef"], self.img)
        self.assertEqual(r["status"], "ACTIVE")

    @if_not_all
    def test_update_server_name(self):
        """Test update_server_name"""
        self.server1 = self._create_server(self.servname1,
            self.flavorid,
            self.img)
        self._test_update_server_name()

    def _test_update_server_name(self):
        new_name = self.servname1 + '_new_name'
        self.client.update_server_name(self.server1['id'], new_name)
        r = self.client.get_server_details(self.server1['id'],
         success=(200, 400))
        self.assertEqual(r['name'], new_name)
        changed = self.servers.pop(self.servname1)
        changed['name'] = new_name
        self.servers[new_name] = changed

    @if_not_all
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
        self._test_reboot_server()
        self._wait_for_status(self.server1['id'], 'REBOOT')
        self._wait_for_status(self.server2['id'], 'REBOOT')

    def _test_reboot_server(self):
        self.client.reboot_server(self.server1['id'])
        self.assertTrue(self._has_status(self.server1['id'], 'REBOOT'))
        self.client.reboot_server(self.server2['id'], hard=True)
        self.assertTrue(self._has_status(self.server2['id'], 'REBOOT'))

    @if_not_all
    def test_get_server_metadata(self):
        """Test get server_metadata"""
        self.server1 = self._create_server(self.servname1,
            self.flavorid,
            self.img)
        self._test_get_server_metadata()

    def _test_get_server_metadata(self):
        self.client.create_server_metadata(self.server1['id'],
            'mymeta_0',
            'val_0')
        r = self.client.get_server_metadata(self.server1['id'], 'mymeta_0')
        self.assertEqual(r['mymeta_0'], 'val_0')

    @if_not_all
    def test_create_server_metadata(self):
        """Test create_server_metadata"""
        self.server1 = self._create_server(self.servname1,
            self.flavorid,
            self.img)
        self._test_create_server_metadata()

    def _test_create_server_metadata(self):
        r1 = self.client.create_server_metadata(self.server1['id'],
            'mymeta',
            'mymeta val')
        self.assertTrue('mymeta' in r1)
        r2 = self.client.get_server_metadata(self.server1['id'], 'mymeta')
        self.assert_dicts_are_deeply_equal(r1, r2)

    @if_not_all
    def test_update_server_metadata(self):
        """Test update_server_metadata"""
        self.server1 = self._create_server(self.servname1,
            self.flavorid,
            self.img)
        self._test_update_server_metadata()

    def _test_update_server_metadata(self):
        r1 = self.client.create_server_metadata(self.server1['id'],
            'mymeta3',
            'val2')
        self.assertTrue('mymeta3'in r1)
        r2 = self.client.update_server_metadata(self.server1['id'],
            mymeta3='val3')
        self.assertTrue(r2['mymeta3'], 'val3')

    @if_not_all
    def test_delete_server_metadata(self):
        """Test delete_server_metadata"""
        self.server1 = self._create_server(self.servname1,
            self.flavorid,
            self.img)
        self._test_delete_server_metadata()

    def _test_delete_server_metadata(self):
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

    @if_not_all
    def test_list_flavors(self):
        """Test flavors_get"""
        self._test_list_flavors()

    def _test_list_flavors(self):
        r = self.client.list_flavors()
        self.assertTrue(len(r) > 1)
        r = self.client.list_flavors(detail=True)
        self.assertTrue('SNF:disk_template' in r[0])

    @if_not_all
    def test_get_flavor_details(self):
        """Test test_get_flavor_details"""
        self._test_get_flavor_details()

    def _test_get_flavor_details(self):
        r = self.client.get_flavor_details(self.flavorid)
        self.assert_dicts_are_deeply_equal(self.flavor_details, r)

    @if_not_all
    def test_list_images(self):
        """Test list_images"""
        self._test_list_images()

    def _test_list_images(self):
        r = self.client.list_images()
        self.assertTrue(len(r) > 1)
        r = self.client.list_images(detail=True)
        for detailed_img in r:
            if detailed_img['id'] == self.img:
                break
        self.assert_dicts_are_deeply_equal(detailed_img, self.img_details)

    @if_not_all
    def test_get_image_details(self):
        """Test image_details"""
        self._test_get_image_details()

    def _test_get_image_details(self):
        r = self.client.get_image_details(self.img)
        r.pop('updated')
        self.assert_dicts_are_deeply_equal(r, self.img_details)

    @if_not_all
    def test_get_image_metadata(self):
        """Test get_image_metadata"""
        self._test_get_image_metadata()

    def _test_get_image_metadata(self):
        r = self.client.get_image_metadata(self.img)
        self.assert_dicts_are_deeply_equal(
            self.img_details['metadata']['values'], r)
        for key, val in self.img_details['metadata']['values'].items():
            r = self.client.get_image_metadata(self.img, key)
            self.assertEqual(r[key], val)

    @if_not_all
    def test_start_server(self):
        """Test start_server"""
        self.server1 = self._create_server(self.servname1,
            self.flavorid,
            self.img)
        self._wait_for_status(self.server1['id'], 'BUILD')
        self.client.shutdown_server(self.server1['id'])
        self._wait_for_status(self.server1['id'], 'ACTIVE')
        self._test_start_server()

    def _test_start_server(self):
        self.client.start_server(self.server1['id'])
        self._wait_for_status(self.server1['id'], 'STOPPED')
        r = self.client.get_server_details(self.server1['id'])
        self.assertEqual(r['status'], 'ACTIVE')

    @if_not_all
    def test_shutdown_server(self):
        """Test shutdown_server"""
        self.server1 = self._create_server(self.servname1,
            self.flavorid,
            self.img)
        self._wait_for_status(self.server1['id'], 'BUILD')
        self._test_shutdown_server()

    def _test_shutdown_server(self):
        self.client.shutdown_server(self.server1['id'])
        self._wait_for_status(self.server1['id'], 'ACTIVE')
        r = self.client.get_server_details(self.server1['id'])
        self.assertEqual(r['status'], 'STOPPED')

    @if_not_all
    def test_get_server_console(self):
        """Test get_server_console"""
        self.server2 = self._create_server(self.servname2,
            self.flavorid + 2,
            self.img)
        self._wait_for_status(self.server2['id'], 'BUILD')
        self._test_get_server_console()

    def _test_get_server_console(self):
        r = self.client.get_server_console(self.server2['id'])
        self.assertTrue('host' in r)
        self.assertTrue('password' in r)
        self.assertTrue('port' in r)
        self.assertTrue('type' in r)

    @if_not_all
    def test_get_firewall_profile(self):
        """Test get_firewall_profile"""
        self.server1 = self._create_server(self.servname1,
            self.flavorid,
            self.img)
        self._test_get_firewall_profile()

    def _test_get_firewall_profile(self):
        self._wait_for_status(self.server1['id'], 'BUILD')
        fprofile = self.client.get_firewall_profile(self.server1['id'])
        self.assertTrue(fprofile in self.PROFILES)

    @if_not_all
    def test_set_firewall_profile(self):
        """Test set_firewall_profile"""
        self.server1 = self._create_server(self.servname1,
            self.flavorid,
            self.img)
        self._test_set_firewall_profile()

    def _test_set_firewall_profile(self):

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

    @if_not_all
    def test_get_server_stats(self):
        self.server1 = self._create_server(self.servname1,
            self.flavorid,
            self.img)
        self._test_get_server_stats()

    def _test_get_server_stats(self):
        r = self.client.get_server_stats(self.server1['id'])
        for term in ('cpuBar',
        'cpuTimeSeries',
        'netBar',
        'netTimeSeries',
        'refresh'):
            self.assertTrue(term in r)

    @if_not_all
    def test_list_networks(self):
        """Test list_network"""
        self.network1 = self._create_network(self.netname1)
        self._wait_for_network(self.network1['id'], 'ACTIVE')
        self._test_list_networks()

    def _test_list_networks(self):
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

    @if_not_all
    def test_create_network(self):
        """Test create_network"""
        self.network1 = self._create_network(self.netname1)
        self._test_create_network()

    def _test_create_network(self):
        nets = self.client.list_networks(self.network1['id'])
        chosen = [net for net in nets if net['id'] == self.network1['id']][0]
        chosen.pop('updated')
        net1 = dict(self.network1)
        net1.pop('updated')
        self.assert_dicts_are_deeply_equal(chosen, net1)

    @if_not_all
    def test_connect_server(self):
        """Test connect_server"""
        self.server1 = self._create_server(self.servname1,
            self.flavorid,
            self.img)
        self.network1 = self._create_network(self.netname1)
        self._wait_for_status(self.server1['id'], 'BUILD')
        self._wait_for_network(self.network1['id'], 'ACTIVE')
        self._test_connect_server()

    def _test_connect_server(self):
        self.client.connect_server(self.server1['id'], self.network1['id'])
        self.assertTrue(self._wait_for_nic(self.network1['id'],
            self.server1['id']))

    @if_not_all
    def test_disconnect_server(self):
        """Test disconnect_server"""
        self.test_connect_server()
        self._test_disconnect_server()

    def _test_disconnect_server(self):
        self.client.disconnect_server(self.server1['id'], self.network1['id'])
        self.assertTrue(self._wait_for_nic(self.network1['id'],
            self.server1['id'],
            in_creation=False))

    @if_not_all
    def test_list_server_nics(self):
        """Test list_server_nics"""
        self.server1 = self._create_server(self.servname1,
            self.flavorid,
            self.img)
        self.network2 = self._create_network(self.netname2)
        self._wait_for_status(self.server1['id'], 'BUILD')
        self._wait_for_network(self.network2['id'], 'ACTIVE')
        self._test_list_server_nics()

    def _test_list_server_nics(self):
        r = self.client.list_server_nics(self.server1['id'])
        len0 = len(r)

        self.client.connect_server(self.server1['id'], self.network2['id'])
        self.assertTrue(self._wait_for_nic(self.network2['id'],
            self.server1['id']))
        r = self.client.list_server_nics(self.server1['id'])
        self.assertTrue(len(r) > len0)

    @if_not_all
    def test_get_network_details(self):
        """Test get_network_details"""
        self.network1 = self._create_network(self.netname1)
        self._test_get_network_details()

    def _test_get_network_details(self):
        r = self.client.get_network_details(self.network1['id'])
        net1 = dict(self.network1)
        net1.pop('status')
        net1.pop('updated', None)
        net1.pop('attachments')
        r.pop('status')
        r.pop('updated', None)
        r.pop('attachments')
        self.assert_dicts_are_deeply_equal(net1, r)

    @if_not_all
    def test_update_network_name(self):
        self.network2 = self._create_network(self.netname2)
        self._test_update_network_name()

    def _test_update_network_name(self):
        updated_name = self.netname2 + '_upd'
        self.client.update_network_name(self.network2['id'], updated_name)
        wait = 3
        c = ['|', '/', '-', '\\']
        r = self.client.get_network_details(self.network2['id'])
        while wait < 50:
            if r['name'] == updated_name:
                break
            sys.stdout.write(
                '\twait for %s renaming (%s->%s) %ss  ' % (self.network2['id'],
                self.network2['name'],
                updated_name, wait))
            for i in range(4 * wait):
                sys.stdout.write('\b%s' % c[i % 4])
                sys.stdout.flush()
                time.sleep(0.25)
            print('')
            wait += 3
            r = self.client.get_network_details(self.network2['id'])
        self.assertEqual(r['name'], updated_name)

    """ Don't have auth to test this
    @if_not_all
    def test_delete_image(self):
        ""Test delete_image""
        self._test_delete_image()
    def _test_delete_image(self):
        images = self.client.list_images()
        self.client.delete_image(images[2]['id'])
        try:
            r = self.client.get_image_details(images[2]['id'], success=(400))
        except ClientError as err:
            self.assertEqual(err.status, 404)

    @if_not_all
    def test_create_image_metadata(self):
        ""Test create_image_metadata""
        self._test_create_image_metadata()
    def _test_create_image_metadata(self):
        r = self.client.create_image_metadata(self.img, 'mykey', 'myval')
        self.assertEqual(r['mykey'], 'myval')

    @if_not_all
    def test_update_image_metadata(self):
        ""Test update_image_metadata""
        self._test_update_image_metadata()
    def _test_update_image_metadata(self):
        r = self.client.create_image_metadata(self.img, 'mykey0', 'myval')
        r = self.client.update_image_metadata(self.img, 'mykey0', 'myval0')
        self.assertEqual(r['mykey0'], 'myval0')

    @if_not_all
    def test_delete_image_metadata(self):
        ""Test delete_image_metadata""
        self._test_delete_image_metadata()
    def _test_delete_image_metadata(self):
        self.client.create_image_metadata(self.img, 'mykey1', 'myval1')
        self.client.delete_image_metadata(self.img, 'mykey1')
        r = self.client.get_image_metadata(self.img)
        self.assertNotEqual('mykey1' in r)
    """


class testPithos(unittest.TestCase):
    """Set up a Pithos+ thorough test"""
    def setUp(self):
        _init_cnf()
        global cnf
        url = cnf.get('store', 'url')

        global token
        global global_username
        account = global_username

        """
        url='https://pithos.okeanos.io/v1'
        """

        """
        def add_handler(name, level, prefix=''):
            h = logging.StreamHandler()
            fmt = logging.Formatter(prefix + '%(message)s')
            h.setFormatter(fmt)
            logger = logging.getLogger(name)
            logger.addHandler(h)
            logger.setLevel(level)
        import logging
        sendlog = logging.getLogger('clients.send')
        recvlog = logging.getLogger('clients.recv')
        add_handler('requests', logging.INFO, prefix='* ')
        add_handler('clients.send', logging.INFO, prefix='> ')
        add_handler('clients.recv', logging.INFO, prefix='< ')
        """

        self.fname = None
        container = None
        self.client = pithos(url, token, account, container)
        self.now = time.mktime(time.gmtime())
        self.c1 = 'c1_' + unicode(self.now)
        self.c2 = 'c2_' + unicode(self.now)
        self.c3 = 'c3_' + unicode(self.now)

        self.client.create_container(self.c1)
        self.client.create_container(self.c2)
        self.client.create_container(self.c3)
        self.makeNewObject(self.c1, 'test')
        self.makeNewObject(self.c2, 'test')
        self.now_unformated = datetime.datetime.utcnow()
        self.makeNewObject(self.c1, 'test1')
        self.makeNewObject(self.c2, 'test1')
        """Prepare an object to be shared - also its container"""
        self.client.container = self.c1
        self.client.object_post('test',
            update=True,
            permissions={'read': 'someUser'})

        self.makeNewObject(self.c1, 'another.test')

    def makeNewObject(self, container, obj):
        self.client.container = container
        self.client.object_put(obj,
            content_type='application/octet-stream',
            data='file %s that lives in %s' % (obj, container),
            metadata={'incontainer': container})

    def forceDeleteContainer(self, container):
        self.client.container = container
        try:
            r = self.client.list_objects()
        except ClientError:
            return
        for obj in r:
            name = obj['name']
            self.client.del_object(name)
        r = self.client.container_delete()
        self.container = ''

    def tearDown(self):
        """Destroy test cases"""
        if self.fname is not None:
            try:
                os.remove(self.fname)
            except OSError:
                pass
            self.fname = None
        self.forceDeleteContainer(self.c1)
        self.forceDeleteContainer(self.c2)
        try:
            self.forceDeleteContainer(self.c3)
        except ClientError:
            pass
        self.client.container = ''

    def test_000(self):
        """Perform a full Pithos+ kamaki support test"""

    def test_account_head(self):
        """Test account_HEAD"""
        r = self.client.account_head()
        self.assertEqual(r.status_code, 204)

        r = self.client.account_head(until='1000000000')
        self.assertEqual(r.status_code, 204)

        r = self.client.get_account_info(until='1000000000')
        datestring = unicode(r['x-account-until-timestamp'])
        self.assertEqual(u'Sun, 09 Sep 2001 01:46:40 GMT', datestring)

        r = self.client.get_account_quota()
        self.assertTrue('x-account-policy-quota' in r)

        r = self.client.get_account_versioning()
        self.assertTrue('x-account-policy-versioning' in r)

        """Check if(un)modified_since"""
        for format in self.client.DATE_FORMATS:
            now_formated = self.now_unformated.strftime(format)
            r1 = self.client.account_head(if_modified_since=now_formated,
                success=(204, 304, 412))
            sc1 = r1.status_code
            r1.release()
            r2 = self.client.account_head(if_unmodified_since=now_formated,
                success=(204, 304, 412))
            sc2 = r2.status_code
            r2.release()
            self.assertNotEqual(sc1, sc2)

    def test_account_get(self):
        """Test account_GET"""
        #r = self.client.account_get()
        #self.assertEqual(r.status_code, 200)
        r = self.client.list_containers()
        fullLen = len(r)
        self.assertTrue(fullLen > 2)

        r = self.client.account_get(limit=1)
        self.assertEqual(len(r.json), 1)

        r = self.client.account_get(marker='c2_')
        temp_c0 = r.json[0]['name']
        temp_c2 = r.json[2]['name']

        r = self.client.account_get(limit=2, marker='c2_')
        conames = [container['name'] for container in r.json \
            if container['name'].lower().startswith('c2_')]
        self.assertTrue(temp_c0 in conames)
        self.assertFalse(temp_c2 in conames)

        r = self.client.account_get(show_only_shared=True)
        self.assertTrue(self.c1 in [c['name'] for c in r.json])

        r = self.client.account_get(until=1342609206)
        self.assertTrue(len(r.json) <= fullLen)

        """Check if(un)modified_since"""
        for format in self.client.DATE_FORMATS:
            now_formated = self.now_unformated.strftime(format)
            r1 = self.client.account_get(if_modified_since=now_formated,
                success=(200, 304, 412))
            sc1 = r1.status_code
            r1.release()
            r2 = self.client.account_get(if_unmodified_since=now_formated,
                success=(200, 304, 412))
            sc2 = r2.status_code
            r2.release()
            self.assertNotEqual(sc1, sc2)

        """Check sharing_accounts"""
        r = self.client.get_sharing_accounts()
        self.assertTrue(len(r) > 0)

    def test_account_post(self):
        """Test account_POST"""
        r = self.client.account_post()
        self.assertEqual(r.status_code, 202)
        grpName = 'grp' + unicode(self.now)

        """Method set/del_account_meta and set_account_groupcall use
            account_post internally
        """
        self.client.set_account_group(grpName, ['u1', 'u2'])
        r = self.client.get_account_group()
        self.assertEqual(r['x-account-group-' + grpName], 'u1,u2')
        self.client.del_account_group(grpName)
        r = self.client.get_account_group()
        self.assertTrue('x-account-group-' + grpName not in r)

        mprefix = 'meta' + unicode(self.now)
        self.client.set_account_meta({mprefix + '1': 'v1',
            mprefix + '2': 'v2'})
        r = self.client.get_account_meta()
        self.assertEqual(r['x-account-meta-' + mprefix + '1'], 'v1')
        self.assertEqual(r['x-account-meta-' + mprefix + '2'], 'v2')

        self.client.del_account_meta(mprefix + '1')
        r = self.client.get_account_meta()
        self.assertTrue('x-account-meta-' + mprefix + '1' not in r)

        self.client.del_account_meta(mprefix + '2')
        r = self.client.get_account_meta()
        self.assertTrue('x-account-meta-' + mprefix + '2' not in r)

        """Missing testing for quota, versioning, because normally
        you don't have permissions to modify those at account level
        """

        newquota = 1000000
        self.client.set_account_quota(newquota)
        #r = self.client.get_account_info()
        #print(unicode(r))
        #r = self.client.get_account_quota()
        #self.assertEqual(r['x-account-policy-quota'], newquota)
        self.client.set_account_versioning('auto')

    def test_container_head(self):
        """Test container_HEAD"""
        self.client.container = self.c1

        r = self.client.container_head()
        self.assertEqual(r.status_code, 204)

        """Check until"""
        r = self.client.container_head(until=1000000, success=(204, 404))
        self.assertEqual(r.status_code, 404)

        """Check and if(un)modified_since"""
        for format in self.client.DATE_FORMATS:
            now_formated = self.now_unformated.strftime(format)
            r1 = self.client.container_head(if_modified_since=now_formated,
                success=(204, 304, 412))
            sc1 = r1.status_code
            r1.release()
            r2 = self.client.container_head(if_unmodified_since=now_formated,
                success=(204, 304, 412))
            sc2 = r2.status_code
            r2.release()
            self.assertNotEqual(sc1, sc2)

        """Check container object meta"""
        r = self.client.get_container_object_meta()
        self.assertEqual(r['x-container-object-meta'], 'Incontainer')

    def test_container_get(self):
        """Test container_GET"""
        self.client.container = self.c1

        r = self.client.container_get()
        self.assertEqual(r.status_code, 200)
        fullLen = len(r.json)

        r = self.client.container_get(prefix='test')
        lalobjects = [obj for obj in r.json if obj['name'].startswith('test')]
        self.assertTrue(len(r.json) > 1)
        self.assertEqual(len(r.json), len(lalobjects))

        r = self.client.container_get(limit=1)
        self.assertEqual(len(r.json), 1)

        r = self.client.container_get(marker='another')
        self.assertTrue(len(r.json) > 1)
        neobjects = [obj for obj in r.json if obj['name'] > 'another']
        self.assertEqual(len(r.json), len(neobjects))

        r = self.client.container_get(prefix='another.test', delimiter='.')
        self.assertTrue(fullLen > len(r.json))

        r = self.client.container_get(path='/')
        self.assertEqual(fullLen, len(r.json))

        r = self.client.container_get(format='xml')
        self.assertEqual(r.text.split()[4], 'name="' + self.c1 + '">')

        r = self.client.container_get(meta=['incontainer'])
        self.assertTrue(len(r.json) > 0)

        r = self.client.container_get(show_only_shared=True)
        self.assertTrue(len(r.json) < fullLen)

        try:
            r = self.client.container_get(until=1000000000)
            datestring = unicode(r.headers['x-account-until-timestamp'])
            self.assertEqual(u'Sun, 09 Sep 2001 01:46:40 GMT', datestring)

        except ClientError:

            pass

        """Check and if un/modified_since"""
        for format in self.client.DATE_FORMATS:
            now_formated = self.now_unformated.strftime(format)
            r1 = self.client.container_get(if_modified_since=now_formated,
                success=(200, 304, 412))
            sc1 = r1.status_code
            r1.release()
            r2 = self.client.container_get(if_unmodified_since=now_formated,
                success=(200, 304, 412))
            sc2 = r2.status_code
            r2.release()
            self.assertNotEqual(sc1, sc2)

    def test_container_put(self):
        """Test container_PUT"""
        self.client.container = self.c2

        r = self.client.container_put()
        self.assertEqual(r.status_code, 202)

        r = self.client.get_container_quota(self.client.container)
        cquota = r.values()[0]
        newquota = 2 * int(cquota)

        r = self.client.container_put(quota=newquota)
        self.assertEqual(r.status_code, 202)

        r = self.client.get_container_quota(self.client.container)
        xquota = int(r.values()[0])
        self.assertEqual(newquota, xquota)

        r = self.client.container_put(versioning='auto')
        self.assertEqual(r.status_code, 202)

        r = self.client.get_container_versioning(self.client.container)
        nvers = r.values()[0]
        self.assertEqual('auto', nvers)

        r = self.client.container_put(versioning='none')
        self.assertEqual(r.status_code, 202)

        r = self.client.get_container_versioning(self.client.container)
        nvers = r.values()[0]
        self.assertEqual('none', nvers)

        r = self.client.container_put(metadata={'m1': 'v1', 'm2': 'v2'})
        self.assertEqual(r.status_code, 202)

        r = self.client.get_container_meta(self.client.container)
        self.assertTrue('x-container-meta-m1' in r)
        self.assertEqual(r['x-container-meta-m1'], 'v1')
        self.assertTrue('x-container-meta-m2' in r)
        self.assertEqual(r['x-container-meta-m2'], 'v2')

        r = self.client.container_put(metadata={'m1': '', 'm2': 'v2a'})
        self.assertEqual(r.status_code, 202)

        r = self.client.get_container_meta(self.client.container)
        self.assertTrue('x-container-meta-m1' not in r)
        self.assertTrue('x-container-meta-m2' in r)
        self.assertEqual(r['x-container-meta-m2'], 'v2a')

        self.client.del_container_meta(self.client.container)

    def test_container_post(self):
        """Test container_POST"""
        self.client.container = self.c2

        """Simple post"""
        r = self.client.container_post()
        self.assertEqual(r.status_code, 202)

        """post meta"""
        self.client.set_container_meta({'m1': 'v1', 'm2': 'v2'})
        r = self.client.get_container_meta(self.client.container)
        self.assertTrue('x-container-meta-m1' in r)
        self.assertEqual(r['x-container-meta-m1'], 'v1')
        self.assertTrue('x-container-meta-m2' in r)
        self.assertEqual(r['x-container-meta-m2'], 'v2')

        """post/2del meta"""
        r = self.client.del_container_meta('m1')
        r = self.client.set_container_meta({'m2': 'v2a'})
        r = self.client.get_container_meta(self.client.container)
        self.assertTrue('x-container-meta-m1' not in r)
        self.assertTrue('x-container-meta-m2' in r)
        self.assertEqual(r['x-container-meta-m2'], 'v2a')

        """check quota"""
        r = self.client.get_container_quota(self.client.container)
        cquota = r.values()[0]
        newquota = 2 * int(cquota)
        r = self.client.set_container_quota(newquota)
        r = self.client.get_container_quota(self.client.container)
        xquota = int(r.values()[0])
        self.assertEqual(newquota, xquota)
        r = self.client.set_container_quota(cquota)
        r = self.client.get_container_quota(self.client.container)
        xquota = r.values()[0]
        self.assertEqual(cquota, xquota)

        """Check versioning"""
        self.client.set_container_versioning('auto')
        r = self.client.get_container_versioning(self.client.container)
        nvers = r.values()[0]
        self.assertEqual('auto', nvers)
        self.client.set_container_versioning('none')
        r = self.client.get_container_versioning(self.client.container)
        nvers = r.values()[0]
        self.assertEqual('none', nvers)

        """put_block uses content_type and content_length to
        post blocks of data 2 container. All that in upload_object"""
        """Change a file at fs"""
        self.fname = 'l100M.' + unicode(self.now)
        self.create_large_file(1024 * 1024 * 100, self.fname)
        """Upload it at a directory in container"""
        self.client.create_directory('dir')
        newf = open(self.fname, 'rb')
        self.client.upload_object('/dir/sample.file', newf)
        newf.close()
        """Check if file has been uploaded"""
        r = self.client.get_object_info('/dir/sample.file')
        self.assertTrue(int(r['content-length']) > 100000000)

        """What is tranfer_encoding? What should I check about it? """
        #TODO

        """Check update=False"""
        r = self.client.object_post('test',
            update=False,
            metadata={'newmeta': 'newval'})

        r = self.client.get_object_info('test')
        self.assertTrue('x-object-meta-newmeta' in r)
        self.assertFalse('x-object-meta-incontainer' in r)

        r = self.client.del_container_meta('m2')

    def test_container_delete(self):
        """Test container_DELETE"""

        """Fail to delete a non-empty container"""
        self.client.container = self.c2
        r = self.client.container_delete(success=409)
        self.assertEqual(r.status_code, 409)

        """Fail to delete c3 (empty) container"""
        self.client.container = self.c3
        r = self.client.container_delete(until='1000000000')
        self.assertEqual(r.status_code, 204)

        """Delete c3 (empty) container"""
        r = self.client.container_delete()
        self.assertEqual(r.status_code, 204)

        """Purge container(empty a container), check versionlist"""
        self.client.container = self.c1
        r = self.client.object_head('test', success=(200, 404))
        self.assertEqual(r.status_code, 200)
        self.client.del_container(delimiter='/')
        r = self.client.object_head('test', success=(200, 404))
        self.assertEqual(r.status_code, 404)
        r = self.client.get_object_versionlist('test')
        self.assertTrue(len(r) > 0)
        self.assertTrue(len(r[0]) > 1)
        self.client.purge_container()
        self.assertRaises(ClientError,
            self.client.get_object_versionlist,
            'test')

    def test_object_head(self):
        """Test object_HEAD"""
        self.client.container = self.c2
        obj = 'test'

        r = self.client.object_head(obj)
        self.assertEqual(r.status_code, 200)
        etag = r.headers['etag']

        r = self.client.object_head(obj, version=40)
        self.assertEqual(r.headers['x-object-version'], '40')

        r = self.client.object_head(obj, if_etag_match=etag)
        self.assertEqual(r.status_code, 200)

        r = self.client.object_head(obj,
            if_etag_not_match=etag,
            success=(200, 412, 304))
        self.assertNotEqual(r.status_code, 200)

        r = self.client.object_head(obj,
            version=40,
            if_etag_match=etag,
            success=412)
        self.assertEqual(r.status_code, 412)

        """Check and if(un)modified_since"""
        for format in self.client.DATE_FORMATS:
            now_formated = self.now_unformated.strftime(format)
            r1 = self.client.object_head(obj, if_modified_since=now_formated,
                success=(200, 304, 412))
            sc1 = r1.status_code
            r1.release()
            r2 = self.client.object_head(obj, if_unmodified_since=now_formated,
                success=(200, 304, 412))
            sc2 = r2.status_code
            r2.release()
            self.assertNotEqual(sc1, sc2)

    def test_object_get(self):
        """Test object_GET"""
        self.client.container = self.c1
        obj = 'test'

        r = self.client.object_get(obj)
        self.assertEqual(r.status_code, 200)

        osize = int(r.headers['content-length'])
        etag = r.headers['etag']

        r = self.client.object_get(obj, hashmap=True)
        self.assertTrue('hashes' in r.json\
            and 'block_hash' in r.json\
            and 'block_size' in r.json\
            and 'bytes' in r.json)

        r = self.client.object_get(obj, format='xml', hashmap=True)
        self.assertEqual(len(r.text.split('hash>')), 3)

        rangestr = 'bytes=%s-%s' % (osize / 3, osize / 2)
        r = self.client.object_get(obj,
            data_range=rangestr,
            success=(200, 206))
        partsize = int(r.headers['content-length'])
        self.assertTrue(0 < partsize and partsize <= 1 + osize / 3)

        rangestr = 'bytes=%s-%s' % (osize / 3, osize / 2)
        r = self.client.object_get(obj,
            data_range=rangestr,
            if_range=True,
            success=(200, 206))
        partsize = int(r.headers['content-length'])
        self.assertTrue(0 < partsize and partsize <= 1 + osize / 3)

        r = self.client.object_get(obj, if_etag_match=etag)
        self.assertEqual(r.status_code, 200)

        r = self.client.object_get(obj, if_etag_not_match=etag + 'LALALA')
        self.assertEqual(r.status_code, 200)

        """Check and if(un)modified_since"""
        for format in self.client.DATE_FORMATS:
            now_formated = self.now_unformated.strftime(format)
            r1 = self.client.object_get(obj, if_modified_since=now_formated,
                success=(200, 304, 412))
            sc1 = r1.status_code
            r1.release()
            r2 = self.client.object_get(obj,
                if_unmodified_since=now_formated,
                success=(200, 304, 412))
            sc2 = r2.status_code
            r2.release()
            self.assertNotEqual(sc1, sc2)

        """Upload an object to download"""
        src_file = tempfile.NamedTemporaryFile(delete=False)
        dnl_file = tempfile.NamedTemporaryFile(delete=False)
        
        src_fname = src_file.name
        dnl_fname = dnl_file.name
        
        src_file.close()
        dnl_file.close()
        
        trg_fname = 'remotefile_%s' % self.now
        f_size = 59247824
        self.create_large_file(f_size, src_fname)
        src_f = open(src_fname, 'rb+')
        print('\tUploading...')
        self.client.upload_object(trg_fname, src_f)
        src_f.close()
        print('\tDownloading...')
        dnl_f = open(dnl_fname, 'wb+')
        self.client.download_object(trg_fname, dnl_f)
        dnl_f.close()

        print('\tCheck if files match...')
        src_f = open(src_fname)
        dnl_f = open(dnl_fname)
        for pos in (0, f_size / 2, f_size - 20):
            src_f.seek(pos)
            dnl_f.seek(pos)
            self.assertEqual(src_f.read(10), dnl_f.read(10))
        src_f.close()
        dnl_f.close()

        os.remove(src_fname)
        os.remove(dnl_fname)

    def test_object_put(self):
        """Test object_PUT"""

        self.client.container = self.c2
        obj = 'another.test'

        self.client.create_object(obj + '.FAKE')
        r = self.client.get_object_info(obj + '.FAKE')
        self.assertEqual(r['content-type'], 'application/octet-stream')

        """create the object"""
        r = self.client.object_put(obj,
            data='a',
            content_type='application/octer-stream',
            permissions={
                'read': ['accX:groupA', 'u1', 'u2'],
                'write': ['u2', 'u3']},
            metadata={'key1': 'val1', 'key2': 'val2'},
            content_encoding='UTF-8',
            content_disposition='attachment; filename="fname.ext"')
        self.assertEqual(r.status_code, 201)
        etag = r.headers['etag']

        """Check content-disposition"""
        r = self.client.get_object_info(obj)
        self.assertTrue('content-disposition' in r)

        """Check permissions"""
        r = self.client.get_object_sharing(obj)
        self.assertTrue('accx:groupa' in r['read'])
        self.assertTrue('u1' in r['read'])
        self.assertTrue('u2' in r['write'])
        self.assertTrue('u3' in r['write'])

        """Check metadata"""
        r = self.client.get_object_meta(obj)
        self.assertEqual(r['x-object-meta-key1'], 'val1')
        self.assertEqual(r['x-object-meta-key2'], 'val2')

        """Check public and if_etag_match"""
        r = self.client.object_put(obj, if_etag_match=etag, data='b',
            content_type='application/octet-stream', public=True)

        r = self.client.object_get(obj)
        self.assertTrue('x-object-public' in r.headers)
        vers2 = int(r.headers['x-object-version'])
        etag = r.headers['etag']
        self.assertEqual(r.text, 'b')

        """Check if_etag_not_match"""
        r = self.client.object_put(obj, if_etag_not_match=etag, data='c',
            content_type='application/octet-stream', success=(201, 412))
        self.assertEqual(r.status_code, 412)

        """Check content_type and content_length"""
        tmpdir = 'dir' + unicode(self.now)
        r = self.client.object_put(tmpdir,
            content_type='application/directory',
            content_length=0)

        r = self.client.get_object_info(tmpdir)
        self.assertEqual(r['content-type'], 'application/directory')

        """Check copy_from, content_encoding"""
        r = self.client.object_put('%s/%s' % (tmpdir, obj),
            format=None,
            copy_from='/%s/%s' % (self.client.container, obj),
            content_encoding='application/octet-stream',
            source_account=self.client.account,
            content_length=0, success=201)
        self.assertEqual(r.status_code, 201)

        """Test copy_object for cross-conctainer copy"""
        self.client.copy_object(src_container=self.c2,
            src_object='%s/%s' % (tmpdir, obj),
            dst_container=self.c1,
            dst_object=obj)
        self.client.container = self.c1
        r1 = self.client.get_object_info(obj)
        self.client.container = self.c2
        r2 = self.client.get_object_info('%s/%s' % (tmpdir, obj))
        self.assertEqual(r1['x-object-hash'], r2['x-object-hash'])

        """Check cross-container copy_from, content_encoding"""
        self.client.container = self.c1
        fromstr = '/%s/%s/%s' % (self.c2, tmpdir, obj)
        r = self.client.object_put(obj,
            format=None,
            copy_from=fromstr,
            content_encoding='application/octet-stream',
            source_account=self.client.account,
            content_length=0, success=201)

        self.assertEqual(r.status_code, 201)
        r = self.client.get_object_info(obj)
        self.assertEqual(r['etag'], etag)

        """Check source_account"""
        self.client.container = self.c2
        fromstr = '/%s/%s' % (self.c1, obj)
        r = self.client.object_put(obj + 'v2',
            format=None,
            move_from=fromstr,
            content_encoding='application/octet-stream',
            source_account='nonExistendAddress@NeverLand.com',
            content_length=0,
            success=(201, 403))
        self.assertEqual(r.status_code, 403)

        """Check cross-container move_from"""
        self.client.container = self.c1
        r1 = self.client.get_object_info(obj)
        self.client.container = self.c2
        self.client.move_object(src_container=self.c1,
            src_object=obj,
            dst_container=self.c2,
            dst_object=obj + 'v0')
        r0 = self.client.get_object_info(obj + 'v0')
        self.assertEqual(r1['x-object-hash'], r0['x-object-hash'])

        """Check move_from"""
        r = self.client.object_put(obj + 'v1',
            format=None,
            move_from='/%s/%s' % (self.c2, obj),
            source_version=vers2,
            content_encoding='application/octet-stream',
            content_length=0, success=201)

        """Check manifest"""
        mobj = 'manifest.test'
        txt = ''
        for i in range(10):
            txt += '%s' % i
            r = self.client.object_put('%s/%s' % (mobj, i),
                data='%s' % i,
                content_length=1,
                success=201,
                content_type='application/octet-stream',
                content_encoding='application/octet-stream')

        r = self.client.object_put(mobj,
            content_length=0,
            content_type='application/octet-stream',
            manifest='%s/%s' % (self.client.container, mobj))

        r = self.client.object_get(mobj)
        self.assertEqual(r.text, txt)

        """Upload a local file with one request"""
        self.fname = 'l10K.' + unicode(self.now)
        self.create_large_file(1024 * 10, self.fname)
        newf = open(self.fname, 'rb')
        self.client.upload_object('sample.file', newf)
        newf.close()
        """Check if file has been uploaded"""
        r = self.client.get_object_info('sample.file')
        self.assertEqual(int(r['content-length']), 10260)

        """Some problems with transfer-encoding?"""

    def test_object_copy(self):
        """Test object_COPY"""
        self.client.container = self.c2
        obj = 'test2'

        data = '{"key1":"val1", "key2":"val2"}'
        r = self.client.object_put(obj + 'orig',
            content_type='application/octet-stream',
            data=data,
            metadata={'mkey1': 'mval1', 'mkey2': 'mval2'},
            permissions={
                'read': ['accX:groupA', 'u1', 'u2'],
                'write': ['u2', 'u3']},
            content_disposition='attachment; filename="fname.ext"')

        r = self.client.object_copy(obj + 'orig',
            destination='/%s/%s' % (self.client.container, obj),
            ignore_content_type=False, content_type='application/json',
            metadata={'mkey2': 'mval2a', 'mkey3': 'mval3'},
            permissions={'write': ['u5', 'accX:groupB']})
        self.assertEqual(r.status_code, 201)

        """Check content-disposition"""
        r = self.client.get_object_info(obj)
        self.assertTrue('content-disposition' in r)

        """Check Metadata"""
        r = self.client.get_object_meta(obj)
        self.assertEqual(r['x-object-meta-mkey1'], 'mval1')
        self.assertEqual(r['x-object-meta-mkey2'], 'mval2a')
        self.assertEqual(r['x-object-meta-mkey3'], 'mval3')

        """Check permissions"""
        r = self.client.get_object_sharing(obj)
        self.assertFalse('read' in r or 'u2' in r['write'])
        self.assertTrue('accx:groupb' in r['write'])

        """Check destination account"""
        r = self.client.object_copy(obj,
            destination='/%s/%s' % (self.c1, obj),
            content_encoding='utf8',
            content_type='application/json',
            destination_account='nonExistendAddress@NeverLand.com',
            success=(201, 403))
        self.assertEqual(r.status_code, 403)

        """Check destination being another container
        and also content_type and content encoding"""
        r = self.client.object_copy(obj,
            destination='/%s/%s' % (self.c1, obj),
            content_encoding='utf8',
            content_type='application/json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.headers['content-type'],
            'application/json; charset=UTF-8')

        """Check ignore_content_type and content_type"""
        r = self.client.object_get(obj)
        etag = r.headers['etag']
        ctype = r.headers['content-type']
        self.assertEqual(ctype, 'application/json')

        r = self.client.object_copy(obj + 'orig',
            destination='/%s/%s0' % (self.client.container, obj),
            ignore_content_type=True,
            content_type='application/json')
        self.assertEqual(r.status_code, 201)
        self.assertNotEqual(r.headers['content-type'], 'application/json')

        """Check if_etag_(not_)match"""
        r = self.client.object_copy(obj,
            destination='/%s/%s1' % (self.client.container, obj),
            if_etag_match=etag)
        self.assertEqual(r.status_code, 201)

        r = self.client.object_copy(obj,
            destination='/%s/%s2' % (self.client.container, obj),
            if_etag_not_match='lalala')
        self.assertEqual(r.status_code, 201)
        vers2 = r.headers['x-object-version']

        """Check source_version, public and format """
        r = self.client.object_copy(obj + '2',
            destination='/%s/%s3' % (self.client.container, obj),
            source_version=vers2,
            format='xml',
            public=True)
        self.assertEqual(r.status_code, 201)
        self.assertTrue(r.headers['content-type'].index('xml') > 0)

        r = self.client.get_object_info(obj + '3')
        self.assertTrue('x-object-public' in r)

    def test_object_move(self):
        """Test object_MOVE"""
        self.client.container = self.c2
        obj = 'test2'

        data = '{"key1": "val1", "key2": "val2"}'
        r = self.client.object_put(obj + 'orig',
            content_type='application/octet-stream',
            data=data,
            metadata={'mkey1': 'mval1', 'mkey2': 'mval2'},
            permissions={'read': ['accX:groupA', 'u1', 'u2'],
                'write': ['u2', 'u3']})

        r = self.client.object_move(obj + 'orig',
            destination='/%s/%s' % (self.client.container, obj),
            ignore_content_type=False,
            content_type='application/json',
            metadata={'mkey2': 'mval2a', 'mkey3': 'mval3'},
            permissions={'write': ['u5', 'accX:groupB']})
        self.assertEqual(r.status_code, 201)

        """Check Metadata"""
        r = self.client.get_object_meta(obj)
        self.assertEqual(r['x-object-meta-mkey1'], 'mval1')
        self.assertEqual(r['x-object-meta-mkey2'], 'mval2a')
        self.assertEqual(r['x-object-meta-mkey3'], 'mval3')

        """Check permissions"""
        r = self.client.get_object_sharing(obj)
        self.assertFalse('read' in r)
        self.assertTrue('u5' in r['write'])
        self.assertTrue('accx:groupb' in r['write'])

        """Check destination account"""
        r = self.client.object_move(obj,
            destination='/%s/%s' % (self.c1, obj),
            content_encoding='utf8',
            content_type='application/json',
            destination_account='nonExistendAddress@NeverLand.com',
            success=(201, 403))
        self.assertEqual(r.status_code, 403)

        """Check destination being another container and also
        content_type, content_disposition and content encoding"""
        r = self.client.object_move(obj,
            destination='/%s/%s' % (self.c1, obj),
            content_encoding='utf8',
            content_type='application/json',
            content_disposition='attachment; filename="fname.ext"')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.headers['content-type'],
            'application/json; charset=UTF-8')
        self.client.container = self.c1
        r = self.client.get_object_info(obj)
        self.assertTrue('content-disposition' in r\
            and 'fname.ext' in r['content-disposition'])
        etag = r['etag']
        ctype = r['content-type']
        self.assertEqual(ctype, 'application/json')

        """Check ignore_content_type and content_type"""
        r = self.client.object_move(obj,
            destination='/%s/%s' % (self.c2, obj),
            ignore_content_type=True,
            content_type='application/json')
        self.assertEqual(r.status_code, 201)
        self.assertNotEqual(r.headers['content-type'], 'application/json')

        """Check if_etag_(not_)match"""
        self.client.container = self.c2
        r = self.client.object_move(obj,
            destination='/%s/%s0' % (self.client.container, obj),
            if_etag_match=etag)
        self.assertEqual(r.status_code, 201)

        r = self.client.object_move(obj + '0',
            destination='/%s/%s1' % (self.client.container, obj),
            if_etag_not_match='lalala')
        self.assertEqual(r.status_code, 201)

        """Check public and format """
        r = self.client.object_move(obj + '1',
            destination='/%s/%s2' % (self.client.container, obj),
            format='xml', public=True)
        self.assertEqual(r.status_code, 201)
        self.assertTrue(r.headers['content-type'].index('xml') > 0)

        r = self.client.get_object_info(obj + '2')
        self.assertTrue('x-object-public' in r)

    def test_object_post(self):
        """Test object_POST"""
        self.client.container = self.c2
        obj = 'test2'
        """create a filesystem file"""
        self.fname = obj
        newf = open(self.fname, 'w')
        newf.writelines(['ello!\n',
            'This is a test line\n',
            'inside a test file\n'])
        newf.close()
        """create a file on container"""
        r = self.client.object_put(obj,
            content_type='application/octet-stream',
            data='H',
            metadata={'mkey1': 'mval1', 'mkey2': 'mval2'},
            permissions={'read': ['accX:groupA', 'u1', 'u2'],
                'write': ['u2', 'u3']})

        """Append tests update, content_range, content_type, content_length"""
        newf = open(obj, 'r')
        self.client.append_object(obj, newf)
        r = self.client.object_get(obj)
        self.assertTrue(r.text.startswith('Hello!'))

        """Overwrite tests update,
            content_type, content_length, content_range
        """
        newf.seek(0)
        r = self.client.overwrite_object(obj, 0, 10, newf)
        r = self.client.object_get(obj)
        self.assertTrue(r.text.startswith('ello!'))
        newf.close()

        """Truncate tests update,
            content_range, content_type, object_bytes and source_object"""
        r = self.client.truncate_object(obj, 5)
        r = self.client.object_get(obj)
        self.assertEqual(r.text, 'ello!')

        """Check metadata"""
        self.client.set_object_meta(obj, {'mkey2': 'mval2a', 'mkey3': 'mval3'})
        r = self.client.get_object_meta(obj)
        self.assertEqual(r['x-object-meta-mkey1'], 'mval1')
        self.assertEqual(r['x-object-meta-mkey2'], 'mval2a')
        self.assertEqual(r['x-object-meta-mkey3'], 'mval3')
        self.client.del_object_meta(obj, 'mkey1')
        r = self.client.get_object_meta(obj)
        self.assertFalse('x-object-meta-mkey1' in r)

        """Check permissions"""
        self.client.set_object_sharing(obj,
            read_permition=['u4', 'u5'], write_permition=['u4'])
        r = self.client.get_object_sharing(obj)
        self.assertTrue('read' in r)
        self.assertTrue('u5' in r['read'])
        self.assertTrue('write' in r)
        self.assertTrue('u4' in r['write'])
        self.client.del_object_sharing(obj)
        r = self.client.get_object_sharing(obj)
        self.assertTrue(len(r) == 0)

        """Check publish"""
        self.client.publish_object(obj)
        r = self.client.get_object_info(obj)
        self.assertTrue('x-object-public' in r)
        self.client.unpublish_object(obj)
        r = self.client.get_object_info(obj)
        self.assertFalse('x-object-public' in r)

        """Check if_etag_(not)match"""
        etag = r['etag']
        """
        r = self.client.object_post(obj,
            update=True,
            public=True,
            if_etag_not_match=etag,
            success=(412, 202, 204))
        self.assertEqual(r.status_code, 412)
        """

        r = self.client.object_post(obj, update=True, public=True,
            if_etag_match=etag, content_encoding='application/json')

        r = self.client.get_object_info(obj)
        helloVersion = r['x-object-version']
        self.assertTrue('x-object-public' in r)
        self.assertEqual(r['content-encoding'], 'application/json')

        """Check source_version and source_account and content_disposition"""
        r = self.client.object_post(obj,
            update=True,
            content_type='application/octet-srteam',
            content_length=5,
            content_range='bytes 1-5/*',
            source_object='/%s/%s' % (self.c2, obj),
            source_account='thisAccountWillNeverExist@adminland.com',
            source_version=helloVersion,
            data='12345',
            success=(403, 202, 204))
        self.assertEqual(r.status_code, 403)

        r = self.client.object_post(obj,
            update=True,
            content_type='application/octet-srteam',
            content_length=5,
            content_range='bytes 1-5/*',
            source_object='/%s/%s' % (self.c2, obj),
            source_account=self.client.account,
            source_version=helloVersion,
            data='12345',
            content_disposition='attachment; filename="fname.ext"')

        r = self.client.object_get(obj)
        self.assertEqual(r.text, 'eello!')
        self.assertTrue('content-disposition' in r.headers\
            and 'fname.ext' in r.headers['content-disposition'])

        """Check manifest"""
        mobj = 'manifest.test'
        txt = ''
        for i in range(10):
            txt += '%s' % i
            r = self.client.object_put('%s/%s' % (mobj, i),
            data='%s' % i,
            content_length=1,
            success=201,
            content_encoding='application/octet-stream',
            content_type='application/octet-stream')

        self.client.create_object_by_manifestation(mobj,
            content_type='application/octet-stream')

        r = self.client.object_post(mobj,
            manifest='%s/%s' % (self.client.container, mobj))

        r = self.client.object_get(mobj)
        self.assertEqual(r.text, txt)

        """We need to check transfer_encoding """

    def test_object_delete(self):
        """Test object_DELETE"""
        self.client.container = self.c2
        obj = 'test2'
        """create a file on container"""
        r = self.client.object_put(obj,
            content_type='application/octet-stream',
            data='H',
            metadata={'mkey1': 'mval1', 'mkey2': 'mval2'},
            permissions={'read': ['accX:groupA', 'u1', 'u2'],
                'write': ['u2', 'u3']})

        """Check with false until"""
        r = self.client.object_delete(obj, until=1000000)

        r = self.client.object_get(obj, success=(200, 404))
        self.assertEqual(r.status_code, 200)

        """Check normal case"""
        r = self.client.object_delete(obj)
        self.assertEqual(r.status_code, 204)

        r = self.client.object_get(obj, success=(200, 404))
        self.assertEqual(r.status_code, 404)

    def create_large_file(self, size, name):
        """Create a large file at fs"""
        self.fname = name
        f = open(self.fname, 'w')
        sys.stdout.write(
            ' create random file %s of size %s      ' % (name, size))
        for hobyte_id in xrange(size / 8):
            random_bytes = os.urandom(8)
            f.write(random_bytes)
            if 0 == (hobyte_id * 800) % size:
                f.write('\n')
                f.flush()
                prs = (hobyte_id * 800) // size
                sys.stdout.write('\b\b')
                if prs > 10:
                    sys.stdout.write('\b')
                sys.stdout.write('%s%%' % prs)
                sys.stdout.flush()
        print('\b\b\b100%')
        f.flush()
        f.close()
        """"""


def init_parser():
    parser = ArgumentParser(add_help=False)
    parser.add_argument('-h', '--help',
        dest='help',
        action='store_true',
        default=False,
        help="Show this help message and exit")
    return parser


def main(argv):

    suiteFew = unittest.TestSuite()
    if len(argv) == 0 or argv[0] == 'pithos':
        if len(argv) == 1:
            suiteFew.addTest(unittest.makeSuite(testPithos))
        else:
            suiteFew.addTest(testPithos('test_' + argv[1]))
    if len(argv) == 0 or argv[0] == 'cyclades':
        if len(argv) == 1:
            #suiteFew.addTest(unittest.makeSuite(testCyclades))
            suiteFew.addTest(testCyclades('test_000'))
        else:
            suiteFew.addTest(testCyclades('test_' + argv[1]))
    if len(argv) == 0 or argv[0] == 'image':
        if len(argv) == 1:
            suiteFew.addTest(unittest.makeSuite(testImage))
        else:
            suiteFew.addTest(testImage('test_' + argv[1]))
    if len(argv) == 0 or argv[0] == 'astakos':
        if len(argv) == 1:
            suiteFew.addTest(unittest.makeSuite(testAstakos))
        else:
            suiteFew.addTest(testAstakos('test_' + argv[1]))

    unittest.TextTestRunner(verbosity=2).run(suiteFew)

if __name__ == '__main__':
    parser = init_parser()
    args, argv = parser.parse_known_args()
    if len(argv) > 2 or getattr(args, 'help') or len(argv) < 1:
        raise Exception('\tusage: tests.py <group> [command]')
    main(argv)
