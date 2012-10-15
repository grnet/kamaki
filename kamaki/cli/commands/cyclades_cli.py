# Copyright 2012 GRNET S.A. All rights reserved.
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

API_DESCRIPTION = {'server':'Compute/Cyclades API server commands',
    'flavor':'Compute/Cyclades API flavor commands',
    'image':'Compute/Cyclades or Glance API image commands',
    'network': 'Compute/Cyclades API network commands'}

from kamaki.cli import command
from kamaki.cli.utils import print_dict, print_items, print_list, format_size, bold
from kamaki.cli.errors import CLIError, raiseCLIError
from kamaki.clients.cyclades import CycladesClient, ClientError
from kamaki.cli.argument import FlagArgument, ValueArgument
from . import _command_init

from base64 import b64encode
from os.path import abspath, exists

class _init_cyclades(_command_init):
    def main(self, service='compute'):
        token = self.config.get(service, 'token') or self.config.get('global', 'token')
        base_url = self.config.get(service, 'url') or self.config.get('global', 'url')
        self.client = CycladesClient(base_url=base_url, token=token)

@command()
class server_list(_init_cyclades):
    """List servers"""

    def __init__(self, arguments={}):
        super(server_list, self).__init__(arguments)
        self.arguments['detail'] = FlagArgument('show detailed output', '-l')

    def _print(self, servers):
        for server in servers:
            sname = server.pop('name')
            sid = server.pop('id')
            print('%s (%s)'%(bold(sname), bold(unicode(sid))))
            if self.get_argument('detail'):
                server_info._print(server)
                print('- - -')

    def main(self):
        super(self.__class__, self).main()
        try:
            servers = self.client.list_servers(self.get_argument('detail'))
            self._print(servers)
            #print_items(servers)
        except ClientError as err:
            raiseCLIError(err)

@command()
class server_info(_init_cyclades):
    """Get server details"""

    @classmethod
    def _print(self,server):
        addr_dict = {}
        if server.has_key('attachments'):
            for addr in server['attachments']['values']:
                ips = addr.pop('values', [])
                for ip in ips:
                    addr['IPv%s'%ip['version']] = ip['addr']
                if addr.has_key('firewallProfile'):
                    addr['firewall'] = addr.pop('firewallProfile')
                addr_dict[addr.pop('id')] = addr
            server['attachments'] = addr_dict if addr_dict is not {} else None
        if server.has_key('metadata'):
            server['metadata'] = server['metadata']['values']
        print_dict(server, ident=14)

    def main(self, server_id):
        super(self.__class__, self).main()
        try:
            server = self.client.get_server_details(int(server_id))
        except ClientError as err:
            raiseCLIError(err)
        except ValueError as err:
            raise CLIError(message='Server id must be positive integer',
                importance=1)
        self._print(server)

class PersonalityArgument(ValueArgument):
    @property 
    def value(self):
        return [self._value] if hasattr(self, '_value') else []
    @value.setter 
    def value(self, newvalue):
        if newvalue == self.default:
            return self.value
        termlist = newvalue.split()
        if len(termlist) > 4:
                raise CLISyntaxError(details='Wrong number of personality terms ("PATH [OWNER [GROUP [MODE]]]"')
        path = termlist[0]
        self._value = dict(path=path)
        if not exists(path):
            raise CLIError(message="File %s does not exist" % path, importance=1)
        with open(path) as f:
            self._value['contents'] = b64encode(f.read())
        try:
            self._value['owner'] = termlist[1]
            self._value['group'] = termlist[2]
            self._value['mode'] = termlist[3]
        except IndexError:
            pass

@command()
class server_create(_init_cyclades):
    """Create a server"""

    def __init__(self, arguments={}):
        super(server_create, self).__init__(arguments)
        self.arguments['personality'] = PersonalityArgument(parsed_name='--personality',
            help='add a personality file ( "PATH [OWNER [GROUP [MODE]]]" )')

    def update_parser(self, parser):
        parser.add_argument('--personality', dest='personalities',
                          action='append', default=[],
                          metavar='PATH[,SERVER PATH[,OWNER[,GROUP,[MODE]]]]',
                          help='add a personality file')

    def main(self, name, flavor_id, image_id):
        super(self.__class__, self).main()
        try:
            reply = self.client.create_server(name, int(flavor_id), image_id,
                self.get_argument('personality'))
        except ClientError as err:
            raiseCLIError(err)
        print_dict(reply)

@command()
class server_rename(_init_cyclades):
    """Update a server's name"""

    def main(self, server_id, new_name):
        super(self.__class__, self).main()
        try:
            self.client.update_server_name(int(server_id), new_name)
        except ClientError as err:
            raiseCLIError(err)
        except ValueError:
            raise CLIError(message='Server id must be positive integer', importance=1)

@command()
class server_delete(_init_cyclades):
    """Delete a server"""

    def main(self, server_id):
        super(self.__class__, self).main()
        try:
            self.client.delete_server(int(server_id))
        except ClientError as err:
            raiseCLIError(err)
        except ValueError:
            raise CLIError(message='Server id must be positive integer', importance=1)

@command()
class server_reboot(_init_cyclades):
    """Reboot a server"""

    def __init__(self, arguments={}):
        super(server_reboot, self).__init__(arguments)
        self.arguments['hard'] = FlagArgument('perform a hard reboot', '-f')

    def main(self, server_id):
        super(self.__class__, self).main()
        try:
            self.client.reboot_server(int(server_id), self.get_argument('hard'))
        except ClientError as err:
            raiseCLIError(err)
        except ValueError:
            raise CLIError(message='Server id must be positive integer', importance=1)

@command()
class server_start(_init_cyclades):
    """Start a server"""

    def main(self, server_id):
        super(self.__class__, self).main()
        try:
            self.client.start_server(int(server_id))
        except ClientError as err:
            raiseCLIError(err)
        except ValueError:
            raise CLIError(message='Server id must be positive integer', importance=1)

@command()
class server_shutdown(_init_cyclades):
    """Shutdown a server"""

    def main(self, server_id):
        super(self.__class__, self).main()
        try:
            self.client.shutdown_server(int(server_id))
        except ClientError as err:
            raiseCLIError(err)
        except ValueError:
            raise CLIError(message='Server id must be positive integer', importance=1)

@command()
class server_console(_init_cyclades):
    """Get a VNC console"""

    def main(self, server_id):
        super(self.__class__, self).main()
        try:
            reply = self.client.get_server_console(int(server_id))
        except ClientError as err:
            raiseCLIError(err)
        except ValueError:
            raise CLIError(message='Server id must be positive integer', importance=1)
        print_dict(reply)

@command()
class server_firewall(_init_cyclades):
    """Set the server's firewall profile"""

    def main(self, server_id, profile):
        super(self.__class__, self).main()
        try:
            self.client.set_firewall_profile(int(server_id), profile)
        except ClientError as err:
            raiseCLIError(err)
        except ValueError:
            raise CLIError(message='Server id must be positive integer', importance=1)

@command()
class server_addr(_init_cyclades):
    """List a server's nic address"""

    def main(self, server_id):
        super(self.__class__, self).main()
        try:
            reply = self.client.list_server_nics(int(server_id))
        except ClientError as err:
            raiseCLIError(err)
        except ValueError:
            raise CLIError(message='Server id must be positive integer', importance=1)
        print_list(reply)

@command()
class server_meta(_init_cyclades):
    """Get a server's metadata"""

    def main(self, server_id, key=None):
        super(self.__class__, self).main()
        try:
            reply = self.client.get_server_metadata(int(server_id), key)
        except ClientError as err:
            raiseCLIError(err)
        except ValueError:
            raise CLIError(message='Server id must be positive integer', importance=1)
        print_dict(reply)

@command()
class server_addmeta(_init_cyclades):
    """Add server metadata"""

    def main(self, server_id, key, val):
        super(self.__class__, self).main()
        try:
            reply = self.client.create_server_metadata(int(server_id), key, val)
        except ClientError as err:
            raiseCLIError(err)
        except ValueError:
            raise CLIError(message='Server id must be positive integer', importance=1)
        print_dict(reply)

@command()
class server_setmeta(_init_cyclades):
    """Update server's metadata"""

    def main(self, server_id, key, val):
        super(self.__class__, self).main()
        metadata = {key: val}
        try:
            reply = self.client.update_server_metadata(int(server_id), **metadata)
        except ClientError as err:
            raiseCLIError(err)
        except ValueError:
            raise CLIError(message='Server id must be positive integer', importance=1)
        print_dict(reply)

@command()
class server_delmeta(_init_cyclades):
    """Delete server metadata"""

    def main(self, server_id, key):
        super(self.__class__, self).main()
        try:
            self.client.delete_server_metadata(int(server_id), key)
        except ClientError as err:
            raiseCLIError(err)
        except ValueError:
            raise CLIError(message='Server id must be positive integer', importance=1)

@command()
class server_stats(_init_cyclades):
    """Get server statistics"""

    def main(self, server_id):
        super(self.__class__, self).main()
        try:
            reply = self.client.get_server_stats(int(server_id))
        except ClientError as err:
            raiseCLIError(err)
        except ValueError:
            raise CLIError(message='Server id must be positive integer', importance=1)
        print_dict(reply, exclude=('serverRef',))

@command()
class flavor_list(_init_cyclades):
    """List flavors"""

    def __init__(self, arguments={}):
        super(flavor_list, self).__init__(arguments)
        self.arguments['detail'] = FlagArgument('show detailed output', '-l')

    def main(self):
        super(self.__class__, self).main()
        try:
            flavors = self.client.list_flavors(self.get_argument('detail'))
        except ClientError as err:
            raiseCLIError(err)
        print_items(flavors)

@command()
class flavor_info(_init_cyclades):
    """Get flavor details"""

    def main(self, flavor_id):
        super(self.__class__, self).main()
        try:
            flavor = self.client.get_flavor_details(int(flavor_id))
        except ClientError as err:
            raiseCLIError(err)
        except ValueError:
            raise CLIError(message='Server id must be positive integer', importance=1)
        print_dict(flavor)

@command()
class network_list(_init_cyclades):
    """List networks"""

    def __init__(self, arguments={}):
        super(network_list, self).__init__(arguments)
        self.arguments['detail'] = FlagArgument('show detailed output', '-l')

    def print_networks(self, nets):
        for net in nets:
            netname = bold(net.pop('name'))
            netid = bold(unicode(net.pop('id')))
            print('%s (%s)'%(netname, netid))
            if self.get_argument('detail'):
                network_info.print_network(net)

    def main(self):
        super(self.__class__, self).main()
        try:
            networks = self.client.list_networks(self.get_argument('detail'))
        except ClientError as err:
            raiseCLIError(err)
        self.print_networks(networks)

@command()
class network_create(_init_cyclades):
    """Create a network"""

    def __init__(self, arguments={}):
        super(network_create, self).__init__(arguments)
        self.arguments['cidr'] = ValueArgument('specific cidr for new network', '--with-cidr')
        self.arguments['gateway'] = ValueArgument('specific gateway for new network',
            '--with-gateway')
        self.arguments['dhcp'] = ValueArgument('specific dhcp for new network', '--with-dhcp')
        self.arguments['type'] = ValueArgument('specific type for new network', '--with-type')

    def main(self, name):
        super(self.__class__, self).main()
        try:
            reply = self.client.create_network(name, cidr= self.get_argument('cidr'),
                gateway=self.get_argument('gateway'), dhcp=self.get_argument('dhcp'),
                type=self.get_argument('type'))
        except ClientError as err:
            raiseCLIError(err)
        print_dict(reply)

@command()
class network_info(_init_cyclades):
    """Get network details"""

    @classmethod
    def print_network(self, net):
        if net.has_key('attachments'):
            att = net['attachments']['values']
            net['attachments'] = att if len(att) > 0 else None
        print_dict(net, ident=14)

    def main(self, network_id):
        super(self.__class__, self).main()
        try:
            network = self.client.get_network_details(network_id)
        except ClientError as err:
            raiseCLIError(err)
        network_info.print_network(network)

@command()
class network_rename(_init_cyclades):
    """Update network name"""

    def main(self, network_id, new_name):
        super(self.__class__, self).main()
        try:
            self.client.update_network_name(network_id, new_name)
        except ClientError as err:
            raiseCLIError(err)

@command()
class network_delete(_init_cyclades):
    """Delete a network"""

    def main(self, network_id):
        super(self.__class__, self).main()
        try:
            self.client.delete_network(network_id)
        except ClientError as err:
            raiseCLIError(err)

@command()
class network_connect(_init_cyclades):
    """Connect a server to a network"""

    def main(self, server_id, network_id):
        super(self.__class__, self).main()
        try:
            self.client.connect_server(server_id, network_id)
        except ClientError as err:
            raiseCLIError(err)

@command()
class network_disconnect(_init_cyclades):
    """Disconnect a nic that connects a server to a network"""

    def main(self, nic_id):
        super(self.__class__, self).main()
        try:
            server_id = nic_id.split('-')[1]
            self.client.disconnect_server(server_id, nic_id)
        except IndexError:
            raise CLIError(message='Incorrect nic format', importance=1,
                details='nid_id format: nic-<server_id>-<nic_index>')
        except ClientError as err:
            raiseCLIError(err)
