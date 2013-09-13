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

example_image_headers = {
    'x-image-meta-id': '3edd4d15-41b4-4a39-9601-015ef56b3bb3',
    'x-image-meta-checksum': 'df23837c30889252c0aed80b6f770a53a86',
    'x-image-meta-container-format': 'bare',
    'x-image-meta-location': 'pithos://a13528163db/con/obj_13.0',
    'x-image-meta-disk-format': 'diskdump',
    'x-image-meta-is-public': 'True',
    'x-image-meta-status': 'available',
    'x-image-meta-deleted-at': '',
    'x-image-meta-updated-at': '2013-04-11 15:22:39',
    'x-image-meta-created-at': '2013-04-11 15:22:37',
    'x-image-meta-owner': 'a13529bb3c3db',
    'x-image-meta-size': '1073741824',
    'x-image-meta-name': 'img_1365686546.0',
    'extraheaders': 'should be ignored'
}
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
imgid = "b4713f20-3a41-4eaf-81ae-88698c18b3e8"
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

image_pkg = 'kamaki.clients.image.ImageClient'


class ImageClient(TestCase):

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
        from kamaki.clients import image
        self.client = image.ImageClient(self.url, self.token)

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

    @patch('%s.head' % image_pkg, return_value=FR())
    def test_get_meta(self, head):
        img0 = example_images[0]
        FR.json = img0
        img0_headers = {}
        for k, v in example_images_detailed[0].items():
            img0_headers['x-image-meta-%s' % k] = v
        FR.headers = img0_headers
        r = self.client.get_meta(img0['id'])
        head.assert_called_once_with('/images/%s' % img0['id'], success=200)
        self.assertEqual(r['id'], img0['id'])
        self.assert_dicts_are_equal(r, example_images_detailed[0])

    @patch('%s.set_header' % image_pkg, return_value=FR())
    @patch('%s.post' % image_pkg, return_value=FR())
    def test_register(self, post, SH):
        img0 = example_images_detailed[0]
        FR.headers = example_image_headers
        img0_location = img0['location']
        img0_name = 'A new img0 name'
        prfx = 'x-image-meta-'
        proprfx = 'x-image-meta-property-'
        keys = [
            'id', 'store', 'dist_format', 'container_format',
            'size', 'checksum', 'is_public', 'owner']
        for args in product(
                ('v_id', None), ('v_store', None),
                ('v_dist_format', None), ('v_container_format', None),
                ('v_size', None), ('v_checksum', None),
                ('v_is_public', None), ('v_owner', None)):
            params = dict()
            async_headers = dict()
            props = dict()
            for i, k in enumerate(keys):
                if args[i]:
                    params[k] = args[i]
                    async_headers['%s%s' % (prfx, k)] = args[i]
                    props['%s%s' % (proprfx, args[i])] = k
            async_headers.update(props)
        r = self.client.register(
            img0_name, img0_location, params=params, properties=props)
        expectedict = dict(example_image_headers)
        expectedict.pop('extraheaders')
        from kamaki.clients.image import _format_image_headers
        self.assert_dicts_are_equal(_format_image_headers(expectedict), r)
        self.assertEqual(
            post.mock_calls[-1],
            call('/images/', async_headers=async_headers, success=200))
        self.assertEqual(SH.mock_calls[-2:], [
            call('X-Image-Meta-Name', img0_name),
            call('X-Image-Meta-Location', img0_location)])
        img1_location = ('some_uuid', 'some_container', 'some/path')
        r = self.client.register(
            img0_name, img1_location, params=params, properties=props)
        img1_location = 'pithos://%s' % '/'.join(img1_location)
        self.assertEqual(SH.mock_calls[-2:], [
            call('X-Image-Meta-Name', img0_name),
            call('X-Image-Meta-Location', img1_location)])

    @patch('%s.delete' % image_pkg)
    def test_unregister(self, delete):
        img_id = 'an1m4g3'
        self.client.unregister(img_id)
        delete.assert_called_once_with('/images/%s' % img_id, success=204)

    @patch('%s.put' % image_pkg, return_value=FR())
    def test_set_members(self, put):
        members = ['use3r-1d-0', 'us2r-1d-1', 'us3r-1d-2']
        self.client.set_members(imgid, members)
        put.assert_called_once_with(
            '/images/%s/members' % imgid,
            json=dict(memberships=[dict(member_id=m) for m in members]),
            success=204)

    @patch('%s.get' % image_pkg, return_value=FR())
    def test_list_members(self, get):
        members = ['use3r-1d-0', 'us2r-1d-1', 'us3r-1d-2']
        FR.json = dict(members=members)
        r = self.client.list_members(imgid)
        get.assert_called_once_with('/images/%s/members' % imgid, success=200)
        self.assertEqual(r, members)

    @patch('%s.put' % image_pkg, return_value=FR())
    def test_add_member(self, put):
        new_member = 'us3r-15-n3w'
        self.client.add_member(imgid, new_member)
        put.assert_called_once_with(
            '/images/%s/members/%s' % (imgid, new_member),
            success=204)

    @patch('%s.delete' % image_pkg, return_value=FR())
    def test_remove_member(self, delete):
        old_member = 'us3r-15-0ld'
        self.client.remove_member(imgid, old_member)
        delete.assert_called_once_with(
            '/images/%s/members/%s' % (imgid, old_member),
            success=204)

    @patch('%s.get' % image_pkg, return_value=FR())
    def test_list_shared(self, get):
        FR.json = dict(shared_images=example_images)
        r = self.client.list_shared(imgid)
        get.assert_called_once_with('/shared-images/%s' % imgid, success=200)
        for i in range(len(r)):
            self.assert_dicts_are_equal(r[i], example_images[i])

    @patch('%s.put' % image_pkg, return_value=FR())
    @patch('%s.set_header' % image_pkg)
    def test_update_image(self, set_header, put):
        FR.headers = 'some headers'
        hcnt = 0
        for args in product(
                ('some id', 'other id'),
                ('image name', None), ('disk fmt', None), ('cnt format', None),
                ('status', None), (True, False, None), ('owner id', None),
                (dict(k1='v1', k2='v2'), {})):
            r = self.client.update_image(*args[:-1], **args[-1])
            (image_id, name, disk_format, container_format,
            status, public, owner_id, properties) = args
            self.assertEqual(r, FR.headers)
            header_calls = [call('Content-Length', 0), ]
            prf = 'X-Image-Meta-'
            if name:
                header_calls.append(call('%sName' % prf, name))
            if disk_format:
                header_calls.append(call('%sDisk-Format' % prf, disk_format))
            if container_format:
                header_calls.append(
                    call('%sContainer-Format' % prf, container_format))
            if status:
                header_calls.append(call('%sStatus' % prf, status))
            if public is not None:
                header_calls.append(call('%sIs-Public' % prf, public))
            if owner_id:
                header_calls.append(call('%sOwner' % prf, owner_id))
            for k, v in properties.items():
                header_calls.append(call('%sProperty-%s' % (prf, k), v))
            self.assertEqual(
                sorted(set_header.mock_calls[hcnt:]), sorted(header_calls))
            hcnt = len(set_header.mock_calls)
            self.assertEqual(
                put.mock_calls[-1], call('/images/%s' % image_id, success=200))


if __name__ == '__main__':
    from sys import argv
    from kamaki.clients.test import runTestCase
    runTestCase(ImageClient, 'Plankton Client', argv[1:])
