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

from kamaki.cli import command
from kamaki.cli.command_tree import CommandTree
from kamaki.cli.utils import print_dict, print_list, bold
from kamaki.cli.errors import CLIError, raiseCLIError, CLISyntaxError
from kamaki.clients.cyclades import CycladesClient, ClientError
from kamaki.cli.argument import FlagArgument, ValueArgument, KeyValueArgument
from kamaki.cli.argument import ProgressBarArgument
from kamaki.cli.commands import _command_init

from base64 import b64encode
from os.path import exists


server_cmds = CommandTree('server',
    'Compute/Cyclades API server commands')
flavor_cmds = CommandTree('flavor',
    'Compute/Cyclades API flavor commands')
image_cmds = CommandTree('image',
    'Compute/Cyclades or Glance API image commands')
network_cmds = CommandTree('network',
    'Compute/Cyclades API network commands')
_commands = [server_cmds, flavor_cmds, image_cmds, network_cmds]


class _init_cyclades(_command_init):
    def main(self, service='compute'):
        token = self.config.get(service, 'token')\
            or self.config.get('global', 'token')
        base_url = self.config.get(service, 'url')\
            or self.config.get('global', 'url')
        self.client = CycladesClient(base_url=base_url, token=token)


@command(server_cmds)
class server_list(_init_cyclades):
    """List servers"""

    def __init__(self, arguments={}):
        super(server_list, self).__init__(arguments)
        self.arguments['detail'] = FlagArgument('show detailed output', '-l')

    def _info_print(self, server):
        addr_dict = {}
        if 'attachments' in server:
            for addr in server['attachments']['values']:
                ips = addr.pop('values', [])
                for ip in ips:
                    addr['IPv%s' % ip['version']] = ip['addr']
                if 'firewallProfile' in addr:
                    addr['firewall'] = addr.pop('firewallProfile')
                addr_dict[addr.pop('id')] = addr
            server['attachments'] = addr_dict if addr_dict is not {} else None
        if 'metadata' in server:
            server['metadata'] = server['metadata']['values']
        print_dict(server, ident=2)

    def _print(self, servers):
        for server in servers:
            sname = server.pop('name')
            sid = server.pop('id')
            print('%s (%s)' % (sid, bold(sname)))
            if self.get_argument('detail'):
                self._info_print(server)
                print(' ')

    def main(self):
        super(self.__class__, self).main()
        try:
            servers = self.client.list_servers(self.get_argument('detail'))
            self._print(servers)
        except ClientError as err:
            raiseCLIError(err)


@command(server_cmds)
class server_info(_init_cyclades):
    """Get server details"""

    @classmethod
    def _print(self, server):
        addr_dict = {}
        if 'attachments' in server:
            atts = server.pop('attachments')
            for addr in atts['values']:
                ips = addr.pop('values', [])
                for ip in ips:
                    addr['IPv%s' % ip['version']] = ip['addr']
                if 'firewallProfile' in addr:
                    addr['firewall'] = addr.pop('firewallProfile')
                addr_dict[addr.pop('id')] = addr
            server['attachments'] = addr_dict if addr_dict else None
        if 'metadata' in server:
            server['metadata'] = server['metadata']['values']
        print_dict(server, ident=2)

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


class PersonalityArgument(KeyValueArgument):
    @property
    def value(self):
        return self._value if hasattr(self, '_value') else []

    @value.setter
    def value(self, newvalue):
        if newvalue == self.default:
            return self.value
        self._value = []
        for i, terms in enumerate(newvalue):
            termlist = terms.split(',')
            if len(termlist) > 5:
                raise CLISyntaxError(details='Wrong number of terms'\
                + ' ("PATH,[SERVER_PATH,[OWNER,[GROUP,[MODE]]]]"')
            path = termlist[0]
            if not exists(path):
                raise CLIError(message="File %s does not exist" % path,
                importance=1)
            self._value.append(dict(path=path))
            with open(path) as f:
                self._value[i]['contents'] = b64encode(f.read())
            try:
                self._value[i]['path'] = termlist[1]
                self._value[i]['owner'] = termlist[2]
                self._value[i]['group'] = termlist[3]
                self._value[i]['mode'] = termlist[4]
            except IndexError:
                pass


@command(server_cmds)
class server_create(_init_cyclades):
    """Create a server"""

    def __init__(self, arguments={}):
        super(server_create, self).__init__(arguments)
        self.arguments['personality'] = PersonalityArgument(\
            'add a personality file ( ' +\
            '"PATH,[SERVER_PATH,[OWNER,[GROUP,[MODE]]]]" )',
            parsed_name='--personality')

    def main(self, name, flavor_id, image_id):
        super(self.__class__, self).main()

        try:
            reply = self.client.create_server(name,
                int(flavor_id),
                image_id,
                self.get_argument('personality'))
        except ClientError as err:
            raiseCLIError(err)
        except ValueError as err:
            raise CLIError('Invalid flavor id %s ' % flavor_id,
                details='Flavor id must be a positive integer',
                importance=1)
        except Exception as err:
            raise CLIError('Syntax error: %s\n' % err, importance=1)
        print_dict(reply)


@command(server_cmds)
class server_rename(_init_cyclades):
    """Update a server's name"""

    def main(self, server_id, new_name):
        super(self.__class__, self).main()
        try:
            self.client.update_server_name(int(server_id), new_name)
        except ClientError as err:
            raiseCLIError(err)
        except ValueError:
            raise CLIError('Invalid server id %s ' % server_id,
                details='Server id must be positive integer\n',
                importance=1)


@command(server_cmds)
class server_delete(_init_cyclades):
    """Delete a server"""

    def main(self, server_id):
        super(self.__class__, self).main()
        try:
            self.client.delete_server(int(server_id))
        except ClientError as err:
            raiseCLIError(err)
        except ValueError:
            raise CLIError(message='Server id must be positive integer',
                importance=1)


@command(server_cmds)
class server_reboot(_init_cyclades):
    """Reboot a server"""

    def __init__(self, arguments={}):
        super(server_reboot, self).__init__(arguments)
        self.arguments['hard'] = FlagArgument('perform a hard reboot', '-f')

    def main(self, server_id):
        super(self.__class__, self).main()
        try:
            self.client.reboot_server(int(server_id),
                self.get_argument('hard'))
        except ClientError as err:
            raiseCLIError(err)
        except ValueError:
            raise CLIError(message='Server id must be positive integer',
                importance=1)


@command(server_cmds)
class server_start(_init_cyclades):
    """Start a server"""

    def main(self, server_id):
        super(self.__class__, self).main()
        try:
            self.client.start_server(int(server_id))
        except ClientError as err:
            raiseCLIError(err)
        except ValueError:
            raise CLIError(message='Server id must be positive integer',
                importance=1)


@command(server_cmds)
class server_shutdown(_init_cyclades):
    """Shutdown a server"""

    def main(self, server_id):
        super(self.__class__, self).main()
        try:
            self.client.shutdown_server(int(server_id))
        except ClientError as err:
            raiseCLIError(err)
        except ValueError:
            raise CLIError(message='Server id must be positive integer',
                importance=1)


@command(server_cmds)
class server_console(_init_cyclades):
    """Get a VNC console"""

    def main(self, server_id):
        super(self.__class__, self).main()
        try:
            reply = self.client.get_server_console(int(server_id))
        except ClientError as err:
            raiseCLIError(err)
        except ValueError:
            raise CLIError(message='Server id must be positive integer',
                importance=1)
        print_dict(reply)


@command(server_cmds)
class server_firewall(_init_cyclades):
    """Set the server's firewall profile"""

    def main(self, server_id, profile):
        super(self.__class__, self).main()
        try:
            self.client.set_firewall_profile(int(server_id), profile)
        except ClientError as err:
            raiseCLIError(err)
        except ValueError:
            raise CLIError(message='Server id must be positive integer',
                importance=1)


@command(server_cmds)
class server_addr(_init_cyclades):
    """List a server's nic address"""

    def main(self, server_id):
        super(self.__class__, self).main()
        try:
            reply = self.client.list_server_nics(int(server_id))
        except ClientError as err:
            raiseCLIError(err)
        except ValueError:
            raise CLIError(message='Server id must be positive integer',
                importance=1)
        print_list(reply)


@command(server_cmds)
class server_meta(_init_cyclades):
    """Get a server's metadata"""

    def main(self, server_id, key=''):
        super(self.__class__, self).main()
        try:
            reply = self.client.get_server_metadata(int(server_id), key)
        except ValueError:
            raise CLIError(message='Server id must be positive integer',
                importance=1)
        except ClientError as err:
            raiseCLIError(err)
        print_dict(reply)


@command(server_cmds)
class server_addmeta(_init_cyclades):
    """Add server metadata"""

    def main(self, server_id, key, val):
        super(self.__class__, self).main()
        try:
            reply = self.client.create_server_metadata(\
                int(server_id), key, val)
        except ClientError as err:
            raiseCLIError(err)
        except ValueError:
            raise CLIError(message='Server id must be positive integer',
                importance=1)
        print_dict(reply)


@command(server_cmds)
class server_setmeta(_init_cyclades):
    """Update server's metadata"""

    def main(self, server_id, key, val):
        super(self.__class__, self).main()
        metadata = {key: val}
        try:
            reply = self.client.update_server_metadata(int(server_id),
                **metadata)
        except ClientError as err:
            raiseCLIError(err)
        except ValueError:
            raise CLIError(message='Server id must be positive integer',
                importance=1)
        print_dict(reply)


@command(server_cmds)
class server_delmeta(_init_cyclades):
    """Delete server metadata"""

    def main(self, server_id, key):
        super(self.__class__, self).main()
        try:
            self.client.delete_server_metadata(int(server_id), key)
        except ClientError as err:
            raiseCLIError(err)
        except ValueError:
            raise CLIError(message='Server id must be positive integer',
                importance=1)


@command(server_cmds)
class server_stats(_init_cyclades):
    """Get server statistics"""

    def main(self, server_id):
        super(self.__class__, self).main()
        try:
            reply = self.client.get_server_stats(int(server_id))
        except ClientError as err:
            raiseCLIError(err)
        except ValueError:
            raise CLIError(message='Server id must be positive integer',
                importance=1)
        print_dict(reply, exclude=('serverRef',))


@command(server_cmds)
class server_wait(_init_cyclades):
    """Wait for server to finish [BUILD, STOPPED, REBOOT, ACTIVE]"""

    def __init__(self, arguments={}):
        super(self.__class__, self).__init__(arguments)
        self.arguments['progress_bar'] = ProgressBarArgument(\
            'do not show progress bar', '--no-progress-bar', False)

    def main(self, server_id, currect_status='BUILD'):
        super(self.__class__, self).main()
        try:
            progress_bar = self.arguments['progress_bar']
            wait_cb = progress_bar.get_generator(\
                'Server %s still in %s mode' % (server_id, currect_status))
        except Exception:
            wait_cb = None
        try:
            new_mode = self.client.wait_server(server_id,
                currect_status,
                wait_cb=wait_cb)
            progress_bar.finish()
        except KeyboardInterrupt:
            print('\nCanceled')
            progress_bar.finish()
            return
        except ClientError as err:
            progress_bar.finish()
            raiseCLIError(err)
        if new_mode:
            print('\nServer %s is now in %s mode' % (server_id, new_mode))
        else:
            print('\nTime out')


@command(flavor_cmds)
class flavor_list(_init_cyclades):
    """List flavors"""

    def __init__(self, arguments={}):
        super(flavor_list, self).__init__(arguments)
        self.arguments['detail'] = FlagArgument('show detailed output', '-l')

    @classmethod
    def _print(self, flist):
        for i, flavor in enumerate(flist):
            print(bold('%s. %s' % (i, flavor['name'])))
            print_dict(flavor, exclude=('name'), ident=2)
            print(' ')

    def main(self):
        super(self.__class__, self).main()
        try:
            flavors = self.client.list_flavors(self.get_argument('detail'))
        except ClientError as err:
            raiseCLIError(err)
        #print_list(flavors)
        self._print(flavors)


@command(flavor_cmds)
class flavor_info(_init_cyclades):
    """Get flavor details"""

    def main(self, flavor_id):
        super(self.__class__, self).main()
        try:
            flavor = self.client.get_flavor_details(int(flavor_id))
        except ClientError as err:
            raiseCLIError(err)
        except ValueError:
            raise CLIError(message='Server id must be positive integer',
                importance=1)
        print_dict(flavor)


@command(network_cmds)
class network_list(_init_cyclades):
    """List networks"""

    def __init__(self, arguments={}):
        super(network_list, self).__init__(arguments)
        self.arguments['detail'] = FlagArgument('show detailed output', '-l')

    def print_networks(self, nets):
        for net in nets:
            netname = bold(net.pop('name'))
            netid = bold(unicode(net.pop('id')))
            print('%s (%s)' % (netid, netname))
            if self.get_argument('detail'):
                network_info.print_network(net)

    def main(self):
        super(self.__class__, self).main()
        try:
            networks = self.client.list_networks(self.get_argument('detail'))
        except ClientError as err:
            raiseCLIError(err)
        self.print_networks(networks)


@command(network_cmds)
class network_create(_init_cyclades):
    """Create a network"""

    def __init__(self, arguments={}):
        super(network_create, self).__init__(arguments)
        self.arguments['cidr'] =\
            ValueArgument('specific cidr for new network', '--with-cidr')
        self.arguments['gateway'] =\
            ValueArgument('specific gateway for new network', '--with-gateway')
        self.arguments['dhcp'] =\
            ValueArgument('specific dhcp for new network', '--with-dhcp')
        self.arguments['type'] =\
            ValueArgument('specific type for new network', '--with-type')

    def main(self, name):
        super(self.__class__, self).main()
        try:
            reply = self.client.create_network(name,
                cidr=self.get_argument('cidr'),
                gateway=self.get_argument('gateway'),
                dhcp=self.get_argument('dhcp'),
                type=self.get_argument('type'))
        except ClientError as err:
            raiseCLIError(err)
        print_dict(reply)


@command(network_cmds)
class network_info(_init_cyclades):
    """Get network details"""

    @classmethod
    def print_network(self, net):
        if 'attachments' in net:
            att = net['attachments']['values']
            net['attachments'] = att if len(att) > 0 else None
        print_dict(net, ident=2)

    def main(self, network_id):
        super(self.__class__, self).main()
        try:
            network = self.client.get_network_details(network_id)
        except ClientError as err:
            raiseCLIError(err)
        network_info.print_network(network)


@command(network_cmds)
class network_rename(_init_cyclades):
    """Update network name"""

    def main(self, network_id, new_name):
        super(self.__class__, self).main()
        try:
            self.client.update_network_name(network_id, new_name)
        except ClientError as err:
            raiseCLIError(err)


@command(network_cmds)
class network_delete(_init_cyclades):
    """Delete a network"""

    def main(self, network_id):
        super(self.__class__, self).main()
        try:
            self.client.delete_network(network_id)
        except ClientError as err:
            raiseCLIError(err)


@command(network_cmds)
class network_connect(_init_cyclades):
    """Connect a server to a network"""

    def main(self, server_id, network_id):
        super(self.__class__, self).main()
        try:
            self.client.connect_server(server_id, network_id)
        except ClientError as err:
            raiseCLIError(err)


@command(network_cmds)
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
