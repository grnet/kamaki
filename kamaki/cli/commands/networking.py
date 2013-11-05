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
from kamaki.clients.networking import NetworkingClient, ClientError
from kamaki.cli.argument import FlagArgument, ValueArgument, KeyValueArgument
from kamaki.cli.argument import ProgressBarArgument, DateArgument, IntArgument
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


#  Remove this when the endpoint issue is resolved
from kamaki.cli.commands.cyclades import _init_cyclades as _init_networking

# class _init_networking(_command_init):
#     @errors.generic.all
#     @addLogSettings
#     def _run(self, service='network'):
#         if getattr(self, 'cloud', None):
#             base_url = self._custom_url(service) or self._custom_url(
#                 'network')
#             if base_url:
#                 token = self._custom_token(service) or self._custom_token(
#                     'network') or self.config.get_cloud('token')
#                 self.client = NetworkingClient(
#                   base_url=base_url, token=token)
#                 return
#         else:
#             self.cloud = 'default'
#         if getattr(self, 'auth_base', False):
#             cyclades_endpoints = self.auth_base.get_service_endpoints(
#                 self._custom_type('network') or 'network',
#                 self._custom_version('network') or '')
#             base_url = cyclades_endpoints['publicURL']
#             token = self.auth_base.token
#             self.client = NetworkingClient(base_url=base_url, token=token)
#         else:
#             raise CLIBaseUrlError(service='network')

#     def main(self):
#         self._run()


@command(network_cmds)
class network_list(_init_networking, _optional_json, _name_filter, _id_filter):
    """List networks
    Use filtering arguments (e.g., --name-like) to manage long server lists
    """

    arguments = dict(
        detail=FlagArgument('show detailed output', ('-l', '--details')),
    )

    @errors.generic.all
    @errors.cyclades.connection
    @errors.cyclades.date
    def _run(self):
        nets = self.client.list_networks()
        if not self['detail']:
            for net in nets:
                net = dict(net['id'], net['name'])
        self._print(nets)

    def main(self):
        super(self.__class__, self)._run()
        self._run()
