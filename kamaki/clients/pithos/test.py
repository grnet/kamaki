# Copyright 2013-2014 GRNET S.A. All rights reserved.
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
from itertools import product
from random import randint

from kamaki.clients import pithos, ClientError


rest_pkg = 'kamaki.clients.pithos.rest_api.PithosRestClient'
pithos_pkg = 'kamaki.clients.pithos.PithosClient'

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
    dict(
        hash="",
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
    dict(
        hash="",
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


class PithosRestClient(TestCase):

    def setUp(self):
        self.url = 'https://www.example.com/pithos'
        self.token = 'p17h0570k3n'
        self.client = pithos.PithosRestClient(self.url, self.token)
        self.client.account = user_id
        self.client.container = 'c0nt@1n3r_i'

    def tearDown(self):
        FR.headers = dict()
        FR.json = dict()
        FR.content = FR.json

    @patch('%s.set_param' % rest_pkg)
    @patch('%s.set_header' % rest_pkg)
    @patch('%s.head' % rest_pkg, return_value=FR())
    def test_account_head(self, head, SH, SP):
        for params in product(
                (None, '50m3-d473'),
                (None, '50m3-07h3r-d473'),
                (None, 'y37-4n7h3r-d473'),
                ((), ('someval',), ('v1', 'v2',)),
                (dict(), dict(success=200), dict(k='v', v='k'))):
            args, kwargs = params[-2], params[-1]
            params = params[:-2]
            self.client.account_head(*(params + args), **kwargs)
            unt = params[0]
            self.assertEqual(SP.mock_calls[-1], call('until', unt, iff=unt))
            IMS, IUS = params[1], params[2]
            self.assertEqual(SH.mock_calls[-2:], [
                call('If-Modified-Since', IMS),
                call('If-Unmodified-Since', IUS)])
            self.assertEqual(head.mock_calls[-1], call(
                '/%s' % self.client.account,
                *args,
                success=kwargs.pop('success', 204),
                **kwargs))

    @patch('%s.set_param' % rest_pkg)
    @patch('%s.set_header' % rest_pkg)
    @patch('%s.get' % rest_pkg, return_value=FR())
    def test_account_get(self, get, SH, SP):
        keys = ('limit', 'marker', 'format', 'shared', 'public', 'until')
        for params in product(
                (None, 42),
                (None, 'X'),
                ('json', 'xml'),
                (False, True),
                (False, True),
                (None, '50m3-d473'),
                (None, '50m3-07h3r-d473'),
                (None, 'y37-4n7h3r-d473'),
                ((), ('someval',), ('v1', 'v2',)),
                (dict(), dict(success=200), dict(k='v', v='k'))):
            args, kwargs = params[-2], params[-1]
            params = params[:-2]
            self.client.account_get(*(params + args), **kwargs)
            self.assertEqual(SP.mock_calls[-6:], [
                call(keys[i], iff=X) if (i in (3, 4)) else call(
                    keys[i], X, iff=X) for i, X in enumerate(params[:6])])
            IMS, IUS = params[6], params[7]
            self.assertEqual(SH.mock_calls[-2:], [
                call('If-Modified-Since', IMS),
                call('If-Unmodified-Since', IUS)])
            self.assertEqual(get.mock_calls[-1], call(
                '/%s' % self.client.account,
                *args,
                success=kwargs.pop('success', (200, 204)),
                **kwargs))

    @patch('%s.set_param' % rest_pkg)
    @patch('%s.set_header' % rest_pkg)
    @patch('%s.post' % rest_pkg, return_value=FR())
    def test_account_post(self, post, SH, SP):
        for pm in product(
                (True, False),
                ({}, dict(g=['u1', 'u2']), dict(g1=[], g2=['u1', 'u2'])),
                (None, dict(k1='v1', k2='v2', k3='v2'), dict(k='v')),
                (None, 42),
                (None, 'v3r510n1ng'),
                ((), ('someval',), ('v1', 'v2',)),
                (dict(), dict(success=200), dict(k='v', v='k'))):
            args, kwargs = pm[-2:]
            pm = pm[:-2]
            self.client.account_post(*(pm + args), **kwargs)
            upd = pm[0]
            self.assertEqual(SP.mock_calls[-1], call('update', '', iff=upd))
            expected = []
            if pm[1]:
                expected += [call(
                    'X-Account-Group-%s' % k, v) for k, v in pm[1].items()]
            if pm[2]:
                expected = [call(
                    'X-Account-Meta-%s' % k, v) for k, v in pm[2].items()]
            expected = [
                call('X-Account-Policy-Quota', pm[3]),
                call('X-Account-Policy-Versioning', pm[4])]
            self.assertEqual(SH.mock_calls[- len(expected):], expected)
            self.assertEqual(post.mock_calls[-1], call(
                '/%s' % self.client.account,
                *args,
                success=kwargs.pop('success', 202),
                **kwargs))

    @patch('%s.set_param' % rest_pkg)
    @patch('%s.set_header' % rest_pkg)
    @patch('%s.head' % rest_pkg, return_value=FR())
    def test_container_head(self, head, SH, SP):
        for pm in product(
                (None, '4-d473'),
                (None, '47h3r-d473'),
                (None, 'y37-4n47h3r'),
                ((), ('someval',)),
                (dict(), dict(success=200), dict(k='v', v='k'))):
            args, kwargs = pm[-2:]
            pm = pm[:-2]
            self.client.container_head(*(pm + args), **kwargs)
            unt, ims, ius = pm[0:3]
            self.assertEqual(SP.mock_calls[-1], call('until', unt, iff=unt))
            self.assertEqual(SH.mock_calls[-2:], [
                call('If-Modified-Since', ims),
                call('If-Unmodified-Since', ius)])
            self.assertEqual(head.mock_calls[-1], call(
                '/%s/%s' % (self.client.account, self.client.container),
                *args,
                success=kwargs.pop('success', 204),
                **kwargs))

    @patch('%s.set_param' % rest_pkg)
    @patch('%s.set_header' % rest_pkg)
    @patch('%s.get' % rest_pkg, return_value=FR())
    def test_container_get(self, get, SH, SP):
        for pm in product(
                (None, 42),
                (None, 'X'),
                (None, 'some/prefix'),
                (None, 'delimiter'),
                (None, '/some/path'),
                ('json', 'some-format'),
                ([], ['k1', 'k2', 'k3']),
                (False, True),
                (False, True),
                (None, 'unt1l-d473'),
                (None, 'y37-4n47h3r'),
                (None, '4n47h3r-d473'),
                ((), ('someval',)),
                (dict(), dict(success=400), dict(k='v', v='k'))):
            args, kwargs = pm[-2:]
            pm = pm[:-2]
            self.client.container_get(*(pm + args), **kwargs)
            lmt, mrk, prfx, dlm, path, frmt, meta, shr, pbl, unt = pm[:-2]
            exp = [call('limit', lmt, iff=lmt), call('marker', mrk, iff=mrk)]
            exp += [call('path', path)] if path else [
                call('prefix', prfx, iff=prfx),
                call('delimiter', dlm, iff=dlm)]
            exp += [
                call('format', frmt, iff=frmt),
                call('shared', iff=shr),
                call('public', iff=pbl)]
            if meta:
                exp += [call('meta', ','.join(meta))]
            exp += [call('until', unt, iff=unt)]
            self.assertEqual(SP.mock_calls[- len(exp):], exp)
            ims, ius = pm[-2:]
            self.assertEqual(SH.mock_calls[-2:], [
                call('If-Modified-Since', ims),
                call('If-Unmodified-Since', ius)])
            self.assertEqual(get.mock_calls[-1], call(
                '/%s/%s' % (self.client.account, self.client.container),
                *args,
                success=kwargs.pop('success', 200),
                **kwargs))

    @patch('%s.set_header' % rest_pkg)
    @patch('%s.put' % rest_pkg, return_value=FR())
    def test_container_put(self, put, SH):
        for pm in product(
                (None, 42),
                (None, 'v3r51on1ng'),
                (None, 'project id'),
                (None, dict(k1='v2'), dict(k2='v2', k3='v3')),
                ((), ('someval',)),
                (dict(), dict(success=400), dict(k='v', v='k'))):
            args, kwargs = pm[-2:]
            pm = pm[:-2]
            self.client.container_put(*(pm + args), **kwargs)
            quota, versioning, project_id = pm[-4:-1]
            metas = pm[-1] or dict()
            exp = [
                call('X-Container-Policy-Quota', quota),
                call('X-Container-Policy-Versioning', versioning)] + (
                    [call('X-Container-Policy-Project', project_id)] if (
                        project_id is not None) else []) + [
                call('X-Container-Meta-%s' % k, v) for k, v in metas.items()]
            self.assertEqual(SH.mock_calls[- len(exp):], exp)
            self.assertEqual(put.mock_calls[-1], call(
                '/%s/%s' % (self.client.account, self.client.container),
                *args,
                success=kwargs.pop('success', (201, 202)),
                **kwargs))

    @patch('%s.set_param' % rest_pkg)
    @patch('%s.set_header' % rest_pkg)
    @patch('%s.post' % rest_pkg, return_value=FR())
    def test_container_post(self, post, SH, SP):
        for pm in product(
                (True, False),
                ('json', 'some-format'),
                (None, 'quota'),
                (None, 'v3r51on1ng'),
                (None, 'project id'),
                (dict(), dict(k1='v2'), dict(k2='v2', k3='v3')),
                (None, 'content-type'),
                (None, 42),
                (None, 'transfer-encoding'),
                ((), ('someval',)),
                (dict(), dict(success=400), dict(k='v', v='k'))):
            args, kwargs = pm[-2:]
            pm = pm[:-2]
            self.client.container_post(*(pm + args), **kwargs)
            upd, frmt = pm[:2]
            self.assertEqual(SP.mock_calls[-2:], [
                call('update', '', iff=upd),
                call('format', frmt, iff=frmt)])
            qta, vrs, project_id, metas, ctype, clen, trenc = pm[2:]
            prfx = 'X-Container-Meta-'
            exp = [
                call('X-Container-Policy-Quota', qta),
                call('X-Container-Policy-Versioning', vrs)] + ([
                    call('X-Container-Policy-Project', project_id)] if (
                        project_id is not None) else []) + [
                call('%s%s' % (prfx, k), v) for k, v in metas.items()] + [
                call('Content-Type', ctype),
                call('Content-Length', clen),
                call('Transfer-Encoding', trenc)]
            self.assertEqual(SH.mock_calls[- len(exp):], exp)
            ims, ius = pm[-2:]
            self.assertEqual(post.mock_calls[-1], call(
                '/%s/%s' % (self.client.account, self.client.container),
                *args,
                success=kwargs.pop('success', 202),
                **kwargs))

    @patch('%s.set_param' % rest_pkg)
    @patch('%s.delete' % rest_pkg, return_value=FR())
    def test_container_delete(self, delete, SP):
        for pm in product(
                (None, 'd473'),
                (None, 'd3l1m'),
                ((), ('someval',)),
                (dict(), dict(success=400), dict(k='v', v='k'))):
            args, kwargs = pm[-2:]
            pm = pm[:-2]
            self.client.container_delete(*(pm + args), **kwargs)
            unt, dlm = pm[-2:]
            self.assertEqual(SP.mock_calls[-2:], [
                call('until', unt, iff=unt),
                call('delimiter', dlm, iff=dlm)])
            self.assertEqual(delete.mock_calls[-1], call(
                '/%s/%s' % (self.client.account, self.client.container),
                *args,
                success=kwargs.pop('success', 204),
                **kwargs))

    @patch('%s.set_param' % rest_pkg)
    @patch('%s.set_header' % rest_pkg)
    @patch('%s.head' % rest_pkg, return_value=FR())
    def test_object_head(self, head, SH, SP):
        for pm in product(
                (None, 'v3r510n'),
                (None, '1f-374g'),
                (None, '1f-n0-74g'),
                (None, '1f-m0d-51nc3'),
                (None, '1f-unm0d-51nc3'),
                ((), ('someval',)),
                (dict(), dict(success=400), dict(k='v', v='k'))):
            args, kwargs = pm[-2:]
            pm = pm[:-2]
            self.client.object_head(obj, *(pm + args), **kwargs)
            vrs, etag, netag, ims, ius = pm[:5]
            self.assertEqual(
                SP.mock_calls[-1],
                call('version', vrs, iff=vrs))
            self.assertEqual(SH.mock_calls[-4:], [
                call('If-Match', etag),
                call('If-None-Match', netag),
                call('If-Modified-Since', ims),
                call('If-Unmodified-Since', ius)])
            acc, cont = self.client.account, self.client.container
            self.assertEqual(head.mock_calls[-1], call(
                '/%s/%s/%s' % (acc, cont, obj),
                *args,
                success=kwargs.pop('success', 200),
                **kwargs))

    @patch('%s.set_param' % rest_pkg)
    @patch('%s.set_header' % rest_pkg)
    @patch('%s.get' % rest_pkg, return_value=FR())
    def test_object_get(self, get, SH, SP):
        for pm in product(
                ('json', 'f0rm47'),
                (False, True),
                (None, 'v3r510n'),
                (None, 'range=74-63'),
                (False, True),
                (None, '3746'),
                (None, 'non-3746'),
                (None, '1f-m0d'),
                (None, '1f-unm0d'),
                ((), ('someval',)),
                (dict(), dict(success=400), dict(k='v', v='k'))):
            args, kwargs = pm[-2:]
            pm = pm[:-2]
            self.client.object_get(obj, *(pm + args), **kwargs)
            format, hashmap, version = pm[:3]
            self.assertEqual(SP.mock_calls[-3:], [
                call('format', format, iff=format),
                call('hashmap', hashmap, iff=hashmap),
                call('version', version, iff=version)])
            rng, ifrng, im, inm, ims, ius = pm[-6:]
            self.assertEqual(SH.mock_calls[-6:], [
                call('Range', rng),
                call('If-Range', '', ifrng and rng),
                call('If-Match', im),
                call('If-None-Match', inm),
                call('If-Modified-Since', ims),
                call('If-Unmodified-Since', ius)])
            acc, cont = self.client.account, self.client.container
            self.assertEqual(get.mock_calls[-1], call(
                '/%s/%s/%s' % (acc, cont, obj),
                *args,
                success=kwargs.pop('success', 200),
                **kwargs))

    @patch('%s.set_param' % rest_pkg)
    @patch('%s.set_header' % rest_pkg)
    @patch('%s.put' % rest_pkg, return_value=FR())
    def test_object_put(self, put, SH, SP):
        for pm in product(
                ('json', 'f0rm47'),
                (False, True),
                (None, 'delim',),
                (dict(), dict(read=['u1', 'g2'], write=['u1'])),
                (False, True),
                (dict(), dict(k2='v2', k3='v3')),
                ((), ('someval',)),
                (dict(), dict(success=400), dict(k='v', v='k'))):
            args, kwargs = pm[-2:]
            pm = pm[:-2]
            terms = [None] * 13
            for i in range(len(terms)):
                if randint(0, 2):
                    terms[i] = 'val_%s' % randint(13, 1024)
            self.client.object_put(
                obj,
                *(pm[:3] + tuple(terms) + pm[3:] + args),
                **kwargs)
            format, hashmap, delimiter = pm[:3]
            self.assertEqual(SP.mock_calls[-3:], [
                call('format', format, iff=format),
                call('hashmap', hashmap, iff=hashmap),
                call('delimiter', delimiter, iff=delimiter)])
            (
                im, inm, etag, clen, ctype, trenc,
                cp, mv, srcacc, srcvrs, conenc, condis, mnf) = terms
            perms, public, metas = pm[3:]
            exp = [
                call('If-Match', im),
                call('If-None-Match', inm),
                call('ETag', etag),
                call('Content-Length', clen),
                call('Content-Type', ctype),
                call('Transfer-Encoding', trenc),
                call('X-Copy-From', cp),
                call('X-Move-From', mv),
                call('X-Source-Account', srcacc),
                call('X-Source-Version', srcvrs),
                call('Content-Encoding', conenc),
                call('Content-Disposition', condis),
                call('X-Object-Manifest', mnf)]
            if perms:
                perm_str = ''
                for ptype, pval in perms.items():
                    if pval:
                        perm_str += ';' if perm_str else ''
                        perm_str += '%s=%s' % (ptype, ','.join(pval))
                exp += [call('X-Object-Sharing', perm_str)]
            exp += [call('X-Object-Public', public, public is not None)]
            for k, v in metas.items():
                exp += [call('X-Object-Meta-%s' % k, v)]
            self.assertEqual(SH.mock_calls[- len(exp):], exp)
            acc, cont = self.client.account, self.client.container
            self.assertEqual(put.mock_calls[-1], call(
                '/%s/%s/%s' % (acc, cont, obj),
                *args,
                success=kwargs.pop('success', 201),
                **kwargs))

    @patch('%s.set_param' % rest_pkg)
    @patch('%s.set_header' % rest_pkg)
    @patch('%s.copy' % rest_pkg, return_value=FR())
    def test_object_copy(self, copy, SH, SP):
        dest = 'dest1n4710n'
        for pm in product(
                ('json', 'f0rm47'),
                (False, True),
                (None, 'ifmatch'),
                (None, 'ifnonematch'),
                (None, 'destinationaccount'),
                (None, 'content-type'),
                (None, 'content-encoding'),
                (None, 'content-disp'),
                (None, 'source-version'),
                (dict(), dict(read=['u1', 'g2'], write=['u1'])),
                (False, True),
                (dict(), dict(k2='v2', k3='v3')),
                ((), ('someval',)),
                (dict(), dict(success=400), dict(k='v', v='k'))):
            args, kwargs = pm[-2:]
            pm = pm[:-2]
            self.client.object_copy(obj, dest, *(pm + args), **kwargs)
            format, ict = pm[:2]
            self.assertEqual(SP.mock_calls[-2:], [
                call('format', format, iff=format),
                call('ignore_content_type', iff=ict)])
            im, inm, da, ct, ce, cd, sv, perms, public, metas = pm[2:]
            exp = [
                call('If-Match', im),
                call('If-None-Match', inm),
                call('Destination', dest),
                call('Destination-Account', da),
                call('Content-Type', ct),
                call('Content-Encoding', ce),
                call('Content-Disposition', cd),
                call('X-Source-Version', sv)]
            if perms:
                perm_str = ''
                for ptype, pval in perms.items():
                    if pval:
                        perm_str += ';' if perm_str else ''
                        perm_str += '%s=%s' % (ptype, ','.join(pval))
                exp += [call('X-Object-Sharing', perm_str)]
            exp += [call('X-Object-Public', public, public is not None)]
            for k, v in metas.items():
                exp += [call('X-Object-Meta-%s' % k, v)]
            self.assertEqual(SH.mock_calls[- len(exp):], exp)
            acc, cont = self.client.account, self.client.container
            self.assertEqual(copy.mock_calls[-1], call(
                '/%s/%s/%s' % (acc, cont, obj),
                *args,
                success=kwargs.pop('success', 201),
                **kwargs))

    @patch('%s.set_param' % rest_pkg)
    @patch('%s.set_header' % rest_pkg)
    @patch('%s.move' % rest_pkg, return_value=FR())
    def test_object_move(self, move, SH, SP):
        for pm in product(
                ('json', 'f0rm47'),
                (False, True),
                (None, 'ifmatch'),
                (None, 'ifnonematch'),
                (None, 'destination'),
                (None, 'destinationaccount'),
                (None, 'content-type'),
                (None, 'content-encoding'),
                (None, 'content-disp'),
                (dict(), dict(read=['u1', 'g2'], write=['u1'])),
                (False, True),
                (dict(), dict(k2='v2', k3='v3')),
                ((), ('someval',)),
                (dict(), dict(success=400), dict(k='v', v='k'))):
            args, kwargs = pm[-2:]
            pm = pm[:-2]
            self.client.object_move(obj, *(pm + args), **kwargs)
            format, ict = pm[:2]
            self.assertEqual(SP.mock_calls[-2:], [
                call('format', format, iff=format),
                call('ignore_content_type', iff=ict)])
            im, inm, d, da, ct, ce, cd, perms, public, metas = pm[2:]
            exp = [
                call('If-Match', im),
                call('If-None-Match', inm),
                call('Destination', d),
                call('Destination-Account', da),
                call('Content-Type', ct),
                call('Content-Encoding', ce),
                call('Content-Disposition', cd)]
            if perms:
                perm_str = ''
                for ptype, pval in perms.items():
                    if pval:
                        perm_str += ';' if perm_str else ''
                        perm_str += '%s=%s' % (ptype, ','.join(pval))
                exp += [call('X-Object-Sharing', perm_str, iff=perms)]
            else:
                exp += [call('X-Object-Sharing', '', iff={})]
            exp += [call('X-Object-Public', public, public is not None)]
            for k, v in metas.items():
                exp += [call('X-Object-Meta-%s' % k, v)]
            self.assertEqual(SH.mock_calls[- len(exp):], exp)
            acc, cont = self.client.account, self.client.container
            self.assertEqual(move.mock_calls[-1], call(
                '/%s/%s/%s' % (acc, cont, obj),
                *args,
                success=kwargs.pop('success', 201),
                **kwargs))

    @patch('%s.set_param' % rest_pkg)
    @patch('%s.set_header' % rest_pkg)
    @patch('%s.post' % rest_pkg, return_value=FR())
    def test_object_post(self, post, SH, SP):
        for pm in product(
                ('json', 'f0rm47'),
                (False, True),
                (dict(), dict(read=['u1', 'g2'], write=['u1'])),
                (False, True),
                (dict(), dict(k2='v2', k3='v3')),
                ((), ('someval',)),
                (dict(), dict(success=400), dict(k='v', v='k'))):
            args, kwargs = pm[-2:]
            pm = pm[:-2]
            terms = [None] * 13
            for i in range(len(terms)):
                if randint(0, 2):
                    terms[i] = 'val_%s' % randint(13, 1024)
            self.client.object_post(
                obj,
                *(pm[:2] + tuple(terms) + pm[2:] + args),
                **kwargs)
            format, update = pm[:2]
            self.assertEqual(SP.mock_calls[-2:], [
                call('format', format, iff=format),
                call('update', '', iff=update)])
            (
                im, inm, clen, ctype, crng, trenc, cenc,
                condis, srcobj, srcacc, srcvrs, obytes, mnfs) = terms
            exp = [
                call('If-Match', im),
                call('If-None-Match', inm),
                call('Content-Length', clen, iff=not trenc),
                call('Content-Type', ctype),
                call('Content-Range', crng),
                call('Transfer-Encoding', trenc),
                call('Content-Encoding', cenc),
                call('Content-Disposition', condis),
                call('X-Source-Object', srcobj),
                call('X-Source-Account', srcacc),
                call('X-Source-Version', srcvrs),
                call('X-Object-Bytes', obytes),
                call('X-Object-Manifest', mnfs)]
            perms, public, metas = pm[2:]
            if perms:
                perm_str = ''
                for ptype, pval in perms.items():
                    if pval:
                        perm_str += ';' if perm_str else ''
                        perm_str += '%s=%s' % (ptype, ','.join(pval))
                exp += [call('X-Object-Sharing', perm_str, iff=perms)]
            else:
                exp += [call('X-Object-Sharing', '', iff={})]
            exp += [call('X-Object-Public', public, public is not None)]
            for k, v in metas.items():
                exp += [call('X-Object-Meta-%s' % k, v)]
            self.assertEqual(SH.mock_calls[- len(exp):], exp)
            acc, cont = self.client.account, self.client.container
            self.assertEqual(post.mock_calls[-1], call(
                '/%s/%s/%s' % (acc, cont, obj),
                *args,
                success=kwargs.pop('success', (202, 204)),
                **kwargs))

    @patch('%s.set_param' % rest_pkg)
    @patch('%s.delete' % rest_pkg, return_value=FR())
    def test_object_delete(self, delete, SP):
        for pm in product(
                (None, 'until'),
                (None, 'delim'),
                ((), ('someval',)),
                (dict(), dict(success=400), dict(k='v', v='k'))):
            args, kwargs = pm[-2:]
            pm = pm[:-2]
            self.client.object_delete(
                obj,
                *(pm + args),
                **kwargs)
            until, dlm = pm[-2:]
            self.assertEqual(SP.mock_calls[-2:], [
                call('until', until, iff=until),
                call('delimiter', dlm, iff=dlm)])
            acc, cont = self.client.account, self.client.container
            self.assertEqual(delete.mock_calls[-1], call(
                '/%s/%s/%s' % (acc, cont, obj),
                *args,
                success=kwargs.pop('success', 204),
                **kwargs))


class PithosMethods(TestCase):

    def test__range_up(self):
        from kamaki.clients.pithos import _range_up
        for args, expected in (
                ((0, 100, 1000, '10'), '0-10'),
                ((0, 100, 1000, '-10'), ''),
                ((900, 1000, 1000, '-10'), '990-1000'),
                ((150, 250, 1000, '10'), ''),
                ((10, 200, 1000, '130-170'), '130-170'),
                ((150, 200, 1000, '130-170'), '150-170'),
                ((100, 150, 1000, '130-170'), '130-150'),
                ((200, 250, 1000, '130-170'), ''),
                ((100, 250, 1000, '30-170,200-270'), '100-170,200-250'),
                ((40, 950, 1000, '-170,200-270,50',), '830-950,200-270,40-50'),
                ((740, 900, 1000, '-170,200-270,50',), '830-900'),
                ((42, 333, 800, '100,50-200,-600',), '42-100,50-200,200-333')):
            self.assertEqual(_range_up(*args), expected)


class PithosClient(TestCase):

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
        self.client = pithos.PithosClient(self.url, self.token)
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

    @patch('%s.account_head' % pithos_pkg, return_value=FR())
    def test_get_account_info(self, AH):
        FR.headers = account_info
        for until in (None, 'un71L-d473'):
            r = self.client.get_account_info(until=until)
            self.assert_dicts_are_equal(r, account_info)
            self.assertEqual(AH.mock_calls[-1], call(until=until))
        FR.status_code = 401
        self.assertRaises(ClientError, self.client.get_account_info)

    @patch('%s.account_post' % pithos_pkg, return_value=FR())
    def test_del_account_meta(self, AP):
        keys = ['k1', 'k2', 'k3']
        for key in keys:
            self.client.del_account_meta(key)
            self.assertEqual(
                AP.mock_calls[-1],
                call(update=True, metadata={key: ''}))

    @patch('%s.container_head' % pithos_pkg, return_value=FR())
    def test_get_container_info(self, CH):
        FR.headers = container_info
        r = self.client.get_container_info()
        self.assert_dicts_are_equal(r, container_info)
        u = 'some date'
        r = self.client.get_container_info(until=u)
        self.assertEqual(CH.mock_calls, [call(until=None), call(until=u)])

    @patch('%s.account_get' % pithos_pkg, return_value=FR())
    def test_list_containers(self, get):
        FR.json = container_list
        r = self.client.list_containers()
        get.assert_called_once_with()
        for i in range(len(r)):
            self.assert_dicts_are_equal(r[i], container_list[i])

    @patch('%s.get_container_info' % pithos_pkg, return_value=container_info)
    @patch('%s.container_post' % pithos_pkg, return_value=FR())
    @patch('%s.object_put' % pithos_pkg, return_value=FR())
    def test_upload_object(self, OP, CP, GCI):
        num_of_blocks = 8
        tmpFile = self._create_temp_file(num_of_blocks)

        # Without kwargs
        exp_headers = dict(id='container id', name='container name')
        FR.headers = dict(exp_headers)
        r = self.client.upload_object(obj, tmpFile)
        self.assert_dicts_are_equal(r, exp_headers)
        self.assertEqual(GCI.mock_calls[-1], call())

        [call1, call2] = OP.mock_calls
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
            r = self.client.upload_object(
                obj, tmpFile,
                hash_cb=blck_gen, upload_cb=upld_gen)
            self.assert_dicts_are_equal(r, exp_headers)

            for i, c in enumerate(OP.mock_calls[-mock_offset:]):
                self.assertEqual(OP.mock_calls[i], c)

        #  With content-type
        tmpFile.seek(0)
        ctype = 'video/mpeg'
        sharing = dict(read=['u1', 'g1', 'u2'], write=['u1'])
        r = self.client.upload_object(
            obj, tmpFile, content_type=ctype, sharing=sharing)
        self.assert_dicts_are_equal(r, exp_headers)
        self.assertEqual(OP.mock_calls[-1][2]['content_type'], ctype)
        self.assert_dicts_are_equal(
            OP.mock_calls[-2][2]['permissions'],
            sharing)

        # With other args
        tmpFile.seek(0)
        kwargs = dict(
            etag='s0m3E74g',
            if_etag_match='if etag match',
            if_not_exist=True,
            content_type=ctype,
            content_disposition=ctype + 'd15p051710n',
            public=True,
            content_encoding='802.11',
            container_info_cache={})
        r = self.client.upload_object(obj, tmpFile, **kwargs)
        self.assert_dicts_are_equal(r, exp_headers)

        kwargs.pop('if_not_exist')
        ematch = kwargs.pop('if_etag_match')
        etag = kwargs.pop('etag')
        self.assert_dicts_are_equal(
            kwargs.pop('container_info_cache'),
            {self.client.container: container_info})
        for arg, val in kwargs.items():
            self.assertEqual(OP.mock_calls[-2][2][arg], val)
        self.assertEqual(OP.mock_calls[-1][2]['if_etag_match'], ematch)
        self.assertEqual(OP.mock_calls[-1][2]['if_etag_not_match'], '*')
        self.assertEqual(OP.mock_calls[-1][2]['etag'], etag)

    @patch('%s.get_container_info' % pithos_pkg, return_value=container_info)
    @patch('%s.container_post' % pithos_pkg, return_value=FR())
    @patch('%s.object_put' % pithos_pkg, return_value=FR())
    def test_upload_from_string(self, OP, CP, GCI):
        num_of_blocks = 2
        tmpFile = self._create_temp_file(num_of_blocks)
        tmpFile.seek(0)
        src_str = tmpFile.read()

        exp_headers = dict(id='container id', name='container name')
        FR.headers = dict(exp_headers)
        r = self.client.upload_from_string(obj, src_str)
        self.assert_dicts_are_equal(r, exp_headers)
        self.assertEqual(GCI.mock_calls[-1], call())

        [call1, call2] = OP.mock_calls
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
            r = self.client.upload_object(
                obj, tmpFile,
                hash_cb=blck_gen, upload_cb=upld_gen)
            self.assert_dicts_are_equal(r, exp_headers)

            for i, c in enumerate(OP.mock_calls[-mock_offset:]):
                self.assertEqual(OP.mock_calls[i], c)

        #  With content-type
        tmpFile.seek(0)
        ctype = 'video/mpeg'
        sharing = dict(read=['u1', 'g1', 'u2'], write=['u1'])
        r = self.client.upload_object(
            obj, tmpFile,
            content_type=ctype, sharing=sharing)
        self.assert_dicts_are_equal(r, exp_headers)
        self.assertEqual(OP.mock_calls[-1][2]['content_type'], ctype)
        self.assert_dicts_are_equal(
            OP.mock_calls[-2][2]['permissions'],
            sharing)

        # With other args
        tmpFile.seek(0)
        kwargs = dict(
            etag='s0m3E74g',
            if_etag_match='if etag match',
            if_not_exist=True,
            content_type=ctype,
            content_disposition=ctype + 'd15p051710n',
            public=True,
            content_encoding='802.11',
            container_info_cache={})
        r = self.client.upload_object(obj, tmpFile, **kwargs)
        self.assert_dicts_are_equal(r, exp_headers)

        kwargs.pop('if_not_exist')
        ematch = kwargs.pop('if_etag_match')
        etag = kwargs.pop('etag')
        self.assert_dicts_are_equal(
            kwargs.pop('container_info_cache'),
            {self.client.container: container_info})
        for arg, val in kwargs.items():
            self.assertEqual(OP.mock_calls[-2][2][arg], val)
        self.assertEqual(OP.mock_calls[-1][2]['if_etag_match'], ematch)
        self.assertEqual(OP.mock_calls[-1][2]['if_etag_not_match'], '*')
        self.assertEqual(OP.mock_calls[-1][2]['etag'], etag)

    def test_get_object_info(self):
        FR.headers = object_info
        version = 'v3r510n'
        with patch.object(
                pithos.PithosClient, 'object_head',
                return_value=FR()) as head:
            r = self.client.get_object_info(obj)
            self.assertEqual(r, object_info)
            r = self.client.get_object_info(obj, version=version)
            self.assertEqual(head.mock_calls, [
                call(obj, version=None),
                call(obj, version=version)])
        with patch.object(
                pithos.PithosClient, 'object_head',
                side_effect=ClientError('Obj not found', 404)):
            self.assertRaises(
                ClientError,
                self.client.get_object_info,
                obj, version=version)

    @patch('%s.get_object_info' % pithos_pkg, return_value=object_info)
    def test_get_object_meta(self, GOI):
        for version in (None, 'v3r510n'):
            r = self.client.get_object_meta(obj, version)
            for k in [k for k in object_info if k.startswith('x-object-meta')]:
                self.assertEqual(r.pop(k), object_info[k])
            self.assertFalse(len(r))
            self.assertEqual(GOI.mock_calls[-1], call(obj, version=version))

    @patch('%s.object_post' % pithos_pkg, return_value=FR())
    def test_del_object_meta(self, post):
        metakey = '50m3m3t4k3y'
        self.client.del_object_meta(obj, metakey)
        post.assert_called_once_with(obj, update=True, metadata={metakey: ''})

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

    #  Pithos+ only methods

    @patch('%s.container_put' % pithos_pkg, return_value=FR())
    def test_create_container(self, CP):
        FR.headers = container_info
        cont = 'an0th3r_c0n741n3r'

        r = self.client.create_container()
        self.assert_dicts_are_equal(r, container_info)
        CP.assert_called_once_with(
            project_id=None, quota=None, versioning=None, metadata=None)

        bu_cont = self.client.container
        r = self.client.create_container(cont)
        self.assertEqual(self.client.container, bu_cont)
        self.assert_dicts_are_equal(r, container_info)
        self.assertEqual(
            CP.mock_calls[-1],
            call(project_id=None, quota=None, versioning=None, metadata=None))

        meta = dict(k1='v1', k2='v2')
        r = self.client.create_container(cont, 42, 'auto', meta, 'prid')
        self.assertEqual(self.client.container, bu_cont)
        self.assert_dicts_are_equal(r, container_info)
        self.assertEqual(CP.mock_calls[-1], call(
            quota=42, versioning='auto', project_id='prid', metadata=meta))

    @patch('%s.container_delete' % pithos_pkg, return_value=FR())
    def test_purge_container(self, CD):
        self.client.purge_container()
        self.assertTrue('until' in CD.mock_calls[-1][2])
        cont = self.client.container
        self.client.purge_container('another-container')
        self.assertEqual(self.client.container, cont)

    @patch('%s.object_put' % pithos_pkg, return_value=FR())
    def test_upload_object_unchunked(self, put):
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
        r = self.client.upload_object_unchunked(obj, tmpFile)
        self.assert_dicts_are_equal(r, FR.headers)
        self.assertEqual(put.mock_calls[-1][1], (obj,))
        self.assertEqual(
            sorted(put.mock_calls[-1][2].keys()),
            sorted(expected.keys()))
        kwargs = dict(expected)
        kwargs.pop('success')
        kwargs['size'] = kwargs.pop('data')
        kwargs['sharing'] = kwargs.pop('permissions')
        tmpFile.seek(0)
        r = self.client.upload_object_unchunked(obj, tmpFile, **kwargs)
        self.assert_dicts_are_equal(r, FR.headers)
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

    @patch('%s.object_put' % pithos_pkg, return_value=FR())
    def test_create_object_by_manifestation(self, put):
        manifest = '%s/%s' % (self.client.container, obj)
        kwargs = dict(
            etag='some-etag',
            content_encoding='some content_encoding',
            content_type='some content-type',
            content_disposition='some content_disposition',
            public=True,
            sharing=dict(read=['u1', 'g1', 'u2'], write=['u1']))
        r = self.client.create_object_by_manifestation(obj)
        self.assert_dicts_are_equal(r, FR.headers)
        expected = dict(content_length=0, manifest=manifest)
        for k in kwargs:
            expected['permissions' if k == 'sharing' else k] = None
        self.assertEqual(put.mock_calls[-1], call(obj, **expected))
        r = self.client.create_object_by_manifestation(obj, **kwargs)
        self.assert_dicts_are_equal(r, FR.headers)
        expected.update(kwargs)
        expected['permissions'] = expected.pop('sharing')
        self.assertEqual(put.mock_calls[-1], call(obj, **expected))

    @patch('%s.get_object_hashmap' % pithos_pkg, return_value=object_hashmap)
    @patch('%s.object_get' % pithos_pkg, return_value=FR())
    def test_download_to_string(self, GET, GOH):
        FR.content = 'some sample content'
        num_of_blocks = len(object_hashmap['hashes'])
        r = self.client.download_to_string(obj)
        expected_content = FR.content * num_of_blocks
        self.assertEqual(expected_content, r)
        self.assertEqual(len(GET.mock_calls), num_of_blocks)
        self.assertEqual(GET.mock_calls[-1][1], (obj,))

        kwargs = dict(
            version='version',
            range_str='10-20',
            if_match='if and only if',
            if_none_match='if and only not',
            if_modified_since='what if not?',
            if_unmodified_since='this happens if not!',
            headers=dict())
        expargs = dict(kwargs)
        expargs.pop('range_str')
        for k, v in expargs.items():
            expargs[k] = None if v else v
        GOH.assert_called_once_with(obj, **expargs)

        r = self.client.download_to_string(obj, **kwargs)
        expargs['data_range'] = 'bytes=%s' % kwargs['range_str']
        expargs.pop('headers')
        for k, v in expargs.items():
            self.assertEqual(
                GET.mock_calls[-1][2][k],
                v or kwargs.get(k))

    @patch('%s.get_object_hashmap' % pithos_pkg, return_value=object_hashmap)
    @patch('%s.object_get' % pithos_pkg, return_value=FR())
    def test_download_object(self, GET, GOH):
        num_of_blocks = 8
        tmpFile = self._create_temp_file(num_of_blocks)
        FR.content = tmpFile.read(4 * 1024 * 1024)
        tmpFile = self._create_temp_file(num_of_blocks)
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
        FR.json = object_hashmap
        for empty in (304, 412):
            with patch.object(
                    pithos.PithosClient, 'object_get',
                    side_effect=ClientError('Empty', status=empty)):
                r = self.client.get_object_hashmap(obj)
                self.assertEqual(r, {})
        exp_args = dict(
            hashmap=True,
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
            if_unmodified_since='some date here')
        with patch.object(
                pithos.PithosClient, 'object_get', return_value=FR()) as get:
            r = self.client.get_object_hashmap(obj)
            self.assertEqual(r, object_hashmap)
            self.assertEqual(get.mock_calls[-1], call(obj, **exp_args))
            r = self.client.get_object_hashmap(obj, **kwargs)
            exp_args['if_etag_match'] = kwargs.pop('if_match')
            exp_args['if_etag_not_match'] = kwargs.pop('if_none_match')
            exp_args.update(kwargs)
            self.assertEqual(get.mock_calls[-1], call(obj, **exp_args))

    @patch('%s.account_post' % pithos_pkg, return_value=FR())
    def test_set_account_group(self, post):
        (group, usernames) = ('aU53rGr0up', ['u1', 'u2', 'u3'])
        self.client.set_account_group(group, usernames)
        post.assert_called_once_with(update=True, groups={group: usernames})

    @patch('%s.account_post' % pithos_pkg, return_value=FR())
    def test_del_account_group(self, post):
        group = 'aU53rGr0up'
        self.client.del_account_group(group)
        post.assert_called_once_with(update=True, groups={group: []})

    @patch('%s.get_account_info' % pithos_pkg, return_value=account_info)
    def test_get_account_quota(self, GAI):
        key = 'x-account-policy-quota'
        r = self.client.get_account_quota()
        GAI.assert_called_once_with()
        self.assertEqual(r[key], account_info[key])

    def test_get_account_meta(self):
        key = 'x-account-meta-'
        with patch.object(
                pithos.PithosClient, 'get_account_info',
                return_value=account_info):
            r = self.client.get_account_meta()
            keys = [k for k in r if k.startswith(key)]
            self.assertFalse(keys)
        acc_info = dict(account_info)
        acc_info['%sk1' % key] = 'v1'
        acc_info['%sk2' % key] = 'v2'
        acc_info['%sk3' % key] = 'v3'
        with patch.object(
                pithos.PithosClient, 'get_account_info',
                return_value=acc_info):
            r = self.client.get_account_meta()
            for k in [k for k in acc_info if k.startswith(key)]:
                self.assertEqual(r[k], acc_info[k])

    def test_get_account_group(self):
        key = 'x-account-group-'
        with patch.object(
                pithos.PithosClient, 'get_account_info',
                return_value=account_info):
            r = self.client.get_account_group()
            keys = [k for k in r if k.startswith(key)]
            self.assertFalse(keys)
        acc_info = dict(account_info)
        acc_info['%sk1' % key] = 'g1'
        acc_info['%sk2' % key] = 'g2'
        acc_info['%sk3' % key] = 'g3'
        with patch.object(
                pithos.PithosClient, 'get_account_info',
                return_value=acc_info):
            r = self.client.get_account_group()
            for k in [k for k in acc_info if k.startswith(key)]:
                self.assertEqual(r[k], acc_info[k])

    @patch('%s.account_post' % pithos_pkg, return_value=FR())
    def test_set_account_meta(self, post):
        metas = dict(k1='v1', k2='v2', k3='v3')
        self.client.set_account_meta(metas)
        post.assert_called_once_with(update=True, metadata=metas)

    @patch('%s.container_delete' % pithos_pkg, return_value=FR())
    def test_del_container(self, delete):
        for kwarg in (
                dict(delimiter=None, until=None),
                dict(delimiter='X', until='50m3d473')):
            self.client.del_container(**kwarg)
            expected = dict(kwarg)
            expected['success'] = (204, 404, 409)
            self.assertEqual(delete.mock_calls[-1], call(**expected))
        for status_code in (404, 409):
            FR.status_code = status_code
            self.assertRaises(ClientError, self.client.del_container)

    @patch('%s.get_container_info' % pithos_pkg, return_value=container_info)
    def test_get_container_versioning(self, GCI):
        key = 'x-container-policy-versioning'
        cont = 'c0n7-417'
        bu_cnt = self.client.container
        for container in (None, cont):
            r = self.client.get_container_versioning(container=container)
            self.assertEqual(r[key], container_info[key])
            self.assertEqual(GCI.mock_calls[-1], call())
            self.assertEqual(bu_cnt, self.client.container)

    @patch('%s.get_container_info' % pithos_pkg, return_value=container_info)
    def test_get_container_limit(self, GCI):
        key = 'x-container-policy-quota'
        cont = 'c0n7-417'
        bu_cnt = self.client.container
        for container in (None, cont):
            r = self.client.get_container_limit(container=container)
            self.assertEqual(r[key], container_info[key])
            self.assertEqual(GCI.mock_calls[-1], call())
            self.assertEqual(bu_cnt, self.client.container)

    def test_get_container_meta(self):
        somedate = '50m3d473'
        key = 'x-container-meta'
        metaval = '50m3m374v41'
        container_plus = dict(container_info)
        container_plus[key] = metaval
        for ret in ((container_info, {}), (container_plus, {key: metaval})):
            with patch.object(
                    pithos.PithosClient,
                    'get_container_info',
                    return_value=ret[0]) as GCI:
                for until in (None, somedate):
                    r = self.client.get_container_meta(until=until)
                    self.assertEqual(r, ret[1])
                    self.assertEqual(GCI.mock_calls[-1], call(until=until))

    def test_get_container_object_meta(self):
        somedate = '50m3d473'
        key = 'x-container-object-meta'
        metaval = '50m3m374v41'
        container_plus = dict(container_info)
        container_plus[key] = metaval
        for ret in (
                (container_info, {key: ''}),
                (container_plus, {key: metaval})):
            with patch.object(
                    pithos.PithosClient,
                    'get_container_info',
                    return_value=ret[0]) as GCI:
                for until in (None, somedate):
                    r = self.client.get_container_object_meta(until=until)
                    self.assertEqual(r, ret[1])
                    self.assertEqual(GCI.mock_calls[-1], call(until=until))

    @patch('%s.container_post' % pithos_pkg, return_value=FR())
    def test_set_container_meta(self, post):
        metas = dict(k1='v1', k2='v2', k3='v3')
        self.client.set_container_meta(metas)
        post.assert_called_once_with(update=True, metadata=metas)

    @patch('%s.container_post' % pithos_pkg, return_value=FR())
    def test_del_container_meta(self, AP):
        self.client.del_container_meta('somekey')
        AP.assert_called_once_with(update=True, metadata={'somekey': ''})

    @patch('%s.container_post' % pithos_pkg, return_value=FR())
    def test_set_container_limit(self, post):
        qu = 1024
        self.client.set_container_limit(qu)
        post.assert_called_once_with(update=True, quota=qu)

    @patch('%s.container_post' % pithos_pkg, return_value=FR())
    def test_set_container_versioning(self, post):
        vrs = 'n3wV3r51on1ngTyp3'
        self.client.set_container_versioning(vrs)
        post.assert_called_once_with(update=True, versioning=vrs)

    @patch('%s.object_delete' % pithos_pkg, return_value=FR())
    def test_del_object(self, delete):
        for kwarg in (
                dict(delimiter=None, until=None),
                dict(delimiter='X', until='50m3d473')):
            self.client.del_object(obj, **kwarg)
            self.assertEqual(delete.mock_calls[-1], call(obj, **kwarg))

    @patch('%s.object_post' % pithos_pkg, return_value=FR())
    def test_set_object_meta(self, post):
        metas = dict(k1='v1', k2='v2', k3='v3')
        self.assertRaises(
            AssertionError,
            self.client.set_object_meta,
            obj, 'Non dict arg')
        self.client.set_object_meta(obj, metas)
        post.assert_called_once_with(obj, update=True, metadata=metas)

    @patch('%s.object_post' % pithos_pkg, return_value=FR())
    def test_publish_object(self, post):
        oinfo = dict(object_info)
        val = 'pubL1c'
        oinfo['x-object-public'] = 'https://www.example.com/' + val
        with patch.object(
                pithos.PithosClient, 'get_object_info',
                return_value=oinfo) as GOF:
            r = self.client.publish_object(obj)
            self.assertEqual(
                post.mock_calls[-1],
                call(obj, public=True, update=True))
            self.assertEqual(GOF.mock_calls[-1], call(obj))
            self.assertEqual(r, '%s%s' % (self.url[:-6], val))

    @patch('%s.object_post' % pithos_pkg, return_value=FR())
    def test_unpublish_object(self, post):
        self.client.unpublish_object(obj)
        post.assert_called_once_with(obj, public=False, update=True)

    def test_get_object_sharing(self):
        info = dict(object_info)
        expected = dict(read='u1,g1,u2', write='u1')
        info['x-object-sharing'] = '; '.join(
            ['%s=%s' % (k, v) for k, v in expected.items()])
        with patch.object(
                pithos.PithosClient, 'get_object_info',
                return_value=info) as GOF:
            r = self.client.get_object_sharing(obj)
            self.assertEqual(GOF.mock_calls[-1], call(obj))
            self.assert_dicts_are_equal(r, expected)
            info['x-object-sharing'] = '//'.join(
                ['%s=%s' % (k, v) for k, v in expected.items()])
            self.assertRaises(
                ValueError,
                self.client.get_object_sharing,
                obj)
            info['x-object-sharing'] = '; '.join(
                ['%s:%s' % (k, v) for k, v in expected.items()])
            self.assertRaises(
                ClientError,
                self.client.get_object_sharing,
                obj)
            info['x-object-sharing'] = 'read=%s' % expected['read']
            r = self.client.get_object_sharing(obj)
            expected.pop('write')
            self.assert_dicts_are_equal(r, expected)

    @patch('%s.object_post' % pithos_pkg, return_value=FR())
    def test_set_object_sharing(self, OP):
        read_perms = ['u1', 'g1', 'u2', 'g2']
        write_perms = ['u1', 'g1']
        for kwargs in (
                dict(read_permission=read_perms, write_permission=write_perms),
                dict(read_permission=read_perms),
                dict(write_permission=write_perms),
                dict()):
            self.client.set_object_sharing(obj, **kwargs)
            kwargs['read'] = kwargs.pop('read_permission', '')
            kwargs['write'] = kwargs.pop('write_permission', '')
            self.assertEqual(
                OP.mock_calls[-1],
                call(obj, update=True, permissions=kwargs))

    @patch('%s.set_object_sharing' % pithos_pkg)
    def test_del_object_sharing(self, SOS):
        self.client.del_object_sharing(obj)
        SOS.assert_called_once_with(obj)

    @patch('%s.get_container_info' % pithos_pkg, return_value=container_info)
    @patch('%s.object_post' % pithos_pkg, return_value=FR())
    def test_append_object(self, post, GCI):
        num_of_blocks = 4
        tmpFile = self._create_temp_file(num_of_blocks)
        tmpFile.seek(0, 2)
        file_size = tmpFile.tell()
        for turn in range(2):
            tmpFile.seek(0, 0)

            try:
                from progress.bar import ShadyBar
                apn_bar = ShadyBar('Mock append')
            except ImportError:
                apn_bar = None

            if apn_bar:

                def append_gen(n):
                    for i in apn_bar.iter(range(n)):
                        yield
                    yield

            else:
                append_gen = None

            self.client.append_object(
                obj, tmpFile,
                upload_cb=append_gen if turn else None)
            self.assertEqual((turn + 1) * num_of_blocks, len(post.mock_calls))
            (args, kwargs) = post.mock_calls[-1][1:3]
            self.assertEqual(kwargs['obj'], obj)
            self.assertEqual(kwargs['content_length'], len(kwargs['data']))
            fsize = num_of_blocks * int(kwargs['content_length'])
            self.assertEqual(fsize, file_size)
            self.assertEqual(kwargs['content_range'], 'bytes */*')
            exp = 'application/octet-stream'
            self.assertEqual(kwargs['content_type'], exp)
            self.assertEqual(kwargs['update'], True)

    @patch('%s.object_post' % pithos_pkg, return_value=FR())
    def test_truncate_object(self, post):
        upto_bytes, obj_info_path = 377, '%s.get_object_info' % pithos_pkg

        with patch(obj_info_path, side_effect=ClientError('Not found')):
            self.assertRaises(
                ClientError, self.client.truncate_object, obj, upto_bytes)

        ret_val = {'content-type': 'ctype'}
        with patch(obj_info_path, return_value=ret_val) as get_object_info:
            self.client.truncate_object(obj, upto_bytes)
            post.assert_called_once_with(
                obj,
                update=True,
                object_bytes=upto_bytes,
                content_range='bytes 0-%s/*' % upto_bytes,
                content_type='ctype',
                source_object='/%s/%s' % (self.client.container, obj))
            get_object_info.assert_called_once_with(obj)

    @patch('%s.get_container_info' % pithos_pkg, return_value=container_info)
    @patch('%s.object_post' % pithos_pkg, return_value=FR())
    def test_overwrite_object(self, post, GCI):
        num_of_blocks = 4
        tmpFile = self._create_temp_file(num_of_blocks)
        tmpFile.seek(0, 2)
        file_size = tmpFile.tell()
        info = dict(object_info)
        info['content-length'] = file_size
        block_size = container_info['x-container-block-size']
        with patch.object(
                pithos.PithosClient, 'get_object_info',
                return_value=info) as GOI:
            for start, end in (
                    (0, file_size + 1),
                    (file_size + 1, file_size + 2)):
                tmpFile.seek(0, 0)
                self.assertRaises(
                    AssertionError,
                    self.client.overwrite_object, obj, start, end, tmpFile)
            for start, end in ((0, 144), (144, 233), (233, file_size)):
                tmpFile.seek(0, 0)
                owr_gen = None
                exp_size = end - start + 1
                if not start or exp_size > block_size:
                    try:
                        from progress.bar import ShadyBar
                        owr_bar = ShadyBar('Mock append')
                    except ImportError:
                        owr_bar = None

                    if owr_bar:

                        def owr_gen(n):
                            for i in owr_bar.iter(range(n)):
                                yield
                            yield

                    if exp_size > block_size:
                        exp_size = exp_size % block_size or block_size

                vrs = 'version'
                self.client.overwrite_object(
                    obj, start, end, tmpFile, vrs, owr_gen)
                self.assertEqual(GOI.mock_calls[-1], call(obj, version=vrs))
                self.assertEqual(GCI.mock_calls[-1], call())
                (args, kwargs) = post.mock_calls[-1][1:3]
                self.assertEqual(args, (obj,))
                self.assertEqual(len(kwargs['data']), exp_size)
                self.assertEqual(kwargs['content_length'], exp_size)
                self.assertEqual(kwargs['update'], True)
                exp = 'application/octet-stream'
                self.assertEqual(kwargs['content_type'], exp)

    @patch('%s.set_param' % pithos_pkg)
    @patch('%s.get' % pithos_pkg, return_value=FR())
    def test_get_sharing_accounts(self, get, SP):
        FR.json = sharers
        for kws in (
                dict(),
                dict(limit='50m3-11m17'),
                dict(marker='X'),
                dict(limit='50m3-11m17', marker='X')):
            r = self.client.get_sharing_accounts(**kws)
            self.assertEqual(get.mock_calls[-1], call('', success=(200, 204)))
            self.assertEqual(SP.mock_calls[-3], call('format', 'json'))
            limit, marker = kws.get('limit', None), kws.get('marker', None)
            self.assertEqual(SP.mock_calls[-2], call(
                'limit', limit,
                iff=limit is not None))
            self.assertEqual(SP.mock_calls[-1], call(
                'marker', marker,
                iff=marker is not None))
            for i in range(len(r)):
                self.assert_dicts_are_equal(r[i], sharers[i])

    @patch('%s.object_get' % pithos_pkg, return_value=FR())
    def test_get_object_versionlist(self, get):
        info = dict(object_info)
        info['versions'] = ['v1', 'v2']
        FR.json = info
        r = self.client.get_object_versionlist(obj)
        get.assert_called_once_with(obj, format='json', version='list')
        self.assertEqual(r, info['versions'])

if __name__ == '__main__':
    from sys import argv
    from kamaki.clients.test import runTestCase
    not_found = True
    if not argv[1:] or argv[1] == 'PithosClient':
        not_found = False
        runTestCase(PithosClient, 'Pithos Client', argv[2:])
    if not argv[1:] or argv[1] == 'PithosRestClient':
        not_found = False
        runTestCase(PithosRestClient, 'PithosRest Client', argv[2:])
    if not argv[1:] or argv[1] == 'PithosMethods':
        not_found = False
        runTestCase(PithosRestClient, 'Pithos Methods', argv[2:])
    if not_found:
        print('TestCase %s not found' % argv[1])
