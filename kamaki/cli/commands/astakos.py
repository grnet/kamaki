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

from json import load
from os.path import abspath

from kamaki.cli import command
from kamaki.clients.astakos import AstakosClient, SynnefoAstakosClient
from kamaki.cli.commands import (
    _command_init, errors, _optional_json, addLogSettings)
from kamaki.cli.command_tree import CommandTree
from kamaki.cli.errors import CLIBaseUrlError, CLIError
from kamaki.cli.argument import FlagArgument, ValueArgument, IntArgument
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


#  command project


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
        self.writeln('Application is submitted successfully')
        return r
    return wrap


@command(project_commands)
class project_list(_init_synnefo_astakosclient, _optional_json):
    """List all projects"""

    arguments = dict(
        name=ValueArgument('Filter by name', ('--with-name', )),
        state=ValueArgument('Filter by state', ('--with-state', )),
        owner=ValueArgument('Filter by owner', ('--with-owner', ))
    )

    @errors.generic.all
    @errors.user.astakosclient
    def _run(self):
        self._print(self.client.get_projects(
            self['name'], self['state'], self['owner']))

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(project_commands)
class project_info(_init_synnefo_astakosclient, _optional_json):
    """Get details for a project"""

    @errors.generic.all
    @errors.user.astakosclient
    def _run(self, project_id):
        self._print(
            self.client.get_project(project_id), self.print_dict)

    def main(self, project_id):
        super(self.__class__, self)._run()
        self._run(project_id)


@command(project_commands)
class project_create(_init_synnefo_astakosclient, _optional_json):
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
    @errors.user.astakosclient
    @apply_notification
    def _run(self):
        input_stream = open(abspath(self['specs_path'])) if (
            self['specs_path']) else self._in
        specs = load(input_stream)
        self._print(
            self.client.create_project(specs), self.print_dict)

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(project_commands)
class project_modify(_init_synnefo_astakosclient, _optional_json):
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
    @errors.user.astakosclient
    @apply_notification
    def _run(self, project_id):
        input_stream = open(abspath(self['specs_path'])) if (
            self['specs_path']) else self._in
        specs = load(input_stream)
        self._print(
            self.client.modify_project(project_id, specs),
            self.print_dict)

    def main(self, project_id):
        super(self.__class__, self)._run()
        self._run(project_id)


class _project_action(_init_synnefo_astakosclient):

    action = ''

    @errors.generic.all
    @errors.user.astakosclient
    def _run(self, project_id, quote_a_reason):
        self.client.project_action(project_id, self.action, quote_a_reason)

    def main(self, project_id, quote_a_reason=''):
        super(_project_action, self)._run()
        self._run(project_id, quote_a_reason)


@command(project_commands)
class project_suspend(_project_action):
    """Suspend a project (special privileges needed)"""
    action = 'suspend'


@command(project_commands)
class project_unsuspend(_project_action):
    """Resume a suspended project (special privileges needed)"""
    action = 'unsuspend'


@command(project_commands)
class project_terminate(_project_action):
    """Terminate a project (special privileges needed)"""
    action = 'terminate'


@command(project_commands)
class project_reinstate(_project_action):
    """Reinstate a terminated project (special privileges needed)"""
    action = 'reinstate'


@command(project_commands)
class project_application(_init_synnefo_astakosclient):
    """Application management commands"""


@command(project_commands)
class project_application_list(_init_synnefo_astakosclient, _optional_json):
    """List all applications (old and new)"""

    arguments = dict(
        project=IntArgument('Filter by project id', '--with-project-id')
    )

    @errors.generic.all
    @errors.user.astakosclient
    def _run(self):
        self._print(self.client.get_applications(self['project']))

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(project_commands)
class project_application_info(_init_synnefo_astakosclient, _optional_json):
    """Get details on an application"""

    @errors.generic.all
    @errors.user.astakosclient
    def _run(self, app_id):
        self._print(
            self.client.get_application(app_id), self.print_dict)

    def main(self, application_id):
        super(self.__class__, self)._run()
        self._run(application_id)


class _application_action(_init_synnefo_astakosclient):

    action = ''

    @errors.generic.all
    @errors.user.astakosclient
    def _run(self, app_id, quote_a_reason):
        self.client.application_action(app_id, self.action, quote_a_reason)

    def main(self, application_id, quote_a_reason=''):
        super(_application_action, self)._run()
        self._run(application_id, quote_a_reason)


@command(project_commands)
class project_application_approve(_application_action):
    """Approve an application (special privileges needed)"""
    action = 'approve'


@command(project_commands)
class project_application_deny(_application_action):
    """Deny an application (special privileges needed)"""
    action = 'deny'


@command(project_commands)
class project_application_dismiss(_application_action):
    """Dismiss your denied application"""
    action = 'dismiss'


@command(project_commands)
class project_application_cancel(_application_action):
    """Cancel your application"""
    action = 'cancel'


@command(project_commands)
class project_membership(_init_synnefo_astakosclient):
    """Project membership management commands"""


@command(project_commands)
class project_membership_list(_init_synnefo_astakosclient, _optional_json):
    """List all memberships"""

    arguments = dict(
        project=IntArgument('Filter by project id', '--with-project-id')
    )

    @errors.generic.all
    @errors.user.astakosclient
    def _run(self):
        self._print(self.client.get_memberships(self['project']))

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(project_commands)
class project_membership_info(_init_synnefo_astakosclient, _optional_json):
    """Details on a membership"""

    @errors.generic.all
    @errors.user.astakosclient
    def _run(self, memb_id):
        self._print(
            self.client.get_membership(memb_id), self.print_dict)

    def main(self, membership_id):
        super(self.__class__, self)._run()
        self._run(membership_id)


class _membership_action(_init_synnefo_astakosclient, _optional_json):

    action = ''

    @errors.generic.all
    @errors.user.astakosclient
    def _run(self, memb_id, quote_a_reason):
        self._print(self.client.membership_action(
            memb_id, self.action, quote_a_reason))

    def main(self, membership_id, quote_a_reason=''):
        super(_membership_action, self)._run()
        self._run(membership_id, quote_a_reason)


@command(project_commands)
class project_membership_leave(_membership_action):
    """Leave a project you have membership to"""
    action = 'leave'


@command(project_commands)
class project_membership_cancel(_membership_action):
    """Cancel your (probably pending) membership to a project"""
    action = 'cancel'


@command(project_commands)
class project_membership_accept(_membership_action):
    """Accept a membership for a project you manage"""
    action = 'accept'


@command(project_commands)
class project_membership_reject(_membership_action):
    """Reject a membership for a project you manage"""
    action = 'reject'


@command(project_commands)
class project_membership_remove(_membership_action):
    """Remove a membership for a project you manage"""
    action = 'remove'


@command(project_commands)
class project_membership_join(_init_synnefo_astakosclient):
    """Join a project"""

    @errors.generic.all
    @errors.user.astakosclient
    def _run(self, project_id):
        self.writeln(self.client.join_project(project_id))

    def main(self, project_id):
        super(project_membership_join, self)._run()
        self._run(project_id)


@command(project_commands)
class project_membership_enroll(_init_synnefo_astakosclient):
    """Enroll somebody to a project you manage"""

    @errors.generic.all
    @errors.user.astakosclient
    def _run(self, project_id, email):
        self.writeln(self.client.enroll_member(project_id, email))

    def main(self, project_id, email):
        super(project_membership_join, self)._run()
        self._run(project_id, email)
