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

from time import localtime, strftime
from io import StringIO
from pydoc import pager
from os import path, walk, makedirs
from threading import activeCount, enumerate as activethreads

from kamaki.clients.pithos import PithosClient, ClientError
from kamaki.clients.utils import escape_ctrl_chars

from kamaki.cli import command
from kamaki.cli.cmdtree import CommandTree
from kamaki.cli.cmds import (
    CommandInit, dont_raise, OptionalOutput, NameFilter, errors, client_log)
from kamaki.cli.errors import (
    CLIBaseUrlError, CLIError, CLIInvalidArgument, raiseCLIError,
    CLISyntaxError)
from kamaki.cli.argument import (
    FlagArgument, IntArgument, ValueArgument, DateArgument, KeyValueArgument,
    ProgressBarArgument, RepeatableArgument, DataSizeArgument,
    UserAccountArgument)
from kamaki.cli.utils import format_size, get_path_size, guess_mime_type, bold

file_cmds = CommandTree('file', 'Pithos+/Storage object level API commands')
container_cmds = CommandTree(
    'container', 'Pithos+/Storage container level API commands')
sharer_cmds = CommandTree('sharer', 'Pithos+/Storage sharers')
group_cmds = CommandTree('group', 'Pithos+/Storage user groups')
namespaces = [file_cmds, container_cmds, sharer_cmds, group_cmds]


class _PithosInit(CommandInit):
    """Initilize a pithos+ client
    There is always a default account (current user uuid)
    There is always a default container (pithos)
    """

    @dont_raise(KeyError)
    def _custom_container(self):
        return self.config.get_cloud(self.cloud, 'pithos_container')

    @dont_raise(KeyError)
    def _custom_uuid(self):
        return self.config.get_cloud(self.cloud, 'pithos_uuid')

    def _set_account(self):
        self.account = self._custom_uuid()
        if self.account:
            return
        astakos = getattr(self, 'astakos', None)
        if astakos:
            self.account = astakos.user_term('id', self.token)
        else:
            raise CLIBaseUrlError(service='astakos')

    @errors.Generic.all
    @client_log
    def _run(self):
        self.client = self.get_client(PithosClient, 'pithos')
        self.endpoint_url = self.client.endpoint_url
        self.token = self.client.token
        self._set_account()
        self.client.account = self.account
        self.container = self._custom_container() or 'pithos'
        self.client.container = self.container

    def main(self):
        self._run()


class _PithosAccount(_PithosInit):
    """Setup account"""

    def __init__(self, arguments={}, astakos=None, cloud=None):
        super(_PithosAccount, self).__init__(arguments, astakos, cloud)
        self['account'] = UserAccountArgument(
            'A user UUID or name', ('-A', '--account'))
        self.arguments['account'].account_client = astakos

    def print_objects(self, object_list):
        for index, obj in enumerate(object_list):
            pretty_obj = obj.copy()
            index += 1
            empty_space = ' ' * (len(str(len(object_list))) - len(str(index)))
            if 'subdir' in obj:
                continue
            if self.object_is_dir(obj):
                size = 'D'
            else:
                size = format_size(obj['bytes'])
                pretty_obj['bytes'] = '%s (%s)' % (obj['bytes'], size)
            oname = escape_ctrl_chars(obj['name'])
            oname = oname if self['more'] else bold(oname)
            prfx = ('%s%s. ' % (empty_space, index)) if self['enum'] else ''
            if self['detail']:
                self.writeln('%s%s' % (prfx, oname))
                self.print_dict(pretty_obj, exclude=('name'))
                self.writeln()
            else:
                oname = '%s%9s %s' % (prfx, size, oname)
                oname += '/' if self.object_is_dir(obj) else u''
                self.writeln(oname)

    @staticmethod
    def object_is_dir(remote_dict):
        """:returns: True if the content type of the object is
            'applcation/directory' or 'application/folder'
        """
        content_type = remote_dict.get(
            'content_type', remote_dict.get('content-type', ''))
        dir_types = ['application/directory', 'application/folder']
        return any([t in content_type for t in dir_types])

    def _run(self):
        super(_PithosAccount, self)._run()
        self.client.account = self['account'] or getattr(
            self, 'account', getattr(self.client, 'account', None))


class _PithosContainer(_PithosAccount):
    """Setup container"""

    def __init__(self, arguments={}, astakos=None, cloud=None):
        super(_PithosContainer, self).__init__(arguments, astakos, cloud)
        self['container'] = ValueArgument(
            'Use this container (default: pithos)', ('-C', '--container'))

    @staticmethod
    def resolve_pithos_url(url):
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

    @errors.Pithos.container
    def _container_exists(self, container=None):
        bu_cont = self.container
        container = container or self.container
        try:
            self.client.get_container_info(container)
        finally:
            self.container = bu_cont

    def _run(self, url=None):
        acc, con, self.path = self.resolve_pithos_url(url or '')
        super(_PithosContainer, self)._run()
        self.container = con or self['container'] or getattr(
            self, 'container', None) or getattr(self.client, 'container', '')
        self.client.account = acc or self.client.account
        self.client.container = self.container


@command(file_cmds)
class file_info(_PithosContainer, OptionalOutput):
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

    @errors.Generic.all
    @errors.Pithos.connection
    @errors.Pithos.object_path
    def _run(self):
        try:
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
        except ClientError as ce:
            if ce.status in (404, ):
                self._container_exists()
            raise
        self.print_(r, self.print_dict)

    def main(self, path_or_url):
        super(self.__class__, self)._run(path_or_url)
        self._run()


@command(file_cmds)
class file_list(_PithosContainer, OptionalOutput, NameFilter):
    """List all objects in a container or a directory"""

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
            ('-r', '--recursive'))
    )

    @errors.Pithos.container
    def _container_info(self):
        r = self.client.container_get(
            limit=False if self['more'] else self['limit'],
            marker=self['marker'],
            prefix=self.path,
            delimiter=self['delimiter'],
            path=self['name_pref'] or '',
            show_only_shared=self['shared_by_me'],
            public=self['public'],
            if_modified_since=self['if_modified_since'],
            if_unmodified_since=self['if_unmodified_since'],
            until=self['until'],
            meta=self['meta'])
        files = list(r.json or [])
        return files

    @errors.Generic.all
    @errors.Pithos.connection
    @errors.Pithos.object_path
    def _run(self):
        r = self._container_info()
        if not r:
            if self.path:
                obj_path = '/%s/%s' % (self.container, self.path)
                obj_info = self.client.get_object_info(self.path)
                if self.object_is_dir(obj_info):
                    self.error('Directory %s is empty' % obj_path)
                else:
                    cnt_msg = '[/%s]' % self.container if (
                        'pithos' == self.container) else '/%s' % self.container
                    raise CLIError(
                        'Object %s is not a directory' % obj_path,
                        importance=2, details=[
                            'Use "list" to see contents of containers or '
                            'directories',
                            'To list all objects in container',
                            '  kamaki file list %s' % cnt_msg,
                            'To list all objects in a directory',
                            '  kamaki file list [/CONTAINER/]DIRECTORY',
                            'To get details on object',
                            '  kamaki file info %s' % obj_path])
            else:
                self.error('Container "%s" is empty' % self.client.container)

        files = self._filter_by_name(r)
        if self['more']:
            outbu, self._out = self._out, StringIO()
        try:
            if self['output_format']:
                self.print_(files)
            else:
                self.print_objects(files)
        finally:
            if self['more']:
                pager(self._out.getvalue())
                self._out = outbu

    def main(self, path_or_url=''):
        super(self.__class__, self)._run(path_or_url)
        self._run()


def _assert_path(self, path_or_url):
    if not self.path:
        raise CLISyntaxError(
            'Invalid or incomplete location %s' % path_or_url,
            details=['Location format', '[[pithos://UUID]/CONTAINER/]PATH'])


@command(file_cmds)
class file_modify(_PithosContainer):
    """Modify the attributes of a file or directory object"""

    arguments = dict(
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
        'uuid_for_read_permission', 'metadata_to_set',
        'uuid_for_write_permission', 'no_permissions',
        'metadata_key_to_delete']

    @errors.Generic.all
    @errors.Pithos.connection
    @errors.Pithos.object_path
    def _run(self):
        try:
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
        except ClientError as ce:
            if ce.status in (404, ):
                self._container_exists()
            raise

    def main(self, path_or_url):
        super(self.__class__, self)._run(path_or_url)
        if self['no_permissions'] and (
                self['uuid_for_read_permission'] or self[
                    'uuid_for_write_permission']):
            raise CLIInvalidArgument(
                '%s cannot be used with other permission arguments' % (
                    self.arguments['no_permissions'].lvalue))
        _assert_path(self, path_or_url)
        self._run()


@command(file_cmds)
class file_publish(_PithosContainer):
    """Publish an object (creates a public URL)"""

    @errors.Generic.all
    @errors.Pithos.connection
    @errors.Pithos.object_path
    def _run(self):
        try:
            self.writeln(self.client.publish_object(self.path))
        except ClientError as ce:
            if ce.status in (404, ):
                self._container_exists()
            raise

    def main(self, path_or_url):
        super(self.__class__, self)._run(path_or_url)
        self._run()


@command(file_cmds)
class file_unpublish(_PithosContainer):
    """Unpublish an object"""

    @errors.Generic.all
    @errors.Pithos.connection
    @errors.Pithos.object_path
    def _run(self):
        try:
            self.client.unpublish_object(self.path)
        except ClientError as ce:
            if ce.status in (404, ):
                self._container_exists()
            raise

    def main(self, path_or_url):
        super(self.__class__, self)._run(path_or_url)
        self._run()


@command(file_cmds)
class file_create(_PithosContainer):
    """Create an empty object"""

    arguments = dict(
        content_type=ValueArgument(
            'Set content type (default: application/octet-stream)',
            '--content-type',
            default='application/octet-stream')
    )

    @errors.Generic.all
    @errors.Pithos.connection
    @errors.Pithos.container
    def _run(self):
        self.client.create_object(self.path, self['content_type'])

    def main(self, path_or_url):
        super(self.__class__, self)._run(path_or_url)
        _assert_path(self, path_or_url)
        self._run()


@command(file_cmds)
class file_mkdir(_PithosContainer):
    """Create a directory object
    Equivalent to
    kamaki file create --content-type='application/directory'
    """

    @errors.Generic.all
    @errors.Pithos.connection
    @errors.Pithos.container
    def _run(self, path):
        self.client.create_directory(self.path)

    def main(self, path_or_url):
        super(self.__class__, self)._run(path_or_url)
        _assert_path(self, path_or_url)
        self._run(self.path)


@command(file_cmds)
class file_delete(_PithosContainer):
    """Delete a file or directory object"""

    arguments = dict(
        until_date=DateArgument('remove history until then', '--until'),
        yes=FlagArgument('Do not prompt for permission', '--yes'),
        recursive=FlagArgument(
            'If a directory, empty first', ('-r', '--recursive')),
        delimiter=ValueArgument(
            'delete objects prefixed with <object><delimiter>', '--delimiter')
    )

    @errors.Pithos.object_path
    def _delete_object(self):
        self.client.get_object_info(self.path)
        if self['yes'] or self.ask_user(
                'Delete /%s/%s ?' % (self.container, self.path)):
            # See if any objects exist under prefix
            # Add a trailing / to object's name
            prefix = self.path.rstrip('/') + '/'
            result = self.client.container_get(prefix=prefix)

            if result.json:
                count = len(result.json)
                self.error(' * %d other object(s) with %s as prefix found' % (
                    count, prefix))

                if self['recursive']:
                    msg = 'The above %d object(s) will be deleted, too' % \
                        count
                else:
                    msg = 'The above %d object(s) will be preserved,' \
                        ' but the directory structure' \
                        ' will become inconsistent' % count

                self.error(' * %s!' % msg)

            if not result.json or self.ask_user("Continue?"):
                self.client.del_object(
                    self.path,
                    until=self['until_date'],
                    delimiter='/' if self['recursive'] else self['delimiter'])
        else:
            self.error('Aborted')

    @errors.Pithos.container
    def _empty_container(self):
        self.client.get_container_info()
        if self['yes'] or self.ask_user(
                'Empty container /%s ?' % self.container):
            self.client.container_delete(self.container, delimiter='/')
        else:
            self.error('Aborted')

    @errors.Generic.all
    @errors.Pithos.connection
    def _run(self):
        if self.path:
            self._delete_object()
        else:
            self._empty_container()

    def main(self, path_or_url):
        super(self.__class__, self)._run(path_or_url)
        self._run()


class _PithosFromTo(_PithosContainer):

    sd_arguments = dict(
        destination_user=UserAccountArgument(
            'UUID or username, default: current user', '--to-account'),
        destination_container=ValueArgument(
            'default: pithos', '--to-container'),
        source_prefix=FlagArgument(
            'Transfer all files that are prefixed with SOURCE PATH . If the '
            'destination path is specified, replace SOURCE_PATH with '
            'DESTINATION_PATH',
            ('-r', '--recursive')),
        force=FlagArgument(
            'Overwrite destination objects, if needed', ('-f', '--force')),
        source_version=ValueArgument(
            'The version of the source object', '--source-version')
    )

    def __init__(self, arguments={}, astakos=None, cloud=None):
        self.arguments.update(arguments)
        self.arguments.update(self.sd_arguments)
        super(_PithosFromTo, self).__init__(
            self.arguments, astakos, cloud)
        self.arguments['destination_user'].account_client = self.astakos

    def _report_transfer(self, src, dst, transfer_name):
        if not dst:
            if transfer_name in ('move', ):
                self.error('  delete source directory %s' % src)
            return
        dst_prf = '' if self.account == self.dst_client.account else (
            'pithos://%s' % self.dst_client.account)
        full_dest_path = '%s/%s/%s' % (dst_prf, self.dst_client.container, dst)
        if src:
            src_prf = '' if self.account == self.dst_client.account else (
                'pithos://%s' % self.account)
            full_src_path = '/%s/%s/%s' % (src_prf, self.container, src)
            self.error('  %s %s  -->  %s' % (
                transfer_name, full_src_path, full_dest_path))
        else:
            self.error('  mkdir %s' % full_dest_path)

    @errors.Generic.all
    @errors.Pithos.account
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
                        self.dst_client.account, self.dst_client.container),
                    importance=2)
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
                        None if self.object_is_dir(src_obj) else src_path,
                        dst_path))
                    if self.object_is_dir(src_obj):
                        pairs.append((self.path or dst_path, None))
                elif not any([
                        self.object_is_dir(dst_obj),
                        self.object_is_dir(src_obj)]):
                    raise CLIError(
                        'Destination object exists', importance=2, details=[
                            'Failed while transfering:',
                            '    pithos://%s/%s/%s' % (
                                self.account, self.container, src_path),
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
                pairs.append((
                    None if self.object_is_dir(src_obj) else self.path,
                    dst_path))
                if self.object_is_dir(src_obj):
                    pairs.append((self.path or dst_path, None))
            elif self.object_is_dir(src_obj):
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
                            self.account, self.container, self.path),
                        '--> pithos://%s/%s/%s' % (
                            self.dst_client.account,
                            self.dst_client.container,
                            dst_path),
                        'Use %s to transfer overwrite' % (
                            self.arguments['force'].lvalue)])
        return pairs

    def _run(self, source_path_or_url, destination_path_or_url=''):
        super(_PithosFromTo, self)._run(source_path_or_url)
        dst_acc, dst_con, dst_path = self.resolve_pithos_url(
            destination_path_or_url)
        self.dst_client = PithosClient(
            endpoint_url=self.client.endpoint_url, token=self.client.token,
            container=self[
                'destination_container'] or dst_con or self.client.container,
            account=self['destination_user'] or dst_acc or self.account)
        self.dst_path = dst_path or self.path


@command(file_cmds)
class file_copy(_PithosFromTo):
    """Copy objects, even between different accounts or containers"""

    arguments = dict(
        public=ValueArgument('publish new object', '--public'),
        content_type=ValueArgument(
            'change object\'s content type', '--content-type'),
        source_version=ValueArgument(
            'The version of the source object', '--object-version')
    )

    @errors.Generic.all
    @errors.Pithos.connection
    @errors.Pithos.container
    @errors.Pithos.account
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
class file_move(_PithosFromTo):
    """Move objects, even between different accounts or containers"""

    arguments = dict(
        public=ValueArgument('publish new object', '--public'),
        content_type=ValueArgument(
            'change object\'s content type', '--content-type')
    )

    @errors.Generic.all
    @errors.Pithos.connection
    @errors.Pithos.container
    @errors.Pithos.account
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
class file_append(_PithosContainer):
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

    @errors.Generic.all
    @errors.Pithos.connection
    @errors.Pithos.object_path
    def _run(self, local_path):
        if self['max_threads'] > 0:
            self.client.MAX_THREADS = int(self['max_threads'])
        (progress_bar, upload_cb) = self._safe_progress_bar('Appending')
        try:
            with open(local_path, 'rb') as f:
                self.client.append_object(self.path, f, upload_cb)
        except ClientError as ce:
            if ce.status in (404, ):
                self._container_exists()
            raise ce
        finally:
            self._safe_progress_bar_finish(progress_bar)

    def main(self, local_path, remote_path_or_url):
        super(self.__class__, self)._run(remote_path_or_url)
        self._run(local_path)


@command(file_cmds)
class file_truncate(_PithosContainer):
    """Truncate remote file up to size"""

    arguments = dict(
        size_in_bytes=IntArgument('Length of file after truncation', '--size')
    )
    required = ('size_in_bytes', )

    @errors.Generic.all
    @errors.Pithos.connection
    @errors.Pithos.object_path
    @errors.Pithos.object_size
    def _run(self, size):
        try:
            self.client.truncate_object(self.path, size)
        except ClientError as ce:
            if ce.status in (404, ):
                self._container_exists()
            raise

    def main(self, path_or_url):
        super(self.__class__, self)._run(path_or_url)
        self._run(size=self['size_in_bytes'])


@command(file_cmds)
class file_overwrite(_PithosContainer):
    """Overwrite part of a remote file"""

    arguments = dict(
        progress_bar=ProgressBarArgument(
            'do not show progress bar', ('-N', '--no-progress-bar'),
            default=False),
        start_position=IntArgument('File position in bytes', '--from'),
        end_position=IntArgument('File position in bytes', '--to'),
        object_version=ValueArgument('File to overwrite', '--object-version'),
    )
    required = ('start_position', 'end_position')

    @errors.Generic.all
    @errors.Pithos.connection
    @errors.Pithos.object_path
    @errors.Pithos.object_size
    def _run(self, local_path, start, end):
        start, end = int(start), int(end)
        (progress_bar, upload_cb) = self._safe_progress_bar(
            'Overwrite %s bytes' % (end - start))
        try:
            with open(path.abspath(local_path), 'rb') as f:
                self.client.overwrite_object(
                    obj=self.path,
                    start=start,
                    end=end,
                    source_file=f,
                    source_version=self['object_version'],
                    upload_cb=upload_cb)
        except ClientError as ce:
            if ce.status in (404, ):
                self._container_exists()
            raise
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
class file_upload(_PithosContainer):
    """Upload a file

    The default destination is /pithos/NAME
    where NAME is the base name of the source path"""

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
        try:
            container_limit = int(cl_dict['x-container-policy-quota'])
        except KeyError:
            container_limit = 0
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
                        details=['Existing objects:'] + ['\t/%s\t[%s]' % (
                            o['name'],
                            o['content_type']) for o in robj.json] + [
                            'Use -f to add, overwrite or resume'])
                else:
                    try:
                        topobj = self.client.get_object_info(rpath)
                        if not self.object_is_dir(topobj):
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
                    # Use the '/' separator for directories that
                    # are about to be created in Pithos
                    rel_path = rel_path.replace(path.sep, '/')
                    self.error('remote: mkdir /%s/%s' % (
                        self.client.container, rel_path))
                    self.client.create_directory(rel_path)
                for f in files:
                    fpath = path.join(top, f)
                    if path.isfile(fpath):
                        rel_path = rel_path.replace(path.sep, '/')
                        pathfix = f.replace(path.sep, '/')
                        yield open(fpath, 'rb'), '%s/%s' % (rel_path, pathfix)
                    else:
                        self.error('%s not a regular file' % fpath)
        else:
            if not path.isfile(lpath):
                raise CLIError(('%s is not a regular file' % lpath) if (
                    path.exists(lpath)) else '%s does not exist' % lpath)
            try:
                robj = self.client.get_object_info(rpath)
                if remote_path and self.object_is_dir(robj):
                    rpath += '/%s' % (short_path.replace(path.sep, '/'))
                    self.client.get_object_info(rpath)
                if not self['overwrite']:
                    raise CLIError(
                        'Object /%s/%s already exists' % (
                            self.container, rpath),
                        details=['use -f to overwrite / resume'])
            except ClientError as ce:
                if ce.status in (404, ):
                    self._container_exists()
                else:
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
        container_info_cache = dict()
        rpref = ('pithos://%s' % self['account']) if self['account'] else ''
        for f, rpath in self._src_dst(local_path, remote_path):
            self.error('%s --> %s/%s/%s' % (
                f.name, rpref, self.client.container, rpath))
            if not (self['content_type'] and self['content_encoding']):
                ctype, cenc = guess_mime_type(f.name)
                params['content_type'] = self['content_type'] or ctype
                params['content_encoding'] = self['content_encoding'] or cenc
            if self['unchunked']:
                self.client.upload_object_unchunked(
                    rpath, f,
                    etag=self['md5_checksum'], withHashFile=self['use_hashes'],
                    **params)
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

                    caller_id = self.astakos.user_term('id')
                    if self.client.account != caller_id:
                        params['target_account'], self.client.account = (
                            self.client.account, caller_id)
                    self.client.upload_object(
                        rpath, f,
                        hash_cb=hash_cb,
                        upload_cb=upload_cb,
                        container_info_cache=container_info_cache,
                        **params)
                except KeyboardInterrupt:
                    timeout = 0.5
                    msg = '\n'
                    while activeCount() > 1:
                        msg += 'Wait for %s threads: ' % (activeCount() - 1)
                        self._err.write(msg)
                        for thread in activethreads():
                            try:
                                thread.join(timeout)
                                self._err.write(
                                    '.' if thread.isAlive() else '*')
                                self._err.flush()
                            except RuntimeError:
                                continue
                            finally:
                                timeout += 0.1
                                self._err.flush()
                                msg = '\b' * len(msg)
                    raise CLIError('Upload canceled by user')
                except Exception:
                    self._safe_progress_bar_finish(progress_bar)
                    raise
                finally:
                    self._safe_progress_bar_finish(progress_bar)

            if self['public']:
                obj = self.client.get_object_info(rpath)
                self.write('%s\n' % obj.get('x-object-public', ''))
            self.error('Upload completed')

    def main(self, local_path, remote_path_or_url=None):
        super(self.__class__, self)._run(remote_path_or_url)
        if local_path.endswith('.') or local_path.endswith(path.sep):
            remote_path = self.path or ''
        else:
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
class file_cat(_PithosContainer):
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
            'Get contents of the chosen version', '--object-version'),
        buffer_blocks=IntArgument(
            'Size of buffer in blocks (default: 4)', '--buffer-blocks')
    )

    @errors.Generic.all
    @errors.Pithos.connection
    @errors.Pithos.object_path
    def _run(self):
        try:
            # self.client.download_object(
            self.client.stream_down(
                self.path, self._out,
                range_str=self['range'],
                version=self['object_version'],
                if_match=self['if_match'],
                if_none_match=self['if_none_match'],
                if_modified_since=self['if_modified_since'],
                if_unmodified_since=self['if_unmodified_since'],
                buffer_blocks=self['buffer_blocks'])
        except ClientError as ce:
            if ce.status in (404, ):
                self._container_exists()
            raise
        self._out.flush()

    def main(self, path_or_url):
        super(self.__class__, self)._run(path_or_url)
        if self['buffer_blocks'] is not None and self['buffer_blocks'] < 1:
            arg = self.arguments['buffer_blocks']
            raise CLIInvalidArgument(
                'Invalid value %s' % arg.value, importance=2, details=[
                    '%s must be a possitive integer' % arg.lvalue])
        self._run()


@command(file_cmds)
class file_download(_PithosContainer):
    """Download a remote file or directory object to local file system"""

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
        ret, obj = [], None
        # The prefix is actually the relative remote path without
        # the trailing separator.
        prefix = self.path.rstrip('/')
        try:
            # prefix here is the object's path we requested to download
            if prefix:
                obj = self.client.get_object_info(
                    prefix, version=self['object_version'])
                obj.setdefault('name', prefix)
        except ClientError as ce:
            if ce.status in (404, ):
                self._container_exists()
                raiseCLIError(ce, details=[
                    'To download an object, it must exist either as a file or'
                    ' as a directory.',
                    'For example, to download everything under prefix/ the '
                    'directory "prefix" must exist.',
                    'To see if an remote object is actually there:',
                    '  kamaki file info [[pithos://UUID]/CONTAINER/]OBJECT',
                    'To create a directory object:',
                    '  kamaki file mkdir [[pithos://UUID]/CONTAINER/]OBJECT'])
            if ce.status in (204, ):
                raise CLIError(
                    'No file or directory objects to download',
                    details=[
                        'To download a container (e.g., %s):' % self.container,
                        '  kamaki container download %s [LOCAL_PATH]' % (
                            self.container)])
            raise

        # We requested to download either a whole container or a directory
        if (not obj) or self.object_is_dir(obj):
            if self['recursive']:
                obj = obj or dict(
                    name='', content_type='application/directory')
                dirs, files = [], []
                result = self.client.container_get(
                    prefix=prefix,
                    if_modified_since=self['modified_since_date'],
                    if_unmodified_since=self['unmodified_since_date'])

                # Find the final local path for each remote object
                # [(remote name, final local path),.]
                for o in result.json:
                    remote = o['name']
                    # First find the relative path of the object
                    # without the prefix and any leading '/'
                    relative = remote[len(prefix):].lstrip('/')
                    # Translate it to a valid path with proper separator
                    norm = relative.replace('/', path.sep)
                    # Append it to the desired local path
                    final = path.join(local_path, norm)
                    if self.object_is_dir(o):
                        dirs.append((remote, final))
                    else:
                        files.append((remote, final))
                    self.error(r"%s -> %s" % (remote, final))

                #  Put the directories on top of the list
                for dpath in sorted(p for _, p in dirs):
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
                for opath, lpath in files:
                    if self['resume']:
                        fxists = path.exists(lpath)
                        if fxists and path.isdir(lpath):
                            raise CLIError(
                                'Cannot change local dir %s into a file' % (
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
            elif prefix:
                raise CLIError(
                    'Remote object /%s/%s is a directory' % (
                        self.container, prefix),
                    details=['Use %s to download directories' % (
                        self.arguments['recursive'].lvalue)])
            else:
                parsed_name = self.arguments['recursive'].lvalue
                raise CLIError(
                    'Cannot download container %s' % self.container,
                    details=[
                        'Use %s to download containers' % parsed_name,
                        '  kamaki file download %s /%s [LOCAL_PATH]' % (
                            parsed_name, self.container)])
        else:
            #  Remote object is just a file
            #  The local path to be stored already exists
            if path.exists(local_path):
                if not self['resume']:
                    raise CLIError(
                        'Cannot overwrite local file %s' % (local_path),
                        details=['To overwrite/resume, use  %s' % (
                            self.arguments['resume'].lvalue)])
            #  The local path does not exist.
            elif path.sep in local_path:
                # Delegate intermediate local dir cration
                # to makedirs() inside _run()
                d = path.dirname(local_path)
                ret.append((None, d, None))
            ret.append((prefix, local_path, self['resume']))

        for r, l, resume in ret:
            if r:
                mode = 'rb+' if resume and path.exists(l) else 'wb+'
                with open(l, mode) as f:
                    yield (r, f)
            else:
                yield (r, l)

    @errors.Generic.all
    @errors.Pithos.connection
    @errors.Pithos.container
    @errors.Pithos.object_path
    @errors.Pithos.local_path
    @errors.Pithos.local_path_download
    def _run(self, local_path):
        self.client.MAX_THREADS = int(self['max_threads'] or 5)
        progress_bar = None
        try:
            # From _src_dst():
            # If rpath is None output_file is a directory.
            # If rpath is not None output_file is a file descriptor.
            for rpath, output_file in self._src_dst(local_path):
                # Create a directory
                if not rpath:
                    if not path.exists(output_file):
                        self.error('Create local directory %s' % output_file)
                        makedirs(output_file)
                    continue
                # Download a file
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
            timeout = 0.5
            msg = '\n'
            while activeCount() > 1:
                msg += 'Wait for %s threads: ' % (activeCount() - 1)
                self._err.write(msg)
                for thread in activethreads():
                    try:
                        thread.join(timeout)
                        self._err.write('.' if thread.isAlive() else '*')
                        self._err.flush()
                    except RuntimeError:
                        continue
                    finally:
                        msg = '\b' * len(msg)
                        timeout += 0.1
            raise CLIError('Download canceled by user')
        finally:
            self._safe_progress_bar_finish(progress_bar)
        self.error('Download completed')

    def main(self, remote_path_or_url, local_path=None):
        """ Dowload remote_path_or_url to local_path. """
        super(self.__class__, self)._run(remote_path_or_url)
        # Translate relative remote path to local path with proper separator
        # and without trailing '/'. If not given use the name of the container
        rpath = self.path.rstrip('/').replace('/', path.sep) or self.container
        # If remote path is /pithos/dir1/dir2/ then here we download dir2
        base = path.basename(rpath)
        # If local_path is not given use current dir
        if not local_path:
            local_path = path.join('.', base)
        # existing_dir/ -> existing_dir/base
        elif path.exists(local_path) and path.isdir(local_path):
            local_path = path.join(local_path, base)
        self._run(local_path=local_path)


@command(container_cmds)
class container_info(_PithosAccount, OptionalOutput):
    """Get information about a container"""

    arguments = dict(
        until_date=DateArgument('show metadata until then', '--until'),
        metadata=FlagArgument('Show only container metadata', '--metadata'),
        sizelimit=FlagArgument(
            'Show the maximum size limit for container', '--size-limit'),
        in_bytes=FlagArgument('Show size limit in bytes', ('-b', '--bytes'))
    )

    @errors.Generic.all
    @errors.Pithos.connection
    @errors.Pithos.container
    def _run(self):
        if self['metadata']:
            r, preflen = dict(), len('x-container-meta-')
            for k, v in self.client.get_container_meta(
                    until=self['until_date']).items():
                r[k[preflen:]] = v
        elif self['sizelimit']:
            r = self.client.get_container_limit()['x-container-policy-quota']
            r = {'size limit': 'unlimited' if r in ('0', ) else (
                int(r) if self['in_bytes'] else format_size(r))}
        else:
            r = self.client.get_container_info()
        self.print_(r, self.print_dict)

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
class container_modify(_PithosAccount, OptionalOutput):
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

    @errors.Generic.all
    @errors.Pithos.connection
    @errors.Pithos.container
    def _run(self):
        metadata = self['metadata_to_add']
        for k in (self['metadata_to_delete'] or []):
            metadata[k] = ''
        if metadata:
            self.client.set_container_meta(metadata)
            self.print_(self.client.get_container_meta(), self.print_dict)
        if self['sizelimit'] is not None:
            self.client.set_container_limit(self['sizelimit'])
            r = self.client.get_container_limit()['x-container-policy-quota']
            r = 'unlimited' if r in ('0', ) else format_size(r)
            self.writeln('new size limit: %s' % r)
        if self['versioning']:
            self.client.set_container_versioning(self['versioning'])
            self.writeln('new versioning scheme: %s' % (
                self.client.get_container_versioning()[
                    'x-container-policy-versioning']))

    def main(self, container):
        super(self.__class__, self)._run()
        self.client.container, self.container = container, container
        self._run()


@command(container_cmds)
class container_list(_PithosAccount, OptionalOutput, NameFilter):
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
            _cname = escape_ctrl_chars(container['name'])
            _cname = _cname if self['more'] else bold(_cname)
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

    @errors.Generic.all
    @errors.Pithos.connection
    @errors.Pithos.container
    def _run(self):
        container = self.container
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
        items = list(r.json or [])
        files = self._filter_by_name(items)
        if self['recursive'] and not container:
            self._create_object_forest(files)
        if self['more']:
            outbu, self._out = self._out, StringIO()
        try:
            if self['output_format']:
                self.print_(files)
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
        self._run()


@command(container_cmds)
class container_create(_PithosAccount):
    """Create a new container"""

    arguments = dict(
        versioning=ValueArgument(
            'set container versioning (auto/none)', '--versioning'),
        limit=IntArgument('set default container limit', '--limit'),
        meta=KeyValueArgument(
            'set container metadata (can be repeated)', '--meta'),
        project_id=ValueArgument('assign container to project', '--project-id')
    )

    @errors.Generic.all
    @errors.Pithos.connection
    @errors.Pithos.container
    def _run(self):
        try:
            self.client.create_container(
                container=self.container,
                sizelimit=self['limit'],
                versioning=self['versioning'],
                project_id=self['project_id'],
                metadata=self['meta'],
                success=(201, ))
        except ClientError as ce:
            if ce.status in (202, ):
                raise CLIError(
                    'Container %s alread exists' % self.container, details=[
                        'Delete %s or choose another name' % self.container])
            elif self['project_id'] and ce.status in (400, 403, 404):
                self._project_id_exists(project_id=self['project_id'])
            raise

    def main(self, new_container):
        super(self.__class__, self)._run()
        self.container, self.client.container = new_container, new_container
        self._run()


@command(container_cmds)
class container_delete(_PithosAccount):
    """Delete a container"""

    arguments = dict(
        yes=FlagArgument('Do not prompt for permission', '--yes'),
        recursive=FlagArgument(
            'delete container even if not empty', ('-r', '--recursive'))
    )

    @errors.Generic.all
    @errors.Pithos.connection
    @errors.Pithos.container
    def _run(self):
        num_of_contents = int(self.client.get_container_info(self.container)[
            'x-container-object-count'])
        delimiter, msg = None, 'Delete container %s ?' % self.container
        if self['recursive']:
            delimiter, msg = '/', 'Empty and d%s' % msg[1:]
        elif num_of_contents:
            raise CLIError(
                'Container %s is not empty' % self.container, details=[
                    'Use %s to delete non-empty containers' % (
                        self.arguments['recursive'].lvalue)])
        if self['yes'] or self.ask_user(msg):
            if num_of_contents:
                self.client.del_container(delimiter=delimiter)
            self.client.purge_container()

    def main(self, container):
        super(self.__class__, self)._run()
        self.container, self.client.container = container, container
        self._run()


@command(container_cmds)
class container_empty(_PithosAccount):
    """Empty a container"""

    arguments = dict(yes=FlagArgument('Do not prompt for permission', '--yes'))

    @errors.Generic.all
    @errors.Pithos.connection
    @errors.Pithos.container
    def _run(self):
        if self['yes'] or self.ask_user(
                'Empty container %s ?' % self.container):
            self.client.del_container(delimiter='/')

    def main(self, container):
        super(self.__class__, self)._run()
        self.container, self.client.container = container, container
        self._run()


@command(container_cmds)
class container_reassign(_PithosAccount):
    """Assign a container to a different project"""

    arguments = dict(
        project_id=ValueArgument('The project to assign', '--project-id')
    )
    required = ('project_id', )

    @errors.Generic.all
    @errors.Pithos.connection
    @errors.Pithos.container
    def _run(self):
        try:
            self.client.reassign_container(self['project_id'])
        except ClientError as ce:
            if ce.status in (400, 403, 404):
                self._project_id_exists(project_id=self['project_id'])
            raise

    def main(self, container):
        super(self.__class__, self)._run()
        self.container, self.client.container = container, container
        self._run()


@command(sharer_cmds)
class sharer_list(_PithosAccount, OptionalOutput):
    """List accounts who share file objects with current user"""

    arguments = dict(
        detail=FlagArgument('show detailed output', ('-l', '--details')),
        marker=ValueArgument('show output greater than marker', '--marker')
    )

    @errors.Generic.all
    @errors.Pithos.connection
    def _run(self):
        accounts = self.client.get_sharing_accounts(marker=self['marker'])
        if not self['output_format']:
            usernames = self._uuids2usernames(
                [acc['name'] for acc in accounts])
            for item in accounts:
                uuid = item['name']
                item['id'], item['name'] = uuid, usernames[uuid]
                if not self['detail']:
                    item.pop('last_modified')
        self.print_(accounts)

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(sharer_cmds)
class sharer_info(_PithosAccount, OptionalOutput):
    """Details on a Pithos+ sharer account (default: current account)"""

    @errors.Generic.all
    @errors.Pithos.connection
    def _run(self):
        self.print_(self.client.get_account_info(), self.print_dict)

    def main(self, account_uuid_or_name=None):
        super(self.__class__, self)._run()
        if account_uuid_or_name:
            arg = UserAccountArgument('Check', ' ')
            arg.account_client = self.astakos
            arg.value = account_uuid_or_name
            self.client.account, self.account = arg.value, arg.value
        self._run()


class _PithosGroup(_PithosAccount):
    prefix = 'x-account-group-'
    preflen = len(prefix)

    def _groups(self):
        groups = dict()
        for k, v in self.client.get_account_group().items():
            groups[k[self.preflen:]] = v
        return groups


@command(group_cmds)
class group_list(_PithosGroup, OptionalOutput):
    """list all groups and group members"""

    @errors.Generic.all
    @errors.Pithos.connection
    def _run(self):
        self.print_(self._groups(), self.print_dict)

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(group_cmds)
class group_create(_PithosGroup, OptionalOutput):
    """Create a group of users"""

    arguments = dict(
        user_uuid=RepeatableArgument('Add a user to the group', '--uuid'),
        username=RepeatableArgument('Add a user to the group', '--username')
    )
    required = ['user_uuid', 'username']

    @errors.Generic.all
    @errors.Pithos.connection
    def _run(self, groupname, *users):
        if groupname in self._groups() and not self.ask_user(
                'Group %s already exists, overwrite?' % groupname):
            self.error('Aborted')
        else:
            self.client.set_account_group(groupname, users)
            self.print_(self._groups(), self.print_dict)

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
class group_delete(_PithosGroup, OptionalOutput):
    """Delete a user group"""

    @errors.Generic.all
    @errors.Pithos.connection
    def _run(self, groupname):
        self.client.del_account_group(groupname)
        self.print_(self._groups(), self.print_dict)

    def main(self, groupname):
        super(self.__class__, self)._run()
        self._run(groupname)
