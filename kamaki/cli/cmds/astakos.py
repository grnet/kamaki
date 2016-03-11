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
from kamaki.clients.astakos import LoggedAstakosClient, ClientError
from kamaki.cli.cmds import (
    CommandInit, NameFilter, OptionalOutput, errors, client_log)
from kamaki.cli.cmdtree import CommandTree
from kamaki.cli.errors import (
    CLIBaseUrlError, CLISyntaxError, CLIError, CLIInvalidArgument)
from kamaki.cli.argument import (
    FlagArgument, ValueArgument, IntArgument, CommaSeparatedListArgument,
    KeyValueArgument, DateArgument, BooleanArgument, UserAccountArgument,
    RepeatableArgument)
from kamaki.cli.utils import format_size, filter_dicts_by_dict

#  Mandatory

user_cmds = CommandTree('user', 'Astakos/Identity API commands')
quota_cmds = CommandTree(
    'quota', 'Astakos/Account API commands for quotas')
resource_cmds = CommandTree(
    'resource', 'Astakos/Account API commands for resources')
project_cmds = CommandTree('project', 'Astakos project API commands')
membership_cmds = CommandTree(
    'membership', 'Astakos project membership API commands')


#  Optional

endpoint_cmds = CommandTree(
    'endpoint', 'Astakos/Account API commands for endpoints')
service_cmds = CommandTree('service', 'Astakos API commands for services')
commission_cmds = CommandTree(
    'commission', 'Astakos API commands for commissions')

namespaces = [
    user_cmds, quota_cmds, resource_cmds, project_cmds, service_cmds,
    commission_cmds, endpoint_cmds, membership_cmds]


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
    wrap.__name__ = func.__name__
    return wrap


class _AstakosInit(CommandInit):

    @errors.Generic.all
    @errors.Astakos.astakosclient
    @client_log
    def _run(self):
        if getattr(self, 'cloud', None):
            endpoint_url = self._custom_url('astakos')
            if endpoint_url:
                token = self._custom_token(
                    'astakos') or self.config.get_cloud(
                    self.cloud, 'token')
                token = token.split()[0] if ' ' in token else token
                self.client = LoggedAstakosClient(endpoint_url, token)
                return
        else:
            self.cloud = 'default'
        if getattr(self, 'astakos', None):
            self.client = self.astakos.get_client()
            return
        raise CLIBaseUrlError(service='astakos')

    def main(self):
        self._run()


@command(quota_cmds)
class quota_list(_AstakosInit, OptionalOutput):
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

    @errors.Generic.all
    @errors.Astakos.astakosclient
    def _run(self):
        quotas = self.client.get_quotas()
        if self['project_id']:
            try:
                resources = quotas[self['project_id']]
            except KeyError:
                raise CLIError(
                    'User not assigned to project with id "%s" ' % (
                        self['project_id']),
                    details=[
                        'See all quotas of current user:',
                        '  kamaki quota list'])
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
        self.print_(quotas, self._print_quotas)

    def main(self):
        super(self.__class__, self)._run()
        self._run()


#  command user session

@command(user_cmds)
class user_authenticate(_AstakosInit, OptionalOutput):
    """Authenticate a user and get all authentication information"""

    @errors.Generic.all
    @errors.Astakos.astakosclient
    @with_temp_token
    def _run(self):
        try:
            self.print_(self.client.authenticate(), self.print_dict)
        except ClientError as ce:
            if ce.status in (401, ):
                raise CLIError(
                    'Token %s was not authenticated' % self.client.token,
                    details=['%s' % ce])
            raise

    def main(self, token=None):
        super(self.__class__, self)._run()
        self._run(token=token)


@command(user_cmds)
class user_uuid2name(_AstakosInit, OptionalOutput):
    """Get user name(s) from uuid(s)"""

    @errors.Generic.all
    @errors.Astakos.astakosclient
    def _run(self, uuids):
        r = self.client.get_usernames(uuids)
        self.print_(r, self.print_dict)
        unresolved = set(uuids).difference(r)
        if unresolved:
            self.error('Unresolved uuids: %s' % ', '.join(unresolved))

    def main(self, uuid, *more_uuids):
        super(self.__class__, self)._run()
        self._run(uuids=((uuid, ) + more_uuids))


@command(user_cmds)
class user_name2uuid(_AstakosInit, OptionalOutput):
    """Get user uuid(s) from name(s)"""

    @errors.Generic.all
    @errors.Astakos.astakosclient
    def _run(self, usernames):
        r = self.client.get_uuids(usernames)
        self.print_(r, self.print_dict)
        unresolved = set(usernames).difference(r)
        if unresolved:
            self.error('Unresolved usernames: %s' % ', '.join(unresolved))

    def main(self, username, *more_usernames):
        super(self.__class__, self)._run()
        self._run(usernames=((username, ) + more_usernames))


@command(user_cmds)
class user_info(_AstakosInit, OptionalOutput):
    """Get info for (current) session user"""

    arguments = dict(
        uuid=ValueArgument('Query user with uuid', '--uuid'),
        name=ValueArgument('Query user with username/email', '--username')
    )

    @errors.Generic.all
    @errors.Astakos.astakosclient
    def _run(self):
        if self['uuid'] and self['name']:
            raise CLISyntaxError(
                'Arguments uuid and username are mutually exclusive',
                details=['Use either uuid OR username OR none, but NOT both'])
        uuid = self['uuid'] or (self._username2uuid(self['name']) if (
            self['name']) else None)
        try:
            if any([self['uuid'], self['name']]) and not uuid:
                raise KeyError()
            token = self.astakos.get_token(uuid) if uuid else None
        except KeyError:
            msg = ('id %s' % self['uuid']) if (
                self['uuid']) else 'username %s' % self['name']
            raise CLIError(
                'No user with %s in the cached session list' % msg, details=[
                    'To see all cached session users:',
                    '  kamaki user list',
                    'To authenticate and add a new user in the session list:',
                    '  kamaki user add NEW_TOKEN'])
        self.print_(self.astakos.user_info(token), self.print_dict)

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(user_cmds)
class user_add(_AstakosInit, OptionalOutput):
    """Authenticate a user by token and add to session user list (cache)"""

    arguments = dict(token=ValueArgument('Token of user to add', '--token'),)
    required = ('token', )

    @errors.Generic.all
    @errors.Astakos.astakosclient
    def _run(self):
        ask = self['token'] and self['token'] not in self.astakos._uuids
        try:
            self.print_(
                self.astakos.authenticate(self['token']), self.print_dict)
        except ClientError as ce:
            if ce.status in (401, ):
                raise CLIError(
                    'Token %s was not authenticated' % self['token'],
                    details=['%s' % ce])
        if ask and self.ask_user(
                'Token is temporarily stored in memory. Append it in '
                'configuration file as an alternative token?'):
            tokens = self.astakos._uuids.keys()
            tokens.remove(self.astakos.token)
            self['config'].set_cloud(
                self.cloud, 'token', ' '.join([self.astakos.token] + tokens))
            self['config'].write()

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(user_cmds)
class user_list(_AstakosInit, OptionalOutput):
    """List (cached) session users"""

    arguments = dict(
        detail=FlagArgument('Detailed listing', ('-l', '--detail'))
    )

    @errors.Generic.all
    @errors.Astakos.astakosclient
    def _run(self):
        self.print_([u if self['detail'] else (dict(
            id=u['id'], name=u['name'])) for u in self.astakos.list_users()])

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(user_cmds)
class user_select(_AstakosInit):
    """Select a user from the (cached) list as the current session user"""

    def __init__(self, arguments={}, astakos=None, cloud=None):
        super(_AstakosInit, self).__init__(arguments, astakos, cloud)
        self['uuid_or_username'] = UserAccountArgument(
            'User to select', ('--user'))
        self.arguments['uuid_or_username'].account_client = astakos

    required = ('uuid_or_username', )

    @errors.Generic.all
    @errors.Astakos.astakosclient
    def _run(self):
        try:
            uuid = self['uuid_or_username']
            first_token = self.astakos.get_token(uuid)
        except KeyError:
            raise CLIError(
                'No user with uuid %s in the cached session list' % uuid,
                details=[
                    'To see all cached session users:', '  kamaki user list'])
        if self.astakos.token != first_token:
            self.astakos.token = first_token
            name = self.astakos.user_info()['name'] or '<USER>'
            self.error('User %s with id %s is now the current session user' % (
                name, uuid))
            if self.ask_user(
                    'Make %s the default user for future sessions?' % name):
                tokens = self.astakos._uuids.keys()
                tokens.remove(self.astakos.token)
                tokens.insert(0, self.astakos.token)
                self['config'].set_cloud(
                    self.cloud, 'token',  ' '.join(tokens))
                self['config'].write()
                self.error('%s is now the default user' % name)
        else:
            name = self.astakos.user_info()['name'] or '<USER>'
            self.error('User %s is already the selected session user' % name)

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(user_cmds)
class user_delete(_AstakosInit):
    """Delete a user (token) from the list of session users"""

    def __init__(self, arguments={}, astakos=None, cloud=None):
        super(_AstakosInit, self).__init__(arguments, astakos, cloud)
        self['uuid_or_username'] = UserAccountArgument(
            'User to delete', ('--user'))
        self.arguments['uuid_or_username'].account_client = astakos

    required = ('uuid_or_username', )

    @errors.Generic.all
    @errors.Astakos.astakosclient
    def _run(self):
        uuid = self['uuid_or_username']
        if uuid == self.astakos.user_term('id'):
            raise CLIError('Cannot remove current session user', details=[
                'To see all cached session users',
                '  kamaki user list',
                'To see current session user',
                '  kamaki user info',
                'To select a different session user',
                '  kamaki user select --user=UUID_OR_USERNAME'])
        try:
            self.astakos.remove_user(uuid)
        except KeyError:
            raise CLIError(
                'No user with uuid %s in session list' % uuid,
                details=[
                    'To see all cached session users',
                    '  kamaki user list',
                    'To authenticate and add a new user in the session list',
                    '  kamaki user add --token=NEW_TOKEN'])
        if self.ask_user('Delete user token from config file?'):
            self['config'].set_cloud(
                self.cloud, 'token', ' '.join(self.astakos._uuids.keys()))
            self['config'].write()

    def main(self):
        super(self.__class__, self)._run()
        self._run()


#  command admin

@command(service_cmds)
class service_list(_AstakosInit, OptionalOutput):
    """List available services"""

    @errors.Generic.all
    @errors.Astakos.astakosclient
    def _run(self):
        self.print_(self.client.get_services())

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(service_cmds)
class service_uuid2username(_AstakosInit, OptionalOutput):
    """Get service username(s) from uuid(s)"""

    arguments = dict(
        service_token=ValueArgument('Authenticate service', '--service-token'),
        uuid=RepeatableArgument('User UUID (can be repeated)', '--uuid')
    )
    required = ('service_token', 'uuid')

    @errors.Generic.all
    @errors.Astakos.astakosclient
    @with_temp_token
    def _run(self):
        if 1 == len(self['uuid']):
            self.print_(self.client.service_get_username(self['uuid'][0]))
        else:
            self.print_(
                self.client.service_get_usernames(self['uuid']),
                self.print_dict)

    def main(self):
        super(self.__class__, self)._run()
        self._run(token=self['service_token'])


@command(service_cmds)
class service_username2uuid(_AstakosInit, OptionalOutput):
    """Get service uuid(s) from username(s)"""

    arguments = dict(
        service_token=ValueArgument('Authenticate service', '--service-token'),
        username=RepeatableArgument('Username (can be repeated)', '--username')
    )
    required = ('service_token', 'username')

    @errors.Generic.all
    @errors.Astakos.astakosclient
    @with_temp_token
    def _run(self):
        if 1 == len(self['username']):
            self.print_(self.client.service_get_uuid(self['username'][0]))
        else:
            self.print_(
                self.client.service_get_uuids(self['username']),
                self.print_dict)

    def main(self):
        super(self.__class__, self)._run()
        self._run(token=self['service_token'])


@command(service_cmds)
class service_quotas(_AstakosInit, OptionalOutput):
    """Get service quotas"""

    arguments = dict(
        service_token=ValueArgument('Authenticate service', '--service-token'),
        uuid=ValueArgument('A user uuid to get quotas for', '--uuid')
    )
    required = ('service_token')

    @errors.Generic.all
    @errors.Astakos.astakosclient
    @with_temp_token
    def _run(self):
        self.print_(self.client.service_get_quotas(self['uuid']))

    def main(self):
        super(self.__class__, self)._run()
        self._run(token=self['service_token'])


@command(commission_cmds)
class commission_pending(_AstakosInit, OptionalOutput):
    """List pending commissions (special privileges required)"""

    @errors.Generic.all
    @errors.Astakos.astakosclient
    def _run(self):
        self.print_(self.client.get_pending_commissions())

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(commission_cmds)
class commission_info(_AstakosInit, OptionalOutput):
    """Get commission info (special privileges required)"""

    @errors.Generic.all
    @errors.Astakos.astakosclient
    def _run(self, commission_id):
        commission_id = int(commission_id)
        self.print_(
            self.client.get_commission_info(commission_id), self.print_dict)

    def main(self, commission_id):
        super(self.__class__, self)._run()
        self._run(commission_id)


@command(commission_cmds)
class commission_accept(_AstakosInit):
    """Accept a pending commission  (special privileges required)"""

    @errors.Generic.all
    @errors.Astakos.astakosclient
    def _run(self, commission_id):
        commission_id = int(commission_id)
        self.client.accept_commission(commission_id)

    def main(self, commission_id):
        super(self.__class__, self)._run()
        self._run(commission_id)


@command(commission_cmds)
class commission_reject(_AstakosInit):
    """Reject a pending commission (special privileges required)"""

    @errors.Generic.all
    @errors.Astakos.astakosclient
    def _run(self, commission_id):
        commission_id = int(commission_id)
        self.client.reject_commission(commission_id)

    def main(self, commission_id):
        super(self.__class__, self)._run()
        self._run(commission_id)


@command(commission_cmds)
class commission_resolve(_AstakosInit, OptionalOutput):
    """Resolve multiple commissions (special privileges required)"""

    arguments = dict(
        accept=CommaSeparatedListArgument(
            'commission ids to accept (e.g., --accept=11,12,13,...)',
            '--accept'),
        reject=CommaSeparatedListArgument(
            'commission ids to reject (e.g., --reject=11,12,13,...)',
            '--reject')
    )
    required = ['accept', 'reject']

    @errors.Generic.all
    @errors.Astakos.astakosclient
    def _run(self):
        r = self.client.resolve_commissions(
            self['accept'] or [], self['reject'] or [])
        self.print_(r, self.print_dict)

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(commission_cmds)
class commission_issue(_AstakosInit, OptionalOutput):
    """Issue commissions as a json string (special privileges required)"""

    arguments = dict(
        uuid=ValueArgument('User UUID', '--uuid'),
        source=ValueArgument('Commission source (ex system)', '--source'),
        file_path=ValueArgument('File of provisions', '--provisions-file'),
        description=ValueArgument('Commision description', '--description'),
        force=FlagArgument('Force commission', '--force'),
        accept=FlagArgument('Do not wait for verification', '--accept')
    )
    required = ('uuid', 'source', 'file_path')

    @errors.Generic.all
    @errors.Astakos.astakosclient
    def _run(self):
        try:
            with open(self['file_path']) as f:
                provisions = loads(f.read())
        except Exception as e:
            raise CLIError(
                'Failed load a json dict from file %s' % self['file_path'],
                importance=2, details=['%s' % e])
        self.print_(self.client.issue_one_commission(
            self['uuid'], self['source'], provisions,
            self['description'] or '', self['force'], self['accept']))

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(resource_cmds)
class resource_list(_AstakosInit, OptionalOutput):
    """List user resources"""

    @errors.Generic.all
    @errors.Astakos.astakosclient
    def _run(self):
        self.print_(self.client.get_resources(), self.print_dict)

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(endpoint_cmds)
class endpoint_list(_AstakosInit, OptionalOutput, NameFilter):
    """Get endpoints service endpoints"""

    arguments = dict(endpoint_type=ValueArgument('Filter by type', '--type'))

    @errors.Generic.all
    @errors.Astakos.astakosclient
    def _run(self):
        r = self.client.get_endpoints()['access']['serviceCatalog']
        r = self._filter_by_name(r)
        if self['endpoint_type']:
            r = filter_dicts_by_dict(r, dict(type=self['endpoint_type']))
        self.print_(r)

    def main(self):
        super(self.__class__, self)._run()
        self._run()


#  command project

_project_specs = """
    {
    "name": name.in.domainlike.format,
    "owner": user-uuid,  # if omitted, request user assumed
    "homepage": homepage,  # optional
    "description": description,  # optional
    "comments": comments,  # optional
    "max_members": max_members,  # optional
    "private": true | false,  # optional
    "start_date": date,  # optional - in ISO8601 format
    "end_date": date,  # in ISO8601 format e.g., YYYY-MM-DDThh:mm:ssZ
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


@command(project_cmds)
class project_list(_AstakosInit, OptionalOutput):
    """List all projects"""

    arguments = dict(
        details=FlagArgument('Show details', ('-l', '--details')),
        name=ValueArgument('Filter by name', ('--with-name', )),
        state=ValueArgument('Filter by state', ('--with-state', )),
        owner=ValueArgument('Filter by owner', ('--with-owner', )),
    )

    @errors.Generic.all
    @errors.Astakos.astakosclient
    def _run(self):
        r = self.client.get_projects(
            self['name'], self['state'], self['owner'])
        if not (self['details'] or self['output_format']):
            r = [dict(
                id=i['id'],
                name=i['name'],
                description=i['description']) for i in r]
        self.print_(r)

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(project_cmds)
class project_info(_AstakosInit, OptionalOutput):
    """Get details for a project"""

    @errors.Generic.all
    @errors.Astakos.astakosclient
    @errors.Astakos.project_id
    def _run(self, project_id):
        self.print_(self.client.get_project(project_id), self.print_dict)

    def main(self, project_id):
        super(self.__class__, self)._run()
        self._run(project_id=project_id)


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
                    'Invalid value for %s' % self.lvalue,
                    details=['Valid values: %s' % ', '.join(self.policies)])


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


@command(project_cmds)
class project_create(_AstakosInit, OptionalOutput):
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

    @errors.Generic.all
    @errors.Astakos.astakosclient
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
        self.print_(self.client.create_project(specs), self.print_dict)

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


@command(project_cmds)
class project_modify(_AstakosInit, OptionalOutput):
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

    @errors.Generic.all
    @errors.Astakos.astakosclient
    @errors.Astakos.project_id
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

        self.print_(
            self.client.modify_project(project_id, specs), self.print_dict)

    def main(self, project_id):
        super(self.__class__, self)._run()
        if self['private'] and self['public']:
            a = self.arguments
            raise CLIInvalidArgument(
                'Invalid argument combination', details=[
                    'Arguments %s and %s are mutually exclussive' % (
                        a['private'].lvalue, a['public'].lvalue)])
        self._run(project_id=project_id)


class _ProjectAction(_AstakosInit):

    action = ''
    arguments = dict(
        reason=ValueArgument('Quote a reason for this action', '--reason'),
    )

    @errors.Generic.all
    @errors.Astakos.astakosclient
    @errors.Astakos.project_id
    def _run(self, project_id):
        self.client.project_action(
            project_id, self.action, self['reason'] or '')

    def main(self, project_id):
        super(_ProjectAction, self)._run()
        self._run(project_id=project_id)


@command(project_cmds)
class project_suspend(_ProjectAction):
    """Suspend a project (special privileges needed)"""
    action = 'suspend'


@command(project_cmds)
class project_unsuspend(_ProjectAction):
    """Resume a suspended project (special privileges needed)"""
    action = 'unsuspend'


@command(project_cmds)
class project_terminate(_ProjectAction):
    """Terminate a project (special privileges needed)"""
    action = 'terminate'


@command(project_cmds)
class project_reinstate(_ProjectAction):
    """Reinstate a terminated project (special privileges needed)"""
    action = 'reinstate'


class _ApplicationAction(_AstakosInit):

    action = ''
    arguments = dict(
        app_id=ValueArgument('The application ID', '--app-id'),
        reason=ValueArgument('Quote a reason for this action', '--reason'),
    )
    required = ('app_id', )

    @errors.Generic.all
    @errors.Astakos.astakosclient
    @errors.Astakos.project_id
    def _run(self, project_id):
        self.client.application_action(
            project_id, self['app_id'], self.action, self['reason'] or '')

    def main(self, project_id):
        super(_ApplicationAction, self)._run()
        self._run(project_id=project_id)


@command(project_cmds)
class project_approve(_ApplicationAction):
    """Approve an application (special privileges needed)"""
    action = 'approve'


@command(project_cmds)
class project_deny(_ApplicationAction):
    """Deny an application (special privileges needed)"""
    action = 'deny'


@command(project_cmds)
class project_dismiss(_ApplicationAction):
    """Dismiss your denied application"""
    action = 'dismiss'


@command(project_cmds)
class project_cancel(_ApplicationAction):
    """Cancel your application"""
    action = 'cancel'


@command(membership_cmds)
class membership(_AstakosInit):
    """Project membership management commands"""


@command(membership_cmds)
class membership_list(_AstakosInit, OptionalOutput):
    """List all memberships"""

    arguments = dict(
        project_id=ValueArgument('Filter by project id', '--project-id')
    )

    @errors.Generic.all
    @errors.Astakos.astakosclient
    @errors.Astakos.project_id
    def _run(self, project_id):
        self.print_(self.client.get_memberships(project_id))

    def main(self):
        super(self.__class__, self)._run()
        self._run(project_id=self['project_id'])


@command(membership_cmds)
class membership_info(_AstakosInit, OptionalOutput):
    """Details on a membership"""

    @errors.Generic.all
    @errors.Astakos.astakosclient
    @errors.Astakos.membership_id
    def _run(self, membership_id):
        self.print_(self.client.get_membership(membership_id), self.print_dict)

    def main(self, membership_id):
        super(self.__class__, self)._run()
        self._run(membership_id=membership_id)


class _MembershipAction(_AstakosInit, OptionalOutput):

    action = ''
    arguments = dict(reason=ValueArgument('Reason for the action', '--reason'))

    @errors.Generic.all
    @errors.Astakos.astakosclient
    @errors.Astakos.membership_id
    def _run(self, membership_id):
        self.print_(self.client.membership_action(
            membership_id, self.action, self['reason'] or ''))

    def main(self, membership_id):
        super(_MembershipAction, self)._run()
        self._run(membership_id=membership_id)


@command(membership_cmds)
class membership_leave(_MembershipAction):
    """Leave a project you have membership to"""
    action = 'leave'


@command(membership_cmds)
class membership_cancel(_MembershipAction):
    """Cancel your (probably pending) membership to a project"""
    action = 'cancel'


@command(membership_cmds)
class membership_accept(_MembershipAction):
    """Accept a membership for a project you manage"""
    action = 'accept'


@command(membership_cmds)
class membership_reject(_MembershipAction):
    """Reject a membership for a project you manage"""
    action = 'reject'


@command(membership_cmds)
class membership_remove(_MembershipAction):
    """Remove a membership for a project you manage"""
    action = 'remove'


@command(project_cmds)
class project_join(_AstakosInit):
    """Join a project"""

    @errors.Generic.all
    @errors.Astakos.astakosclient
    @errors.Astakos.project_id
    def _run(self, project_id):
        self.writeln(self.client.join_project(project_id))

    def main(self, project_id):
        super(project_join, self)._run()
        self._run(project_id=project_id)


@command(project_cmds)
class project_enroll(_AstakosInit):
    """Enroll a user to a project"""

    arguments = dict(email=ValueArgument('User e-mail', '--email'))
    required = ('email', )

    @errors.Generic.all
    @errors.Astakos.astakosclient
    @errors.Astakos.project_id
    def _run(self, project_id):
        self.writeln(self.client.enroll_member(project_id, self['email']))

    def main(self, project_id):
        super(project_enroll, self)._run()
        self._run(project_id=project_id)
