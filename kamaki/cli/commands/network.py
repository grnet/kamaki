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

from io import StringIO
from pydoc import pager

from kamaki.cli import command
from kamaki.cli.command_tree import CommandTree
from kamaki.cli.errors import (
    CLISyntaxError, CLIBaseUrlError, CLIInvalidArgument)
from kamaki.clients.cyclades import CycladesNetworkClient
from kamaki.cli.argument import FlagArgument, ValueArgument, RepeatableArgument
from kamaki.cli.commands import _command_init, errors, addLogSettings
from kamaki.cli.commands import (
    _optional_output_cmd, _optional_json, _name_filter, _id_filter)
from kamaki.cli.utils import filter_dicts_by_dict


network_cmds = CommandTree('network', 'Networking API network commands')
port_cmds = CommandTree('port', 'Networking API network commands')
subnet_cmds = CommandTree('subnet', 'Networking API network commands')
_commands = [network_cmds, port_cmds, subnet_cmds]


about_authentication = '\nUser Authentication:\
    \n* to check authentication: /user authenticate\
    \n* to set authentication token: /config set cloud.<cloud>.token <token>'


class _init_network(_command_init):
    @errors.generic.all
    @addLogSettings
    def _run(self, service='network'):
        if getattr(self, 'cloud', None):
            base_url = self._custom_url(service) or self._custom_url(
                'compute')
            if base_url:
                token = self._custom_token(service) or self._custom_token(
                    'compute') or self.config.get_cloud('token')
                self.client = CycladesNetworkClient(
                  base_url=base_url, token=token)
                return
        else:
            self.cloud = 'default'
        if getattr(self, 'auth_base', False):
            cyclades_endpoints = self.auth_base.get_service_endpoints(
                self._custom_type('compute') or 'compute',
                self._custom_version('compute') or '')
            base_url = cyclades_endpoints['publicURL']
            token = self.auth_base.token
            self.client = CycladesNetworkClient(base_url=base_url, token=token)
        else:
            raise CLIBaseUrlError(service='network')

    def main(self):
        self._run()


@command(network_cmds)
class network_list(_init_network, _optional_json, _name_filter, _id_filter):
    """List networks
    Use filtering arguments (e.g., --name-like) to manage long server lists
    """

    arguments = dict(
        detail=FlagArgument('show detailed output', ('-l', '--details')),
        more=FlagArgument(
            'output results in pages (-n to set items per page, default 10)',
            '--more'),
        user_id=ValueArgument(
            'show only networks belonging to user with this id', '--user-id')
    )

    def _filter_by_user_id(self, nets):
        return filter_dicts_by_dict(nets, dict(user_id=self['user_id'])) if (
            self['user_id']) else nets

    @errors.generic.all
    @errors.cyclades.connection
    def _run(self):
        detail = self['detail'] or self['user_id']
        nets = self.client.list_networks(detail=detail)
        nets = self._filter_by_user_id(nets)
        nets = self._filter_by_name(nets)
        nets = self._filter_by_id(nets)
        if detail and not self['detail']:
            nets = [dict(
                id=n['id'], name=n['name'], links=n['links']) for n in nets]
        kwargs = dict()
        if self['more']:
            kwargs['out'] = StringIO()
            kwargs['title'] = ()
        self._print(nets, **kwargs)
        if self['more']:
            pager(kwargs['out'].getvalue())

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(network_cmds)
class network_info(_init_network, _optional_json):
    """Get details about a network"""

    @errors.generic.all
    @errors.cyclades.connection
    @errors.cyclades.network_id
    def _run(self, network_id):
        net = self.client.get_network_details(network_id)
        self._print(net, self.print_dict)

    def main(self, network_id):
        super(self.__class__, self)._run()
        self._run(network_id=network_id)


@command(network_cmds)
class network_create(_init_network, _optional_json):
    """Create a new network
    Valid network types: CUSTOM MAC_FILTERED IP_LESS_ROUTED PHYSICAL_VLAN
    """

    arguments = dict(
        name=ValueArgument('Network name', '--name'),
        shared=FlagArgument(
            'Make network shared (special privileges required)', '--shared')
    )

    @errors.generic.all
    @errors.cyclades.connection
    @errors.cyclades.network_type
    def _run(self, network_type):
        net = self.client.create_network(
            network_type, name=self['name'], shared=self['shared'])
        self._print(net, self.print_dict)

    def main(self, network_type):
        super(self.__class__, self)._run()
        self._run(network_type=network_type)


@command(network_cmds)
class network_delete(_init_network, _optional_output_cmd):
    """Delete a network"""

    @errors.generic.all
    @errors.cyclades.connection
    @errors.cyclades.network_id
    def _run(self, network_id):
        r = self.client.delete_network(network_id)
        self._optional_output(r)

    def main(self, network_id):
        super(self.__class__, self)._run()
        self._run(network_id=network_id)


@command(network_cmds)
class network_set(_init_network, _optional_json):
    """Set an attribute of a network, leave the rest untouched (update)
    Only "--name" is supported for now
    """

    arguments = dict(name=ValueArgument('New name of the network', '--name'))

    @errors.generic.all
    @errors.cyclades.connection
    @errors.cyclades.network_id
    def _run(self, network_id):
        if self['name'] in (None, ):
            raise CLISyntaxError(
                'Missing network attributes to update',
                details=[
                    'At least one if the following is expected:',
                    '  --name=<new name>'])
        r = self.client.update_network(network_id, name=self['name'])
        self._print(r, self.print_dict)

    def main(self, network_id):
        super(self.__class__, self)._run()
        self._run(network_id=network_id)


@command(subnet_cmds)
class subnet_list(_init_network, _optional_json, _name_filter, _id_filter):
    """List subnets
    Use filtering arguments (e.g., --name-like) to manage long server lists
    """

    arguments = dict(
        detail=FlagArgument('show detailed output', ('-l', '--details')),
        more=FlagArgument(
            'output results in pages (-n to set items per page, default 10)',
            '--more'),
        user_id=ValueArgument(
            'show only subnets belonging to user with this id', '--user-id')
    )

    def _filter_by_user_id(self, nets):
        return filter_dicts_by_dict(nets, dict(user_id=self['user_id'])) if (
            self['user_id']) else nets

    @errors.generic.all
    @errors.cyclades.connection
    def _run(self):
        detail = self['detail'] or self['user_id']
        nets = self.client.list_subnets()
        nets = self._filter_by_user_id(nets)
        nets = self._filter_by_name(nets)
        nets = self._filter_by_id(nets)
        if detail and not self['detail']:
            nets = [dict(
                id=n['id'], name=n['name'], links=n['links']) for n in nets]
        kwargs = dict()
        if self['more']:
            kwargs['out'] = StringIO()
            kwargs['title'] = ()
        self._print(nets, **kwargs)
        if self['more']:
            pager(kwargs['out'].getvalue())

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(subnet_cmds)
class subnet_info(_init_network, _optional_json):
    """Get details about a subnet"""

    @errors.generic.all
    @errors.cyclades.connection
    def _run(self, subnet_id):
        net = self.client.get_subnet_details(subnet_id)
        self._print(net, self.print_dict)

    def main(self, subnet_id):
        super(self.__class__, self)._run()
        self._run(subnet_id=subnet_id)


class AllocationPoolArgument(RepeatableArgument):

    @property
    def value(self):
        return super(AllocationPoolArgument, self).value or []

    @value.setter
    def value(self, new_pools):
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
class subnet_create(_init_network, _optional_json):
    """Create a new subnet
    """

    arguments = dict(
        name=ValueArgument('Subnet name', '--name'),
        allocation_pools=AllocationPoolArgument(
            'start_address,end_address of allocation pool (can be repeated)'
            ' e.g., --alloc-pool=123.45.67.1,123.45.67.8',
            '--alloc-pool'),
        gateway=ValueArgument('Gateway IP', '--gateway'),
        subnet_id=ValueArgument('The id for the subnet', '--id'),
        ipv6=FlagArgument('If set, IP version is set to 6, else 4', '--ipv6'),
        enable_dhcp=FlagArgument('Enable dhcp (default: off)', '--with-dhcp')
    )

    @errors.generic.all
    @errors.cyclades.connection
    @errors.cyclades.network_id
    def _run(self, network_id, cidr):
        net = self.client.create_subnet(
            network_id, cidr,
            self['name'], self['allocation_pools'], self['gateway'],
            self['subnet_id'], self['ipv6'], self['enable_dhcp'])
        self._print(net, self.print_dict)

    def main(self, network_id, cidr):
        super(self.__class__, self)._run()
        self._run(network_id=network_id, cidr=cidr)


# @command(subnet_cmds)
# class subnet_delete(_init_network, _optional_output_cmd):
#     """Delete a subnet"""

#     @errors.generic.all
#     @errors.cyclades.connection
#     def _run(self, subnet_id):
#         r = self.client.delete_subnet(subnet_id)
#         self._optional_output(r)

#     def main(self, subnet_id):
#         super(self.__class__, self)._run()
#         self._run(subnet_id=subnet_id)


@command(subnet_cmds)
class subnet_set(_init_network, _optional_json):
    """Set an attribute of a subnet, leave the rest untouched (update)
    Only "--name" is supported for now
    """

    arguments = dict(name=ValueArgument('New name of the subnet', '--name'))

    @errors.generic.all
    @errors.cyclades.connection
    def _run(self, subnet_id):
        if self['name'] in (None, ):
            raise CLISyntaxError(
                'Missing subnet attributes to update',
                details=[
                    'At least one if the following is expected:',
                    '  --name=<new name>'])
        r = self.client.get_subnet_details(subnet_id)
        r = self.client.update_subnet(
            subnet_id, r['network_id'], name=self['name'])
        self._print(r, self.print_dict)

    def main(self, subnet_id):
        super(self.__class__, self)._run()
        self._run(subnet_id=subnet_id)


@command(port_cmds)
class port_info(_init_network, _optional_json):
    """Get details about a port"""

    @errors.generic.all
    @errors.cyclades.connection
    def _run(self, port_id):
        net = self.client.get_port_details(port_id)
        self._print(net, self.print_dict)

    def main(self, port_id):
        super(self.__class__, self)._run()
        self._run(port_id=port_id)


@command(port_cmds)
class port_info(_init_network, _optional_json):
    """Get details about a port"""

    @errors.generic.all
    @errors.cyclades.connection
    def _run(self, port_id):
        net = self.client.get_port_details(port_id)
        self._print(net, self.print_dict)

    def main(self, port_id):
        super(self.__class__, self)._run()
        self._run(port_id=port_id)


@command(port_cmds)
class port_delete(_init_network, _optional_output_cmd):
    """Delete a port"""

    @errors.generic.all
    @errors.cyclades.connection
    def _run(self, port_id):
        r = self.client.delete_port(port_id)
        self._optional_output(r)

    def main(self, port_id):
        super(self.__class__, self)._run()
        self._run(port_id=port_id)


@command(port_cmds)
class port_set(_init_network, _optional_json):
    """Set an attribute of a port, leave the rest untouched (update)
    Only "--name" is supported for now
    """

    arguments = dict(name=ValueArgument('New name of the port', '--name'))

    @errors.generic.all
    @errors.cyclades.connection
    def _run(self, port_id):
        if self['name'] in (None, ):
            raise CLISyntaxError(
                'Missing port attributes to update',
                details=[
                    'At least one if the following is expected:',
                    '  --name=<new name>'])
        r = self.client.get_port_details(port_id)
        r = self.client.update_port(
            port_id, r['network_id'], name=self['name'])
        self._print(r, self.print_dict)

    def main(self, port_id):
        super(self.__class__, self)._run()
        self._run(port_id=port_id)


#@command(port_cmds)
#class port_create(_init_network, _optional_json):
#
