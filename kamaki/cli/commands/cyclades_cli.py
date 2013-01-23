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

from kamaki.cli import command
from kamaki.cli.command_tree import CommandTree
from kamaki.cli.utils import print_dict, print_list, print_items
from kamaki.cli.errors import raiseCLIError, CLISyntaxError
from kamaki.clients.cyclades import CycladesClient, ClientError
from kamaki.cli.argument import FlagArgument, ValueArgument, KeyValueArgument
from kamaki.cli.argument import ProgressBarArgument, DateArgument, IntArgument
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


about_authentication = '\n  User Authentication:\
    \n    to check authentication: /astakos authenticate\
    \n    to set authentication token: /config set token <token>'

howto_personality = [
    'Defines a file to be injected to VMs personality.',
    'Personality value syntax: PATH,[SERVER_PATH,[OWNER,[GROUP,[MODE]]]]',
    '  PATH: of local file to be injected',
    '  SERVER_PATH: destination location inside server Image',
    '  OWNER: user id of destination file owner',
    '  GROUP: group id or name to own destination file',
    '  MODEL: permition in octal (e.g. 0777 or o+rwx)']


def raise_if_connection_error(err, base_url='compute.url'):
    if err.status == 401:
        raiseCLIError(err, 'Authorization failed', details=[
            'Make sure a valid token is provided:',
            '  to check if the token is valid: /astakos authenticate',
            '  to set a token: /config set [.server.]token <token>',
            '  to get current token: /config get [server.]token'])
    elif err.status in range(-12, 200) + [403, 500]:
        raiseCLIError(err, details=[
            'Check if service is up or set to %s' % base_url,
            '  to get service url: /config get %s' % base_url,
            '  to set service url: /config set %s <URL>' % base_url]
        )


class _init_cyclades(_command_init):
    def main(self, service='compute'):
        token = self.config.get(service, 'token')\
            or self.config.get('global', 'token')
        base_url = self.config.get(service, 'url')\
            or self.config.get('global', 'url')
        self.client = CycladesClient(base_url=base_url, token=token)


@command(server_cmds)
class server_list(_init_cyclades):
    """List Virtual Machines accessible by user
    """

    __doc__ += about_authentication

    arguments = dict(
        detail=FlagArgument('show detailed output', '-l'),
        since=DateArgument(
            'show only items since date (\' d/m/Y H:M:S \')',
            '--since'),
        limit=IntArgument('limit the number of VMs to list', '-n'),
        more=FlagArgument(
            'output results in pages (-n to set items per page, default 10)',
            '--more')
    )

    def _make_results_pretty(self, servers):
        for server in servers:
            addr_dict = {}
            if 'attachments' in server:
                for addr in server['attachments']['values']:
                    ips = addr.pop('values', [])
                    for ip in ips:
                        addr['IPv%s' % ip['version']] = ip['addr']
                    if 'firewallProfile' in addr:
                        addr['firewall'] = addr.pop('firewallProfile')
                    addr_dict[addr.pop('id')] = addr
                server['attachments'] = addr_dict if addr_dict else None
            if 'metadata' in server:
                server['metadata'] = server['metadata']['values']

    def main(self):
        super(self.__class__, self).main()
        try:
            servers = self.client.list_servers(self['detail'], self['since'])
            if self['detail']:
                self._make_results_pretty(servers)
        except ClientError as ce:
            if ce.status == 400 and 'changes-since' in ('%s' % ce):
                raiseCLIError(None,
                    'Incorrect date format for --since',
                    details=['Accepted date format: d/m/y'])
            raise_if_connection_error(ce)
            raiseCLIError(ce)
        except Exception as err:
            raiseCLIError(err)
        if self['more']:
            print_items(
                servers,
                page_size=self['limit'] if self['limit'] else 10)
        else:
            print_items(
                servers[:self['limit'] if self['limit'] else len(servers)])


@command(server_cmds)
class server_info(_init_cyclades):
    """Detailed information on a Virtual Machine
    Contains:
    - name, id, status, create/update dates
    - network interfaces
    - metadata (e.g. os, superuser) and diagnostics
    - hardware flavor and os image ids
    """

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
        print_dict(server, ident=1)

    def main(self, server_id):
        super(self.__class__, self).main()
        try:
            server = self.client.get_server_details(int(server_id))
        except ValueError as err:
            raiseCLIError(err, 'Server id must be a positive integer', 1)
        except ClientError as ce:
            if ce.status == 404:
                raiseCLIError(ce, 'Server with id %s not found' % server_id)
            raise_if_connection_error(ce)
            raiseCLIError(ce)
        except Exception as err:
            raiseCLIError(err)
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
                raiseCLIError(
                CLISyntaxError('Wrong number of terms (should be 1 to 5)'),
                details=howto_personality)
            path = termlist[0]
            if not exists(path):
                raiseCLIError(None,
                    '--personality: File %s does not exist' % path,
                    importance=1,
                    details=howto_personality)
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
    """Create a server (aka Virtual Machine)
    Parameters:
    - name: (single quoted text)
    - flavor id: Hardware flavor. Pick one from: /flavor list
    - image id: OS images. Pick one from: /image list
    """

    arguments = dict(
        personality=PersonalityArgument(
            ' _ _ _ '.join(howto_personality),
            parsed_name='--personality')
    )

    def main(self, name, flavor_id, image_id):
        super(self.__class__, self).main()

        try:
            reply = self.client.create_server(
                        name,
                        int(flavor_id),
                        image_id,
                        self['personality']
                    )
        except ClientError as ce:
            if ce.status == 404:
                msg = ('%s' % ce).lower()
                if 'flavor' in msg:
                    raiseCLIError(ce,
                        'Flavor id %s not found' % flavor_id,
                        details=['How to pick a valid flavor id:',
                        '  - get a list of flavor ids: /flavor list',
                        '  - details on a flavor: /flavor info <flavor id>'])
                elif 'image' in msg:
                    raiseCLIError(ce,
                        'Image id %s not found' % image_id,
                        details=['How to pick a valid image id:',
                        '  - get a list of image ids: /image list',
                        '  - details on an image: /image info <image id>'])
            raise_if_connection_error(ce)
            raiseCLIError(ce)
        except ValueError as err:
            raiseCLIError(err, 'Invalid flavor id %s ' % flavor_id,
                details='Flavor id must be a positive integer',
                importance=1)
        except Exception as err:
            raiseCLIError(err, 'Syntax error: %s\n' % err, importance=1)
        print_dict(reply)


@command(server_cmds)
class server_rename(_init_cyclades):
    """Set/update a server (VM) name
    VM names are not unique, therefore multiple server may share the same name
    """

    def main(self, server_id, new_name):
        super(self.__class__, self).main()
        try:
            self.client.update_server_name(int(server_id), new_name)
        except ClientError as ce:
            if ce.status == 404:
                raiseCLIError(ce, 'Server with id %s not found' % server_id)
            raise_if_connection_error(ce)
            raiseCLIError(ce)
        except ValueError as err:
            raiseCLIError(err, 'Invalid server id %s ' % server_id,
                details=['Server id must be positive integer\n'],
                importance=1)


@command(server_cmds)
class server_delete(_init_cyclades):
    """Delete a server (VM)"""

    def main(self, server_id):
        super(self.__class__, self).main()
        try:
            self.client.delete_server(int(server_id))
        except ClientError as ce:
            if ce.status == 404:
                raiseCLIError(ce, 'Server with id %s not found' % server_id)
            raise_if_connection_error(ce)
            raiseCLIError(ce)
        except ValueError as err:
            raiseCLIError(err, 'Invalid server id %s ' % server_id,
                details=['Server id must be positive integer\n'],
                importance=1)
        except Exception as err:
            raiseCLIError(err)


@command(server_cmds)
class server_reboot(_init_cyclades):
    """Reboot a server (VM)"""

    arguments = dict(
        hard=FlagArgument('perform a hard reboot', '-f')
    )

    def main(self, server_id):
        super(self.__class__, self).main()
        try:
            self.client.reboot_server(int(server_id), self['hard'])
        except ClientError as ce:
            if ce.status == 404:
                raiseCLIError(ce, 'Server with id %s not found' % server_id)
            raise_if_connection_error(ce)
            raiseCLIError(ce)
        except ValueError as err:
            raiseCLIError(err, 'Invalid server id %s ' % server_id,
                details=['Server id must be positive integer\n'],
                importance=1)
        except Exception as err:
            raiseCLIError(err)


@command(server_cmds)
class server_start(_init_cyclades):
    """Start an existing server (VM)"""

    def main(self, server_id):
        super(self.__class__, self).main()
        try:
            self.client.start_server(int(server_id))
        except ClientError as ce:
            if ce.status == 404:
                raiseCLIError(ce, 'Server with id %s not found' % server_id)
            raise_if_connection_error(ce)
            raiseCLIError(ce)
        except ValueError as err:
            raiseCLIError(err, 'Invalid server id %s ' % server_id,
                details=['Server id must be positive integer\n'],
                importance=1)
        except Exception as err:
            raiseCLIError(err)


@command(server_cmds)
class server_shutdown(_init_cyclades):
    """Shutdown an active server (VM)"""

    def main(self, server_id):
        super(self.__class__, self).main()
        try:
            self.client.shutdown_server(int(server_id))
        except ClientError as ce:
            if ce.status == 404:
                raiseCLIError(ce, 'Server with id %s not found' % server_id)
            raise_if_connection_error(ce)
            raiseCLIError(ce)
        except ValueError as err:
            raiseCLIError(err, 'Invalid server id %s ' % server_id,
                details=['Server id must be positive integer\n'],
                importance=1)
        except Exception as err:
            raiseCLIError(err)


@command(server_cmds)
class server_console(_init_cyclades):
    """Get a VNC console to access an existing server (VM)
    Console connection information provided (at least):
    - host: (url or address) a VNC host
    - port: (int) the gateway to enter VM on host
    - password: for VNC authorization
    """

    def main(self, server_id):
        super(self.__class__, self).main()
        try:
            reply = self.client.get_server_console(int(server_id))
        except ClientError as ce:
            if ce.status == 404:
                raiseCLIError(ce, 'Server with id %s not found' % server_id)
            raise_if_connection_error(ce)
            raiseCLIError(ce)
        except ValueError as err:
            raiseCLIError(err, 'Invalid server id %s ' % server_id,
                details=['Server id must be positive integer\n'],
                importance=1)
        except Exception as err:
            raiseCLIError(err)
        print_dict(reply)


@command(server_cmds)
class server_firewall(_init_cyclades):
    """Set the server (VM) firewall profile on VMs public network
    Values for profile:
    - DISABLED: Shutdown firewall
    - ENABLED: Firewall in normal mode
    - PROTECTED: Firewall in secure mode
    """

    def main(self, server_id, profile):
        super(self.__class__, self).main()
        try:
            self.client.set_firewall_profile(
                int(server_id),
                unicode(profile).upper())
        except ClientError as ce:
            if ce.status == 400 and 'firewall' in '%s' % ce:
                raiseCLIError(ce,
                    '%s is an unsupported firewall profile' % profile)
            elif ce.status == 404:
                raiseCLIError(ce, 'Server with id %s not found' % server_id)
            raise_if_connection_error(ce)
            raiseCLIError(ce)
        except ValueError as err:
            raiseCLIError(err, 'Invalid server id %s ' % server_id,
                details=['Server id must be positive integer\n'],
                importance=1)
        except Exception as err:
            raiseCLIError(err)


@command(server_cmds)
class server_addr(_init_cyclades):
    """List the addresses of all network interfaces on a server (VM)"""

    def main(self, server_id):
        super(self.__class__, self).main()
        try:
            reply = self.client.list_server_nics(int(server_id))
        except ClientError as ce:
            if ce.status == 404:
                raiseCLIError(ce, 'Server with id %s not found' % server_id)
            raise_if_connection_error(ce)
            raiseCLIError(ce)
        except ValueError as err:
            raiseCLIError(err, 'Invalid server id %s ' % server_id,
                details=['Server id must be positive integer\n'],
                importance=1)
        except Exception as err:
            raiseCLIError(err)
        print_list(reply, with_enumeration=len(reply) > 1)


@command(server_cmds)
class server_meta(_init_cyclades):
    """Get a server's metadatum
    Metadata are formed as key:value pairs where key is used to retrieve them
    """

    def main(self, server_id, key=''):
        super(self.__class__, self).main()
        try:
            reply = self.client.get_server_metadata(int(server_id), key)
        except ClientError as ce:
            if ce.status == 404:
                msg = 'No metadata with key %s' % key\
                if 'Metadata' in '%s' % ce\
                else 'Server with id %s not found' % server_id
                raiseCLIError(ce, msg)
            raise_if_connection_error(ce)
            raiseCLIError(ce)
        except ValueError as err:
            raiseCLIError(err, 'Invalid server id %s ' % server_id,
                details=['Server id must be positive integer\n'],
                importance=1)
        except Exception as err:
            raiseCLIError(err)
        print_dict(reply)


@command(server_cmds)
class server_setmeta(_init_cyclades):
    """set server (VM) metadata
    Metadata are formed as key:value pairs, both needed to set one
    """

    def main(self, server_id, key, val):
        super(self.__class__, self).main()
        metadata = {key: val}
        try:
            reply = self.client.update_server_metadata(int(server_id),
                **metadata)
        except ClientError as ce:
            if ce.status == 404:
                raiseCLIError(ce, 'Server with id %s not found' % server_id)
            raise_if_connection_error(ce)
            raiseCLIError(ce)
        except ValueError as err:
            raiseCLIError(err, 'Invalid server id %s ' % server_id,
                details=['Server id must be positive integer\n'],
                importance=1)
        except Exception as err:
            raiseCLIError(err)
        print_dict(reply)


@command(server_cmds)
class server_delmeta(_init_cyclades):
    """Delete server (VM) metadata"""

    def main(self, server_id, key):
        super(self.__class__, self).main()
        try:
            self.client.delete_server_metadata(int(server_id), key)
        except ClientError as ce:
            if ce.status == 404:
                msg = 'No metadata with key %s' % key\
                if 'Metadata' in '%s' % ce\
                else 'Server with id %s not found' % server_id
                raiseCLIError(ce, msg)
            raise_if_connection_error(ce)
            raiseCLIError(ce)
        except ValueError as err:
            raiseCLIError(err, 'Invalid server id %s ' % server_id,
                details=['Server id must be positive integer\n'],
                importance=1)
        except Exception as err:
            raiseCLIError(err)


@command(server_cmds)
class server_stats(_init_cyclades):
    """Get server (VM) statistics"""

    def main(self, server_id):
        super(self.__class__, self).main()
        try:
            reply = self.client.get_server_stats(int(server_id))
        except ClientError as ce:
            if ce.status == 404:
                raiseCLIError(ce, 'Server with id %s not found' % server_id)
            raise_if_connection_error(ce)
            raiseCLIError(ce)
        except ValueError as err:
            raiseCLIError(err, 'Invalid server id %s ' % server_id,
                details=['Server id must be positive integer\n'],
                importance=1)
        except Exception as err:
            raiseCLIError(err)
        print_dict(reply, exclude=('serverRef',))


@command(server_cmds)
class server_wait(_init_cyclades):
    """Wait for server to finish [BUILD, STOPPED, REBOOT, ACTIVE]"""

    arguments = dict(
        progress_bar=ProgressBarArgument(
            'do not show progress bar',
            '--no-progress-bar',
            False
        )
    )

    def main(self, server_id, currect_status='BUILD'):
        super(self.__class__, self).main()
        try:
            progress_bar = self.arguments['progress_bar']
            wait_cb = progress_bar.get_generator(\
                'Server %s still in %s mode' % (server_id, currect_status))
        except ValueError as err:
            raiseCLIError(err, 'Invalid server id %s ' % server_id,
                details=['Server id must be positive integer\n'],
                importance=1)
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
        except ClientError as ce:
            progress_bar.finish()
            if ce.status == 404:
                raiseCLIError(ce, 'Server with id %s not found' % server_id)
            raise_if_connection_error(ce)
            raiseCLIError(ce)
        if new_mode:
            print('Server %s is now in %s mode' % (server_id, new_mode))
        else:
            raiseCLIError(None, 'Time out')


@command(flavor_cmds)
class flavor_list(_init_cyclades):
    """List available hardware flavors"""

    arguments = dict(
        detail=FlagArgument('show detailed output', '-l'),
        limit=IntArgument('limit the number of flavors to list', '-n'),
        more=FlagArgument(
        'output results in pages (-n to set items per page, default 10)',
        '--more')
    )

    def main(self):
        super(self.__class__, self).main()
        try:
            flavors = self.client.list_flavors(self['detail'])
        except ClientError as ce:
            raise_if_connection_error(ce)
            raiseCLIError(ce)
        except Exception as err:
            raiseCLIError(err)
        if self['more']:
            print_items(
                flavors,
                with_redundancy=self['detail'],
                page_size=self['limit'] if self['limit'] else 10)
        else:
            print_items(
                flavors,
                with_redundancy=self['detail'],
                page_size=self['limit'])


@command(flavor_cmds)
class flavor_info(_init_cyclades):
    """Detailed information on a hardware flavor
    To get a list of available flavors and flavor ids, try /flavor list
    """

    def main(self, flavor_id):
        super(self.__class__, self).main()
        try:
            flavor = self.client.get_flavor_details(int(flavor_id))
        except ClientError as ce:
            raise_if_connection_error(ce)
            raiseCLIError(ce)
        except ValueError as err:
            raiseCLIError(err,
                'Invalid flavor id %s' % flavor_id,
                importance=1,
                details=['Flavor id must be possitive integer'])
        except Exception as err:
            raiseCLIError(err)
        print_dict(flavor)


@command(network_cmds)
class network_info(_init_cyclades):
    """Detailed information on a network
    To get a list of available networks and network ids, try /network list
    """

    @classmethod
    def _make_result_pretty(self, net):
        if 'attachments' in net:
            att = net['attachments']['values']
            count = len(att)
            net['attachments'] = att if count else None

    def main(self, network_id):
        super(self.__class__, self).main()
        try:
            network = self.client.get_network_details(int(network_id))
            self._make_result_pretty(network)
        except ClientError as ce:
            raise_if_connection_error(ce)
            if ce.status == 404:
                raiseCLIError(ce,
                    'No network found with id %s' % network_id,
                    details=['To see a detailed list of available network ids',
                    ' try /network list'])
            raiseCLIError(ce)
        except ValueError as ve:
            raiseCLIError(ve,
                'Invalid network_id %s' % network_id,
                importance=1,
                details=['Network id must be a possitive integer'])
        except Exception as err:
            raiseCLIError(err)
        print_dict(network)


@command(network_cmds)
class network_list(_init_cyclades):
    """List networks"""

    arguments = dict(
        detail=FlagArgument('show detailed output', '-l'),
        limit=IntArgument('limit the number of networks in list', '-n'),
        more=FlagArgument(
            'output results in pages (-n to set items per page, default 10)',
            '--more')
    )

    def _make_results_pretty(self, nets):
        for net in nets:
            network_info._make_result_pretty(net)

    def main(self):
        super(self.__class__, self).main()
        try:
            networks = self.client.list_networks(self['detail'])
            if self['detail']:
                self._make_results_pretty(networks)
        except ClientError as ce:
            raise_if_connection_error(ce)
            if ce.status == 404:
                raiseCLIError(ce,
                    'No networks found on server %s' % self.client.base_url,
                    details=[
                    'Please, check if service url is correctly set',
                    '  to get current service url: /config get compute.url',
                    '  to set service url: /config set compute.url <URL>'])
            raiseCLIError(ce)
        except Exception as err:
            raiseCLIError(err)
        if self['more']:
            print_items(networks,
                page_size=self['limit'] if self['limit'] else 10)
        elif self['limit']:
            print_items(networks[:self['limit']])
        else:
            print_items(networks)


@command(network_cmds)
class network_create(_init_cyclades):
    """Create an (unconnected) network"""

    arguments = dict(
        cidr=ValueArgument('explicitly set cidr', '--with-cidr'),
        gateway=ValueArgument('explicitly set gateway', '--with-gateway'),
        dhcp=ValueArgument('explicitly set dhcp', '--with-dhcp'),
        type=ValueArgument('explicitly set type', '--with-type')
    )

    def main(self, name):
        super(self.__class__, self).main()
        try:
            reply = self.client.create_network(name,
                cidr=self['cidr'],
                gateway=self['gateway'],
                dhcp=self['dhcp'],
                type=self['type'])
        except ClientError as ce:
            raise_if_connection_error(ce)
            if ce.status == 413:
                raiseCLIError(ce,
                    'Cannot create another network',
                    details=['Maximum number of networks reached'])
            raiseCLIError(ce)
        except Exception as err:
            raiseCLIError(err)
        print_items([reply])


@command(network_cmds)
class network_rename(_init_cyclades):
    """Set the name of a network"""

    def main(self, network_id, new_name):
        super(self.__class__, self).main()
        try:
            self.client.update_network_name(int(network_id), new_name)
        except ClientError as ce:
            raise_if_connection_error(ce)
            if ce.status == 404:
                raiseCLIError(ce,
                    'No network found with id %s' % network_id,
                    details=['To see a detailed list of available network ids',
                    ' try /network list'])
            raiseCLIError(ce)
        except ValueError as ve:
            raiseCLIError(ve,
                'Invalid network_id %s' % network_id,
                importance=1,
                details=['Network id must be a possitive integer'])
        except Exception as err:
            raiseCLIError(err)


@command(network_cmds)
class network_delete(_init_cyclades):
    """Delete a network"""

    def main(self, network_id):
        super(self.__class__, self).main()
        try:
            self.client.delete_network(int(network_id))
        except ClientError as ce:
            raise_if_connection_error(ce)
            if ce.status == 421:
                raiseCLIError(ce,
                    'Network with id %s is in use' % network_id,
                    details=[
                        'Disconnect all nics/VMs of this network first',
                        '  to get nics: /network info %s' % network_id,
                        '    (under "attachments" section)',
                        '  to disconnect: /network disconnect <nic id>'])
            elif ce.status == 404:
                raiseCLIError(ce,
                    'No network found with id %s' % network_id,
                    details=['To see a detailed list of available network ids',
                    ' try /network list'])
            raiseCLIError(ce)
        except ValueError as ve:
            raiseCLIError(ve,
                'Invalid network_id %s' % network_id,
                importance=1,
                details=['Network id must be a possitive integer'])
        except Exception as err:
            raiseCLIError(err)


@command(network_cmds)
class network_connect(_init_cyclades):
    """Connect a server to a network"""

    def main(self, server_id, network_id):
        super(self.__class__, self).main()
        try:
            network_id = int(network_id)
            server_id = int(server_id)
            self.client.connect_server(server_id, network_id)
        except ClientError as ce:
            raise_if_connection_error(ce)
            if ce.status == 404:
                (thename, theid) = ('server', server_id)\
                    if 'server' in ('%s' % ce).lower()\
                    else ('network', network_id)
                raiseCLIError(ce,
                    'No %s found with id %s' % (thename, theid),
                    details=[
                    'To see a detailed list of available %s ids' % thename,
                    ' try /%s list' % thename])
            raiseCLIError(ce)
        except ValueError as ve:
            (thename, theid) = ('server', server_id)\
            if isinstance(network_id, int) else ('network', network_id)
            raiseCLIError(ve,
                'Invalid %s id %s' % (thename, theid),
                importance=1,
                details=['The %s id must be a possitive integer' % thename,
                '  to get available %s ids: /%s list' % (thename, thename)])
        except Exception as err:
            raiseCLIError(err)


@command(network_cmds)
class network_disconnect(_init_cyclades):
    """Disconnect a nic that connects a server to a network
    Nic ids are listed as "attachments" in detailed network information
    To get detailed network information: /network info <network id>
    """

    def main(self, nic_id):
        super(self.__class__, self).main()
        try:
            server_id = nic_id.split('-')[1]
            if not self.client.disconnect_server(server_id, nic_id):
                raise ClientError('Network Interface not found', status=404)
        except ClientError as ce:
            raise_if_connection_error(ce)
            if ce.status == 404:
                if 'server' in ('%s' % ce).lower():
                    raiseCLIError(ce,
                        'No server found with id %s' % (server_id),
                        details=[
                        'To see a detailed list of available server ids',
                        ' try /server list'])
                raiseCLIError(ce,
                    'No nic %s in server with id %s' % (nic_id, server_id),
                    details=[
                    'To see a list of nic ids for server %s try:' % server_id,
                    '  /server addr %s' % server_id])
            raiseCLIError(ce)
        except IndexError as err:
            raiseCLIError(err,
                'Nic %s is of incorrect format' % nic_id,
                importance=1,
                details=['nid_id format: nic-<server_id>-<nic_index>',
                    '  to get nic ids of a network: /network info <net_id>',
                    '  they are listed under the "attachments" section'])
        except Exception as err:
            raiseCLIError(err)
