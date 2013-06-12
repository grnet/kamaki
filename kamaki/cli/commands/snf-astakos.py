# Copyright 2013 GRNET S.A. All rights reserved.
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

from astakosclient import AstakosClient

from kamaki.cli import command
from kamaki.cli.errors import CLIBaseUrlError
from kamaki.cli.commands import (
    _command_init, errors, _optional_json, addLogSettings)
from kamaki.cli.command_tree import CommandTree
from kamaki.cli.utils import print_dict
from kamaki.cli.argument import FlagArgument, ValueArgument
from kamaki.cli.logger import add_stream_logger

snfastakos_cmds = CommandTree('astakos', 'astakosclient CLI')
_commands = [snfastakos_cmds]


log = add_stream_logger(__name__)


class _astakos_init(_command_init):

    def __init__(self, arguments=dict(), auth_base=None, cloud=None):
        super(_astakos_init, self).__init__(arguments, auth_base, cloud)
        self['token'] = ValueArgument('Custom token', '--token')

    @errors.generic.all
    #@errors.user.load
    @addLogSettings
    def _run(self):
        self.cloud = self.cloud if self.cloud else 'default'
        self.token = self['token'] or self._custom_token('astakos')\
            or self.config.get_cloud(self.cloud, 'token')
        if getattr(self, 'auth_base', False):
            astakos_endpoints = self.auth_base.get_service_endpoints(
                self._custom_type('astakos') or 'identity',
                self._custom_version('astakos') or '')
            base_url = astakos_endpoints['publicURL']
        else:
            base_url = self._custom_url('astakos')
        if not base_url:
            raise CLIBaseUrlError(service='astakos')
        self.client = AstakosClient(base_url, logger=log)

    def main(self):
        self._run()


@command(snfastakos_cmds)
class astakos_authenticate(_astakos_init, _optional_json):
    """Authenticate a user
    Get user information (e.g. unique account name) from token
    Token should be set in settings:
    *  check if a token is set    /config get cloud.default.token
    *  permanently set a token    /config set cloud.default.token <token>
    Token can also be provided as a parameter
    (To use a named cloud, use its name instead of "default")
    """

    arguments = dict(
        usage=FlagArgument('also return usage information', ('--with-usage'))
    )

    @errors.generic.all
    #@errors.user.authenticate
    def _run(self):
        print('KAMAKI LOG: call get_user_info(%s, %s)' % (
            self.token, self['usage']))
        self._print(
            self.client.get_user_info(self.token, self['usage']),
            print_dict)

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(snfastakos_cmds)
class astakos_username(_astakos_init, _optional_json):
    """Get username(s) from uuid(s)"""

    arguments = dict(
        service_token=ValueArgument(
            'Use service token instead', '--service-token')
    )

    def _run(self, uuids):
        assert uuids and isinstance(uuids, list), 'No valid uuids'
        if 1 == len(uuids):
            self._print(self.client.get_username(self.token, uuids[0]))
        else:
            self._print(
                self.client.get_username(self.token, uuids), print_dict)

    def main(self, uuid, *more_uuids):
        super(self.__class__, self)._run()
        self._run([uuid] + list(more_uuids))


@command(snfastakos_cmds)
class astakos_uuid(_astakos_init, _optional_json):
    """Get uuid(s) from username(s)"""

    def _run(self, usernames):
        assert usernames and isinstance(usernames, list), 'No valid usernames'
        if 1 == len(usernames):
            self._print(self.client.get_uuid(self.token, usernames[0]))
        else:
            self._print(
                self.client.get_uuids(self.token, usernames), print_dict)

    def main(self, usernames, *more_usernames):
        super(self.__class__, self)._run()
        self._run([usernames] + list(more_usernames))


@command(snfastakos_cmds)
class astakos_quotas(_astakos_init, _optional_json):
    """Get user (or service) quotas"""

    def _run(self):
            self._print(self.client.get_quotas(self.token), print_dict)

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(snfastakos_cmds)
class astakos_services(_astakos_init):
    """Astakos operations filtered by services"""


@command(snfastakos_cmds)
class astakos_services_list(_astakos_init):
    """List available services"""

    def _run(self):
        self._print(self.client.get_services())

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(snfastakos_cmds)
class astakos_services_username(_astakos_init, _optional_json):
    """Get service username(s) from uuid(s)"""

    def _run(self, stoken, uuids):
        assert uuids and isinstance(uuids, list), 'No valid uuids'
        if 1 == len(uuids):
            self._print(self.client.service_get_username(stoken, uuids[0]))
        else:
            self._print(
                self.client.service_get_usernames(stoken, uuids), print_dict)

    def main(self, service_token, uuid, *more_uuids):
        super(self.__class__, self)._run()
        self._run(service_token, [uuid] + list(more_uuids))


@command(snfastakos_cmds)
class astakos_services_uuid(_astakos_init, _optional_json):
    """Get service uuid(s) from username(s)"""

    def _run(self, stoken, usernames):
        assert usernames and isinstance(usernames, list), 'No valid usernames'
        if 1 == len(usernames):
            self._print(self.client.service_get_uuid(self.token, usernames[0]))
        else:
            self._print(
                self.client.service_get_uuids(self.token, usernames),
                print_dict)

    def main(self, service_token, usernames, *more_usernames):
        super(self.__class__, self)._run()
        self._run(service_token, [usernames] + list(more_usernames))


@command(snfastakos_cmds)
class astakos_services_quotas(_astakos_init, _optional_json):
    """Get user (or service) quotas"""

    arguments = dict(
        uuid=ValueArgument('A user unique id to get quotas for', '--uuid')
    )

    def _run(self, stoken):
        self._print(self.client.service_get_quotas(stoken, self['uuid']))

    def main(self, service_token):
        super(self.__class__, self)._run()
        self._run(service_token)
