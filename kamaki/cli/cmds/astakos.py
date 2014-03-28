# Copyright 2011-2014 GRNET S.A. All rights reserved.
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

from json import load, loads
from os.path import abspath

from kamaki.cli import command
from kamaki.clients.astakos import LoggedAstakosClient
from kamaki.cli.cmds import (
    CommandInit, NameFilter, OptionalOutput, errors, addLogSettings)
from kamaki.cli.cmdtree import CommandTree
from kamaki.cli.errors import (
    CLIBaseUrlError, CLISyntaxError, CLIError, CLIInvalidArgument)
from kamaki.cli.argument import (
    FlagArgument, ValueArgument, IntArgument, CommaSeparatedListArgument,
    KeyValueArgument, DateArgument, BooleanArgument)
from kamaki.cli.utils import format_size, filter_dicts_by_dict

#  Mandatory

user_commands = CommandTree('user', 'Astakos/Identity API commands')
quota_commands = CommandTree(
    'quota', 'Astakos/Account API commands for quotas')
resource_commands = CommandTree(
    'resource', 'Astakos/Account API commands for resources')
project_commands = CommandTree('project', 'Astakos project API commands')
membership_commands = CommandTree(
    'membership', 'Astakos project membership API commands')


#  Optional

endpoint_commands = CommandTree(
    'endpoint', 'Astakos/Account API commands for endpoints')
service_commands = CommandTree('service', 'Astakos API commands for services')
commission_commands = CommandTree(
    'commission', 'Astakos API commands for commissions')

_commands = [
    user_commands, quota_commands, resource_commands, project_commands,
    service_commands, commission_commands, endpoint_commands,
    membership_commands]


def with_temp_token(func):
    """ Set token to self.client.token, run func, recover old token """
    def wrap(self, *args, **kwargs):
        try:
            token = kwargs.pop('token')
        except KeyError:
            raise CLISyntaxError('A token is needed for %s' % func)
        token_bu = self.client.token
        try:
            self.client.token = token or token_bu
            return func(self, *args, **kwargs)
        finally:
            self.client.token = token_bu
    return wrap


class _init_synnefo_astakosclient(CommandInit):

    @errors.generic.all
    @errors.user.load
    @errors.user.astakosclient
    @addLogSettings
    def _run(self):
        if getattr(self, 'cloud', None):
            base_url = self._custom_url('astakos')
            if base_url:
                token = self._custom_token(
                    'astakos') or self.config.get_cloud(
                    self.cloud, 'token')
                token = token.split()[0] if ' ' in token else token
                self.client = LoggedAstakosClient(base_url, token)
                return
        else:
            self.cloud = 'default'
        if getattr(self, 'auth_base', None):
            self.client = self.auth_base.get_client()
            return
        raise CLIBaseUrlError(service='astakos')

    def main(self):
        self._run()


@command(user_commands)
class user_authenticate(_init_synnefo_astakosclient, OptionalOutput):
    """Authenticate a user and get all authentication information"""

    @errors.generic.all
    @errors.user.authenticate
    @errors.user.astakosclient
    @with_temp_token
    def _run(self):
        self._print(self.client.authenticate(), self.print_dict)

    def main(self, token=None):
        super(self.__class__, self)._run()
        self._run(token=token)


@command(user_commands)
class user_uuid2name(_init_synnefo_astakosclient, OptionalOutput):
    """Get user name(s) from uuid(s)"""

    #@errors.generic.all
    #@errors.user.astakosclient
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
class user_name2uuid(_init_synnefo_astakosclient, OptionalOutput):
    """Get user uuid(s) from name(s)"""

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


@command(quota_commands)
class quota_list(_init_synnefo_astakosclient, OptionalOutput):
    """Show user quotas"""

    _to_format = set(['cyclades.disk', 'pithos.diskspace', 'cyclades.ram'])
    arguments = dict(
        resource=ValueArgument('Filter by resource', '--resource'),
        project_id=ValueArgument('Filter by project', '--project-id'),
        bytes=FlagArgument('Show data size in bytes', '--bytes')
    )

    def _print_quotas(self, quotas, *args, **kwargs):
        if not self['bytes']:
            for project_id, resources in quotas.items():
                for r in self._to_format.intersection(resources):
                    resources[r] = dict(
                        [(k, format_size(v)) for k, v in resources[r].items()])
        self.print_dict(quotas, *args, **kwargs)

    @errors.generic.all
    @errors.user.astakosclient
    def _run(self):
        quotas = self.client.get_quotas()
        if self['project_id']:
            try:
                resources = quotas[self['project_id']]
            except KeyError:
                raise CLIError('User not assigned to project with id "%s" ' % (
                    self['project_id']), details=[
                    'See all quotas of current user:', '  kamaki quota list'])
            quotas = {self['project_id']: resources}
        if self['resource']:
            d = dict()
            for project_id, resources in quotas.items():
                r = dict()
                for resource, value in resources.items():
                    if (resource.startswith(self['resource'])):
                        r[resource] = value
                if r:
                    d[project_id] = r
            if not d:
                raise CLIError('Resource "%s" not found' % self['resource'])
            quotas = d
        self._print(quotas, self._print_quotas)

    def main(self):
        super(self.__class__, self)._run()
        self._run()


#  command user session


@command(user_commands)
class user_info(_init_synnefo_astakosclient, OptionalOutput):
    """Get info for (current) session user"""

    arguments = dict(
        uuid=ValueArgument('Query user with uuid', '--uuid'),
        name=ValueArgument('Query user with username/email', '--username')
    )

    @errors.generic.all
    @errors.user.astakosclient
    def _run(self):
        if self['uuid'] and self['name']:
            raise CLISyntaxError(
                'Arguments uuid and username are mutually exclusive',
                details=['Use either uuid OR username OR none, not both'])
        uuid = self['uuid'] or (self._username2uuid(self['name']) if (
            self['name']) else None)
        try:
            token = self.auth_base.get_token(uuid) if uuid else None
        except KeyError:
            msg = ('id %s' % self['uuid']) if (
                self['uuid']) else 'username %s' % self['name']
            raise CLIError(
                'No user with %s in the cached session list' % msg, details=[
                    'To see all cached session users',
                    '  /user list',
                    'To authenticate and add a new user in the session list',
                    '  /user add <new token>'])
        self._print(self.auth_base.user_info(token), self.print_dict)


@command(user_commands)
class user_add(_init_synnefo_astakosclient, OptionalOutput):
    """Authenticate a user by token and add to kamaki session (cache)"""

    @errors.generic.all
    @errors.user.astakosclient
    def _run(self, token=None):
        ask = token and token not in self.auth_base._uuids
        self._print(self.auth_base.authenticate(token), self.print_dict)
        if ask and self.ask_user(
                'Token is temporarily stored in memory. If it is stored in'
                ' kamaki configuration file, it will be available in later'
                ' sessions. Do you want to permanently store this token?'):
            tokens = self.auth_base._uuids.keys()
            tokens.remove(self.auth_base.token)
            self['config'].set_cloud(
                self.cloud, 'token', ' '.join([self.auth_base.token] + tokens))
            self['config'].write()

    def main(self, new_token=None):
        super(self.__class__, self)._run()
        self._run(token=new_token)


@command(user_commands)
class user_list(_init_synnefo_astakosclient, OptionalOutput):
    """List (cached) session users"""

    arguments = dict(
        detail=FlagArgument('Detailed listing', ('-l', '--detail'))
    )

    @errors.generic.all
    @errors.user.astakosclient
    def _run(self):
        self._print([u if self['detail'] else (dict(
            id=u['id'], name=u['name'])) for u in self.auth_base.list_users()])

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(user_commands)
class user_select(_init_synnefo_astakosclient):
    """Select a user from the (cached) list as the current session user"""

    @errors.generic.all
    @errors.user.astakosclient
    def _run(self, uuid):
        try:
            first_token = self.auth_base.get_token(uuid)
        except KeyError:
            raise CLIError(
                'No user with uuid %s in the cached session list' % uuid,
                details=[
                    'To see all cached session users',
                    '  /user list',
                    'To authenticate and add a new user in the session list',
                    '  /user add <new token>'])
        if self.auth_base.token != first_token:
            self.auth_base.token = first_token
            msg = 'User with id %s is now the current session user.\n' % uuid
            msg += 'Do you want future sessions to also start with this user?'
            if self.ask_user(msg):
                tokens = self.auth_base._uuids.keys()
                tokens.remove(self.auth_base.token)
                tokens.insert(0, self.auth_base.token)
                self['config'].set_cloud(
                    self.cloud, 'token',  ' '.join(tokens))
                self['config'].write()
                self.error('User is selected for next sessions')
            else:
                self.error('User is not permanently selected')
        else:
            self.error('User was already the selected session user')

    def main(self, user_uuid):
        super(self.__class__, self)._run()
        self._run(uuid=user_uuid)


@command(user_commands)
class user_delete(_init_synnefo_astakosclient):
    """Delete a user (token) from the (cached) list of session users"""

    @errors.generic.all
    @errors.user.astakosclient
    def _run(self, uuid):
        if uuid == self.auth_base.user_term('id'):
            raise CLIError('Cannot remove current session user', details=[
                'To see all cached session users',
                '  /user list',
                'To see current session user',
                '  /user info',
                'To select a different session user',
                '  /user select <user uuid>'])
        try:
            self.auth_base.remove_user(uuid)
        except KeyError:
            raise CLIError('No user with uuid %s in session list' % uuid,
                details=[
                    'To see all cached session users',
                    '  /user list',
                    'To authenticate and add a new user in the session list',
                    '  /user add <new token>'])
        if self.ask_user(
                'User is removed from current session, but will be restored in'
                ' the next session. Remove the user from future sessions?'):
            self['config'].set_cloud(
                self.cloud, 'token', ' '.join(self.auth_base._uuids.keys()))
            self['config'].write()

    def main(self, user_uuid):
        super(self.__class__, self)._run()
        self._run(uuid=user_uuid)


#  command admin

@command(service_commands)
class service_list(_init_synnefo_astakosclient, OptionalOutput):
    """List available services"""

    @errors.generic.all
    @errors.user.astakosclient
    def _run(self):
        self._print(self.client.get_services())

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(service_commands)
class service_uuid2username(_init_synnefo_astakosclient, OptionalOutput):
    """Get service username(s) from uuid(s)"""

    @errors.generic.all
    @errors.user.astakosclient
    @with_temp_token
    def _run(self, uuids):
        if 1 == len(uuids):
            self._print(self.client.service_get_username(uuids[0]))
        else:
            self._print(
                self.client.service_get_usernames(uuids),
                self.print_dict)

    def main(self, service_token, uuid, *more_uuids):
        super(self.__class__, self)._run()
        self._run([uuid] + list(more_uuids), token=service_token)


@command(service_commands)
class service_username2uuid(_init_synnefo_astakosclient, OptionalOutput):
    """Get service uuid(s) from username(s)"""

    @errors.generic.all
    @errors.user.astakosclient
    @with_temp_token
    def _run(self, usernames):
        if 1 == len(usernames):
            self._print(self.client.service_get_uuid(usernames[0]))
        else:
            self._print(
                self.client.service_get_uuids(usernames),
                self.print_dict)

    def main(self, service_token, usernames, *more_usernames):
        super(self.__class__, self)._run()
        self._run([usernames] + list(more_usernames), token=service_token)


@command(service_commands)
class service_quotas(_init_synnefo_astakosclient, OptionalOutput):
    """Get service quotas"""

    arguments = dict(
        uuid=ValueArgument('A user uuid to get quotas for', '--uuid')
    )

    @errors.generic.all
    @errors.user.astakosclient
    @with_temp_token
    def _run(self):
        self._print(self.client.service_get_quotas(self['uuid']))

    def main(self, service_token):
        super(self.__class__, self)._run()
        self._run(token=service_token)


@command(commission_commands)
class commission_pending(_init_synnefo_astakosclient, OptionalOutput):
    """List pending commissions (special privileges required)"""

    @errors.generic.all
    @errors.user.astakosclient
    def _run(self):
        self._print(self.client.get_pending_commissions())

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(commission_commands)
class commission_info(_init_synnefo_astakosclient, OptionalOutput):
    """Get commission info (special privileges required)"""

    @errors.generic.all
    @errors.user.astakosclient
    def _run(self, commission_id):
        commission_id = int(commission_id)
        self._print(
            self.client.get_commission_info(commission_id), self.print_dict)

    def main(self, commission_id):
        super(self.__class__, self)._run()
        self._run(commission_id)


@command(commission_commands)
class commission_accept(_init_synnefo_astakosclient):
    """Accept a pending commission  (special privileges required)"""

    @errors.generic.all
    @errors.user.astakosclient
    def _run(self, commission_id):
        commission_id = int(commission_id)
        self.client.accept_commission(commission_id)

    def main(self, commission_id):
        super(self.__class__, self)._run()
        self._run(commission_id)


@command(commission_commands)
class commission_reject(_init_synnefo_astakosclient):
    """Reject a pending commission (special privileges required)"""

    @errors.generic.all
    @errors.user.astakosclient
    def _run(self, commission_id):
        commission_id = int(commission_id)
        self.client.reject_commission(commission_id)

    def main(self, commission_id):
        super(self.__class__, self)._run()
        self._run(commission_id)


@command(commission_commands)
class commission_resolve(_init_synnefo_astakosclient, OptionalOutput):
    """Resolve multiple commissions (special privileges required)"""

    arguments = dict(
        accept=CommaSeparatedListArgument(
            'commission ids to accept (e.g., --accept=11,12,13,...',
            '--accept'),
        reject=CommaSeparatedListArgument(
            'commission ids to reject (e.g., --reject=11,12,13,...',
            '--reject')
    )

    @errors.generic.all
    @errors.user.astakosclient
    def _run(self):
        self.writeln('accepted ', self['accept'])
        self.writeln('rejected ', self['reject'])
        self._print(
            self.client.resolve_commissions(self['accept'], self['reject']),
            self.print_dict)

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(commission_commands)
class commission_issue(_init_synnefo_astakosclient, OptionalOutput):
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
    @errors.user.astakosclient
    def _run(self, holder, source, provisions, name=''):
        provisions = loads(provisions)
        self._print(self.client.issue_one_commission(
            holder, source, provisions, name,
            self['force'], self['accept']))

    def main(self, user_uuid, source, provisions_file, name=''):
        super(self.__class__, self)._run()
        self._run(user_uuid, source, provisions_file, name)


@command(resource_commands)
class resource_list(_init_synnefo_astakosclient, OptionalOutput):
    """List user resources"""

    @errors.generic.all
    @errors.user.astakosclient
    def _run(self):
        self._print(self.client.get_resources(), self.print_dict)

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(endpoint_commands)
class endpoint_list(_init_synnefo_astakosclient, OptionalOutput, NameFilter):
    """Get endpoints service endpoints"""

    arguments = dict(endpoint_type=ValueArgument('Filter by type', '--type'))

    @errors.generic.all
    @errors.user.astakosclient
    def _run(self):
        r = self.client.get_endpoints()['access']['serviceCatalog']
        r = self._filter_by_name(r)
        if self['endpoint_type']:
            r = filter_dicts_by_dict(r, dict(type=self['endpoint_type']))
        self._print(r)

    def main(self):
        super(self.__class__, self)._run()
        self._run()


#  command project


_project_specs = """
    {
    "name": name,
    "owner": uuid,  # if omitted, request user assumed
    "homepage": homepage,  # optional
    "description": description,  # optional
    "comments": comments,  # optional
    "max_members": max_members,  # optional
    "private": true | false,  # optional
    "start_date": date,  # optional
    "end_date": date,
    "join_policy": "auto" | "moderated" | "closed",  # default: "moderated"
    "leave_policy": "auto" | "moderated" | "closed",  # default: "auto"
    "resources": {
    "cyclades.vm": {"project_capacity": int, "member_capacity": int
    }}}"""


def apply_notification(func):
    def wrap(self, *args, **kwargs):
        r = func(self, *args, **kwargs)
        self.error('Application is submitted successfully')
        return r
    return wrap


@command(project_commands)
class project_list(_init_synnefo_astakosclient, OptionalOutput):
    """List all projects"""

    arguments = dict(
        details=FlagArgument('Show details', ('-l', '--details')),
        name=ValueArgument('Filter by name', ('--with-name', )),
        state=ValueArgument('Filter by state', ('--with-state', )),
        owner=ValueArgument('Filter by owner', ('--with-owner', ))
    )

    @errors.generic.all
    @errors.user.astakosclient
    def _run(self):
        r = self.client.get_projects(
            self['name'], self['state'], self['owner'])
        if not (self['details'] or self['output_format']):
            r = [dict(
                id=i['id'],
                name=i['name'],
                description=i['description']) for i in r]
        self._print(r)

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(project_commands)
class project_info(_init_synnefo_astakosclient, OptionalOutput):
    """Get details for a project"""

    @errors.generic.all
    @errors.user.astakosclient
    def _run(self, project_id):
        self._print(
            self.client.get_project(project_id), self.print_dict)

    def main(self, project_id):
        super(self.__class__, self)._run()
        self._run(project_id)


class PolicyArgument(ValueArgument):
    """A Policy argument"""
    policies = ('auto', 'moderated', 'closed')

    @property
    def value(self):
        return getattr(self, '_value', None)

    @value.setter
    def value(self, new_policy):
        if new_policy:
            if new_policy.lower() in self.policies:
                self._value = new_policy.lower()
            else:
                raise CLIInvalidArgument(
                    'Invalid value for %s' % self.lvalue, details=[
                    'Valid values: %s' % ', '.join(self.policies)])


class ProjectResourceArgument(KeyValueArgument):
    """"A <resource>=<member_capacity>,<project_capacity> argument  e.g.,
    --resource cyclades.cpu=5,1
    """
    @property
    def value(self):
        return super(ProjectResourceArgument, self).value

    @value.setter
    def value(self, key_value_pairs):
        if key_value_pairs:
            super(ProjectResourceArgument, self.__class__).value.fset(
                self, key_value_pairs)
            d = dict(self._value)
            for key, value in d.items():
                try:
                    member_capacity, project_capacity = value.split(',')
                    member_capacity = int(member_capacity)
                    project_capacity = int(project_capacity)
                    assert member_capacity <= project_capacity
                except Exception as e:
                    raise CLIInvalidArgument(
                        'Invalid resource value %s' % value, details=[
                        'Usage:',
                        '  %s %s=<member_capacity>,<project_capacity>' % (
                            self.lvalue, key),
                        'where both capacities are integers',
                        'and member_capacity <= project_capacity', '',
                        '(%s)' % e])
                self._value[key] = dict(
                    member_capacity=member_capacity,
                    project_capacity=project_capacity)


@command(project_commands)
class project_create(_init_synnefo_astakosclient, OptionalOutput):
    """Apply for a new project"""

    __doc__ += _project_specs
    arguments = dict(
        specs_path=ValueArgument(
            'Specification file (contents in json)', '--spec-file'),
        project_name=ValueArgument('Name the project', '--name'),
        owner_uuid=ValueArgument('Project owner', '--owner'),
        homepage_url=ValueArgument('Project homepage', '--homepage'),
        description=ValueArgument('Describe the project', '--description'),
        max_members=IntArgument('Maximum subscribers', '--max-members'),
        private=BooleanArgument(
            'True for private, False (default) for public', '--private'),
        start_date=DateArgument('When to start the project', '--start-date'),
        end_date=DateArgument('When to end the project', '--end-date'),
        join_policy=PolicyArgument(
            'Set join policy (%s)' % ', '.join(PolicyArgument.policies),
            '--join-policy'),
        leave_policy=PolicyArgument(
            'Set leave policy (%s)' % ', '.join(PolicyArgument.policies),
            '--leave-policy'),
        resource_capacities=ProjectResourceArgument(
            'Set the member and project capacities for resources (repeatable) '
            'e.g., --resource cyclades.cpu=1,5    means "members will have at '
            'most 1 cpu but the project will have at most 5"       To see all '
            'resources:   kamaki resource list',
            '--resource')
    )
    required = ['specs_path', 'project_name', 'end_date']

    @errors.generic.all
    @errors.user.astakosclient
    @apply_notification
    def _run(self):
        specs = dict()
        if self['specs_path']:
            with open(abspath(self['specs_path'])) as f:
                specs = load(f)
        for key, arg in (
                ('name', self['project_name']),
                ('end_date', self.arguments['end_date'].isoformat),
                ('start_date', self.arguments['start_date'].isoformat),
                ('owner', self['owner_uuid']),
                ('homepage', self['homepage_url']),
                ('description', self['description']),
                ('max_members', self['max_members']),
                ('private', self['private']),
                ('join_policy', self['join_policy']),
                ('leave_policy', self['leave_policy']),
                ('resources', self['resource_capacities'])):
            if arg:
                specs[key] = arg
        self._print(self.client.create_project(specs), self.print_dict)

    def main(self):
        super(self.__class__, self)._run()
        self._req2 = [arg for arg in self.required if arg != 'specs_path']
        if not (self['specs_path'] or all(self[arg] for arg in self._req2)):
            raise CLIInvalidArgument('Insufficient arguments', details=[
                'Both of the following arguments are needed:',
                ', '.join([self.arguments[arg].lvalue for arg in self._req2]),
                'OR provide a spec file (json) with %s' % self.arguments[
                    'specs_path'].lvalue,
                'OR combine arguments (higher priority) with a file'])
        self._run()


@command(project_commands)
class project_modify(_init_synnefo_astakosclient, OptionalOutput):
    """Modify properties of a project"""

    __doc__ += _project_specs
    arguments = dict(
        specs_path=ValueArgument(
            'Specification file (contents in json)', '--spec-file'),
        project_name=ValueArgument('Name the project', '--name'),
        owner_uuid=ValueArgument('Project owner', '--owner'),
        homepage_url=ValueArgument('Project homepage', '--homepage'),
        description=ValueArgument('Describe the project', '--description'),
        max_members=IntArgument('Maximum subscribers', '--max-members'),
        private=FlagArgument('Make the project private', '--private'),
        public=FlagArgument('Make the project public', '--public'),
        start_date=DateArgument('When to start the project', '--start-date'),
        end_date=DateArgument('When to end the project', '--end-date'),
        join_policy=PolicyArgument(
            'Set join policy (%s)' % ', '.join(PolicyArgument.policies),
            '--join-policy'),
        leave_policy=PolicyArgument(
            'Set leave policy (%s)' % ', '.join(PolicyArgument.policies),
            '--leave-policy'),
        resource_capacities=ProjectResourceArgument(
            'Set the member and project capacities for resources (repeatable) '
            'e.g., --resource cyclades.cpu=1,5    means "members will have at '
            'most 1 cpu but the project will have at most 5"       To see all '
            'resources:   kamaki resource list',
            '--resource')
    )
    required = [
        'specs_path', 'owner_uuid', 'homepage_url', 'description', 'public',
        'private', 'project_name', 'start_date', 'end_date', 'join_policy',
        'leave_policy', 'resource_capacities', 'max_members']

    @errors.generic.all
    @errors.user.astakosclient
    @apply_notification
    def _run(self, project_id):
        specs = dict()
        if self['specs_path']:
            with open(abspath(self['specs_path'])) as f:
                specs = load(f)
        for key, arg in (
                ('name', self['project_name']),
                ('owner', self['owner_uuid']),
                ('homepage', self['homepage_url']),
                ('description', self['description']),
                ('max_members', self['max_members']),
                ('start_date', self.arguments['start_date'].isoformat),
                ('end_date', self.arguments['end_date'].isoformat),
                ('join_policy', self['join_policy']),
                ('leave_policy', self['leave_policy']),
                ('resources', self['resource_capacities'])):
            if arg:
                specs[key] = arg
        private = self['private'] or (False if self['public'] else None)
        if private is not None:
            self['private'] = private

        self._print(
            self.client.modify_project(project_id, specs), self.print_dict)

    def main(self, project_id):
        super(self.__class__, self)._run()
        if self['private'] and self['public']:
            a = self.arguments
            raise CLIInvalidArgument(
                'Invalid argument combination', details=[
                'Arguments %s and %s are mutually exclussive' % (
                    a['private'].lvalue, a['public'].lvalue)])
        self._run(project_id)


class _project_action(_init_synnefo_astakosclient):

    action = ''

    arguments = dict(
        reason=ValueArgument('Quote a reason for this action', '--reason'),
    )

    @errors.generic.all
    @errors.user.astakosclient
    def _run(self, project_id, quote_a_reason):
        self.client.project_action(project_id, self.action, quote_a_reason)

    def main(self, project_id):
        super(_project_action, self)._run()
        self._run(project_id, self['reason'] or '')


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


class _application_action(_init_synnefo_astakosclient):

    action = ''

    arguments = dict(
        app_id=ValueArgument('The application ID', '--app-id'),
        reason=ValueArgument('Quote a reason for this action', '--reason'),
    )
    required = ('app_id', )

    @errors.generic.all
    @errors.user.astakosclient
    def _run(self, project_id, app_id, quote_a_reason):
        self.client.application_action(
            project_id, app_id, self.action, quote_a_reason)

    def main(self, project_id):
        super(_application_action, self)._run()
        self._run(project_id, self['app_id'], self['reason'] or '')


@command(project_commands)
class project_approve(_application_action):
    """Approve an application (special privileges needed)"""
    action = 'approve'


@command(project_commands)
class project_deny(_application_action):
    """Deny an application (special privileges needed)"""
    action = 'deny'


@command(project_commands)
class project_dismiss(_application_action):
    """Dismiss your denied application"""
    action = 'dismiss'


@command(project_commands)
class project_cancel(_application_action):
    """Cancel your application"""
    action = 'cancel'


@command(membership_commands)
class membership(_init_synnefo_astakosclient):
    """Project membership management commands"""


@command(membership_commands)
class membership_list(_init_synnefo_astakosclient, OptionalOutput):
    """List all memberships"""

    arguments = dict(
        project=ValueArgument('Filter by project id', '--project-id')
    )

    @errors.generic.all
    @errors.user.astakosclient
    def _run(self):
        self._print(self.client.get_memberships(self['project']))

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(membership_commands)
class membership_info(_init_synnefo_astakosclient, OptionalOutput):
    """Details on a membership"""

    @errors.generic.all
    @errors.user.astakosclient
    def _run(self, memb_id):
        self._print(
            self.client.get_membership(memb_id), self.print_dict)

    def main(self, membership_id):
        super(self.__class__, self)._run()
        self._run(memb_id=membership_id)


class _membership_action(_init_synnefo_astakosclient, OptionalOutput):

    action = ''
    arguments = dict(reason=ValueArgument('Reason for the action', '--reason'))

    @errors.generic.all
    @errors.user.astakosclient
    def _run(self, memb_id, quote_a_reason):
        self._print(self.client.membership_action(
            memb_id, self.action, quote_a_reason))

    def main(self, membership_id):
        super(_membership_action, self)._run()
        self._run(membership_id, self['reason'] or '')


@command(membership_commands)
class membership_leave(_membership_action):
    """Leave a project you have membership to"""
    action = 'leave'


@command(membership_commands)
class membership_cancel(_membership_action):
    """Cancel your (probably pending) membership to a project"""
    action = 'cancel'


@command(membership_commands)
class membership_accept(_membership_action):
    """Accept a membership for a project you manage"""
    action = 'accept'


@command(membership_commands)
class membership_reject(_membership_action):
    """Reject a membership for a project you manage"""
    action = 'reject'


@command(membership_commands)
class membership_remove(_membership_action):
    """Remove a membership for a project you manage"""
    action = 'remove'


@command(project_commands)
class project_join(_init_synnefo_astakosclient):
    """Join a project"""

    @errors.generic.all
    @errors.user.astakosclient
    def _run(self, project_id):
        self.writeln(self.client.join_project(project_id))

    def main(self, project_id):
        super(project_join, self)._run()
        self._run(project_id)


@command(project_commands)
class project_enroll(_init_synnefo_astakosclient):
    """Enroll a user to a project"""

    arguments = dict(email=ValueArgument('User e-mail', '--email'))
    required = ('email', )

    @errors.generic.all
    @errors.user.astakosclient
    def _run(self, project_id, email):
        self.writeln(self.client.enroll_member(project_id, email))

    def main(self, project_id):
        super(project_enroll, self)._run()
        self._run(project_id, self['email'])
