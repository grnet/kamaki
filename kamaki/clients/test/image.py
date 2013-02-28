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

from mock import patch
import time

from unittest import TestCase
from kamaki.clients import ClientError

example_images = [
    {
        "status": "available",
        "name": "Archlinux",
        "disk_format": "diskdump",
        "container_format": "bare",
        "id": "b4713f20-3a41-4eaf-81ae-88698c18b3e8",
        "size": 752782848},
    {
        "status": "available",
        "name": "Debian_Wheezy_Base",
        "disk_format": "diskdump",
        "container_format": "bare",
        "id": "1f8454f0-8e3e-4b6c-ab8e-5236b728dffe",
        "size": 795107328},
    {
        "status": "available",
        "name": "maelstrom",
        "disk_format": "diskdump",
        "container_format": "bare",
        "id": "0fb03e45-7d5a-4515-bd4e-e6bbf6457f06",
        "size": 2583195644},
    {
        "status": "available",
        "name": "Gardenia",
        "disk_format": "diskdump",
        "container_format": "bare",
        "id": "5963020b-ab74-4e11-bc59-90c494bbdedb",
        "size": 2589802496}]

class Image(TestCase):

    class FR(object):
        json = example_images
        headers = {}
        content = json
        status = None
        status_code = 200

    def setUp(self):
        self.now = time.mktime(time.gmtime())
        self.imgname = 'img_%s' % self.now
        self.url = 'http://image.example.com'
        self.token = 'an1m@g370k3n=='
        from kamaki.clients.image import ImageClient
        self.client = ImageClient(self.url, self.token)
        self.cyclades_url = 'http://cyclades.example.com'
        from kamaki.clients.cyclades import CycladesClient
        self.cyclades = CycladesClient(self.cyclades_url, self.token)
        from kamaki.clients.connection.kamakicon import KamakiHTTPConnection
        self.C = KamakiHTTPConnection

    def tearDown(self):
        self.FR.json = example_images

    def assert_dicts_are_deeply_equal(self, d1, d2):
        for k, v in d1.items():
            self.assertTrue(k in d2)
            if isinstance(v, dict):
                self.assert_dicts_are_deeply_equal(v, d2[k])
            else:
                self.assertEqual(unicode(v), unicode(d2[k]))

    def test_list_public(self):
        with patch.object(
            self.C,
            'perform_request',
            return_value=self.FR()) as perform_req:
            r = self.client.list_public()
            self.assertEqual(self.client.http_client.url, self.url)
            self.assertEqual(self.client.http_client.path, '/images/')
            params = perform_req.call_args[0][3]
            self.assertEqual(params['sort_dir'], 'asc')
            for i in range(len(r)):
                self.assert_dicts_are_deeply_equal(r[i], example_images[i])

            r = self.client.list_public(order='-')
            params = perform_req.call_args[0][3]
            self.assertEqual(params['sort_dir'], 'desc')
            self.assertEqual(self.client.http_client.url, self.url)
            self.assertEqual(self.client.http_client.path, '/images/')

            r = self.client.list_public(detail=True)
            self.assertEqual(self.client.http_client.url, self.url)
            self.assertEqual(self.client.http_client.path, '/images/detail')

            size_max = 1000000000
            r = self.client.list_public(filters=dict(size_max=size_max))
            params = perform_req.call_args[0][3]
            self.assertEqual(params['size_max'], size_max)
            self.assertEqual(self.client.http_client.url, self.url)
            self.assertEqual(self.client.http_client.path, '/images/')

    """
    def test_get_meta(self):
        ""Test get_meta""
        self._test_get_meta()

    def _test_get_meta(self):
        r = self.client.get_meta(self['image', 'id'])
        self.assertEqual(r['id'], self['image', 'id'])
        for term in (
                'status',
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
            for interm in (
                    'kernel',
                    'osfamily',
                    'users',
                    'gui', 'sortorder',
                    'root-partition',
                    'os',
                    'description'):
                self.assertTrue(interm in r['properties'])

    def test_register(self):
        ""Test register""
        self._prepare_img()
        self._test_register()

    def _test_register(self):
        self.assertTrue(self._imglist)
        for img in self._imglist.values():
            self.assertTrue(img is not None)

    def test_reregister(self):
        ""Test reregister""
        self._prepare_img()
        self._test_reregister()

    def _test_reregister(self):
        self.client.reregister(
            self.location,
            properties=dict(my_property='some_value'))

    def test_set_members(self):
        ""Test set_members""
        self._prepare_img()
        self._test_set_members()

    def _test_set_members(self):
        members = ['%s@fake.net' % self.now]
        for img in self._imglist.values():
            self.client.set_members(img['id'], members)
            r = self.client.list_members(img['id'])
            self.assertEqual(r[0]['member_id'], members[0])

    def test_list_members(self):
        ""Test list_members""
        self._test_list_members()

    def _test_list_members(self):
        self._test_set_members()

    def test_remove_members(self):
        ""Test remove_members - NO CHECK""
        self._prepare_img()
        self._test_remove_members()

    def _test_remove_members(self):
        return
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
        ""Test list_shared - NOT CHECKED""
        self._test_list_shared()

    def _test_list_shared(self):
        #No way to test this, if I dont have member images
        pass
    """
