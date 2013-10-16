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

from kamaki.cli import command
from kamaki.clients.astakos import AstakosClient, SynnefoAstakosClient
from kamaki.cli.commands import (
    _command_init, errors, _optional_json, addLogSettings)
from kamaki.cli.command_tree import CommandTree
from kamaki.cli.errors import CLIBaseUrlError, CLIError
from kamaki.cli.argument import FlagArgument
from kamaki.cli.utils import format_size

user_commands = CommandTree('user', 'Astakos/Identity API commands')
admin_commands = CommandTree('admin', 'Astakos/Account API commands')
project_commands = CommandTree('project', 'Astakos project API commands')
_commands = [user_commands, admin_commands, project_commands]


class _init_synnefo_astakosclient(_command_init):
    @errors.generic.all
    @errors.user.load
    @errors.user.astakosclient
    @addLogSettings
    def _run(self):
        if getattr(self, 'cloud', None):
            base_url = self._custom_url('astakos')
            if base_url:
                token = self._custom_token(
                    'astakos') or self.config.get_cloud(self.cloud, 'token')
                token = token.split()[0] if ' ' in token else token
                self.client = SynnefoAstakosClient(
                    auth_url=base_url, token=token)
                return
        else:
            self.cloud = 'default'
        if getattr(self, 'auth_base', None):
            self.client = SynnefoAstakosClient(
                auth_url=self.auth_base.base_url, token=self.auth_base.token)
            return
        raise CLIBaseUrlError(service='astakos')

    def main(self):
        self._run()


@command(user_commands)
class user_info(_init_synnefo_astakosclient, _optional_json):
    """Authenticate a user and get info"""

    @errors.generic.all
    @errors.user.authenticate
    @errors.user.astakosclient
    def _run(self, custom_token=None):
        token_bu = self.client.token
        try:
            self.client.token = custom_token or token_bu
            self._print(
                self.client.get_user_info(), self.print_dict)
        finally:
            self.client.token = token_bu

    def main(self, token=None):
        super(self.__class__, self)._run()
        self._run(custom_token=token)


@command(user_commands)
class user_uuid2username(_init_synnefo_astakosclient, _optional_json):
    """Get username(s) from uuid(s)"""

    @errors.generic.all
    @errors.user.astakosclient
    def _run(self, uuids):
        r = self.client.get_usernames(uuids)
        self._print(r, self.print_dict)
        unresolved = set(uuids).difference(r)
        if unresolved:
            self.error('Unresolved uuids: %s' % ', '.join(unresolved))

    def main(self, uuid, *more_uuids):
        super(self.__class__, self)._run()
        self._run(uuids=((uuid, ) + more_uuids))


@command(user_commands)
class user_username2uuid(_init_synnefo_astakosclient, _optional_json):
    """Get uuid(s) from username(s)"""

    @errors.generic.all
    @errors.user.astakosclient
    def _run(self, usernames):
        r = self.client.get_uuids(usernames)
        self._print(r, self.print_dict)
        unresolved = set(usernames).difference(r)
        if unresolved:
            self.error('Unresolved usernames: %s' % ', '.join(unresolved))

    def main(self, username, *more_usernames):
        super(self.__class__, self)._run()
        self._run(usernames=((username, ) + more_usernames))


@command(user_commands)
class user_quotas(_init_synnefo_astakosclient, _optional_json):
    """Get user quotas"""

    _to_format = set(['cyclades.disk', 'pithos.diskspace', 'cyclades.ram'])

    arguments = dict(
        bytes=FlagArgument('Show data size in bytes', '--bytes')
    )

    def _print_quotas(self, quotas, *args, **kwargs):
        if not self['bytes']:
            for category in quotas.values():
                for service in self._to_format.intersection(category):
                    for attr, v in category[service].items():
                        category[service][attr] = format_size(v)
        self.print_dict(quotas, *args, **kwargs)

    @errors.generic.all
    @errors.user.astakosclient
    def _run(self):
        self._print(self.client.get_quotas(), self._print_quotas)

    def main(self):
        super(self.__class__, self)._run()
        self._run()
