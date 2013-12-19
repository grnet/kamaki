# Copyright 2011-2013 GRNET S.A. All rights reserved.
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

from traceback import print_stack, print_exc
from astakosclient import AstakosClientException

from kamaki.clients import ClientError
from kamaki.cli.errors import CLIError, raiseCLIError, CLISyntaxError
from kamaki.cli import _debug, kloger
from kamaki.cli.utils import format_size

CLOUDNAME = [
    'Note: If you use a named cloud, use its name instead of "default"']


class generic(object):

    @classmethod
    def all(this, func):
        def _raise(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                if _debug:
                    print_stack()
                    print_exc(e)
                if isinstance(e, CLIError) or isinstance(e, ClientError):
                    raiseCLIError(e)
                raiseCLIError(e, details=['%s, -d for debug info' % type(e)])
        return _raise

    @classmethod
    def _connection(this, func):
        def _raise(self, *args, **kwargs):
            try:
                func(self, *args, **kwargs)
            except ClientError as ce:
                ce_msg = ('%s' % ce).lower()
                if ce.status == 401:
                    raiseCLIError(ce, 'Authorization failed', details=[
                        'Make sure a valid token is provided:',
                        '  to check if token is valid: /user authenticate',
                        '  to set token:',
                        '    /config set cloud.default.token <token>',
                        '  to get current token:',
                        '    /config get cloud.default.token'] + CLOUDNAME)
                elif ce.status in range(-12, 200) + [302, 401, 403, 500]:
                    raiseCLIError(ce, importance=3, details=[
                        'Check if service is up'])
                elif ce.status == 404 and 'kamakihttpresponse' in ce_msg:
                    client = getattr(self, 'client', None)
                    if not client:
                        raise
                    url = getattr(client, 'base_url', '<empty>')
                    msg = 'Invalid service URL %s' % url
                    raiseCLIError(ce, msg, details=[
                        'Check if authentication URL is correct',
                        '  check current URL:',
                        '    /config get cloud.default.url',
                        '  set new authentication URL:',
                        '    /config set cloud.default.url'] + CLOUDNAME)
                raise
        return _raise


class user(object):

    _token_details = [
        'To check default token: /config get cloud.default.token',
        'If set/update a token:',
        '*  (permanent):  /config set cloud.default.token <token>',
        '*  (temporary):  re-run with <token> parameter'] + CLOUDNAME

    @classmethod
    def astakosclient(this, func):
        def _raise(self, *args, **kwargs):
            try:
                r = func(self, *args, **kwargs)
            except AstakosClientException as ace:
                raiseCLIError(ace, 'Error in synnefo-AstakosClient')
            return r
        return _raise

    @classmethod
    def load(this, func):
        def _raise(self, *args, **kwargs):
            r = func(self, *args, **kwargs)
            try:
                client = getattr(self, 'client')
            except AttributeError as ae:
                raiseCLIError(ae, 'Client setup failure', importance=3)
            if not getattr(client, 'token', False):
                kloger.warning(
                    'No permanent token (try:'
                    ' kamaki config set cloud.default.token <tkn>)')
            if not getattr(client, 'astakos_base_url', False):
                msg = 'Missing synnefo authentication URL'
                raise CLIError(msg, importance=3, details=[
                    'Check if authentication URL is correct',
                        '  check current URL:',
                        '    /config get cloud.default.url',
                        '  set new auth. URL:',
                        '    /config set cloud.default.url'] + CLOUDNAME)
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
                    raiseCLIError(ce, msg, details=details)
                raise ce
            self._raise = func
        return _raise


class history(object):
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


class cyclades(object):
    about_flavor_id = [
        'How to pick a valid flavor id:',
        '* get a list of flavor ids: /flavor list',
        '* details of flavor: /flavor info <flavor id>']

    about_network_id = [
        'How to pick a valid network id:',
        '* get a list of network ids: /network list',
        '* details of network: /network info <network id>']

    net_types = ('CUSTOM', 'MAC_FILTERED', 'IP_LESS_ROUTED', 'PHYSICAL_VLAN')

    @classmethod
    def connection(this, func):
        return generic._connection(func)

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
                raiseCLIError(ve, msg, importance=1, details=[
                    'Cluster size must be a positive integer'])
            except AssertionError as ae:
                raiseCLIError(
                    ae, 'Invalid cluster size %s' % size, importance=1)
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
                msg = 'Invalid network id %s ' % network_id
                details = 'network id must be a positive integer'
                raiseCLIError(ve, msg, details=details, importance=1)
            except ClientError as ce:
                if network_id and ce.status == 404 and (
                    'network' in ('%s' % ce).lower()
                ):
                    msg = 'No network with id %s found' % network_id,
                    raiseCLIError(ce, msg, details=this.about_network_id)
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
    def network_max(this, func):
        def _raise(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except ClientError as ce:
                if ce.status == 413:
                    msg = 'Cannot create another network',
                    details = [
                        'Maximum number of networks reached',
                        '* to get a list of networks: /network list',
                        '* to delete a network: /network delete <net id>']
                    raiseCLIError(ce, msg, details=details)
                raise
        return _raise

    @classmethod
    def network_in_use(this, func):
        def _raise(self, *args, **kwargs):
            network_id = kwargs.get('network_id', None)
            try:
                return func(self, *args, **kwargs)
            except ClientError as ce:
                if network_id and ce.status in (400, ):
                    msg = 'Network with id %s does not exist' % network_id,
                    raiseCLIError(ce, msg, details=this.about_network_id)
                elif network_id or ce.status in (421, ):
                    msg = 'Network with id %s is in use' % network_id,
                    raiseCLIError(ce, msg, details=[
                        'Disconnect all nics/servers of this network first',
                        '* to get nics: /network info %s' % network_id,
                        '.  (under "attachments" section)',
                        '* to disconnect: /network disconnect <nic id>'])
                raise
        return _raise

    @classmethod
    def flavor_id(this, func):
        def _raise(self, *args, **kwargs):
            flavor_id = kwargs.get('flavor_id', None)
            try:
                flavor_id = int(flavor_id)
                return func(self, *args, **kwargs)
            except ValueError as ve:
                msg = 'Invalid flavor id %s ' % flavor_id,
                details = 'Flavor id must be a positive integer'
                raiseCLIError(ve, msg, details=details, importance=1)
            except ClientError as ce:
                if flavor_id and ce.status == 404 and (
                    'flavor' in ('%s' % ce).lower()
                ):
                        msg = 'No flavor with id %s found' % flavor_id,
                        raiseCLIError(ce, msg, details=this.about_flavor_id)
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
                msg = 'Invalid virtual server id %s' % server_id,
                details = 'Server id must be a positive integer'
                raiseCLIError(ve, msg, details=details, importance=1)
            except ClientError as ce:
                err_msg = ('%s' % ce).lower()
                if (
                    ce.status == 404 and 'server' in err_msg
                ) or (
                    ce.status == 400 and 'not found' in err_msg
                ):
                    msg = 'virtual server with id %s not found' % server_id,
                    raiseCLIError(ce, msg, details=[
                        '* to get ids of all servers: /server list',
                        '* to get server details: /server info <server id>'])
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
                    msg = '%s is an invalid firewall profile term' % profile
                    raiseCLIError(ce, msg, details=[
                        'Try one of the following:',
                        '* DISABLED: Shutdown firewall',
                        '* ENABLED: Firewall in normal mode',
                        '* PROTECTED: Firewall in secure mode'])
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
                    raiseCLIError(ce, err_msg, details=[
                        '* check v. server with id %s: /server info %s' % (
                            server_id,
                            server_id),
                        '* list nics for v. server with id %s:' % server_id,
                        '      /server addr %s' % server_id])
                raise
        return _raise

    @classmethod
    def nic_format(this, func):
        def _raise(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except IndexError as ie:
                nic_id = kwargs.get('nic_id', None)
                msg = 'Invalid format for network interface (nic) %s' % nic_id
                raiseCLIError(ie, msg, importance=1, details=[
                    'nid_id format: nic-<server id>-<nic id>',
                    '* get nics of a network: /network info <net id>',
                    '    (listed the "attachments" section)'])
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
                        raiseCLIError(
                            ce, 'No virtual server metadata with key %s' % key)
                raise
        return _raise


class plankton(object):

    about_image_id = [
        'How to pick a suitable image:',
        '* get a list of image ids: /image list',
        '* details of image: /image meta <image id>']

    @classmethod
    def connection(this, func):
        return generic._connection(func)

    @classmethod
    def id(this, func):
        def _raise(self, *args, **kwargs):
            image_id = kwargs.get('image_id', None)
            try:
                func(self, *args, **kwargs)
            except ClientError as ce:
                if image_id and (
                    ce.status == 404
                    or (
                        ce.status == 400
                        and 'image not found' in ('%s' % ce).lower())
                    or ce.status == 411
                ):
                        msg = 'No image with id %s found' % image_id
                        raiseCLIError(ce, msg, details=this.about_image_id)
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
                    msg = 'No properties with key %s in this image' % key
                    raiseCLIError(ce, msg)
                raise
        return _raise


class pithos(object):
    container_howto = [
        'To specify a container:',
        '  1. --container=<container> (temporary, overrides all)',
        '  2. Use the container:path format (temporary, overrides 3)',
        '  3. Set pithos_container variable (permanent)',
        '     /config set pithos_container <container>',
        'For a list of containers: /file list']

    @classmethod
    def connection(this, func):
        return generic._connection(func)

    @classmethod
    def account(this, func):
        def _raise(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except ClientError as ce:
                if ce.status == 403:
                    raiseCLIError(
                        ce,
                        'Invalid account credentials for this operation',
                        details=['Check user account settings'])
                raise
        return _raise

    @classmethod
    def quota(this, func):
        def _raise(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except ClientError as ce:
                if ce.status == 413:
                    raiseCLIError(ce, 'User quota exceeded', details=[
                        '* get quotas:',
                        '  * upper total limit:      /file quota',
                        '  * container limit:',
                        '    /file containerlimit get <container>',
                        '* set a higher container limit:',
                        '    /file containerlimit set <limit> <container>'])
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
                        msg = 'Is container %s in current account?' % (cont),
                        raiseCLIError(ce, msg, details=this.container_howto)
                raise
        return _raise

    @classmethod
    def local_path_download(this, func):
        def _raise(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except IOError as ioe:
                msg = 'Failed to access a local file',
                raiseCLIError(ioe, msg, importance=2, details=[
                    'Check if the file exists. Also check if the remote',
                    'directories exist. All directories in a remote path',
                    'must exist to succesfully download a container or a',
                    'directory.',
                    'To create a remote directory:',
                    '  [kamaki] file mkdir REMOTE_DIRECTORY_PATH'])
        return _raise

    @classmethod
    def local_path(this, func):
        def _raise(self, *args, **kwargs):
            local_path = kwargs.get('local_path', None)
            try:
                return func(self, *args, **kwargs)
            except IOError as ioe:
                msg = 'Failed to access file %s' % local_path,
                raiseCLIError(ioe, msg, importance=2)
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
                    msg = 'No object %s in container %s' % (
                        self.path,
                        self.container)
                    raiseCLIError(ce, msg, details=this.container_howto)
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
                    msg = 'Invalid file size %s ' % size
                    details = ['size must be a positive integer']
                    raiseCLIError(ve, msg, details=details, importance=1)
            else:
                try:
                    start = int(start)
                except ValueError as e:
                    msg = 'Invalid start value %s in range' % start,
                    details = ['size must be a positive integer'],
                    raiseCLIError(e, msg, details=details, importance=1)
                try:
                    end = int(end)
                except ValueError as e:
                    msg = 'Invalid end value %s in range' % end
                    details = ['size must be a positive integer']
                    raiseCLIError(e, msg, details=details, importance=1)
                if start > end:
                    raiseCLIError(
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
                    raiseCLIError(ce, 'Remote object %s:%s <= %s %s' % (
                        self.container, self.path, format_size(size),
                        ('(%sB)' % size) if size >= 1024 else ''))
                raise
        return _raise
