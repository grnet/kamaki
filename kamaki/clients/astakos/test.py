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

from mock import patch, call
from unittest import TestCase

from kamaki.clients import astakos


example = dict(
        name='Simple Name',
        username='User Full Name',
        auth_token_expires='1362583796000',
        auth_token_created='1359991796000',
        email=['user@example.gr'],
        id=42,
        uuid='aus3r-uu1d-f0r-73s71ng-as7ak0s')

example0 = dict(
        name='Simple Name 0',
        username='User Full Name 0',
        auth_token_expires='1362583796001',
        auth_token_created='1359991796001',
        email=['user0@example.gr'],
        id=32,
        uuid='an07h2r-us3r-uu1d-f0r-as7ak0s')


class FR(object):
    json = example
    headers = {}
    content = json
    status = None
    status_code = 200

astakos_pkg = 'kamaki.clients.astakos.AstakosClient'


class AstakosClient(TestCase):

    cached = False

    def setUp(self):
        self.url = 'https://astakos.example.com'
        self.token = 'ast@k0sT0k3n=='
        self.client = astakos.AstakosClient(self.url, self.token)

    def tearDown(self):
        FR.json = example

    @patch('%s.get' % astakos_pkg, return_value=FR())
    def _authenticate(self, get):
        r = self.client.authenticate()
        self.assertEqual(get.mock_calls[-1], call('/im/authenticate'))
        self.cached = True
        return r

    def test_authenticate(self):
        r = self._authenticate()
        for term, val in example.items():
            self.assertTrue(term in r)
            self.assertEqual(val, r[term])

    def test_info(self):
        if not self.cached:
            self._authenticate()
            return self.test_info()
        self.assertTrue(set(
            example.keys()).issubset(self.client.info().keys()))

    def test_get(self):
        if not self.cached:
            self._authenticate()
            return self.test_get()
        for term, val in example.items():
            self.assertEqual(self.client.term(term, self.token), val)
        self.assertTrue(example['email'][0] in self.client.term('email'))

    def test_list(self):
        if not self.cached:
            self._authenticate
        FR.json = example0
        self._authenticate()
        r = self.client.list()
        self.assertTrue(len(r) == 1)
        self.assertEqual(r[0]['auth_token'], self.token)

if __name__ == '__main__':
    from sys import argv
    from kamaki.clients.test import runTestCase
    runTestCase(AstakosClient, 'AstakosClient', argv[1:])
