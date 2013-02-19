# Copyright 2011-2012 GRNET S.A. All rights reserved.
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
from logging import getLogger
from os import path, makedirs

from kamaki.cli import command
from kamaki.cli.command_tree import CommandTree
from kamaki.cli.errors import raiseCLIError, CLISyntaxError
from kamaki.cli.utils import (
    format_size,
    to_bytes,
    print_dict,
    print_items,
    pretty_keys,
    page_hold,
    bold,
    ask_user)
from kamaki.cli.argument import FlagArgument, ValueArgument, IntArgument
from kamaki.cli.argument import KeyValueArgument, DateArgument
from kamaki.cli.argument import ProgressBarArgument
from kamaki.cli.commands import _command_init, errors
from kamaki.clients.pithos import PithosClient, ClientError
from kamaki.clients.astakos import AstakosClient


kloger = getLogger('kamaki')

pithos_cmds = CommandTree('store', 'Pithos+ storage commands')
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
    def value(self, newvalue):
        if newvalue is None:
            self._value = self.default
            return
        (start, end) = newvalue.split('-')
        (start, end) = (int(start), int(end))
        self._value = '%s-%s' % (start, end)

# Command specs


class _pithos_init(_command_init):
    """Initialize a pithos+ kamaki client"""

    @errors.generic.all
    def _run(self):
        self.token = self.config.get('store', 'token')\
            or self.config.get('global', 'token')
        self.base_url = self.config.get('store', 'url')\
            or self.config.get('global', 'url')
        self._set_account()
        self.container = self.config.get('store', 'container')\
            or self.config.get('global', 'container')
        self.client = PithosClient(
            base_url=self.base_url,
            token=self.token,
            account=self.account,
            container=self.container)

    def main(self):
        self._run()

    def _set_account(self):
        astakos = AstakosClient(self.config.get('astakos', 'url'), self.token)
        self.account = self['account'] or astakos.term('uuid')

        """Backwards compatibility"""
        self.account = self.account\
            or self.config.get('store', 'account')\
            or self.config.get('global', 'account')


class _store_account_command(_pithos_init):
    """Base class for account level storage commands"""

    def __init__(self, arguments={}):
        super(_store_account_command, self).__init__(arguments)
        self['account'] = ValueArgument(
            'Set user account (not permanent)',
            '--account')

    def _run(self):
        super(_store_account_command, self)._run()
        if self['account']:
            self.client.account = self['account']

    @errors.generic.all
    def main(self):
        self._run()


class _store_container_command(_store_account_command):
    """Base class for container level storage commands"""

    container = None
    path = None

    def __init__(self, arguments={}):
        super(_store_container_command, self).__init__(arguments)
        self['container'] = ValueArgument(
            'Set container to work with (temporary)',
            '--container')

    @errors.generic.all
    def _dest_container_path(self, dest_container_path):
        if self['destination_container']:
            return (self['destination_container'], dest_container_path)
        dst = dest_container_path.split(':')
        return (dst[0], dst[1]) if len(dst) > 1 else (None, dst[0])

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
        super(_store_container_command, self)._run()
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
class store_list(_store_container_command):
    """List containers, object trees or objects in a directory
    Use with:
    1 no parameters : containers in current account
    2. one parameter (container) or --container : contents of container
    3. <container>:<prefix> or --container=<container> <prefix>: objects in
    .   container starting with prefix
    """

    arguments = dict(
        detail=FlagArgument('show detailed output', '-l'),
        limit=IntArgument('limit the number of listed items', '-n'),
        marker=ValueArgument('show output greater that marker', '--marker'),
        prefix=ValueArgument('show output starting with prefix', '--prefix'),
        delimiter=ValueArgument('show output up to delimiter', '--delimiter'),
        path=ValueArgument(
            'show output starting with prefix up to /',
            '--path'),
        meta=ValueArgument(
            'show output with specified meta keys',
            '--meta',
            default=[]),
        if_modified_since=ValueArgument(
            'show output modified since then',
            '--if-modified-since'),
        if_unmodified_since=ValueArgument(
            'show output not modified since then',
            '--if-unmodified-since'),
        until=DateArgument('show metadata until then', '--until'),
        format=ValueArgument(
            'format to parse until data (default: d/m/Y H:M:S )',
            '--format'),
        shared=FlagArgument('show only shared', '--shared'),
        public=FlagArgument('show only public', '--public'),
        more=FlagArgument(
            'output results in pages (-n to set items per page, default 10)',
            '--more'),
        exact_match=FlagArgument(
            'Show only objects that match exactly with path',
            '--exact-match')
    )

    def print_objects(self, object_list):
        limit = int(self['limit']) if self['limit'] > 0 else len(object_list)
        for index, obj in enumerate(object_list):
            if self['exact_match'] and self.path and not (
                    obj['name'] == self.path or 'content_type' in obj):
                continue
            pretty_obj = obj.copy()
            index += 1
            empty_space = ' ' * (len(str(len(object_list))) - len(str(index)))
            if obj['content_type'] == 'application/directory':
                isDir = True
                size = 'D'
            else:
                isDir = False
                size = format_size(obj['bytes'])
                pretty_obj['bytes'] = '%s (%s)' % (obj['bytes'], size)
            oname = bold(obj['name'])
            if self['detail']:
                print('%s%s. %s' % (empty_space, index, oname))
                print_dict(pretty_keys(pretty_obj), exclude=('name'))
                print
            else:
                oname = '%s%s. %6s %s' % (empty_space, index, size, oname)
                oname += '/' if isDir else ''
                print(oname)
            if self['more']:
                page_hold(index, limit, len(object_list))

    def print_containers(self, container_list):
        limit = int(self['limit']) if self['limit'] > 0\
            else len(container_list)
        for index, container in enumerate(container_list):
            if 'bytes' in container:
                size = format_size(container['bytes'])
            cname = '%s. %s' % (index + 1, bold(container['name']))
            if self['detail']:
                print(cname)
                pretty_c = container.copy()
                if 'bytes' in container:
                    pretty_c['bytes'] = '%s (%s)' % (container['bytes'], size)
                print_dict(pretty_keys(pretty_c), exclude=('name'))
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
            self.print_containers(r.json)
        else:
            prefix = self.path or self['prefix']
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
            self.print_objects(r.json)

    def main(self, container____path__=None):
        super(self.__class__, self)._run(container____path__)
        self._run()


@command(pithos_cmds)
class store_mkdir(_store_container_command):
    """Create a directory"""

    __doc__ += '\n. '.join([
        'Kamaki hanldes directories the same way as OOS Storage and Pithos+:',
        'A   directory  is   an  object  with  type  "application/directory"',
        'An object with path  dir/name can exist even if  dir does not exist',
        'or even if dir  is  a non  directory  object.  Users can modify dir',
        'without affecting the dir/name object in any way.'])

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    def _run(self):
        self.client.create_directory(self.path)

    def main(self, container___directory):
        super(self.__class__, self)._run(
            container___directory,
            path_is_optional=False)
        self._run()


@command(pithos_cmds)
class store_touch(_store_container_command):
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
        self.client.create_object(self.path, self['content_type'])

    def main(self, container___path):
        super(store_touch, self)._run(
            container___path,
            path_is_optional=False)
        self._run()


@command(pithos_cmds)
class store_create(_store_container_command):
    """Create a container"""

    arguments = dict(
        versioning=ValueArgument(
            'set container versioning (auto/none)',
            '--versioning'),
        quota=IntArgument('set default container quota', '--quota'),
        meta=KeyValueArgument(
            'set container metadata (can be repeated)',
            '--meta')
    )

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    def _run(self):
        self.client.container_put(
            quota=self['quota'],
            versioning=self['versioning'],
            metadata=self['meta'])

    def main(self, container=None):
        super(self.__class__, self)._run(container)
        if container and self.container != container:
            raiseCLIError('Invalid container name %s' % container, details=[
                'Did you mean "%s" ?' % self.container,
                'Use --container for names containing :'])
        self._run()


@command(pithos_cmds)
class store_copy(_store_container_command):
    """Copy objects from container to (another) container
    Semantics:
    copy cont:path path2
    .   will copy all <obj> prefixed with path, as path2<obj>
    .   or as path2 if path corresponds to just one whole object
    copy cont:path cont2:
    .   will copy all <obj> prefixed with path to container cont2
    copy cont:path [cont2:]path2 --exact-match
    .   will copy at most one <obj> as a new object named path2,
    .   provided path corresponds to a whole object path
    copy cont:path [cont2:]path2 --replace
    .   will copy all <obj> prefixed with path, replacing path with path2
    where <obj> is a full file or directory object path.
    Use options:
    1. <container1>:<path1> [container2:]<path2> : if container2 is not given,
    destination is container1:path2
    2. <container>:<path1> <path2> : make a copy in the same container
    3. Can use --container= instead of <container1>
    """

    arguments = dict(
        destination_container=ValueArgument(
            'use it if destination container name contains a : character',
            '--dst-container'),
        source_version=ValueArgument(
            'copy specific version',
            '--source-version'),
        public=ValueArgument('make object publicly accessible', '--public'),
        content_type=ValueArgument(
            'change object\'s content type',
            '--content-type'),
        recursive=FlagArgument(
            'mass copy with delimiter /',
            ('-r', '--recursive')),
        exact_match=FlagArgument(
            'Copy only the object that fully matches path',
            '--exact-match'),
        replace=FlagArgument('Replace src. path with dst. path', '--replace')
    )

    def _objlist(self, dst_path):
        if self['exact_match']:
            return [(dst_path or self.path, self.path)]
        r = self.client.container_get(prefix=self.path)
        if len(r.json) == 1:
            obj = r.json[0]
            return [(obj['name'], dst_path or obj['name'])]
        start = len(self.path) if self['replace'] else 0
        return [(obj['name'], '%s%s' % (
            dst_path,
            obj['name'][start:])) for obj in r.json]

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    def _run(self, dst_cont, dst_path):
        no_source_object = True
        for src_object, dst_object in self._objlist(dst_path):
            no_source_object = False
            self.client.copy_object(
                src_container=self.container,
                src_object=src_object,
                dst_container=dst_cont or self.container,
                dst_object=dst_object,
                source_version=self['source_version'],
                public=self['public'],
                content_type=self['content_type'])
        if no_source_object:
            raiseCLIError('No object %s in container %s' % (
                self.path,
                self.container))

    def main(
            self,
            source_container___path,
            destination_container___path=None):
        super(self.__class__, self)._run(
            source_container___path,
            path_is_optional=False)
        (dst_cont, dst_path) = self._dest_container_path(
            destination_container___path)
        self._run(dst_cont=dst_cont, dst_path=dst_path or '')


@command(pithos_cmds)
class store_move(_store_container_command):
    """Move/rename objects
    Semantics:
    move cont:path path2
    .   will move all <obj> prefixed with path, as path2<obj>
    .   or as path2 if path corresponds to just one whole object
    move cont:path cont2:
    .   will move all <obj> prefixed with path to container cont2
    move cont:path [cont2:]path2 --exact-match
    .   will move at most one <obj> as a new object named path2,
    .   provided path corresponds to a whole object path
    move cont:path [cont2:]path2 --replace
    .   will move all <obj> prefixed with path, replacing path with path2
    where <obj> is a full file or directory object path.
    Use options:
    1. <container1>:<path1> [container2:]<path2> : if container2 not given,
    destination is container1:path2
    2. <container>:<path1> path2 : rename
    3. Can use --container= instead of <container1>
    """

    arguments = dict(
        destination_container=ValueArgument(
            'use it if destination container name contains a : character',
            '--dst-container'),
        source_version=ValueArgument('specify version', '--source-version'),
        public=FlagArgument('make object publicly accessible', '--public'),
        content_type=ValueArgument('modify content type', '--content-type'),
        recursive=FlagArgument('up to delimiter /', ('-r', '--recursive')),
        exact_match=FlagArgument(
            'Copy only the object that fully matches path',
            '--exact-match'),
        replace=FlagArgument('Replace src. path with dst. path', '--replace')
    )

    def _objlist(self, dst_path):
        if self['exact_match']:
            return [(dst_path or self.path, self.path)]
        r = self.client.container_get(prefix=self.path)
        if len(r.json) == 1:
            obj = r.json[0]
            return [(obj['name'], dst_path or obj['name'])]
        return [(
            obj['name'],
            '%s%s' % (
                dst_path,
                obj['name'][len(self.path) if self['replace'] else 0:]
            )) for obj in r.json]

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    def _run(self, dst_cont, dst_path):
        no_source_object = True
        for src_object, dst_object in self._objlist(dst_path):
            no_source_object = False
            self.client.move_object(
                src_container=self.container,
                src_object=src_object,
                dst_container=dst_cont or self.container,
                dst_object=dst_object,
                source_version=self['source_version'],
                public=self['public'],
                content_type=self['content_type'])
        if no_source_object:
            raiseCLIError('No object %s in container %s' % (
                self.path,
                self.container))

    def main(
            self,
            source_container___path,
            destination_container___path=None):
        super(self.__class__, self)._run(
            source_container___path,
            path_is_optional=False)
        (dst_cont, dst_path) = self._dest_container_path(
            destination_container___path)
        self._run(dst_cont=dst_cont, dst_path=dst_path or '')


@command(pithos_cmds)
class store_append(_store_container_command):
    """Append local file to (existing) remote object
    The remote object should exist.
    If the remote object is a directory, it is transformed into a file.
    In the later case, objects under the directory remain intact.
    """

    arguments = dict(
        progress_bar=ProgressBarArgument(
            'do not show progress bar',
            '--no-progress-bar',
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
            self.client.append_object(self.path, f, upload_cb)
        except Exception:
            self._safe_progress_bar_finish(progress_bar)
            raise
        finally:
            self._safe_progress_bar_finish(progress_bar)

    def main(self, local_path, container___path):
        super(self.__class__, self)._run(
            container___path,
            path_is_optional=False)
        self._run(local_path)


@command(pithos_cmds)
class store_truncate(_store_container_command):
    """Truncate remote file up to a size (default is 0)"""

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    @errors.pithos.object_path
    @errors.pithos.object_size
    def _run(self, size=0):
        self.client.truncate_object(self.path, size)

    def main(self, container___path, size=0):
        super(self.__class__, self)._run(container___path)
        self._run(size=size)


@command(pithos_cmds)
class store_overwrite(_store_container_command):
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
            '--no-progress-bar',
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
            self.client.overwrite_object(
                obj=self.path,
                start=start,
                end=end,
                source_file=f,
                upload_cb=upload_cb)
        except Exception:
            self._safe_progress_bar_finish(progress_bar)
            raise
        finally:
            self._safe_progress_bar_finish(progress_bar)

    def main(self, local_path, container___path, start, end):
        super(self.__class__, self)._run(
            container___path,
            path_is_optional=None)
        self.path = self.path or path.basename(local_path)
        self._run(local_path=local_path, start=start, end=end)


@command(pithos_cmds)
class store_manifest(_store_container_command):
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
            'set MIME content type',
            '--content-encoding'),
        content_disposition=ValueArgument(
            'the presentation style of the object',
            '--content-disposition'),
        content_type=ValueArgument(
            'specify content type',
            '--content-type',
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
        self.client.create_object_by_manifestation(
            self.path,
            content_encoding=self['content_encoding'],
            content_disposition=self['content_disposition'],
            content_type=self['content_type'],
            sharing=self['sharing'],
            public=self['public'])

    def main(self, container___path):
        super(self.__class__, self)._run(
            container___path,
            path_is_optional=False)
        self.run()


@command(pithos_cmds)
class store_upload(_store_container_command):
    """Upload a file"""

    arguments = dict(
        use_hashes=FlagArgument(
            'provide hashmap file instead of data',
            '--use-hashes'),
        etag=ValueArgument('check written data', '--etag'),
        unchunked=FlagArgument('avoid chunked transfer mode', '--unchunked'),
        content_encoding=ValueArgument(
            'set MIME content type',
            '--content-encoding'),
        content_disposition=ValueArgument(
            'specify objects presentation style',
            '--content-disposition'),
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
            '--no-progress-bar',
            default=False),
        overwrite=FlagArgument('Force overwrite, if object exists', '-f')
    )

    def _remote_path(self, remote_path, local_path=''):
        if self['overwrite']:
            return remote_path
        try:
            r = self.client.get_object_info(remote_path)
        except ClientError as ce:
            if ce.status == 404:
                return remote_path
            raise ce
        ctype = r.get('content-type', '')
        if 'application/directory' == ctype.lower():
            ret = '%s/%s' % (remote_path, local_path)
            return self._remote_path(ret) if local_path else ret
        raiseCLIError(
            'Object %s already exists' % remote_path,
            importance=1,
            details=['use -f to overwrite or resume'])

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    @errors.pithos.object_path
    @errors.pithos.local_path
    def _run(self, local_path, remote_path):
        poolsize = self['poolsize']
        if poolsize > 0:
            self.client.POOL_SIZE = int(poolsize)
        params = dict(
            content_encoding=self['content_encoding'],
            content_type=self['content_type'],
            content_disposition=self['content_disposition'],
            sharing=self['sharing'],
            public=self['public'])
        remote_path = self._remote_path(remote_path, local_path)
        with open(path.abspath(local_path), 'rb') as f:
            if self['unchunked']:
                self.client.upload_object_unchunked(
                    remote_path,
                    f,
                    etag=self['etag'],
                    withHashFile=self['use_hashes'],
                    **params)
            else:
                try:
                    (progress_bar, upload_cb) = self._safe_progress_bar(
                        'Uploading')
                    if progress_bar:
                        hash_bar = progress_bar.clone()
                        hash_cb = hash_bar.get_generator(
                            'Calculating block hashes'
                        )
                    else:
                        hash_cb = None
                    self.client.upload_object(
                        remote_path,
                        f,
                        hash_cb=hash_cb,
                        upload_cb=upload_cb,
                        **params)
                except Exception:
                    self._safe_progress_bar_finish(progress_bar)
                    raise
                finally:
                    self._safe_progress_bar_finish(progress_bar)
        print 'Upload completed'

    def main(self, local_path, container____path__=None):
        super(self.__class__, self)._run(container____path__)
        remote_path = self.path or path.basename(local_path)
        self._run(local_path=local_path, remote_path=remote_path)


@command(pithos_cmds)
class store_cat(_store_container_command):
    """Print remote file contents to console"""

    arguments = dict(
        range=RangeArgument('show range of data', '--range'),
        if_match=ValueArgument('show output if ETags match', '--if-match'),
        if_none_match=ValueArgument(
            'show output if ETags match',
            '--if-none-match'),
        if_modified_since=DateArgument(
            'show output modified since then',
            '--if-modified-since'),
        if_unmodified_since=DateArgument(
            'show output unmodified since then',
            '--if-unmodified-since'),
        object_version=ValueArgument(
            'get the specific version',
            '--object-version')
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
            container___path,
            path_is_optional=False)
        self._run()


@command(pithos_cmds)
class store_download(_store_container_command):
    """Download remote object as local file
    If local destination is a directory:
    *   download <container>:<path> <local dir> -r
    will download all files on <container> prefixed as <path>,
    to <local dir>/<full path>
    *   download <container>:<path> <local dir> --exact-match
    will download only one file, exactly matching <path>
    ATTENTION: to download cont:dir1/dir2/file there must exist objects
    cont:dir1 and cont:dir1/dir2 of type application/directory
    To create directory objects, use /store mkdir
    """

    arguments = dict(
        resume=FlagArgument('Resume instead of overwrite', '--resume'),
        range=RangeArgument('show range of data', '--range'),
        if_match=ValueArgument('show output if ETags match', '--if-match'),
        if_none_match=ValueArgument(
            'show output if ETags match',
            '--if-none-match'),
        if_modified_since=DateArgument(
            'show output modified since then',
            '--if-modified-since'),
        if_unmodified_since=DateArgument(
            'show output unmodified since then',
            '--if-unmodified-since'),
        object_version=ValueArgument(
            'get the specific version',
            '--object-version'),
        poolsize=IntArgument('set pool size', '--with-pool-size'),
        progress_bar=ProgressBarArgument(
            'do not show progress bar',
            '--no-progress-bar',
            default=False),
        recursive=FlagArgument(
            'Download a remote path and all its contents',
            '--recursive')
    )

    @staticmethod
    def _is_dir(remote_dict):
        return 'application/directory' == remote_dict.get(
            'content_type',
            remote_dict.get('content-type', ''))

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
                remotes.append((rname, store_download._is_dir(remote)))
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
            if store_download._is_dir(r):
                raiseCLIError(
                    'Illegal download: Remote object %s is a directory' % (
                        self.path),
                    details=['To download a directory, try --recursive'])
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
                        self.path,
                        self.container),
                    details=[
                        'To list the contents of %s, try:' % self.container,
                        '   /store list %s' % self.container])
            raiseCLIError(
                'Illegal download of container %s' % self.container,
                details=[
                    'To download a whole container, try:',
                    '   /store download --recursive <container>'])

        lprefix = path.abspath(local_path or path.curdir)
        if path.isdir(lprefix):
            for rpath, remote_is_dir in remotes:
                lpath = '/%s/%s' % (lprefix.strip('/'), rpath.strip('/'))
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
        #outputs = self._outputs(local_path)
        poolsize = self['poolsize']
        if poolsize:
            self.client.POOL_SIZE = int(poolsize)
        progress_bar = None
        try:
            for f, rpath in self._outputs(local_path):
                (
                    progress_bar,
                    download_cb) = self._safe_progress_bar(
                        'Download %s' % rpath)
                self.client.download_object(
                    rpath,
                    f,
                    download_cb=download_cb,
                    range_str=self['range'],
                    version=self['object_version'],
                    if_match=self['if_match'],
                    resume=self['resume'],
                    if_none_match=self['if_none_match'],
                    if_modified_since=self['if_modified_since'],
                    if_unmodified_since=self['if_unmodified_since'])
        except KeyboardInterrupt:
            from threading import enumerate as activethreads
            stdout.write('\nFinishing active threads ')
            for thread in activethreads():
                stdout.flush()
                try:
                    thread.join()
                    stdout.write('.')
                except RuntimeError:
                    continue
            print('\ndownload canceled by user')
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
class store_hashmap(_store_container_command):
    """Get the hash-map of an object"""

    arguments = dict(
        if_match=ValueArgument('show output if ETags match', '--if-match'),
        if_none_match=ValueArgument(
            'show output if ETags match',
            '--if-none-match'),
        if_modified_since=DateArgument(
            'show output modified since then',
            '--if-modified-since'),
        if_unmodified_since=DateArgument(
            'show output unmodified since then',
            '--if-unmodified-since'),
        object_version=ValueArgument(
            'get the specific version',
            '--object-version')
    )

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    @errors.pithos.object_path
    def _run(self):
        data = self.client.get_object_hashmap(
            self.path,
            version=self['object_version'],
            if_match=self['if_match'],
            if_none_match=self['if_none_match'],
            if_modified_since=self['if_modified_since'],
            if_unmodified_since=self['if_unmodified_since'])
        print_dict(data)

    def main(self, container___path):
        super(self.__class__, self)._run(
            container___path,
            path_is_optional=False)
        self._run()


@command(pithos_cmds)
class store_delete(_store_container_command):
    """Delete a container [or an object]
    How to delete a non-empty container:
    - empty the container:  /store delete -r <container>
    - delete it:            /store delete <container>
    .
    Semantics of directory deletion:
    .a preserve the contents: /store delete <container>:<directory>
    .    objects of the form dir/filename can exist with a dir object
    .b delete contents:       /store delete -r <container>:<directory>
    .    all dir/* objects are affected, even if dir does not exist
    .
    To restore a deleted object OBJ in a container CONT:
    - get object versions: /store versions CONT:OBJ
    .   and choose the version to be restored
    - restore the object:  /store copy --source-version=<version> CONT:OBJ OBJ
    """

    arguments = dict(
        until=DateArgument('remove history until that date', '--until'),
        yes=FlagArgument('Do not prompt for permission', '--yes'),
        recursive=FlagArgument(
            'empty dir or container and delete (if dir)',
            ('-r', '--recursive'))
    )

    def __init__(self, arguments={}):
        super(self.__class__, self).__init__(arguments)
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
                self.client.del_object(
                    self.path,
                    until=self['until'],
                    delimiter=self['delimiter'])
            else:
                print('Aborted')
        else:
            if self['recursive']:
                ask_msg = 'Delete container contents'
            else:
                ask_msg = 'Delete container'
            if self['yes'] or ask_user('%s %s ?' % (ask_msg, self.container)):
                self.client.del_container(
                    until=self['until'],
                    delimiter=self['delimiter'])
            else:
                print('Aborted')

    def main(self, container____path__=None):
        super(self.__class__, self)._run(container____path__)
        self._run()


@command(pithos_cmds)
class store_purge(_store_container_command):
    """Delete a container and release related data blocks
    Non-empty containers can not purged.
    To purge a container with content:
    .   /store delete -r <container>
    .      objects are deleted, but data blocks remain on server
    .   /store purge <container>
    .      container and data blocks are released and deleted
    """

    arguments = dict(
        yes=FlagArgument('Do not prompt for permission', '--yes'),
    )

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    def _run(self):
        if self['yes'] or ask_user('Purge container %s?' % self.container):
                self.client.purge_container()
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
class store_publish(_store_container_command):
    """Publish the object and print the public url"""

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    @errors.pithos.object_path
    def _run(self):
        url = self.client.publish_object(self.path)
        print(url)

    def main(self, container___path):
        super(self.__class__, self)._run(
            container___path,
            path_is_optional=False)
        self._run()


@command(pithos_cmds)
class store_unpublish(_store_container_command):
    """Unpublish an object"""

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    @errors.pithos.object_path
    def _run(self):
            self.client.unpublish_object(self.path)

    def main(self, container___path):
        super(self.__class__, self)._run(
            container___path,
            path_is_optional=False)
        self._run()


@command(pithos_cmds)
class store_permissions(_store_container_command):
    """Get read and write permissions of an object
    Permissions are lists of users and user groups. There is read and write
    permissions. Users and groups with write permission have also read
    permission.
    """

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    @errors.pithos.object_path
    def _run(self):
        r = self.client.get_object_sharing(self.path)
        print_dict(r)

    def main(self, container___path):
        super(self.__class__, self)._run(
            container___path,
            path_is_optional=False)
        self._run()


@command(pithos_cmds)
class store_setpermissions(_store_container_command):
    """Set permissions for an object
    New permissions overwrite existing permissions.
    Permission format:
    -   read=<username>[,usergroup[,...]]
    -   write=<username>[,usegroup[,...]]
    E.g. to give read permissions for file F to users A and B and write for C:
    .       /store setpermissions F read=A,B write=C
    """

    @errors.generic.all
    def format_permition_dict(self, permissions):
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
        self.client.set_object_sharing(
            self.path,
            read_permition=read,
            write_permition=write)

    def main(self, container___path, *permissions):
        super(self.__class__, self)._run(
            container___path,
            path_is_optional=False)
        (read, write) = self.format_permition_dict(permissions)
        self._run(read, write)


@command(pithos_cmds)
class store_delpermissions(_store_container_command):
    """Delete all permissions set on object
    To modify permissions, use /store setpermssions
    """

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    @errors.pithos.object_path
    def _run(self):
        self.client.del_object_sharing(self.path)

    def main(self, container___path):
        super(self.__class__, self)._run(
            container___path,
            path_is_optional=False)
        self._run()


@command(pithos_cmds)
class store_info(_store_container_command):
    """Get detailed information for user account, containers or objects
    to get account info:    /store info
    to get container info:  /store info <container>
    to get object info:     /store info <container>:<path>
    """

    arguments = dict(
        object_version=ValueArgument(
            'show specific version \ (applies only for objects)',
            '--object-version')
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
                self.path,
                version=self['object_version'])
        print_dict(r)

    def main(self, container____path__=None):
        super(self.__class__, self)._run(container____path__)
        self._run()


@command(pithos_cmds)
class store_meta(_store_container_command):
    """Get metadata for account, containers or objects"""

    arguments = dict(
        detail=FlagArgument('show detailed output', '-l'),
        until=DateArgument('show metadata until then', '--until'),
        object_version=ValueArgument(
            'show specific version \ (applies only for objects)',
            '--object-version')
    )

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    @errors.pithos.object_path
    def _run(self):
        until = self['until']
        if self.container is None:
            if self['detail']:
                r = self.client.get_account_info(until=until)
            else:
                r = self.client.get_account_meta(until=until)
                r = pretty_keys(r, '-')
            if r:
                print(bold(self.client.account))
        elif self.path is None:
            if self['detail']:
                r = self.client.get_container_info(until=until)
            else:
                cmeta = self.client.get_container_meta(until=until)
                ometa = self.client.get_container_object_meta(until=until)
                r = {}
                if cmeta:
                    r['container-meta'] = pretty_keys(cmeta, '-')
                if ometa:
                    r['object-meta'] = pretty_keys(ometa, '-')
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
                r = pretty_keys(pretty_keys(r, '-'))
        if r:
            print_dict(r)

    def main(self, container____path__=None):
        super(self.__class__, self)._run(container____path__)
        self._run()


@command(pithos_cmds)
class store_setmeta(_store_container_command):
    """Set a piece of metadata for account, container or object
    Metadata are formed as key:value pairs
    """

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    @errors.pithos.object_path
    def _run(self, metakey, metaval):
        if not self.container:
            self.client.set_account_meta({metakey: metaval})
        elif not self.path:
            self.client.set_container_meta({metakey: metaval})
        else:
            self.client.set_object_meta(self.path, {metakey: metaval})

    def main(self, metakey, metaval, container____path__=None):
        super(self.__class__, self)._run(container____path__)
        self._run(metakey=metakey, metaval=metaval)


@command(pithos_cmds)
class store_delmeta(_store_container_command):
    """Delete metadata with given key from account, container or object
    Metadata are formed as key:value objects
    - to get metadata of current account:     /store meta
    - to get metadata of a container:         /store meta <container>
    - to get metadata of an object:           /store meta <container>:<path>
    """

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    @errors.pithos.object_path
    def _run(self, metakey):
        if self.container is None:
            self.client.del_account_meta(metakey)
        elif self.path is None:
            self.client.del_container_meta(metakey)
        else:
            self.client.del_object_meta(self.path, metakey)

    def main(self, metakey, container____path__=None):
        super(self.__class__, self)._run(container____path__)
        self._run(metakey)


@command(pithos_cmds)
class store_quota(_store_account_command):
    """Get quota for account or container"""

    arguments = dict(
        in_bytes=FlagArgument('Show result in bytes', ('-b', '--bytes'))
    )

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    def _run(self):
        if self.container:
            reply = self.client.get_container_quota(self.container)
        else:
            reply = self.client.get_account_quota()
        if not self['in_bytes']:
            for k in reply:
                reply[k] = format_size(reply[k])
        print_dict(pretty_keys(reply, '-'))

    def main(self, container=None):
        super(self.__class__, self)._run()
        self.container = container
        self._run()


@command(pithos_cmds)
class store_setquota(_store_account_command):
    """Set new quota for account or container
    By default, quota is set in bytes
    Users may specify a different unit, e.g:
    /store setquota 2.3GB mycontainer
    Accepted units: B, KiB (1024 B), KB (1000 B), MiB, MB, GiB, GB, TiB, TB
    """

    @errors.generic.all
    def _calculate_quota(self, user_input):
        quota = 0
        try:
            quota = int(user_input)
        except ValueError:
            index = 0
            digits = [str(num) for num in range(0, 10)] + ['.']
            while user_input[index] in digits:
                index += 1
            quota = user_input[:index]
            format = user_input[index:]
            try:
                return to_bytes(quota, format)
            except Exception as qe:
                msg = 'Failed to convert %s to bytes' % user_input,
                raiseCLIError(qe, msg, details=[
                    'Syntax: setquota <quota>[format] [container]',
                    'e.g.: setquota 2.3GB mycontainer',
                    'Acceptable formats:',
                    '(*1024): B, KiB, MiB, GiB, TiB',
                    '(*1000): B, KB, MB, GB, TB'])
        return quota

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    def _run(self, quota):
        if self.container:
            self.client.container = self.container
            self.client.set_container_quota(quota)
        else:
            self.client.set_account_quota(quota)

    def main(self, quota, container=None):
        super(self.__class__, self)._run()
        quota = self._calculate_quota(quota)
        self.container = container
        self._run(quota)


@command(pithos_cmds)
class store_versioning(_store_account_command):
    """Get  versioning for account or container"""

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    def _run(self):
        if self.container:
            r = self.client.get_container_versioning(self.container)
        else:
            r = self.client.get_account_versioning()
        print_dict(r)

    def main(self, container=None):
        super(self.__class__, self)._run()
        self.container = container
        self._run()


@command(pithos_cmds)
class store_setversioning(_store_account_command):
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
        if self.container:
            self.client.container = self.container
            self.client.set_container_versioning(versioning)
        else:
            self.client.set_account_versioning(versioning)

    def main(self, versioning, container=None):
        super(self.__class__, self)._run()
        self._run(self._check_versioning(versioning))


@command(pithos_cmds)
class store_group(_store_account_command):
    """Get groups and group members"""

    @errors.generic.all
    @errors.pithos.connection
    def _run(self):
        r = self.client.get_account_group()
        print_dict(pretty_keys(r, '-'))

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(pithos_cmds)
class store_setgroup(_store_account_command):
    """Set a user group"""

    @errors.generic.all
    @errors.pithos.connection
    def _run(self, groupname, *users):
        self.client.set_account_group(groupname, users)

    def main(self, groupname, *users):
        super(self.__class__, self)._run()
        if users:
            self._run(groupname, *users)
        else:
            raiseCLIError('No users to add in group %s' % groupname)


@command(pithos_cmds)
class store_delgroup(_store_account_command):
    """Delete a user group"""

    @errors.generic.all
    @errors.pithos.connection
    def _run(self, groupname):
        self.client.del_account_group(groupname)

    def main(self, groupname):
        super(self.__class__, self)._run()
        self._run(groupname)


@command(pithos_cmds)
class store_sharers(_store_account_command):
    """List the accounts that share objects with current user"""

    arguments = dict(
        detail=FlagArgument('show detailed output', '-l'),
        marker=ValueArgument('show output greater then marker', '--marker')
    )

    @errors.generic.all
    @errors.pithos.connection
    def _run(self):
        accounts = self.client.get_sharing_accounts(marker=self['marker'])
        if self['detail']:
            print_items(accounts)
        else:
            print_items([acc['name'] for acc in accounts])

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(pithos_cmds)
class store_versions(_store_container_command):
    """Get the list of object versions
    Deleted objects may still have versions that can be used to restore it and
    get information about its previous state.
    The version number can be used in a number of other commands, like info,
    copy, move, meta. See these commands for more information, e.g.
    /store info -h
    """

    @errors.generic.all
    @errors.pithos.connection
    @errors.pithos.container
    @errors.pithos.object_path
    def _run(self):
        versions = self.client.get_object_versionlist(self.path)
        print_items([dict(id=vitem[0], created=strftime(
            '%d-%m-%Y %H:%M:%S',
            localtime(float(vitem[1])))) for vitem in versions])

    def main(self, container___path):
        super(store_versions, self)._run(
            container___path,
            path_is_optional=False)
        self._run()
