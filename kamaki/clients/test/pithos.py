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


class Pithos(TestCase):

    class FR(object):
        """FR stands for Fake Response"""
        json = dict()
        headers = {}
        content = json
        status = None
        status_code = 200
        headers = dict()

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
