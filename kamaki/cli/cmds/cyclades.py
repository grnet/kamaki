# Copyright 2011-2015 GRNET S.A. All rights reserved.
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
import cStringIO
import codecs
from base64 import b64encode
from os.path import exists, expanduser
from io import StringIO
from pydoc import pager

from kamaki.cli import command
from kamaki.cli.cmdtree import CommandTree
from kamaki.cli.utils import remove_from_items, filter_dicts_by_dict
from kamaki.cli.errors import raiseCLIError, CLISyntaxError, CLIInvalidArgument
from kamaki.clients.cyclades import (
    CycladesComputeClient, ClientError, CycladesNetworkClient)
from kamaki.cli.argument import (
    FlagArgument, ValueArgument, KeyValueArgument, RepeatableArgument,
    DateArgument, IntArgument, StatusArgument)
from kamaki.cli.cmds import (
    CommandInit, fall_back, OptionalOutput, NameFilter, IDFilter, Wait, errors,
    client_log)


server_cmds = CommandTree('server', 'Cyclades/Compute API server commands')
flavor_cmds = CommandTree('flavor', 'Cyclades/Compute API flavor commands')
namespaces = [server_cmds, flavor_cmds]

howto_personality = [
    'Defines a file to be injected to virtual servers file system.',
    'syntax:  PATH,[SERVER_PATH,[OWNER,[GROUP,[MODE]]]]',
    '  [local-path=]PATH: local file to be injected (relative or absolute)',
    '  [server-path=]SERVER_PATH: destination location inside server Image',
    '  [owner=]OWNER: virtual servers user id for the remote file',
    '  [group=]GROUP: virtual servers group id or name for the remote file',
    '  [mode=]MODE: permission in octal (e.g., 0777)',
    'e.g., -p /tmp/my.file,owner=root,mode=0777']

server_states = ('BUILD', 'ACTIVE', 'STOPPED', 'REBOOT', 'ERROR')


class _ServerWait(Wait):

    def wait_while(self, server_id, current_status, timeout=60):
        if current_status in ('BUILD', ):

            def update_cb(item_details):
                return item_details.get('progress', None)
        else:
            update_cb = None

        super(_ServerWait, self).wait(
            'Server', server_id, self.client.wait_server_while, current_status,
            countdown=(current_status not in ('BUILD', )),
            timeout=timeout, update_cb=update_cb)

    def wait_until(self, server_id, target_status, timeout=60):
        super(_ServerWait, self).wait(
            'Server', server_id, self.client.wait_server_until, target_status,
            timeout=timeout, msg='not yet')

    def assert_not_in_status(self, server_id, status):
        """
        :returns: current server status
        :raises CLIError: if server is already in this status
        :raises ClientError: (404) if server not found
        """
        current = self.client.get_server_details(server_id).get('status', None)
        if current in (status, ):
            raiseCLIError('Server %s is already %s' % (server_id, status))
        return current


class _CycladesInit(CommandInit):
    @errors.Generic.all
    @client_log
    def _run(self):
        self.client = self.get_client(CycladesComputeClient, 'cyclades')

    @errors.Cyclades.flavor_id
    def _flavor_exists(self, flavor_id):
        self.client.get_flavor_details(flavor_id=flavor_id)

    @errors.Cyclades.server_id
    def _server_exists(self, server_id):
        self.client.get_server_details(server_id=server_id)

    @fall_back
    def _restruct_server_info(self, vm):
        if not vm:
            return vm
        img = vm['image']
        try:
            img.pop('links', None)
            img['name'] = self.client.get_image_details(img['id'])['name']
        except Exception:
            pass
        flv = vm['flavor']
        try:
            flv.pop('links', None)
            flv['name'] = self.client.get_flavor_details(flv['id'])['name']
        except Exception:
            pass
        vm['ports'] = vm.pop('attachments', dict())
        for port in vm['ports']:
            netid = port.get('network_id')
            for k in vm['addresses'].get(netid, []):
                k.pop('addr', None)
                k.pop('version', None)
                port.update(k)
        uuids = self._uuids2usernames([vm['user_id'], vm['tenant_id']])
        vm['user_id'] += ' (%s)' % uuids[vm['user_id']]
        for key in ('addresses', 'tenant_id', 'links'):
            vm.pop(key, None)
        return vm

    def main(self):
        self._run()


@command(server_cmds)
class server_list(_CycladesInit, OptionalOutput, NameFilter, IDFilter):
    """List virtual servers accessible by user
    Use filtering arguments (e.g., --name-like) to manage long server lists
    """

    arguments = dict(
        detail=FlagArgument('show detailed output', ('-l', '--details')),
        since=DateArgument(
            'show only items modified since date (\'H:M:S YYYY-mm-dd\') '
            'Can look back up to a limit (POLL_TIME) defined on service-side',
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
            [srv['user_id'] for srv in servers])))
        for srv in servers:
            srv['user_id'] += ' (%s)' % uuids[srv['user_id']]
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
            '%s' % srv['flavor']['id'] == '%s' % fid)]

    def _filter_by_metadata(self, servers):
        new_servers = []
        for srv in servers:
            if 'metadata' not in srv:
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

    @errors.Generic.all
    @errors.Cyclades.connection
    @errors.Cyclades.date
    def _run(self):
        withimage = bool(self['image_id'])
        withflavor = bool(self['flavor_id'])
        withmeta = bool(self['meta'] or self['meta_like'])
        withcommons = bool(
            self['status'] or self['user_id'] or self['user_name'])
        detail = self['detail'] or (
            withimage or withflavor or withmeta or withcommons)
        ch_since = self.arguments['since'].isoformat if self['since'] else None
        servers = list(self.client.list_servers(detail, ch_since) or [])

        servers = self._filter_by_name(servers)
        servers = self._filter_by_id(servers)
        servers = self._apply_common_filters(servers)
        if withimage:
            servers = self._filter_by_image(servers)
        if withflavor:
            servers = self._filter_by_flavor(servers)
        if withmeta:
            servers = self._filter_by_metadata(servers)

        if detail and self['detail']:
            pass
        else:
            for srv in servers:
                for key in set(srv).difference(['id', 'name']):
                    srv.pop(key)

        kwargs = dict(with_enumeration=self['enum'])
        if self['more']:
            codecinfo = codecs.lookup('utf-8')
            kwargs['out'] = codecs.StreamReaderWriter(
                cStringIO.StringIO(),
                codecinfo.streamreader,
                codecinfo.streamwriter)
            kwargs['title'] = ()
        if self['limit']:
            servers = servers[:self['limit']]
        self.print_(servers, **kwargs)
        if self['more']:
            pager(kwargs['out'].getvalue())

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(server_cmds)
class server_info(_CycladesInit, OptionalOutput):
    """Detailed information on a Virtual Machine"""

    arguments = dict(
        nics=FlagArgument(
            'Show only the network interfaces of this virtual server',
            '--nics'),
        stats=FlagArgument('Get URLs for server statistics', '--stats'),
        diagnostics=FlagArgument('Diagnostic information', '--diagnostics')
    )

    @errors.Generic.all
    @errors.Cyclades.connection
    @errors.Cyclades.server_id
    def _run(self, server_id):
        if self['nics']:
            self.print_(
                self.client.get_server_nics(server_id), self.print_dict)
        elif self['stats']:
            self.print_(
                self.client.get_server_stats(server_id), self.print_dict)
        elif self['diagnostics']:
            self.print_(self.client.get_server_diagnostics(server_id))
        else:
            vm = self.client.get_server_details(server_id)
            self.print_(vm, self.print_dict)

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
                        'Invalid network argument %s' % v,
                        details=['Valid format: [id=]NETWORK_ID[,[ip=]IP]'])
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
                    'Invalid network argument %s' % v,
                    details=['Valid format: [id=]NETWORK_ID[,[ip=]IP]'])
            self._value = getattr(self, '_value', [])
            self._value.append(dict(uuid=netid))
            if ip:
                self._value[-1]['fixed_ip'] = ip


@command(server_cmds)
class server_create(_CycladesInit, OptionalOutput, _ServerWait):
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
            '--no-network'),
        project_id=ValueArgument('Assign server to project', '--project-id'),
        metadata=KeyValueArgument(
            'Add custom metadata in key=value form (can be repeated). '
            'Overwrites metadata defined otherwise (i.e., image).',
            ('-m', '--metadata'))
    )
    required = ('server_name', 'flavor_id', 'image_id')

    @errors.Cyclades.cluster_size
    def _create_cluster(self, prefix, flavor_id, image_id, size):
        networks = self['network_configuration'] or (
            [] if self['no_network'] else None)
        servers = [dict(
            name='%s%s' % (prefix, i if size > 1 else ''),
            flavor_id=flavor_id,
            image_id=image_id,
            project_id=self['project_id'],
            personality=self['personality'],
            metadata=self['metadata'],
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
                self.print_(spawned_servers, out=self._err)
                self.error('Check if any of these servers should be removed')
            except Exception as ne:
                self.error('Error (%s) while notifying about errors' % ne)
            finally:
                raise e

    def _get_network_client(self):
        network = getattr(self, '_network_client', None)
        if not network:
            net_URL = self.astakos.get_endpoint_url(
                CycladesNetworkClient.service_type)
            network = CycladesNetworkClient(net_URL, self.client.token)
            self._network_client = network
        return network

    @errors.Image.id
    def _image_exists(self, image_id):
        self.client.get_image_details(image_id)

    @errors.Cyclades.network_id
    def _network_exists(self, network_id):
        network = self._get_network_client()
        network.get_network_details(network_id)

    def _ip_ready(self, ip, network_id, cerror):
        network = self._get_network_client()
        ips = [fip for fip in network.list_floatingips() if (
            fip['floating_ip_address'] == ip)]
        if not ips:
            msg = 'IP %s not available for current user' % ip
            raiseCLIError(cerror, details=[msg] + errors.Cyclades.about_ips)
        ipnet, ipvm = ips[0]['floating_network_id'], ips[0]['instance_id']
        if getattr(cerror, 'status', 0) in (409, ):
            msg = ''
            if ipnet != network_id:
                msg = 'IP %s belong to network %s, not %s' % (
                    ip, ipnet, network_id)
            elif ipvm:
                msg = 'IP %s is already used by device %s' % (ip, ipvm)
            if msg:
                raiseCLIError(cerror, details=[
                    msg,
                    'To get details on IP',
                    '  kamaki ip info %s' % ip] + errors.Cyclades.about_ips)

    @errors.Generic.all
    @errors.Cyclades.connection
    def _run(self):
        try:
            for r in self._create_cluster(
                    self['server_name'], self['flavor_id'], self['image_id'],
                    size=self['cluster_size'] or 1):
                if not r:
                    self.error('Create %s: server response was %s' % (
                        self['server_name'], r))
                    continue
                self.print_(r, self.print_dict)
                if self['wait']:
                    self.wait_while(r['id'], r['status'] or 'BUILD')
                self.writeln(' ')
        except ClientError as ce:
            if ce.status in (404, 400):
                self._flavor_exists(flavor_id=self['flavor_id'])
                self._image_exists(image_id=self['image_id'])
            if ce.status in (404, 400, 409):
                for net in self['network_configuration'] or []:
                    self._network_exists(network_id=net['uuid'])
                    if 'fixed_ip' in net:
                        self._ip_ready(net['fixed_ip'], net['uuid'], ce)
            if self['project_id'] and ce.status in (400, 403, 404):
                self._project_id_exists(project_id=self['project_id'])
            raise

    def main(self):
        super(self.__class__, self)._run()
        if self['no_network'] and self['network_configuration']:
            raise CLIInvalidArgument(
                'Invalid argument combination', importance=2, details=[
                    'Arguments %s and %s are mutually exclusive' % (
                        self.arguments['no_network'].lvalue,
                        self.arguments['network_configuration'].lvalue)])
        self._run()


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
class server_modify(_CycladesInit):
    """Modify attributes of a virtual server"""

    arguments = dict(
        server_name=ValueArgument('The new name', '--name'),
        flavor_id=IntArgument('Resize (set another flavor)', '--flavor-id'),
        firewall_profile=FirewallProfileArgument(
            'Valid values: %s' % (', '.join(FirewallProfileArgument.profiles)),
            '--firewall'),
        metadata_to_set=KeyValueArgument(
            'Set metadata in key=value form (can be repeated)',
            '--metadata-set'),
        metadata_to_delete=RepeatableArgument(
            'Delete metadata by key (can be repeated)', '--metadata-del'),
        public_network_port_id=ValueArgument(
            'Connection to set new firewall (* for all)', '--port-id'),
    )
    required = [
        'server_name', 'flavor_id', 'firewall_profile', 'metadata_to_set',
        'metadata_to_delete']

    def _set_firewall_profile(self, server_id):
        vm = self._restruct_server_info(
            self.client.get_server_details(server_id))
        ports = [p for p in vm['ports'] if 'firewallProfile' in p]
        pick_port = self.arguments['public_network_port_id']
        if pick_port.value:
            ports = [p for p in ports if pick_port.value in (
                '*', '%s' % p['id'])]
        elif len(ports) > 1:
            port_strings = ['Server %s ports to public networks:' % server_id]
            for p in ports:
                port_strings.append('  %s' % p['id'])
                for k in ('network_id', 'ipv4', 'ipv6', 'firewallProfile'):
                    v = p.get(k)
                    if v:
                        port_strings.append('\t%s: %s' % (k, v))
            raiseCLIError(
                'Multiple public connections on server %s' % (
                    server_id), details=port_strings + [
                        'To select one:',
                        '  %s PORT_ID' % pick_port.lvalue,
                        'To set all:',
                        '  %s *' % pick_port.lvalue, ])
        if not ports:
            pp = pick_port.value
            raiseCLIError(
                'No public networks attached on server %s%s' % (
                    server_id, ' through port %s' % pp if pp else ''),
                details=[
                    'To see all networks:', '  kamaki network list',
                    'To see all connections:',
                    '  kamaki server info %s --nics' % server_id,
                    'To connect to a network:',
                    '  kamaki network connect NETWORK_ID --device-id %s' % (
                        server_id)])
        for port in ports:
            self.error('Set port %s firewall to %s' % (
                port['id'], self['firewall_profile']))
            self.client.set_firewall_profile(
                server_id=server_id,
                profile=self['firewall_profile'],
                port_id=port['id'])

    def _server_is_stopped(self, server_id, cerror):
        vm = self.client.get_server_details(server_id)
        if vm['status'].lower() not in ('stopped'):
            raiseCLIError(cerror, details=[
                'To resize a virtual server, it must be STOPPED',
                'Server %s status is %s' % (server_id, vm['status']),
                'To stop the server',
                '  kamaki server shutdown %s -w' % server_id])

    @errors.Generic.all
    @errors.Cyclades.connection
    @errors.Cyclades.server_id
    def _run(self, server_id):
        if self['server_name'] is not None:
            self.client.update_server_name((server_id), self['server_name'])
        if self['flavor_id']:
            try:
                self.client.resize_server(server_id, self['flavor_id'])
            except ClientError as ce:
                if ce.status in (404, ):
                    self._flavor_exists(flavor_id=self['flavor_id'])
                if ce.status in (400, ):
                    self._server_is_stopped(server_id, ce)
                raise
        if self['firewall_profile']:
            self._set_firewall_profile(server_id)
        if self['metadata_to_set']:
            self.client.update_server_metadata(
                server_id, **self['metadata_to_set'])
        for key in (self['metadata_to_delete'] or []):
            errors.Cyclades.metadata(
                self.client.delete_server_metadata)(server_id, key=key)

    def main(self, server_id):
        super(self.__class__, self)._run()
        pnpid = self.arguments['public_network_port_id']
        fp = self.arguments['firewall_profile']
        if pnpid.value and not fp.value:
            raise CLIInvalidArgument('Invalid argument compination', details=[
                'Argument %s should always be combined with %s' % (
                    pnpid.lvalue, fp.lvalue)])
        self._run(server_id=server_id)


@command(server_cmds)
class server_reassign(_CycladesInit, OptionalOutput):
    """Assign a virtual server to a different project"""

    arguments = dict(
        project_id=ValueArgument('The project to assign', '--project-id')
    )
    required = ('project_id', )

    @errors.Generic.all
    @errors.Cyclades.connection
    @errors.Cyclades.server_id
    def _run(self, server_id):
        try:
            self.client.reassign_server(server_id, self['project_id'])
        except ClientError as ce:
            if ce.status in (400, 403, 404):
                self._project_id_exists(project_id=self['project_id'])
            raise

    def main(self, server_id):
        super(self.__class__, self)._run()
        self._run(server_id=server_id)


@command(server_cmds)
class server_delete(_CycladesInit, _ServerWait):
    """Delete a virtual server"""

    arguments = dict(
        wait=FlagArgument('Wait server to be destroyed', ('-w', '--wait')),
        cluster=FlagArgument(
            '(DANGEROUS) Delete all VMs with names starting with the cluster '
            'prefix. Do not use it if unsure. Syntax:'
            ' kamaki server delete --cluster CLUSTER_PREFIX',
            '--cluster')
    )

    def _server_ids(self, server_var):
        if self['cluster']:
            return [s['id'] for s in self.client.list_servers() if (
                s['name'].startswith(server_var))]

        return [server_var, ]

    @errors.Cyclades.server_id
    def _delete_server(self, server_id):
        if self['wait']:
            details = self.client.get_server_details(server_id)
            status = details['status']

        self.client.delete_server(server_id)
        if self['wait']:
            self.wait_while(server_id, status)

    @errors.Generic.all
    @errors.Cyclades.connection
    def _run(self, server_var):
        deleted_vms = []
        for server_id in self._server_ids(server_var):
            self._delete_server(server_id=server_id)
            deleted_vms.append(server_id)
        if self['cluster']:
            dlen = len(deleted_vms)
            self.error('%s virtual server %s deleted' % (
                dlen, '' if dlen == 1 else 's'))

    def main(self, server_id_or_cluster_prefix):
        super(self.__class__, self)._run()
        self._run(server_id_or_cluster_prefix)


@command(server_cmds)
class server_reboot(_CycladesInit, _ServerWait):
    """Reboot a virtual server"""

    arguments = dict(
        type=ValueArgument('SOFT or HARD - default: SOFT', ('--type')),
        wait=FlagArgument('Wait server to start again', ('-w', '--wait'))
    )

    @errors.Generic.all
    @errors.Cyclades.connection
    @errors.Cyclades.server_id
    def _run(self, server_id):
        hard_reboot = None
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

        self.client.reboot_server(int(server_id), hard_reboot)
        if self['wait']:
            self.wait_while(server_id, 'REBOOT')

    def main(self, server_id):
        super(self.__class__, self)._run()
        self._run(server_id=server_id)


@command(server_cmds)
class server_start(_CycladesInit, _ServerWait):
    """Start an existing virtual server"""

    arguments = dict(
        wait=FlagArgument('Wait server to start', ('-w', '--wait'))
    )

    @errors.Generic.all
    @errors.Cyclades.connection
    @errors.Cyclades.server_id
    def _run(self, server_id):
        status = self.assert_not_in_status(server_id, 'ACTIVE')
        self.client.start_server(int(server_id))
        if self['wait']:
            self.wait_while(server_id, status)

    def main(self, server_id):
        super(self.__class__, self)._run()
        self._run(server_id=server_id)


@command(server_cmds)
class server_shutdown(_CycladesInit,  _ServerWait):
    """Shutdown an active virtual server"""

    arguments = dict(
        wait=FlagArgument('Wait server to shut down', ('-w', '--wait'))
    )

    @errors.Generic.all
    @errors.Cyclades.connection
    @errors.Cyclades.server_id
    def _run(self, server_id):
        status = self.assert_not_in_status(server_id, 'STOPPED')
        self.client.shutdown_server(int(server_id))
        if self['wait']:
            self.wait_while(server_id, status)

    def main(self, server_id):
        super(self.__class__, self)._run()
        self._run(server_id=server_id)


_basic_cons = CycladesComputeClient.CONSOLE_TYPES


class ConsoleTypeArgument(ValueArgument):

    TRANSLATE = {'no-vnc': 'vnc-ws', 'no-vnc-encrypted': 'vnc-wss'}

    @property
    def value(self):
        return getattr(self, '_value', None)

    @value.setter
    def value(self, new_value):
        global _basic_cons
        if new_value:
            v = new_value.lower()
            v = self.TRANSLATE.get(v, v)
            if v in _basic_cons:
                self._value = v
            else:
                ctypes = set(_basic_cons).difference(self.TRANSLATE.values())
                ctypes = list(ctypes) + [
                    '%s (aka %s)' % (a, t) for t, a in self.TRANSLATE.items()]
                raise CLIInvalidArgument(
                    'Invalid console type %s' % new_value, details=[
                        'Valid console types: %s' % (', '.join(ctypes)), ])


_translated = ConsoleTypeArgument.TRANSLATE
VALID_CONSOLE_TYPES = list(set(_basic_cons).difference(_translated.values()))
VALID_CONSOLE_TYPES += ['%s (aka %s)' % (a, t) for t, a in _translated.items()]


@command(server_cmds)
class server_console(_CycladesInit, OptionalOutput):
    """Create a VNC console and show connection information"""

    arguments = dict(
        console_type=ConsoleTypeArgument(
            'Valid values: %s Default: %s' % (
                ', '.join(VALID_CONSOLE_TYPES), VALID_CONSOLE_TYPES[0]),
            '--type'),
    )

    @errors.Generic.all
    @errors.Cyclades.connection
    @errors.Cyclades.server_id
    def _run(self, server_id):
        self.error('The following credentials will be invalidated shortly')
        ctype = self['console_type'] or VALID_CONSOLE_TYPES[0]
        self.print_(
            self.client.get_server_console(server_id, ctype), self.print_dict)

    def main(self, server_id):
        super(self.__class__, self)._run()
        self._run(server_id=server_id)


@command(server_cmds)
class server_wait(_CycladesInit, _ServerWait):
    """Wait for server to change its status (default: --while BUILD)"""

    arguments = dict(
        timeout=IntArgument(
            'Wait limit in seconds (default: 60)', '--timeout', default=60),
        status=StatusArgument(
            'DEPRECATED in next version, equivalent to "--while"',
            '--status',
            valid_states=server_states),
        status_w=StatusArgument(
            'Wait while in status (%s)' % ','.join(server_states), '--while',
            valid_states=server_states),
        status_u=StatusArgument(
            'Wait until status is reached (%s)' % ','.join(server_states),
            '--until',
            valid_states=server_states),
    )

    @errors.Generic.all
    @errors.Cyclades.connection
    @errors.Cyclades.server_id
    def _run(self, server_id):
        r = self.client.get_server_details(server_id)

        if self['status_u']:
            if r['status'].lower() == self['status_u'].lower():
                self.error(
                    'Server %s: already in %s' % (server_id, r['status']))
            else:
                self.wait_until(
                    server_id, self['status_u'], timeout=self['timeout'])
        else:
            status_w = self['status_w'] or self['status'] or 'BUILD'
            if r['status'].lower() == status_w.lower():
                self.wait_while(
                    server_id, status_w, timeout=self['timeout'])
            else:
                self.error(
                    'Server %s status: %s' % (server_id, r['status']))

    def main(self, server_id):
        super(self.__class__, self)._run()

        status_args = [self['status'], self['status_w'], self['status_u']]
        if len([x for x in status_args if x]) > 1:
            raise CLIInvalidArgument(
                'Invalid argument combination', importance=2, details=[
                    'Arguments %s, %s and %s are mutually exclusive' % (
                        self.arguments['status'].lvalue,
                        self.arguments['status_w'].lvalue,
                        self.arguments['status_u'].lvalue)])
        if self['status']:
            self.error(
                'WARNING: argument %s will be deprecated '
                'in the next version, use %s instead' % (
                    self.arguments['status'].lvalue,
                    self.arguments['status_w'].lvalue))

        self._run(server_id=server_id)


@command(flavor_cmds)
class flavor_list(_CycladesInit, OptionalOutput, NameFilter, IDFilter):
    """List available hardware flavors"""

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

    @errors.Generic.all
    @errors.Cyclades.connection
    def _run(self):
        withcommons = self['ram'] or self['vcpus'] or (
            self['disk'] or self['disk_template'])
        detail = self['detail'] or withcommons
        flavors = self.client.list_flavors(detail)
        flavors = self._filter_by_name(flavors)
        flavors = self._filter_by_id(flavors)
        if withcommons:
            flavors = self._apply_common_filters(flavors)
        if not (self['detail'] or self['output_format']):
            remove_from_items(flavors, 'links')
        if detail and not self['detail']:
            for flv in flavors:
                for key in set(flv).difference(['id', 'name']):
                    flv.pop(key)
        kwargs = dict(out=StringIO(), title=()) if self['more'] else {}
        self.print_(flavors, with_enumeration=self['enum'], **kwargs)
        if self['more']:
            pager(kwargs['out'].getvalue())

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(flavor_cmds)
class flavor_info(_CycladesInit, OptionalOutput):
    """Detailed information on a hardware flavor"""

    @errors.Generic.all
    @errors.Cyclades.connection
    @errors.Cyclades.flavor_id
    def _run(self, flavor_id):
        self.print_(self.client.get_flavor_details(flavor_id), self.print_dict)

    def main(self, flavor_id):
        super(self.__class__, self)._run()
        self._run(flavor_id=flavor_id)


# Volume Attachment Commands

@command(server_cmds)
class server_attachment(_CycladesInit, OptionalOutput):
    """Details on the attachment of a volume
    This is not information about the volume. To see volume information:
        $ kamaki volume info VOLUME_ID
    """

    arguments = dict(
        attachment_id=ValueArgument(
            'The volume attachment', '--attachment-id', )
    )
    required = ('attachment_id', )

    @errors.Generic.all
    @errors.Cyclades.connection
    @errors.Cyclades.server_id
    @errors.Cyclades.endpoint
    def _run(self, server_id):
        r = self.client.get_volume_attachment(server_id, self['attachment_id'])
        self.print_(r, self.print_dict)

    def main(self, server_id):
        super(self.__class__, self)._run()
        self._run(server_id=server_id)


@command(server_cmds)
class server_attachments(_CycladesInit, OptionalOutput):
    """List the volume attachments of a VM"""

    @errors.Generic.all
    @errors.Cyclades.connection
    @errors.Cyclades.server_id
    @errors.Cyclades.endpoint
    def _run(self, server_id):
        r = self.client.list_volume_attachments(server_id)
        self.print_(r)

    def main(self, server_id):
        super(self.__class__, self)._run()
        self._run(server_id=server_id)


@command(server_cmds)
class server_attach(_CycladesInit, OptionalOutput):
    """Attach a volume on a VM"""

    arguments = dict(
        volume_id=ValueArgument('The volume to be attached', '--volume-id')
    )
    required = ('volume_id', )

    @errors.Generic.all
    @errors.Cyclades.connection
    @errors.Cyclades.server_id
    @errors.Cyclades.endpoint
    def _run(self, server_id):
        r = self.client.attach_volume(server_id, self['volume_id'])
        self.print_(r, self.print_dict)

    def main(self, server_id):
        super(self.__class__, self)._run()
        self._run(server_id=server_id)


@command(server_cmds)
class server_detach(_CycladesInit):
    """Detach a volume from a VM"""

    arguments = dict(
        attachment_id=ValueArgument(
            'The volume attachment (mutually exclusive to --volume-id)',
            '--attachment-id', ),
        volume_id=ValueArgument(
            'Volume to detach from VM (mutually exclusive to --attachment-id)',
            '--volume-id')
    )
    required = ['attachment_id', 'volume_id']

    @errors.Generic.all
    @errors.Cyclades.connection
    @errors.Cyclades.server_id
    @errors.Cyclades.endpoint
    def _run(self, server_id):
        att_id = self['attachment_id']
        if att_id:
            self.client.delete_volume_attachment(server_id, att_id)
        else:
            r = self.client.detach_volume(server_id, self['volume_id'])
            self.error('%s detachment%s deleted, volume is detached' % (
                len(r), '' if len(r) == 1 else 's'))
        self.error('OK')

    def main(self, server_id):
        super(self.__class__, self)._run()
        if all([self['attachment_id'], self['volume_id']]):
            raise CLISyntaxError('Invalid argument compination', details=[
                '%s and %s are mutually exclusive' % (
                    self.arguments['attachment_id'].lvalue,
                    self.arguments['volume_id'].lvalue)])
        self._run(server_id=server_id)
