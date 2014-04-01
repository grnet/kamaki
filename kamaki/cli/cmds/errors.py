# Copyright 2011-2014 GRNET S.A. All rights reserved.
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
# or implied, of GRNET S.A.command

from traceback import format_exc, format_stack
from logging import getLogger
from astakosclient import AstakosClientException

from kamaki.clients import ClientError
from kamaki.cli.errors import CLIError, CLISyntaxError
from kamaki.cli.utils import format_size

log = getLogger(__name__)

CLOUDNAME = ['Note: Set a cloud and use its name instead of "default"']


class Generic(object):

    @classmethod
    def all(this, func):
        def _raise(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                log.debug('Error stack:\n%s' % ''.join(format_stack()))
                log.debug(format_exc(e))
                if isinstance(e, CLIError):
                    raise e
                elif isinstance(e, ClientError):
                    raise CLIError(
                        u'(%s) %s' % (getattr(e, 'status', 'no status'), e),
                        details=getattr(e, 'details', []),
                        importance=1 if (
                            e.status < 200) else 2 if (
                            e.status < 300) else 3 if (
                            e.status < 400) else 4)
                raise CLIError(
                    '%s' % e, details=['%s, -d for debug info' % type(e)])
        return _raise

    @classmethod
    def _connection(this, func):
        def _raise(self, *args, **kwargs):
            try:
                func(self, *args, **kwargs)
            except ClientError as ce:
                ce_msg = ('%s' % ce).lower()
                if ce.status == 401:
                    raise CLIError('Authorization failed', details=[
                        'Make sure a valid token is provided:',
                        '  # to check if token is valid',
                        '  $ kamaki user authenticate',
                        '  # to set token:',
                        '  $ kamaki config set cloud.default.token <token>',
                        '  # to get current token:',
                        '  $ kamaki config get cloud.default.token',
                        '%s' % ce,
                    ] + CLOUDNAME)
                elif ce.status in range(-12, 200) + [302, 401, 500]:
                    raise CLIError('%s' % ce, importance=3)
                elif ce.status == 404 and 'kamakihttpresponse' in ce_msg:
                    client = getattr(self, 'client', None)
                    if not client:
                        raise
                    url = getattr(client, 'base_url', '<empty>')
                    raise CLIError('Invalid service URL %s' % url, details=[
                        '%s' % ce,
                        'Check if authentication URL is correct',
                        '  # check current URL',
                        '  $ kamaki config get cloud.default.url',
                        '  # set new authentication URL',
                        '  $ kamaki config set cloud.default.url'] + CLOUDNAME)
                raise
        return _raise


class Astakos(object):

    _token_details = [
        'To check default token: /config get cloud.default.token',
        'If set/update a token:',
        '  #  (permanent)',
        '  $ kamaki config set cloud.default.token <token>'] + CLOUDNAME

    @classmethod
    def astakosclient(this, func):
        def _raise(self, *args, **kwargs):
            try:
                r = func(self, *args, **kwargs)
            except AstakosClientException as ace:
                raise CLIError(
                    'Error in AstakosClient', details=['%s' % ace, ])
            return r
        return _raise

    @classmethod
    def load(this, func):
        def _raise(self, *args, **kwargs):
            r = func(self, *args, **kwargs)
            try:
                client = getattr(self, 'client')
            except AttributeError as ae:
                raise CLIError('Client setup failure', importance=3, details=[
                    '%s' % ae])
            if not getattr(client, 'token', False):
                log.warning(
                    'No permanent token (try:'
                    ' kamaki config set cloud.default.token <tkn>)')
            if not getattr(client, 'astakos_base_url', False):
                msg = 'Missing synnefo authentication URL'
                raise CLIError(msg, importance=3, details=[
                    'Check if authentication URL is correct',
                    '  # check current URL:',
                    '  $ kamaki config get cloud.default.url',
                    '  # set new auth. URL:',
                    '  $ kamaki config set cloud.default.url'] + CLOUDNAME)
            return r
        return _raise

    @classmethod
    def authenticate(this, func):
        def _raise(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except (ClientError, AstakosClientException) as ce:
                if ce.status == 401:
                    token = kwargs.get('custom_token', 0) or self.client.token
                    msg = ('Authorization failed for token %s' % token) if (
                        token) else 'No token provided',
                    details = [] if token else this._token_details
                    raise CLIError(msg, details=details + ['%s' % ce, ])
                raise ce
            self._raise = func
        return _raise


class History(object):
    @classmethod
    def init(this, func):
        def _raise(self, *args, **kwargs):
            r = func(self, *args, **kwargs)
            if not hasattr(self, 'history'):
                raise CLIError('Failed to load history', importance=2)
            return r
        return _raise

    @classmethod
    def _get_cmd_ids(this, func):
        def _raise(self, cmd_ids, *args, **kwargs):
            if not cmd_ids:
                raise CLISyntaxError(
                    'Usage: <id1|id1-id2> [id3|id3-id4] ...',
                    details=self.__doc__.split('\n'))
            return func(self, cmd_ids, *args, **kwargs)
        return _raise


class Cyclades(object):
    about_flavor_id = [
        'How to pick a valid flavor id:',
        '  # get a list of flavor ids',
        '  $ kamaki flavor list',
        '  # details of flavor',
        '  $ kamaki flavor info <flavor id>',
        '',
    ]

    about_network_id = [
        'How to pick a valid network id:',
        '  # get a list of network ids',
        '  $ kamaki network list',
        '  # details of network',
        '  $ kamaki network info <network id>',
        '',
    ]

    net_types = ('CUSTOM', 'MAC_FILTERED', 'IP_LESS_ROUTED', 'PHYSICAL_VLAN')

    @classmethod
    def connection(this, func):
        return Generic._connection(func)

    @classmethod
    def date(this, func):
        def _raise(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except ClientError as ce:
                if ce.status == 400 and 'changes-since' in ('%s' % ce):
                    raise CLIError(
                        'Incorrect date format for --since',
                        details=['Accepted date format: d/m/y'])
                raise
        return _raise

    @classmethod
    def cluster_size(this, func):
        def _raise(self, *args, **kwargs):
            size = kwargs.get('size', None)
            try:
                size = int(size)
                assert size > 0, 'Cluster size must be a positive integer'
                return func(self, *args, **kwargs)
            except ValueError as ve:
                msg = 'Invalid cluster size value %s' % size
                raise CLIError(msg, importance=1, details=[
                    'Cluster size must be a positive integer', '%s' % ve])
            except AssertionError as ae:
                raise CLIError(
                    'Invalid cluster size %s' % size, importance=1, details=[
                    '%s' % ae])
            except ClientError:
                raise
        return _raise

    @classmethod
    def network_id(this, func):
        def _raise(self, *args, **kwargs):
            network_id = kwargs.get('network_id', None)
            try:
                network_id = int(network_id)
                return func(self, *args, **kwargs)
            except ValueError as ve:
                raise CLIError(
                    'Invalid network id %s ' % network_id,
                    details=[
                        'network id must be a positive integer', '%s' % ve],
                    importance=1)
            except ClientError as ce:
                if network_id and ce.status == 404 and (
                    'network' in ('%s' % ce).lower()
                ):
                    raise CLIError(
                        'No network with id %s found' % network_id,
                        details=this.about_network_id + ['%s' % ce])
                raise
        return _raise

    @classmethod
    def network_type(this, func):
        def _raise(self, *args, **kwargs):
            network_type = kwargs.get('network_type', None)
            msg = 'Invalid network type %s.\nValid types: %s' % (
                network_type, ' '.join(this.net_types))
            assert network_type in this.net_types, msg
            return func(self, *args, **kwargs)
        return _raise

    @classmethod
    def flavor_id(this, func):
        def _raise(self, *args, **kwargs):
            flavor_id = kwargs.get('flavor_id', None)
            try:
                flavor_id = int(flavor_id)
                return func(self, *args, **kwargs)
            except ValueError as ve:
                raise CLIError(
                    'Invalid flavor id %s ' % flavor_id,
                    details=[
                        'Flavor id must be a positive integer', '%s' % ve],
                    importance=1)
            except ClientError as ce:
                if flavor_id and ce.status == 404 and (
                    'flavor' in ('%s' % ce).lower()
                ):
                    raise CLIError(
                        'No flavor with id %s found' % flavor_id,
                        details=this.about_flavor_id + ['%s' % ce, ])
                raise
        return _raise

    @classmethod
    def server_id(this, func):
        def _raise(self, *args, **kwargs):
            server_id = kwargs.get('server_id', None)
            try:
                server_id = int(server_id)
                return func(self, *args, **kwargs)
            except ValueError as ve:
                raise CLIError(
                    'Invalid virtual server id %s' % server_id,
                    details=[
                        'Server id must be a positive integer', '%s' % ve],
                    importance=1)
            except ClientError as ce:
                err_msg = ('%s' % ce).lower()
                if (
                    ce.status == 404 and 'server' in err_msg
                ) or (
                    ce.status == 400 and 'not found' in err_msg
                ):
                    raise CLIError(
                        'virtual server with id %s not found' % server_id,
                        details=[
                        '# to get ids of all servers',
                        '$ kamaki server list',
                        '# to get server details',
                        '$ kamaki server info <server id>',
                        '%s' % ce])
                raise
        return _raise

    @classmethod
    def firewall(this, func):
        def _raise(self, *args, **kwargs):
            profile = kwargs.get('profile', None)
            try:
                return func(self, *args, **kwargs)
            except ClientError as ce:
                if ce.status == 400 and profile and (
                    'firewall' in ('%s' % ce).lower()
                ):
                    raise CLIError(
                        '%s is an invalid firewall profile term' % profile,
                        details=[
                        'Try one of the following:',
                        '* DISABLED: Shutdown firewall',
                        '* ENABLED: Firewall in normal mode',
                        '* PROTECTED: Firewall in secure mode',
                        '%s' % ce])
                raise
        return _raise

    @classmethod
    def nic_id(this, func):
        def _raise(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except ClientError as ce:
                nic_id = kwargs.get('nic_id', None)
                if nic_id and ce.status == 404 and (
                    'network interface' in ('%s' % ce).lower()
                ):
                    server_id = kwargs.get('server_id', '<no server>')
                    err_msg = 'No nic %s on virtual server with id %s' % (
                        nic_id,
                        server_id)
                    raise CLIError(err_msg, details=[
                        '* check v. server with id %s: /server info %s' % (
                            server_id,
                            server_id),
                        '* list nics for v. server with id %s:' % server_id,
                        '      /server addr %s' % server_id,
                        '%s' % ce])
                raise
        return _raise

    @classmethod
    def metadata(this, func):
        def _raise(self, *args, **kwargs):
            key = kwargs.get('key', None)
            try:
                func(self, *args, **kwargs)
            except ClientError as ce:
                if key and ce.status == 404 and (
                    'metadata' in ('%s' % ce).lower()
                ):
                        raise CLIError(
                            'No virtual server metadata with key %s' % key,
                            details=['%s' % ce, ])
                raise
        return _raise


class Image(object):
    about_image_id = [
        'How to pick a suitable image:',
        '  # get a list of image ids',
        '  $ kamaki image list',
        '  # details of an image',
        '  $ kamaki image info <image id>',
        '',
    ]

    @classmethod
    def connection(this, func):
        return Generic._connection(func)

    @classmethod
    def id(this, func):
        def _raise(self, *args, **kwargs):
            image_id = kwargs.get('image_id', None)
            try:
                func(self, *args, **kwargs)
            except ClientError as ce:
                if image_id or (ce.status in (404, 400) and (
                        'image not found' in ('%s' % ce).lower())):
                    raise CLIError(
                        'No image with id %s found' % image_id,
                        details=this.about_image_id + ['%s' % ce])
                raise
        return _raise

    @classmethod
    def metadata(this, func):
        def _raise(self, *args, **kwargs):
            key = kwargs.get('key', None)
            try:
                return func(self, *args, **kwargs)
            except ClientError as ce:
                ce_msg = ('%s' % ce).lower()
                if ce.status == 404 or (
                        ce.status == 400 and 'metadata' in ce_msg):
                    raise CLIError(
                        'No properties with key %s in this image' % key,
                        details=['%s' % ce, ])
                raise
        return _raise


class Pithos(object):
    container_howto = [
        'Use a / to refer to a container (default: /pithos) e.g.,',
        '  # list the contents of container "images"',
        '  $ kamaki file list /images',
        '  # get information on file "my.img" in container "images"',
        '  $ kamaki file info /images/my.img',
        '',
        'To get a list of containers:',
        '  $ kamaki container list',
        '',
    ]

    @classmethod
    def connection(this, func):
        return Generic._connection(func)

    @classmethod
    def account(this, func):
        def _raise(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except ClientError as ce:
                if ce.status == 403:
                    raise CLIError(
                        'Invalid account credentials for this operation',
                        details=['Check user account settings', '%s' % ce])
                raise
        return _raise

    @classmethod
    def quota(this, func):
        def _raise(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except ClientError as ce:
                if ce.status == 413:
                    raise CLIError('User quota exceeded', details=[
                        '* get quotas:',
                        '  * upper total limit:      /file quota',
                        '  * container limit:',
                        '    /file containerlimit get <container>',
                        '* set a higher container limit:',
                        '    /file containerlimit set <limit> <container>',
                        '%s' % ce])
                raise
        return _raise

    @classmethod
    def container(this, func):
        def _raise(self, *args, **kwargs):
            dst_cont = kwargs.get('dst_cont', None)
            try:
                return func(self, *args, **kwargs)
            except ClientError as ce:
                if ce.status == 404 and 'container' in ('%s' % ce).lower():
                        cont = ('%s or %s' % (
                            self.container,
                            dst_cont)) if dst_cont else self.container
                        raise CLIError(
                            'Container "%s" does not exist' % cont,
                            details=this.container_howto + ['%s' % ce])
                raise
        return _raise

    @classmethod
    def local_path_download(this, func):
        def _raise(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except IOError as ioe:
                raise CLIError(
                    'Failed to access a local file', importance=2, details=[
                    'Check if the file exists. Also check if the remote',
                    'directories exist. All directories in a remote path',
                    'must exist to succesfully download a container or a',
                    'directory.',
                    'To create a remote directory:',
                    '  [kamaki] file mkdir REMOTE_DIRECTORY_PATH',
                    '%s' % ioe])
        return _raise

    @classmethod
    def local_path(this, func):
        def _raise(self, *args, **kwargs):
            local_path = kwargs.get('local_path', None)
            try:
                return func(self, *args, **kwargs)
            except IOError as ioe:
                raise CLIError(
                    'Failed to access file %s' % local_path,
                    details=['%s' % ioe, ], importance=2)
        return _raise

    @classmethod
    def object_path(this, func):
        def _raise(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except ClientError as ce:
                err_msg = ('%s' % ce).lower()
                if (
                    ce.status == 404 or ce.status == 500
                ) and 'object' in err_msg and 'not' in err_msg:
                    raise CLIError(
                        'No object %s in container %s' % (
                            self.path, self.container),
                        details=this.container_howto + ['%s' % ce, ])
                raise
        return _raise

    @classmethod
    def object_size(this, func):
        def _raise(self, *args, **kwargs):
            size = kwargs.get('size', None)
            start = kwargs.get('start', 0)
            end = kwargs.get('end', 0)
            if size:
                try:
                    size = int(size)
                except ValueError as ve:
                    raise CLIError(
                        'Invalid file size %s ' % size,
                        details=['size must be a positive integer', '%s' % ve],
                        importance=1)
            else:
                try:
                    start = int(start)
                except ValueError as e:
                    raise CLIError(
                        'Invalid start value %s in range' % start,
                        details=['size must be a positive integer', '%s' % e],
                        importance=1)
                try:
                    end = int(end)
                except ValueError as e:
                    raise CLIError(
                        'Invalid end value %s in range' % end,
                        details=['size must be a positive integer', '%s' % e],
                        importance=1)
                if start > end:
                    raise CLIError(
                        'Invalid range %s-%s' % (start, end),
                        details=['size must be a positive integer'],
                        importance=1)
                size = end - start
            try:
                return func(self, *args, **kwargs)
            except ClientError as ce:
                err_msg = ('%s' % ce).lower()
                expected = 'object length is smaller than range length'
                if size and (
                    ce.status == 416 or (
                        ce.status == 400 and expected in err_msg)):
                    raise CLIError(
                        'Remote object %s:%s <= %s %s' % (
                            self.container, self.path, format_size(size),
                            ('(%sB)' % size) if size >= 1024 else ''),
                        details=['%s' % ce])
                raise
        return _raise
