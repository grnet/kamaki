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

from itertools import product

from kamaki.clients import livetest, ClientError
from kamaki.clients.astakos import AstakosClient


class Astakos(livetest.Generic):
    def setUp(self):
        self.cloud = 'cloud.%s' % self['testcloud']
        self.client = AstakosClient(
            self[self.cloud, 'url'], self[self.cloud, 'token'])
        with open(self['astakos', 'details']) as f:
            self._astakos_details = eval(f.read())

    def test_authenticate(self):
        self._test_0010_authenticate()

    def _test_0010_authenticate(self):
        r = self.client.authenticate()
        self.assert_dicts_are_equal(r, self._astakos_details)

    def test_get_services(self):
        self._test_0020_get_services()

    def _test_0020_get_services(self):
        for args in (tuple(), (self[self.cloud, 'token'],)):
            r = self.client.get_services(*args)
            services = self._astakos_details['access']['serviceCatalog']
            self.assertEqual(len(services), len(r))
            for i, service in enumerate(services):
                self.assert_dicts_are_equal(r[i], service)
        self.assertRaises(ClientError, self.client.get_services, 'wrong_token')

    def test_get_service_details(self):
        self._test_0020_get_service_details()

    def _test_0020_get_service_details(self):
        parsed_services = dict()
        for args in product(
                self._astakos_details['access']['serviceCatalog'],
                ([tuple(), (self[self.cloud, 'token'],)])):
            service = args[0]
            if service['type'] in parsed_services:
                continue
            r = self.client.get_service_details(service['type'], *args[1])
            self.assert_dicts_are_equal(r, service)
            parsed_services[service['type']] = True
        self.assertRaises(
            ClientError, self.client.get_service_details, 'wrong_token')

    def test_get_service_endpoints(self):
        self._test_0020_get_service_endpoints()

    def _test_0020_get_service_endpoints(self):
        parsed_services = dict()
        for args in product(
                self._astakos_details['access']['serviceCatalog'],
                ([], [self[self.cloud, 'token']])):
            service = args[0]
            if service['type'] in parsed_services:
                continue
            for endpoint, with_id in product(
                    service['endpoints'], (True, False)):
                vid = endpoint['versionId'] if (
                    with_id and endpoint['versionId']) else None
                end_args = [service['type'], vid] + args[1]
                r = self.client.get_service_endpoints(*end_args)
                self.assert_dicts_are_equal(r, endpoint)
            parsed_services[service['type']] = True
        self.assertRaises(
            ClientError, self.client.get_service_endpoints, 'wrong_token')

    def test_user_info(self):
        self._test_0020_user_info()

    def _test_0020_user_info(self):
        self.assertTrue(set([
            'roles',
            'name',
            'id']).issubset(self.client.user_info().keys()))

    def test_get(self):
        self._test_0020_get()

    def _test_0020_get(self):
        for term in ('id', 'name'):
            self.assertEqual(
                self.client.term(term, self[self.cloud, 'token']),
                self['astakos', term] or '')

    def test_list_users(self):
        self.client.authenticate()
        self._test_0020_list_users()

    def _test_0020_list_users(self):
        terms = set(['name', 'id'])
        uuid = 0
        for r in self.client.list_users():
            self.assertTrue(terms.issubset(r.keys()))
            self.assertTrue(uuid != r['id'] if uuid else True)
            uuid = r['id']
