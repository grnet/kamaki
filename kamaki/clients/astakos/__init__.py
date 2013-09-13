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

from logging import getLogger

from kamaki.clients import Client, ClientError


class AstakosClient(Client):
    """Synnefo Astakos API client"""

    def __init__(self, base_url, token=None):
        super(AstakosClient, self).__init__(base_url, token)
        self._cache = {}
        self._uuids = {}
        self.log = getLogger('__name__')

    def authenticate(self, token=None):
        """Get authentication information and store it in this client
        As long as the AstakosClient instance is alive, the latest
        authentication information for this token will be available

        :param token: (str) custom token to authenticate

        :returns: (dict) authentication information
        """
        self.token = token or self.token
        body = dict(auth=dict(token=dict(id=self.token)))
        r = self.post('/tokens', json=body).json
        uuid = r['access']['user']['id']
        self._uuids[self.token] = uuid
        self._cache[uuid] = r
        return self._cache[uuid]

    def get_token(self, uuid):
        return self._cache[uuid]['access']['token']['id']

    def get_services(self, token=None):
        """
        :returns: (list) [{name:..., type:..., endpoints:[...]}, ...]
        """
        token_bu = self.token or token
        token = token or self.token
        try:
            r = self._cache[self._uuids[token]]
        except KeyError:
            r = self.authenticate(token)
        finally:
            self.token = token_bu
        return r['access']['serviceCatalog']

    def get_service_details(self, service_type, token=None):
        """
        :param service_type: (str) compute, object-store, image, account, etc.

        :returns: (dict) {name:..., type:..., endpoints:[...]}

        :raises ClientError: (600) if service_type not in service catalog
        """
        services = self.get_services(token)
        for service in services:
            try:
                if service['type'].lower() == service_type.lower():
                    return service
            except KeyError:
                self.log.warning('Misformated service %s' % service)
        raise ClientError(
            'Service type "%s" not in service catalog' % service_type, 600)

    def get_service_endpoints(self, service_type, version=None, token=None):
        """
        :param service_type: (str) can be compute, object-store, etc.

        :param version: (str) the version id of the service

        :returns: (dict) {SNF:uiURL, adminURL, internalURL, publicURL, ...}

        :raises ClientError: (600) if service_type not in service catalog

        :raises ClientError: (601) if #matching endpoints != 1
        """
        service = self.get_service_details(service_type, token)
        matches = []
        for endpoint in service['endpoints']:
            if (not version) or (
                    endpoint['versionId'].lower() == version.lower()):
                matches.append(endpoint)
        if len(matches) != 1:
            raise ClientError(
                '%s endpoints match type %s %s' % (
                    len(matches), service_type,
                    ('and versionId %s' % version) if version else ''),
                601)
        return matches[0]

    def list_users(self):
        """list cached users information"""
        if not self._cache:
            self.authenticate()
        r = []
        for k, v in self._cache.items():
            r.append(dict(v['access']['user']))
            r[-1].update(dict(auth_token=self.get_token(k)))
        return r

    def user_info(self, token=None):
        """Get (cached) user information"""
        token_bu = self.token or token
        token = token or self.token
        try:
            r = self._cache[self._uuids[token]]
        except KeyError:
            r = self.authenticate(token)
        finally:
            self.token = token_bu
        return r['access']['user']

    def term(self, key, token=None):
        """Get (cached) term, from user credentials"""
        return self.user_term(key, token)

    def user_term(self, key, token=None):
        """Get (cached) term, from user credentials"""
        return self.user_info(token).get(key, None)

    def post_user_catalogs(self, uuids=None, displaynames=None):
        """POST base_url/user_catalogs

        :param uuids: (list or tuple) user uuids

        :param displaynames: (list or tuple) usernames (mut. excl. to uuids)

        :returns: (dict) {uuid1: name1, uuid2: name2, ...} or oposite
        """
        account_url = self.get_service_endpoints('account')['publicURL']
        account = AstakosClient(account_url, self.token)
        json_data = dict(uuids=uuids) if (
            uuids) else dict(displaynames=displaynames)
        return account.post('user_catalogs', json=json_data)
