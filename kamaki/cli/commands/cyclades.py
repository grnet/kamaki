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
from kamaki.clients.cyclades import CycladesClient, ClientError
from kamaki.cli.argument import FlagArgument, ValueArgument, KeyValueArgument
from kamaki.cli.argument import ProgressBarArgument, DateArgument, IntArgument
from kamaki.cli.commands import _command_init, errors, addLogSettings
from kamaki.cli.commands import (
    _optional_output_cmd, _optional_json, _name_filter, _id_filter)


server_cmds = CommandTree('server', 'Cyclades/Compute API server commands')
flavor_cmds = CommandTree('flavor', 'Cyclades/Compute API flavor commands')
network_cmds = CommandTree('network', 'Cyclades/Compute API network commands')
ip_cmds = CommandTree('ip', 'Cyclades/Compute API floating ip commands')
_commands = [server_cmds, flavor_cmds, network_cmds, ip_cmds]


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


class _network_wait(_service_wait):

    def _wait(self, net_id, current_status, timeout=60):
        super(_network_wait, self)._wait(
            'Network', net_id, self.client.wait_network, current_status,
            timeout=timeout)


class _firewall_wait(_service_wait):

    def _wait(self, server_id, current_status, timeout=60):
        super(_firewall_wait, self)._wait(
            'Firewall of server',
            server_id, self.client.wait_firewall, current_status,
            timeout=timeout)


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
    """Detailed information on a Virtual Machine
    Contains:
    - name, id, status, create/update dates
    - network interfaces
    - metadata (e.g., os, superuser) and diagnostics
    - hardware flavor and os image ids
    """

    @errors.generic.all
    @errors.cyclades.connection
    @errors.cyclades.server_id
    def _run(self, server_id):
        vm = self.client.get_server_details(server_id)
        uuids = self._uuids2usernames([vm['user_id'], vm['tenant_id']])
        vm['user_id'] += ' (%s)' % uuids[vm['user_id']]
        vm['tenant_id'] += ' (%s)' % uuids[vm['tenant_id']]
        self._print(vm, self.print_dict)

    def main(self, server_id):
        super(self.__class__, self)._run()
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


@command(server_cmds)
class server_create(_init_cyclades, _optional_json, _server_wait):
    """Create a server (aka Virtual Machine)
    Parameters:
    - name: (single quoted text)
    - flavor id: Hardware flavor. Pick one from: /flavor list
    - image id: OS images. Pick one from: /image list
    """

    arguments = dict(
        personality=PersonalityArgument(
            (80 * ' ').join(howto_personality), ('-p', '--personality')),
        wait=FlagArgument('Wait server to build', ('-w', '--wait')),
        cluster_size=IntArgument(
            'Create a cluster of servers of this size. In this case, the name'
            'parameter is the prefix of each server in the cluster (e.g.,'
            'srv1, srv2, etc.',
            '--cluster-size')
    )

    @errors.cyclades.cluster_size
    def _create_cluster(self, prefix, flavor_id, image_id, size):
        servers = [dict(
            name='%s%s' % (prefix, i if size > 1 else ''),
            flavor_id=flavor_id,
            image_id=image_id,
            personality=self['personality']) for i in range(1, 1 + size)]
        if size == 1:
            return [self.client.create_server(**servers[0])]
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

    def main(self, name, flavor_id, image_id):
        super(self.__class__, self)._run()
        self._run(name=name, flavor_id=flavor_id, image_id=image_id)


@command(server_cmds)
class server_rename(_init_cyclades, _optional_output_cmd):
    """Set/update a virtual server name
    virtual server names are not unique, therefore multiple servers may share
    the same name
    """

    @errors.generic.all
    @errors.cyclades.connection
    @errors.cyclades.server_id
    def _run(self, server_id, new_name):
        self._optional_output(
            self.client.update_server_name(int(server_id), new_name))

    def main(self, server_id, new_name):
        super(self.__class__, self)._run()
        self._run(server_id=server_id, new_name=new_name)


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
class server_console(_init_cyclades, _optional_json):
    """Get a VNC console to access an existing virtual server
    Console connection information provided (at least):
    - host: (url or address) a VNC host
    - port: (int) the gateway to enter virtual server on host
    - password: for VNC authorization
    """

    @errors.generic.all
    @errors.cyclades.connection
    @errors.cyclades.server_id
    def _run(self, server_id):
        self._print(
            self.client.get_server_console(int(server_id)), self.print_dict)

    def main(self, server_id):
        super(self.__class__, self)._run()
        self._run(server_id=server_id)


@command(server_cmds)
class server_resize(_init_cyclades, _optional_output_cmd):
    """Set a different flavor for an existing server
    To get server ids and flavor ids:
    /server list
    /flavor list
    """

    @errors.generic.all
    @errors.cyclades.connection
    @errors.cyclades.server_id
    @errors.cyclades.flavor_id
    def _run(self, server_id, flavor_id):
        self._optional_output(self.client.resize_server(server_id, flavor_id))

    def main(self, server_id, flavor_id):
        super(self.__class__, self)._run()
        self._run(server_id=server_id, flavor_id=flavor_id)


@command(server_cmds)
class server_firewall(_init_cyclades):
    """Manage virtual server firewall profiles for public networks"""


@command(server_cmds)
class server_firewall_set(
        _init_cyclades, _optional_output_cmd, _firewall_wait):
    """Set the firewall profile on virtual server public network
    Values for profile:
    - DISABLED: Shutdown firewall
    - ENABLED: Firewall in normal mode
    - PROTECTED: Firewall in secure mode
    """

    arguments = dict(
        wait=FlagArgument('Wait server firewall to build', ('-w', '--wait')),
        timeout=IntArgument(
            'Set wait timeout in seconds (default: 60)', '--timeout',
            default=60)
    )

    @errors.generic.all
    @errors.cyclades.connection
    @errors.cyclades.server_id
    @errors.cyclades.firewall
    def _run(self, server_id, profile):
        if self['timeout'] and not self['wait']:
            raise CLIInvalidArgument('Invalid use of --timeout', details=[
                'Timeout is used only along with -w/--wait'])
        old_profile = self.client.get_firewall_profile(server_id)
        if old_profile.lower() == profile.lower():
            self.error('Firewall of server %s: allready in status %s' % (
                server_id, old_profile))
        else:
            self._optional_output(self.client.set_firewall_profile(
                server_id=int(server_id), profile=('%s' % profile).upper()))
            if self['wait']:
                self._wait(server_id, old_profile, timeout=self['timeout'])

    def main(self, server_id, profile):
        super(self.__class__, self)._run()
        self._run(server_id=server_id, profile=profile)


@command(server_cmds)
class server_firewall_get(_init_cyclades):
    """Get the firewall profile for a virtual servers' public network"""

    @errors.generic.all
    @errors.cyclades.connection
    @errors.cyclades.server_id
    def _run(self, server_id):
        self.writeln(self.client.get_firewall_profile(server_id))

    def main(self, server_id):
        super(self.__class__, self)._run()
        self._run(server_id=server_id)


@command(server_cmds)
class server_addr(_init_cyclades, _optional_json):
    """List the addresses of all network interfaces on a virtual server"""

    arguments = dict(
        enum=FlagArgument('Enumerate results', '--enumerate')
    )

    @errors.generic.all
    @errors.cyclades.connection
    @errors.cyclades.server_id
    def _run(self, server_id):
        reply = self.client.list_server_nics(int(server_id))
        self._print(reply, with_enumeration=self['enum'] and (reply) > 1)

    def main(self, server_id):
        super(self.__class__, self)._run()
        self._run(server_id=server_id)


@command(server_cmds)
class server_metadata(_init_cyclades):
    """Manage Server metadata (key:value pairs of server attributes)"""


@command(server_cmds)
class server_metadata_list(_init_cyclades, _optional_json):
    """Get server metadata"""

    @errors.generic.all
    @errors.cyclades.connection
    @errors.cyclades.server_id
    @errors.cyclades.metadata
    def _run(self, server_id, key=''):
        self._print(
            self.client.get_server_metadata(int(server_id), key),
            self.print_dict)

    def main(self, server_id, key=''):
        super(self.__class__, self)._run()
        self._run(server_id=server_id, key=key)


@command(server_cmds)
class server_metadata_set(_init_cyclades, _optional_json):
    """Set / update virtual server metadata
    Metadata should be given in key/value pairs in key=value format
    For example: /server metadata set <server id> key1=value1 key2=value2
    Old, unreferenced metadata will remain intact
    """

    @errors.generic.all
    @errors.cyclades.connection
    @errors.cyclades.server_id
    def _run(self, server_id, keyvals):
        assert keyvals, 'Please, add some metadata ( key=value)'
        metadata = dict()
        for keyval in keyvals:
            k, sep, v = keyval.partition('=')
            if sep and k:
                metadata[k] = v
            else:
                raiseCLIError(
                    'Invalid piece of metadata %s' % keyval,
                    importance=2, details=[
                        'Correct metadata format: key=val',
                        'For example:',
                        '/server metadata set <server id>'
                        'key1=value1 key2=value2'])
        self._print(
            self.client.update_server_metadata(int(server_id), **metadata),
            self.print_dict)

    def main(self, server_id, *key_equals_val):
        super(self.__class__, self)._run()
        self._run(server_id=server_id, keyvals=key_equals_val)


@command(server_cmds)
class server_metadata_delete(_init_cyclades, _optional_output_cmd):
    """Delete virtual server metadata"""

    @errors.generic.all
    @errors.cyclades.connection
    @errors.cyclades.server_id
    @errors.cyclades.metadata
    def _run(self, server_id, key):
        self._optional_output(
            self.client.delete_server_metadata(int(server_id), key))

    def main(self, server_id, key):
        super(self.__class__, self)._run()
        self._run(server_id=server_id, key=key)


@command(server_cmds)
class server_stats(_init_cyclades, _optional_json):
    """Get virtual server statistics"""

    @errors.generic.all
    @errors.cyclades.connection
    @errors.cyclades.server_id
    def _run(self, server_id):
        self._print(
            self.client.get_server_stats(int(server_id)), self.print_dict)

    def main(self, server_id):
        super(self.__class__, self)._run()
        self._run(server_id=server_id)


@command(server_cmds)
class server_wait(_init_cyclades, _server_wait):
    """Wait for server to finish [BUILD, STOPPED, REBOOT, ACTIVE]"""

    arguments = dict(
        timeout=IntArgument(
            'Wait limit in seconds (default: 60)', '--timeout', default=60)
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

    def main(self, server_id, current_status='BUILD'):
        super(self.__class__, self)._run()
        self._run(server_id=server_id, current_status=current_status)


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


@command(network_cmds)
class network_info(_init_cyclades, _optional_json):
    """Detailed information on a network
    To get a list of available networks and network ids, try /network list
    """

    @errors.generic.all
    @errors.cyclades.connection
    @errors.cyclades.network_id
    def _run(self, network_id):
        network = self.client.get_network_details(int(network_id))
        _add_name(self, network)
        self._print(network, self.print_dict, exclude=('id'))

    def main(self, network_id):
        super(self.__class__, self)._run()
        self._run(network_id=network_id)


@command(network_cmds)
class network_list(_init_cyclades, _optional_json, _name_filter, _id_filter):
    """List networks"""

    PERMANENTS = ('id', 'name')

    arguments = dict(
        detail=FlagArgument('show detailed output', ('-l', '--details')),
        limit=IntArgument('limit # of listed networks', ('-n', '--number')),
        more=FlagArgument(
            'output results in pages (-n to set items per page, default 10)',
            '--more'),
        enum=FlagArgument('Enumerate results', '--enumerate'),
        status=ValueArgument('filter by status', ('--status')),
        public=FlagArgument('only public networks', ('--public')),
        private=FlagArgument('only private networks', ('--private')),
        dhcp=FlagArgument('show networks with dhcp', ('--with-dhcp')),
        no_dhcp=FlagArgument('show networks without dhcp', ('--without-dhcp')),
        user_id=ValueArgument('filter by user id', ('--user-id')),
        user_name=ValueArgument('filter by user name', ('--user-name')),
        gateway=ValueArgument('filter by gateway (IPv4)', ('--gateway')),
        gateway6=ValueArgument('filter by gateway (IPv6)', ('--gateway6')),
        cidr=ValueArgument('filter by cidr (IPv4)', ('--cidr')),
        cidr6=ValueArgument('filter by cidr (IPv6)', ('--cidr6')),
        type=ValueArgument('filter by type', ('--type')),
    )

    def _apply_common_filters(self, networks):
        common_filter = dict()
        if self['public']:
            if self['private']:
                return []
            common_filter['public'] = self['public']
        elif self['private']:
            common_filter['public'] = False
        if self['dhcp']:
            if self['no_dhcp']:
                return []
            common_filter['dhcp'] = True
        elif self['no_dhcp']:
            common_filter['dhcp'] = False
        if self['user_id'] or self['user_name']:
            uuid = self['user_id'] or self._username2uuid(self['user_name'])
            common_filter['user_id'] = uuid
        for term in ('status', 'gateway', 'gateway6', 'cidr', 'cidr6', 'type'):
            if self[term]:
                common_filter[term] = self[term]
        return filter_dicts_by_dict(networks, common_filter)

    def _add_name(self, networks, key='user_id'):
        uuids = self._uuids2usernames(
            list(set([net[key] for net in networks])))
        for net in networks:
            v = net.get(key, None)
            if v:
                net[key] += ' (%s)' % uuids[v]
        return networks

    @errors.generic.all
    @errors.cyclades.connection
    def _run(self):
        withcommons = False
        for term in (
                'status', 'public', 'private', 'user_id', 'user_name', 'type',
                'gateway', 'gateway6', 'cidr', 'cidr6', 'dhcp', 'no_dhcp'):
            if self[term]:
                withcommons = True
                break
        detail = self['detail'] or withcommons
        networks = self.client.list_networks(detail)
        networks = self._filter_by_name(networks)
        networks = self._filter_by_id(networks)
        if withcommons:
            networks = self._apply_common_filters(networks)
        if not (self['detail'] or (
                self['json_output'] or self['output_format'])):
            remove_from_items(networks, 'links')
        if detail and not self['detail']:
            for net in networks:
                for key in set(net).difference(self.PERMANENTS):
                    net.pop(key)
        if self['detail'] and not (
                self['json_output'] or self['output_format']):
            self._add_name(networks)
            self._add_name(networks, 'tenant_id')
        kwargs = dict(with_enumeration=self['enum'])
        if self['more']:
            kwargs['out'] = StringIO()
            kwargs['title'] = ()
        if self['limit']:
            networks = networks[:self['limit']]
        self._print(networks, **kwargs)
        if self['more']:
            pager(kwargs['out'].getvalue())

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(network_cmds)
class network_create(_init_cyclades, _optional_json, _network_wait):
    """Create an (unconnected) network"""

    arguments = dict(
        cidr=ValueArgument('explicitly set cidr', '--with-cidr'),
        gateway=ValueArgument('explicitly set gateway', '--with-gateway'),
        dhcp=FlagArgument('Use dhcp (default: off)', '--with-dhcp'),
        type=ValueArgument(
            'Valid network types are '
            'CUSTOM, IP_LESS_ROUTED, MAC_FILTERED (default), PHYSICAL_VLAN',
            '--with-type',
            default='MAC_FILTERED'),
        wait=FlagArgument('Wait network to build', ('-w', '--wait'))
    )

    @errors.generic.all
    @errors.cyclades.connection
    @errors.cyclades.network_max
    def _run(self, name):
        r = self.client.create_network(
            name,
            cidr=self['cidr'],
            gateway=self['gateway'],
            dhcp=self['dhcp'],
            type=self['type'])
        _add_name(self, r)
        self._print(r, self.print_dict)
        if self['wait'] and r['status'] in ('PENDING', ):
            self._wait(r['id'], 'PENDING')

    def main(self, name):
        super(self.__class__, self)._run()
        self._run(name)


@command(network_cmds)
class network_rename(_init_cyclades, _optional_output_cmd):
    """Set the name of a network"""

    @errors.generic.all
    @errors.cyclades.connection
    @errors.cyclades.network_id
    def _run(self, network_id, new_name):
        self._optional_output(
                self.client.update_network_name(int(network_id), new_name))

    def main(self, network_id, new_name):
        super(self.__class__, self)._run()
        self._run(network_id=network_id, new_name=new_name)


@command(network_cmds)
class network_delete(_init_cyclades, _optional_output_cmd, _network_wait):
    """Delete a network"""

    arguments = dict(
        wait=FlagArgument('Wait network to build', ('-w', '--wait'))
    )

    @errors.generic.all
    @errors.cyclades.connection
    @errors.cyclades.network_in_use
    @errors.cyclades.network_id
    def _run(self, network_id):
        status = 'DELETED'
        if self['wait']:
            r = self.client.get_network_details(network_id)
            status = r['status']
            if status in ('DELETED', ):
                return

        r = self.client.delete_network(int(network_id))
        self._optional_output(r)

        if self['wait']:
            self._wait(network_id, status)

    def main(self, network_id):
        super(self.__class__, self)._run()
        self._run(network_id=network_id)


@command(network_cmds)
class network_connect(_init_cyclades, _optional_output_cmd):
    """Connect a server to a network"""

    @errors.generic.all
    @errors.cyclades.connection
    @errors.cyclades.server_id
    @errors.cyclades.network_id
    def _run(self, server_id, network_id):
        self._optional_output(
                self.client.connect_server(int(server_id), int(network_id)))

    def main(self, server_id, network_id):
        super(self.__class__, self)._run()
        self._run(server_id=server_id, network_id=network_id)


@command(network_cmds)
class network_disconnect(_init_cyclades):
    """Disconnect a nic that connects a server to a network
    Nic ids are listed as "attachments" in detailed network information
    To get detailed network information: /network info <network id>
    """

    @errors.cyclades.nic_format
    def _server_id_from_nic(self, nic_id):
        return nic_id.split('-')[1]

    @errors.generic.all
    @errors.cyclades.connection
    @errors.cyclades.server_id
    @errors.cyclades.nic_id
    def _run(self, nic_id, server_id):
        num_of_disconnected = self.client.disconnect_server(server_id, nic_id)
        if not num_of_disconnected:
            raise ClientError(
                'Network Interface %s not found on server %s' % (
                    nic_id, server_id),
                status=404)
        print('Disconnected %s connections' % num_of_disconnected)

    def main(self, nic_id):
        super(self.__class__, self)._run()
        server_id = self._server_id_from_nic(nic_id=nic_id)
        self._run(nic_id=nic_id, server_id=server_id)


@command(network_cmds)
class network_wait(_init_cyclades, _network_wait):
    """Wait for server to finish [PENDING, ACTIVE, DELETED]"""

    arguments = dict(
        timeout=IntArgument(
            'Wait limit in seconds (default: 60)', '--timeout', default=60)
    )

    @errors.generic.all
    @errors.cyclades.connection
    @errors.cyclades.network_id
    def _run(self, network_id, current_status):
        net = self.client.get_network_details(network_id)
        if net['status'].lower() == current_status.lower():
            self._wait(network_id, current_status, timeout=self['timeout'])
        else:
            self.error(
                'Network %s: Cannot wait for status %s, '
                'status is already %s' % (
                    network_id, current_status, net['status']))

    def main(self, network_id, current_status='PENDING'):
        super(self.__class__, self)._run()
        self._run(network_id=network_id, current_status=current_status)


@command(ip_cmds)
class ip_pools(_init_cyclades, _optional_json):
    """List pools of floating IPs"""

    @errors.generic.all
    @errors.cyclades.connection
    def _run(self):
        r = self.client.get_floating_ip_pools()
        self._print(r if self['json_output'] or self['output_format'] else r[
            'floating_ip_pools'])

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(ip_cmds)
class ip_list(_init_cyclades, _optional_json):
    """List reserved floating IPs"""

    @errors.generic.all
    @errors.cyclades.connection
    def _run(self):
        r = self.client.get_floating_ips()
        self._print(r if self['json_output'] or self['output_format'] else r[
            'floating_ips'])

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(ip_cmds)
class ip_info(_init_cyclades, _optional_json):
    """Details for an IP"""

    @errors.generic.all
    @errors.cyclades.connection
    def _run(self, ip):
        self._print(self.client.get_floating_ip(ip), self.print_dict)

    def main(self, IP):
        super(self.__class__, self)._run()
        self._run(ip=IP)


@command(ip_cmds)
class ip_reserve(_init_cyclades, _optional_json):
    """Reserve a floating IP
    An IP is reserved from an IP pool. The default IP pool is chosen
    automatically, but there is the option if specifying an explicit IP pool.
    """

    arguments = dict(pool=ValueArgument('Source IP pool', ('--pool'), None))

    @errors.generic.all
    @errors.cyclades.connection
    def _run(self, ip=None):
        self._print([self.client.alloc_floating_ip(self['pool'], ip)])

    def main(self, requested_IP=None):
        super(self.__class__, self)._run()
        self._run(ip=requested_IP)


@command(ip_cmds)
class ip_release(_init_cyclades, _optional_output_cmd):
    """Release a floating IP
    The release IP is "returned" to the IP pool it came from.
    """

    @errors.generic.all
    @errors.cyclades.connection
    def _run(self, ip):
        self._optional_output(self.client.delete_floating_ip(ip))

    def main(self, IP):
        super(self.__class__, self)._run()
        self._run(ip=IP)


@command(ip_cmds)
class ip_attach(_init_cyclades, _optional_output_cmd):
    """Attach a floating IP to a server
    """

    @errors.generic.all
    @errors.cyclades.connection
    @errors.cyclades.server_id
    def _run(self, server_id, ip):
        self._optional_output(self.client.attach_floating_ip(server_id, ip))

    def main(self, server_id, IP):
        super(self.__class__, self)._run()
        self._run(server_id=server_id, ip=IP)


@command(ip_cmds)
class ip_detach(_init_cyclades, _optional_output_cmd):
    """Detach a floating IP from a server
    """

    @errors.generic.all
    @errors.cyclades.connection
    @errors.cyclades.server_id
    def _run(self, server_id, ip):
        self._optional_output(self.client.detach_floating_ip(server_id, ip))

    def main(self, server_id, IP):
        super(self.__class__, self)._run()
        self._run(server_id=server_id, ip=IP)
