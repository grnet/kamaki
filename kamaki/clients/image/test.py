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

from mock import patch, call
from unittest import TestCase
from itertools import product

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


class FR(object):
    json = example_images
    headers = {}
    content = json
    status = None
    status_code = 200

    def release(self):
        pass

khttp = 'kamaki.clients.connection.kamakicon.KamakiHTTPConnection'
image_pkg = 'kamaki.clients.image.ImageClient'


class Image(TestCase):

    def assert_dicts_are_equal(self, d1, d2):
        for k, v in d1.items():
            self.assertTrue(k in d2)
            if isinstance(v, dict):
                self.assert_dicts_are_equal(v, d2[k])
            else:
                self.assertEqual(unicode(v), unicode(d2[k]))

    def setUp(self):
        self.url = 'http://image.example.com'
        self.token = 'an1m@g370k3n=='
        from kamaki.clients.image import ImageClient
        self.client = ImageClient(self.url, self.token)
        from kamaki.clients.connection.kamakicon import KamakiHTTPConnection
        self.C = KamakiHTTPConnection

    def tearDown(self):
        FR.json = example_images
        FR.status_code = 200

    @patch('%s.get' % image_pkg, return_value=FR())
    def test_list_public(self, get):
        a_filter = dict(size_max=42)
        for args in product((False, True), ({}, a_filter), ('', '-')):
            (detail, filters, order) = args
            r = self.client.list_public(*args)
            filters['sort_dir'] = 'desc' if order.startswith('-') else 'asc'
            self.assertEqual(get.mock_calls[-1], call(
                '/images/%s' % ('detail' if detail else ''),
                async_params=filters, success=200))
            for i in range(len(r)):
                self.assert_dicts_are_equal(r[i], example_images[i])

    @patch('%s.perform_request' % khttp, return_value=FR())
    def test_get_meta(self, PR):
        img0 = example_images[0]
        FR.json = img0
        img0_headers = {}
        for k, v in example_images_detailed[0].items():
            img0_headers['x-image-meta-%s' % k] = v
        FR.headers = img0_headers
        r = self.client.get_meta(img0['id'])
        self.assertEqual(self.client.http_client.url, self.url)
        expected_path = '/images/%s' % img0['id']
        self.assertEqual(self.client.http_client.path, expected_path)

        self.assertEqual(r['id'], img0['id'])
        self.assert_dicts_are_equal(r, example_images_detailed[0])

    @patch('%s.perform_request' % khttp, return_value=FR())
    def test_register(self, PR):
        img0 = example_images_detailed[0]
        img0_location = img0['location']
        img0_name = 'A new img0 name'
        self.client.register(img0_name, img0_location)
        self.assertEqual(self.client.http_client.url, self.url)
        self.assertEqual(self.client.http_client.path, '/images/')
        (method, data, headers, params) = PR.call_args[0]
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
            (method, data, a_headers, a_params) = PR.call_args[0]
            key = 'x-image-meta-%s' % key.replace('_', '-')
            self.assertEqual(a_headers[key], val)
        self.client.register(img0_name, img0_location, params=param_dict)
        (method, data, a_headers, a_params) = PR.call_args[0]
        self.assertEqual(len(param_dict), len(a_headers))
        for key, val in param_dict.items():
            key = 'x-image-meta-%s' % key.replace('_', '-')
            self.assertEqual(a_headers[key], val)

        props = dict(key0='val0', key2='val2', key3='val3')
        self.client.register(img0_name, img0_location, properties=props)
        (method, data, a_headers, a_params) = PR.call_args[0]
        for k, v in props.items():
            self.assertEquals(a_headers['X-Image-Meta-Property-%s' % k], v)

    @patch('%s.perform_request' % khttp, return_value=FR())
    def test_set_members(self, PR):
        img0 = example_images_detailed[0]
        members = ['use3r-1d-0', 'us2r-1d-1', 'us3r-1d-2']
        self.assertRaises(
            ClientError,
            self.client.set_members,
            img0['id'], members)
        FR.status_code = 204
        self.client.set_members(img0['id'], members)
        self.assertEqual(self.client.http_client.url, self.url)
        self.assertEqual(
                self.client.http_client.path,
            '/images/%s/members' % img0['id'])
        (method, data, a_headers, a_params) = PR.call_args[0]
        from json import loads
        memberships = loads(data)['memberships']
        for membership in memberships:
            self.assertTrue(membership['member_id'] in members)

    @patch('%s.perform_request' % khttp, return_value=FR())
    def test_list_members(self, PR):
        img0 = example_images_detailed[0]
        members = ['use3r-1d-0', 'us2r-1d-1', 'us3r-1d-2']
        FR.json = dict(members=members)
        r = self.client.list_members(img0['id'])
        self.assertEqual(self.client.http_client.url, self.url)
        self.assertEqual(
            self.client.http_client.path,
            '/images/%s/members' % img0['id'])
        self.assertEqual(r, members)

    @patch('%s.perform_request' % khttp, return_value=FR())
    def test_add_member(self, PR):
        img0 = example_images_detailed[0]
        new_member = 'us3r-15-n3w'
        self.assertRaises(
            ClientError,
            self.client.add_member,
            img0['id'], new_member)
        FR.status_code = 204
        self.client.add_member(img0['id'], new_member)
        self.assertEqual(self.client.http_client.url, self.url)
        self.assertEqual(
            self.client.http_client.path,
            '/images/%s/members/%s' % (img0['id'], new_member))

    @patch('%s.perform_request' % khttp, return_value=FR())
    def test_remove_member(self, PR):
        img0 = example_images_detailed[0]
        old_member = 'us3r-15-0ld'
        self.assertRaises(
            ClientError,
            self.client.remove_member,
            img0['id'], old_member)
        FR.status_code = 204
        self.client.remove_member(img0['id'], old_member)
        self.assertEqual(self.client.http_client.url, self.url)
        self.assertEqual(
            self.client.http_client.path,
            '/images/%s/members/%s' % (img0['id'], old_member))

    @patch('%s.perform_request' % khttp, return_value=FR())
    def test_list_shared(self, PR):
        img0 = example_images_detailed[0]
        FR.json = dict(shared_images=example_images)
        r = self.client.list_shared(img0['id'])
        self.assertEqual(self.client.http_client.url, self.url)
        self.assertEqual(
            self.client.http_client.path,
            '/shared-images/%s' % img0['id'])
        for i in range(len(r)):
            self.assert_dicts_are_equal(r[i], example_images[i])

if __name__ == '__main__':
    from sys import argv
    from kamaki.clients.test import runTestCase
    runTestCase(Image, 'Plankton Client', argv[1:])
