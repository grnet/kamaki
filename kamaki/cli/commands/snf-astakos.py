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

from astakosclient import AstakosClient, AstakosClientException

from kamaki.cli import command
from kamaki.cli.errors import CLIBaseUrlError
from kamaki.cli.commands import (
    _command_init, errors, _optional_json, addLogSettings)
from kamaki.cli.command_tree import CommandTree
from kamaki.cli.utils import print_dict, format_size
from kamaki.cli.argument import FlagArgument, ValueArgument
from kamaki.cli.argument import CommaSeparatedListArgument
from kamaki.cli.logger import get_logger

snfastakos_cmds = CommandTree('astakos', 'astakosclient CLI')
_commands = [snfastakos_cmds]


def astakoserror(foo):
    def _raise(self, *args, **kwargs):
        try:
            return foo(self, *args, **kwargs)
        except AstakosClientException as ace:
            try:
                ace.details = ['%s' % ace.details]
            except Exception:
                pass
            finally:
                raise ace
    return _raise


class _astakos_init(_command_init):

    def __init__(self, arguments=dict(), auth_base=None, cloud=None):
        super(_astakos_init, self).__init__(arguments, auth_base, cloud)
        self['token'] = ValueArgument('Custom token', '--token')

    @errors.generic.all
    @astakoserror
    @addLogSettings
    def _run(self):
        self.cloud = self.cloud if self.cloud else 'default'
        self.token = self['token'] or self._custom_token('astakos')\
            or self.config.get_cloud(self.cloud, 'token')
        if getattr(self, 'auth_base', False):
            astakos_endpoints = self.auth_base.get_service_endpoints(
                self._custom_type('astakos') or 'identity',
                self._custom_version('astakos') or '')
            base_url = astakos_endpoints['SNF:uiURL']
            base_url = base_url[:-3]
            #base_url = ''.join(base_url.split('/ui'))
        else:
            base_url = self._custom_url('astakos')
        if not base_url:
            raise CLIBaseUrlError(service='astakos')
        self.client = AstakosClient(
            base_url, logger=get_logger('kamaki.clients'))

    def main(self):
        self._run()


@command(snfastakos_cmds)
class astakos_user_info(_astakos_init, _optional_json):
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
    @astakoserror
    def _run(self):
        self._print(
            self.client.get_user_info(self.token, self['usage']), print_dict)

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(snfastakos_cmds)
class astakos_user_name(_astakos_init, _optional_json):
    """Get username(s) from uuid(s)"""

    arguments = dict(
        service_token=ValueArgument(
            'Use service token instead', '--service-token')
    )

    @errors.generic.all
    @astakoserror
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
class astakos_user_uuid(_astakos_init, _optional_json):
    """Get uuid(s) from username(s)"""

    @errors.generic.all
    @astakoserror
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

    @staticmethod
    def _print_with_format(d):
        """ Print d with size formating when needed
        :param d: (dict) {system: {<service>: {usage: ..., limit: ..., }, ...}}
        """
        newd = dict()
        for k, service in d['system'].items():
            newd[k] = dict(service)
            for term in ('usage', 'limit'):
                if term in service:
                    newd[k][term] = format_size(service[term])
        print_dict(newd)

    @errors.generic.all
    @astakoserror
    def _run(self):
            self._print(
                self.client.get_quotas(self.token), self._print_with_format)

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(snfastakos_cmds)
class astakos_services(_astakos_init):
    """Astakos operations filtered by services"""


@command(snfastakos_cmds)
class astakos_services_list(_astakos_init, _optional_json):
    """List available services"""

    @errors.generic.all
    @astakoserror
    def _run(self):
        self._print(self.client.get_services())

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(snfastakos_cmds)
class astakos_services_username(_astakos_init, _optional_json):
    """Get service username(s) from uuid(s)"""

    @errors.generic.all
    @astakoserror
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

    @errors.generic.all
    @astakoserror
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

    @errors.generic.all
    @astakoserror
    def _run(self, stoken):
        self._print(self.client.service_get_quotas(stoken, self['uuid']))

    def main(self, service_token):
        super(self.__class__, self)._run()
        self._run(service_token)


@command(snfastakos_cmds)
class astakos_resources(_astakos_init, _optional_json):
    """List user resources"""

    @errors.generic.all
    @astakoserror
    def _run(self):
        self._print(self.client.get_resources(), print_dict)

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(snfastakos_cmds)
class astakos_feedback(_astakos_init):
    """Send feedback to astakos server"""

    @errors.generic.all
    @astakoserror
    def _run(self, msg, more_info=None):
        self.client.send_feedback(self.token, msg, more_info or '')

    def main(self, message, more_info=None):
        super(self.__class__, self)._run()
        self._run(message, more_info)


@command(snfastakos_cmds)
class astakos_endpoints(_astakos_init, _optional_json):
    """Get endpoints service endpoints"""

    arguments = dict(uuid=ValueArgument('User uuid', '--uuid'))

    @errors.generic.all
    @astakoserror
    def _run(self):
        self._print(
            self.client.get_endpoints(self.token, self['uuid']),
            print_dict)

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(snfastakos_cmds)
class astakos_commission(_astakos_init):
    """Manage commissions (special privileges required)"""


@command(snfastakos_cmds)
class astakos_commission_pending(_astakos_init, _optional_json):
    """List pending commissions (special privileges required)"""

    @errors.generic.all
    @astakoserror
    def _run(self):
        self._print(self.client.get_pending_commissions(self.token))

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(snfastakos_cmds)
class astakos_commission_info(_astakos_init, _optional_json):
    """Get commission info (special privileges required)"""

    @errors.generic.all
    @astakoserror
    def _run(self, commission_id):
        commission_id = int(commission_id)
        self._print(
            self.client.get_commission_info(self.token, commission_id),
            print_dict)

    def main(self, commission_id):
        super(self.__class__, self)._run()
        self._run(commission_id)


@command(snfastakos_cmds)
class astakos_commission_action(_astakos_init, _optional_json):
    """Invoke an action in a commission (special privileges required)
    Actions can be accept or reject
    """

    actions = ('accept', 'reject')

    @errors.generic.all
    @astakoserror
    def _run(self, commission_id, action):
        commission_id = int(commission_id)
        action = action.lower()
        assert action in self.actions, 'Actions can be %s' % (
            ' or '.join(self.actions))
        self._print(
            self.client.commission_acction(self.token, commission_id, action),
            print_dict)

    def main(self, commission_id, action):
        super(self.__class__, self)._run()
        self._run(commission_id, action)


@command(snfastakos_cmds)
class astakos_commission_accept(_astakos_init):
    """Accept a pending commission  (special privileges required)"""

    @errors.generic.all
    @astakoserror
    def _run(self, commission_id):
        commission_id = int(commission_id)
        self.client.accept_commission(self.token, commission_id)

    def main(self, commission_id):
        super(self.__class__, self)._run()
        self._run(commission_id)


@command(snfastakos_cmds)
class astakos_commission_reject(_astakos_init):
    """Reject a pending commission  (special privileges required)"""

    @errors.generic.all
    @astakoserror
    def _run(self, commission_id):
        commission_id = int(commission_id)
        self.client.reject_commission(self.token, commission_id)

    def main(self, commission_id):
        super(self.__class__, self)._run()
        self._run(commission_id)


@command(snfastakos_cmds)
class astakos_commission_resolve(_astakos_init, _optional_json):
    """Resolve multiple commissions  (special privileges required)"""

    arguments = dict(
        accept=CommaSeparatedListArgument(
            'commission ids to accept (e.g. --accept=11,12,13,...',
            '--accept'),
        reject=CommaSeparatedListArgument(
            'commission ids to reject (e.g. --reject=11,12,13,...',
            '--reject'),
    )

    @errors.generic.all
    @astakoserror
    def _run(self):
        print 'accepted ', self['accept']
        print 'rejected ', self['reject']
        self._print(
            self.client.resolve_commissions(
                self.token, self['accept'], self['reject']),
            print_dict)

    def main(self):
        super(self.__class__, self)._run()
        self._run()

# commission pending
# commission info
# commission action
# commission accept
# commission reject
# commission resolve

# XXX issue_commission, issue_one_commission


@command(snfastakos_cmds)
class astakos_test(_astakos_init):
    """Test an astakos command"""

    @errors.generic.all
    @astakoserror
    def _run(self, *args):
        r = self.client.get_pending_commissions(self.token)
        print r

    def main(self, *args):
        super(self.__class__, self)._run()
        self._run(*args)
