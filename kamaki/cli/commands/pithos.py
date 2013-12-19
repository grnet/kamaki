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

from time import localtime, strftime
from io import StringIO
from pydoc import pager
from os import path, walk, makedirs

from kamaki.clients.pithos import PithosClient, ClientError

from kamaki.cli import command
from kamaki.cli.command_tree import CommandTree
from kamaki.cli.commands import (
    _command_init, errors, addLogSettings, DontRaiseKeyError, _optional_json,
    _name_filter, _optional_output_cmd)
from kamaki.cli.errors import (
    CLIBaseUrlError, CLIError, CLIInvalidArgument, raiseCLIError,
    CLISyntaxError)
from kamaki.cli.argument import (
    FlagArgument, IntArgument, ValueArgument, DateArgument, KeyValueArgument,
    ProgressBarArgument, RepeatableArgument, DataSizeArgument)
from kamaki.cli.utils import (
    format_size, bold, get_path_size, guess_mime_type)

file_cmds = CommandTree('file', 'Pithos+/Storage object level API commands')
container_cmds = CommandTree(
    'container', 'Pithos+/Storage container level API commands')
sharer_cmds = CommandTree('sharer', 'Pithos+/Storage sharers')
group_cmds = CommandTree('group', 'Pithos+/Storage user groups')
_commands = [file_cmds, container_cmds, sharer_cmds, group_cmds]


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

    def print_objects(self, object_list):
        for index, obj in enumerate(object_list):
            pretty_obj = obj.copy()
            index += 1
            empty_space = ' ' * (len(str(len(object_list))) - len(str(index)))
            if 'subdir' in obj:
                continue
            if self._is_dir(obj):
                size = 'D'
            else:
                size = format_size(obj['bytes'])
                pretty_obj['bytes'] = '%s (%s)' % (obj['bytes'], size)
            oname = obj['name'] if self['more'] else bold(obj['name'])
            prfx = ('%s%s. ' % (empty_space, index)) if self['enum'] else ''
            if self['detail']:
                self.writeln('%s%s' % (prfx, oname))
                self.print_dict(pretty_obj, exclude=('name'))
                self.writeln()
            else:
                oname = '%s%9s %s' % (prfx, size, oname)
                oname += '/' if self._is_dir(obj) else u''
                self.writeln(oname)

    @staticmethod
    def _is_dir(remote_dict):
        return 'application/directory' == remote_dict.get(
            'content_type', remote_dict.get('content-type', ''))

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
    def _resolve_pithos_url(url):
        """Match urls of one of the following formats:
        pithos://ACCOUNT/CONTAINER/OBJECT_PATH
        /CONTAINER/OBJECT_PATH
        return account, container, path
        """
        account, container, obj_path, prefix = '', '', url, 'pithos://'
        if url.startswith(prefix):
            account, sep, url = url[len(prefix):].partition('/')
            url = '/%s' % url
        if url.startswith('/'):
            container, sep, obj_path = url[1:].partition('/')
        return account, container, obj_path

    def _run(self, url=None):
        acc, con, self.path = self._resolve_pithos_url(url or '')
        #  self.account = acc or getattr(self, 'account', '')
        super(_pithos_container, self)._run()
        self.container = con or self['container'] or getattr(
            self, 'container', None) or getattr(self.client, 'container', '')
        self.client.account = acc or self.client.account
        self.client.container = self.container


@command(file_cmds)
class file_info(_pithos_container, _optional_json):
    """Get information/details about a file"""

    arguments = dict(
        object_version=ValueArgument(
            'download a file of a specific version', '--object-version'),
        hashmap=FlagArgument(
            'Get file hashmap instead of details', '--hashmap'),
        matching_etag=ValueArgument(
            'show output if ETags match', '--if-match'),
        non_matching_etag=ValueArgument(
            'show output if ETags DO NOT match', '--if-none-match'),
        modified_since_date=DateArgument(
            'show output modified since then', '--if-modified-since'),
        unmodified_since_date=DateArgument(
            'show output unmodified since then', '--if-unmodified-since'),
        sharing=FlagArgument(
            'show object permissions and sharing information', '--sharing'),
        metadata=FlagArgument('show only object metadata', '--metadata'),
        versions=FlagArgument(
            'show the list of versions for the file', '--object-versions')
    )

    def version_print(self, versions):
        return {'/%s/%s' % (self.container, self.path): [
            dict(version_id=vitem[0], created=strftime(
                '%d-%m-%Y %H:%M:%S',
                localtime(float(vitem[1])))) for vitem in versions]}

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    @errors.pithos.object_path
    def _run(self):
        if self['hashmap']:
            r = self.client.get_object_hashmap(
                self.path,
                version=self['object_version'],
                if_match=self['matching_etag'],
                if_none_match=self['non_matching_etag'],
                if_modified_since=self['modified_since_date'],
                if_unmodified_since=self['unmodified_since_date'])
        elif self['sharing']:
            r = self.client.get_object_sharing(self.path)
            r['public url'] = self.client.get_object_info(
                self.path, version=self['object_version']).get(
                    'x-object-public', None)
        elif self['metadata']:
            r, preflen = dict(), len('x-object-meta-')
            for k, v in self.client.get_object_meta(self.path).items():
                r[k[preflen:]] = v
        elif self['versions']:
            r = self.version_print(
                self.client.get_object_versionlist(self.path))
        else:
            r = self.client.get_object_info(
                self.path, version=self['object_version'])
        self._print(r, self.print_dict)

    def main(self, path_or_url):
        super(self.__class__, self)._run(path_or_url)
        self._run()


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
        shared_by_me=FlagArgument(
            'show only files shared to other users', '--shared-by-me'),
        public=FlagArgument('show only published objects', '--public'),
        more=FlagArgument('read long results', '--more'),
        enum=FlagArgument('Enumerate results', '--enumerate'),
        recursive=FlagArgument(
            'Recursively list containers and their contents',
            ('-R', '--recursive'))
    )

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    @errors.pithos.object_path
    def _run(self):
        r = self.client.container_get(
            limit=False if self['more'] else self['limit'],
            marker=self['marker'],
            prefix=self['name_pref'],
            delimiter=self['delimiter'],
            path=self.path or '',
            show_only_shared=self['shared_by_me'],
            public=self['public'],
            if_modified_since=self['if_modified_since'],
            if_unmodified_since=self['if_unmodified_since'],
            until=self['until'],
            meta=self['meta'])

        #  REMOVE THIS if version >> 0.12
        if not r.json:
            self.error('  NOTE: Since v0.12, use / for containers e.g.,')
            self.error('    [kamaki] file list /pithos')

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

    def main(self, path_or_url=''):
        super(self.__class__, self)._run(path_or_url)
        self._run()


@command(file_cmds)
class file_modify(_pithos_container):
    """Modify the attributes of a file or directory object"""

    arguments = dict(
        publish=FlagArgument(
            'Make an object public (returns the public URL)', '--publish'),
        unpublish=FlagArgument(
            'Make an object unpublic', '--unpublish'),
        uuid_for_read_permission=RepeatableArgument(
            'Give read access to user/group (can be repeated, accumulative). '
            'Format for users: UUID . Format for groups: UUID:GROUP . '
            'Use * for all users/groups', '--read-permission'),
        uuid_for_write_permission=RepeatableArgument(
            'Give write access to user/group (can be repeated, accumulative). '
            'Format for users: UUID . Format for groups: UUID:GROUP . '
            'Use * for all users/groups', '--write-permission'),
        no_permissions=FlagArgument('Remove permissions', '--no-permissions'),
        metadata_to_set=KeyValueArgument(
            'Add metadata (KEY=VALUE) to an object (can be repeated)',
            '--metadata-add'),
        metadata_key_to_delete=RepeatableArgument(
            'Delete object metadata (can be repeated)', '--metadata-del'),
    )
    required = [
        'publish', 'unpublish', 'uuid_for_read_permission', 'metadata_to_set',
        'uuid_for_write_permission', 'no_permissions',
        'metadata_key_to_delete']

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    @errors.pithos.object_path
    def _run(self):
        if self['publish']:
            self.writeln(self.client.publish_object(self.path))
        if self['unpublish']:
            self.client.unpublish_object(self.path)
        if self['uuid_for_read_permission'] or self[
                'uuid_for_write_permission']:
            perms = self.client.get_object_sharing(self.path)
            read, write = perms.get('read', ''), perms.get('write', '')
            read = read.split(',') if read else []
            write = write.split(',') if write else []
            read += (self['uuid_for_read_permission'] or [])
            write += (self['uuid_for_write_permission'] or [])
            self.client.set_object_sharing(
                self.path, read_permission=read, write_permission=write)
            self.print_dict(self.client.get_object_sharing(self.path))
        if self['no_permissions']:
            self.client.del_object_sharing(self.path)
        metadata = self['metadata_to_set'] or dict()
        for k in (self['metadata_key_to_delete'] or []):
            metadata[k] = ''
        if metadata:
            self.client.set_object_meta(self.path, metadata)
            self.print_dict(self.client.get_object_meta(self.path))

    def main(self, path_or_url):
        super(self.__class__, self)._run(path_or_url)
        if self['publish'] and self['unpublish']:
            raise CLIInvalidArgument(
                'Arguments %s and %s cannot be used together' % (
                    self.arguments['publish'].lvalue,
                    self.arguments['publish'].lvalue))
        if self['no_permissions'] and (
                self['uuid_for_read_permission'] or self[
                    'uuid_for_write_permission']):
            raise CLIInvalidArgument(
                '%s cannot be used with other permission arguments' % (
                    self.arguments['no_permissions'].lvalue))
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

    def main(self, path_or_url):
        super(self.__class__, self)._run(path_or_url)
        self._run()


@command(file_cmds)
class file_delete(_pithos_container):
    """Delete a file or directory object"""

    arguments = dict(
        until_date=DateArgument('remove history until then', '--until'),
        yes=FlagArgument('Do not prompt for permission', '--yes'),
        recursive=FlagArgument(
            'If a directory, empty first', ('-r', '--recursive')),
        delimiter=ValueArgument(
            'delete objects prefixed with <object><delimiter>', '--delimiter')
    )

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    @errors.pithos.object_path
    def _run(self):
        if self.path:
            if self['yes'] or self.ask_user(
                    'Delete /%s/%s ?' % (self.container, self.path)):
                self.client.del_object(
                    self.path,
                    until=self['until_date'],
                    delimiter='/' if self['recursive'] else self['delimiter'])
            else:
                self.error('Aborted')
        else:
            if self['yes'] or self.ask_user(
                    'Empty container /%s ?' % self.container):
                self.client.container_delete(self.container, delimiter='/')
            else:
                self.error('Aborted')

    def main(self, path_or_url):
        super(self.__class__, self)._run(path_or_url)
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
            'Overwrite destination objects, if needed', ('-f', '--force')),
        source_version=ValueArgument(
            'The version of the source object', '--source-version')
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
            for src_obj in self.client.list_objects(prefix=self.path):
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
                            'Use %s to transfer overwrite' % (
                                    self.arguments['force'].lvalue)])
        else:
            #  One object transfer
            try:
                src_version_arg = self.arguments.get('source_version', None)
                src_obj = self.client.get_object_info(
                    self.path,
                    version=src_version_arg.value if src_version_arg else None)
            except ClientError as ce:
                if ce.status in (204, ):
                    raise CLIError(
                        'Missing specific path container %s' % self.container,
                        importance=2, details=[
                            'To transfer container contents %s' % (
                                self.arguments['source_prefix'].lvalue)])
                raise
            dst_path = self.dst_path or self.path
            dst_obj = dst_objects.get(dst_path or self.path, None)
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
                        '  %s' % self.arguments['source_prefix'].lvalue,
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
                        'Use %s to transfer overwrite' % (
                                self.arguments['force'].lvalue)])
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
                'destination_user_uuid'] or dst_acc or self.account)
        self.dst_path = dst_path or self.path


@command(file_cmds)
class file_copy(_source_destination):
    """Copy objects, even between different accounts or containers"""

    arguments = dict(
        public=ValueArgument('publish new object', '--public'),
        content_type=ValueArgument(
            'change object\'s content type', '--content-type'),
        source_version=ValueArgument(
            'The version of the source object', '--object-version')
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
                    source_account=self.client.account,
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


@command(file_cmds)
class file_append(_pithos_container, _optional_output_cmd):
    """Append local file to (existing) remote object
    The remote object should exist.
    If the remote object is a directory, it is transformed into a file.
    In the later case, objects under the directory remain intact.
    """

    arguments = dict(
        progress_bar=ProgressBarArgument(
            'do not show progress bar', ('-N', '--no-progress-bar'),
            default=False),
        max_threads=IntArgument('default: 1', '--threads'),
    )

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    @errors.pithos.object_path
    def _run(self, local_path):
        if self['max_threads'] > 0:
            self.client.MAX_THREADS = int(self['max_threads'])
        (progress_bar, upload_cb) = self._safe_progress_bar('Appending')
        try:
            with open(local_path, 'rb') as f:
                self._optional_output(
                    self.client.append_object(self.path, f, upload_cb))
        finally:
            self._safe_progress_bar_finish(progress_bar)

    def main(self, local_path, remote_path_or_url):
        super(self.__class__, self)._run(remote_path_or_url)
        self._run(local_path)


@command(file_cmds)
class file_truncate(_pithos_container, _optional_output_cmd):
    """Truncate remote file up to size"""

    arguments = dict(
        size_in_bytes=IntArgument('Length of file after truncation', '--size')
    )
    required = ('size_in_bytes', )

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    @errors.pithos.object_path
    @errors.pithos.object_size
    def _run(self, size):
        self._optional_output(self.client.truncate_object(self.path, size))

    def main(self, path_or_url):
        super(self.__class__, self)._run(path_or_url)
        self._run(size=self['size_in_bytes'])


@command(file_cmds)
class file_overwrite(_pithos_container, _optional_output_cmd):
    """Overwrite part of a remote file"""

    arguments = dict(
        progress_bar=ProgressBarArgument(
            'do not show progress bar', ('-N', '--no-progress-bar'),
            default=False),
        start_position=IntArgument('File position in bytes', '--from'),
        end_position=IntArgument('File position in bytes', '--to')
    )
    required = ('start_position', 'end_position')

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    @errors.pithos.object_path
    @errors.pithos.object_size
    def _run(self, local_path, start, end):
        start, end = int(start), int(end)
        (progress_bar, upload_cb) = self._safe_progress_bar(
            'Overwrite %s bytes' % (end - start))
        try:
            with open(path.abspath(local_path), 'rb') as f:
                self._optional_output(self.client.overwrite_object(
                    obj=self.path,
                    start=start,
                    end=end,
                    source_file=f,
                    upload_cb=upload_cb))
        finally:
            self._safe_progress_bar_finish(progress_bar)

    def main(self, local_path, path_or_url):
        super(self.__class__, self)._run(path_or_url)
        self.path = self.path or path.basename(local_path)
        self._run(
            local_path=local_path,
            start=self['start_position'],
            end=self['end_position'])


@command(file_cmds)
class file_upload(_pithos_container, _optional_output_cmd):
    """Upload a file"""

    arguments = dict(
        max_threads=IntArgument('default: 5', '--threads'),
        content_encoding=ValueArgument(
            'set MIME content type', '--content-encoding'),
        content_disposition=ValueArgument(
            'specify objects presentation style', '--content-disposition'),
        content_type=ValueArgument('specify content type', '--content-type'),
        uuid_for_read_permission=RepeatableArgument(
            'Give read access to a user or group (can be repeated) '
            'Use * for all users',
            '--read-permission'),
        uuid_for_write_permission=RepeatableArgument(
            'Give write access to a user or group (can be repeated) '
            'Use * for all users',
            '--write-permission'),
        public=FlagArgument('make object publicly accessible', '--public'),
        progress_bar=ProgressBarArgument(
            'do not show progress bar',
            ('-N', '--no-progress-bar'),
            default=False),
        overwrite=FlagArgument('Force (over)write', ('-f', '--force')),
        recursive=FlagArgument(
            'Recursively upload directory *contents* + subdirectories',
            ('-r', '--recursive')),
        unchunked=FlagArgument(
            'Upload file as one block (not recommended)', '--unchunked'),
        md5_checksum=ValueArgument(
            'Confirm upload with a custom checksum (MD5)', '--etag'),
        use_hashes=FlagArgument(
            'Source file contains hashmap not data', '--source-is-hashmap'),
    )

    def _sharing(self):
        sharing = dict()
        readlist = self['uuid_for_read_permission']
        if readlist:
            sharing['read'] = self['uuid_for_read_permission']
        writelist = self['uuid_for_write_permission']
        if writelist:
            sharing['write'] = self['uuid_for_write_permission']
        return sharing or None

    def _check_container_limit(self, path):
        cl_dict = self.client.get_container_limit()
        container_limit = int(cl_dict['x-container-policy-quota'])
        r = self.client.container_get()
        used_bytes = sum(int(o['bytes']) for o in r.json)
        path_size = get_path_size(path)
        if container_limit and path_size > (container_limit - used_bytes):
            raise CLIError(
                'Container %s (limit(%s) - used(%s)) < (size(%s) of %s)' % (
                    self.client.container,
                    format_size(container_limit),
                    format_size(used_bytes),
                    format_size(path_size),
                    path),
                details=[
                    'Check accound limit: /file quota',
                    'Check container limit:',
                    '\t/file containerlimit get %s' % self.client.container,
                    'Increase container limit:',
                    '\t/file containerlimit set <new limit> %s' % (
                        self.client.container)])

    def _src_dst(self, local_path, remote_path, objlist=None):
        lpath = path.abspath(local_path)
        short_path = path.basename(path.abspath(local_path))
        rpath = remote_path or short_path
        if path.isdir(lpath):
            if not self['recursive']:
                raise CLIError('%s is a directory' % lpath, details=[
                    'Use %s to upload directories & contents' % (
                        self.arguments['recursive'].lvalue)])
            robj = self.client.container_get(path=rpath)
            if not self['overwrite']:
                if robj.json:
                    raise CLIError(
                        'Objects/files prefixed as %s already exist' % rpath,
                        details=['Existing objects:'] + ['\t/%s/\t%s' % (
                            o['name'],
                            o['content_type'][12:]) for o in robj.json] + [
                            'Use -f to add, overwrite or resume'])
                else:
                    try:
                        topobj = self.client.get_object_info(rpath)
                        if not self._is_dir(topobj):
                            raise CLIError(
                                'Object /%s/%s exists but not a directory' % (
                                    self.container, rpath),
                                details=['Use -f to overwrite'])
                    except ClientError as ce:
                        if ce.status not in (404, ):
                            raise
            self._check_container_limit(lpath)
            prev = ''
            for top, subdirs, files in walk(lpath):
                if top != prev:
                    prev = top
                    try:
                        rel_path = rpath + top.split(lpath)[1]
                    except IndexError:
                        rel_path = rpath
                    self.error('mkdir /%s/%s' % (
                        self.client.container, rel_path))
                    self.client.create_directory(rel_path)
                for f in files:
                    fpath = path.join(top, f)
                    if path.isfile(fpath):
                        rel_path = rel_path.replace(path.sep, '/')
                        pathfix = f.replace(path.sep, '/')
                        yield open(fpath, 'rb'), '%s/%s' % (rel_path, pathfix)
                    else:
                        self.error('%s is not a regular file' % fpath)
        else:
            if not path.isfile(lpath):
                raise CLIError(('%s is not a regular file' % lpath) if (
                    path.exists(lpath)) else '%s does not exist' % lpath)
            try:
                robj = self.client.get_object_info(rpath)
                if remote_path and self._is_dir(robj):
                    rpath += '/%s' % (short_path.replace(path.sep, '/'))
                    self.client.get_object_info(rpath)
                if not self['overwrite']:
                    raise CLIError(
                        'Object /%s/%s already exists' % (
                            self.container, rpath),
                        details=['use -f to overwrite / resume'])
            except ClientError as ce:
                if ce.status not in (404, ):
                    raise
            self._check_container_limit(lpath)
            yield open(lpath, 'rb'), rpath

    def _run(self, local_path, remote_path):
        self.client.MAX_THREADS = int(self['max_threads'] or 5)
        params = dict(
            content_encoding=self['content_encoding'],
            content_type=self['content_type'],
            content_disposition=self['content_disposition'],
            sharing=self._sharing(),
            public=self['public'])
        uploaded, container_info_cache = list, dict()
        rpref = 'pithos://%s' if self['account'] else ''
        for f, rpath in self._src_dst(local_path, remote_path):
            self.error('%s --> %s/%s/%s' % (
                f.name, rpref, self.client.container, rpath))
            if not (self['content_type'] and self['content_encoding']):
                ctype, cenc = guess_mime_type(f.name)
                params['content_type'] = self['content_type'] or ctype
                params['content_encoding'] = self['content_encoding'] or cenc
            if self['unchunked']:
                r = self.client.upload_object_unchunked(
                    rpath, f,
                    etag=self['md5_checksum'], withHashFile=self['use_hashes'],
                    **params)
                if self['with_output'] or self['json_output']:
                    r['name'] = '/%s/%s' % (self.client.container, rpath)
                    uploaded.append(r)
            else:
                try:
                    (progress_bar, upload_cb) = self._safe_progress_bar(
                        'Uploading %s' % f.name.split(path.sep)[-1])
                    if progress_bar:
                        hash_bar = progress_bar.clone()
                        hash_cb = hash_bar.get_generator(
                            'Calculating block hashes')
                    else:
                        hash_cb = None
                    r = self.client.upload_object(
                        rpath, f,
                        hash_cb=hash_cb,
                        upload_cb=upload_cb,
                        container_info_cache=container_info_cache,
                        **params)
                    if self['with_output'] or self['json_output']:
                        r['name'] = '/%s/%s' % (self.client.container, rpath)
                        uploaded.append(r)
                except Exception:
                    self._safe_progress_bar_finish(progress_bar)
                    raise
                finally:
                    self._safe_progress_bar_finish(progress_bar)
        self._optional_output(uploaded)
        self.error('Upload completed')

    def main(self, local_path, remote_path_or_url):
        super(self.__class__, self)._run(remote_path_or_url)
        remote_path = self.path or path.basename(path.abspath(local_path))
        self._run(local_path=local_path, remote_path=remote_path)


class RangeArgument(ValueArgument):
    """
    :value type: string of the form <start>-<end> where <start> and <end> are
        integers
    :value returns: the input string, after type checking <start> and <end>
    """

    @property
    def value(self):
        return getattr(self, '_value', self.default)

    @value.setter
    def value(self, newvalues):
        if newvalues:
            self._value = getattr(self, '_value', self.default)
            for newvalue in newvalues.split(','):
                self._value = ('%s,' % self._value) if self._value else ''
                start, sep, end = newvalue.partition('-')
                if sep:
                    if start:
                        start, end = (int(start), int(end))
                        if start > end:
                            raise CLIInvalidArgument(
                                'Invalid range %s' % newvalue, details=[
                                'Valid range formats',
                                '  START-END', '  UP_TO', '  -FROM',
                                'where all values are integers',
                                'OR a compination (csv), e.g.,',
                                '  %s=5,10-20,-5' % self.lvalue])
                        self._value += '%s-%s' % (start, end)
                    else:
                        self._value += '-%s' % int(end)
                else:
                    self._value += '%s' % int(start)


@command(file_cmds)
class file_cat(_pithos_container):
    """Fetch remote file contents"""

    arguments = dict(
        range=RangeArgument('show range of data e.g., 5,10-20,-5', '--range'),
        if_match=ValueArgument('show output if ETags match', '--if-match'),
        if_none_match=ValueArgument(
            'show output if ETags match', '--if-none-match'),
        if_modified_since=DateArgument(
            'show output modified since then', '--if-modified-since'),
        if_unmodified_since=DateArgument(
            'show output unmodified since then', '--if-unmodified-since'),
        object_version=ValueArgument(
            'Get contents of the chosen version', '--object-version')
    )

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    @errors.pithos.object_path
    def _run(self):
        r = self.client.download_object(
            self.path, self._out,
            range_str=self['range'],
            version=self['object_version'],
            if_match=self['if_match'],
            if_none_match=self['if_none_match'],
            if_modified_since=self['if_modified_since'],
            if_unmodified_since=self['if_unmodified_since'])
        print r

    def main(self, path_or_url):
        super(self.__class__, self)._run(path_or_url)
        self._run()


@command(file_cmds)
class file_download(_pithos_container):
    """Download a remove file or directory object to local file system"""

    arguments = dict(
        resume=FlagArgument(
            'Resume/Overwrite (attempt resume, else overwrite)',
            ('-f', '--resume')),
        range=RangeArgument(
            'Download only that range of data e.g., 5,10-20,-5', '--range'),
        matching_etag=ValueArgument('download iff ETag match', '--if-match'),
        non_matching_etag=ValueArgument(
            'download iff ETags DO NOT match', '--if-none-match'),
        modified_since_date=DateArgument(
            'download iff remote file is modified since then',
            '--if-modified-since'),
        unmodified_since_date=DateArgument(
            'show output iff remote file is unmodified since then',
            '--if-unmodified-since'),
        object_version=ValueArgument(
            'download a file of a specific version', '--object-version'),
        max_threads=IntArgument('default: 5', '--threads'),
        progress_bar=ProgressBarArgument(
            'do not show progress bar', ('-N', '--no-progress-bar'),
            default=False),
        recursive=FlagArgument(
            'Download a remote directory object and its contents',
            ('-r', '--recursive'))
        )

    def _src_dst(self, local_path):
        """Create a list of (src, dst) where src is a remote location and dst
        is an open file descriptor. Directories are denoted as (None, dirpath)
        and they are pretended to other objects in a very strict order (shorter
        to longer path)."""
        ret = []
        try:
            if self.path:
                obj = self.client.get_object_info(
                    self.path, version=self['object_version'])
                obj.setdefault('name', self.path.strip('/'))
            else:
                obj = None
        except ClientError as ce:
            if ce.status in (404, ):
                raiseCLIError(ce, details=[
                    'To download an object, it must exist either as a file or'
                    ' as a directory.',
                    'For example, to download everything under prefix/ the '
                    'directory "prefix" must exist.',
                    'To see if an remote object is actually there:',
                    '  /file info [/CONTAINER/]OBJECT',
                    'To create a directory object:',
                    '  /file mkdir [/CONTAINER/]OBJECT'])
            if ce.status in (204, ):
                raise CLIError(
                    'No file or directory objects to download',
                    details=[
                        'To download a container (e.g., %s):' % self.container,
                        '  [kamaki] container download %s [LOCAL_PATH]' % (
                            self.container)])
            raise
        rpath = self.path.strip('/')
        if local_path and self.path and local_path.endswith('/'):
            local_path = local_path[-1:]

        if (not obj) or self._is_dir(obj):
            if self['recursive']:
                if not (self.path or local_path.endswith('/')):
                    #  Download the whole container
                    local_path = '' if local_path in ('.', ) else local_path
                    local_path = '%s/' % (local_path or self.container)
                obj = obj or dict(
                    name='', content_type='application/directory')
                dirs, files = [obj, ], []
                objects = self.client.container_get(
                    path=self.path,
                    if_modified_since=self['modified_since_date'],
                    if_unmodified_since=self['unmodified_since_date'])
                for o in objects.json:
                    (dirs if self._is_dir(o) else files).append(o)

                #  Put the directories on top of the list
                for dpath in sorted(['%s%s' % (
                        local_path, d['name'][len(rpath):]) for d in dirs]):
                    if path.exists(dpath):
                        if path.isdir(dpath):
                            continue
                        raise CLIError(
                            'Cannot replace local file %s with a directory '
                            'of the same name' % dpath,
                            details=[
                                'Either remove the file or specify a'
                                'different target location'])
                    ret.append((None, dpath, None))

                #  Append the file objects
                for opath in [o['name'] for o in files]:
                    lpath = '%s%s' % (local_path, opath[len(rpath):])
                    if self['resume']:
                        fxists = path.exists(lpath)
                        if fxists and path.isdir(lpath):
                            raise CLIError(
                                'Cannot change local dir %s info file' % (
                                    lpath),
                                details=[
                                    'Either remove the file or specify a'
                                    'different target location'])
                        ret.append((opath, lpath, fxists))
                    elif path.exists(lpath):
                        raise CLIError(
                            'Cannot overwrite %s' % lpath,
                            details=['To overwrite/resume, use  %s' % (
                                self.arguments['resume'].lvalue)])
                    else:
                        ret.append((opath, lpath, None))
            elif self.path:
                raise CLIError(
                    'Remote object /%s/%s is a directory' % (
                        self.container, local_path),
                    details=['Use %s to download directories' % (
                        self.arguments['recursive'].lvalue)])
            else:
                parsed_name = self.arguments['recursive'].lvalue
                raise CLIError(
                    'Cannot download container %s' % self.container,
                    details=[
                        'Use %s to download containers' % parsed_name,
                        '  [kamaki] file download %s /%s [LOCAL_PATH]' % (
                            parsed_name, self.container)])
        else:
            #  Remote object is just a file
            if path.exists(local_path):
                if not self['resume']:
                    raise CLIError(
                        'Cannot overwrite local file %s' % (local_path),
                        details=['To overwrite/resume, use  %s' % (
                            self.arguments['resume'].lvalue)])
            elif '/' in local_path[1:-1]:
                dirs = [p for p in local_path.split('/') if p]
                pref = '/' if local_path.startswith('/') else ''
                for d in dirs[:-1]:
                    pref += d
                    if not path.exists(pref):
                        ret.append((None, d, None))
                    elif not path.isdir(pref):
                        raise CLIError(
                            'Failed to use %s as a destination' % local_path,
                            importance=3,
                            details=[
                                'Local file %s is not a directory' % pref,
                                'Destination prefix must consist of '
                                'directories or non-existing names',
                                'Either remove the file, or choose another '
                                'destination'])
            ret.append((rpath, local_path, self['resume']))
        for r, l, resume in ret:
            if r:
                with open(l, 'rwb+' if resume else 'wb+') as f:
                    yield (r, f)
            else:
                yield (r, l)

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    @errors.pithos.object_path
    @errors.pithos.local_path
    @errors.pithos.local_path_download
    def _run(self, local_path):
        self.client.MAX_THREADS = int(self['max_threads'] or 5)
        progress_bar = None
        try:
            for rpath, output_file in self._src_dst(local_path):
                if not rpath:
                    self.error('Create local directory %s' % output_file)
                    makedirs(output_file)
                    continue
                self.error('/%s/%s --> %s' % (
                    self.container, rpath, output_file.name))
                progress_bar, download_cb = self._safe_progress_bar(
                    '  download')
                self.client.download_object(
                    rpath, output_file,
                    download_cb=download_cb,
                    range_str=self['range'],
                    version=self['object_version'],
                    if_match=self['matching_etag'],
                    resume=self['resume'],
                    if_none_match=self['non_matching_etag'],
                    if_modified_since=self['modified_since_date'],
                    if_unmodified_since=self['unmodified_since_date'])
        except KeyboardInterrupt:
            from threading import activeCount, enumerate as activethreads
            timeout = 0.5
            while activeCount() > 1:
                self._out.write('\nCancel %s threads: ' % (activeCount() - 1))
                self._out.flush()
                for thread in activethreads():
                    try:
                        thread.join(timeout)
                        self._out.write('.' if thread.isAlive() else '*')
                    except RuntimeError:
                        continue
                    finally:
                        self._out.flush()
                        timeout += 0.1
            self.error('\nDownload canceled by user')
            if local_path is not None:
                self.error('to resume, re-run with --resume')
        finally:
            self._safe_progress_bar_finish(progress_bar)

    def main(self, remote_path_or_url, local_path=None):
        super(self.__class__, self)._run(remote_path_or_url)
        local_path = local_path or self.path or '.'
        self._run(local_path=local_path)


@command(container_cmds)
class container_info(_pithos_account, _optional_json):
    """Get information about a container"""

    arguments = dict(
        until_date=DateArgument('show metadata until then', '--until'),
        metadata=FlagArgument('Show only container metadata', '--metadata'),
        sizelimit=FlagArgument(
            'Show the maximum size limit for container', '--size-limit'),
        in_bytes=FlagArgument('Show size limit in bytes', ('-b', '--bytes'))
    )

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    @errors.pithos.object_path
    def _run(self):
        if self['metadata']:
            r, preflen = dict(), len('x-container-meta-')
            for k, v in self.client.get_container_meta(
                    until=self['until_date']).items():
                r[k[preflen:]] = v
        elif self['sizelimit']:
            r = self.client.get_container_limit(
                self.container)['x-container-policy-quota']
            r = {'size limit': 'unlimited' if r in ('0', ) else (
                int(r) if self['in_bytes'] else format_size(r))}
        else:
            r = self.client.get_container_info(self.container)
        self._print(r, self.print_dict)

    def main(self, container):
        super(self.__class__, self)._run()
        self.container, self.client.container = container, container
        self._run()


class VersioningArgument(ValueArgument):

    schemes = ('auto', 'none')

    @property
    def value(self):
        return getattr(self, '_value', None)

    @value.setter
    def value(self, new_scheme):
        if new_scheme:
            new_scheme = new_scheme.lower()
            if new_scheme not in self.schemes:
                raise CLIInvalidArgument('Invalid versioning value', details=[
                    'Valid versioning values are %s' % ', '.join(
                        self.schemes)])
            self._value = new_scheme


@command(container_cmds)
class container_modify(_pithos_account, _optional_json):
    """Modify the properties of a container"""

    arguments = dict(
        metadata_to_add=KeyValueArgument(
            'Add metadata in the form KEY=VALUE (can be repeated)',
            '--metadata-add'),
        metadata_to_delete=RepeatableArgument(
            'Delete metadata by KEY (can be repeated)', '--metadata-del'),
        sizelimit=DataSizeArgument(
            'Set max size limit (0 for unlimited, '
            'use units B, KiB, KB, etc.)', '--size-limit'),
        versioning=VersioningArgument(
            'Set a versioning scheme (%s)' % ', '.join(
                VersioningArgument.schemes), '--versioning')
    )
    required = [
        'metadata_to_add', 'metadata_to_delete', 'sizelimit', 'versioning']

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    def _run(self, container):
        metadata = self['metadata_to_add']
        for k in (self['metadata_to_delete'] or []):
            metadata[k] = ''
        if metadata:
            self.client.set_container_meta(metadata)
            self._print(self.client.get_container_meta(), self.print_dict)
        if self['sizelimit'] is not None:
            self.client.set_container_limit(self['sizelimit'])
            r = self.client.get_container_limit()['x-container-policy-quota']
            r = 'unlimited' if r in ('0', ) else format_size(r)
            self.writeln('new size limit: %s' % r)
        if self['versioning']:
            self.client.set_container_versioning(self['versioning'])
            self.writeln('new versioning scheme: %s' % (
                self.client.get_container_versioning(self.container)[
                    'x-container-policy-versioning']))

    def main(self, container):
        super(self.__class__, self)._run()
        self.client.container, self.container = container, container
        self._run(container=container)


@command(container_cmds)
class container_list(_pithos_account, _optional_json, _name_filter):
    """List all containers, or their contents"""

    arguments = dict(
        detail=FlagArgument('Containers with details', ('-l', '--list')),
        limit=IntArgument('limit number of listed items', ('-n', '--number')),
        marker=ValueArgument('output greater that marker', '--marker'),
        modified_since_date=ValueArgument(
            'show output modified since then', '--if-modified-since'),
        unmodified_since_date=ValueArgument(
            'show output not modified since then', '--if-unmodified-since'),
        until_date=DateArgument('show metadata until then', '--until'),
        shared=FlagArgument('show only shared', '--shared'),
        more=FlagArgument('read long results', '--more'),
        enum=FlagArgument('Enumerate results', '--enumerate'),
        recursive=FlagArgument(
            'Recursively list containers and their contents',
            ('-r', '--recursive')),
        shared_by_me=FlagArgument(
            'show only files shared to other users', '--shared-by-me'),
        public=FlagArgument('show only published objects', '--public'),
    )

    def print_containers(self, container_list):
        for index, container in enumerate(container_list):
            if 'bytes' in container:
                size = format_size(container['bytes'])
            prfx = ('%s. ' % (index + 1)) if self['enum'] else ''
            _cname = container['name'] if (
                self['more']) else bold(container['name'])
            cname = u'%s%s' % (prfx, _cname)
            if self['detail']:
                self.writeln(cname)
                pretty_c = container.copy()
                if 'bytes' in container:
                    pretty_c['bytes'] = '%s (%s)' % (container['bytes'], size)
                self.print_dict(pretty_c, exclude=('name'))
                self.writeln()
            else:
                if 'count' in container and 'bytes' in container:
                    self.writeln('%s (%s, %s objects)' % (
                        cname, size, container['count']))
                else:
                    self.writeln(cname)
            objects = container.get('objects', [])
            if objects:
                self.print_objects(objects)
                self.writeln('')

    def _create_object_forest(self, container_list):
        try:
            for container in container_list:
                self.client.container = container['name']
                objects = self.client.container_get(
                    limit=False if self['more'] else self['limit'],
                    if_modified_since=self['modified_since_date'],
                    if_unmodified_since=self['unmodified_since_date'],
                    until=self['until_date'],
                    show_only_shared=self['shared_by_me'],
                    public=self['public'])
                container['objects'] = objects.json
        finally:
            self.client.container = None

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.object_path
    @errors.pithos.container
    def _run(self, container):
        if container:
            r = self.client.container_get(
                limit=False if self['more'] else self['limit'],
                marker=self['marker'],
                if_modified_since=self['modified_since_date'],
                if_unmodified_since=self['unmodified_since_date'],
                until=self['until_date'],
                show_only_shared=self['shared_by_me'],
                public=self['public'])
        else:
            r = self.client.account_get(
                limit=False if self['more'] else self['limit'],
                marker=self['marker'],
                if_modified_since=self['modified_since_date'],
                if_unmodified_since=self['unmodified_since_date'],
                until=self['until_date'],
                show_only_shared=self['shared_by_me'],
                public=self['public'])
        files = self._filter_by_name(r.json)
        if self['recursive'] and not container:
            self._create_object_forest(files)
        if self['more']:
            outbu, self._out = self._out, StringIO()
        try:
            if self['json_output'] or self['output_format']:
                self._print(files)
            else:
                (self.print_objects if container else self.print_containers)(
                    files)
        finally:
            if self['more']:
                pager(self._out.getvalue())
                self._out = outbu

    def main(self, container=None):
        super(self.__class__, self)._run()
        self.client.container, self.container = container, container
        self._run(container)


@command(container_cmds)
class container_create(_pithos_account):
    """Create a new container"""

    arguments = dict(
        versioning=ValueArgument(
            'set container versioning (auto/none)', '--versioning'),
        limit=IntArgument('set default container limit', '--limit'),
        meta=KeyValueArgument(
            'set container metadata (can be repeated)', '--meta')
    )

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    def _run(self, container):
        try:
            self.client.create_container(
                container=container,
                sizelimit=self['limit'],
                versioning=self['versioning'],
                metadata=self['meta'],
                success=(201, ))
        except ClientError as ce:
            if ce.status in (202, ):
                raise CLIError(
                    'Container %s alread exists' % container, details=[
                    'Either delete %s or choose another name' % (container)])
            raise

    def main(self, new_container):
        super(self.__class__, self)._run()
        self._run(container=new_container)


@command(container_cmds)
class container_delete(_pithos_account):
    """Delete a container"""

    arguments = dict(
        yes=FlagArgument('Do not prompt for permission', '--yes'),
        recursive=FlagArgument(
            'delete container even if not empty', ('-r', '--recursive'))
    )

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    def _run(self, container):
        num_of_contents = int(self.client.get_container_info(container)[
            'x-container-object-count'])
        delimiter, msg = None, 'Delete container %s ?' % container
        if self['recursive']:
            delimiter, msg = '/', 'Empty and d%s' % msg[1:]
        elif num_of_contents:
            raise CLIError('Container %s is not empty' % container, details=[
                'Use %s to delete non-empty containers' % (
                    self.arguments['recursive'].lvalue)])
        if self['yes'] or self.ask_user(msg):
            if num_of_contents:
                self.client.del_container(delimiter=delimiter)
            self.client.purge_container()

    def main(self, container):
        super(self.__class__, self)._run()
        self.container, self.client.container = container, container
        self._run(container)


@command(container_cmds)
class container_empty(_pithos_account):
    """Empty a container"""

    arguments = dict(yes=FlagArgument('Do not prompt for permission', '--yes'))

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    def _run(self, container):
        if self['yes'] or self.ask_user('Empty container %s ?' % container):
            self.client.del_container(delimiter='/')

    def main(self, container):
        super(self.__class__, self)._run()
        self.container, self.client.container = container, container
        self._run(container)


@command(sharer_cmds)
class sharer_list(_pithos_account, _optional_json):
    """List accounts who share file objects with current user"""

    arguments = dict(
        detail=FlagArgument('show detailed output', ('-l', '--details')),
        marker=ValueArgument('show output greater then marker', '--marker')
    )

    @errors.generic.all
    @errors.pithos.connection
    def _run(self):
        accounts = self.client.get_sharing_accounts(marker=self['marker'])
        if not (self['json_output'] or self['output_format']):
            usernames = self._uuids2usernames(
                [acc['name'] for acc in accounts])
            for item in accounts:
                uuid = item['name']
                item['id'], item['name'] = uuid, usernames[uuid]
                if not self['detail']:
                    item.pop('last_modified')
        self._print(accounts)

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(sharer_cmds)
class sharer_info(_pithos_account, _optional_json):
    """Details on a Pithos+ sharer account (default: current account)"""

    @errors.generic.all
    @errors.pithos.connection
    def _run(self):
        self._print(self.client.get_account_info(), self.print_dict)

    def main(self, account_uuid=None):
        super(self.__class__, self)._run()
        if account_uuid:
            self.client.account, self.account = account_uuid, account_uuid
        self._run()


class _pithos_group(_pithos_account):
    prefix = 'x-account-group-'
    preflen = len(prefix)

    def _groups(self):
        groups = dict()
        for k, v in self.client.get_account_group().items():
            groups[k[self.preflen:]] = v
        return groups


@command(group_cmds)
class group_list(_pithos_group, _optional_json):
    """list all groups and group members"""

    @errors.generic.all
    @errors.pithos.connection
    def _run(self):
        self._print(self._groups(), self.print_dict)

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(group_cmds)
class group_create(_pithos_group, _optional_json):
    """Create a group of users"""

    arguments = dict(
        user_uuid=RepeatableArgument('Add a user to the group', '--uuid'),
        username=RepeatableArgument('Add a user to the group', '--username')
    )
    required = ['user_uuid', 'username']

    @errors.generic.all
    @errors.pithos.connection
    def _run(self, groupname, *users):
        if groupname in self._groups() and not self.ask_user(
                'Group %s already exists, overwrite?' % groupname):
            self.error('Aborted')
            return
        self.client.set_account_group(groupname, users)
        self._print(self._groups(), self.print_dict)

    def main(self, groupname):
        super(self.__class__, self)._run()
        users = (self['user_uuid'] or []) + self._usernames2uuids(
            self['username'] or []).values()
        if users:
            self._run(groupname, *users)
        else:
            raise CLISyntaxError(
                'No valid users specified, use %s or %s' % (
                    self.arguments['user_uuid'].lvalue,
                    self.arguments['username'].lvalue),
                details=[
                    'Check if a username or uuid is valid with',
                    '  user uuid2username', 'OR', '  user username2uuid'])


@command(group_cmds)
class group_delete(_pithos_group, _optional_json):
    """Delete a user group"""

    @errors.generic.all
    @errors.pithos.connection
    def _run(self, groupname):
        self.client.del_account_group(groupname)
        self._print(self._groups(), self.print_dict)

    def main(self, groupname):
        super(self.__class__, self)._run()
        self._run(groupname)


#  Deprecated commands

@command(file_cmds)
class file_publish(_pithos_init):
    """DEPRECATED, replaced by [kamaki] file modify OBJECT --publish"""

    def main(self, *args):
        raise CLISyntaxError('DEPRECATED', details=[
            'This command is replaced by:',
            '  [kamaki] file modify OBJECT --publish'])


@command(file_cmds)
class file_unpublish(_pithos_init):
    """DEPRECATED, replaced by [kamaki] file modify OBJECT --unpublish"""

    def main(self, *args):
        raise CLISyntaxError('DEPRECATED', details=[
            'This command is replaced by:',
            '  [kamaki] file modify OBJECT --unpublish'])
