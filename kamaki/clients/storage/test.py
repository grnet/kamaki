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
from kamaki.clients.connection.kamakicon import KamakiHTTPConnection as C

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
object_hashmap = dict(
    block_hash="sha256", block_size=4194304, bytes=33554432,
    hashes=[
        "4988438cc1c0292c085d289649b28cf547ba3db71c6efaac9f2df7e193d4d0af",
        "b214244aa56df7d1df7c6cac066e7cef268d9c2beb4dcf7ce68af667b0626f91",
        "17f365f25e0682565ded30576066bb13377a3d306967e4d74e06bb6bbc20f75f",
        "2524ae208932669fff89adf8a2fc0df3b67736ca0d3aadce7a2ce640f142af37",
        "5d807a2129d2fcd3c221c3da418ed52af3fc48d0817b62e0bb437acffccd3514",
        "609de22ce842d997f645fc49d5f14e0e3766dd51a6cbe66383b2bab82c8dfcd0",
        "3102851ac168c78be70e35ff5178c7b1ebebd589e5106d565ca1094d1ca8ff59",
        "bfe306dd24e92a8d85caf7055643f250fd319e8c4cdd4755ddabbf3ff97e83c7"])
sharers = [
    dict(last_modified="2013-01-29T16:50:06.084674+00:00", name="0b1a-82d5"),
    dict(last_modified="2013-01-29T16:50:06.084674+00:00", name="0b2a-f2d5"),
    dict(last_modified="2013-01-29T16:50:06.084674+00:00", name="2b1a-82d6")]


class FR(object):
    """FR stands for Fake Response"""
    json = dict()
    headers = dict()
    content = json
    status = None
    status_code = 200

    def release(self):
        pass


class Storage(TestCase):

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
        self.assertEqual(
            head.mock_calls[-1],
            call('/%s' % self.client.account, success=(204, 401)))
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
        self.assertEqual(
            post.mock_calls[-1],
            call('/%s' % self.client.account, success=202))

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
        expected = call('/%s/%s' % (user_id, cont), success=(201, 202))
        self.assertEqual(put.mock_calls[-1], expected)
        FR.status_code = 202
        self.assertRaises(ClientError, self.client.create_container, cont)

    @patch('%s.head' % storage_pkg, return_value=FR())
    def test_get_container_info(self, head):
        FR.headers = container_info
        cont = self.client.container
        r = self.client.get_container_info(cont)
        self.assert_dicts_are_equal(r, container_info)
        path = '/%s/%s' % (self.client.account, cont)
        self.assertEqual(head.mock_calls[-1], call(path, success=(204, 404)))
        FR.status_code = 404
        self.assertRaises(ClientError, self.client.get_container_info, cont)

    """
    @patch('%s.delete' % pithos_pkg, return_value=FR())
    def test_delete_container(self, delete):
        FR.status_code = 204
        cont = 's0m3c0n731n3r'
        self.client.delete_container(cont)
        for err_code in (404, 409):
            FR.status_code = err_code
            self.assertRaises(ClientError, self.client.delete_container, cont)
        acall = call('/%s/%s' % (user_id, cont), success=(204, 404, 409))
        self.assertEqual(delete.mock_calls, [acall] * 3)

    @patch('%s.account_get' % pithos_pkg, return_value=FR())
    def test_list_containers(self, get):
        FR.json = container_list
        r = self.client.list_containers()
        for i in range(len(r)):
            self.assert_dicts_are_equal(r[i], container_list[i])

    @patch('%s.get_container_info' % pithos_pkg, return_value=container_info)
    @patch('%s.container_post' % pithos_pkg, return_value=FR())
    @patch('%s.object_put' % pithos_pkg, return_value=FR())
    def test_upload_object(self, CI, CP, OP):
        num_of_blocks = 8
        tmpFile = self._create_temp_file(num_of_blocks)

        # Without kwargs
        self.client.upload_object(obj, tmpFile)
        self.assertEqual(PC.get_container_info.mock_calls, [call()])
        [call1, call2] = PC.object_put.mock_calls

        (args1, kwargs1) = call1[1:3]
        (args2, kwargs2) = call2[1:3]
        self.assertEqual(args1, (obj,))
        expected1 = dict(
            hashmap=True,
            success=(201, 409),
            format='json',
            json=dict(
                hashes=['s0m3h@5h'] * num_of_blocks,
                bytes=num_of_blocks * 4 * 1024 * 1024),
            etag=None,
            content_encoding=None,
            content_type='application/octet-stream',
            content_disposition=None,
            public=None,
            permissions=None)
        for k, v in expected1.items():
            if k == 'json':
                self.assertEqual(len(v['hashes']), len(kwargs1[k]['hashes']))
                self.assertEqual(v['bytes'], kwargs1[k]['bytes'])
            else:
                self.assertEqual(v, kwargs1[k])

        (args2, kwargs2) = call2[1:3]
        self.assertEqual(args2, (obj,))
        expected2 = dict(
            json=dict(
                hashes=['s0m3h@5h'] * num_of_blocks,
                bytes=num_of_blocks * 4 * 1024 * 1024),
            content_type='application/octet-stream',
            hashmap=True,
            success=201,
            format='json')
        for k, v in expected2.items():
            if k == 'json':
                self.assertEqual(len(v['hashes']), len(kwargs2[k]['hashes']))
                self.assertEqual(v['bytes'], kwargs2[k]['bytes'])
            else:
                self.assertEqual(v, kwargs2[k])

        OP = PC.object_put
        mock_offset = 2

        #  With progress bars
        try:
            from progress.bar import ShadyBar
            blck_bar = ShadyBar('Mock blck calc.')
            upld_bar = ShadyBar('Mock uplds')
        except ImportError:
            blck_bar = None
            upld_bar = None

        if blck_bar and upld_bar:

            def blck_gen(n):
                for i in blck_bar.iter(range(n)):
                    yield
                yield

            def upld_gen(n):
                for i in upld_bar.iter(range(n)):
                    yield
                yield

            tmpFile.seek(0)
            self.client.upload_object(
                obj, tmpFile,
                hash_cb=blck_gen, upload_cb=upld_gen)

            for i, c in enumerate(OP.mock_calls[-mock_offset:]):
                self.assertEqual(OP.mock_calls[i], c)

        #  With content-type
        tmpFile.seek(0)
        ctype = 'video/mpeg'
        sharing = dict(read=['u1', 'g1', 'u2'], write=['u1'])
        self.client.upload_object(obj, tmpFile,
            content_type=ctype, sharing=sharing)
        self.assertEqual(OP.mock_calls[-1][2]['content_type'], ctype)
        self.assert_dicts_are_equal(
            OP.mock_calls[-2][2]['permissions'],
            sharing)

        # With other args
        tmpFile.seek(0)
        kwargs = dict(
            etag='s0m3E74g',
            content_type=ctype,
            content_disposition=ctype + 'd15p051710n',
            public=True,
            content_encoding='802.11')
        self.client.upload_object(obj, tmpFile, **kwargs)
        for arg, val in kwargs.items():
            self.assertEqual(OP.mock_calls[-2][2][arg], val)

    @patch('%s.put' % pithos_pkg, return_value=FR())
    @patch('%s.set_header' % client_pkg)
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
        self.assertEqual(PC.set_header.mock_calls, exp_shd)
        self.assertEqual(put.mock_calls, exp_put)

    @patch('%s.put' % pithos_pkg, return_value=FR())
    @patch('%s.set_header' % client_pkg)
    def test_create_directory(self, SH, put):
        cont = self.client.container
        exp_shd = [
            call('Content-Type', 'application/directory'),
            call('Content-length', '0')]
        exp_put = [call('/%s/%s/%s' % (user_id, cont, obj), success=201)]
        self.client.create_directory(obj)
        self.assertEqual(PC.set_header.mock_calls, exp_shd)
        self.assertEqual(put.mock_calls, exp_put)

    def test_get_object_info(self):
        FR.headers = object_info
        version = 'v3r510n'
        with patch.object(PC, 'object_head', return_value=FR()) as head:
            r = self.client.get_object_info(obj)
            self.assertEqual(r, object_info)
            r = self.client.get_object_info(obj, version=version)
            self.assertEqual(head.mock_calls, [
                call(obj, version=None),
                call(obj, version=version)])
        with patch.object(
                PC,
                'object_head',
                side_effect=ClientError('Obj not found', 404)):
            self.assertRaises(
                ClientError,
                self.client.get_object_info,
                obj, version=version)

    @patch('%s.get_object_info' % pithos_pkg, return_value=object_info)
    def test_get_object_meta(self, GOI):
        expected = dict()
        for k, v in object_info.items():
            expected[k] = v
        r = self.client.get_object_meta(obj)
        self.assert_dicts_are_equal(r, expected)

    @patch('%s.object_post' % pithos_pkg, return_value=FR())
    def test_del_object_meta(self, post):
        metakey = '50m3m3t4k3y'
        self.client.del_object_meta(obj, metakey)
        expected = call(obj, update=True, metadata={metakey: ''})
        self.assertEqual(post.mock_calls[-1], expected)

    @patch('%s.post' % client_pkg, return_value=FR())
    @patch('%s.set_header' % client_pkg)
    def test_replace_object_meta(self, SH, post):
        metas = dict(k1='new1', k2='new2', k3='new3')
        cont = self.client.container
        self.client.replace_object_meta(metas)
        expected = call('/%s/%s' % (user_id, cont), success=202)
        self.assertEqual(post.mock_calls[-1], expected)
        prfx = 'X-Object-Meta-'
        expected = [call('%s%s' % (prfx, k), v) for k, v in metas.items()]
        self.assertEqual(PC.set_header.mock_calls, expected)

    @patch('%s.object_put' % pithos_pkg, return_value=FR())
    def test_copy_object(self, put):
        src_cont = 'src-c0nt41n3r'
        src_obj = 'src-0bj'
        dst_cont = 'dst-c0nt41n3r'
        dst_obj = 'dst-0bj'
        expected = call(
            src_obj,
            content_length=0,
            source_account=None,
            success=201,
            copy_from='/%s/%s' % (src_cont, src_obj),
            delimiter=None,
            content_type=None,
            source_version=None,
            public=False)
        self.client.copy_object(src_cont, src_obj, dst_cont)
        self.assertEqual(put.mock_calls[-1], expected)
        self.client.copy_object(src_cont, src_obj, dst_cont, dst_obj)
        self.assertEqual(put.mock_calls[-1][1], (dst_obj,))
        kwargs = dict(
            source_version='src-v3r510n',
            source_account='src-4cc0un7',
            public=True,
            content_type='c0n73n7Typ3',
            delimiter='5')
        self.client.copy_object(src_cont, src_obj, dst_cont, **kwargs)
        for k, v in kwargs.items():
            self.assertEqual(v, put.mock_calls[-1][2][k])

    @patch('%s.object_put' % pithos_pkg, return_value=FR())
    def test_move_object(self, put):
        src_cont = 'src-c0nt41n3r'
        src_obj = 'src-0bj'
        dst_cont = 'dst-c0nt41n3r'
        dst_obj = 'dst-0bj'
        expected = call(
            src_obj,
            content_length=0,
            source_account=None,
            success=201,
            move_from='/%s/%s' % (src_cont, src_obj),
            delimiter=None,
            content_type=None,
            source_version=None,
            public=False)
        self.client.move_object(src_cont, src_obj, dst_cont)
        self.assertEqual(put.mock_calls[-1], expected)
        self.client.move_object(src_cont, src_obj, dst_cont, dst_obj)
        self.assertEqual(put.mock_calls[-1][1], (dst_obj,))
        kwargs = dict(
            source_version='src-v3r510n',
            source_account='src-4cc0un7',
            public=True,
            content_type='c0n73n7Typ3',
            delimiter='5')
        self.client.move_object(src_cont, src_obj, dst_cont, **kwargs)
        for k, v in kwargs.items():
            self.assertEqual(v, put.mock_calls[-1][2][k])

    @patch('%s.delete' % client_pkg, return_value=FR())
    def test_delete_object(self, delete):
        cont = self.client.container
        self.client.delete_object(obj)
        self.assertEqual(
            delete.mock_calls[-1],
            call('/%s/%s/%s' % (user_id, cont, obj), success=(204, 404)))
        FR.status_code = 404
        self.assertRaises(ClientError, self.client.delete_object, obj)

    @patch('%s.get' % client_pkg, return_value=FR())
    @patch('%s.set_param' % client_pkg)
    def test_list_objects(self, SP, get):
        FR.json = object_list
        acc = self.client.account
        cont = self.client.container
        SP = PC.set_param
        r = self.client.list_objects()
        for i in range(len(r)):
            self.assert_dicts_are_equal(r[i], object_list[i])
        self.assertEqual(get.mock_calls, [
            call('/%s/%s' % (acc, cont), success=(200, 204, 304, 404))])
        self.assertEqual(SP.mock_calls, [call('format', 'json')])
        FR.status_code = 304
        self.assertEqual(self.client.list_objects(), [])
        FR.status_code = 404
        self.assertRaises(ClientError, self.client.list_objects)

    @patch('%s.get' % client_pkg, return_value=FR())
    @patch('%s.set_param' % client_pkg)
    def test_list_objects_in_path(self, SP, get):
        FR.json = object_list
        path = '/some/awsome/path'
        acc = self.client.account
        cont = self.client.container
        SP = PC.set_param
        self.client.list_objects_in_path(path)
        self.assertEqual(get.mock_calls, [
            call('/%s/%s' % (acc, cont), success=(200, 204, 404))])
        self.assertEqual(SP.mock_calls, [
            call('format', 'json'), call('path', path)])
        FR.status_code = 404
        self.assertRaises(ClientError, self.client.list_objects)
    """

if __name__ == '__main__':
    from sys import argv
    from kamaki.clients.test import runTestCase
    runTestCase(Storage, 'Storage Client', argv[1:])
