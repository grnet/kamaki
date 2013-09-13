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

from sys import stdout
from time import localtime, strftime
from os import path, makedirs, walk

from kamaki.cli import command
from kamaki.cli.command_tree import CommandTree
from kamaki.cli.errors import raiseCLIError, CLISyntaxError, CLIBaseUrlError
from kamaki.cli.utils import (
    format_size, to_bytes, print_dict, print_items, page_hold, bold, ask_user,
    get_path_size, print_json, guess_mime_type)
from kamaki.cli.argument import FlagArgument, ValueArgument, IntArgument
from kamaki.cli.argument import KeyValueArgument, DateArgument
from kamaki.cli.argument import ProgressBarArgument
from kamaki.cli.commands import _command_init, errors
from kamaki.cli.commands import addLogSettings, DontRaiseKeyError
from kamaki.cli.commands import (
    _optional_output_cmd, _optional_json, _name_filter)
from kamaki.clients.pithos import PithosClient, ClientError
from kamaki.clients.astakos import AstakosClient

pithos_cmds = CommandTree('file', 'Pithos+/Storage API commands')
_commands = [pithos_cmds]


# Argument functionality

class DelimiterArgument(ValueArgument):
    """
    :value type: string
    :value returns: given string or /
    """

    def __init__(self, caller_obj, help='', parsed_name=None, default=None):
        super(DelimiterArgument, self).__init__(help, parsed_name, default)
        self.caller_obj = caller_obj

    @property
    def value(self):
        if self.caller_obj['recursive']:
            return '/'
        return getattr(self, '_value', self.default)

    @value.setter
    def value(self, newvalue):
        self._value = newvalue


class SharingArgument(ValueArgument):
    """Set sharing (read and/or write) groups
    .
    :value type: "read=term1,term2,... write=term1,term2,..."
    .
    :value returns: {'read':['term1', 'term2', ...],
    .   'write':['term1', 'term2', ...]}
    """

    @property
    def value(self):
        return getattr(self, '_value', self.default)

    @value.setter
    def value(self, newvalue):
        perms = {}
        try:
            permlist = newvalue.split(' ')
        except AttributeError:
            return
        for p in permlist:
            try:
                (key, val) = p.split('=')
            except ValueError as err:
                raiseCLIError(
                    err,
                    'Error in --sharing',
                    details='Incorrect format',
                    importance=1)
            if key.lower() not in ('read', 'write'):
                msg = 'Error in --sharing'
                raiseCLIError(err, msg, importance=1, details=[
                    'Invalid permission key %s' % key])
            val_list = val.split(',')
            if not key in perms:
                perms[key] = []
            for item in val_list:
                if item not in perms[key]:
                    perms[key].append(item)
        self._value = perms


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
        if not newvalues:
            self._value = self.default
            return
        self._value = ''
        for newvalue in newvalues.split(','):
            self._value = ('%s,' % self._value) if self._value else ''
            start, sep, end = newvalue.partition('-')
            if sep:
                if start:
                    start, end = (int(start), int(end))
                    assert start <= end, 'Invalid range value %s' % newvalue
                    self._value += '%s-%s' % (int(start), int(end))
                else:
                    self._value += '-%s' % int(end)
            else:
                self._value += '%s' % int(start)


# Command specs


class _pithos_init(_command_init):
    """Initialize a pithos+ kamaki client"""

    @staticmethod
    def _is_dir(remote_dict):
        return 'application/directory' == remote_dict.get(
            'content_type', remote_dict.get('content-type', ''))

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
        if getattr(self, 'auth_base', False):
            self.account = self.auth_base.user_term('id', self.token)
        else:
            astakos_url = self._custom_url('astakos')
            astakos_token = self._custom_token('astakos') or self.token
            if not astakos_url:
                raise CLIBaseUrlError(service='astakos')
            astakos = AstakosClient(astakos_url, astakos_token)
            self.account = astakos.user_term('id')

    @errors.generic.all
    @addLogSettings
    def _run(self):
        self.base_url = None
        if getattr(self, 'cloud', None):
            self.base_url = self._custom_url('pithos')
        else:
            self.cloud = 'default'
        self.token = self._custom_token('pithos')
        self.container = self._custom_container()

        if getattr(self, 'auth_base', False):
            self.token = self.token or self.auth_base.token
            if not self.base_url:
                pithos_endpoints = self.auth_base.get_service_endpoints(
                    self._custom_type('pithos') or 'object-store',
                    self._custom_version('pithos') or '')
                self.base_url = pithos_endpoints['publicURL']
        elif not self.base_url:
            raise CLIBaseUrlError(service='pithos')

        self._set_account()
        self.client = PithosClient(
            base_url=self.base_url,
            token=self.token,
            account=self.account,
            container=self.container)

    def main(self):
        self._run()


class _file_account_command(_pithos_init):
    """Base class for account level storage commands"""

    def __init__(self, arguments={}, auth_base=None, cloud=None):
        super(_file_account_command, self).__init__(
            arguments, auth_base, cloud)
        self['account'] = ValueArgument(
            'Set user account (not permanent)', ('-A', '--account'))

    def _run(self, custom_account=None):
        super(_file_account_command, self)._run()
        if custom_account:
            self.client.account = custom_account
        elif self['account']:
            self.client.account = self['account']

    @errors.generic.all
    def main(self):
        self._run()


class _file_container_command(_file_account_command):
    """Base class for container level storage commands"""

    container = None
    path = None

    def __init__(self, arguments={}, auth_base=None, cloud=None):
        super(_file_container_command, self).__init__(
            arguments, auth_base, cloud)
        self['container'] = ValueArgument(
            'Set container to work with (temporary)', ('-C', '--container'))

    def extract_container_and_path(
            self,
            container_with_path,
            path_is_optional=True):
        """Contains all heuristics for deciding what should be used as
        container or path. Options are:
        * user string of the form container:path
        * self.container, self.path variables set by super constructor, or
        explicitly by the caller application
        Error handling is explicit as these error cases happen only here
        """
        try:
            assert isinstance(container_with_path, str)
        except AssertionError as err:
            if self['container'] and path_is_optional:
                self.container = self['container']
                self.client.container = self['container']
                return
            raiseCLIError(err)

        user_cont, sep, userpath = container_with_path.partition(':')

        if sep:
            if not user_cont:
                raiseCLIError(CLISyntaxError(
                    'Container is missing\n',
                    details=errors.pithos.container_howto))
            alt_cont = self['container']
            if alt_cont and user_cont != alt_cont:
                raiseCLIError(CLISyntaxError(
                    'Conflict: 2 containers (%s, %s)' % (user_cont, alt_cont),
                    details=errors.pithos.container_howto)
                )
            self.container = user_cont
            if not userpath:
                raiseCLIError(CLISyntaxError(
                    'Path is missing for object in container %s' % user_cont,
                    details=errors.pithos.container_howto)
                )
            self.path = userpath
        else:
            alt_cont = self['container'] or self.client.container
            if alt_cont:
                self.container = alt_cont
                self.path = user_cont
            elif path_is_optional:
                self.container = user_cont
                self.path = None
            else:
                self.container = user_cont
                raiseCLIError(CLISyntaxError(
                    'Both container and path are required',
                    details=errors.pithos.container_howto)
                )

    @errors.generic.all
    def _run(self, container_with_path=None, path_is_optional=True):
        super(_file_container_command, self)._run()
        if self['container']:
            self.client.container = self['container']
            if container_with_path:
                self.path = container_with_path
            elif not path_is_optional:
                raise CLISyntaxError(
                    'Both container and path are required',
                    details=errors.pithos.container_howto)
        elif container_with_path:
            self.extract_container_and_path(
                container_with_path,
                path_is_optional)
            self.client.container = self.container
        self.container = self.client.container

    def main(self, container_with_path=None, path_is_optional=True):
        self._run(container_with_path, path_is_optional)


@command(pithos_cmds)
class file_list(_file_container_command, _optional_json, _name_filter):
    """List containers, object trees or objects in a directory
    Use with:
    1 no parameters : containers in current account
    2. one parameter (container) or --container : contents of container
    3. <container>:<prefix> or --container=<container> <prefix>: objects in
    .   container starting with prefix
    """

    arguments = dict(
        detail=FlagArgument('detailed output', ('-l', '--list')),
        limit=IntArgument('limit number of listed items', ('-n', '--number')),
        marker=ValueArgument('output greater that marker', '--marker'),
        delimiter=ValueArgument('show output up to delimiter', '--delimiter'),
        path=ValueArgument(
            'show output starting with prefix up to /', '--path'),
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
        more=FlagArgument(
            'output results in pages (-n to set items per page, default 10)',
            '--more'),
        exact_match=FlagArgument(
            'Show only objects that match exactly with path',
            '--exact-match'),
        enum=FlagArgument('Enumerate results', '--enumerate')
    )

    def print_objects(self, object_list):
        if self['json_output']:
            print_json(object_list)
            return
        limit = int(self['limit']) if self['limit'] > 0 else len(object_list)
        for index, obj in enumerate(object_list):
            if self['exact_match'] and self.path and not (
                    obj['name'] == self.path or 'content_type' in obj):
                continue
            pretty_obj = obj.copy()
            index += 1
            empty_space = ' ' * (len(str(len(object_list))) - len(str(index)))
            if 'subdir' in obj:
                continue
            if obj['content_type'] == 'application/directory':
                isDir = True
                size = 'D'
            else:
                isDir = False
                size = format_size(obj['bytes'])
                pretty_obj['bytes'] = '%s (%s)' % (obj['bytes'], size)
            oname = bold(obj['name'])
            prfx = ('%s%s. ' % (empty_space, index)) if self['enum'] else ''
            if self['detail']:
                print('%s%s' % (prfx, oname))
                print_dict(pretty_obj, exclude=('name'))
                print
            else:
                oname = '%s%9s %s' % (prfx, size, oname)
                oname += '/' if isDir else ''
                print(oname)
            if self['more']:
                page_hold(index, limit, len(object_list))

    def print_containers(self, container_list):
        if self['json_output']:
            print_json(container_list)
            return
        limit = int(self['limit']) if self['limit'] > 0\
            else len(container_list)
        for index, container in enumerate(container_list):
            if 'bytes' in container:
                size = format_size(container['bytes'])
            prfx = ('%s. ' % (index + 1)) if self['enum'] else ''
            cname = '%s%s' % (prfx, bold(container['name']))
            if self['detail']:
                print(cname)
                pretty_c = container.copy()
                if 'bytes' in container:
                    pretty_c['bytes'] = '%s (%s)' % (container['bytes'], size)
                print_dict(pretty_c, exclude=('name'))
                print
            else:
                if 'count' in container and 'bytes' in container:
                    print('%s (%s, %s objects)' % (
                        cname,
                        size,
                        container['count']))
                else:
                    print(cname)
            if self['more']:
                page_hold(index + 1, limit, len(container_list))

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.object_path
    @errors.pithos.container
    def _run(self):
        if self.container is None:
            r = self.client.account_get(
                limit=False if self['more'] else self['limit'],
                marker=self['marker'],
                if_modified_since=self['if_modified_since'],
                if_unmodified_since=self['if_unmodified_since'],
                until=self['until'],
                show_only_shared=self['shared'])
            files = self._filter_by_name(r.json)
            self._print(files, self.print_containers)
        else:
            prefix = (self.path and not self['name']) or self['name_pref']
            r = self.client.container_get(
                limit=False if self['more'] else self['limit'],
                marker=self['marker'],
                prefix=prefix,
                delimiter=self['delimiter'],
                path=self['path'],
                if_modified_since=self['if_modified_since'],
                if_unmodified_since=self['if_unmodified_since'],
                until=self['until'],
                meta=self['meta'],
                show_only_shared=self['shared'])
            files = self._filter_by_name(r.json)
            self._print(files, self.print_objects)

    def main(self, container____path__=None):
        super(self.__class__, self)._run(container____path__)
        self._run()


@command(pithos_cmds)
class file_mkdir(_file_container_command, _optional_output_cmd):
    """Create a directory
    Kamaki hanldes directories the same way as OOS Storage and Pithos+:
    A directory  is   an  object  with  type  "application/directory"
    An object with path  dir/name can exist even if  dir does not exist
    or even if dir  is  a non  directory  object.  Users can modify dir '
    without affecting the dir/name object in any way.
    """

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    def _run(self):
        self._optional_output(self.client.create_directory(self.path))

    def main(self, container___directory):
        super(self.__class__, self)._run(
            container___directory,
            path_is_optional=False)
        self._run()


@command(pithos_cmds)
class file_touch(_file_container_command, _optional_output_cmd):
    """Create an empty object (file)
    If object exists, this command will reset it to 0 length
    """

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

    def main(self, container___path):
        super(file_touch, self)._run(
            container___path,
            path_is_optional=False)
        self._run()


@command(pithos_cmds)
class file_create(_file_container_command, _optional_output_cmd):
    """Create a container"""

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
        self._optional_output(self.client.create_container(
            container=container,
            sizelimit=self['limit'],
            versioning=self['versioning'],
            metadata=self['meta']))

    def main(self, container=None):
        super(self.__class__, self)._run(container)
        if container and self.container != container:
            raiseCLIError('Invalid container name %s' % container, details=[
                'Did you mean "%s" ?' % self.container,
                'Use --container for names containing :'])
        self._run(container)


class _source_destination_command(_file_container_command):

    arguments = dict(
        destination_account=ValueArgument('', ('-a', '--dst-account')),
        recursive=FlagArgument('', ('-R', '--recursive')),
        prefix=FlagArgument('', '--with-prefix', default=''),
        suffix=ValueArgument('', '--with-suffix', default=''),
        add_prefix=ValueArgument('', '--add-prefix', default=''),
        add_suffix=ValueArgument('', '--add-suffix', default=''),
        prefix_replace=ValueArgument('', '--prefix-to-replace', default=''),
        suffix_replace=ValueArgument('', '--suffix-to-replace', default=''),
    )

    def __init__(self, arguments={}, auth_base=None, cloud=None):
        self.arguments.update(arguments)
        super(_source_destination_command, self).__init__(
            self.arguments, auth_base, cloud)

    def _run(self, source_container___path, path_is_optional=False):
        super(_source_destination_command, self)._run(
            source_container___path,
            path_is_optional)
        self.dst_client = PithosClient(
            base_url=self.client.base_url,
            token=self.client.token,
            account=self['destination_account'] or self.client.account)

    @errors.generic.all
    @errors.pithos.account
    def _dest_container_path(self, dest_container_path):
        if self['destination_container']:
            self.dst_client.container = self['destination_container']
            return (self['destination_container'], dest_container_path)
        if dest_container_path:
            dst = dest_container_path.split(':')
            if len(dst) > 1:
                try:
                    self.dst_client.container = dst[0]
                    self.dst_client.get_container_info(dst[0])
                except ClientError as err:
                    if err.status in (404, 204):
                        raiseCLIError(
                            'Destination container %s not found' % dst[0])
                    raise
                else:
                    self.dst_client.container = dst[0]
                return (dst[0], dst[1])
            return(None, dst[0])
        raiseCLIError('No destination container:path provided')

    def _get_all(self, prefix):
        return self.client.container_get(prefix=prefix).json

    def _get_src_objects(self, src_path, source_version=None):
        """Get a list of the source objects to be called

        :param src_path: (str) source path

        :returns: (method, params) a method that returns a list when called
        or (object) if it is a single object
        """
        if src_path and src_path[-1] == '/':
            src_path = src_path[:-1]

        if self['prefix']:
            return (self._get_all, dict(prefix=src_path))
        try:
            srcobj = self.client.get_object_info(
                src_path, version=source_version)
        except ClientError as srcerr:
            if srcerr.status == 404:
                raiseCLIError(
                    'Source object %s not in source container %s' % (
                        src_path, self.client.container),
                    details=['Hint: --with-prefix to match multiple objects'])
            elif srcerr.status not in (204,):
                raise
            return (self.client.list_objects, {})

        if self._is_dir(srcobj):
            if not self['recursive']:
                raiseCLIError(
                    'Object %s of cont. %s is a dir' % (
                        src_path, self.client.container),
                    details=['Use --recursive to access directories'])
            return (self._get_all, dict(prefix=src_path))
        srcobj['name'] = src_path
        return srcobj

    def src_dst_pairs(self, dst_path, source_version=None):
        src_iter = self._get_src_objects(self.path, source_version)
        src_N = isinstance(src_iter, tuple)
        add_prefix = self['add_prefix'].strip('/')

        if dst_path and dst_path.endswith('/'):
            dst_path = dst_path[:-1]

        try:
            dstobj = self.dst_client.get_object_info(dst_path)
        except ClientError as trgerr:
            if trgerr.status in (404,):
                if src_N:
                    raiseCLIError(
                        'Cannot merge multiple paths to path %s' % dst_path,
                        details=[
                            'Try to use / or a directory as destination',
                            'or create the destination dir (/file mkdir)',
                            'or use a single object as source'])
            elif trgerr.status not in (204,):
                raise
        else:
            if self._is_dir(dstobj):
                add_prefix = '%s/%s' % (dst_path.strip('/'), add_prefix)
            elif src_N:
                raiseCLIError(
                    'Cannot merge multiple paths to path' % dst_path,
                    details=[
                        'Try to use / or a directory as destination',
                        'or create the destination dir (/file mkdir)',
                        'or use a single object as source'])

        if src_N:
            (method, kwargs) = src_iter
            for obj in method(**kwargs):
                name = obj['name']
                if name.endswith(self['suffix']):
                    yield (name, self._get_new_object(name, add_prefix))
        elif src_iter['name'].endswith(self['suffix']):
            name = src_iter['name']
            yield (name, self._get_new_object(dst_path or name, add_prefix))
        else:
            raiseCLIError('Source path %s conflicts with suffix %s' % (
                src_iter['name'], self['suffix']))

    def _get_new_object(self, obj, add_prefix):
        if self['prefix_replace'] and obj.startswith(self['prefix_replace']):
            obj = obj[len(self['prefix_replace']):]
        if self['suffix_replace'] and obj.endswith(self['suffix_replace']):
            obj = obj[:-len(self['suffix_replace'])]
        return add_prefix + obj + self['add_suffix']


@command(pithos_cmds)
class file_copy(_source_destination_command, _optional_output_cmd):
    """Copy objects from container to (another) container
    Semantics:
    copy cont:path dir
    .   transfer path as dir/path
    copy cont:path cont2:
    .   trasnfer all <obj> prefixed with path to container cont2
    copy cont:path [cont2:]path2
    .   transfer path to path2
    Use options:
    1. <container1>:<path1> [container2:]<path2> : if container2 is not given,
    destination is container1:path2
    2. <container>:<path1> <path2> : make a copy in the same container
    3. Can use --container= instead of <container1>
    """

    arguments = dict(
        destination_account=ValueArgument(
            'Account to copy to', ('-a', '--dst-account')),
        destination_container=ValueArgument(
            'use it if destination container name contains a : character',
            ('-D', '--dst-container')),
        public=ValueArgument('make object publicly accessible', '--public'),
        content_type=ValueArgument(
            'change object\'s content type', '--content-type'),
        recursive=FlagArgument(
            'copy directory and contents', ('-R', '--recursive')),
        prefix=FlagArgument(
            'Match objects prefixed with src path (feels like src_path*)',
            '--with-prefix',
            default=''),
        suffix=ValueArgument(
            'Suffix of source objects (feels like *suffix)', '--with-suffix',
            default=''),
        add_prefix=ValueArgument('Prefix targets', '--add-prefix', default=''),
        add_suffix=ValueArgument('Suffix targets', '--add-suffix', default=''),
        prefix_replace=ValueArgument(
            'Prefix of src to replace with dst path + add_prefix, if matched',
            '--prefix-to-replace',
            default=''),
        suffix_replace=ValueArgument(
            'Suffix of src to replace with add_suffix, if matched',
            '--suffix-to-replace',
            default=''),
        source_version=ValueArgument(
            'copy specific version', ('-S', '--source-version'))
    )

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    @errors.pithos.account
    def _run(self, dst_path):
        no_source_object = True
        src_account = self.client.account if (
            self['destination_account']) else None
        for src_obj, dst_obj in self.src_dst_pairs(
                dst_path, self['source_version']):
            no_source_object = False
            r = self.dst_client.copy_object(
                src_container=self.client.container,
                src_object=src_obj,
                dst_container=self.dst_client.container,
                dst_object=dst_obj,
                source_account=src_account,
                source_version=self['source_version'],
                public=self['public'],
                content_type=self['content_type'])
        if no_source_object:
            raiseCLIError('No object %s in container %s' % (
                self.path, self.container))
        self._optional_output(r)

    def main(
            self, source_container___path,
            destination_container___path=None):
        super(file_copy, self)._run(
            source_container___path,
            path_is_optional=False)
        (dst_cont, dst_path) = self._dest_container_path(
            destination_container___path)
        self.dst_client.container = dst_cont or self.container
        self._run(dst_path=dst_path or '')


@command(pithos_cmds)
class file_move(_source_destination_command, _optional_output_cmd):
    """Move/rename objects from container to (another) container
    Semantics:
    move cont:path dir
    .   rename path as dir/path
    move cont:path cont2:
    .   trasnfer all <obj> prefixed with path to container cont2
    move cont:path [cont2:]path2
    .   transfer path to path2
    Use options:
    1. <container1>:<path1> [container2:]<path2> : if container2 is not given,
    destination is container1:path2
    2. <container>:<path1> <path2> : move in the same container
    3. Can use --container= instead of <container1>
    """

    arguments = dict(
        destination_account=ValueArgument(
            'Account to move to', ('-a', '--dst-account')),
        destination_container=ValueArgument(
            'use it if destination container name contains a : character',
            ('-D', '--dst-container')),
        public=ValueArgument('make object publicly accessible', '--public'),
        content_type=ValueArgument(
            'change object\'s content type', '--content-type'),
        recursive=FlagArgument(
            'copy directory and contents', ('-R', '--recursive')),
        prefix=FlagArgument(
            'Match objects prefixed with src path (feels like src_path*)',
            '--with-prefix',
            default=''),
        suffix=ValueArgument(
            'Suffix of source objects (feels like *suffix)', '--with-suffix',
            default=''),
        add_prefix=ValueArgument('Prefix targets', '--add-prefix', default=''),
        add_suffix=ValueArgument('Suffix targets', '--add-suffix', default=''),
        prefix_replace=ValueArgument(
            'Prefix of src to replace with dst path + add_prefix, if matched',
            '--prefix-to-replace',
            default=''),
        suffix_replace=ValueArgument(
            'Suffix of src to replace with add_suffix, if matched',
            '--suffix-to-replace',
            default='')
    )

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    def _run(self, dst_path):
        no_source_object = True
        src_account = self.client.account if (
            self['destination_account']) else None
        for src_obj, dst_obj in self.src_dst_pairs(dst_path):
            no_source_object = False
            r = self.dst_client.move_object(
                src_container=self.container,
                src_object=src_obj,
                dst_container=self.dst_client.container,
                dst_object=dst_obj,
                source_account=src_account,
                public=self['public'],
                content_type=self['content_type'])
        if no_source_object:
            raiseCLIError('No object %s in container %s' % (
                self.path,
                self.container))
        self._optional_output(r)

    def main(
            self, source_container___path,
            destination_container___path=None):
        super(self.__class__, self)._run(
            source_container___path,
            path_is_optional=False)
        (dst_cont, dst_path) = self._dest_container_path(
            destination_container___path)
        (dst_cont, dst_path) = self._dest_container_path(
            destination_container___path)
        self.dst_client.container = dst_cont or self.container
        self._run(dst_path=dst_path or '')


@command(pithos_cmds)
class file_append(_file_container_command, _optional_output_cmd):
    """Append local file to (existing) remote object
    The remote object should exist.
    If the remote object is a directory, it is transformed into a file.
    In the later case, objects under the directory remain intact.
    """

    arguments = dict(
        progress_bar=ProgressBarArgument(
            'do not show progress bar',
            ('-N', '--no-progress-bar'),
            default=False)
    )

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    @errors.pithos.object_path
    def _run(self, local_path):
        (progress_bar, upload_cb) = self._safe_progress_bar('Appending')
        try:
            f = open(local_path, 'rb')
            self._optional_output(
                self.client.append_object(self.path, f, upload_cb))
        except Exception:
            self._safe_progress_bar_finish(progress_bar)
            raise
        finally:
            self._safe_progress_bar_finish(progress_bar)

    def main(self, local_path, container___path):
        super(self.__class__, self)._run(
            container___path, path_is_optional=False)
        self._run(local_path)


@command(pithos_cmds)
class file_truncate(_file_container_command, _optional_output_cmd):
    """Truncate remote file up to a size (default is 0)"""

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    @errors.pithos.object_path
    @errors.pithos.object_size
    def _run(self, size=0):
        self._optional_output(self.client.truncate_object(self.path, size))

    def main(self, container___path, size=0):
        super(self.__class__, self)._run(container___path)
        self._run(size=size)


@command(pithos_cmds)
class file_overwrite(_file_container_command, _optional_output_cmd):
    """Overwrite part (from start to end) of a remote file
    overwrite local-path container 10 20
    .   will overwrite bytes from 10 to 20 of a remote file with the same name
    .   as local-path basename
    overwrite local-path container:path 10 20
    .   will overwrite as above, but the remote file is named path
    """

    arguments = dict(
        progress_bar=ProgressBarArgument(
            'do not show progress bar',
            ('-N', '--no-progress-bar'),
            default=False)
    )

    def _open_file(self, local_path, start):
        f = open(path.abspath(local_path), 'rb')
        f.seek(0, 2)
        f_size = f.tell()
        f.seek(start, 0)
        return (f, f_size)

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    @errors.pithos.object_path
    @errors.pithos.object_size
    def _run(self, local_path, start, end):
        (start, end) = (int(start), int(end))
        (f, f_size) = self._open_file(local_path, start)
        (progress_bar, upload_cb) = self._safe_progress_bar(
            'Overwrite %s bytes' % (end - start))
        try:
            self._optional_output(self.client.overwrite_object(
                obj=self.path,
                start=start,
                end=end,
                source_file=f,
                upload_cb=upload_cb))
        finally:
            self._safe_progress_bar_finish(progress_bar)

    def main(self, local_path, container___path, start, end):
        super(self.__class__, self)._run(
            container___path, path_is_optional=None)
        self.path = self.path or path.basename(local_path)
        self._run(local_path=local_path, start=start, end=end)


@command(pithos_cmds)
class file_manifest(_file_container_command, _optional_output_cmd):
    """Create a remote file of uploaded parts by manifestation
    Remains functional for compatibility with OOS Storage. Users are advised
    to use the upload command instead.
    Manifestation is a compliant process for uploading large files. The files
    have to be chunked in smalled files and uploaded as <prefix><increment>
    where increment is 1, 2, ...
    Finally, the manifest command glues partial files together in one file
    named <prefix>
    The upload command is faster, easier and more intuitive than manifest
    """

    arguments = dict(
        etag=ValueArgument('check written data', '--etag'),
        content_encoding=ValueArgument(
            'set MIME content type', '--content-encoding'),
        content_disposition=ValueArgument(
            'the presentation style of the object', '--content-disposition'),
        content_type=ValueArgument(
            'specify content type', '--content-type',
            default='application/octet-stream'),
        sharing=SharingArgument(
            '\n'.join([
                'define object sharing policy',
                '    ( "read=user1,grp1,user2,... write=user1,grp2,..." )']),
            '--sharing'),
        public=FlagArgument('make object publicly accessible', '--public')
    )

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    @errors.pithos.object_path
    def _run(self):
        ctype, cenc = guess_mime_type(self.path)
        self._optional_output(self.client.create_object_by_manifestation(
            self.path,
            content_encoding=self['content_encoding'] or cenc,
            content_disposition=self['content_disposition'],
            content_type=self['content_type'] or ctype,
            sharing=self['sharing'],
            public=self['public']))

    def main(self, container___path):
        super(self.__class__, self)._run(
            container___path, path_is_optional=False)
        self.run()


@command(pithos_cmds)
class file_upload(_file_container_command, _optional_output_cmd):
    """Upload a file"""

    arguments = dict(
        use_hashes=FlagArgument(
            'provide hashmap file instead of data', '--use-hashes'),
        etag=ValueArgument('check written data', '--etag'),
        unchunked=FlagArgument('avoid chunked transfer mode', '--unchunked'),
        content_encoding=ValueArgument(
            'set MIME content type', '--content-encoding'),
        content_disposition=ValueArgument(
            'specify objects presentation style', '--content-disposition'),
        content_type=ValueArgument('specify content type', '--content-type'),
        sharing=SharingArgument(
            help='\n'.join([
                'define sharing object policy',
                '( "read=user1,grp1,user2,... write=user1,grp2,... )']),
            parsed_name='--sharing'),
        public=FlagArgument('make object publicly accessible', '--public'),
        poolsize=IntArgument('set pool size', '--with-pool-size'),
        progress_bar=ProgressBarArgument(
            'do not show progress bar',
            ('-N', '--no-progress-bar'),
            default=False),
        overwrite=FlagArgument('Force (over)write', ('-f', '--force')),
        recursive=FlagArgument(
            'Recursively upload directory *contents* + subdirectories',
            ('-R', '--recursive'))
    )

    def _check_container_limit(self, path):
        cl_dict = self.client.get_container_limit()
        container_limit = int(cl_dict['x-container-policy-quota'])
        r = self.client.container_get()
        used_bytes = sum(int(o['bytes']) for o in r.json)
        path_size = get_path_size(path)
        if container_limit and path_size > (container_limit - used_bytes):
            raiseCLIError(
                'Container(%s) (limit(%s) - used(%s)) < size(%s) of %s' % (
                    self.client.container,
                    format_size(container_limit),
                    format_size(used_bytes),
                    format_size(path_size),
                    path),
                importance=1, details=[
                    'Check accound limit: /file quota',
                    'Check container limit:',
                    '\t/file containerlimit get %s' % self.client.container,
                    'Increase container limit:',
                    '\t/file containerlimit set <new limit> %s' % (
                        self.client.container)])

    def _path_pairs(self, local_path, remote_path):
        """Get pairs of local and remote paths"""
        lpath = path.abspath(local_path)
        short_path = lpath.split(path.sep)[-1]
        rpath = remote_path or short_path
        if path.isdir(lpath):
            if not self['recursive']:
                raiseCLIError('%s is a directory' % lpath, details=[
                    'Use -R to upload directory contents'])
            robj = self.client.container_get(path=rpath)
            if robj.json and not self['overwrite']:
                raiseCLIError(
                    'Objects prefixed with %s already exist' % rpath,
                    importance=1,
                    details=['Existing objects:'] + ['\t%s:\t%s' % (
                        o['content_type'][12:],
                        o['name']) for o in robj.json] + [
                        'Use -f to add, overwrite or resume'])
            if not self['overwrite']:
                try:
                    topobj = self.client.get_object_info(rpath)
                    if not self._is_dir(topobj):
                        raiseCLIError(
                            'Object %s exists but it is not a dir' % rpath,
                            importance=1, details=['Use -f to overwrite'])
                except ClientError as ce:
                    if ce.status != 404:
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
                    print('mkdir %s:%s' % (self.client.container, rel_path))
                    self.client.create_directory(rel_path)
                for f in files:
                    fpath = path.join(top, f)
                    if path.isfile(fpath):
                        rel_path = rel_path.replace(path.sep, '/')
                        pathfix = f.replace(path.sep, '/')
                        yield open(fpath, 'rb'), '%s/%s' % (rel_path, pathfix)
                    else:
                        print('%s is not a regular file' % fpath)
        else:
            if not path.isfile(lpath):
                raiseCLIError(('%s is not a regular file' % lpath) if (
                    path.exists(lpath)) else '%s does not exist' % lpath)
            try:
                robj = self.client.get_object_info(rpath)
                if remote_path and self._is_dir(robj):
                    rpath += '/%s' % (short_path.replace(path.sep, '/'))
                    self.client.get_object_info(rpath)
                if not self['overwrite']:
                    raiseCLIError(
                        'Object %s already exists' % rpath,
                        importance=1,
                        details=['use -f to overwrite or resume'])
            except ClientError as ce:
                if ce.status != 404:
                    raise
            self._check_container_limit(lpath)
            yield open(lpath, 'rb'), rpath

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    @errors.pithos.object_path
    @errors.pithos.local_path
    def _run(self, local_path, remote_path):
        poolsize = self['poolsize']
        if poolsize > 0:
            self.client.MAX_THREADS = int(poolsize)
        params = dict(
            content_encoding=self['content_encoding'],
            content_type=self['content_type'],
            content_disposition=self['content_disposition'],
            sharing=self['sharing'],
            public=self['public'])
        uploaded = []
        container_info_cache = dict()
        for f, rpath in self._path_pairs(local_path, remote_path):
            print('%s --> %s:%s' % (f.name, self.client.container, rpath))
            if not (self['content_type'] and self['content_encoding']):
                ctype, cenc = guess_mime_type(f.name)
                params['content_type'] = self['content_type'] or ctype
                params['content_encoding'] = self['content_encoding'] or cenc
            if self['unchunked']:
                r = self.client.upload_object_unchunked(
                    rpath, f,
                    etag=self['etag'], withHashFile=self['use_hashes'],
                    **params)
                if self['with_output'] or self['json_output']:
                    r['name'] = '%s: %s' % (self.client.container, rpath)
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
                        r['name'] = '%s: %s' % (self.client.container, rpath)
                        uploaded.append(r)
                except Exception:
                    self._safe_progress_bar_finish(progress_bar)
                    raise
                finally:
                    self._safe_progress_bar_finish(progress_bar)
        self._optional_output(uploaded)
        print('Upload completed')

    def main(self, local_path, container____path__=None):
        super(self.__class__, self)._run(container____path__)
        remote_path = self.path or path.basename(path.abspath(local_path))
        self._run(local_path=local_path, remote_path=remote_path)


@command(pithos_cmds)
class file_cat(_file_container_command):
    """Print remote file contents to console"""

    arguments = dict(
        range=RangeArgument('show range of data', '--range'),
        if_match=ValueArgument('show output if ETags match', '--if-match'),
        if_none_match=ValueArgument(
            'show output if ETags match', '--if-none-match'),
        if_modified_since=DateArgument(
            'show output modified since then', '--if-modified-since'),
        if_unmodified_since=DateArgument(
            'show output unmodified since then', '--if-unmodified-since'),
        object_version=ValueArgument(
            'get the specific version', ('-O', '--object-version'))
    )

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    @errors.pithos.object_path
    def _run(self):
        self.client.download_object(
            self.path,
            stdout,
            range_str=self['range'],
            version=self['object_version'],
            if_match=self['if_match'],
            if_none_match=self['if_none_match'],
            if_modified_since=self['if_modified_since'],
            if_unmodified_since=self['if_unmodified_since'])

    def main(self, container___path):
        super(self.__class__, self)._run(
            container___path, path_is_optional=False)
        self._run()


@command(pithos_cmds)
class file_download(_file_container_command):
    """Download remote object as local file
    If local destination is a directory:
    *   download <container>:<path> <local dir> -R
    will download all files on <container> prefixed as <path>,
    to <local dir>/<full path> (or <local dir>\<full path> in windows)
    *   download <container>:<path> <local dir> --exact-match
    will download only one file, exactly matching <path>
    ATTENTION: to download cont:dir1/dir2/file there must exist objects
    cont:dir1 and cont:dir1/dir2 of type application/directory
    To create directory objects, use /file mkdir
    """

    arguments = dict(
        resume=FlagArgument('Resume instead of overwrite', ('-r', '--resume')),
        range=RangeArgument('show range of data', '--range'),
        if_match=ValueArgument('show output if ETags match', '--if-match'),
        if_none_match=ValueArgument(
            'show output if ETags match', '--if-none-match'),
        if_modified_since=DateArgument(
            'show output modified since then', '--if-modified-since'),
        if_unmodified_since=DateArgument(
            'show output unmodified since then', '--if-unmodified-since'),
        object_version=ValueArgument(
            'get the specific version', ('-O', '--object-version')),
        poolsize=IntArgument('set pool size', '--with-pool-size'),
        progress_bar=ProgressBarArgument(
            'do not show progress bar',
            ('-N', '--no-progress-bar'),
            default=False),
        recursive=FlagArgument(
            'Download a remote path and all its contents',
            ('-R', '--recursive'))
    )

    def _outputs(self, local_path):
        """:returns: (local_file, remote_path)"""
        remotes = []
        if self['recursive']:
            r = self.client.container_get(
                prefix=self.path or '/',
                if_modified_since=self['if_modified_since'],
                if_unmodified_since=self['if_unmodified_since'])
            dirlist = dict()
            for remote in r.json:
                rname = remote['name'].strip('/')
                tmppath = ''
                for newdir in rname.strip('/').split('/')[:-1]:
                    tmppath = '/'.join([tmppath, newdir])
                    dirlist.update({tmppath.strip('/'): True})
                remotes.append((rname, file_download._is_dir(remote)))
            dir_remotes = [r[0] for r in remotes if r[1]]
            if not set(dirlist).issubset(dir_remotes):
                badguys = [bg.strip('/') for bg in set(
                    dirlist).difference(dir_remotes)]
                raiseCLIError(
                    'Some remote paths contain non existing directories',
                    details=['Missing remote directories:'] + badguys)
        elif self.path:
            r = self.client.get_object_info(
                self.path,
                version=self['object_version'])
            if file_download._is_dir(r):
                raiseCLIError(
                    'Illegal download: Remote object %s is a directory' % (
                        self.path),
                    details=['To download a directory, try --recursive or -R'])
            if '/' in self.path.strip('/') and not local_path:
                raiseCLIError(
                    'Illegal download: remote object %s contains "/"' % (
                        self.path),
                    details=[
                        'To download an object containing "/" characters',
                        'either create the remote directories or',
                        'specify a non-directory local path for this object'])
            remotes = [(self.path, False)]
        if not remotes:
            if self.path:
                raiseCLIError(
                    'No matching path %s on container %s' % (
                        self.path, self.container),
                    details=[
                        'To list the contents of %s, try:' % self.container,
                        '   /file list %s' % self.container])
            raiseCLIError(
                'Illegal download of container %s' % self.container,
                details=[
                    'To download a whole container, try:',
                    '   /file download --recursive <container>'])

        lprefix = path.abspath(local_path or path.curdir)
        if path.isdir(lprefix):
            for rpath, remote_is_dir in remotes:
                lpath = path.sep.join([
                    lprefix[:-1] if lprefix.endswith(path.sep) else lprefix,
                    rpath.strip('/').replace('/', path.sep)])
                if remote_is_dir:
                    if path.exists(lpath) and path.isdir(lpath):
                        continue
                    makedirs(lpath)
                elif path.exists(lpath):
                    if not self['resume']:
                        print('File %s exists, aborting...' % lpath)
                        continue
                    with open(lpath, 'rwb+') as f:
                        yield (f, rpath)
                else:
                    with open(lpath, 'wb+') as f:
                        yield (f, rpath)
        elif path.exists(lprefix):
            if len(remotes) > 1:
                raiseCLIError(
                    '%s remote objects cannot be merged in local file %s' % (
                        len(remotes),
                        local_path),
                    details=[
                        'To download multiple objects, local path should be',
                        'a directory, or use download without a local path'])
            (rpath, remote_is_dir) = remotes[0]
            if remote_is_dir:
                raiseCLIError(
                    'Remote directory %s should not replace local file %s' % (
                        rpath,
                        local_path))
            if self['resume']:
                with open(lprefix, 'rwb+') as f:
                    yield (f, rpath)
            else:
                raiseCLIError(
                    'Local file %s already exist' % local_path,
                    details=['Try --resume to overwrite it'])
        else:
            if len(remotes) > 1 or remotes[0][1]:
                raiseCLIError(
                    'Local directory %s does not exist' % local_path)
            with open(lprefix, 'wb+') as f:
                yield (f, remotes[0][0])

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    @errors.pithos.object_path
    @errors.pithos.local_path
    def _run(self, local_path):
        poolsize = self['poolsize']
        if poolsize:
            self.client.MAX_THREADS = int(poolsize)
        progress_bar = None
        try:
            for f, rpath in self._outputs(local_path):
                (
                    progress_bar,
                    download_cb) = self._safe_progress_bar(
                        'Download %s' % rpath)
                self.client.download_object(
                    rpath, f,
                    download_cb=download_cb,
                    range_str=self['range'],
                    version=self['object_version'],
                    if_match=self['if_match'],
                    resume=self['resume'],
                    if_none_match=self['if_none_match'],
                    if_modified_since=self['if_modified_since'],
                    if_unmodified_since=self['if_unmodified_since'])
        except KeyboardInterrupt:
            from threading import activeCount, enumerate as activethreads
            timeout = 0.5
            while activeCount() > 1:
                stdout.write('\nCancel %s threads: ' % (activeCount() - 1))
                stdout.flush()
                for thread in activethreads():
                    try:
                        thread.join(timeout)
                        stdout.write('.' if thread.isAlive() else '*')
                    except RuntimeError:
                        continue
                    finally:
                        stdout.flush()
                        timeout += 0.1
            print('\nDownload canceled by user')
            if local_path is not None:
                print('to resume, re-run with --resume')
        except Exception:
            self._safe_progress_bar_finish(progress_bar)
            raise
        finally:
            self._safe_progress_bar_finish(progress_bar)

    def main(self, container___path, local_path=None):
        super(self.__class__, self)._run(container___path)
        self._run(local_path=local_path)


@command(pithos_cmds)
class file_hashmap(_file_container_command, _optional_json):
    """Get the hash-map of an object"""

    arguments = dict(
        if_match=ValueArgument('show output if ETags match', '--if-match'),
        if_none_match=ValueArgument(
            'show output if ETags match', '--if-none-match'),
        if_modified_since=DateArgument(
            'show output modified since then', '--if-modified-since'),
        if_unmodified_since=DateArgument(
            'show output unmodified since then', '--if-unmodified-since'),
        object_version=ValueArgument(
            'get the specific version', ('-O', '--object-version'))
    )

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    @errors.pithos.object_path
    def _run(self):
        self._print(self.client.get_object_hashmap(
            self.path,
            version=self['object_version'],
            if_match=self['if_match'],
            if_none_match=self['if_none_match'],
            if_modified_since=self['if_modified_since'],
            if_unmodified_since=self['if_unmodified_since']), print_dict)

    def main(self, container___path):
        super(self.__class__, self)._run(
            container___path,
            path_is_optional=False)
        self._run()


@command(pithos_cmds)
class file_delete(_file_container_command, _optional_output_cmd):
    """Delete a container [or an object]
    How to delete a non-empty container:
    - empty the container:  /file delete -R <container>
    - delete it:            /file delete <container>
    .
    Semantics of directory deletion:
    .a preserve the contents: /file delete <container>:<directory>
    .    objects of the form dir/filename can exist with a dir object
    .b delete contents:       /file delete -R <container>:<directory>
    .    all dir/* objects are affected, even if dir does not exist
    .
    To restore a deleted object OBJ in a container CONT:
    - get object versions: /file versions CONT:OBJ
    .   and choose the version to be restored
    - restore the object:  /file copy --source-version=<version> CONT:OBJ OBJ
    """

    arguments = dict(
        until=DateArgument('remove history until that date', '--until'),
        yes=FlagArgument('Do not prompt for permission', '--yes'),
        recursive=FlagArgument(
            'empty dir or container and delete (if dir)',
            ('-R', '--recursive'))
    )

    def __init__(self, arguments={}, auth_base=None, cloud=None):
        super(self.__class__, self).__init__(arguments,  auth_base, cloud)
        self['delimiter'] = DelimiterArgument(
            self,
            parsed_name='--delimiter',
            help='delete objects prefixed with <object><delimiter>')

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    @errors.pithos.object_path
    def _run(self):
        if self.path:
            if self['yes'] or ask_user(
                    'Delete %s:%s ?' % (self.container, self.path)):
                self._optional_output(self.client.del_object(
                    self.path,
                    until=self['until'], delimiter=self['delimiter']))
            else:
                print('Aborted')
        elif self.container:
            if self['recursive']:
                ask_msg = 'Delete container contents'
            else:
                ask_msg = 'Delete container'
            if self['yes'] or ask_user('%s %s ?' % (ask_msg, self.container)):
                self._optional_output(self.client.del_container(
                    until=self['until'], delimiter=self['delimiter']))
            else:
                print('Aborted')
        else:
            raiseCLIError('Nothing to delete, please provide container[:path]')

    def main(self, container____path__=None):
        super(self.__class__, self)._run(container____path__)
        self._run()


@command(pithos_cmds)
class file_purge(_file_container_command, _optional_output_cmd):
    """Delete a container and release related data blocks
    Non-empty containers can not purged.
    To purge a container with content:
    .   /file delete -R <container>
    .      objects are deleted, but data blocks remain on server
    .   /file purge <container>
    .      container and data blocks are released and deleted
    """

    arguments = dict(
        yes=FlagArgument('Do not prompt for permission', '--yes'),
        force=FlagArgument('purge even if not empty', ('-F', '--force'))
    )

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    def _run(self):
        if self['yes'] or ask_user('Purge container %s?' % self.container):
            try:
                r = self.client.purge_container()
            except ClientError as ce:
                if ce.status in (409,):
                    if self['force']:
                        self.client.del_container(delimiter='/')
                        r = self.client.purge_container()
                    else:
                        raiseCLIError(ce, details=['Try -F to force-purge'])
                else:
                    raise
            self._optional_output(r)
        else:
            print('Aborted')

    def main(self, container=None):
        super(self.__class__, self)._run(container)
        if container and self.container != container:
            raiseCLIError('Invalid container name %s' % container, details=[
                'Did you mean "%s" ?' % self.container,
                'Use --container for names containing :'])
        self._run()


@command(pithos_cmds)
class file_publish(_file_container_command):
    """Publish the object and print the public url"""

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    @errors.pithos.object_path
    def _run(self):
        print self.client.publish_object(self.path)

    def main(self, container___path):
        super(self.__class__, self)._run(
            container___path, path_is_optional=False)
        self._run()


@command(pithos_cmds)
class file_unpublish(_file_container_command, _optional_output_cmd):
    """Unpublish an object"""

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    @errors.pithos.object_path
    def _run(self):
            self._optional_output(self.client.unpublish_object(self.path))

    def main(self, container___path):
        super(self.__class__, self)._run(
            container___path, path_is_optional=False)
        self._run()


@command(pithos_cmds)
class file_permissions(_pithos_init):
    """Manage user and group accessibility for objects
    Permissions are lists of users and user groups. There are read and write
    permissions. Users and groups with write permission have also read
    permission.
    """


def print_permissions(permissions_dict):
    expected_keys = ('read', 'write')
    if set(permissions_dict).issubset(expected_keys):
        print_dict(permissions_dict)
    else:
        invalid_keys = set(permissions_dict.keys()).difference(expected_keys)
        raiseCLIError(
            'Illegal permission keys: %s' % ', '.join(invalid_keys),
            importance=1, details=[
                'Valid permission types: %s' % ' '.join(expected_keys)])


@command(pithos_cmds)
class file_permissions_get(_file_container_command, _optional_json):
    """Get read and write permissions of an object"""

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    @errors.pithos.object_path
    def _run(self):
        self._print(
            self.client.get_object_sharing(self.path), print_permissions)

    def main(self, container___path):
        super(self.__class__, self)._run(
            container___path, path_is_optional=False)
        self._run()


@command(pithos_cmds)
class file_permissions_set(_file_container_command, _optional_output_cmd):
    """Set permissions for an object
    New permissions overwrite existing permissions.
    Permission format:
    -   read=<username>[,usergroup[,...]]
    -   write=<username>[,usegroup[,...]]
    E.g. to give read permissions for file F to users A and B and write for C:
    .       /file permissions set F read=A,B write=C
    """

    @errors.generic.all
    def format_permission_dict(self, permissions):
        read = False
        write = False
        for perms in permissions:
            splstr = perms.split('=')
            if 'read' == splstr[0]:
                read = [ug.strip() for ug in splstr[1].split(',')]
            elif 'write' == splstr[0]:
                write = [ug.strip() for ug in splstr[1].split(',')]
            else:
                msg = 'Usage:\tread=<groups,users> write=<groups,users>'
                raiseCLIError(None, msg)
        return (read, write)

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    @errors.pithos.object_path
    def _run(self, read, write):
        self._optional_output(self.client.set_object_sharing(
            self.path, read_permission=read, write_permission=write))

    def main(self, container___path, *permissions):
        super(self.__class__, self)._run(
            container___path, path_is_optional=False)
        read, write = self.format_permission_dict(permissions)
        self._run(read, write)


@command(pithos_cmds)
class file_permissions_delete(_file_container_command, _optional_output_cmd):
    """Delete all permissions set on object
    To modify permissions, use /file permissions set
    """

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    @errors.pithos.object_path
    def _run(self):
        self._optional_output(self.client.del_object_sharing(self.path))

    def main(self, container___path):
        super(self.__class__, self)._run(
            container___path, path_is_optional=False)
        self._run()


@command(pithos_cmds)
class file_info(_file_container_command, _optional_json):
    """Get detailed information for user account, containers or objects
    to get account info:    /file info
    to get container info:  /file info <container>
    to get object info:     /file info <container>:<path>
    """

    arguments = dict(
        object_version=ValueArgument(
            'show specific version \ (applies only for objects)',
            ('-O', '--object-version'))
    )

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    @errors.pithos.object_path
    def _run(self):
        if self.container is None:
            r = self.client.get_account_info()
        elif self.path is None:
            r = self.client.get_container_info(self.container)
        else:
            r = self.client.get_object_info(
                self.path, version=self['object_version'])
        self._print(r, print_dict)

    def main(self, container____path__=None):
        super(self.__class__, self)._run(container____path__)
        self._run()


@command(pithos_cmds)
class file_metadata(_pithos_init):
    """Metadata are attached on objects. They are formed as key:value pairs.
    They can have arbitary values.
    """


@command(pithos_cmds)
class file_metadata_get(_file_container_command, _optional_json):
    """Get metadata for account, containers or objects"""

    arguments = dict(
        detail=FlagArgument('show detailed output', ('-l', '--details')),
        until=DateArgument('show metadata until then', '--until'),
        object_version=ValueArgument(
            'show specific version (applies only for objects)',
            ('-O', '--object-version'))
    )

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    @errors.pithos.object_path
    def _run(self):
        until = self['until']
        r = None
        if self.container is None:
            r = self.client.get_account_info(until=until)
        elif self.path is None:
            if self['detail']:
                r = self.client.get_container_info(until=until)
            else:
                cmeta = self.client.get_container_meta(until=until)
                ometa = self.client.get_container_object_meta(until=until)
                r = {}
                if cmeta:
                    r['container-meta'] = cmeta
                if ometa:
                    r['object-meta'] = ometa
        else:
            if self['detail']:
                r = self.client.get_object_info(
                    self.path,
                    version=self['object_version'])
            else:
                r = self.client.get_object_meta(
                    self.path,
                    version=self['object_version'])
        if r:
            self._print(r, print_dict)

    def main(self, container____path__=None):
        super(self.__class__, self)._run(container____path__)
        self._run()


@command(pithos_cmds)
class file_metadata_set(_file_container_command, _optional_output_cmd):
    """Set a piece of metadata for account, container or object"""

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    @errors.pithos.object_path
    def _run(self, metakey, metaval):
        if not self.container:
            r = self.client.set_account_meta({metakey: metaval})
        elif not self.path:
            r = self.client.set_container_meta({metakey: metaval})
        else:
            r = self.client.set_object_meta(self.path, {metakey: metaval})
        self._optional_output(r)

    def main(self, metakey, metaval, container____path__=None):
        super(self.__class__, self)._run(container____path__)
        self._run(metakey=metakey, metaval=metaval)


@command(pithos_cmds)
class file_metadata_delete(_file_container_command, _optional_output_cmd):
    """Delete metadata with given key from account, container or object
    - to get metadata of current account: /file metadata get
    - to get metadata of a container:     /file metadata get <container>
    - to get metadata of an object:       /file metadata get <container>:<path>
    """

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    @errors.pithos.object_path
    def _run(self, metakey):
        if self.container is None:
            r = self.client.del_account_meta(metakey)
        elif self.path is None:
            r = self.client.del_container_meta(metakey)
        else:
            r = self.client.del_object_meta(self.path, metakey)
        self._optional_output(r)

    def main(self, metakey, container____path__=None):
        super(self.__class__, self)._run(container____path__)
        self._run(metakey)


@command(pithos_cmds)
class file_quota(_file_account_command, _optional_json):
    """Get account quota"""

    arguments = dict(
        in_bytes=FlagArgument('Show result in bytes', ('-b', '--bytes'))
    )

    @errors.generic.all
    @errors.pithos.connection
    def _run(self):

        def pretty_print(output):
            if not self['in_bytes']:
                for k in output:
                    output[k] = format_size(output[k])
            print_dict(output, '-')

        self._print(self.client.get_account_quota(), pretty_print)

    def main(self, custom_uuid=None):
        super(self.__class__, self)._run(custom_account=custom_uuid)
        self._run()


@command(pithos_cmds)
class file_containerlimit(_pithos_init):
    """Container size limit commands"""


@command(pithos_cmds)
class file_containerlimit_get(_file_container_command, _optional_json):
    """Get container size limit"""

    arguments = dict(
        in_bytes=FlagArgument('Show result in bytes', ('-b', '--bytes'))
    )

    @errors.generic.all
    @errors.pithos.container
    def _run(self):

        def pretty_print(output):
            if not self['in_bytes']:
                for k, v in output.items():
                    output[k] = 'unlimited' if '0' == v else format_size(v)
            print_dict(output, '-')

        self._print(
            self.client.get_container_limit(self.container), pretty_print)

    def main(self, container=None):
        super(self.__class__, self)._run()
        self.container = container
        self._run()


@command(pithos_cmds)
class file_containerlimit_set(_file_account_command, _optional_output_cmd):
    """Set new storage limit for a container
    By default, the limit is set in bytes
    Users may specify a different unit, e.g:
    /file containerlimit set 2.3GB mycontainer
    Valid units: B, KiB (1024 B), KB (1000 B), MiB, MB, GiB, GB, TiB, TB
    To set container limit to "unlimited", use 0
    """

    @errors.generic.all
    def _calculate_limit(self, user_input):
        limit = 0
        try:
            limit = int(user_input)
        except ValueError:
            index = 0
            digits = [str(num) for num in range(0, 10)] + ['.']
            while user_input[index] in digits:
                index += 1
            limit = user_input[:index]
            format = user_input[index:]
            try:
                return to_bytes(limit, format)
            except Exception as qe:
                msg = 'Failed to convert %s to bytes' % user_input,
                raiseCLIError(qe, msg, details=[
                    'Syntax: containerlimit set <limit>[format] [container]',
                    'e.g.: containerlimit set 2.3GB mycontainer',
                    'Valid formats:',
                    '(*1024): B, KiB, MiB, GiB, TiB',
                    '(*1000): B, KB, MB, GB, TB'])
        return limit

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    def _run(self, limit):
        if self.container:
            self.client.container = self.container
        self._optional_output(self.client.set_container_limit(limit))

    def main(self, limit, container=None):
        super(self.__class__, self)._run()
        limit = self._calculate_limit(limit)
        self.container = container
        self._run(limit)


@command(pithos_cmds)
class file_versioning(_pithos_init):
    """Manage the versioning scheme of current pithos user account"""


@command(pithos_cmds)
class file_versioning_get(_file_account_command, _optional_json):
    """Get  versioning for account or container"""

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    def _run(self):
        self._print(
            self.client.get_container_versioning(self.container), print_dict)

    def main(self, container):
        super(self.__class__, self)._run()
        self.container = container
        self._run()


@command(pithos_cmds)
class file_versioning_set(_file_account_command, _optional_output_cmd):
    """Set versioning mode (auto, none) for account or container"""

    def _check_versioning(self, versioning):
        if versioning and versioning.lower() in ('auto', 'none'):
            return versioning.lower()
        raiseCLIError('Invalid versioning %s' % versioning, details=[
            'Versioning can be auto or none'])

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    def _run(self, versioning):
        self.client.container = self.container
        r = self.client.set_container_versioning(versioning)
        self._optional_output(r)

    def main(self, versioning, container):
        super(self.__class__, self)._run()
        self._run(self._check_versioning(versioning))


@command(pithos_cmds)
class file_group(_pithos_init):
    """Manage access groups and group members"""


@command(pithos_cmds)
class file_group_list(_file_account_command, _optional_json):
    """list all groups and group members"""

    @errors.generic.all
    @errors.pithos.connection
    def _run(self):
        self._print(self.client.get_account_group(), print_dict, delim='-')

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(pithos_cmds)
class file_group_set(_file_account_command, _optional_output_cmd):
    """Set a user group"""

    @errors.generic.all
    @errors.pithos.connection
    def _run(self, groupname, *users):
        self._optional_output(self.client.set_account_group(groupname, users))

    def main(self, groupname, *users):
        super(self.__class__, self)._run()
        if users:
            self._run(groupname, *users)
        else:
            raiseCLIError('No users to add in group %s' % groupname)


@command(pithos_cmds)
class file_group_delete(_file_account_command, _optional_output_cmd):
    """Delete a user group"""

    @errors.generic.all
    @errors.pithos.connection
    def _run(self, groupname):
        self._optional_output(self.client.del_account_group(groupname))

    def main(self, groupname):
        super(self.__class__, self)._run()
        self._run(groupname)


@command(pithos_cmds)
class file_sharers(_file_account_command, _optional_json):
    """List the accounts that share objects with current user"""

    arguments = dict(
        detail=FlagArgument('show detailed output', ('-l', '--details')),
        marker=ValueArgument('show output greater then marker', '--marker')
    )

    @errors.generic.all
    @errors.pithos.connection
    def _run(self):
        accounts = self.client.get_sharing_accounts(marker=self['marker'])
        if not self['json_output']:
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


def version_print(versions):
    print_items([dict(id=vitem[0], created=strftime(
            '%d-%m-%Y %H:%M:%S',
            localtime(float(vitem[1])))) for vitem in versions])


@command(pithos_cmds)
class file_versions(_file_container_command, _optional_json):
    """Get the list of object versions
    Deleted objects may still have versions that can be used to restore it and
    get information about its previous state.
    The version number can be used in a number of other commands, like info,
    copy, move, meta. See these commands for more information, e.g.
    /file info -h
    """

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    @errors.pithos.object_path
    def _run(self):
        self._print(
            self.client.get_object_versionlist(self.path), version_print)

    def main(self, container___path):
        super(file_versions, self)._run(
            container___path,
            path_is_optional=False)
        self._run()
