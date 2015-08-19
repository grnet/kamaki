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

from io import StringIO
from pydoc import pager

from kamaki.cli import command
from kamaki.cli.cmdtree import CommandTree
from kamaki.cli.errors import CLIInvalidArgument, raiseCLIError
from kamaki.clients.cyclades import (
    CycladesNetworkClient, ClientError, CycladesComputeClient)
from kamaki.cli.argument import (
    FlagArgument, ValueArgument, RepeatableArgument, IntArgument,
    StatusArgument)
from kamaki.cli.cmds import (
    CommandInit, OptionalOutput, NameFilter, IDFilter, errors, client_log)
from kamaki.cli.cmds import Wait


network_cmds = CommandTree('network', 'Network API network commands')
port_cmds = CommandTree('port', 'Network API port commands')
subnet_cmds = CommandTree('subnet', 'Network API subnet commands')
ip_cmds = CommandTree('ip', 'Network API floatingip commands')
namespaces = [network_cmds, port_cmds, subnet_cmds, ip_cmds]

port_states = ('BUILD', 'ACTIVE', 'DOWN', 'ERROR')


class _PortWait(Wait):

    def wait_while(self, port_id, current_status, timeout=60):
        super(_PortWait, self).wait(
            'Port', port_id, self.client.wait_port_while, current_status,
            timeout=timeout)

    def wait_until(self, port_id, target_status, timeout=60):
        super(_PortWait, self).wait(
            'Port', port_id, self.client.wait_port_until, target_status,
            timeout=timeout, msg='not yet')


class _NetworkInit(CommandInit):
    @errors.Generic.all
    @client_log
    def _run(self):
        self.client = self.get_client(CycladesNetworkClient, 'network')

    def _filter_by_user_id(self, nets):
        return [net for net in nets if net['user_id'] == self['user_id']] if (
            self['user_id']) else nets

    def _get_compute_client(self):
        compute = getattr(self, '_compute_client', None)
        if not compute:
            compute = self.get_client(CycladesComputeClient, 'cyclades')
            self._compute_client = compute
        return compute

    @errors.Cyclades.network_id
    def _network_exists(self, network_id):
        self.client.get_network_details(network_id)

    @errors.Cyclades.server_id
    def _server_exists(self, server_id):
        compute_client = self._get_compute_client()
        compute_client.get_server_details(server_id)

    def _ip_exists(self, ip, network_id, error):
        for ip_item in self.client.list_floatingips():
            if ip_item['floating_ip_address'] == ip:
                if network_id and ip_item['floating_network_id'] != network_id:
                    raiseCLIError(error, details=[
                        'Floating IP %s does not belong to network %s ,' % (
                            ip, network_id),
                        'To get information on IP %s' % ip,
                        '  kamaki ip info %s' % ip_item['id']])
                return
        raiseCLIError(error, details=[
            'Floating IP %s not found' % ip] + errors.Cyclades.about_ips)

    def main(self):
        self._run()


@command(network_cmds)
class network_list(_NetworkInit, OptionalOutput, NameFilter, IDFilter):
    """List networks
    Use filtering arguments (e.g., --name-like) to manage long lists
    """

    arguments = dict(
        detail=FlagArgument('show detailed output', ('-l', '--details')),
        more=FlagArgument(
            'output results in pages (-n to set items per page, default 10)',
            '--more'),
        user_id=ValueArgument(
            'show only networks belonging to user with this id', '--user-id')
    )

    @errors.Generic.all
    @errors.Cyclades.connection
    def _run(self):
        nets = self.client.list_networks(detail=True)
        nets = self._filter_by_user_id(nets)
        nets = self._filter_by_name(nets)
        nets = self._filter_by_id(nets)
        if not self['detail']:
            nets = [dict(
                id=n['id'],
                name=n['name'],
                public='( %s )' % ('public' if (
                    n.get('public', None)) else 'private')) for n in nets]
            kwargs = dict(title=('id', 'name', 'public'))
        else:
            kwargs = dict()
        if self['more']:
            kwargs['out'] = StringIO()
            kwargs['title'] = ()
        self.print_(nets, **kwargs)
        if self['more']:
            pager(kwargs['out'].getvalue())

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(network_cmds)
class network_info(_NetworkInit, OptionalOutput):
    """Get details about a network"""

    @errors.Generic.all
    @errors.Cyclades.connection
    @errors.Cyclades.network_id
    def _run(self, network_id):
        net = self.client.get_network_details(network_id)
        self.print_(net, self.print_dict)

    def main(self, network_id):
        super(self.__class__, self)._run()
        self._run(network_id=network_id)


class NetworkTypeArgument(ValueArgument):

    types = ('MAC_FILTERED', 'CUSTOM', 'IP_LESS_ROUTED', 'PHYSICAL_VLAN')

    @property
    def value(self):
        return getattr(self, '_value', self.types[0])

    @value.setter
    def value(self, new_value):
        if new_value and new_value.upper() in self.types:
            self._value = new_value.upper()
        elif new_value:
            raise CLIInvalidArgument(
                'Invalid network type %s' % new_value, details=[
                    'Valid types: %s' % ', '.join(self.types), ])


@command(network_cmds)
class network_create(_NetworkInit, OptionalOutput):
    """Create a new network (default type: MAC_FILTERED)"""

    arguments = dict(
        name=ValueArgument('Network name', '--name'),
        shared=FlagArgument(
            'Make network shared (special privileges required)', '--shared'),
        project_id=ValueArgument('Assign network to project', '--project-id'),
        network_type=NetworkTypeArgument(
            'Valid network types: %s' % (', '.join(NetworkTypeArgument.types)),
            '--type')
    )

    @errors.Generic.all
    @errors.Cyclades.connection
    def _run(self):
        try:
            net = self.client.create_network(
                self['network_type'],
                name=self['name'],
                shared=self['shared'],
                project_id=self['project_id'])
        except ClientError as ce:
            if self['project_id'] and ce.status in (400, 403, 404):
                self._project_id_exists(project_id=self['project_id'])
            raise
        self.print_(net, self.print_dict)

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(network_cmds)
class network_reassign(_NetworkInit, OptionalOutput):
    """Assign a network to a different project"""

    arguments = dict(
        project_id=ValueArgument('Assign network to project', '--project-id'),
    )
    required = ('project_id', )

    @errors.Generic.all
    @errors.Cyclades.connection
    @errors.Cyclades.network_permissions
    @errors.Cyclades.network_id
    def _run(self, network_id):
        try:
            self.client.reassign_network(network_id, self['project_id'])
        except ClientError as ce:
            if ce.status in (400, 403, 404):
                self._project_id_exists(project_id=self['project_id'])
            raise

    def main(self, network_id):
        super(self.__class__, self)._run()
        self._run(network_id=network_id)


@command(network_cmds)
class network_delete(_NetworkInit):
    """Delete a network"""

    @errors.Generic.all
    @errors.Cyclades.connection
    @errors.Cyclades.network_permissions
    @errors.Cyclades.network_in_use
    @errors.Cyclades.network_id
    def _run(self, network_id):
        self.client.delete_network(network_id)

    def main(self, network_id):
        super(self.__class__, self)._run()
        self._run(network_id=network_id)


@command(network_cmds)
class network_modify(_NetworkInit, OptionalOutput):
    """Modify network attributes"""

    arguments = dict(new_name=ValueArgument('Rename the network', '--name'))
    required = ['new_name', ]

    @errors.Generic.all
    @errors.Cyclades.connection
    @errors.Cyclades.network_permissions
    @errors.Cyclades.network_id
    def _run(self, network_id):
        r = self.client.update_network(network_id, name=self['new_name'])
        self.print_(r, self.print_dict)

    def main(self, network_id):
        super(self.__class__, self)._run()
        self._run(network_id=network_id)


@command(subnet_cmds)
class subnet_list(_NetworkInit, OptionalOutput, NameFilter, IDFilter):
    """List subnets
    Use filtering arguments (e.g., --name-like) to manage long server lists
    """

    arguments = dict(
        detail=FlagArgument('show detailed output', ('-l', '--details')),
        more=FlagArgument('output results in pages', '--more')
    )

    @errors.Generic.all
    @errors.Cyclades.connection
    def _run(self):
        nets = self.client.list_subnets()
        nets = self._filter_by_name(nets)
        nets = self._filter_by_id(nets)
        if not self['detail']:
            nets = [dict(
                id=n['id'],
                name=n['name'],
                net='( of network %s )' % n['network_id']) for n in nets]
            kwargs = dict(title=('id', 'name', 'net'))
        else:
            kwargs = dict()
        if self['more']:
            kwargs['out'] = StringIO()
            kwargs['title'] = ()
        self.print_(nets, **kwargs)
        if self['more']:
            pager('%s' % kwargs['out'].getvalue())

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(subnet_cmds)
class subnet_info(_NetworkInit, OptionalOutput):
    """Get details about a subnet"""

    @errors.Generic.all
    @errors.Cyclades.connection
    @errors.Cyclades.subnet_id
    def _run(self, subnet_id):
        net = self.client.get_subnet_details(subnet_id)
        self.print_(net, self.print_dict)

    def main(self, subnet_id):
        super(self.__class__, self)._run()
        self._run(subnet_id=subnet_id)


class AllocationPoolArgument(RepeatableArgument):

    @property
    def value(self):
        return super(AllocationPoolArgument, self).value or []

    @value.setter
    def value(self, new_pools):
        if not new_pools:
            return
        new_list = []
        for pool in new_pools:
            start, comma, end = pool.partition(',')
            if not (start and comma and end):
                raise CLIInvalidArgument(
                    'Invalid allocation pool argument %s' % pool, details=[
                        'Allocation values must be of the form:',
                        '  <start address>,<end address>'])
            new_list.append(dict(start=start, end=end))
        self._value = new_list


@command(subnet_cmds)
class subnet_create(_NetworkInit, OptionalOutput):
    """Create a new subnet"""

    arguments = dict(
        name=ValueArgument('Subnet name', '--name'),
        allocation_pools=AllocationPoolArgument(
            'start_address,end_address of allocation pool (can be repeated)'
            ' e.g., --alloc-pool=123.45.67.1,123.45.67.8',
            '--alloc-pool'),
        gateway=ValueArgument('Gateway IP', '--gateway'),
        no_gateway=FlagArgument('Do not assign a gateway IP', '--no-gateway'),
        subnet_id=ValueArgument('The id for the subnet', '--id'),
        ipv6=FlagArgument('If set, IP version is set to 6, else 4', '--ipv6'),
        enable_dhcp=FlagArgument('Enable dhcp (default: off)', '--with-dhcp'),
        network_id=ValueArgument('Set the network ID', '--network-id'),
        cidr=ValueArgument('Set the CIDR', '--cidr')
    )
    required = ('network_id', 'cidr')

    @errors.Generic.all
    @errors.Cyclades.connection
    def _run(self):
        gateway = '' if self['no_gateway'] else self['gateway']
        try:
            net = self.client.create_subnet(
                self['network_id'], self['cidr'],
                self['name'], self['allocation_pools'], gateway,
                self['subnet_id'], self['ipv6'], self['enable_dhcp'])
        except ClientError as ce:
            if ce.status in (404, 400):
                self._network_exists(network_id=self['network_id'])
            raise
        self.print_(net, self.print_dict)

    def main(self):
        super(self.__class__, self)._run()
        if self['gateway'] and self['no_gateway']:
            raise CLIInvalidArgument('Conflicting arguments', details=[
                'Arguments %s and %s cannot be used together' % (
                    self.arguments['gateway'].lvalue,
                    self.arguments['no_gateway'].lvalue)])
        self._run()


@command(subnet_cmds)
class subnet_modify(_NetworkInit, OptionalOutput):
    """Modify the attributes of a subnet"""

    arguments = dict(
        new_name=ValueArgument('New name of the subnet', '--name')
    )
    required = ['new_name']

    @errors.Generic.all
    @errors.Cyclades.connection
    @errors.Cyclades.subnet_permissions
    @errors.Cyclades.subnet_id
    def _run(self, subnet_id):
        r = self.client.update_subnet(subnet_id, name=self['new_name'])
        self.print_(r, self.print_dict)

    def main(self, subnet_id):
        super(self.__class__, self)._run()
        self._run(subnet_id=subnet_id)


@command(port_cmds)
class port_list(_NetworkInit, OptionalOutput, NameFilter, IDFilter):
    """List all ports"""

    arguments = dict(
        detail=FlagArgument('show detailed output', ('-l', '--details')),
        more=FlagArgument('output results in pages', '--more'),
        user_id=ValueArgument(
            'show only networks belonging to user with this id', '--user-id')
    )

    @errors.Generic.all
    @errors.Cyclades.connection
    def _run(self):
        ports = self.client.list_ports()
        ports = self._filter_by_user_id(ports)
        ports = self._filter_by_name(ports)
        ports = self._filter_by_id(ports)
        if not self['detail']:
            ports = [dict(id=p['id'], name=p['name']) for p in ports]
        kwargs = dict()
        if self['more']:
            kwargs['out'] = StringIO()
            kwargs['title'] = ()
        self.print_(ports, **kwargs)
        if self['more']:
            pager(kwargs['out'].getvalue())

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(port_cmds)
class port_info(_NetworkInit, OptionalOutput):
    """Get details about a port"""

    @errors.Generic.all
    @errors.Cyclades.connection
    @errors.Cyclades.port_id
    def _run(self, port_id):
        port = self.client.get_port_details(port_id)
        self.print_(port, self.print_dict)

    def main(self, port_id):
        super(self.__class__, self)._run()
        self._run(port_id=port_id)


@command(port_cmds)
class port_delete(_NetworkInit, _PortWait):
    """Delete a port (== disconnect server from network)"""

    arguments = dict(
        wait=FlagArgument('Wait port to be deleted', ('-w', '--wait'))
    )

    @errors.Generic.all
    @errors.Cyclades.connection
    @errors.Cyclades.port_id
    def _run(self, port_id):
        if self['wait']:
            status = self.client.get_port_details(port_id)['status']
        self.client.delete_port(port_id)
        if self['wait']:
            try:
                self.wait_while(port_id, status)
            except ClientError as ce:
                if ce.status not in (404, ):
                    raise
                self.error('Port %s is deleted' % port_id)

    def main(self, port_id):
        super(self.__class__, self)._run()
        self._run(port_id=port_id)


@command(port_cmds)
class port_modify(_NetworkInit, OptionalOutput):
    """Modify the attributes of a port"""

    arguments = dict(new_name=ValueArgument('New name of the port', '--name'))
    required = ['new_name', ]

    @errors.Generic.all
    @errors.Cyclades.connection
    @errors.Cyclades.port_id
    def _run(self, port_id):
        r = self.client.get_port_details(port_id)
        r = self.client.update_port(
            port_id, r['network_id'], name=self['new_name'])
        self.print_(r, self.print_dict)

    def main(self, port_id):
        super(self.__class__, self)._run()
        self._run(port_id=port_id)


class _port_create(_NetworkInit, OptionalOutput, _PortWait):

    @errors.Cyclades.subnet_id
    def _subnet_exists(self, subnet_id):
        self.client.get_subnet_details(subnet_id)

    def connect(self, network_id, device_id):
        subnet_id, ip = self['subnet_id'], self['ip_address']
        fixed_ips = [dict(ip_address=ip)] if (ip) else None
        if fixed_ips and subnet_id:
            fixed_ips[0]['subnet_id'] = subnet_id
        try:
            r = self.client.create_port(
                network_id, device_id,
                name=self['name'],
                security_groups=self['security_group_id'],
                fixed_ips=fixed_ips)
        except ClientError as ce:
            if ce.status in (400, 404):
                self._network_exists(network_id=network_id)
                self._server_exists(server_id=device_id)
                if subnet_id:
                    self._subnet_exists(subnet_id=subnet_id)
                if self['ip_address']:
                    self._ip_exists(ip=ip, network_id=network_id, error=ce)
            raise
        if self['wait']:
            self.wait_while(r['id'], r['status'])
            r = self.client.get_port_details(r['id'])
        self.print_([r])


@command(port_cmds)
class port_create(_port_create):
    """Create a new port (== connect server to network)"""

    arguments = dict(
        name=ValueArgument('A human readable name', '--name'),
        security_group_id=RepeatableArgument(
            'Add a security group id (can be repeated)',
            ('-g', '--security-group')),
        subnet_id=ValueArgument(
            'Subnet id for fixed ips (used with --ip-address)',
            '--subnet-id'),
        ip_address=ValueArgument('IP address for subnet id', '--ip-address'),
        network_id=ValueArgument('Set the network ID', '--network-id'),
        device_id=ValueArgument(
            'The device is either a virtual server or a virtual router',
            '--device-id'),
        wait=FlagArgument('Wait port to be established', ('-w', '--wait')),
    )
    required = ('network_id', 'device_id')

    @errors.Generic.all
    @errors.Cyclades.connection
    def _run(self):
        self.connect(self['network_id'], self['device_id'])

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(port_cmds)
class port_wait(_NetworkInit, _PortWait):
    """Wait for port to finish (default: --while BUILD)"""

    arguments = dict(
        timeout=IntArgument(
            'Wait limit in seconds (default: 60)', '--timeout', default=60),
        status=StatusArgument(
            'DEPRECATED in next version, equivalent to "--while"', '--status',
            valid_states=port_states),
        status_w=StatusArgument(
            'Wait while in status (%s)' % ','.join(port_states), '--while',
            valid_states=port_states),
        status_u=StatusArgument(
            'Wait until status is reached (%s)' % ','.join(port_states),
            '--until',
            valid_states=port_states),
    )

    @errors.Generic.all
    @errors.Cyclades.connection
    def _run(self, port_id):
        r = self.client.get_port_details(port_id)

        if self['status_u']:
            if r['status'].lower() == self['status_u'].lower():
                self.error('Port %s: already in %s' % (port_id, r['status']))
            else:
                self.wait_until(
                    port_id, self['status_u'], timeout=self['timeout'])
        else:
            status_w = self['status_w'] or self['status'] or 'BUILD'
            if r['status'].lower() == status_w.lower():
                self.wait_while(port_id, status_w, timeout=self['timeout'])
            else:
                self.error('Port %s status: %s' % (port_id, r['status']))

    def main(self, port_id):
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

        self._run(port_id=port_id)


@command(ip_cmds)
class ip_list(_NetworkInit, OptionalOutput):
    """List reserved floating IPs"""

    @errors.Generic.all
    @errors.Cyclades.connection
    def _run(self):
        self.print_(self.client.list_floatingips())

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(ip_cmds)
class ip_info(_NetworkInit, OptionalOutput):
    """Get details on a floating IP"""

    @errors.Generic.all
    @errors.Cyclades.connection
    @errors.Cyclades.ip_id
    def _run(self, ip_id):
        self.print_(self.client.get_floatingip_details(ip_id), self.print_dict)

    def main(self, ip_id):
        super(self.__class__, self)._run()
        self._run(ip_id=ip_id)


@command(ip_cmds)
class ip_create(_NetworkInit, OptionalOutput):
    """Reserve an IP on a network"""

    arguments = dict(
        network_id=ValueArgument(
            'The network to preserve the IP on', '--network-id'),
        ip_address=ValueArgument('Allocate an IP address', '--address'),
        project_id=ValueArgument('Assign the IP to project', '--project-id'),
    )

    @errors.Generic.all
    @errors.Cyclades.connection
    def _run(self):
        try:
            self.print_(
                self.client.create_floatingip(
                    self['network_id'],
                    floating_ip_address=self['ip_address'],
                    project_id=self['project_id']),
                self.print_dict)
        except ClientError as ce:
            if ce.status in (400, 404):
                network_id, ip = self['network_id'], self['ip_address']
                self._network_exists(network_id=network_id)
                if ip:
                    self._ip_exists(ip, network_id, ce)
            if self['project_id'] and ce.status in (400, 403, 404):
                self._project_id_exists(project_id=self['project_id'])
            raise

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(ip_cmds)
class ip_reassign(_NetworkInit):
    """Assign a floating IP to a different project"""

    arguments = dict(
        project_id=ValueArgument('Assign the IP to project', '--project-id'),
    )
    required = ('project_id', )

    @errors.Generic.all
    @errors.Cyclades.connection
    def _run(self, ip):
        try:
            self.client.reassign_floating_ip(ip, self['project_id'])
        except ClientError as ce:
            if ce.status in (400, 404):
                self._ip_exists(ip=ip, network_id=None, error=ce)
            raise

    def main(self, IP):
        super(self.__class__, self)._run()
        self._run(ip=IP)


@command(ip_cmds)
class ip_delete(_NetworkInit):
    """Unreserve an IP (also delete the port, if attached)"""

    @errors.Generic.all
    @errors.Cyclades.connection
    @errors.Cyclades.ip_id
    def _run(self, ip_id):
        self.client.delete_floatingip(ip_id)

    def main(self, ip_id):
        super(self.__class__, self)._run()
        self._run(ip_id=ip_id)


@command(ip_cmds)
class ip_attach(_port_create):
    """Attach an IP on a virtual server"""

    arguments = dict(
        name=ValueArgument('A human readable name for the port', '--name'),
        security_group_id=RepeatableArgument(
            'Add a security group id (can be repeated)',
            ('-g', '--security-group')),
        subnet_id=ValueArgument('Subnet id', '--subnet-id'),
        wait=FlagArgument('Wait IP to be attached', ('-w', '--wait')),
        server_id=ValueArgument('Server to attach to this IP', '--server-id')
    )
    required = ('server_id', )

    @errors.Generic.all
    @errors.Cyclades.connection
    def _run(self, ip_or_ip_id):
        netid = None
        for ip in self.client.list_floatingips():
            if ip_or_ip_id in (ip['floating_ip_address'], ip['id']):
                netid = ip['floating_network_id']
                iparg = ValueArgument(parsed_name='--ip')
                iparg.value = ip['floating_ip_address']
                self.arguments['ip_address'] = iparg
                break
        if netid:
            server_id = self['server_id']
            self.error('Creating a port to attach IP %s to server %s' % (
                ip_or_ip_id, server_id))
            try:
                self.connect(netid, server_id)
            except ClientError as ce:
                self.error('Failed to connect network %s with server %s' % (
                    netid, server_id))
                if ce.status in (400, 404):
                    self._server_exists(server_id=server_id)
                    self._network_exists(network_id=netid)
                raise
        else:
            raiseCLIError(
                '%s does not match any reserved IPs or IP ids' % ip_or_ip_id,
                details=errors.Cyclades.about_ips)

    def main(self, ip_or_ip_id):
        super(self.__class__, self)._run()
        self._run(ip_or_ip_id=ip_or_ip_id)


@command(ip_cmds)
class ip_detach(_NetworkInit, _PortWait, OptionalOutput):
    """Detach an IP from a virtual server"""

    arguments = dict(
        wait=FlagArgument('Wait until IP is detached', ('-w', '--wait')),
    )

    @errors.Generic.all
    @errors.Cyclades.connection
    def _run(self, ip_or_ip_id):
        for ip in self.client.list_floatingips():
            if ip_or_ip_id in (ip['floating_ip_address'], ip['id']):
                if not ip['port_id']:
                    raiseCLIError('IP %s is not attached' % ip_or_ip_id)
                self.error('Deleting port %s:' % ip['port_id'])
                self.client.delete_port(ip['port_id'])
                if self['wait']:
                    port_status = self.client.get_port_details(ip['port_id'])[
                        'status']
                    try:
                        self.wait_while(ip['port_id'], port_status)
                    except ClientError as ce:
                        if ce.status not in (404, ):
                            raise
                        self.error('Port %s is deleted' % ip['port_id'])
                return
        raiseCLIError('IP or IP id %s not found' % ip_or_ip_id)

    def main(self, ip_or_ip_id):
        super(self.__class__, self)._run()
        self._run(ip_or_ip_id)


@command(network_cmds)
class network_connect(_port_create):
    """Connect a network with a device (server or router)"""

    arguments = dict(
        name=ValueArgument('A human readable name for the port', '--name'),
        security_group_id=RepeatableArgument(
            'Add a security group id (can be repeated)',
            ('-g', '--security-group')),
        subnet_id=ValueArgument(
            'Subnet id for fixed ips (used with --ip-address)',
            '--subnet-id'),
        ip_address=ValueArgument(
            'IP address for subnet id (used with --subnet-id', '--ip-address'),
        wait=FlagArgument('Wait network to connect', ('-w', '--wait')),
        device_id=RepeatableArgument(
            'Connect this device to the network (can be repeated)',
            '--device-id')
    )
    required = ('device_id', )

    @errors.Generic.all
    @errors.Cyclades.connection
    @errors.Cyclades.network_id
    def _run(self, network_id, server_id):
        self.error('Creating a port to connect network %s with device %s' % (
            network_id, server_id))
        try:
            self.connect(network_id, server_id)
        except ClientError as ce:
            if ce.status in (400, 404):
                self._server_exists(server_id=server_id)
            raise

    def main(self, network_id):
        super(self.__class__, self)._run()
        for sid in self['device_id']:
            self._run(network_id=network_id, server_id=sid)


@command(network_cmds)
class network_disconnect(_NetworkInit, _PortWait, OptionalOutput):
    """Disconnect a network from a device"""

    arguments = dict(
        wait=FlagArgument('Wait network to disconnect', ('-w', '--wait')),
        device_id=RepeatableArgument(
            'Disconnect device from the network (can be repeated)',
            '--device-id')
    )
    required = ('device_id', )

    @errors.Cyclades.server_id
    def _get_vm(self, server_id):
        return self._get_compute_client().get_server_details(server_id)

    @errors.Generic.all
    @errors.Cyclades.connection
    @errors.Cyclades.network_id
    def _run(self, network_id, server_id):
        vm = self._get_vm(server_id=server_id)
        ports = [port for port in vm['attachments'] if (
            port['network_id'] in (network_id, ))]
        if not ports:
            raiseCLIError('Device %s has no network %s attached' % (
                server_id, network_id), importance=2, details=[
                    'To get device networking',
                    '  kamaki server info %s --nics' % server_id])
        for port in ports:
            if self['wait']:
                port['status'] = self.client.get_port_details(port['id'])[
                    'status']
            self.client.delete_port(port['id'])
            self.error('Deleting port %s (net-id: %s, device-id: %s):' % (
                port['id'], network_id, server_id))
            if self['wait']:
                try:
                    self.wait_while(port['id'], port['status'])
                except ClientError as ce:
                    if ce.status not in (404, ):
                        raise
                    self.error('Port %s is deleted' % port['id'])

    def main(self, network_id):
        super(self.__class__, self)._run()
        for sid in self['device_id']:
            self._run(network_id=network_id, server_id=sid)
