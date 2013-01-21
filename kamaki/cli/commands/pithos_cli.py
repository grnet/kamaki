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

from kamaki.cli import command
from kamaki.cli.command_tree import CommandTree
from kamaki.cli.errors import raiseCLIError, CLISyntaxError
from kamaki.cli.utils import format_size, print_dict, pretty_keys, page_hold
from kamaki.cli.argument import FlagArgument, ValueArgument, IntArgument
from kamaki.cli.argument import KeyValueArgument, DateArgument
from kamaki.cli.argument import ProgressBarArgument
from kamaki.cli.commands import _command_init
from kamaki.clients.pithos import PithosClient, ClientError
from kamaki.cli.utils import bold
from sys import stdout
from time import localtime, strftime
from logging import getLogger
from os import path

kloger = getLogger('kamaki')

pithos_cmds = CommandTree('store', 'Pithos+ storage commands')
_commands = [pithos_cmds]


about_directories = [
    'Kamaki hanldes directories the same way as OOS Storage and Pithos+:',
    'A directory is an object with type "application/directory"',
    'An object with path dir/name can exist even if dir does not exist or',
    'even if dir is a non directory object. Users can modify dir without',
    'affecting the dir/name object in any way.']


# Argument functionality

def raise_connection_errors(e):
    if e.status in range(200) + [403, 401]:
        raiseCLIError(e, details=[
            'Please check the service url and the authentication information',
            ' ',
            '  to get the service url: /config get store.url',
            '  to set the service url: /config set store.url <url>',
            ' ',
            '  to get user the account: /config get store.account',
            '           or              /config get account',
            '  to set the user account: /config set store.account <account>',
            ' ',
            '  to get authentication token: /config get token',
            '  to set authentication token: /config set token <token>'
            ])
    elif e.status == 413:
        raiseCLIError(e, details=[
            'Get quotas:',
            '- total quota:      /store quota',
            '- container quota:  /store quota <container>',
            'Users shall set a higher container quota, if available:',
            '-                  /store setquota <limit in KB> <container>'
            ])


def check_range(start, end):
    """
    :param start: (int)

    :param end: (int)

    :returns: (int(start), int(end))

    :raises CLIError - Invalid start/end value in range
    :raises CLIError - Invalid range
    """
    try:
        start = int(start)
    except ValueError as e:
        raiseCLIError(e, 'Invalid start value %s in range' % start)
    try:
        end = int(end)
    except ValueError as e:
        raiseCLIError(e, 'Invalid end value %s in range' % end)
    if start > end:
        raiseCLIError('Invalid range %s-%s' % (start, end))
    return (start, end)


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
                raiseCLIError(err, 'Error in --sharing',
                    details='Incorrect format',
                    importance=1)
            if key.lower() not in ('read', 'write'):
                raiseCLIError(err, 'Error in --sharing',
                    details='Invalid permission key %s' % key,
                    importance=1)
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

    def main(self):
        self.token = self.config.get('store', 'token')\
            or self.config.get('global', 'token')
        self.base_url = self.config.get('store', 'url')\
            or self.config.get('global', 'url')
        self.account = self.config.get('store', 'account')\
            or self.config.get('global', 'account')
        self.container = self.config.get('store', 'container')\
            or self.config.get('global', 'container')
        self.client = PithosClient(base_url=self.base_url,
            token=self.token,
            account=self.account,
            container=self.container)


class _store_account_command(_pithos_init):
    """Base class for account level storage commands"""

    def __init__(self, arguments={}):
        super(_store_account_command, self).__init__(arguments)
        self['account'] = ValueArgument(
            'Set user account (not permanent)',
            '--account')

    def main(self):
        super(_store_account_command, self).main()
        if self['account']:
            self.client.account = self['account']


class _store_container_command(_store_account_command):
    """Base class for container level storage commands"""

    generic_err_details = ['To specify a container:',
    '  1. Set store.container variable (permanent)',
    '     /config set store.container <container>',
    '  2. --container=<container> (temporary, overrides 1)',
    '  3. Use the container:path format (temporary, overrides all)']

    container = None
    path = None

    def __init__(self, arguments={}):
        super(_store_container_command, self).__init__(arguments)
        self['container'] = ValueArgument(
            'Set container to work with (temporary)',
            '--container')

    def extract_container_and_path(self,
        container_with_path,
        path_is_optional=True):
        try:
            assert isinstance(container_with_path, str)
        except AssertionError as err:
            raiseCLIError(err)

        cont, sep, path = container_with_path.partition(':')

        if sep:
            if not cont:
                raiseCLIError(CLISyntaxError('Container is missing\n',
                    details=self.generic_err_details))
            alt_cont = self['container']
            if alt_cont and cont != alt_cont:
                raiseCLIError(CLISyntaxError(
                    'Conflict: 2 containers (%s, %s)' % (cont, alt_cont),
                    details=self.generic_err_details)
                )
            self.container = cont
            if not path:
                raiseCLIError(CLISyntaxError(
                    'Path is missing for object in container %s' % cont,
                    details=self.generic_err_details)
                )
            self.path = path
        else:
            alt_cont = self['container'] or self.client.container
            if alt_cont:
                self.container = alt_cont
                self.path = cont
            elif path_is_optional:
                self.container = cont
                self.path = None
            else:
                self.container = cont
                raiseCLIError(CLISyntaxError(
                    'Both container and path are required',
                    details=self.generic_err_details)
                )

    def main(self, container_with_path=None, path_is_optional=True):
        super(_store_container_command, self).main()
        if container_with_path is not None:
            self.extract_container_and_path(
                container_with_path,
                path_is_optional)
            self.client.container = self.container
        elif self['container']:
            self.client.container = self['container']
        self.container = self.client.container


@command(pithos_cmds)
class store_list(_store_container_command):
    """List containers, object trees or objects in a directory
    Use with:
    1 no parameters : containers in set account
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
            if (self['exact_match'] and self.path and\
                obj['name'] != self.path) or 'content_type' not in obj:
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
                    print('%s (%s, %s objects)'\
                    % (cname, size, container['count']))
                else:
                    print(cname)
            if self['more']:
                page_hold(index + 1, limit, len(container_list))

    def main(self, container____path__=None):
        super(self.__class__, self).main(container____path__)
        try:
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
                prefix = self.path if self.path else self['prefix']
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
        except ClientError as err:
            if err.status == 404:
                if 'container' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No container %s in account %s'\
                        % (self.container, self.account),
                        details=self.generic_err_details)
                elif 'object' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No object %s in %s\'s container %s'\
                        % (self.path, self.account, self.container),
                        details=self.generic_err_details)
            raise_connection_errors(err)
            raiseCLIError(err)
        except Exception as e:
            raiseCLIError(e)


@command(pithos_cmds)
class store_mkdir(_store_container_command):
    """Create a directory"""

    __doc__ += '\n. '.join(about_directories)

    def main(self, container___directory):
        super(self.__class__,
            self).main(container___directory, path_is_optional=False)
        try:
            self.client.create_directory(self.path)
        except ClientError as err:
            if err.status == 404:
                if 'container' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No container %s in account %s'\
                        % (self.container, self.account),
                        details=self.generic_err_details)
                elif 'object' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No object %s in container %s'\
                        % (self.path, self.container),
                        details=self.generic_err_details)
            raise_connection_errors(err)
            raiseCLIError(err)
        except Exception as err:
            raiseCLIError(err)


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

    def main(self, container___path):
        super(store_touch, self).main(container___path)
        try:
            self.client.create_object(self.path, self['content_type'])
        except ClientError as err:
            if err.status == 404:
                if 'container' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No container %s in account %s'\
                        % (self.container, self.account),
                        details=self.generic_err_details)
                elif 'object' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No object %s in container %s'\
                        % (self.path, self.container),
                        details=self.generic_err_details)
            raise_connection_errors(err)
            raiseCLIError(err)
        except Exception as err:
            raiseCLIError(err)


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

    def main(self, container):
        super(self.__class__, self).main(container)
        try:
            self.client.container_put(quota=self['quota'],
                versioning=self['versioning'],
                metadata=self['meta'])
        except ClientError as err:
            if err.status == 404:
                if 'container' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No container %s in account %s'\
                        % (self.container, self.account),
                        details=self.generic_err_details)
                elif 'object' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No object %s in container %s'\
                        % (self.path, self.container),
                        details=self.generic_err_details)
            raise_connection_errors(err)
            raiseCLIError(err)
        except Exception as e:
            raiseCLIError(e)


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
            return [(dst_path if dst_path else self.path, self.path)]
        r = self.client.container_get(prefix=self.path)
        if len(r.json) == 1:
            obj = r.json[0]
            return [(obj['name'], dst_path if dst_path else obj['name'])]
        return [(obj['name'], '%s%s' % (
                    dst_path,
                    obj['name'][len(self.path) if self['replace'] else 0:])
                ) for obj in r.json]

    def main(self, source_container___path, destination_container___path):
        super(self.__class__,
            self).main(source_container___path, path_is_optional=False)
        try:
            dst = destination_container___path.split(':')
            (dst_cont, dst_path) = (dst[0], dst[1])\
            if len(dst) > 1 else (None, dst[0])
            for src_object, dst_object in self._objlist(dst_path):
                self.client.copy_object(src_container=self.container,
                    src_object=src_object,
                    dst_container=dst_cont if dst_cont else self.container,
                    dst_object=dst_object,
                    source_version=self['source_version'],
                    public=self['public'],
                    content_type=self['content_type'])
        except ClientError as err:
            if err.status == 404:
                if 'object' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No object %s in container %s'\
                        % (self.path, self.container),
                        details=self.generic_err_details)
                elif 'container' in ('%s' % err).lower():
                    cont_msg = '(either %s or %s)' % (
                        self.container,
                        dst_cont
                    ) if dst_cont else self.container
                    raiseCLIError(
                        err,
                        'No container %s in account %s'\
                        % (cont_msg, self.account),
                        details=self.generic_err_details)
            raise_connection_errors(err)
            raiseCLIError(err)
        except Exception as e:
            raiseCLIError(e)


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
            return [(dst_path if dst_path else self.path, self.path)]
        r = self.client.container_get(prefix=self.path)
        if len(r.json) == 1:
            obj = r.json[0]
            return [(obj['name'], dst_path if dst_path else obj['name'])]
        return [(obj['name'], '%s%s' % (
                    dst_path,
                    obj['name'][len(self.path) if self['replace'] else 0:])
                ) for obj in r.json]

    def main(self, source_container___path, destination_container____path__):
        super(self.__class__,
            self).main(source_container___path, path_is_optional=False)
        try:
            dst = destination_container____path__.split(':')
            (dst_cont, dst_path) = (dst[0], dst[1])\
            if len(dst) > 1 else (None, dst[0])
            for src_object, dst_object in self._objlist(dst_path):
                self.client.move_object(
                    src_container=self.container,
                    src_object=src_object,
                    dst_container=dst_cont if dst_cont else self.container,
                    dst_object=dst_object,
                    source_version=self['source_version'],
                    public=self['public'],
                    content_type=self['content_type'])
        except ClientError as err:
            if err.status == 404:
                if 'object' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No object %s in container %s'\
                        % (self.path, self.container),
                        details=self.generic_err_details)
                elif 'container' in ('%s' % err).lower():
                    cont_msg = '(either %s or %s)' % (
                        self.container,
                        dst_cont
                    ) if dst_cont else self.container
                    raiseCLIError(
                        err,
                        'No container %s in account %s'\
                        % (cont_msg, self.account),
                        details=self.generic_err_details)
            raise_connection_errors(err)
            raiseCLIError(err)
        except Exception as e:
            raiseCLIError(e)


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

    def main(self, local_path, container___path):
        super(self.__class__, self).main(
            container___path,
            path_is_optional=False)
        progress_bar = self.arguments['progress_bar']
        try:
            upload_cb = progress_bar.get_generator('Appending blocks')
        except Exception:
            upload_cb = None
        try:
            f = open(local_path, 'rb')
            self.client.append_object(self.path, f, upload_cb)
        except ClientError as err:
            progress_bar.finish()
            if err.status == 404:
                if 'container' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No container %s in account %s'\
                        % (self.container, self.account),
                        details=self.generic_err_details)
                elif 'object' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No object %s in container %s'\
                        % (self.path, self.container),
                        details=self.generic_err_details)
            raise_connection_errors(err)
            raiseCLIError(err)
        except Exception as e:
            progress_bar.finish()
            raiseCLIError(e)
        finally:
            progress_bar.finish()


@command(pithos_cmds)
class store_truncate(_store_container_command):
    """Truncate remote file up to a size (default is 0)"""

    def main(self, container___path, size=0):
        super(self.__class__, self).main(container___path)
        try:
            self.client.truncate_object(self.path, size)
        except ClientError as err:
            if err.status == 404:
                if 'container' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No container %s in account %s'\
                        % (self.container, self.account),
                        details=self.generic_err_details)
                elif 'object' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No object %s in container %s'\
                        % (self.path, self.container),
                        details=self.generic_err_details)
            if err.status == 400 and\
                'object length is smaller than range length'\
                in ('%s' % err).lower():
                raiseCLIError(err, 'Object %s:%s <= %sb' % (
                    self.container,
                    self.path,
                    size))
            raise_connection_errors(err)
            raiseCLIError(err)
        except Exception as e:
            raiseCLIError(e)


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

    def main(self, local_path, container____path__, start, end):
        (start, end) = check_range(start, end)
        super(self.__class__, self).main(container____path__)
        try:
            f = open(local_path, 'rb')
            f.seek(0, 2)
            f_size = f.tell()
            f.seek(start, 0)
        except Exception as e:
            raiseCLIError(e)
        progress_bar = self.arguments['progress_bar']
        try:
            upload_cb = progress_bar.get_generator(
                'Overwriting %s blocks' % end - start)
        except Exception:
            upload_cb = None
        try:
            self.path = self.path if self.path else path.basename(local_path)
            self.client.overwrite_object(
                obj=self.path,
                start=start,
                end=end,
                source_file=f,
                upload_cb=upload_cb)
        except ClientError as err:
            progress_bar.finish()
            if (err.status == 400 and\
            'content length does not match range' in ('%s' % err).lower()) or\
            err.status == 416:
                raiseCLIError(err, details=[
                    'Content size: %s' % f_size,
                    'Range: %s-%s (size: %s)' % (start, end, end - start)])
            elif err.status == 404:
                if 'container' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No container %s in account %s'\
                        % (self.container, self.account),
                        details=self.generic_err_details)
                elif 'object' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No object %s in container %s'\
                        % (self.path, self.container),
                        details=self.generic_err_details)
            raise_connection_errors(err)
            raiseCLIError(err)
        except Exception as e:
            progress_bar.finish()
            raiseCLIError(e)
        finally:
            progress_bar.finish()


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
            'define object sharing policy \n' +\
            '    ( "read=user1,grp1,user2,... write=user1,grp2,..." )',
            '--sharing'),
        public=FlagArgument('make object publicly accessible', '--public')
    )

    def main(self, container___path):
        super(self.__class__,
            self).main(container___path, path_is_optional=False)
        try:
            self.client.create_object_by_manifestation(
                self.path,
                content_encoding=self['content_encoding'],
                content_disposition=self['content_disposition'],
                content_type=self['content_type'],
                sharing=self['sharing'],
                public=self['public'])
        except ClientError as err:
            if err.status == 404:
                if 'container' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No container %s in account %s'\
                        % (self.container, self.account),
                        details=self.generic_err_details)
                elif 'object' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No object %s in container %s'\
                        % (self.path, self.container),
                        details=self.generic_err_details)
            raise_connection_errors(err)
            raiseCLIError(err)
        except Exception as e:
            raiseCLIError(e)


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
            help='define sharing object policy \n' +\
            '( "read=user1,grp1,user2,... write=user1,grp2,... )',
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

    def main(self, local_path, container____path__=None):
        super(self.__class__, self).main(container____path__)
        remote_path = self.path if self.path else path.basename(local_path)
        poolsize = self['poolsize']
        if poolsize > 0:
            self.client.POOL_SIZE = int(poolsize)
        params = dict(
            content_encoding=self['content_encoding'],
            content_type=self['content_type'],
            content_disposition=self['content_disposition'],
            sharing=self['sharing'],
            public=self['public'])
        try:
            progress_bar = self.arguments['progress_bar']
            hash_bar = progress_bar.clone()
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
                    hash_cb = hash_bar.get_generator(
                        'Calculating block hashes')
                    upload_cb = progress_bar.get_generator('Uploading')
                    self.client.upload_object(
                        remote_path,
                        f,
                        hash_cb=hash_cb,
                        upload_cb=upload_cb,
                        **params)
                    progress_bar.finish()
                    hash_bar.finish()
        except ClientError as err:
            try:
                progress_bar.finish()
                hash_bar.finish()
            except Exception:
                pass
            if err.status == 404:
                if 'container' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No container %s in account %s'\
                        % (self.container, self.account),
                        details=[self.generic_err_details])
            elif err.status == 800:
                raiseCLIError(err, details=[
                    'Possible cause: temporary server failure',
                    'Try to re-upload the file',
                    'For more error details, try kamaki store upload -d'])
            raise_connection_errors(err)
            raiseCLIError(err, 'Failed to upload to %s' % container____path__)
        except IOError as err:
            try:
                progress_bar.finish()
                hash_bar.finish()
            except Exception:
                pass
            raiseCLIError(err, 'Failed to read form file %s' % local_path, 2)
        except Exception as e:
            try:
                progress_bar.finish()
                hash_bar.finish()
            except Exception:
                pass
            raiseCLIError(e)
        print 'Upload completed'


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

    def main(self, container___path):
        super(self.__class__, self).main(
            container___path,
            path_is_optional=False)
        try:
            self.client.download_object(self.path, stdout,
            range=self['range'],
            version=self['object_version'],
            if_match=self['if_match'],
            if_none_match=self['if_none_match'],
            if_modified_since=self['if_modified_since'],
            if_unmodified_since=self['if_unmodified_since'])
        except ClientError as err:
            if err.status == 404:
                if 'container' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No container %s in account %s'\
                        % (self.container, self.account),
                        details=self.generic_err_details)
                elif 'object' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No object %s in container %s'\
                        % (self.path, self.container),
                        details=self.generic_err_details)
            raise_connection_errors(err)
            raiseCLIError(err)
        except Exception as e:
            raiseCLIError(e)


@command(pithos_cmds)
class store_download(_store_container_command):
    """Download remote object as local file"""

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
            default=False)
    )

    def _output_stream(self, local_path):
        if local_path is None:
            return stdout
        try:
            return open(
                path.abspath(local_path),
                'rwb+' if self['resume'] else 'wb+')
        except IOError as err:
            raiseCLIError(err, 'Cannot write to file %s' % local_path, 1)

    def main(self, container___path, local_path=None):
        super(self.__class__, self).main(
            container___path,
            path_is_optional=False)

        out = self._output_stream(local_path)
        poolsize = self['poolsize']
        if poolsize is not None:
            self.client.POOL_SIZE = int(poolsize)

        try:
            progress_bar = self.arguments['progress_bar']
            download_cb = progress_bar.get_generator('Downloading')
            self.client.download_object(
                self.path,
                out,
                download_cb=download_cb,
                range=self['range'],
                version=self['object_version'],
                if_match=self['if_match'],
                resume=self['resume'],
                if_none_match=self['if_none_match'],
                if_modified_since=self['if_modified_since'],
                if_unmodified_since=self['if_unmodified_since'])
            progress_bar.finish()
        except ClientError as err:
            progress_bar.finish()
            if err.status == 404:
                if 'container' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No container %s in account %s'\
                        % (self.container, self.account),
                        details=self.generic_err_details)
                elif 'object' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No object %s in container %s'\
                        % (self.path, self.container),
                        details=self.generic_err_details)
            raise_connection_errors(err)
            raiseCLIError(err, '"%s" not accessible' % container___path)
        except IOError as err:
            try:
                progress_bar.finish()
            except Exception:
                pass
            raiseCLIError(err, 'Failed to write on file %s' % local_path, 2)
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
            try:
                progress_bar.finish()
            except Exception:
                pass
            print('\ndownload canceled by user')
            if local_path is not None:
                print('to resume, re-run with --resume')
        except Exception as e:
            try:
                progress_bar.finish()
            except Exception:
                pass
            raiseCLIError(e)
        print


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

    def main(self, container___path):
        super(self.__class__, self).main(
            container___path,
            path_is_optional=False)
        try:
            data = self.client.get_object_hashmap(
                self.path,
                version=self['object_version'],
                if_match=self['if_match'],
                if_none_match=self['if_none_match'],
                if_modified_since=self['if_modified_since'],
                if_unmodified_since=self['if_unmodified_since'])
        except ClientError as err:
            if err.status == 404:
                if 'container' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No container %s in account %s'\
                        % (self.container, self.account),
                        details=self.generic_err_details)
                elif 'object' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No object %s in container %s'\
                        % (self.path, self.container),
                        details=self.generic_err_details)
            raise_connection_errors(err)
            raiseCLIError(err)
        except Exception as e:
            raiseCLIError(e)
        print_dict(data)


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

    def main(self, container____path__):
        super(self.__class__, self).main(container____path__)
        try:
            if self.path is None:
                self.client.del_container(
                    until=self['until'],
                    delimiter=self['delimiter'])
            else:
                # self.client.delete_object(self.path)
                self.client.del_object(
                    self.path,
                    until=self['until'],
                    delimiter=self['delimiter'])
        except ClientError as err:
            if err.status == 404:
                if 'container' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No container %s in account %s'\
                        % (self.container, self.account),
                        details=self.generic_err_details)
                elif 'object' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No object %s in container %s'\
                        % (self.path, self.container),
                        details=self.generic_err_details)
            raise_connection_errors(err)
            raiseCLIError(err)
        except Exception as e:
            raiseCLIError(e)


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

    def main(self, container):
        super(self.__class__, self).main(container)
        try:
            self.client.purge_container()
        except ClientError as err:
            if err.status == 404:
                if 'container' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No container %s in account %s'\
                        % (self.container, self.account),
                        details=self.generic_err_details)
            raise_connection_errors(err)
            raiseCLIError(err)
        except Exception as e:
            raiseCLIError(e)


@command(pithos_cmds)
class store_publish(_store_container_command):
    """Publish the object and print the public url"""

    def main(self, container___path):
        super(self.__class__, self).main(
            container___path,
            path_is_optional=False)
        try:
            url = self.client.publish_object(self.path)
        except ClientError as err:
            if err.status == 404:
                if 'container' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No container %s in account %s'\
                        % (self.container, self.account),
                        details=self.generic_err_details)
                elif 'object' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No object %s in container %s'\
                        % (self.path, self.container),
                        details=self.generic_err_details)
            raise_connection_errors(err)
            raiseCLIError(err)
        except Exception as e:
            raiseCLIError(e)
        print(url)


@command(pithos_cmds)
class store_unpublish(_store_container_command):
    """Unpublish an object"""

    def main(self, container___path):
        super(self.__class__, self).main(
            container___path,
            path_is_optional=False)
        try:
            self.client.unpublish_object(self.path)
        except ClientError as err:
            if err.status == 404:
                if 'container' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No container %s in account %s'\
                        % (self.container, self.account),
                        details=self.generic_err_details)
                elif 'object' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No object %s in container %s'\
                        % (self.path, self.container),
                        details=self.generic_err_details)
            raise_connection_errors(err)
            raiseCLIError(err)
        except Exception as e:
            raiseCLIError(e)


@command(pithos_cmds)
class store_permissions(_store_container_command):
    """Get read and write permissions of an object
    Permissions are lists of users and user groups. There is read and write
    permissions. Users and groups with write permission have also read
    permission.
    """

    def main(self, container___path):
        super(self.__class__, self).main(
            container___path,
            path_is_optional=False)
        try:
            reply = self.client.get_object_sharing(self.path)
        except ClientError as err:
            if err.status == 404:
                if 'container' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No container %s in account %s'\
                        % (self.container, self.account),
                        details=self.generic_err_details)
                elif 'object' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No object %s in container %s'\
                        % (self.path, self.container),
                        details=self.generic_err_details)
            raise_connection_errors(err)
            raiseCLIError(err)
        except Exception as e:
            raiseCLIError(e)
        print_dict(reply)


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

    def format_permition_dict(self, permissions):
        read = False
        write = False
        for perms in permissions:
            splstr = perms.split('=')
            if 'read' == splstr[0]:
                read = [user_or_group.strip() \
                for user_or_group in splstr[1].split(',')]
            elif 'write' == splstr[0]:
                write = [user_or_group.strip() \
                for user_or_group in splstr[1].split(',')]
            else:
                read = False
                write = False
        if not read and not write:
            raiseCLIError(None,
            'Usage:\tread=<groups,users> write=<groups,users>')
        return (read, write)

    def main(self, container___path, *permissions):
        super(self.__class__,
            self).main(container___path, path_is_optional=False)
        (read, write) = self.format_permition_dict(permissions)
        try:
            self.client.set_object_sharing(self.path,
                read_permition=read, write_permition=write)
        except ClientError as err:
            if err.status == 404:
                if 'container' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No container %s in account %s'\
                        % (self.container, self.account),
                        details=self.generic_err_details)
                elif 'object' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No object %s in container %s'\
                        % (self.path, self.container),
                        details=self.generic_err_details)
            raise_connection_errors(err)
            raiseCLIError(err)
        except Exception as e:
            raiseCLIError(e)


@command(pithos_cmds)
class store_delpermissions(_store_container_command):
    """Delete all permissions set on object
    To modify permissions, use /store setpermssions
    """

    def main(self, container___path):
        super(self.__class__,
            self).main(container___path, path_is_optional=False)
        try:
            self.client.del_object_sharing(self.path)
        except ClientError as err:
            if err.status == 404:
                if 'container' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No container %s in account %s'\
                        % (self.container, self.account),
                        details=self.generic_err_details)
                elif 'object' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No object %s in container %s'\
                        % (self.path, self.container),
                        details=self.generic_err_details)
            raise_connection_errors(err)
            raiseCLIError(err)
        except Exception as e:
            raiseCLIError(e)


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

    def main(self, container____path__=None):
        super(self.__class__, self).main(container____path__)
        try:
            if self.container is None:
                reply = self.client.get_account_info()
            elif self.path is None:
                reply = self.client.get_container_info(self.container)
            else:
                reply = self.client.get_object_info(
                    self.path,
                    version=self['object_version'])
        except ClientError as err:
            if err.status == 404:
                if 'container' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No container %s in account %s'\
                        % (self.container, self.account),
                        details=self.generic_err_details)
                elif 'object' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No object %s in container %s'\
                        % (self.path, self.container),
                        details=self.generic_err_details)
            raise_connection_errors(err)
            raiseCLIError(err)
        except Exception as e:
            raiseCLIError(e)
        print_dict(reply)


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

    def main(self, container____path__=None):
        super(self.__class__, self).main(container____path__)

        detail = self['detail']
        try:
            until = self['until']
            if self.container is None:
                if detail:
                    reply = self.client.get_account_info(until=until)
                else:
                    reply = self.client.get_account_meta(until=until)
                    reply = pretty_keys(reply, '-')
                if reply:
                    print(bold(self.client.account))
            elif self.path is None:
                if detail:
                    reply = self.client.get_container_info(until=until)
                else:
                    cmeta = self.client.get_container_meta(until=until)
                    ometa = self.client.get_container_object_meta(until=until)
                    reply = {}
                    if cmeta:
                        reply['container-meta'] = pretty_keys(cmeta, '-')
                    if ometa:
                        reply['object-meta'] = pretty_keys(ometa, '-')
            else:
                if detail:
                    reply = self.client.get_object_info(self.path,
                        version=self['object_version'])
                else:
                    reply = self.client.get_object_meta(self.path,
                        version=self['object_version'])
                if reply:
                    reply = pretty_keys(pretty_keys(reply, '-'))
        except ClientError as err:
            if err.status == 404:
                if 'container' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No container %s in account %s'\
                        % (self.container, self.account),
                        details=self.generic_err_details)
                elif 'object' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No object %s in container %s'\
                        % (self.path, self.container),
                        details=self.generic_err_details)
                else:
                    raiseCLIError(err, details=self.generic_err_details)
            raise_connection_errors(err)
            raiseCLIError(err)
        except Exception as e:
            raiseCLIError(e)
        if reply:
            print_dict(reply)


@command(pithos_cmds)
class store_setmeta(_store_container_command):
    """Set a piece of metadata for account, container or object
    Metadata are formed as key:value pairs
    """

    def main(self, metakey___metaval, container____path__=None):
        super(self.__class__, self).main(container____path__)
        try:
            metakey, metavalue = metakey___metaval.split(':')
        except ValueError as err:
            raiseCLIError(err,
                'Cannot parse %s as a key:value pair' % metakey___metaval,
                details=['Syntax:',
                    '   store setmeta metakey:metavalue [cont[:path]]'
                ],
                importance=1,
                )
        try:
            if self.container is None:
                self.client.set_account_meta({metakey: metavalue})
            elif self.path is None:
                self.client.set_container_meta({metakey: metavalue})
            else:
                self.client.set_object_meta(self.path, {metakey: metavalue})
        except ClientError as err:
            if err.status == 404:
                if 'container' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No container %s in account %s'\
                        % (self.container, self.account),
                        details=self.generic_err_details)
                elif 'object' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No object %s in container %s'\
                        % (self.path, self.container),
                        details=self.generic_err_details)
                else:
                    raiseCLIError(err, details=self.generic_err_details)
            raise_connection_errors(err)
            raiseCLIError(err)
        except Exception as err:
            raiseCLIError(err)


@command(pithos_cmds)
class store_delmeta(_store_container_command):
    """Delete metadata with given key from account, container or object
    Metadata are formed as key:value objects
    - to get metadata of current account:     /store meta
    - to get metadata of a container:         /store meta <container>
    - to get metadata of an object:           /store meta <container>:<path>
    """

    def main(self, metakey, container____path__=None):
        super(self.__class__, self).main(container____path__)
        try:
            if self.container is None:
                self.client.del_account_meta(metakey)
            elif self.path is None:
                self.client.del_container_meta(metakey)
            else:
                self.client.del_object_meta(self.path, metakey)
        except ClientError as err:
            if err.status == 404:
                if 'container' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No container %s in account %s'\
                        % (self.container, self.account),
                        details=self.generic_err_details)
                elif 'object' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No object %s in container %s'\
                        % (self.path, self.container),
                        details=self.generic_err_details)
                else:
                    raiseCLIError(err, details=self.generic_err_details)
            raise_connection_errors(err)
            raiseCLIError(err)
        except Exception as err:
            raiseCLIError(err)


@command(pithos_cmds)
class store_quota(_store_account_command):
    """Get quota (in KB) for account or container"""

    def main(self, container=None):
        super(self.__class__, self).main()
        try:
            if container is None:
                reply = self.client.get_account_quota()
            else:
                reply = self.client.get_container_quota(container)
        except ClientError as err:
            if err.status == 404:
                if 'container' in ('%s' % err).lower():
                    raiseCLIError(err,
                        'No container %s in account %s'\
                        % (container, self.account))
            raise_connection_errors(err)
            raiseCLIError(err)
        except Exception as err:
            raiseCLIError(err)
        print_dict(pretty_keys(reply, '-'))


@command(pithos_cmds)
class store_setquota(_store_account_command):
    """Set new quota (in KB) for account or container"""

    def main(self, quota, container=None):
        super(self.__class__, self).main()
        try:
            if container is None:
                self.client.set_account_quota(quota)
            else:
                self.client.container = container
                self.client.set_container_quota(quota)
        except ClientError as err:
            if err.status == 404:
                if 'container' in ('%s' % err).lower():
                    raiseCLIError(err,
                        'No container %s in account %s'\
                        % (container, self.account))
            raise_connection_errors(err)
            raiseCLIError(err)
        except Exception as err:
            raiseCLIError(err)


@command(pithos_cmds)
class store_versioning(_store_account_command):
    """Get  versioning for account or container"""

    def main(self, container=None):
        super(self.__class__, self).main()
        try:
            if container is None:
                reply = self.client.get_account_versioning()
            else:
                reply = self.client.get_container_versioning(container)
        except ClientError as err:
            if err.status == 404:
                if 'container' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No container %s in account %s'\
                        % (self.container, self.account),
                        details=self.generic_err_details)
                else:
                    raiseCLIError(err, details=self.generic_err_details)
            raise_connection_errors(err)
            raiseCLIError(err)
        except Exception as err:
            raiseCLIError(err)
        print_dict(reply)


@command(pithos_cmds)
class store_setversioning(_store_account_command):
    """Set versioning mode (auto, none) for account or container"""

    def main(self, versioning, container=None):
        super(self.__class__, self).main()
        try:
            if container is None:
                self.client.set_account_versioning(versioning)
            else:
                self.client.container = container
                self.client.set_container_versioning(versioning)
        except ClientError as err:
            if err.status == 404:
                if 'container' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No container %s in account %s'\
                        % (self.container, self.account),
                        details=self.generic_err_details)
                else:
                    raiseCLIError(err, details=self.generic_err_details)
            raise_connection_errors(err)
            raiseCLIError(err)
        except Exception as err:
            raiseCLIError(err)


@command(pithos_cmds)
class store_group(_store_account_command):
    """Get groups and group members"""

    def main(self):
        super(self.__class__, self).main()
        try:
            reply = self.client.get_account_group()
        except ClientError as err:
            raise_connection_errors(err)
            raiseCLIError(err)
        except Exception as err:
            raiseCLIError(err)
        print_dict(pretty_keys(reply, '-'))


@command(pithos_cmds)
class store_setgroup(_store_account_command):
    """Set a user group"""

    def main(self, groupname, *users):
        super(self.__class__, self).main()
        try:
            self.client.set_account_group(groupname, users)
        except ClientError as err:
            raise_connection_errors(err)
            raiseCLIError(err)
        except Exception as err:
            raiseCLIError(err)


@command(pithos_cmds)
class store_delgroup(_store_account_command):
    """Delete a user group"""

    def main(self, groupname):
        super(self.__class__, self).main()
        try:
            self.client.del_account_group(groupname)
        except ClientError as err:
            raise_connection_errors(err)
            raiseCLIError(err)
        except Exception as err:
            raiseCLIError(err)


@command(pithos_cmds)
class store_sharers(_store_account_command):
    """List the accounts that share objects with current user"""

    arguments = dict(
        detail=FlagArgument('show detailed output', '-l'),
        marker=ValueArgument('show output greater then marker', '--marker')
    )

    def main(self):
        super(self.__class__, self).main()
        try:
            marker = self['marker']
            accounts = self.client.get_sharing_accounts(marker=marker)
        except ClientError as err:
            raise_connection_errors(err)
            raiseCLIError(err)
        except Exception as err:
            raiseCLIError(err)

        for acc in accounts:
            stdout.write(bold(acc['name']) + ' ')
            if self['detail']:
                print_dict(acc, exclude='name')
        if not self['detail']:
            print


@command(pithos_cmds)
class store_versions(_store_container_command):
    """Get the list of object versions
    Deleted objects may still have versions that can be used to restore it and
    get information about its previous state.
    The version number can be used in a number of other commands, like info,
    copy, move, meta. See these commands for more information, e.g.
    /store info -h
    """

    def main(self, container___path):
        super(store_versions, self).main(container___path)
        try:
            versions = self.client.get_object_versionlist(self.path)

            for vitem in versions:
                t = localtime(float(vitem[1]))
                vid = bold(unicode(vitem[0]))
                print('\t%s \t(%s)' % (vid, strftime('%d-%m-%Y %H:%M:%S', t)))
        except ClientError as err:
            if err.status == 404:
                if 'container' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No container %s in account %s'\
                        % (self.container, self.account),
                        details=self.generic_err_details)
                elif 'object' in ('%s' % err).lower():
                    raiseCLIError(
                        err,
                        'No object %s in container %s'\
                        % (self.path, self.container),
                        details=self.generic_err_details)
                else:
                    raiseCLIError(err, details=self.generic_err_details)
            raise_connection_errors(err)
            raiseCLIError(err)
        except Exception as err:
            raiseCLIError(err)
