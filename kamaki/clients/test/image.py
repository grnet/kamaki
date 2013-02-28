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

example_images_detailed = [
    {
        "status": "available",
        "name": "Archlinux",
        "checksum": "1a126aad07475b43cc1959b446344211be13974",
        "created_at": "2013-01-28 22:44:54",
        "disk_format": "diskdump",
        "updated_at": "2013-01-28 22:44:55",
        "properties": {
            "partition_table": "msdos",
            "osfamily": "linux",
            "users": "root",
            "exclude_task_assignhostname": "yes",
            "os": "archlinux",
            "root_partition": "1",
            "description": "Archlinux base install 2012.12.01"},
        "location": "pithos://us3r-I6E-1d/images/archlinux.12.2012",
        "container_format": "bare",
        "owner": "user163@mail.example.com",
        "is_public": True,
        "deleted_at": "",
        "id": "b4713f20-3a41-4eaf-81ae-88698c18b3e8",
        "size": 752782848},
    {
        "status": "available",
        "name": "maelstrom",
        "checksum": "b202b8c7030cb22f896c6664ac",
        "created_at": "2013-02-13 10:07:42",
        "disk_format": "diskdump",
        "updated_at": "2013-02-13 10:07:44",
        "properties": {
            "partition_table": "msdos",
            "osfamily": "linux",
            "description": "Ubuntu 12.04.1 LTS",
            "os": "ubuntu",
            "root_partition": "1",
            "users": "user"},
        "location": "pithos://us3r-@r3n@-1d/images/mls-201302131203.diskdump",
        "container_format": "bare",
        "owner": "user3@mail.example.com",
        "is_public": True,
        "deleted_at": "",
        "id": "0fb03e45-7d5a-4515-bd4e-e6bbf6457f06",
        "size": 2583195648},
    {
        "status": "available",
        "name": "Gardenia",
        "checksum": "06d3099815d1f6fada91e80107638b882",
        "created_at": "2013-02-13 12:35:21",
        "disk_format": "diskdump",
        "updated_at": "2013-02-13 12:35:23",
        "properties": {
            "partition_table": "msdos",
            "osfamily": "linux",
            "description": "Ubuntu 12.04.2 LTS",
            "os": "ubuntu",
            "root_partition": "1",
            "users": "user"},
        "location": "pithos://us3r-E-1d/images/Gardenia-201302131431.diskdump",
        "container_format": "bare",
        "owner": "user3@mail.example.com",
        "is_public": True,
        "deleted_at": "",
        "id": "5963020b-ab74-4e11-bc59-90c494bbdedb",
        "size": 2589802496}]


class Image(TestCase):

    class FR(object):
        json = example_images
        headers = {}
        content = json
        status = None
        status_code = 200

        def release(self):
            pass

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
        self.FR.status_code = 200

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

            self.FR.json = example_images_detailed
            r = self.client.list_public(detail=True)
            self.assertEqual(self.client.http_client.url, self.url)
            self.assertEqual(self.client.http_client.path, '/images/detail')
            for i in range(len(r)):
                self.assert_dicts_are_deeply_equal(
                    r[i],
                    example_images_detailed[i])

            size_max = 1000000000
            r = self.client.list_public(filters=dict(size_max=size_max))
            params = perform_req.call_args[0][3]
            self.assertEqual(params['size_max'], size_max)
            self.assertEqual(self.client.http_client.url, self.url)
            self.assertEqual(self.client.http_client.path, '/images/')

    def test_get_meta(self):
        img0 = example_images[0]
        self.FR.json = img0
        img0_headers = {}
        for k, v in example_images_detailed[0].items():
            img0_headers['x-image-meta-%s' % k] = v
        self.FR.headers = img0_headers
        with patch.object(self.C, 'perform_request', return_value=self.FR()):
            r = self.client.get_meta(img0['id'])
            self.assertEqual(self.client.http_client.url, self.url)
            expected_path = '/images/%s' % img0['id']
            self.assertEqual(self.client.http_client.path, expected_path)

            self.assertEqual(r['id'], img0['id'])
            self.assert_dicts_are_deeply_equal(r, example_images_detailed[0])

    def test_register(self):
        img0 = example_images_detailed[0]
        img0_location = img0['location']
        img0_name = 'A new img0 name'
        with patch.object(
                self.C,
                'perform_request',
                return_value=self.FR()) as perform_req:
            self.client.register(img0_name, img0_location)
            self.assertEqual(self.client.http_client.url, self.url)
            self.assertEqual(self.client.http_client.path, '/images/')
            (method, data, headers, params) = perform_req.call_args[0]
            self.assertEqual(method, 'post')
            self.assertTrue(0 == len(params))

            val = 'Some random value'
            param_dict = dict(
                id=val,
                store=val,
                disk_format=val,
                container_format=val,
                size=val,
                checksum=val,
                is_public=val,
                owner=val)
            for key in param_dict.keys():
                param = {key: val}
                self.client.register(img0_name, img0_location, params=param)
                (method, data, a_headers, a_params) = perform_req.call_args[0]
                key = 'x-image-meta-%s' % key.replace('_', '-')
                self.assertEqual(a_headers[key], val)
            self.client.register(img0_name, img0_location, params=param_dict)
            (method, data, a_headers, a_params) = perform_req.call_args[0]
            self.assertEqual(len(param_dict), len(a_headers))
            for key, val in param_dict.items():
                key = 'x-image-meta-%s' % key.replace('_', '-')
                self.assertEqual(a_headers[key], val)

            props = dict(key0='val0', key2='val2', key3='val3')
            self.client.register(img0_name, img0_location, properties=props)
            (method, data, a_headers, a_params) = perform_req.call_args[0]
            for k, v in props.items():
                self.assertEquals(a_headers['X-Image-Meta-Property-%s' % k], v)

    def test_set_members(self):
        img0 = example_images_detailed[0]
        members = ['use3r-1d-0', 'us2r-1d-1', 'us3r-1d-2']
        with patch.object(
                self.C,
                'perform_request',
                return_value=self.FR()) as perform_req:
            self.assertRaises(
                ClientError,
                self.client.set_members,
                img0['id'], members)
            self.FR.status_code = 204
            self.client.set_members(img0['id'], members)
            self.assertEqual(self.client.http_client.url, self.url)
            self.assertEqual(
                    self.client.http_client.path,
                '/images/%s/members' % img0['id'])
            (method, data, a_headers, a_params) = perform_req.call_args[0]
            from json import loads
            memberships = loads(data)['memberships']
            for membership in memberships:
                self.assertTrue(membership['member_id'] in members)

    def test_list_members(self):
        img0 = example_images_detailed[0]
        members = ['use3r-1d-0', 'us2r-1d-1', 'us3r-1d-2']
        self.FR.json = dict(members=members)
        with patch.object(self.C, 'perform_request', return_value=self.FR()):
            r = self.client.list_members(img0['id'])
            self.assertEqual(self.client.http_client.url, self.url)
            self.assertEqual(
                self.client.http_client.path,
                '/images/%s/members' % img0['id'])
            self.assertEqual(r, members)

    def test_add_member(self):
        img0 = example_images_detailed[0]
        new_member = 'us3r-15-n3w'
        with patch.object(self.C, 'perform_request', return_value=self.FR()):
            self.assertRaises(
                ClientError,
                self.client.set_members,
                img0['id'], new_member)
            self.FR.status_code = 204
            self.client.add_member(img0['id'], new_member)
            self.assertEqual(self.client.http_client.url, self.url)
            self.assertEqual(
                self.client.http_client.path,
                '/images/%s/members/%s' % (img0['id'], new_member))

    """
    def test_remove_members(self):
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
        #No way to test this, if I dont have member images
        pass
    """
