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

from json import loads, load
from sys import stdin
from os.path import abspath

from astakosclient import AstakosClient, AstakosClientException

from kamaki.cli import command
from kamaki.cli.errors import CLIBaseUrlError
from kamaki.cli.commands import (
    _command_init, errors, _optional_json, addLogSettings)
from kamaki.cli.command_tree import CommandTree
from kamaki.cli.utils import print_dict, format_size
from kamaki.cli.argument import FlagArgument, ValueArgument, IntArgument
from kamaki.cli.argument import CommaSeparatedListArgument
from kamaki.cli.logger import get_logger

snfastakos_cmds = CommandTree('astakos', 'astakosclient CLI')
snfproject_cmds = CommandTree('project', 'Synnefo project management CLI')
_commands = [snfastakos_cmds, snfproject_cmds]


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
            base_url = astakos_endpoints['publicURL']
            base_url, sep, suffix = base_url.rpartition('identity')
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
                self.client.get_usernames(self.token, uuids), print_dict)

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


@command(snfastakos_cmds)
class astakos_commission_issue(_astakos_init, _optional_json):
    """Issue commissions as a json string (special privileges required)
    Parameters:
    holder      -- user's id (string)
    source      -- commission's source (ex system) (string)
    provisions  -- resources with their quantity (json-dict from string to int)
    name        -- description of the commission (string)
    """

    arguments = dict(
        force=FlagArgument('Force commission', '--force'),
        accept=FlagArgument('Do not wait for verification', '--accept')
    )

    @errors.generic.all
    @astakoserror
    def _run(
            self, holder, source, provisions, name=''):
        provisions = loads(provisions)
        self._print(self.client.issue_one_commission(
            self.token, holder, source, provisions, name,
            self['force'], self['accept']))

    def main(self, holder, source, provisions, name=''):
        super(self.__class__, self)._run()
        self._run(holder, source, provisions, name)


@command(snfastakos_cmds)
class astakos_commission_issuejson(_astakos_init, _optional_json):
    """Issue commissions as a json string (special privileges required)"""

    @errors.generic.all
    @astakoserror
    def _run(self, info_json):
        infodict = loads(info_json)
        self._print(self.client.issue_commission(self.token, infodict))

    def main(self, info_json):
        super(self.__class__, self)._run()
        self._run(info_json)

# XXX issue_commission, issue_one_commission


# Project commands


_project_specs = """
    {
        "name": name,
        "owner": uuid,
        "homepage": homepage,         # optional
        "description": description,   # optional
        "comments": comments,         # optional
        "start_date": date,           # optional
        "end_date": date,
        "join_policy": "auto" | "moderated" | "closed",  # default: "moderated"
        "leave_policy": "auto" | "moderated" | "closed", # default: "auto"
        "resources": {
            "cyclades.vm": {
                "project_capacity": int or null,
                 "member_capacity": int
            }
        }
  }
  """


def apply_notification(foo):
    def wrap(self, *args, **kwargs):
        r = foo(self, *args, **kwargs)
        print 'Application is submitted successfully'
        return r
    return wrap


@command(snfproject_cmds)
class project_list(_astakos_init, _optional_json):
    """List all projects"""

    arguments = dict(
        name=ValueArgument('Filter by name', ('--with-name', )),
        state=ValueArgument('Filter by state', ('--with-state', )),
        owner=ValueArgument('Filter by owner', ('--with-owner', ))
    )

    @errors.generic.all
    @astakoserror
    def _run(self):
        self._print(self.client.get_projects(
            self.token, self['name'], self['state'], self['owner']))

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(snfproject_cmds)
class project_info(_astakos_init, _optional_json):
    """Get details for a project"""

    @errors.generic.all
    @astakoserror
    def _run(self, project_id):
        self._print(
            self.client.get_project(self.token, project_id), print_dict)

    def main(self, project_id):
        super(self.__class__, self)._run()
        self._run(project_id)


@command(snfproject_cmds)
class project_create(_astakos_init, _optional_json):
    """Apply for a new project (input a json-dict)
    Project details must be provided as a json-formated dict from the standard
    input, or through a file
    """

    __doc__ += _project_specs

    arguments = dict(
        specs_path=ValueArgument(
            'Specification file path (content must be in json)', '--spec-file')
    )

    @errors.generic.all
    @astakoserror
    @apply_notification
    def _run(self):
        input_stream = open(abspath(self['specs_path'])) if (
            self['specs_path']) else stdin
        specs = load(input_stream)
        self._print(self.client.create_project(self.token, specs), print_dict)

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(snfproject_cmds)
class project_modify(_astakos_init, _optional_json):
    """Modify a project (input a json-dict)
    Project details must be provided as a json-formated dict from the standard
    input, or through a file
    """

    __doc__ += _project_specs

    arguments = dict(
        specs_path=ValueArgument(
            'Specification file path (content must be in json)', '--spec-file')
    )

    @errors.generic.all
    @astakoserror
    @apply_notification
    def _run(self, project_id):
        input_stream = open(abspath(self['specs_path'])) if (
            self['specs_path']) else stdin
        specs = load(input_stream)
        self._print(
            self.client.modify_project(self.token, project_id, specs),
            print_dict)

    def main(self, project_id):
        super(self.__class__, self)._run()
        self._run(project_id)


class _project_action(_astakos_init):

    action = ''

    @errors.generic.all
    @astakoserror
    def _run(self, project_id, quote_a_reason):
        self.client.project_action(
            self.token, project_id, self.action, quote_a_reason)

    def main(self, project_id, quote_a_reason=''):
        super(_project_action, self)._run()
        self._run(project_id, quote_a_reason)


@command(snfproject_cmds)
class project_suspend(_project_action):
    """Suspend a project (special privileges needed)"""
    action = 'suspend'


@command(snfproject_cmds)
class project_unsuspend(_project_action):
    """Resume a suspended project (special privileges needed)"""
    action = 'unsuspend'


@command(snfproject_cmds)
class project_terminate(_project_action):
    """Terminate a project (special privileges needed)"""
    action = 'terminate'


@command(snfproject_cmds)
class project_reinstate(_project_action):
    """Reinstate a terminated project (special privileges needed)"""
    action = 'reinstate'


@command(snfproject_cmds)
class project_application(_astakos_init):
    """Application management commands"""


@command(snfproject_cmds)
class project_application_list(_astakos_init, _optional_json):
    """List all applications (old and new)"""

    arguments = dict(
        project=IntArgument('Filter by project id', '--with-project-id')
    )

    @errors.generic.all
    @astakoserror
    def _run(self):
        self._print(self.client.get_applications(self.token, self['project']))

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(snfproject_cmds)
class project_application_info(_astakos_init, _optional_json):
    """Get details on an application"""

    @errors.generic.all
    @astakoserror
    def _run(self, app_id):
        self._print(
            self.client.get_application(self.token, app_id), print_dict)

    def main(self, application_id):
        super(self.__class__, self)._run()
        self._run(application_id)


class _application_action(_astakos_init):

    action = ''

    @errors.generic.all
    @astakoserror
    def _run(self, app_id, quote_a_reason):
        self.client.application_action(
            self.token, app_id, self.action, quote_a_reason)

    def main(self, application_id, quote_a_reason=''):
        super(_application_action, self)._run()
        self._run(application_id, quote_a_reason)


@command(snfproject_cmds)
class project_application_approve(_application_action):
    """Approve an application (special privileges needed)"""
    action = 'approve'


@command(snfproject_cmds)
class project_application_deny(_application_action):
    """Deny an application (special privileges needed)"""
    action = 'deny'


@command(snfproject_cmds)
class project_application_dismiss(_application_action):
    """Dismiss your denied application"""
    action = 'dismiss'


@command(snfproject_cmds)
class project_application_cancel(_application_action):
    """Cancel your application"""
    action = 'cancel'


@command(snfproject_cmds)
class project_membership(_astakos_init):
    """Project membership management commands"""


@command(snfproject_cmds)
class project_membership_list(_astakos_init, _optional_json):
    """List all memberships"""

    arguments = dict(
        project=IntArgument('Filter by project id', '--with-project-id')
    )

    @errors.generic.all
    @astakoserror
    def _run(self):
        self._print(self.client.get_memberships(self.token, self['project']))

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(snfproject_cmds)
class project_membership_info(_astakos_init, _optional_json):
    """Details on a membership"""

    @errors.generic.all
    @astakoserror
    def _run(self, memb_id):
        self._print(self.client.get_membership(self.token, memb_id),
                    print_dict)

    def main(self, membership_id):
        super(self.__class__, self)._run()
        self._run(membership_id)


class _membership_action(_astakos_init, _optional_json):

    action = ''

    @errors.generic.all
    @astakoserror
    def _run(self, memb_id, quote_a_reason):
        self._print(self.client.membership_action(
            self.token, memb_id, self.action, quote_a_reason))

    def main(self, membership_id, quote_a_reason=''):
        super(_membership_action, self)._run()
        self._run(membership_id, quote_a_reason)


@command(snfproject_cmds)
class project_membership_leave(_membership_action):
    """Leave a project you have membership to"""
    action = 'leave'


@command(snfproject_cmds)
class project_membership_cancel(_membership_action):
    """Cancel your (probably pending) membership to a project"""
    action = 'cancel'


@command(snfproject_cmds)
class project_membership_accept(_membership_action):
    """Accept a membership for a project you manage"""
    action = 'accept'


@command(snfproject_cmds)
class project_membership_reject(_membership_action):
    """Reject a membership for a project you manage"""
    action = 'reject'


@command(snfproject_cmds)
class project_membership_remove(_membership_action):
    """Remove a membership for a project you manage"""
    action = 'remove'


@command(snfproject_cmds)
class project_membership_join(_astakos_init):
    """Join a project"""

    @errors.generic.all
    @astakoserror
    def _run(self, project_id):
        print self.client.join_project(self.token, project_id)

    def main(self, project_id):
        super(project_membership_join, self)._run()
        self._run(project_id)


@command(snfproject_cmds)
class project_membership_enroll(_astakos_init):
    """Enroll somebody to a project you manage"""

    @errors.generic.all
    @astakoserror
    def _run(self, project_id, email):
        print self.client.enroll_member(self.token, project_id, email)

    def main(self, project_id, email):
        super(project_membership_join, self)._run()
        self._run(project_id, email)
