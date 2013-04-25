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

from kamaki.clients import livetest
from kamaki.clients.astakos import AstakosClient


class Astakos(livetest.Generic):
    def setUp(self):
        self.client = AstakosClient(
            self['user', 'url'],
            self['user', 'token'])

    def test_authenticate(self):
        self._test_0010_authenticate()

    def _test_0010_authenticate(self):
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
                self.client.term(term, self['user', 'token']),
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
