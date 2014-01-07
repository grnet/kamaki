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
from logging import getLogger
from unittest import TestCase

from kamaki.clients import ClientError


example = dict(
    access=dict(
         token=dict(
            expires="2013-07-14T10:07:42.481134+00:00",
            id="ast@k0sT0k3n==",
            tenant=dict(
                id="42",
                name="Simple Name 0")
        ),
        serviceCatalog=[
            dict(name='service name 1', type='compute', endpoints=[
                dict(versionId='v1', publicUrl='http://1.1.1.1/v1'),
                dict(versionId='v2', publicUrl='http://1.1.1.1/v2')]),
            dict(name='service name 3', type='object-storage', endpoints=[
                dict(versionId='v2', publicUrl='http://1.1.1.1/v2'),
                dict(versionId='v2.1', publicUrl='http://1.1.1.1/v2/xtra')])
            ],
        user=dict(
            name='Simple Name 0',
            username='User Full Name 0',
            auth_token_expires='1362585796000',
            auth_token_created='1359931796000',
            email=['user0@example.gr'],
            id=42,
            uuid='aus3r-uu1d-507-73s71ng-as7ak0s')
        )
    )


class FR(object):
    json = example
    headers = {}
    content = json
    status = None
    status_code = 200

astakos_pkg = 'kamaki.clients.astakos'


class AstakosClient(TestCase):

    cached = False

    def assert_dicts_are_equal(self, d1, d2):
        for k, v in d1.items():
            self.assertTrue(k in d2)
            if isinstance(v, dict):
                self.assert_dicts_are_equal(v, d2[k])
            else:
                self.assertEqual(unicode(v), unicode(d2[k]))

    def setUp(self):
        self.url = 'https://astakos.example.com'
        self.token = 'ast@k0sT0k3n=='
        from kamaki.clients.astakos import AstakosClient as AC
        self.client = AC(self.url, self.token)

    def tearDown(self):
        FR.json = example

    @patch('%s.LoggedAstakosClient.__init__' % astakos_pkg, return_value=None)
    @patch(
        '%s.LoggedAstakosClient.get_endpoints' % astakos_pkg,
        return_value=example)
    def _authenticate(self, get_endpoints, sac):
        r = self.client.authenticate()
        self.assertEqual(
            sac.mock_calls[-1], call(self.token, self.url,
                logger=getLogger('astakosclient')))
        self.assertEqual(get_endpoints.mock_calls[-1], call())
        return r

    def test_authenticate(self):
        r = self._authenticate()
        self.assert_dicts_are_equal(r, example)
        uuid = example['access']['user']['id']
        self.assert_dicts_are_equal(self.client._uuids, {self.token: uuid})
        self.assert_dicts_are_equal(self.client._cache, {uuid: r})
        from astakosclient import AstakosClient as SAC
        self.assertTrue(isinstance(self.client._astakos[uuid], SAC))
        self.assert_dicts_are_equal(self.client._uuids2usernames, {uuid: {}})
        self.assert_dicts_are_equal(self.client._usernames2uuids, {uuid: {}})

    def test_get_client(self):
        if not self.cached:
            self._authenticate()
        from astakosclient import AstakosClient as SNFAC
        self.assertTrue(self.client.get_client(), SNFAC)

    def test_get_token(self):
        self._authenticate()
        uuid = self.client._uuids.values()[0]
        self.assertEqual(self.client.get_token(uuid), self.token)

    def test_get_services(self):
        if not self.cached:
            self._authenticate()
        slist = self.client.get_services()
        self.assertEqual(slist, example['access']['serviceCatalog'])

    def test_get_service_details(self):
        if not self.cached:
            self._authenticate()
        stype = '#FAIL'
        self.assertRaises(ClientError, self.client.get_service_details, stype)
        stype = 'compute'
        expected = [s for s in example['access']['serviceCatalog'] if (
            s['type'] == stype)]
        self.assert_dicts_are_equal(
            self.client.get_service_details(stype), expected[0])

    def test_get_service_endpoints(self):
        if not self.cached:
            self._authenticate()
        stype, version = 'compute', 'V2'
        self.assertRaises(
            ClientError, self.client.get_service_endpoints, stype)
        expected = [s for s in example['access']['serviceCatalog'] if (
            s['type'] == stype)]
        expected = [e for e in expected[0]['endpoints'] if (
            e['versionId'] == version.lower())]
        self.assert_dicts_are_equal(
            self.client.get_service_endpoints(stype, version), expected[0])

    def test_user_info(self):
        if not self.cached:
            self._authenticate()
        self.assertTrue(set(example['access']['user'].keys()).issubset(
            self.client.user_info().keys()))

    def test_item(self):
        if not self.cached:
            self._authenticate()
        for term, val in example['access']['user'].items():
            self.assertEqual(self.client.term(term, self.token), val)
        self.assertTrue(
            example['access']['user']['email'][0] in self.client.term('email'))

    def test_list_users(self):
        if not self.cached:
            self._authenticate()
        FR.json = example
        self._authenticate()
        r = self.client.list_users()
        self.assertTrue(len(r) == 1)
        self.assertEqual(r[0]['auth_token'], self.token)

    @patch(
        '%s.LoggedAstakosClient.get_usernames' % astakos_pkg,
        return_value={42: 'username42', 43: 'username43'})
    def test_uuids2usernames(self, get_usernames):
        from astakosclient import AstakosClientException
        self.assertRaises(
            AstakosClientException, self.client.uuids2usernames, [42, 43])
        with patch(
                '%s.LoggedAstakosClient.__init__' % astakos_pkg,
                return_value=None) as sac:
            with patch(
                    '%s.LoggedAstakosClient.get_endpoints' % astakos_pkg,
                    return_value=example) as get_endpoints:
                r = self.client.uuids2usernames([42, 43])
                self.assert_dicts_are_equal(
                    r, {42: 'username42', 43: 'username43'})
                self.assertEqual(sac.mock_calls[-1], call(
                    self.token, self.url, logger=getLogger('astakosclient')))
                self.assertEqual(get_endpoints.mock_calls[-1], call())
                self.assertEqual(get_usernames.mock_calls[-1], call([42, 43]))

    @patch(
        '%s.LoggedAstakosClient.get_uuids' % astakos_pkg,
        return_value={'username42': 42, 'username43': 43})
    def test_usernames2uuids(self, get_uuids):
        from astakosclient import AstakosClientException
        self.assertRaises(
            AstakosClientException, self.client.usernames2uuids, ['u1', 'u2'])
        with patch(
                '%s.LoggedAstakosClient.__init__' % astakos_pkg,
                return_value=None) as sac:
            with patch(
                    '%s.LoggedAstakosClient.get_endpoints' % astakos_pkg,
                    return_value=example) as get_endpoints:
                r = self.client.usernames2uuids(['u1', 'u2'])
                self.assert_dicts_are_equal(
                    r, {'username42': 42, 'username43': 43})
                self.assertEqual(sac.mock_calls[-1], call(
                    self.token, self.url, logger=getLogger('astakosclient')))
                self.assertEqual(get_endpoints.mock_calls[-1], call())
                self.assertEqual(get_uuids.mock_calls[-1], call(['u1', 'u2']))


if __name__ == '__main__':
    from sys import argv
    from kamaki.clients.test import runTestCase
    runTestCase(AstakosClient, 'AstakosClient', argv[1:])
