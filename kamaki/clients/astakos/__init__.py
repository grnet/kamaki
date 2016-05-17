# Copyright 2012-2016 GRNET S.A. All rights reserved.
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
from functools import wraps
import inspect
import ssl

from astakosclient import AstakosClientException, parse_endpoints
import astakosclient

from kamaki.clients import (
    Client, Logged, ClientError, KamakiSSLError, RequestManager, recvlog)

from kamaki.clients.utils import https


log = getLogger(__name__)


class AstakosClientError(ClientError):
    pass


def mk_astakosclienterror(sace):
    """Make an AstakosClientError from an AstakosClientException"""
    return AstakosClientError(
        message=sace.message, status=sace.status, details=sace.details)


def _log_astakosclient_request(cls):
    """
    :param cls: An AstakosClient instance
    """
    try:
        log_request = getattr(cls, 'log_request', None)
        if log_request:
            req = RequestManager(
                method=log_request['method'],
                url='%s://%s' % (cls.scheme, cls.astakos_base_url),
                path=log_request['path'],
                data=log_request.get('body', None),
                headers=log_request.get('headers', dict()))
            req.LOG_TOKEN, req.LOG_DATA = cls.LOG_TOKEN, cls.LOG_DATA
            req.dump_log()
            log_response = getattr(cls, 'log_response', None)
            if log_response:
                cls._dump_response(
                    req,
                    status=log_response['status'],
                    message=log_response['message'],
                    data=log_response.get('data', ''))
    except Exception:
        recvlog.debug('Kamaki failed to log an AstakosClient call')


def _astakos_error(func):
    @wraps(func)
    def wrap(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except AstakosClientException as sace:
            _log_astakosclient_request(self)
            if isinstance(getattr(sace, 'errobject', None), ssl.SSLError):
                raise KamakiSSLError('SSL Connection error (%s)' % sace)
            raise mk_astakosclienterror(sace)
    return wrap


#  Patch AstakosClient to support SSLAuthentication
astakosclient.utils.PooledHTTPConnection = https.PooledHTTPConnection
astakosclient.utils.HTTPSConnection = https.HTTPSClientAuthConnection
OriginalAstakosClient = astakosclient.AstakosClient


class AstakosClient(OriginalAstakosClient):
    """Wrap Original AstakosClient to ensure compatibility in kamaki clients"""

    @_astakos_error
    def __init__(self, *args, **kwargs):
        if args:
            args = list(args)
            url = args.pop(0)
            token = args.pop(0) if args else kwargs.pop('token', None)
            args = tuple([token, url] + args)
        else:
            kwargs.setdefault(
                'auth_url', kwargs.get('endpoint_url', kwargs['base_url']))

        # If no CA certificates are set, get the defaults from kamaki.defaults
        if https.HTTPSClientAuthConnection.ca_file is None:
            try:
                from kamaki import defaults
                https.HTTPSClientAuthConnection.ca_file = getattr(
                    defaults, 'CACERTS_DEFAULT_PATH', None)
            except ImportError as ie:
                log.debug('ImportError while loading default certs: %s' % ie)

        super(AstakosClient, self).__init__(*args, **kwargs)

    def get_service_endpoints(self, service_type, version=None):
        services = parse_endpoints(
            self.get_endpoints(), ep_type=service_type, ep_version_id=version)
        return services[0]['endpoints'][0] if services else {}

    def get_endpoint_url(self, service_type, version=None):
        return self.get_service_endpoints(service_type, version)['publicURL']

    @property
    def user_info(self):
        return self.authenticate()['access']['user']

    def user_term(self, term):
        return self.user_info[term]


#  Wrap AstakosClient public methods to raise AstakosClientError
for m in inspect.getmembers(AstakosClient):
    if hasattr(m[1], '__call__') and not ('%s' % m[0]).startswith('_'):
        setattr(AstakosClient, m[0], _astakos_error(m[1]))


class LoggedAstakosClient(AstakosClient, Logged):
    """An AstakosClient wrapper with modified logging

    Logs are adjusted to appear similar to the ones of kamaki clients.
    No other changes are made to the parent class.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('logger', log)
        AstakosClient.__init__(self, *args, **kwargs)

    def _dump_response(self, request, status, message, data):
        recvlog.info('%d %s' % (status, message))
        recvlog.info('data size: %s' % len(data))
        if not self.LOG_TOKEN:
            token = request.headers.get('X-Auth-Token', '')
            if self.LOG_DATA:
                data = data.replace(token, '...') if token else data
        if self.LOG_DATA:
            recvlog.info(data)

    def _call_astakos(self, *args, **kwargs):
        r = AstakosClient._call_astakos(self, *args, **kwargs)
        _log_astakosclient_request(self)
        return r


class CachedAstakosClient(Client):
    """Synnefo Astakos cached client wraper"""
    service_type = 'identity'

    @_astakos_error
    def __init__(self, endpoint_url, token=None):
        super(CachedAstakosClient, self).__init__(endpoint_url, token)
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
        token = token or self.token
        assert token, 'No token provided'
        return token[0] if (
            isinstance(token, list) or isinstance(token, tuple)) else token

    def get_client(self, token=None):
        """Get the Synnefo AstakosClient instance used by client"""
        token = self._resolve_token(token)
        self._validate_token(token)
        return self._astakos[self._uuids[token]]

    @_astakos_error
    def authenticate(self, token=None):
        """Get authentication information and store it in this client
        As long as the CachedAstakosClient instance is alive, the latest
        authentication information for this token will be available

        :param token: (str) custom token to authenticate
        """
        token = self._resolve_token(token)
        astakos = LoggedAstakosClient(self.endpoint_url, token, logger=log)
        astakos.LOG_TOKEN = getattr(self, 'LOG_TOKEN', False)
        astakos.LOG_DATA = getattr(self, 'LOG_DATA', False)
        r = astakos.authenticate()
        uuid = r['access']['user']['id']
        self._uuids[token] = uuid
        self._cache[uuid] = r
        self._astakos[uuid] = astakos
        self._uuids2usernames[uuid] = dict()
        self._usernames2uuids[uuid] = dict()
        return self._cache[uuid]

    def remove_user(self, uuid):
        self._uuids.pop(self.get_token(uuid))
        self._cache.pop(uuid)
        self._astakos.pop(uuid)
        self._uuids2usernames.pop(uuid)
        self._usernames2uuids.pop(uuid)

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

        :raises AstakosClientError: if service_type not in service catalog
        """
        services = self.get_services(token)
        for service in services:
            try:
                if service['type'].lower() == service_type.lower():
                    return service
            except KeyError:
                self.log.warning('Misformated service %s' % service)
        raise AstakosClientError(
            'Service type "%s" not in service catalog' % service_type)

    def get_service_endpoints(self, service_type, version=None, token=None):
        """
        :param service_type: (str) can be compute, object-store, etc.

        :param version: (str) the version id of the service

        :returns: (dict) {SNF:uiURL, adminURL, internalURL, publicURL, ...}

        :raises AstakosClientError: if service_type not in service catalog, or
            if #matching endpoints != 1
        """
        service = self.get_service_details(service_type, token)
        matches = []
        for endpoint in service['endpoints']:
            if (not version) or (
                    endpoint['versionId'].lower() == version.lower()):
                matches.append(endpoint)
        if len(matches) != 1:
            raise AstakosClientError(
                '%s endpoints match type %s %s' % (
                    len(matches), service_type,
                    ('and versionId %s' % version) if version else ''))
        return matches[0]

    def get_endpoint_url(self, service_type, version=None, token=None):
        r = self.get_service_endpoints(service_type, version, token)
        return r['publicURL']

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
        """POST endpoint_url/user_catalogs

        :param uuids: (list or tuple) user uuids

        :param displaynames: (list or tuple) usernames (mut. excl. to uuids)

        :returns: (dict) {uuid1: name1, uuid2: name2, ...} or oposite
        """
        return self.uuids2usernames(uuids, token) if (
            uuids) else self.usernames2uuids(displaynames, token)

    @_astakos_error
    def uuids2usernames(self, uuids, token=None):
        token = self._resolve_token(token)
        self._validate_token(token)
        uuid = self._uuids[token]
        astakos = self._astakos[uuid]
        if set(uuids or []).difference(self._uuids2usernames[uuid]):
            self._uuids2usernames[uuid].update(astakos.get_usernames(uuids))
        return self._uuids2usernames[uuid]

    @_astakos_error
    def usernames2uuids(self, usernames, token=None):
        token = self._resolve_token(token)
        self._validate_token(token)
        uuid = self._uuids[token]
        astakos = self._astakos[uuid]
        if set(usernames or []).difference(self._usernames2uuids[uuid]):
            self._usernames2uuids[uuid].update(astakos.get_uuids(usernames))
        return self._usernames2uuids[uuid]
