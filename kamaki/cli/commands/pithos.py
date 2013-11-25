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

from io import StringIO
from pydoc import pager

from kamaki.clients.pithos import PithosClient, ClientError

from kamaki.cli import command
from kamaki.cli.command_tree import CommandTree
from kamaki.cli.commands import (
    _command_init, errors, addLogSettings, DontRaiseKeyError, _optional_json,
    _name_filter, _optional_output_cmd)
from kamaki.cli.errors import (
    CLIBaseUrlError, CLIError)
from kamaki.cli.argument import (
    FlagArgument, IntArgument, ValueArgument, DateArgument)
from kamaki.cli.utils import (format_size, bold)

file_cmds = CommandTree('file', 'Pithos+/Storage object level API commands')
container_cmds = CommandTree(
    'container', 'Pithos+/Storage container level API commands')
sharers_commands = CommandTree('sharers', 'Pithos+/Storage sharers')
_commands = [file_cmds, container_cmds, sharers_commands]


class _pithos_init(_command_init):
    """Initilize a pithos+ client
    There is always a default account (current user uuid)
    There is always a default container (pithos)
    """

    @DontRaiseKeyError
    def _custom_container(self):
        return self.config.get_cloud(self.cloud, 'pithos_container')

    @DontRaiseKeyError
    def _custom_uuid(self):
        return self.config.get_cloud(self.cloud, 'pithos_uuid')

    def _set_account(self):
        self.account = self._custom_uuid()
        if self.account:
            return
        astakos = getattr(self, 'auth_base', None)
        if astakos:
            self.account = astakos.user_term('id', self.token)
        else:
            raise CLIBaseUrlError(service='astakos')

    @errors.generic.all
    @addLogSettings
    def _run(self):
        cloud = getattr(self, 'cloud', None)
        if cloud:
            self.base_url = self._custom_url('pithos')
        else:
            self.cloud = 'default'
        self.token = self._custom_token('pithos')
        self.container = self._custom_container() or 'pithos'

        astakos = getattr(self, 'auth_base', None)
        if astakos:
            self.token = self.token or astakos.token
            if not self.base_url:
                pithos_endpoints = astakos.get_service_endpoints(
                    self._custom_type('pithos') or 'object-store',
                    self._custom_version('pithos') or '')
                self.base_url = pithos_endpoints['publicURL']
        else:
            raise CLIBaseUrlError(service='astakos')

        self._set_account()
        self.client = PithosClient(
            self.base_url, self.token, self.account, self.container)

    def main(self):
        self._run()


class _pithos_account(_pithos_init):
    """Setup account"""

    def __init__(self, arguments={}, auth_base=None, cloud=None):
        super(_pithos_account, self).__init__(arguments, auth_base, cloud)
        self['account'] = ValueArgument(
            'Use (a different) user uuid', ('-A', '--account'))

    def _run(self):
        super(_pithos_account, self)._run()
        self.client.account = self['account'] or getattr(
            self, 'account', getattr(self.client, 'account', None))


class _pithos_container(_pithos_account):
    """Setup container"""

    def __init__(self, arguments={}, auth_base=None, cloud=None):
        super(_pithos_container, self).__init__(arguments, auth_base, cloud)
        self['container'] = ValueArgument(
            'Use this container (default: pithos)', ('-C', '--container'))

    @staticmethod
    def _is_dir(remote_dict):
        return 'application/directory' == remote_dict.get(
            'content_type', remote_dict.get('content-type', ''))

    @staticmethod
    def _resolve_pithos_url(url):
        """Match urls of one of the following formats:
        pithos://ACCOUNT/CONTAINER/OBJECT_PATH
        /CONTAINER/OBJECT_PATH
        return account, container, path
        """
        account, container, path, prefix = '', '', url, 'pithos://'
        if url.startswith(prefix):
            account, sep, url = url[len(prefix):].partition('/')
            url = '/%s' % url
        if url.startswith('/'):
            container, sep, path = url[1:].partition('/')
        return account, container, path

    def _run(self, url=None):
        acc, con, self.path = self._resolve_pithos_url(url or '')
        self.account = acc or getattr(self, 'account', '')
        super(_pithos_container, self)._run()
        self.container = con or self['container'] or getattr(
            self, 'container', None) or getattr(self.client, 'container', '')
        self.client.container = self.container


@command(file_cmds)
class file_list(_pithos_container, _optional_json, _name_filter):
    """List all objects in a container or a directory object"""

    arguments = dict(
        detail=FlagArgument('detailed output', ('-l', '--list')),
        limit=IntArgument('limit number of listed items', ('-n', '--number')),
        marker=ValueArgument('output greater that marker', '--marker'),
        delimiter=ValueArgument('show output up to delimiter', '--delimiter'),
        meta=ValueArgument(
            'show output with specified meta keys', '--meta',
            default=[]),
        if_modified_since=ValueArgument(
            'show output modified since then', '--if-modified-since'),
        if_unmodified_since=ValueArgument(
            'show output not modified since then', '--if-unmodified-since'),
        until=DateArgument('show metadata until then', '--until'),
        format=ValueArgument(
            'format to parse until data (default: d/m/Y H:M:S )', '--format'),
        shared=FlagArgument('show only shared', '--shared'),
        more=FlagArgument('read long results', '--more'),
        enum=FlagArgument('Enumerate results', '--enumerate'),
        recursive=FlagArgument(
            'Recursively list containers and their contents',
            ('-R', '--recursive'))
    )

    def print_objects(self, object_list):
        for index, obj in enumerate(object_list):
            pretty_obj = obj.copy()
            index += 1
            empty_space = ' ' * (len(str(len(object_list))) - len(str(index)))
            if 'subdir' in obj:
                continue
            if obj['content_type'] == 'application/directory':
                isDir, size = True, 'D'
            else:
                isDir, size = False, format_size(obj['bytes'])
                pretty_obj['bytes'] = '%s (%s)' % (obj['bytes'], size)
            oname = obj['name'] if self['more'] else bold(obj['name'])
            prfx = ('%s%s. ' % (empty_space, index)) if self['enum'] else ''
            if self['detail']:
                self.writeln('%s%s' % (prfx, oname))
                self.print_dict(pretty_obj, exclude=('name'))
                self.writeln()
            else:
                oname = '%s%9s %s' % (prfx, size, oname)
                oname += '/' if isDir else u''
                self.writeln(oname)

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    @errors.pithos.object_path
    def _run(self):
        r = self.client.container_get(
            limit=False if self['more'] else self['limit'],
            marker=self['marker'],
            prefix=self['name_pref'] or '/',
            delimiter=self['delimiter'],
            path=self.path or '',
            if_modified_since=self['if_modified_since'],
            if_unmodified_since=self['if_unmodified_since'],
            until=self['until'],
            meta=self['meta'],
            show_only_shared=self['shared'])
        files = self._filter_by_name(r.json)
        if self['more']:
            outbu, self._out = self._out, StringIO()
        try:
            if self['json_output'] or self['output_format']:
                self._print(files)
            else:
                self.print_objects(files)
        finally:
            if self['more']:
                pager(self._out.getvalue())
                self._out = outbu

    def main(self, path_or_url='/'):
        super(self.__class__, self)._run(path_or_url)
        self._run()


@command(file_cmds)
class file_create(_pithos_container, _optional_output_cmd):
    """Create an empty file"""

    arguments = dict(
        content_type=ValueArgument(
            'Set content type (default: application/octet-stream)',
            '--content-type',
            default='application/octet-stream')
    )

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    def _run(self):
        self._optional_output(
            self.client.create_object(self.path, self['content_type']))

    def main(self, path_or_url):
        super(self.__class__, self)._run(path_or_url)
        self._run()


@command(file_cmds)
class file_mkdir(_pithos_container, _optional_output_cmd):
    """Create a directory: /file create --content-type='applcation/directory'
    """

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    def _run(self):
        self._optional_output(self.client.create_directory(self.path))

    def main(self, container___directory):
        super(self.__class__, self)._run(
            container___directory, path_is_optional=False)
        self._run()


class _source_destination(_pithos_container, _optional_output_cmd):

    sd_arguments = dict(
        destination_user_uuid=ValueArgument(
            'default: current user uuid', '--to-account'),
        destination_container=ValueArgument(
            'default: pithos', '--to-container'),
        source_prefix=FlagArgument(
            'Transfer all files that are prefixed with SOURCE PATH If the '
            'destination path is specified, replace SOURCE_PATH with '
            'DESTINATION_PATH',
            ('-r', '--recursive')),
        force=FlagArgument(
            'Overwrite destination objects, if needed', ('-f', '--force'))
    )

    def __init__(self, arguments={}, auth_base=None, cloud=None):
        self.arguments.update(arguments)
        self.arguments.update(self.sd_arguments)
        super(_source_destination, self).__init__(
            self.arguments, auth_base, cloud)

    def _report_transfer(self, src, dst, transfer_name):
        if not dst:
            if transfer_name in ('move', ):
                self.error('  delete source directory %s' % src)
            return
        dst_prf = '' if self.account == self.dst_client.account else (
                'pithos://%s' % self.dst_client.account)
        if src:
            src_prf = '' if self.account == self.dst_client.account else (
                    'pithos://%s' % self.account)
            self.error('  %s %s/%s/%s\n  -->  %s/%s/%s' % (
                transfer_name,
                src_prf, self.container, src,
                dst_prf, self.dst_client.container, dst))
        else:
            self.error('  mkdir %s/%s/%s' % (
                dst_prf, self.dst_client.container, dst))

    @errors.generic.all
    @errors.pithos.account
    def _src_dst(self, version=None):
        """Preconditions:
        self.account, self.container, self.path
        self.dst_acc, self.dst_con, self.dst_path
        They should all be configured properly
        :returns: [(src_path, dst_path), ...], if src_path is None, create
            destination directory
        """
        src_objects, dst_objects, pairs = dict(), dict(), []
        try:
            for obj in self.dst_client.list_objects(
                    prefix=self.dst_path or self.path or '/'):
                dst_objects[obj['name']] = obj
        except ClientError as ce:
            if ce.status in (404, ):
                raise CLIError(
                    'Destination container pithos://%s/%s not found' % (
                        self.dst_client.account, self.dst_client.container))
            raise ce
        if self['source_prefix']:
            #  Copy and replace prefixes
            for src_obj in self.client.list_objects(prefix=self.path or '/'):
                src_objects[src_obj['name']] = src_obj
            for src_path, src_obj in src_objects.items():
                dst_path = '%s%s' % (
                    self.dst_path or self.path, src_path[len(self.path):])
                dst_obj = dst_objects.get(dst_path, None)
                if self['force'] or not dst_obj:
                    #  Just do it
                    pairs.append((
                        None if self._is_dir(src_obj) else src_path, dst_path))
                    if self._is_dir(src_obj):
                        pairs.append((self.path or dst_path, None))
                elif not (self._is_dir(dst_obj) and self._is_dir(src_obj)):
                    raise CLIError(
                        'Destination object exists', importance=2, details=[
                            'Failed while transfering:',
                            '    pithos://%s/%s/%s' % (
                                    self.account,
                                    self.container,
                                    src_path),
                            '--> pithos://%s/%s/%s' % (
                                    self.dst_client.account,
                                    self.dst_client.container,
                                    dst_path),
                            'Use %s to transfer overwrite' % ('/'.join(
                                    self.arguments['force'].parsed_name))])
        else:
            #  One object transfer
            try:
                src_obj = self.client.get_object_info(self.path)
            except ClientError as ce:
                if ce.status in (204, ):
                    raise CLIError(
                        'Missing specific path container %s' % self.container,
                        importance=2, details=[
                            'To transfer container contents %s' % (
                                '/'.join(self.arguments[
                                    'source_prefix'].parsed_name))])
                raise
            dst_path = self.dst_path or self.path
            dst_obj = dst_objects.get(dst_path, None) or self.path
            if self['force'] or not dst_obj:
                pairs.append(
                    (None if self._is_dir(src_obj) else self.path, dst_path))
                if self._is_dir(src_obj):
                    pairs.append((self.path or dst_path, None))
            elif self._is_dir(src_obj):
                raise CLIError(
                    'Cannot transfer an application/directory object',
                    importance=2, details=[
                        'The object pithos://%s/%s/%s is a directory' % (
                            self.account,
                            self.container,
                            self.path),
                        'To recursively copy a directory, use',
                        '  %s' % ('/'.join(
                            self.arguments['source_prefix'].parsed_name)),
                        'To create a file, use',
                        '  /file create  (general purpose)',
                        '  /file mkdir   (a directory object)'])
            else:
                raise CLIError(
                    'Destination object exists',
                    importance=2, details=[
                        'Failed while transfering:',
                        '    pithos://%s/%s/%s' % (
                                self.account,
                                self.container,
                                self.path),
                        '--> pithos://%s/%s/%s' % (
                                self.dst_client.account,
                                self.dst_client.container,
                                dst_path),
                        'Use %s to transfer overwrite' % ('/'.join(
                                self.arguments['force'].parsed_name))])
        return pairs

    def _run(self, source_path_or_url, destination_path_or_url=''):
        super(_source_destination, self)._run(source_path_or_url)
        dst_acc, dst_con, dst_path = self._resolve_pithos_url(
            destination_path_or_url)
        self.dst_client = PithosClient(
            base_url=self.client.base_url, token=self.client.token,
            container=self[
                'destination_container'] or dst_con or self.client.container,
            account=self[
                'destination_user_uuid'] or dst_acc or self.client.account)
        self.dst_path = dst_path or self.path


@command(file_cmds)
class file_copy(_source_destination):
    """Copy objects, even between different accounts or containers"""

    arguments = dict(
        public=ValueArgument('publish new object', '--public'),
        content_type=ValueArgument(
            'change object\'s content type', '--content-type'),
        source_version=ValueArgument(
            'copy specific version', ('-S', '--source-version'))
    )

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    @errors.pithos.account
    def _run(self):
        for src, dst in self._src_dst(self['source_version']):
            self._report_transfer(src, dst, 'copy')
            if src and dst:
                self.dst_client.copy_object(
                    src_container=self.client.container,
                    src_object=src,
                    dst_container=self.dst_client.container,
                    dst_object=dst,
                    source_account=self.account,
                    source_version=self['source_version'],
                    public=self['public'],
                    content_type=self['content_type'])
            elif dst:
                self.dst_client.create_directory(dst)

    def main(self, source_path_or_url, destination_path_or_url=None):
        super(file_copy, self)._run(
            source_path_or_url, destination_path_or_url or '')
        self._run()


@command(file_cmds)
class file_move(_source_destination):
    """Move objects, even between different accounts or containers"""

    arguments = dict(
        public=ValueArgument('publish new object', '--public'),
        content_type=ValueArgument(
            'change object\'s content type', '--content-type')
    )

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    @errors.pithos.account
    def _run(self):
        for src, dst in self._src_dst():
            self._report_transfer(src, dst, 'move')
            if src and dst:
                self.dst_client.move_object(
                    src_container=self.client.container,
                    src_object=src,
                    dst_container=self.dst_client.container,
                    dst_object=dst,
                    source_account=self.account,
                    public=self['public'],
                    content_type=self['content_type'])
            elif dst:
                self.dst_client.create_directory(dst)
            else:
                self.client.del_object(src)

    def main(self, source_path_or_url, destination_path_or_url=None):
        super(file_move, self)._run(
            source_path_or_url, destination_path_or_url or '')
        self._run()
