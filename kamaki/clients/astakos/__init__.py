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
from astakosclient import AstakosClient as SynnefoAstakosClient

from kamaki.clients import Client, ClientError


class AstakosClient(Client):
    """Synnefo Astakos cached client wraper"""

    def __init__(self, base_url, token=None):
        super(AstakosClient, self).__init__(base_url, token)
        self._astakos = dict()
        self._uuids = dict()
        self._cache = dict()
        self._uuids2usernames = dict()
        self._usernames2uuids = dict()

    def _resolve_token(self, token):
        """
        :returns: (str) a single token

        :raises AssertionError: if no token exists (either param or member)
        """
        token = token or self.token or self.tokenlist[0]
        assert token, 'No token provided'
        return token[0] if (
            isinstance(token, list) or isinstance(token, tuple)) else token

    def authenticate(self, token=None):
        """Get authentication information and store it in this client
        As long as the AstakosClient instance is alive, the latest
        authentication information for this token will be available

        :param token: (str) custom token to authenticate
        """
        token = self._resolve_token(token)
        astakos = SynnefoAstakosClient(
            token, self.base_url, logger=getLogger('_my_.astakosclient'))
        r = astakos.get_endpoints()
        uuid = r['access']['user']['id']
        self._uuids[token] = uuid
        self._cache[uuid] = r
        self._astakos[uuid] = astakos
        self._uuids2usernames[token] = dict()
        self._usernames2uuids[token] = dict()

    def get_token(self, uuid):
        return self._cache[uuid]['access']['token']['id']

    def _validate_token(self, token):
        if (token not in self._uuids) or (
                self.get_token(self._uuids[token]) != token):
            self._uuids.pop(token, None)
            self.authenticate(token)

    def get_services(self, token=None):
        """
        :returns: (list) [{name:..., type:..., endpoints:[...]}, ...]
        """
        token = self._resolve_token(token)
        self._validate_token(token)
        r = self._cache[self._uuids[token]]
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
        token = self._resolve_token(token)
        self._validate_token(token)
        r = self._cache[self._uuids[token]]
        return r['access']['user']

    def term(self, key, token=None):
        """Get (cached) term, from user credentials"""
        return self.user_term(key, token)

    def user_term(self, key, token=None):
        """Get (cached) term, from user credentials"""
        return self.user_info(token).get(key, None)

    def post_user_catalogs(self, uuids=None, displaynames=None, token=None):
        """POST base_url/user_catalogs

        :param uuids: (list or tuple) user uuids

        :param displaynames: (list or tuple) usernames (mut. excl. to uuids)

        :returns: (dict) {uuid1: name1, uuid2: name2, ...} or oposite
        """
        return self.uuids2usernames(uuids, token) if (
            uuids) else self.usernnames2uuids(displaynames, token)

    def uuids2usernames(self, uuids, token=None):
        token = self._resolve_token(token)
        self._validate_token(token)
        astakos = self._astakos[self._uuids[token]]
        if set(uuids).difference(self._uuids2usernames[token]):
            self._uuids2usernames[token].update(astakos.get_usernames(uuids))
        return self._uuids2usernames[token]

    def usernames2uuids(self, usernames, token=None):
        token = self._resolve_token(token)
        self._validate_token(token)
        astakos = self._astakos[self._uuids[token]]
        if set(usernames).difference(self._usernames2uuids[token]):
            self._usernames2uuids[token].update(astakos.get_uuids(usernames))
        return self._usernames2uuids
