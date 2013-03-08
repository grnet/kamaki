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
from mock import patch, call, Mock
from tempfile import NamedTemporaryFile
from os import urandom

from kamaki.clients import ClientError
from kamaki.clients.pithos import PithosClient as PC
from kamaki.clients.astakos import AstakosClient
from kamaki.clients.connection.kamakicon import KamakiHTTPConnection as C

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
    'x-account-policy-versioning': 'auto'}
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


class Pithos(TestCase):

    class FR(object):
        """FR stands for Fake Response"""
        json = dict()
        headers = dict()
        content = json
        status = None
        status_code = 200

        def release(self):
            pass

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
        self.client = PC(self.url, self.token)
        self.client.account = user_id
        self.client.container = 'c0nt@1n3r_i'

    def tearDown(self):
        self.FR.headers = dict()
        self.FR.status_code = 200
        self.FR.json = dict()
        self.FR.content = self.FR.json
        for f in self.files:
            f.close()

    #  Pithos+ methods that extend storage API

    def test_get_account_info(self):
        self.FR.headers = account_info
        self.FR.status_code = 204
        with patch.object(C, 'perform_request', return_value=self.FR()):
            r = self.client.get_account_info()
            self.assertEqual(self.client.http_client.url, self.url)
            self.assertEqual(self.client.http_client.path, '/%s' % user_id)
            self.assert_dicts_are_equal(r, account_info)
            PC.set_param = Mock()
            untils = ['date 1', 'date 2', 'date 3']
            for unt in untils:
                r = self.client.get_account_info(until=unt)
                self.assert_dicts_are_equal(r, account_info)
            for i in range(len(untils)):
                self.assertEqual(
                    PC.set_param.mock_calls[i],
                    call('until', untils[i], iff=untils[i]))
            self.FR.status_code = 401
            self.assertRaises(ClientError, self.client.get_account_info)

    def test_replace_account_meta(self):
        self.FR.status_code = 202
        metas = dict(k1='v1', k2='v2', k3='v3')
        PC.set_header = Mock()
        with patch.object(C, 'perform_request', return_value=self.FR()):
            self.client.replace_account_meta(metas)
            self.assertEqual(self.client.http_client.url, self.url)
            self.assertEqual(self.client.http_client.path, '/%s' % user_id)
            prfx = 'X-Account-Meta-'
            expected = [call('%s%s' % (prfx, k), v) for k, v in metas.items()]
            self.assertEqual(PC.set_header.mock_calls, expected)

    def test_del_account_meta(self):
        keys = ['k1', 'k2', 'k3']
        with patch.object(PC, 'account_post', return_value=self.FR()) as ap:
            expected = []
            for key in keys:
                self.client.del_account_meta(key)
                expected.append(call(update=True, metadata={key: ''}))
            self.assertEqual(ap.mock_calls, expected)

    def test_create_container(self):
        self.FR.status_code = 201
        with patch.object(PC, 'put', return_value=self.FR()) as put:
            cont = 's0m3c0n731n3r'
            self.client.create_container(cont)
            expected = [call('/%s/%s' % (user_id, cont), success=(201, 202))]
            self.assertEqual(put.mock_calls, expected)
            self.FR.status_code = 202
            self.assertRaises(ClientError, self.client.create_container, cont)

    def test_get_container_info(self):
        self.FR.headers = container_info
        with patch.object(PC, 'container_head', return_value=self.FR()) as ch:
            r = self.client.get_container_info()
            self.assert_dicts_are_equal(r, container_info)
            u = 'some date'
            r = self.client.get_container_info(until=u)
            self.assertEqual(ch.mock_calls, [call(until=None), call(until=u)])

    def test_delete_container(self):
        self.FR.status_code = 204
        with patch.object(PC, 'delete', return_value=self.FR()) as delete:
            cont = 's0m3c0n731n3r'
            self.client.delete_container(cont)
            self.FR.status_code = 404
            self.assertRaises(ClientError, self.client.delete_container, cont)
            self.FR.status_code = 409
            self.assertRaises(ClientError, self.client.delete_container, cont)
            acall = call('/%s/%s' % (user_id, cont), success=(204, 404, 409))
            self.assertEqual(delete.mock_calls, [acall] * 3)

    def test_list_containers(self):
        self.FR.json = container_list
        with patch.object(PC, 'account_get', return_value=self.FR()):
            r = self.client.list_containers()
            for i in range(len(r)):
                self.assert_dicts_are_equal(r[i], container_list[i])

    def test_upload_object(self):
        PC.get_container_info = Mock(return_value=container_info)
        PC.container_post = Mock(return_value=self.FR())
        PC.object_put = Mock(return_value=self.FR())
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

    def test_create_object(self):
        PC.set_header = Mock()
        cont = self.client.container
        ctype = 'c0n73n7/typ3'
        exp_shd = [
            call('Content-Type', 'application/octet-stream'),
            call('Content-length', '0'),
            call('Content-Type', ctype), call('Content-length', '42')]
        exp_put = [call('/%s/%s/%s' % (user_id, cont, obj), success=201)] * 2
        with patch.object(PC, 'put', return_value=self.FR()) as put:
            self.client.create_object(obj)
            self.client.create_object(obj,
                content_type=ctype, content_length=42)
            self.assertEqual(PC.set_header.mock_calls, exp_shd)
            self.assertEqual(put.mock_calls, exp_put)

    def test_create_directory(self):
        PC.set_header = Mock()
        cont = self.client.container
        exp_shd = [
            call('Content-Type', 'application/directory'),
            call('Content-length', '0')]
        exp_put = [call('/%s/%s/%s' % (user_id, cont, obj), success=201)]
        with patch.object(PC, 'put', return_value=self.FR()) as put:
            self.client.create_directory(obj)
            self.assertEqual(PC.set_header.mock_calls, exp_shd)
            self.assertEqual(put.mock_calls, exp_put)

    def test_get_object_info(self):
        self.FR.headers = object_info
        version = 'v3r510n'
        with patch.object(PC, 'object_head', return_value=self.FR()) as head:
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

    def test_get_object_meta(self):
        expected = dict()
        for k, v in object_info.items():
            expected[k] = v
        with patch.object(
                PC,
                'get_object_info',
                return_value=object_info):
            r = self.client.get_object_meta(obj)
            self.assert_dicts_are_equal(r, expected)

    def test_del_object_meta(self):
        metakey = '50m3m3t4k3y'
        with patch.object(PC, 'object_post', return_value=self.FR()) as post:
            self.client.del_object_meta(obj, metakey)
            self.assertEqual(
                post.mock_calls,
                [call(obj, update=True, metadata={metakey: ''})])

    def test_replace_object_meta(self):
        PC.set_header = Mock()
        metas = dict(k1='new1', k2='new2', k3='new3')
        cont = self.client.container
        with patch.object(PC, 'post', return_value=self.FR()) as post:
            self.client.replace_object_meta(metas)
            self.assertEqual(post.mock_calls, [
                call('/%s/%s' % (user_id, cont),
                success=202)])
            prfx = 'X-Object-Meta-'
            expected = [call('%s%s' % (prfx, k), v) for k, v in metas.items()]
            self.assertEqual(PC.set_header.mock_calls, expected)

    def test_copy_object(self):
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
        with patch.object(PC, 'object_put', return_value=self.FR()) as put:
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

    def test_move_object(self):
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
        with patch.object(PC, 'object_put', return_value=self.FR()) as put:
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

    def test_delete_object(self):
        cont = self.client.container
        with patch.object(PC, 'delete', return_value=self.FR()) as delete:
            self.client.delete_object(obj)
            self.assertEqual(delete.mock_calls, [
                call('/%s/%s/%s' % (user_id, cont, obj), success=(204, 404))])
            self.FR.status_code = 404
            self.assertRaises(ClientError, self.client.delete_object, obj)

    def test_list_objects(self):
        self.FR.json = object_list
        acc = self.client.account
        cont = self.client.container
        PC.set_param = Mock()
        SP = PC.set_param
        with patch.object(PC, 'get', return_value=self.FR()) as get:
            r = self.client.list_objects()
            for i in range(len(r)):
                self.assert_dicts_are_equal(r[i], object_list[i])
            self.assertEqual(get.mock_calls, [
                call('/%s/%s' % (acc, cont), success=(200, 204, 304, 404))])
            self.assertEqual(SP.mock_calls, [call('format', 'json')])
            self.FR.status_code = 304
            self.assertEqual(self.client.list_objects(), [])
            self.FR.status_code = 404
            self.assertRaises(ClientError, self.client.list_objects)

    def test_list_objects_in_path(self):
        self.FR.json = object_list
        path = '/some/awsome/path'
        acc = self.client.account
        cont = self.client.container
        PC.set_param = Mock()
        SP = PC.set_param
        with patch.object(PC, 'get', return_value=self.FR()) as get:
            self.client.list_objects_in_path(path)
            self.assertEqual(get.mock_calls, [
                call('/%s/%s' % (acc, cont), success=(200, 204, 404))])
            self.assertEqual(SP.mock_calls, [
                call('format', 'json'), call('path', path)])
            self.FR.status_code = 404
            self.assertRaises(ClientError, self.client.list_objects)

    #  Pithos+ only methods

    def test_purge_container(self):
        with patch.object(
                PC,
                'container_delete',
                return_value=self.FR()) as cd:
            self.client.purge_container()
            self.assertTrue('until' in cd.mock_calls[-1][2])
            cont = self.client.container
            self.client.purge_container('another-container')
            self.assertEqual(self.client.container, cont)

    def test_upload_object_unchunked(self):
        num_of_blocks = 8
        tmpFile = self._create_temp_file(num_of_blocks)
        expected = dict(
                success=201,
                data=num_of_blocks * 4 * 1024 * 1024,
                etag='some-etag',
                content_encoding='some content_encoding',
                content_type='some content-type',
                content_disposition='some content_disposition',
                public=True,
                permissions=dict(read=['u1', 'g1', 'u2'], write=['u1']))
        with patch.object(PC, 'object_put', return_value=self.FR()) as put:
            self.client.upload_object_unchunked(obj, tmpFile)
            self.assertEqual(put.mock_calls[-1][1], (obj,))
            self.assertEqual(
                sorted(put.mock_calls[-1][2].keys()),
                sorted(expected.keys()))
            kwargs = dict(expected)
            kwargs.pop('success')
            kwargs['size'] = kwargs.pop('data')
            kwargs['sharing'] = kwargs.pop('permissions')
            tmpFile.seek(0)
            self.client.upload_object_unchunked(obj, tmpFile, **kwargs)
            pmc = put.mock_calls[-1][2]
            for k, v in expected.items():
                if k == 'data':
                    self.assertEqual(len(pmc[k]), v)
                else:
                    self.assertEqual(pmc[k], v)
            self.assertRaises(
                ClientError,
                self.client.upload_object_unchunked,
                obj, tmpFile, withHashFile=True)

    def test_create_object_by_manifestation(self):
        manifest = '%s/%s' % (self.client.container, obj)
        kwargs = dict(
                etag='some-etag',
                content_encoding='some content_encoding',
                content_type='some content-type',
                content_disposition='some content_disposition',
                public=True,
                sharing=dict(read=['u1', 'g1', 'u2'], write=['u1']))
        with patch.object(PC, 'object_put', return_value=self.FR()) as put:
            self.client.create_object_by_manifestation(obj)
            expected = dict(content_length=0, manifest=manifest)
            for k in kwargs:
                expected['permissions' if k == 'sharing' else k] = None
            self.assertEqual(put.mock_calls[-1], call(obj, **expected))
            self.client.create_object_by_manifestation(obj, **kwargs)
            expected.update(kwargs)
            expected['permissions'] = expected.pop('sharing')
            self.assertEqual(put.mock_calls[-1], call(obj, **expected))

    def test_download_object(self):
        PC.get_object_hashmap = Mock(return_value=object_hashmap)
        num_of_blocks = 8
        tmpFile = self._create_temp_file(num_of_blocks)
        self.FR.content = tmpFile.read(4 * 1024 * 1024)
        tmpFile = self._create_temp_file(num_of_blocks)
        PC.object_get = Mock(return_value=self.FR())
        GET = PC.object_get
        num_of_blocks = len(object_hashmap['hashes'])

        kwargs = dict(
            resume=True,
            version='version',
            range_str='10-20',
            if_match='if and only if',
            if_none_match='if and only not',
            if_modified_since='what if not?',
            if_unmodified_since='this happens if not!',
            async_headers=dict(Range='bytes=0-88888888'))

        self.client.download_object(obj, tmpFile)
        self.assertEqual(len(GET.mock_calls), num_of_blocks)
        self.assertEqual(GET.mock_calls[-1][1], (obj,))
        for k, v in kwargs.items():
            if k == 'async_headers':
                self.assertTrue('Range' in GET.mock_calls[-1][2][k])
            elif k in ('resume', 'range_str'):
                continue
            else:
                self.assertEqual(GET.mock_calls[-1][2][k], None)

        #  Check ranges are consecutive
        starts = []
        ends = []
        for c in GET.mock_calls:
            rng_str = c[2]['async_headers']['Range']
            (start, rng_str) = rng_str.split('=')
            (start, end) = rng_str.split('-')
            starts.append(start)
            ends.append(end)
        ends = sorted(ends)
        for i, start in enumerate(sorted(starts)):
            if i:
                int(ends[i - 1]) == int(start) - 1

        #  With progress bars
        try:
            from progress.bar import ShadyBar
            dl_bar = ShadyBar('Mock dl')
        except ImportError:
            dl_bar = None

        if dl_bar:

            def blck_gen(n):
                for i in dl_bar.iter(range(n)):
                    yield
                yield

            tmpFile.seek(0)
            self.client.download_object(obj, tmpFile, download_cb=blck_gen)
            self.assertEqual(len(GET.mock_calls), 2 * num_of_blocks)

        tmpFile.seek(0)
        kwargs.pop('async_headers')
        kwargs.pop('resume')
        self.client.download_object(obj, tmpFile, **kwargs)
        for k, v in kwargs.items():
            if k == 'range_str':
                self.assertEqual(
                    GET.mock_calls[-1][2]['data_range'],
                    'bytes=%s' % v)
            else:
                self.assertEqual(GET.mock_calls[-1][2][k], v)

        #  ALl options on no tty

        def foo():
            return True

        tmpFile.seek(0)
        tmpFile.isatty = foo
        self.client.download_object(obj, tmpFile, **kwargs)
        for k, v in kwargs.items():
            if k == 'range_str':
                self.assertTrue('data_range' in GET.mock_calls[-1][2])
            else:
                self.assertEqual(GET.mock_calls[-1][2][k], v)

    def test_get_object_hashmap(self):
        self.FR.json = object_hashmap
        for empty in (304, 412):
            with patch.object(
                    PC, 'object_get',
                    side_effect=ClientError('Empty', status=empty)):
                r = self.client.get_object_hashmap(obj)
                self.assertEqual(r, {})
        exp_args = dict(
            hashmap=True,
            data_range=None,
            version=None,
            if_etag_match=None,
            if_etag_not_match=None,
            if_modified_since=None,
            if_unmodified_since=None)
        kwargs = dict(
            version='s0m3v3r51on',
            if_match='if match',
            if_none_match='if non match',
            if_modified_since='some date here',
            if_unmodified_since='some date here',
            data_range='10-20')
        with patch.object(PC, 'object_get', return_value=self.FR()) as get:
            r = self.client.get_object_hashmap(obj)
            self.assertEqual(r, object_hashmap)
            self.assertEqual(get.mock_calls[-1], call(obj, **exp_args))
            r = self.client.get_object_hashmap(obj, **kwargs)
            exp_args['if_etag_match'] = kwargs.pop('if_match')
            exp_args['if_etag_not_match'] = kwargs.pop('if_none_match')
            exp_args.update(kwargs)
            self.assertEqual(get.mock_calls[-1], call(obj, **exp_args))

    def test_set_account_group(self):
        group = 'aU53rGr0up'
        usernames = ['u1', 'u2', 'u3']
        with patch.object(PC, 'account_post', return_value=self.FR()) as post:
            self.client.set_account_group(group, usernames)
            self.assertEqual(
                post.mock_calls[-1],
                call(update=True, groups={group: usernames}))

    def test_del_account_group(self):
        group = 'aU53rGr0up'
        with patch.object(PC, 'account_post', return_value=self.FR()) as post:
            self.client.del_account_group(group)
            self.assertEqual(
                post.mock_calls[-1],
                call(update=True, groups={group: []}))

    def test_get_account_quota(self):
        key = 'x-account-policy-quota'
        with patch.object(PC, 'get_account_info', return_value=account_info):
            r = self.client.get_account_quota()
            self.assertEqual(r[key], account_info[key])

    def test_get_account_versioning(self):
        key = 'x-account-policy-versioning'
        with patch.object(PC, 'get_account_info', return_value=account_info):
            r = self.client.get_account_versioning()
            self.assertEqual(r[key], account_info[key])

    def test_get_account_meta(self):
        key = 'x-account-meta-'
        with patch.object(PC, 'get_account_info', return_value=account_info):
            r = self.client.get_account_meta()
            keys = [k for k in r if k.startswith(key)]
            self.assertFalse(keys)
        acc_info = dict(account_info)
        acc_info['%sk1' % key] = 'v1'
        acc_info['%sk2' % key] = 'v2'
        acc_info['%sk3' % key] = 'v3'
        with patch.object(PC, 'get_account_info', return_value=acc_info):
            r = self.client.get_account_meta()
            for k in [k for k in acc_info if k.startswith(key)]:
                self.assertEqual(r[k], acc_info[k])

    def test_get_account_group(self):
        key = 'x-account-group-'
        with patch.object(PC, 'get_account_info', return_value=account_info):
            r = self.client.get_account_group()
            keys = [k for k in r if k.startswith(key)]
            self.assertFalse(keys)
        acc_info = dict(account_info)
        acc_info['%sk1' % key] = 'g1'
        acc_info['%sk2' % key] = 'g2'
        acc_info['%sk3' % key] = 'g3'
        with patch.object(PC, 'get_account_info', return_value=acc_info):
            r = self.client.get_account_group()
            for k in [k for k in acc_info if k.startswith(key)]:
                self.assertEqual(r[k], acc_info[k])

    def test_set_account_meta(self):
        metas = dict(k1='v1', k2='v2', k3='v3')
        with patch.object(PC, 'account_post', return_value=self.FR()) as post:
            self.client.set_account_meta(metas)
            self.assertEqual(
                post.mock_calls[-1],
                call(update=True, metadata=metas))

    def test_set_account_quota(self):
        qu = 1024
        with patch.object(PC, 'account_post', return_value=self.FR()) as post:
            self.client.set_account_quota(qu)
            self.assertEqual(post.mock_calls[-1], call(update=True, quota=qu))

    def test_set_account_versioning(self):
        vrs = 'n3wV3r51on1ngTyp3'
        with patch.object(PC, 'account_post', return_value=self.FR()) as post:
            self.client.set_account_versioning(vrs)
            self.assertEqual(
                post.mock_calls[-1],
                call(update=True, versioning=vrs))

    def test_del_container(self):
        kwarg_list = [
            dict(delimiter=None, until=None),
            dict(delimiter='X', until='50m3d473')]
        with patch.object(
                PC,
                'container_delete',
                return_value=self.FR()) as delete:
            for kwarg in kwarg_list:
                self.client.del_container(**kwarg)
                expected = dict(kwarg)
                expected['success'] = (204, 404, 409)
                self.assertEqual(delete.mock_calls[-1], call(**expected))
            for status_code in (404, 409):
                self.FR.status_code = status_code
                self.assertRaises(ClientError, self.client.del_container)
