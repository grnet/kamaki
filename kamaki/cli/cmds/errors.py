# Copyright 2011-2015 GRNET S.A. All rights reserved.
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

from kamaki.clients import ClientError
from kamaki.cli import DEF_CLOUD_ENV
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
                        '(%s) %s' % (getattr(e, 'status', 'no status'), e),
                        details=getattr(e, 'details', []),
                        importance=1 if (
                            e.status < 200) else 2 if (
                            e.status < 300) else 3 if (
                            e.status < 400) else 4)
                raise CLIError(
                    '%s' % e, details=['%s, -d for debug info' % type(e)])
        _raise.__name__ = func.__name__
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
                        'To check if token is valid',
                        '  kamaki user authenticate',
                        'To set token:',
                        '  kamaki config set cloud.default.token <token>',
                        'To get current token:',
                        '  kamaki config get cloud.default.token',
                        '%s %s' % (getattr(ce, 'status', ''), ce)] + CLOUDNAME)
                elif ce.status in range(-12, 200) + [302, 401, 500]:
                    raise CLIError(
                        '%s %s' % (getattr(ce, 'status', ''), ce),
                        importance=3)
                elif ce.status == 404 and 'kamakihttpresponse' in ce_msg:
                    client = getattr(self, 'client', None)
                    if not client:
                        raise
                    url = getattr(client, 'endpoint_url', '<empty>')
                    raise CLIError('Invalid service URL %s' % url, details=[
                        'Check if authentication URL is correct',
                        'To check current URL',
                        '  kamaki config get cloud.default.url',
                        'To set new authentication URL',
                        '  kamaki config set cloud.default.url',
                        '%s %s' % (getattr(ce, 'status', ''), ce)] + CLOUDNAME)
                raise
        _raise.__name__ = func.__name__
        return _raise


class Astakos(object):

    _token_details = [
        'To check a token:',
        '  kamaki config get cloud.CLOUD.token',
        'To see all configured clouds:',
        '  kamaki config get cloud'
        'To set/get the default cloud:',
        '  kamaki config get default_cloud',
        '  kamaki config set default_cloud CLOUD',
        '  or get/set the %s enviroment variable' % DEF_CLOUD_ENV,
        'If (re)set a token:',
        '  #  (permanent)',
        '  $ kamaki config set cloud.CLOUD.token <token>']

    @classmethod
    def astakosclient(this, func):
        def _raise(self, *args, **kwargs):
            return func(self, *args, **kwargs)
        _raise.__name__ = func.__name__
        return _raise

    @classmethod
    def project_id(this, func):
        def _raise(self, *args, **kwargs):
            project_id = kwargs.get('project_id', None)
            try:
                return func(self, *args, **kwargs)
            except ClientError as ce:
                if project_id and ce.status in (400, 404):
                    raise CLIError(
                        'No project with ID %s' % project_id,
                        importance=2, details=[
                            'To see all projects', '  kamaki project list',
                            '%s %s' % (getattr(ce, 'status', ''), ce)])
                elif project_id and ce.status in (403, ):
                    raise CLIError(
                        'No access to project %s' % project_id,
                        importance=3, details=[
                            'To see all projects', '  kamaki project list',
                            'To see  memberships',
                            '  kamaki membership list',
                            '%s %s' % (getattr(ce, 'status', ''), ce)])
                raise
        _raise.__name__ = func.__name__
        return _raise

    @classmethod
    def membership_id(this, func):
        def _raise(self, *args, **kwargs):
            membership_id = kwargs.get('membership_id', None)
            try:
                return func(self, *args, **kwargs)
            except ClientError as ce:
                if membership_id and ce.status in (400, 404):
                    raise CLIError(
                        'No membership with ID %s' % membership_id,
                        importance=2, details=[
                            'To list all memberships',
                            '  kamaki membership list',
                            '%s %s' % (getattr(ce, 'status', ''), ce)])
                elif membership_id and ce.status in (403, ):
                    raise CLIError(
                        'No access to membership %s' % membership_id,
                        importance=3, details=[
                            'To see all memberships',
                            '  kamaki membership list',
                            '%s %s' % (getattr(ce, 'status', ''), ce)])
        _raise.__name__ = func.__name__
        return _raise


class History(object):
    @classmethod
    def init(this, func):
        def _raise(self, *args, **kwargs):
            r = func(self, *args, **kwargs)
            if not hasattr(self, 'history'):
                raise CLIError('Failed to load history', importance=2)
            return r
        _raise.__name__ = func.__name__
        return _raise

    @classmethod
    def _get_cmd_ids(this, func):
        def _raise(self, cmd_ids, *args, **kwargs):
            if not cmd_ids:
                raise CLISyntaxError(
                    'Usage: <id1|id1-id2> [id3|id3-id4] ...',
                    details=self.__doc__.split('\n'))
            return func(self, cmd_ids, *args, **kwargs)
        _raise.__name__ = func.__name__
        return _raise


class Cyclades(object):
    about_flavor_id = [
        'To get a list of flavors', '  kamaki flavor list',
        'More details on a flavor', '  kamaki flavor info FLAVOR_ID', ]

    about_network_id = [
        'To get a list of networks', '  kamaki network list',
        'More details on a network', '  kamaki network info NETWORK_ID', ]

    about_ips = [
        'To list available IPs', '  kamaki ip list',
        'To reserve a new IP', '  kamaki ip create', ]

    @classmethod
    def connection(this, func):
        return Generic._connection(func)

    @classmethod
    def date(this, func):
        def _raise(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except ClientError as ce:
                if ce.status in (304, ):
                    log.debug('%s %s' % (ce.status, ce))
                    self.error('No servers have been modified since')
                else:
                    raise
        _raise.__name__ = func.__name__
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
                    'Invalid cluster size %s' % size,
                    importance=1, details=['%s' % ae])
            except ClientError:
                raise
        _raise.__name__ = func.__name__
        return _raise

    @classmethod
    def network_id(this, func):
        def _raise(self, *args, **kwargs):
            network_id = kwargs.get('network_id', None)
            try:
                return func(self, *args, **kwargs)
            except ClientError as ce:
                if network_id and ce.status in (404, 400):
                    msg = ''
                    if ce.status in (400, ):
                        try:
                            network_id = int(network_id)
                        except ValueError:
                            msg = 'Network ID should be a positive integer'
                            log.debug(msg)
                    raise CLIError(
                        'No network with id %s found' % network_id,
                        importance=2,
                        details=[msg, ] + this.about_network_id + [
                            '%s %s' % (getattr(ce, 'status', ''), ce)])
                raise
        _raise.__name__ = func.__name__
        return _raise

    @classmethod
    def network_in_use(this, func):
        def _raise(self, *args, **kwargs):
            network_id = kwargs.get('network_id', None)
            try:
                return func(self, *args, **kwargs)
            except ClientError as ce:
                if ce.status in (409, ):
                    raise CLIError(
                        'Network with id %s is in use' % network_id,
                        importance=3, details=[
                            'To list all network ports', '  kamaki port list',
                            '%s %s' % (getattr(ce, 'status', ''), ce)])
                raise
        _raise.__name__ = func.__name__
        return _raise

    @classmethod
    def network_permissions(this, func):
        def _raise(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except ClientError as ce:
                if ce.status in (403, ):
                    network_id = kwargs.get('network_id', '')
                    raise CLIError(
                        'Insufficient permissions for this action',
                        importance=2, details=[
                            'To get information on network',
                            '  kamaki network info %s' % network_id,
                            '%s %s' % (getattr(ce, 'status', ''), ce)])
                raise
        _raise.__name__ = func.__name__
        return _raise

    @classmethod
    def subnet_id(this, func):
        def _raise(self, *args, **kwargs):
            subnet_id = kwargs.get('subnet_id', None)
            try:
                return func(self, *args, **kwargs)
            except ClientError as ce:
                if subnet_id and ce.status in (404, 400):
                    details = []
                    if ce.status in (400, ):
                        try:
                            subnet_id = int(subnet_id)
                        except ValueError:
                            details = ['Subnet ID should be positive integer']
                            log.debug(details[-1])
                    raise CLIError(
                        'No subnet with id %s found' % subnet_id,
                        importance=2, details=details + [
                            'To list subnets', '  kamaki subnet list',
                            '%s %s' % (getattr(ce, 'status', ''), ce)])
                raise
        _raise.__name__ = func.__name__
        return _raise

    @classmethod
    def subnet_permissions(this, func):
        def _raise(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except ClientError as ce:
                if ce.status in (401, ):
                    subnet_id = kwargs.get('subnet_id', '')
                    raise CLIError(
                        'Insufficient permissions for this action',
                        importance=2, details=[
                            'Make sure this subnet belongs to current user',
                            'To see information on subnet',
                            '  kamaki subnet info %s' % subnet_id,
                            '%s %s' % (getattr(ce, 'status', ''), ce)])
                raise
        _raise.__name__ = func.__name__
        return _raise

    @classmethod
    def port_id(this, func):
        def _raise(self, *args, **kwargs):
            port_id = kwargs.get('port_id', None)
            try:
                return func(self, *args, **kwargs)
            except ClientError as ce:
                if port_id and ce.status in (404, 400):
                    details = []
                    if ce.status in (400, ):
                        try:
                            port_id = int(port_id)
                        except ValueError:
                            details = ['Port ID should be positive integer']
                            log.debug(details[-1])
                    raise CLIError(
                        'No port with id %s found' % port_id,
                        importance=2, details=details + [
                            'To list ports', '  kamaki port list',
                            '%s %s' % (getattr(ce, 'status', ''), ce)])
                raise
        _raise.__name__ = func.__name__
        return _raise

    @classmethod
    def ip_id(this, func):
        def _raise(self, *args, **kwargs):
            ip_id = kwargs.get('ip_id', None)
            try:
                return func(self, *args, **kwargs)
            except ClientError as ce:
                if ce.status in (404, 400):
                    details = []
                    if ce.status in (400, ):
                        try:
                            ip_id = int(ip_id)
                        except ValueError:
                            details = ['IP ID should be positive integer']
                            log.debug(details[-1])
                    raise CLIError(
                        'No floating IP with ID %s found' % ip_id,
                        importance=2, details=details + this.about_ips + [
                            '%s %s' % (getattr(ce, 'status', ''), ce)])
                raise
        _raise.__name__ = func.__name__
        return _raise

    @classmethod
    def flavor_id(this, func):
        def _raise(self, *args, **kwargs):
            flavor_id = kwargs.get('flavor_id', None)
            try:
                return func(self, *args, **kwargs)
            except ClientError as ce:
                if ce.status in (404, 400):
                    details = this.about_flavor_id
                    if ce.status in (400, ):
                        try:
                            flavor_id = int(flavor_id)
                        except ValueError:
                            details.insert(
                                0, 'Flavor ID should be a positive integer')
                    raise CLIError(
                        'No flavor with ID %s' % flavor_id,
                        importance=2, details=details + [
                            '%s %s' % (getattr(ce, 'status', ''), ce)])
                raise
        _raise.__name__ = func.__name__
        return _raise

    @classmethod
    def server_id(this, func):
        def _raise(self, *args, **kwargs):
            details = ['To get a list of all servers', '  kamaki server list']
            server_id = kwargs.get('server_id', None)
            try:
                server_id = int(server_id)
                assert server_id > 0, 'error: %s is not positive' % server_id
            except (ValueError, AssertionError) as err:
                raise CLIError(
                    'Invalid server id %s' % server_id,
                    importance=2, details=[
                        'Server id must be a positive integer'] + details + [
                            err, ])
            try:
                return func(self, *args, **kwargs)
            except ClientError as ce:
                if ce.status in (404, ):
                    raise CLIError(
                        'No servers with ID %s' % server_id,
                        importance=2, details=details + [
                            '%s %s' % (getattr(ce, 'status', ''), ce)])
                raise
        _raise.__name__ = func.__name__
        return _raise

    @classmethod
    def endpoint(this, func):
        """If the endpoint contains server_id, check if the id exists"""
        def _raise(self, *args, **kwargs):
            server_id = kwargs.get('server_id', None)
            try:
                func(self, *args, **kwargs)
            except ClientError as ce:
                if ce.status in (400, ):
                    self.client.get_server_details(server_id)
                raise
        _raise.__name__ = func.__name__
        return _raise

    @classmethod
    def metadata(this, func):
        def _raise(self, *args, **kwargs):
            key = kwargs.get('key', None)
            try:
                func(self, *args, **kwargs)
            except ClientError as ce:
                if key and ce.status == 404 and (
                        'metadata' in ('%s' % ce).lower()):
                    raise CLIError(
                        'No virtual server metadata with key %s' % key,
                        details=['%s %s' % (getattr(ce, 'status', ''), ce), ])
                raise
        _raise.__name__ = func.__name__
        return _raise


class Image(object):
    about_image_id = [
        'To list all images', '  kamaki image list',
        'To get image details', '  kamaki image info IMAGE_ID', ]

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
                if image_id and ce.status in (404, 400):
                    raise CLIError(
                        'No image with id %s found' % image_id,
                        importance=2, details=this.about_image_id + [
                            '%s %s' % (getattr(ce, 'status', ''), ce)])
                raise
        _raise.__name__ = func.__name__
        return _raise

    @classmethod
    def permissions(this, func):
        def _raise(self, *args, **kwargs):
            try:
                func(self, *args, **kwargs)
            except ClientError as ce:
                if ce.status in (403, 405):
                    raise CLIError(
                        'Insufficient permissions for this action',
                        importance=2, details=[
                            'To see the owner of an image',
                            '  kamaki image info IMAGE_ID',
                            'To see image file permissions',
                            '  kamaki file info IMAGE_LOCATION --sharing',
                            '%s %s' % (getattr(ce, 'status', ''), ce)])
                raise
        _raise.__name__ = func.__name__
        return _raise


class Pithos(object):
    container_howto = [
        'To list containers',
        '  kamaki container list',
        'Hint: Use a / to refer to a container (default: /pithos) e.g.,',
        'To list contents of container "images"',
        '  kamaki file list /images',
        'To get information on file "my.img" in container "images"',
        '  kamaki file info /images/my.img', ]

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
                        'Insufficient credentials for this operation',
                        details=['%s %s' % (getattr(ce, 'status', ''), ce), ])
                raise
        _raise.__name__ = func.__name__
        return _raise

    @classmethod
    def quota(this, func):
        def _raise(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except ClientError as ce:
                if ce.status == 413:
                    raise CLIError('User quota exceeded', details=[
                        'To get total quotas',
                        '  kamaki quota list --resource=pithos',
                        'To get container limit',
                        '  kamaki container info CONTAINER --size-limit',
                        'Set a higher container limit:',
                        '  kamaki container modify CONTAINER '
                        '--size-limit=NEW_LIMIT',
                        '%s' % ce])
                raise
        _raise.__name__ = func.__name__
        return _raise

    @classmethod
    def container(this, func):
        def _raise(self, *args, **kwargs):
            dst_cont = kwargs.get('dst_cont', None)
            try:
                return func(self, *args, **kwargs)
            except ClientError as ce:
                if '/' in getattr(self, 'container', ''):
                    raise CLIError(
                        'Invalid container name %s' % self.container,
                        importance=2, details=[
                            '"/" is an invalid character for containers',
                            '%s %s' % (getattr(ce, 'status', ''), ce)
                        ])
                elif ce.status in (404, ):
                        cont = ('%s or %s' % (self.container, dst_cont)) if (
                            dst_cont) else self.container
                        raise CLIError(
                            'Container "%s" does not exist' % cont,
                            importance=2, details=this.container_howto + [
                                '%s %s' % (getattr(ce, 'status', ''), ce)])
                raise
        _raise.__name__ = func.__name__
        return _raise

    @classmethod
    def local_path_download(this, func):
        def _raise(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except IOError as ioe:
                raise CLIError(
                    'Failed to access a local file', importance=2, details=[
                        'To check if the file exists',
                        '  kamaki file info PATH',
                        'All directories in a remote path must exist, or the '
                        'download will fail',
                        'To create a remote directory',
                        '  kamaki file mkdir REMOTE_DIRECTORY_PATH',
                        u'%s' % ioe])
        _raise.__name__ = func.__name__
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
                    details=[u'%s' % ioe, ], importance=2)
        _raise.__name__ = func.__name__
        return _raise

    @classmethod
    def object_path(this, func):
        def _raise(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except ClientError as ce:
                if ce.status in (404, ):
                    _cnt = self.container
                    _cnt = '[/%s]' % _cnt if _cnt == 'pithos' else '/%s' % _cnt
                    raise CLIError(
                        'No object "%s" in container "%s"' % (
                            self.path, self.container),
                        importance=2, details=[
                            'To list contents in container',
                            '  kamaki file list %s' % _cnt,
                            '%s %s' % (getattr(ce, 'status', ''), ce), ])
                raise
        _raise.__name__ = func.__name__
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
                if size and ce.status in (416, 400):
                    raise CLIError(
                        'Remote object %s:%s <= %s %s' % (
                            self.container, self.path, format_size(size),
                            ('(%sB)' % size) if size >= 1024 else ''),
                        details=['%s %s' % (getattr(ce, 'status', ''), ce)])
                raise
        _raise.__name__ = func.__name__
        return _raise
