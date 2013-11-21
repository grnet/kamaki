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

from kamaki.cli import command
from kamaki.cli.command_tree import CommandTree
from kamaki.cli.commands import (
    _command_init, errors, addLogSettings, DontRaiseKeyError, _optional_json,
    _name_filter, _optional_output_cmd)
from kamaki.clients.pithos import PithosClient
from kamaki.cli.errors import (
    CLIBaseUrlError)
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

    def __init__(self, *args, **kwargs):
        super(_pithos_account, self).__init__(*args, **kwargs)
        self['account'] = ValueArgument(
            'Use (a different) user uuid', ('-A', '--account'))

    def _run(self):
        super(_pithos_account, self)._run()
        self.client.account = self['account'] or getattr(
            self, 'account', getattr(self.client, 'account', None))


class _pithos_container(_pithos_account):
    """Setup container"""

    def __init__(self, *args, **kwargs):
        super(_pithos_container, self).__init__(*args, **kwargs)
        self['container'] = ValueArgument(
            'Use this container (default: pithos)', ('-C', '--container'))

    def _resolve_pithos_url(self, url):
        """Match urls of one of the following formats:
        pithos://ACCOUNT/CONTAINER/OBJECT_PATH
        /CONTAINER/OBJECT_PATH
        Anything resolved, is set as self.<account|container|path>
        """
        account, container, path, prefix = '', '', url, 'pithos://'
        if url.startswith(prefix):
            self.account, sep, url = url[len(prefix):].partition('/')
            url = '/%s' % url
        if url.startswith('/'):
            self.container, sep, path = url[1:].partition('/')
        self.path = path

    def _run(self, url=None):
        super(_pithos_container, self)._run()
        self._resolve_pithos_url(url or '')
        self.client.container = self['container'] or getattr(
            self, 'container', None) or getattr(self.client, 'container', '')


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
    """Create an empty remove file"""

    arguments = dict(
        content_type=ValueArgument(
            'Set content type (default: application/octet-stream)',
            '--content-type',
            default='application/octet-stream')
    )

    def _run(self):
        self._optional_output(
            self.client.create_object(self.path, self['content_type']))

    def main(self, path_or_url):
        super(self.__class__, self)._run(path_or_url)
        self._run()
