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
# or implied, of GRNET S.A.

from base64 import b64encode
from os.path import exists, expanduser
from io import StringIO
from pydoc import pager

from kamaki.cli import command
from kamaki.cli.command_tree import CommandTree
from kamaki.cli.utils import remove_from_items, filter_dicts_by_dict
from kamaki.cli.errors import (
    raiseCLIError, CLISyntaxError, CLIBaseUrlError, CLIInvalidArgument)
from kamaki.clients.cyclades import CycladesClient
from kamaki.cli.argument import (
    FlagArgument, ValueArgument, KeyValueArgument, RepeatableArgument,
    ProgressBarArgument, DateArgument, IntArgument, StatusArgument)
from kamaki.cli.commands import _command_init, errors, addLogSettings
from kamaki.cli.commands import (
    _optional_output_cmd, _optional_json, _name_filter, _id_filter)


server_cmds = CommandTree('server', 'Cyclades/Compute API server commands')
flavor_cmds = CommandTree('flavor', 'Cyclades/Compute API flavor commands')
_commands = [server_cmds, flavor_cmds]


about_authentication = '\nUser Authentication:\
    \n* to check authentication: /user authenticate\
    \n* to set authentication token: /config set cloud.<cloud>.token <token>'

howto_personality = [
    'Defines a file to be injected to virtual servers file system.',
    'syntax:  PATH,[SERVER_PATH,[OWNER,[GROUP,[MODE]]]]',
    '  [local-path=]PATH: local file to be injected (relative or absolute)',
    '  [server-path=]SERVER_PATH: destination location inside server Image',
    '  [owner=]OWNER: virtual servers user id for the remote file',
    '  [group=]GROUP: virtual servers group id or name for the remote file',
    '  [mode=]MODE: permission in octal (e.g., 0777)',
    'e.g., -p /tmp/my.file,owner=root,mode=0777']

server_states = ('BUILD', 'ACTIVE', 'STOPPED', 'REBOOT')


class _service_wait(object):

    wait_arguments = dict(
        progress_bar=ProgressBarArgument(
            'do not show progress bar', ('-N', '--no-progress-bar'), False)
    )

    def _wait(
            self, service, service_id, status_method, current_status,
            countdown=True, timeout=60):
        (progress_bar, wait_cb) = self._safe_progress_bar(
            '%s %s: status is still %s' % (
                service, service_id, current_status),
            countdown=countdown, timeout=timeout)

        try:
            new_mode = status_method(
                service_id, current_status, max_wait=timeout, wait_cb=wait_cb)
            if new_mode:
                self.error('%s %s: status is now %s' % (
                    service, service_id, new_mode))
            else:
                self.error('%s %s: status is still %s' % (
                    service, service_id, current_status))
        except KeyboardInterrupt:
            self.error('\n- canceled')
        finally:
            self._safe_progress_bar_finish(progress_bar)


class _server_wait(_service_wait):

    def _wait(self, server_id, current_status, timeout=60):
        super(_server_wait, self)._wait(
            'Server', server_id, self.client.wait_server, current_status,
            countdown=(current_status not in ('BUILD', )),
            timeout=timeout if current_status not in ('BUILD', ) else 100)


class _init_cyclades(_command_init):
    @errors.generic.all
    @addLogSettings
    def _run(self, service='compute'):
        if getattr(self, 'cloud', None):
            base_url = self._custom_url(service) or self._custom_url(
                'cyclades')
            if base_url:
                token = self._custom_token(service) or self._custom_token(
                    'cyclades') or self.config.get_cloud('token')
                self.client = CycladesClient(base_url=base_url, token=token)
                return
        else:
            self.cloud = 'default'
        if getattr(self, 'auth_base', False):
            cyclades_endpoints = self.auth_base.get_service_endpoints(
                self._custom_type('cyclades') or 'compute',
                self._custom_version('cyclades') or '')
            base_url = cyclades_endpoints['publicURL']
            token = self.auth_base.token
            self.client = CycladesClient(base_url=base_url, token=token)
        else:
            raise CLIBaseUrlError(service='cyclades')

    def main(self):
        self._run()


@command(server_cmds)
class server_list(_init_cyclades, _optional_json, _name_filter, _id_filter):
    """List virtual servers accessible by user
    Use filtering arguments (e.g., --name-like) to manage long server lists
    """

    PERMANENTS = ('id', 'name')

    arguments = dict(
        detail=FlagArgument('show detailed output', ('-l', '--details')),
        since=DateArgument(
            'show only items since date (\' d/m/Y H:M:S \')',
            '--since'),
        limit=IntArgument(
            'limit number of listed virtual servers', ('-n', '--number')),
        more=FlagArgument(
            'output results in pages (-n to set items per page, default 10)',
            '--more'),
        enum=FlagArgument('Enumerate results', '--enumerate'),
        flavor_id=ValueArgument('filter by flavor id', ('--flavor-id')),
        image_id=ValueArgument('filter by image id', ('--image-id')),
        user_id=ValueArgument('filter by user id', ('--user-id')),
        user_name=ValueArgument('filter by user name', ('--user-name')),
        status=ValueArgument(
            'filter by status (ACTIVE, STOPPED, REBOOT, ERROR, etc.)',
            ('--status')),
        meta=KeyValueArgument('filter by metadata key=values', ('--metadata')),
        meta_like=KeyValueArgument(
            'print only if in key=value, the value is part of actual value',
            ('--metadata-like')),
    )

    def _add_user_name(self, servers):
        uuids = self._uuids2usernames(list(set(
                [srv['user_id'] for srv in servers] +
                [srv['tenant_id'] for srv in servers])))
        for srv in servers:
            srv['user_id'] += ' (%s)' % uuids[srv['user_id']]
            srv['tenant_id'] += ' (%s)' % uuids[srv['tenant_id']]
        return servers

    def _apply_common_filters(self, servers):
        common_filters = dict()
        if self['status']:
            common_filters['status'] = self['status']
        if self['user_id'] or self['user_name']:
            uuid = self['user_id'] or self._username2uuid(self['user_name'])
            common_filters['user_id'] = uuid
        return filter_dicts_by_dict(servers, common_filters)

    def _filter_by_image(self, servers):
        iid = self['image_id']
        return [srv for srv in servers if srv['image']['id'] == iid]

    def _filter_by_flavor(self, servers):
        fid = self['flavor_id']
        return [srv for srv in servers if (
            '%s' % srv['image']['id'] == '%s' % fid)]

    def _filter_by_metadata(self, servers):
        new_servers = []
        for srv in servers:
            if not 'metadata' in srv:
                continue
            meta = [dict(srv['metadata'])]
            if self['meta']:
                meta = filter_dicts_by_dict(meta, self['meta'])
            if meta and self['meta_like']:
                meta = filter_dicts_by_dict(
                    meta, self['meta_like'], exact_match=False)
            if meta:
                new_servers.append(srv)
        return new_servers

    @errors.generic.all
    @errors.cyclades.connection
    @errors.cyclades.date
    def _run(self):
        withimage = bool(self['image_id'])
        withflavor = bool(self['flavor_id'])
        withmeta = bool(self['meta'] or self['meta_like'])
        withcommons = bool(
            self['status'] or self['user_id'] or self['user_name'])
        detail = self['detail'] or (
            withimage or withflavor or withmeta or withcommons)
        servers = self.client.list_servers(detail, self['since'])

        servers = self._filter_by_name(servers)
        servers = self._filter_by_id(servers)
        servers = self._apply_common_filters(servers)
        if withimage:
            servers = self._filter_by_image(servers)
        if withflavor:
            servers = self._filter_by_flavor(servers)
        if withmeta:
            servers = self._filter_by_metadata(servers)

        if self['detail'] and not (
                self['json_output'] or self['output_format']):
            servers = self._add_user_name(servers)
        elif not (self['detail'] or (
                self['json_output'] or self['output_format'])):
            remove_from_items(servers, 'links')
        if detail and not self['detail']:
            for srv in servers:
                for key in set(srv).difference(self.PERMANENTS):
                    srv.pop(key)
        kwargs = dict(with_enumeration=self['enum'])
        if self['more']:
            kwargs['out'] = StringIO()
            kwargs['title'] = ()
        if self['limit']:
            servers = servers[:self['limit']]
        self._print(servers, **kwargs)
        if self['more']:
            pager(kwargs['out'].getvalue())

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(server_cmds)
class server_info(_init_cyclades, _optional_json):
    """Detailed information on a Virtual Machine"""

    arguments = dict(
        nics=FlagArgument(
            'Show only the network interfaces of this virtual server',
            '--nics'),
        network_id=ValueArgument(
            'Show the connection details to that network', '--network-id'),
        stats=FlagArgument('Get URLs for server statistics', '--stats'),
        diagnostics=FlagArgument('Diagnostic information', '--diagnostics')
    )

    @errors.generic.all
    @errors.cyclades.connection
    @errors.cyclades.server_id
    def _run(self, server_id):
        if self['nics']:
            self._print(
                self.client.get_server_nics(server_id), self.print_dict)
        elif self['network_id']:
            self._print(
                self.client.get_server_network_nics(
                    server_id, self['network_id']), self.print_dict)
        elif self['stats']:
            self._print(
                self.client.get_server_stats(server_id), self.print_dict)
        elif self['diagnostics']:
            self._print(self.client.get_server_diagnostics(server_id))
        else:
            vm = self.client.get_server_details(server_id)
            uuids = self._uuids2usernames([vm['user_id'], vm['tenant_id']])
            vm['user_id'] += ' (%s)' % uuids[vm['user_id']]
            vm['tenant_id'] += ' (%s)' % uuids[vm['tenant_id']]
            self._print(vm, self.print_dict)

    def main(self, server_id):
        super(self.__class__, self)._run()
        choose_one = ('nics', 'stats', 'diagnostics')
        count = len([a for a in choose_one if self[a]])
        if count > 1:
            raise CLIInvalidArgument('Invalid argument combination', details=[
                'Arguments %s cannot be used simultaneously' % ', '.join(
                    [self.arguments[a].lvalue for a in choose_one])])
        self._run(server_id=server_id)


class PersonalityArgument(KeyValueArgument):

    terms = (
        ('local-path', 'contents'),
        ('server-path', 'path'),
        ('owner', 'owner'),
        ('group', 'group'),
        ('mode', 'mode'))

    @property
    def value(self):
        return getattr(self, '_value', [])

    @value.setter
    def value(self, newvalue):
        if newvalue == self.default:
            return self.value
        self._value, input_dict = [], {}
        for i, terms in enumerate(newvalue):
            termlist = terms.split(',')
            if len(termlist) > len(self.terms):
                msg = 'Wrong number of terms (1<=terms<=%s)' % len(self.terms)
                raiseCLIError(CLISyntaxError(msg), details=howto_personality)

            for k, v in self.terms:
                prefix = '%s=' % k
                for item in termlist:
                    if item.lower().startswith(prefix):
                        input_dict[k] = item[len(k) + 1:]
                        break
                    item = None
                if item:
                    termlist.remove(item)

            try:
                path = input_dict['local-path']
            except KeyError:
                path = termlist.pop(0)
                if not path:
                    raise CLIInvalidArgument(
                        '--personality: No local path specified',
                        details=howto_personality)

            if not exists(path):
                raise CLIInvalidArgument(
                    '--personality: File %s does not exist' % path,
                    details=howto_personality)

            self._value.append(dict(path=path))
            with open(expanduser(path)) as f:
                self._value[i]['contents'] = b64encode(f.read())
            for k, v in self.terms[1:]:
                try:
                    self._value[i][v] = input_dict[k]
                except KeyError:
                    try:
                        self._value[i][v] = termlist.pop(0)
                    except IndexError:
                        continue
                if k in ('mode', ) and self._value[i][v]:
                    try:
                        self._value[i][v] = int(self._value[i][v], 8)
                    except ValueError as ve:
                        raise CLIInvalidArgument(
                            'Personality mode must be in octal', details=[
                                '%s' % ve])


class NetworkArgument(RepeatableArgument):
    """[id=]NETWORK_ID[,[ip=]IP]"""

    @property
    def value(self):
        return getattr(self, '_value', self.default)

    @value.setter
    def value(self, new_value):
        for v in new_value or []:
            part1, sep, part2 = v.partition(',')
            netid, ip = '', ''
            if part1.startswith('id='):
                netid = part1[len('id='):]
            elif part1.startswith('ip='):
                ip = part1[len('ip='):]
            else:
                netid = part1
            if part2:
                if (part2.startswith('id=') and netid) or (
                        part2.startswith('ip=') and ip):
                    raise CLIInvalidArgument(
                        'Invalid network argument %s' % v, details=[
                        'Valid format: [id=]NETWORK_ID[,[ip=]IP]'])
                if part2.startswith('id='):
                    netid = part2[len('id='):]
                elif part2.startswith('ip='):
                    ip = part2[len('ip='):]
                elif netid:
                    ip = part2
                else:
                    netid = part2
            if not netid:
                raise CLIInvalidArgument(
                    'Invalid network argument %s' % v, details=[
                    'Valid format: [id=]NETWORK_ID[,[ip=]IP]'])
            self._value = getattr(self, '_value', [])
            self._value.append(dict(uuid=netid))
            if ip:
                self._value[-1]['fixed_ip'] = ip


@command(server_cmds)
class server_create(_init_cyclades, _optional_json, _server_wait):
    """Create a server (aka Virtual Machine)"""

    arguments = dict(
        server_name=ValueArgument('The name of the new server', '--name'),
        flavor_id=IntArgument('The ID of the flavor', '--flavor-id'),
        image_id=ValueArgument('The ID of the image', '--image-id'),
        personality=PersonalityArgument(
            (80 * ' ').join(howto_personality), ('-p', '--personality')),
        wait=FlagArgument('Wait server to build', ('-w', '--wait')),
        cluster_size=IntArgument(
            'Create a cluster of servers of this size. In this case, the name'
            'parameter is the prefix of each server in the cluster (e.g.,'
            'srv1, srv2, etc.',
            '--cluster-size'),
        max_threads=IntArgument(
            'Max threads in cluster mode (default 1)', '--threads'),
        network_configuration=NetworkArgument(
            'Connect server to network: [id=]NETWORK_ID[,[ip=]IP]        . '
            'Use only NETWORK_ID for private networks.        . '
            'Use NETWORK_ID,[ip=]IP for networks with IP.        . '
            'Can be repeated, mutually exclussive with --no-network',
            '--network'),
        no_network=FlagArgument(
            'Do not create any network NICs on the server.        . '
            'Mutually exclusive to --network        . '
            'If neither --network or --no-network are used, the default '
            'network policy is applied. These policies are set on the cloud, '
            'so kamaki is oblivious to them',
            '--no-network')
    )
    required = ('server_name', 'flavor_id', 'image_id')

    @errors.cyclades.cluster_size
    def _create_cluster(self, prefix, flavor_id, image_id, size):
        networks = self['network_configuration'] or (
            [] if self['no_network'] else None)
        servers = [dict(
            name='%s%s' % (prefix, i if size > 1 else ''),
            flavor_id=flavor_id,
            image_id=image_id,
            personality=self['personality'],
            networks=networks) for i in range(1, 1 + size)]
        if size == 1:
            return [self.client.create_server(**servers[0])]
        self.client.MAX_THREADS = int(self['max_threads'] or 1)
        try:
            r = self.client.async_run(self.client.create_server, servers)
            return r
        except Exception as e:
            if size == 1:
                raise e
            try:
                requested_names = [s['name'] for s in servers]
                spawned_servers = [dict(
                    name=s['name'],
                    id=s['id']) for s in self.client.list_servers() if (
                        s['name'] in requested_names)]
                self.error('Failed to build %s servers' % size)
                self.error('Found %s matching servers:' % len(spawned_servers))
                self._print(spawned_servers, out=self._err)
                self.error('Check if any of these servers should be removed\n')
            except Exception as ne:
                self.error('Error (%s) while notifying about errors' % ne)
            finally:
                raise e

    @errors.generic.all
    @errors.cyclades.connection
    @errors.plankton.id
    @errors.cyclades.flavor_id
    def _run(self, name, flavor_id, image_id):
        for r in self._create_cluster(
                name, flavor_id, image_id, size=self['cluster_size'] or 1):
            if not r:
                self.error('Create %s: server response was %s' % (name, r))
                continue
            usernames = self._uuids2usernames(
                [r['user_id'], r['tenant_id']])
            r['user_id'] += ' (%s)' % usernames[r['user_id']]
            r['tenant_id'] += ' (%s)' % usernames[r['tenant_id']]
            self._print(r, self.print_dict)
            if self['wait']:
                self._wait(r['id'], r['status'])
            self.writeln(' ')

    def main(self):
        super(self.__class__, self)._run()
        if self['no_network'] and self['network_configuration']:
            raise CLIInvalidArgument(
                'Invalid argument compination', importance=2, details=[
                'Arguments %s and %s are mutually exclusive' % (
                    self.arguments['no_network'].lvalue,
                    self.arguments['network_configuration'].lvalue)])
        self._run(
            name=self['server_name'],
            flavor_id=self['flavor_id'],
            image_id=self['image_id'])


class FirewallProfileArgument(ValueArgument):

    profiles = ('DISABLED', 'ENABLED', 'PROTECTED')

    @property
    def value(self):
        return getattr(self, '_value', None)

    @value.setter
    def value(self, new_profile):
        if new_profile:
            new_profile = new_profile.upper()
            if new_profile in self.profiles:
                self._value = new_profile
            else:
                raise CLIInvalidArgument(
                    'Invalid firewall profile %s' % new_profile,
                    details=['Valid values: %s' % ', '.join(self.profiles)])


@command(server_cmds)
class server_modify(_init_cyclades, _optional_output_cmd):
    """Modify attributes of a virtual server"""

    arguments = dict(
        server_name=ValueArgument('The new name', '--name'),
        flavor_id=IntArgument('Set a different flavor', '--flavor-id'),
        firewall_profile=FirewallProfileArgument(
            'Valid values: %s' % (', '.join(FirewallProfileArgument.profiles)),
            '--firewall'),
        metadata_to_set=KeyValueArgument(
            'Set metadata in key=value form (can be repeated)',
            '--metadata-set'),
        metadata_to_delete=RepeatableArgument(
            'Delete metadata by key (can be repeated)', '--metadata-del')
    )
    required = [
        'server_name', 'flavor_id', 'firewall_profile', 'metadata_to_set',
        'metadata_to_delete']

    @errors.generic.all
    @errors.cyclades.connection
    @errors.cyclades.server_id
    def _run(self, server_id):
        if self['server_name']:
            self.client.update_server_name((server_id), self['server_name'])
        if self['flavor_id']:
            self.client.resize_server(server_id, self['flavor_id'])
        if self['firewall_profile']:
            self.client.set_firewall_profile(
                server_id=server_id, profile=self['firewall_profile'])
        if self['metadata_to_set']:
            self.client.update_server_metadata(
                server_id, **self['metadata_to_set'])
        for key in (self['metadata_to_delete'] or []):
            errors.cyclades.metadata(
                self.client.delete_server_metadata)(server_id, key=key)
        if self['with_output']:
            self._optional_output(self.client.get_server_details(server_id))

    def main(self, server_id):
        super(self.__class__, self)._run()
        self._run(server_id=server_id)


@command(server_cmds)
class server_delete(_init_cyclades, _optional_output_cmd, _server_wait):
    """Delete a virtual server"""

    arguments = dict(
        wait=FlagArgument('Wait server to be destroyed', ('-w', '--wait')),
        cluster=FlagArgument(
            '(DANGEROUS) Delete all virtual servers prefixed with the cluster '
            'prefix. In that case, the prefix replaces the server id',
            '--cluster')
    )

    def _server_ids(self, server_var):
        if self['cluster']:
            return [s['id'] for s in self.client.list_servers() if (
                s['name'].startswith(server_var))]

        @errors.cyclades.server_id
        def _check_server_id(self, server_id):
            return server_id

        return [_check_server_id(self, server_id=server_var), ]

    @errors.generic.all
    @errors.cyclades.connection
    def _run(self, server_var):
        for server_id in self._server_ids(server_var):
            if self['wait']:
                details = self.client.get_server_details(server_id)
                status = details['status']

            r = self.client.delete_server(server_id)
            self._optional_output(r)

            if self['wait']:
                self._wait(server_id, status)

    def main(self, server_id_or_cluster_prefix):
        super(self.__class__, self)._run()
        self._run(server_id_or_cluster_prefix)


@command(server_cmds)
class server_reboot(_init_cyclades, _optional_output_cmd, _server_wait):
    """Reboot a virtual server"""

    arguments = dict(
        hard=FlagArgument(
            'perform a hard reboot (deprecated)', ('-f', '--force')),
        type=ValueArgument('SOFT or HARD - default: SOFT', ('--type')),
        wait=FlagArgument('Wait server to be destroyed', ('-w', '--wait'))
    )

    @errors.generic.all
    @errors.cyclades.connection
    @errors.cyclades.server_id
    def _run(self, server_id):
        hard_reboot = self['hard']
        if hard_reboot:
            self.error(
                'WARNING: -f/--force will be deprecated in version 0.12\n'
                '\tIn the future, please use --type=hard instead')
        if self['type']:
            if self['type'].lower() in ('soft', ):
                hard_reboot = False
            elif self['type'].lower() in ('hard', ):
                hard_reboot = True
            else:
                raise CLISyntaxError(
                    'Invalid reboot type %s' % self['type'],
                    importance=2, details=[
                        '--type values are either SOFT (default) or HARD'])

        r = self.client.reboot_server(int(server_id), hard_reboot)
        self._optional_output(r)

        if self['wait']:
            self._wait(server_id, 'REBOOT')

    def main(self, server_id):
        super(self.__class__, self)._run()
        self._run(server_id=server_id)


@command(server_cmds)
class server_start(_init_cyclades, _optional_output_cmd, _server_wait):
    """Start an existing virtual server"""

    arguments = dict(
        wait=FlagArgument('Wait server to be destroyed', ('-w', '--wait'))
    )

    @errors.generic.all
    @errors.cyclades.connection
    @errors.cyclades.server_id
    def _run(self, server_id):
        status = 'ACTIVE'
        if self['wait']:
            details = self.client.get_server_details(server_id)
            status = details['status']
            if status in ('ACTIVE', ):
                return

        r = self.client.start_server(int(server_id))
        self._optional_output(r)

        if self['wait']:
            self._wait(server_id, status)

    def main(self, server_id):
        super(self.__class__, self)._run()
        self._run(server_id=server_id)


@command(server_cmds)
class server_shutdown(_init_cyclades, _optional_output_cmd, _server_wait):
    """Shutdown an active virtual server"""

    arguments = dict(
        wait=FlagArgument('Wait server to be destroyed', ('-w', '--wait'))
    )

    @errors.generic.all
    @errors.cyclades.connection
    @errors.cyclades.server_id
    def _run(self, server_id):
        status = 'STOPPED'
        if self['wait']:
            details = self.client.get_server_details(server_id)
            status = details['status']
            if status in ('STOPPED', ):
                return

        r = self.client.shutdown_server(int(server_id))
        self._optional_output(r)

        if self['wait']:
            self._wait(server_id, status)

    def main(self, server_id):
        super(self.__class__, self)._run()
        self._run(server_id=server_id)


@command(server_cmds)
class server_nics(_init_cyclades):
    """DEPRECATED, use: [kamaki] server info SERVER_ID --nics"""

    def main(self, *args):
        raiseCLIError('DEPRECATED since v0.12', importance=3, details=[
            'Replaced by',
            '  [kamaki] server info <SERVER_ID> --nics'])


@command(server_cmds)
class server_console(_init_cyclades, _optional_json):
    """Create a VMC console and show connection information"""

    @errors.generic.all
    @errors.cyclades.connection
    @errors.cyclades.server_id
    def _run(self, server_id):
        self.error('The following credentials will be invalidated shortly')
        self._print(
            self.client.get_server_console(server_id), self.print_dict)

    def main(self, server_id):
        super(self.__class__, self)._run()
        self._run(server_id=server_id)


@command(server_cmds)
class server_rename(_init_cyclades, _optional_json):
    """DEPRECATED, use: [kamaki] server modify SERVER_ID --name=NEW_NAME"""

    def main(self, *args):
        raiseCLIError('DEPRECATED since v0.12', importance=3, details=[
            'Replaced by',
            '  [kamaki] server modify <SERVER_ID> --name=NEW_NAME'])


@command(server_cmds)
class server_stats(_init_cyclades, _optional_json):
    """DEPRECATED, use: [kamaki] server info SERVER_ID --stats"""

    def main(self, *args):
        raiseCLIError('DEPRECATED since v0.12', importance=3, details=[
            'Replaced by',
            '  [kamaki] server info <SERVER_ID> --stats'])


@command(server_cmds)
class server_wait(_init_cyclades, _server_wait):
    """Wait for server to change its status (default: BUILD)"""

    arguments = dict(
        timeout=IntArgument(
            'Wait limit in seconds (default: 60)', '--timeout', default=60),
        server_status=StatusArgument(
            'Status to wait for (%s, default: %s)' % (
                ', '.join(server_states), server_states[0]),
            '--status',
            valid_states=server_states)
    )

    @errors.generic.all
    @errors.cyclades.connection
    @errors.cyclades.server_id
    def _run(self, server_id, current_status):
        r = self.client.get_server_details(server_id)
        if r['status'].lower() == current_status.lower():
            self._wait(server_id, current_status, timeout=self['timeout'])
        else:
            self.error(
                'Server %s: Cannot wait for status %s, '
                'status is already %s' % (
                    server_id, current_status, r['status']))

    def main(self, server_id):
        super(self.__class__, self)._run()
        self._run(
            server_id=server_id, current_status=self['server_status'] or '')


@command(flavor_cmds)
class flavor_list(_init_cyclades, _optional_json, _name_filter, _id_filter):
    """List available hardware flavors"""

    PERMANENTS = ('id', 'name')

    arguments = dict(
        detail=FlagArgument('show detailed output', ('-l', '--details')),
        limit=IntArgument('limit # of listed flavors', ('-n', '--number')),
        more=FlagArgument(
            'output results in pages (-n to set items per page, default 10)',
            '--more'),
        enum=FlagArgument('Enumerate results', '--enumerate'),
        ram=ValueArgument('filter by ram', ('--ram')),
        vcpus=ValueArgument('filter by number of VCPUs', ('--vcpus')),
        disk=ValueArgument('filter by disk size in GB', ('--disk')),
        disk_template=ValueArgument(
            'filter by disk_templace', ('--disk-template'))
    )

    def _apply_common_filters(self, flavors):
        common_filters = dict()
        if self['ram']:
            common_filters['ram'] = self['ram']
        if self['vcpus']:
            common_filters['vcpus'] = self['vcpus']
        if self['disk']:
            common_filters['disk'] = self['disk']
        if self['disk_template']:
            common_filters['SNF:disk_template'] = self['disk_template']
        return filter_dicts_by_dict(flavors, common_filters)

    @errors.generic.all
    @errors.cyclades.connection
    def _run(self):
        withcommons = self['ram'] or self['vcpus'] or (
            self['disk'] or self['disk_template'])
        detail = self['detail'] or withcommons
        flavors = self.client.list_flavors(detail)
        flavors = self._filter_by_name(flavors)
        flavors = self._filter_by_id(flavors)
        if withcommons:
            flavors = self._apply_common_filters(flavors)
        if not (self['detail'] or (
                self['json_output'] or self['output_format'])):
            remove_from_items(flavors, 'links')
        if detail and not self['detail']:
            for flv in flavors:
                for key in set(flv).difference(self.PERMANENTS):
                    flv.pop(key)
        kwargs = dict(out=StringIO(), title=()) if self['more'] else {}
        self._print(
            flavors,
            with_redundancy=self['detail'], with_enumeration=self['enum'],
            **kwargs)
        if self['more']:
            pager(kwargs['out'].getvalue())

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(flavor_cmds)
class flavor_info(_init_cyclades, _optional_json):
    """Detailed information on a hardware flavor
    To get a list of available flavors and flavor ids, try /flavor list
    """

    @errors.generic.all
    @errors.cyclades.connection
    @errors.cyclades.flavor_id
    def _run(self, flavor_id):
        self._print(
            self.client.get_flavor_details(int(flavor_id)), self.print_dict)

    def main(self, flavor_id):
        super(self.__class__, self)._run()
        self._run(flavor_id=flavor_id)


def _add_name(self, net):
        user_id, tenant_id, uuids = net['user_id'], net['tenant_id'], []
        if user_id:
            uuids.append(user_id)
        if tenant_id:
            uuids.append(tenant_id)
        if uuids:
            usernames = self._uuids2usernames(uuids)
            if user_id:
                net['user_id'] += ' (%s)' % usernames[user_id]
            if tenant_id:
                net['tenant_id'] += ' (%s)' % usernames[tenant_id]
