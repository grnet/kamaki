# Copyright 2013-2016 GRNET S.A. All rights reserved.
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
from itertools import product

from kamaki.clients import astakos


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
    """Test synnefo.AstakosClient wrapper"""

    def setUp(self):
        self.url, self.token = 'https://astakos.example.com', 'ast@k0sT0k3n=='
        self.client = astakos.AstakosClient(self.url, self.token)

    @patch('astakosclient.AstakosClient.__init__')
    def test___init__(self, init):
        for args, kwargs in (
                (['some url', 'some token'], {}),
                (['some url', 'some token', 'other', 'params'], {}),
                (['some url', 'some token', 'other params'], (dict(k='v'))),
                (['some url', 'some token'], (dict(k1='v1', k2='v2'))),
                (['some url', ], (dict(k1='v1', k2='v2', token='some token')))
                ):
            astakos.AstakosClient(*args, **kwargs)
            url, token = args.pop(0), kwargs.pop('token', None) or args.pop(0)
            self.assertTrue(
                init.mock_calls[-1], call(token, url, *args, **kwargs))

    @patch('%s.AstakosClient.get_endpoints' % astakos_pkg, return_value='ges')
    @patch('kamaki.clients.astakos.parse_endpoints', return_value=[
        dict(endpoints=['e1', 'e2', 'e3']), 'stuff'])
    def test_get_service_endpoints(self, parse_endpoints, get_endpoints):
        self.assertEqual(
            'e1', self.client.get_service_endpoints('service_type', 'version'))
        assert get_endpoints.call_count == 1
        parse_endpoints.assert_called_once_with(
            'ges', ep_type='service_type', ep_version_id='version')

    @patch(
        '%s.AstakosClient.get_service_endpoints' % astakos_pkg,
        return_value=dict(publicURL='gse', itsnot='important'))
    def test_get_endpoint_url(self, get_service_endpoints):
        self.assertEqual(
            'gse', self.client.get_endpoint_url('serv_type', 'version'))
        get_service_endpoints.assert_called_once_with('serv_type', 'version')

    @patch('%s.AstakosClient.authenticate' % astakos_pkg, return_value=dict(
        access=dict(user='some user', itsnot='important'), isit='nope'))
    def test_user_info(self, authenticate):
        self.assertEqual('some user', self.client.user_info)
        authenticate.assert_called_once_with()

    @patch('%s.AstakosClient.authenticate' % astakos_pkg, return_value=dict(
        access=dict(user=dict(name='user'), itsnot='important'), isit='nope'))
    def test_user_term(self, authenticate):
        self.assertEqual('user', self.client.user_term('name'))
        authenticate.assert_called_once_with()


class LoggedAstakosClient(TestCase):
    """Test LoggedAstakosClient methods"""

    def setUp(self):
        self.url, self.token = 'https://astakos.example.com', 'ast@k0sT0k3n=='
        self.client = astakos.LoggedAstakosClient(self.url, self.token)

    def tearDown(self):
        FR.headers = {}

    @patch('kamaki.clients.recvlog.info', return_value='recvlog info')
    def test__dump_response(self, recvlog_info):
        for headers, status, message, data, LOG_DATA, LOG_TOKEN in product(
                (
                    {'k': 'v'},
                    {'X-Auth-Token': 'xxx'},
                    {'X-Auth-Token': 'xxx', 'k': 'v'}),
                (42, 'status'), ('message', ), ('data', 'My token is xxx'),
                (True, None), (True, None)):
            FR.headers = headers
            self.client.LOG_DATA, self.client.LOG_TOKEN = LOG_DATA, LOG_TOKEN
            if isinstance(status, int):
                self.client._dump_response(FR(), status, message, data)
                mock_calls = list(recvlog_info.mock_calls[-5:])
                size = len(data)
                if LOG_DATA:
                    token = headers.get('X-Auth-Token', '')
                    if token and not LOG_TOKEN:
                        data = data.replace(token, '...')
                    self.assertEqual(mock_calls.pop(), call(data))
                self.assertEqual(mock_calls[-2:], [
                    call('%s %s' % (status, message)),
                    call('data size: %s' % size)])
            else:
                self.assertRaises(
                    TypeError,
                    self.client._dump_response, FR(), status, message, data)

    @patch('%s.AstakosClient._call_astakos' % astakos_pkg, return_value='ret')
    def test__call_astakos(self, super_call):
        self.assertEqual(self.client._call_astakos('x', y='y'), 'ret')
        super_call.assert_called_once_with(self.client, 'x', y='y')


class CachedAstakosClient(TestCase):
    """Test Chached Astakos Client"""
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
        self.client = astakos.CachedAstakosClient(self.url, self.token)

    def tearDown(self):
        FR.json = example

    @patch('kamaki.clients.Client.__init__')
    def test___init__(self, super_init):
        c = astakos.CachedAstakosClient(self.url, self.token)
        super_init.assert_called_once_with(self.url, self.token)
        self.assertEqual(c._astakos, dict())
        self.assertEqual(c._uuids, dict())
        self.assertEqual(c._cache, dict())
        self.assertEqual(c._uuids2usernames, dict())
        self.assertEqual(c._usernames2uuids, dict())

    def test__resolve_token(self):
        for tok, exp in (
                (None, self.token), ('some token', 'some token'),
                (['token 1', 'token 2', 'token 3'], 'token 1')):
            self.assertEqual(exp, self.client._resolve_token(tok))
        self.client.token = None
        self.assertRaises(AssertionError, self.client._resolve_token, None)

    @patch(
        '%s.CachedAstakosClient._resolve_token' % astakos_pkg,
        return_value='rtoken')
    @patch('%s.CachedAstakosClient._validate_token' % astakos_pkg)
    def test_get_client(self, validate, resolve):
        self.client._uuids['rtoken'] = 'ruuid'
        self.client._astakos['ruuid'] = 'rclient'
        self.assertEqual('rclient', self.client.get_client('not important'))
        validate.assert_called_once_with('rtoken')
        resolve.assert_called_once_with('not important')

    @patch(
        '%s.CachedAstakosClient._resolve_token' % astakos_pkg,
        return_value='rtoken')
    @patch('%s.LoggedAstakosClient.__init__' % astakos_pkg, return_value=None)
    @patch(
        '%s.LoggedAstakosClient.authenticate' % astakos_pkg,
        return_value=example)
    def test_authenticate(self, authenticate, super_init, resolve):
        self.assertEqual(example, self.client.authenticate('not important'))
        resolve.assert_called_once_with('not important')
        super_init.assert_called_once_with(
            self.url, 'rtoken', logger=astakos.log)
        authenticate.assert_called_once_with()
        uuid = example['access']['user']['id']
        self.assertEqual(self.client._uuids['rtoken'], uuid)
        self.assertEqual(self.client._cache[uuid], example)
        self.assertTrue(isinstance(
            self.client._astakos[uuid], astakos.LoggedAstakosClient))
        self.assertFalse(self.client._astakos[uuid].LOG_TOKEN)
        self.assertFalse(self.client._astakos[uuid].LOG_DATA)
        self.assertEqual(self.client._uuids2usernames[uuid], dict())
        self.assertEqual(self.client._usernames2uuids[uuid], dict())

        self.client.LOG_TOKEN, self.client.LOG_DATA = 'tkn', 'dt'
        self.client.authenticate()
        self.assertEqual(resolve.mock_calls[-1], call(None))
        self.assertEqual(self.client._astakos[uuid].LOG_TOKEN, 'tkn')
        self.assertEqual(self.client._astakos[uuid].LOG_DATA, 'dt')

    @patch(
        '%s.CachedAstakosClient.get_token' % astakos_pkg, return_value='t1')
    def test_remove_user(self, get_token):
        self.client._uuids = dict(t1='v1', t2='v2')
        self.client._cache = dict(u1='v1', u2='v2')
        self.client._astakos = dict(u1='v1', u2='v2')
        self.client._uuids2usernames = dict(u1='v1', u2='v2')
        self.client._usernames2uuids = dict(u1='v1', u2='v2')
        self.client.remove_user('u1')
        get_token.assert_called_once_with('u1')
        self.assertEqual(self.client._uuids, dict(t2='v2'))
        self.assertEqual(self.client._cache, dict(u2='v2'))
        self.assertEqual(self.client._astakos, dict(u2='v2'))
        self.assertEqual(self.client._uuids2usernames, dict(u2='v2'))
        self.assertEqual(self.client._usernames2uuids, dict(u2='v2'))
        self.assertRaises(KeyError, self.client.remove_user, 'u1')

    def test_get_token(self):
        token = example['access']['token']['id']
        self.client._cache['uuid'] = example
        self.assertEqual(self.client.get_token('uuid'), token)
        self.assertRaises(KeyError, self.client.get_token, 'non uuid')

    @patch('%s.CachedAstakosClient.get_token' % astakos_pkg, return_value='t1')
    @patch('%s.CachedAstakosClient.authenticate' % astakos_pkg)
    def test__validate_token(self, authenticate, get_token):
        self.client._uuids['t1'] = 'u1'
        self.client._validate_token('t1')
        self.assertEqual(get_token.mock_calls[-1], call('u1'))
        self.assertEqual(authenticate.mock_calls, [])
        self.assertTrue('t1' in self.client._uuids)

        self.client._uuids['t2'] = 'u2'
        self.client._validate_token('t2')
        self.assertEqual(get_token.mock_calls[-1], call('u2'))
        self.assertEqual(authenticate.mock_calls[-1], call('t2'))
        self.assertTrue('t2' not in self.client._uuids)

        self.client._validate_token('t3')
        self.assertEqual(authenticate.mock_calls[-1], call('t3'))

    @patch(
        '%s.CachedAstakosClient._resolve_token' % astakos_pkg,
        return_value='tkn')
    @patch('%s.CachedAstakosClient._validate_token' % astakos_pkg)
    def test_get_services(self, validate, resolve):
        self.client._cache['u1'], self.client._uuids['tkn'] = example, 'u1'
        self.assertEqual(
            self.client.get_services('dont care'),
            example['access']['serviceCatalog'])
        resolve.assert_called_once_with('dont care')
        validate.assert_called_once_with('tkn')

    @patch(
        '%s.CachedAstakosClient.get_services' % astakos_pkg,
        return_value=example['access']['serviceCatalog'])
    def test_get_service_details(self, get_services):
        self.assertEqual(
            example['access']['serviceCatalog'][0],
            self.client.get_service_details('compute', 'dont care'))
        get_services.assert_called_once_with('dont care')
        self.assertRaises(
            astakos.AstakosClientError, self.client.get_service_details,
            'non-existing type', 'dont care')

    @patch(
        '%s.CachedAstakosClient.get_service_details' % astakos_pkg,
        return_value=example['access']['serviceCatalog'][0])
    def test_get_service_endpoints(self, get_service_details):
        service = example['access']['serviceCatalog'][0]
        self.assertEqual(
            self.client.get_service_endpoints('not important', 'v1'),
            service['endpoints'][0])
        get_service_details.assert_called_once_with('not important', None)
        self.assertRaises(
            astakos.AstakosClientError, self.client.get_service_endpoints,
            'dont care', 'vX')

    @patch(
        '%s.CachedAstakosClient.get_service_endpoints' % astakos_pkg,
        return_value=dict(publicURL='a URL'))
    def test_get_endpoint_url(self, get_service_endpoints):
        args = ('stype', 'version', 'token')
        self.assertEqual(self.client.get_endpoint_url(*args), 'a URL')
        get_service_endpoints.assert_called_once_with(*args)

    @patch('%s.CachedAstakosClient.authenticate' % astakos_pkg)
    @patch('%s.CachedAstakosClient.get_token' % astakos_pkg, return_value='t1')
    def test_list_users(self, get_token, authenticate):
        self.client._cache = dict()
        self.assertEqual(self.client.list_users(), [])

        e1 = dict(access=dict(
            token=dict(id='t1', otherstuff='...'),
            user=dict(name='user 1', otherstuff2='...')))
        e2 = dict(access=dict(
            token=dict(id='t2', otherstuff='...'),
            user=dict(name='user 2', otherstuff2='...')))
        self.client._cache = dict(u1=e1, u2=e2)
        e1['access']['user']['auth_token'] = 't1'
        e2['access']['user']['auth_token'] = 't1'
        self.assertEqual(
            sorted(self.client.list_users()),
            sorted([e1['access']['user'], e2['access']['user']]))

    @patch(
        '%s.CachedAstakosClient._resolve_token' % astakos_pkg,
        return_value='t1')
    @patch('%s.CachedAstakosClient._validate_token' % astakos_pkg)
    def test_user_info(self, validate, resolve):
        self.client._uuids = dict(t1='u1', t2='u2')
        self.client._cache = dict(u1=example, u2='nothing')
        self.assertEqual(
            self.client.user_info('dont care'), example['access']['user'])
        resolve.assert_called_once_with('dont care')
        validate.assert_called_once_with('t1')

    @patch('%s.CachedAstakosClient.user_info' % astakos_pkg, return_value=dict(
        key='val'))
    def test_user_term(self, user_info):
        self.assertEqual('val', self.client.user_term('key', 'dont care'))
        user_info.assert_called_once_with('dont care')
        self.assertEqual(None, self.client.user_term('not key', 'dont care'))

    @patch('%s.CachedAstakosClient.user_term' % astakos_pkg, return_value='rt')
    def test_term(self, user_term):
        self.assertEqual('rt', self.client.term('key', 'dont care'))
        user_term.assert_called_once_with('key', 'dont care')

    @patch(
        '%s.CachedAstakosClient.uuids2usernames' % astakos_pkg,
        return_value='a user name list')
    @patch(
        '%s.CachedAstakosClient.usernames2uuids' % astakos_pkg,
        return_value='a uuid list')
    def test_post_user_catalogs(self, usernames2uuids, uuids2usernames):
        self.assertEqual('a user name list', self.client.post_user_catalogs(
            uuids=['u1'], token='X'))
        self.assertEqual('a uuid list', self.client.post_user_catalogs(
            displaynames=['n1', 'n2'], token='X'))
        uuids2usernames.assert_called_once_with(['u1'], 'X')
        usernames2uuids.assert_called_once_with(['n1', 'n2'], 'X')

    @patch(
        'astakosclient.AstakosClient.get_usernames',
        return_value=dict(uuid1='name 1', uuid2='name 2'))
    @patch(
        '%s.CachedAstakosClient._resolve_token' % astakos_pkg,
        return_value='t1')
    @patch('%s.CachedAstakosClient._validate_token' % astakos_pkg)
    @patch('astakosclient.AstakosClient.__init__', return_value=None)
    def test_uuids2usernames(
            self, orig_astakos, validate, resolve, get_usernames):
        import astakosclient
        self.client._uuids['t1'] = 'uuid0'
        self.client._astakos['uuid0'] = astakosclient.AstakosClient(
            self.url, self.token)
        self.client._uuids2usernames['uuid0'] = dict(uuid0='name 0')
        exp = dict()
        for i in range(3):
            exp['uuid%s' % i] = 'name %s' % i
        self.assertEqual(exp, self.client.uuids2usernames(
            ['uuid1', 'uuid2'], 'dont care'))
        resolve.assert_called_once_with('dont care')
        validate.assert_called_once_with('t1')
        get_usernames.assert_called_once_with(['uuid1', 'uuid2'])

    @patch(
        'astakosclient.AstakosClient.get_uuids',
        return_value=dict(name1='uuid 1', name2='uuid 2'))
    @patch(
        '%s.CachedAstakosClient._resolve_token' % astakos_pkg,
        return_value='t1')
    @patch('%s.CachedAstakosClient._validate_token' % astakos_pkg)
    @patch('astakosclient.AstakosClient.__init__', return_value=None)
    def test_usernames2uuids(
            self, orig_astakos, validate, resolve, get_uuids):
        import astakosclient
        self.client._uuids['t1'] = 'uuid 0'
        self.client._astakos['uuid 0'] = astakosclient.AstakosClient(
            self.url, self.token)
        self.client._usernames2uuids['uuid 0'] = dict(name0='uuid 0')
        exp = dict()
        for i in range(3):
            exp['name%s' % i] = 'uuid %s' % i
        self.assertEqual(exp, self.client.usernames2uuids(
            ['name1', 'name2'], 'dont care'))
        resolve.assert_called_once_with('dont care')
        validate.assert_called_once_with('t1')
        get_uuids.assert_called_once_with(['name1', 'name2'])


if __name__ == '__main__':
    from sys import argv
    from kamaki.clients.test import runTestCase
    not_found = True
    if not argv[1:] or argv[1] == 'AstakosClient':
        not_found = False
        runTestCase(AstakosClient, 'Kamaki Astakos Client', argv[2:])
    if not argv[1:] or argv[1] == 'LoggedAstakosClient':
        not_found = False
        runTestCase(LoggedAstakosClient, 'Logged Astakos Client', argv[2:])
    if not argv[1:] or argv[1] == 'CachedAstakosClient':
        not_found = False
        runTestCase(CachedAstakosClient, 'Cached Astakos Client', argv[2:])
    if not_found:
        print('TestCase %s not found' % argv[1])
