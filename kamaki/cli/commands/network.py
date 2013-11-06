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
from kamaki.cli.argument import FlagArgument, ValueArgument
from kamaki.cli.commands import _command_init, errors, addLogSettings
from kamaki.cli.commands import (
    _optional_output_cmd, _optional_json, _name_filter, _id_filter)


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
    )

    @errors.generic.all
    @errors.cyclades.connection
    def _run(self):
        nets = self.client.list_networks()
        nets = self._filter_by_name(nets)
        nets = self._filter_by_id(nets)
        if not self['detail']:
            nets = [dict(id=net['id'], name=net['name']) for net in nets]
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
    Valid network types: CUSTOM, MAC_FILTERED, IP_LESS_ROUTED, PHYSICAL_VLAN
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
