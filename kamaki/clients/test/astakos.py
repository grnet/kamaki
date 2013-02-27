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

from mock import Mock, patch

from unittest import TestCase
from kamaki.clients.astakos import AstakosClient
from json import dumps


class Astakos(TestCase):

    class fakeResponse(object):
        json = dumps(dict(
            name='Simple Name',
            username='User Full Name',
            auth_token_expires='1362583796000',
            auth_token_created='1359991796000',
            email=['user@example.gr'],
            id=42,
            uuid='aus3r-uu1d-f0r-73s71ng-as7ak0s'))
        headers = {}
        content = json
        status = None
        status_code = 200

        def release(self):
            pass

    def setUp(self):
        self.url = 'https://astakos.example.com'
        self.token = 'ast@k0sT0k3n=='
        self.client = AstakosClient(self.url, self.token)
        from kamaki.clients.connection.kamakicon import KamakiHTTPConnection
        self.C = KamakiHTTPConnection
        self.FR = self.fakeResponse

    def test_authenticate(self):
        with patch.object(self.C, 'perform_request', return_value=self.FR()):
            r = self.client.authenticate()
            for term in (
                    'name',
                    'username',
                    'auth_token_expires',
                    'auth_token_created',
                    'uuid',
                    'id',
                    'email'):
                self.assertTrue(term in r)

    """
    def test_info(self):
        self._test_0020_info()

    def _test_0020_info(self):
        self.assertTrue(set([
            'name',
            'username',
            'uuid']).issubset(self.client.info().keys()))

    def test_get(self):
        self._test_0020_get()

    def _test_0020_get(self):
        for term in ('uuid', 'name', 'username'):
            self.assertEqual(
                self.client.term(term, self['astakos', 'token']),
                self['astakos', term])
        self.assertTrue(self['astakos', 'email'] in self.client.term('email'))

    def test_list(self):
        self.client.authenticate()
        self._test_0020_list()

    def _test_0020_list(self):
        terms = set(['name', 'username', 'uuid', 'email', 'auth_token'])
        uuid = 0
        for r in self.client.list():
            self.assertTrue(terms.issubset(r.keys()))
            self.assertTrue(uuid != r['uuid'] if uuid else True)
            uuid = r['uuid']
    """
