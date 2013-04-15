# Copyright 2013 GRNET S.A. All rights reserved.
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

from unittest import TestCase
from mock import patch, call
from tempfile import NamedTemporaryFile
from os import urandom

from kamaki.clients import ClientError
from kamaki.clients.storage import StorageClient as SC

client_pkg = 'kamaki.clients.Client'
storage_pkg = 'kamaki.clients.storage.StorageClient'

user_id = 'ac0un7-1d-5tr1ng'
obj = 'obj3c7N4m3'

account_info = {
    'content-language': 'en-us',
    'content-type': 'text/html; charset=utf-8',
    'date': 'Wed, 06 Mar 2013 13:25:51 GMT',
    'last-modified': 'Mon, 04 Mar 2013 18:22:31 GMT',
    'server': 'gunicorn/0.14.5',
    'vary': 'Accept-Language',
    'x-account-bytes-used': '751615526',
    'x-account-container-count': 7,
    'x-account-policy-quota': 53687091200,
    'x-account-policy-versioning': 'auto',
    'x-account-meta-k1': 'val1',
    'x-account-meta-k2': 'val2',
    'x-account-meta-k3': 'val3'}
container_info = {
    'content-language': 'en-us',
    'content-type': 'text/html; charset=utf-8',
    'date': 'Wed, 06 Mar 2013 15:11:05 GMT',
    'last-modified': 'Wed, 27 Feb 2013 15:56:13 GMT',
    'server': 'gunicorn/0.14.5',
    'vary': 'Accept-Language',
    'x-container-block-hash': 'sha256',
    'x-container-block-size': 4194304,
    'x-container-bytes-used': 309528938,
    'x-container-object-count': 14,
    'x-container-object-meta': '',
    'x-container-policy-quota': 53687091200,
    'x-container-policy-versioning': 'auto'}
object_info = {
    'content-language': 'en-us',
    'content-length': 254965,
    'content-type': 'application/octet-stream',
    'date': 'Thu, 07 Mar 2013 13:27:43 GMT',
    'etag': '',
    'last-modified': 'Mon, 04 Mar 2013 18:22:31 GMT',
    'server': 'gunicorn/0.14.5',
    'vary': 'Accept-Language',
    'x-object-hash': 'obj3c7h45h1s0bj3c7h45h411r34dY',
    'x-object-uuid': 'd0c747ca-34bd-49e0-8e98-1d07d8b0cbc7',
    'x-object-version': '525996',
    'x-object-version-timestamp': 'Mon, 04 Mar 2013 18:22:31 GMT',
    'x-object-meta-k1': 'v1',
    'x-object-meta-k2': 'v2'}
container_list = [
    dict(
        count=2,
        last_modified="2013-02-27T11:56:09.893033+00:00",
        bytes=677076979,
        name="pithos",
        x_container_policy=dict(quota="21474836480", versioning="auto")),
    dict(
        count=0,
        last_modified="2012-10-23T12:25:17.229187+00:00",
        bytes=0,
        name="trash",
        x_container_policy=dict(quota="21474836480", versioning="auto"))]
object_list = [
    dict(hash="",
        name="The_Secret_Garden.zip",
        x_object_public="/public/wdp9p",
        bytes=203304947,
        x_object_version_timestamp="1360237915.7027509",
        x_object_uuid="s0m3uu1df0r0bj0n3",
        last_modified="2013-02-07T11:51:55.702751+00:00",
        content_type="application/octet-stream",
        x_object_hash="0afdf29f71cd53126225c3f54ca",
        x_object_version=17737,
        x_object_modified_by=user_id),
    dict(hash="",
        name="The_Revealed_Garden.zip",
        x_object_public="/public/wpd7p",
        bytes=20330947,
        x_object_version_timestamp="13602915.7027509",
        x_object_uuid="s0m3uu1df0r0bj70w",
        last_modified="2013-02-07T11:51:55.702751+00:00",
        content_type="application/octet-stream",
        x_object_hash="0afdf29f71cd53126225c3f54ca",
        x_object_version=17737,
        x_object_modified_by=user_id)]


class FR(object):
    """FR stands for Fake Response"""
    json = dict()
    headers = dict()
    content = json
    status = None
    status_code = 200


class StorageClient(TestCase):

    files = []

    def _create_temp_file(self, num_of_blocks):
        self.files.append(NamedTemporaryFile())
        tmpFile = self.files[-1]
        file_size = num_of_blocks * 4 * 1024 * 1024
        print('\n\tCreate tmp file')
        tmpFile.write(urandom(file_size))
        tmpFile.flush()
        tmpFile.seek(0)
        print('\t\tDone')
        return tmpFile

    def assert_dicts_are_equal(self, d1, d2):
        for k, v in d1.items():
            self.assertTrue(k in d2)
            if isinstance(v, dict):
                self.assert_dicts_are_equal(v, d2[k])
            else:
                self.assertEqual(unicode(v), unicode(d2[k]))

    def setUp(self):
        self.url = 'https://www.example.com/pithos'
        self.token = 'p17h0570k3n'
        self.client = SC(self.url, self.token)
        self.client.account = user_id
        self.client.container = 'c0nt@1n3r_i'

    def tearDown(self):
        FR.headers = dict()
        FR.status_code = 200
        FR.json = dict()
        FR.content = FR.json
        for f in self.files:
            f.close()

    #  Pithos+ methods that extend storage API

    @patch('%s.head' % client_pkg, return_value=FR())
    def test_get_account_info(self, head):
        FR.headers = account_info
        r = self.client.get_account_info()
        self.assert_dicts_are_equal(account_info, r)
        head.assert_called_once_with(
            '/%s' % self.client.account,
            success=(204, 401))
        FR.status_code = 401
        self.assertRaises(ClientError, self.client.get_account_info)

    @patch('%s.post' % storage_pkg, return_value=FR())
    @patch('%s.set_header' % storage_pkg)
    def test_replace_account_meta(self, SH, post):
        metas = dict(k1='v1', k2='v2', k3='v3')
        self.client.replace_account_meta(metas)
        prfx = 'X-Account-Meta-'
        expected = [call('%s%s' % (prfx, k), v) for k, v in metas.items()]
        self.assertEqual(SH.mock_calls, expected)
        post.assert_called_once_with('/%s' % self.client.account, success=202)

    @patch('%s.post' % storage_pkg, return_value=FR())
    @patch('%s.get_account_info' % storage_pkg, return_value=account_info)
    def test_del_account_meta(self, GAI, post):
        prfx = 'x-account-meta-'
        keys = [k[len(prfx):] for k in account_info if k.startswith(prfx)]
        for key in keys:
            self.client.del_account_meta(key)
            self.assertEqual(
                post.mock_calls[-1],
                call('/%s' % self.client.account, success=202))
        self.assertEqual(len(keys), len(post.mock_calls))
        self.assertRaises(ClientError, self.client.del_account_meta, 'k4')

    @patch('%s.put' % storage_pkg, return_value=FR())
    def test_create_container(self, put):
        cont = 's0m3c0n731n3r'
        self.client.create_container(cont)
        args = (user_id, cont)
        put.assert_called_once_with('/%s/%s' % args, success=(201, 202))
        FR.status_code = 202
        self.assertRaises(ClientError, self.client.create_container, cont)

    @patch('%s.head' % storage_pkg, return_value=FR())
    def test_get_container_info(self, head):
        FR.headers = container_info
        cont = self.client.container
        r = self.client.get_container_info(cont)
        self.assert_dicts_are_equal(r, container_info)
        path = '/%s/%s' % (self.client.account, cont)
        head.assert_called_once_with(path, success=(204, 404))
        FR.status_code = 404
        self.assertRaises(ClientError, self.client.get_container_info, cont)

    @patch('%s.delete' % storage_pkg, return_value=FR())
    def test_delete_container(self, delete):
        FR.status_code = 204
        cont = 's0m3c0n731n3r'
        self.client.delete_container(cont)
        for err_code in (404, 409):
            FR.status_code = err_code
            self.assertRaises(ClientError, self.client.delete_container, cont)
        acall = call('/%s/%s' % (user_id, cont), success=(204, 404, 409))
        self.assertEqual(delete.mock_calls, [acall] * 3)

    @patch('%s.get' % storage_pkg, return_value=FR())
    @patch('%s.set_param' % storage_pkg)
    def test_list_containers(self, SP, get):
        FR.json, acc = container_list, self.client.account
        r = self.client.list_containers()
        SP.assert_called_once_with('format', 'json')
        get.assert_called_once_with('/%s' % acc, success=(200, 204))
        for i in range(len(r)):
            self.assert_dicts_are_equal(r[i], container_list[i])

    @patch('%s.put' % storage_pkg, return_value=FR())
    def test_upload_object(self, put):
        (acc, cont) = (self.client.account, self.client.container)
        num_of_blocks = 4
        tmpFile = self._create_temp_file(num_of_blocks)
        tmpFile.seek(0, 2)
        sizes = [None, (tmpFile.tell() / num_of_blocks) / 2]
        for size in sizes:
            tmpFile.seek(0)
            self.client.upload_object(obj, tmpFile, size)
            tmpFile.seek(0)
            self.assertEqual(put.mock_calls[-1], call(
                '/%s/%s/%s' % (acc, cont, obj),
                data=tmpFile.read(size) if size else tmpFile.read(),
                success=201))

    @patch('%s.put' % storage_pkg, return_value=FR())
    @patch('%s.set_header' % storage_pkg)
    def test_create_object(self, SH, put):
        cont = self.client.container
        ctype = 'c0n73n7/typ3'
        exp_shd = [
            call('Content-Type', 'application/octet-stream'),
            call('Content-length', '0'),
            call('Content-Type', ctype), call('Content-length', '42')]
        exp_put = [call('/%s/%s/%s' % (user_id, cont, obj), success=201)] * 2
        self.client.create_object(obj)
        self.client.create_object(obj, content_type=ctype, content_length=42)
        self.assertEqual(SH.mock_calls, exp_shd)
        self.assertEqual(put.mock_calls, exp_put)

    @patch('%s.put' % storage_pkg, return_value=FR())
    @patch('%s.set_header' % client_pkg)
    def test_create_directory(self, SH, put):
        cont = self.client.container
        exp_shd = [
            call('Content-Type', 'application/directory'),
            call('Content-length', '0')]
        exp_put = [call('/%s/%s/%s' % (user_id, cont, obj), success=201)]
        self.client.create_directory(obj)
        self.assertEqual(SH.mock_calls, exp_shd)
        self.assertEqual(put.mock_calls, exp_put)

    @patch('%s.head' % storage_pkg, return_value=FR())
    def test_get_object_info(self, head):
        FR.headers = object_info
        path = '/%s/%s/%s' % (self.client.account, self.client.container, obj)
        r = self.client.get_object_info(obj)
        head.assert_called_once_with(path, success=200)
        self.assertEqual(r, object_info)

    @patch('%s.get_object_info' % storage_pkg, return_value=object_info)
    def test_get_object_meta(self, GOI):
        r = self.client.get_object_meta(obj)
        GOI.assert_called_once_with(obj)
        prfx = 'x-object-meta-'
        for k in [k for k in object_info if k.startswith(prfx)]:
            self.assertEqual(r.pop(k[len(prfx):]), object_info[k])
        self.assertFalse(len(r))

    @patch('%s.post' % storage_pkg, return_value=FR())
    @patch('%s.set_header' % storage_pkg)
    def test_del_object_meta(self, SH, post):
        key = '50m3m3t4k3y'
        self.client.del_object_meta(obj, key)
        prfx = 'X-Object-Meta-'
        SH.assert_called_once_with('%s%s' % (prfx, key), '')
        exp = '/%s/%s/%s' % (self.client.account, self.client.container, obj)
        post.assert_called_once_with(exp, success=202)

    @patch('%s.post' % client_pkg, return_value=FR())
    @patch('%s.set_header' % client_pkg)
    def test_replace_object_meta(self, SH, post):
        metas = dict(k1='new1', k2='new2', k3='new3')
        cont = self.client.container
        self.client.replace_object_meta(metas)
        post.assert_called_once_with('/%s/%s' % (user_id, cont), success=202)
        prfx = 'X-Object-Meta-'
        expected = [call('%s%s' % (prfx, k), v) for k, v in metas.items()]
        self.assertEqual(SH.mock_calls, expected)

    @patch('%s.put' % storage_pkg, return_value=FR())
    @patch('%s.set_header' % storage_pkg)
    def test_copy_object(self, SH, put):
        src_cont = 'src-c0nt41n3r'
        src_obj = 'src-0bj'
        dst_cont = 'dst-c0nt41n3r'
        for dst_obj in (None, 'dst-0bj'):
            dst_path = dst_obj or src_obj
            path = '/%s/%s/%s' % (self.client.account, dst_cont, dst_path)
            self.client.copy_object(src_cont, src_obj, dst_cont, dst_obj)
            self.assertEqual(put.mock_calls[-1], call(path, success=201))
            kwargs = {
                'X-Copy-From': '/%s/%s' % (src_cont, src_obj),
                'Content-Length': 0}
            self.assertEqual(
                SH.mock_calls[-2:],
                [call(k, v) for k, v in kwargs.items()])

    @patch('%s.put' % storage_pkg, return_value=FR())
    @patch('%s.set_header' % storage_pkg)
    def test_move_object(self, SH, put):
        src_cont = 'src-c0nt41n3r'
        src_obj = 'src-0bj'
        dst_cont = 'dst-c0nt41n3r'
        for dst_obj in (None, 'dst-0bj'):
            dst_path = dst_obj or src_obj
            path = '/%s/%s/%s' % (self.client.account, dst_cont, dst_path)
            self.client.move_object(src_cont, src_obj, dst_cont, dst_obj)
            self.assertEqual(put.mock_calls[-1], call(path, success=201))
            kwargs = {
                'X-Move-From': '/%s/%s' % (src_cont, src_obj),
                'Content-Length': 0}
            self.assertEqual(
                SH.mock_calls[-2:],
                [call(k, v) for k, v in kwargs.items()])

    @patch('%s.delete' % storage_pkg, return_value=FR())
    def test_delete_object(self, delete):
        cont = self.client.container
        self.client.delete_object(obj)
        exp = '/%s/%s/%s' % (user_id, cont, obj)
        delete.assert_called_once_with(exp, success=(204, 404))
        FR.status_code = 404
        self.assertRaises(ClientError, self.client.delete_object, obj)

    @patch('%s.get' % client_pkg, return_value=FR())
    @patch('%s.set_param' % client_pkg)
    def test_list_objects(self, SP, get):
        FR.json = object_list
        acc, cont = self.client.account, self.client.container
        r = self.client.list_objects()
        for i in range(len(r)):
            self.assert_dicts_are_equal(r[i], object_list[i])
        exp = '/%s/%s' % (acc, cont)
        get.assert_called_once_with(exp, success=(200, 204, 304, 404))
        self.assertEqual(SP.mock_calls, [
            call('format', 'json'),
            call('limit', None, iff=None),
            call('marker', None, iff=None),
            call('prefix', None, iff=None),
            call('delimiter', None, iff=None)])
        self.client.list_objects(
            format='xml', limit=10, marker='X', path='/lala')
        self.assertEqual(SP.mock_calls[-4:], [
            call('format', 'xml'),
            call('limit', 10, iff=10),
            call('marker', 'X', iff='X'),
            call('path', '/lala')])
        self.client.list_objects(delimiter='X', prefix='/lala')
        self.assertEqual(SP.mock_calls[-5:], [
            call('format', 'json'),
            call('limit', None, iff=None),
            call('marker', None, iff=None),
            call('prefix', '/lala', iff='/lala'),
            call('delimiter', 'X', iff='X'),
            ])
        FR.status_code = 304
        self.assertEqual(self.client.list_objects(), [])
        FR.status_code = 404
        self.assertRaises(ClientError, self.client.list_objects)

    @patch('%s.get' % client_pkg, return_value=FR())
    @patch('%s.set_param' % client_pkg)
    def test_list_objects_in_path(self, SP, get):
        FR.json = object_list
        path = '/some/awsome/path'
        acc, cont = self.client.account, self.client.container
        self.client.list_objects_in_path(path)
        exp = '/%s/%s' % (acc, cont)
        get.assert_called_once_with(exp, success=(200, 204, 404))
        self.assertEqual(
            SP.mock_calls,
            [call('format', 'json'), call('path', path)])
        FR.status_code = 404
        self.assertRaises(ClientError, self.client.list_objects)

if __name__ == '__main__':
    from sys import argv
    from kamaki.clients.test import runTestCase
    runTestCase(StorageClient, 'Storage Client', argv[1:])
