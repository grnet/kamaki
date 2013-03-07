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

from kamaki.clients import ClientError
from kamaki.clients.pithos import PithosClient as PC
from kamaki.clients.astakos import AstakosClient
from kamaki.clients.connection.kamakicon import KamakiHTTPConnection as C

user_id = 'ac0un7-1d-5tr1ng'

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
        for f in self.files:
            f.close()

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
        from tempfile import NamedTemporaryFile
        from os import urandom
        self.files.append(NamedTemporaryFile())
        tmpFile = self.files[-1]
        num_of_blocks = 8
        file_size = num_of_blocks * 4 * 1024 * 1024
        print('\n\tCreate tmp file')
        tmpFile.write(urandom(file_size))
        tmpFile.flush()
        tmpFile.seek(0)
        print('\t\tDone')
        obj = 'objectName'

        # No special args
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
                bytes=file_size),
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
                bytes=file_size),
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
        obj = 'r4nd0m0bj3c7'
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
        obj = 'r4nd0m0bj3c7'
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
        obj = 'r4nd0m0bj3c7'
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
        obj = 'r4nd0m0bj3c7'
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
        obj = 'r4nd0m0bj3c7'
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
