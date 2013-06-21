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
from kamaki.cli.utils import print_dict, remove_from_items
from kamaki.cli.errors import raiseCLIError, CLISyntaxError, CLIBaseUrlError
from kamaki.clients.cyclades import CycladesClient, ClientError
from kamaki.cli.argument import FlagArgument, ValueArgument, KeyValueArgument
from kamaki.cli.argument import ProgressBarArgument, DateArgument, IntArgument
from kamaki.cli.commands import _command_init, errors, addLogSettings
from kamaki.cli.commands import _optional_output_cmd, _optional_json

from base64 import b64encode
from os.path import exists


server_cmds = CommandTree('server', 'Cyclades/Compute API server commands')
flavor_cmds = CommandTree('flavor', 'Cyclades/Compute API flavor commands')
network_cmds = CommandTree('network', 'Cyclades/Compute API network commands')
_commands = [server_cmds, flavor_cmds, network_cmds]


about_authentication = '\nUser Authentication:\
    \n* to check authentication: /user authenticate\
    \n* to set authentication token: /config set cloud.<cloud>.token <token>'

howto_personality = [
    'Defines a file to be injected to VMs personality.',
    'Personality value syntax: PATH,[SERVER_PATH,[OWNER,[GROUP,[MODE]]]]',
    '  PATH: of local file to be injected',
    '  SERVER_PATH: destination location inside server Image',
    '  OWNER: user id of destination file owner',
    '  GROUP: group id or name to own destination file',
    '  MODEL: permition in octal (e.g. 0777 or o+rwx)']


class _init_cyclades(_command_init):
    @errors.generic.all
    @addLogSettings
    def _run(self, service='compute'):
        if getattr(self, 'cloud', None):
            base_url = self._custom_url(service)\
                or self._custom_url('cyclades')
            if base_url:
                token = self._custom_token(service)\
                    or self._custom_token('cyclades')\
                    or self.config.get_cloud('token')
                self.client = CycladesClient(
                    base_url=base_url, token=token)
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
class server_list(_init_cyclades, _optional_json):
    """List Virtual Machines accessible by user"""

    __doc__ += about_authentication

    arguments = dict(
        detail=FlagArgument('show detailed output', ('-l', '--details')),
        since=DateArgument(
            'show only items since date (\' d/m/Y H:M:S \')',
            '--since'),
        limit=IntArgument('limit number of listed VMs', ('-n', '--number')),
        more=FlagArgument(
            'output results in pages (-n to set items per page, default 10)',
            '--more'),
        enum=FlagArgument('Enumerate results', '--enumerate')
    )

    @errors.generic.all
    @errors.cyclades.connection
    @errors.cyclades.date
    def _run(self):
        servers = self.client.list_servers(self['detail'], self['since'])
        if not (self['detail'] or self['json_output']):
            remove_from_items(servers, 'links')

        kwargs = dict(with_enumeration=self['enum'])
        if self['more']:
            kwargs['page_size'] = self['limit'] if self['limit'] else 10
        elif self['limit']:
            servers = servers[:self['limit']]
        self._print(servers, **kwargs)

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(server_cmds)
class server_info(_init_cyclades, _optional_json):
    """Detailed information on a Virtual Machine
    Contains:
    - name, id, status, create/update dates
    - network interfaces
    - metadata (e.g. os, superuser) and diagnostics
    - hardware flavor and os image ids
    """

    @errors.generic.all
    @errors.cyclades.connection
    @errors.cyclades.server_id
    def _run(self, server_id):
        self._print(self.client.get_server_details(server_id), print_dict)

    def main(self, server_id):
        super(self.__class__, self)._run()
        self._run(server_id=server_id)


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
                msg = 'Wrong number of terms (should be 1 to 5)'
                raiseCLIError(CLISyntaxError(msg), details=howto_personality)
            path = termlist[0]
            if not exists(path):
                raiseCLIError(
                    None,
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
class server_create(_init_cyclades, _optional_json):
    """Create a server (aka Virtual Machine)
    Parameters:
    - name: (single quoted text)
    - flavor id: Hardware flavor. Pick one from: /flavor list
    - image id: OS images. Pick one from: /image list
    """

    arguments = dict(
        personality=PersonalityArgument(
            (80 * ' ').join(howto_personality), ('-p', '--personality'))
    )

    @errors.generic.all
    @errors.cyclades.connection
    @errors.plankton.id
    @errors.cyclades.flavor_id
    def _run(self, name, flavor_id, image_id):
        self._print(
            self.client.create_server(
                name, int(flavor_id), image_id, self['personality']),
            print_dict)

    def main(self, name, flavor_id, image_id):
        super(self.__class__, self)._run()
        self._run(name=name, flavor_id=flavor_id, image_id=image_id)


@command(server_cmds)
class server_rename(_init_cyclades, _optional_output_cmd):
    """Set/update a server (VM) name
    VM names are not unique, therefore multiple servers may share the same name
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
class server_delete(_init_cyclades, _optional_output_cmd):
    """Delete a server (VM)"""

    @errors.generic.all
    @errors.cyclades.connection
    @errors.cyclades.server_id
    def _run(self, server_id):
            self._optional_output(self.client.delete_server(int(server_id)))

    def main(self, server_id):
        super(self.__class__, self)._run()
        self._run(server_id=server_id)


@command(server_cmds)
class server_reboot(_init_cyclades, _optional_output_cmd):
    """Reboot a server (VM)"""

    arguments = dict(
        hard=FlagArgument('perform a hard reboot', ('-f', '--force'))
    )

    @errors.generic.all
    @errors.cyclades.connection
    @errors.cyclades.server_id
    def _run(self, server_id):
        self._optional_output(
            self.client.reboot_server(int(server_id), self['hard']))

    def main(self, server_id):
        super(self.__class__, self)._run()
        self._run(server_id=server_id)


@command(server_cmds)
class server_start(_init_cyclades, _optional_output_cmd):
    """Start an existing server (VM)"""

    @errors.generic.all
    @errors.cyclades.connection
    @errors.cyclades.server_id
    def _run(self, server_id):
        self._optional_output(self.client.start_server(int(server_id)))

    def main(self, server_id):
        super(self.__class__, self)._run()
        self._run(server_id=server_id)


@command(server_cmds)
class server_shutdown(_init_cyclades, _optional_output_cmd):
    """Shutdown an active server (VM)"""

    @errors.generic.all
    @errors.cyclades.connection
    @errors.cyclades.server_id
    def _run(self, server_id):
        self._optional_output(self.client.shutdown_server(int(server_id)))

    def main(self, server_id):
        super(self.__class__, self)._run()
        self._run(server_id=server_id)


@command(server_cmds)
class server_console(_init_cyclades, _optional_json):
    """Get a VNC console to access an existing server (VM)
    Console connection information provided (at least):
    - host: (url or address) a VNC host
    - port: (int) the gateway to enter VM on host
    - password: for VNC authorization
    """

    @errors.generic.all
    @errors.cyclades.connection
    @errors.cyclades.server_id
    def _run(self, server_id):
        self._print(
            self.client.get_server_console(int(server_id)), print_dict)

    def main(self, server_id):
        super(self.__class__, self)._run()
        self._run(server_id=server_id)


@command(server_cmds)
class server_firewall(_init_cyclades):
    """Manage server (VM) firewall profiles for public networks"""


@command(server_cmds)
class server_firewall_set(_init_cyclades, _optional_output_cmd):
    """Set the server (VM) firewall profile on VMs public network
    Values for profile:
    - DISABLED: Shutdown firewall
    - ENABLED: Firewall in normal mode
    - PROTECTED: Firewall in secure mode
    """

    @errors.generic.all
    @errors.cyclades.connection
    @errors.cyclades.server_id
    @errors.cyclades.firewall
    def _run(self, server_id, profile):
        self._optional_output(self.client.set_firewall_profile(
            server_id=int(server_id), profile=('%s' % profile).upper()))

    def main(self, server_id, profile):
        super(self.__class__, self)._run()
        self._run(server_id=server_id, profile=profile)


@command(server_cmds)
class server_firewall_get(_init_cyclades):
    """Get the server (VM) firewall profile for its public network"""

    @errors.generic.all
    @errors.cyclades.connection
    @errors.cyclades.server_id
    def _run(self, server_id):
        print(self.client.get_firewall_profile(server_id))

    def main(self, server_id):
        super(self.__class__, self)._run()
        self._run(server_id=server_id)


@command(server_cmds)
class server_addr(_init_cyclades, _optional_json):
    """List the addresses of all network interfaces on a server (VM)"""

    arguments = dict(
        enum=FlagArgument('Enumerate results', '--enumerate')
    )

    @errors.generic.all
    @errors.cyclades.connection
    @errors.cyclades.server_id
    def _run(self, server_id):
        reply = self.client.list_server_nics(int(server_id))
        self._print(
            reply, with_enumeration=self['enum'] and len(reply) > 1)

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
            self.client.get_server_metadata(int(server_id), key), print_dict)

    def main(self, server_id, key=''):
        super(self.__class__, self)._run()
        self._run(server_id=server_id, key=key)


@command(server_cmds)
class server_metadata_set(_init_cyclades, _optional_json):
    """Set / update server(VM) metadata
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
            print_dict)

    def main(self, server_id, *key_equals_val):
        super(self.__class__, self)._run()
        self._run(server_id=server_id, keyvals=key_equals_val)


@command(server_cmds)
class server_metadata_delete(_init_cyclades, _optional_output_cmd):
    """Delete server (VM) metadata"""

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
    """Get server (VM) statistics"""

    @errors.generic.all
    @errors.cyclades.connection
    @errors.cyclades.server_id
    def _run(self, server_id):
        self._print(self.client.get_server_stats(int(server_id)), print_dict)

    def main(self, server_id):
        super(self.__class__, self)._run()
        self._run(server_id=server_id)


@command(server_cmds)
class server_wait(_init_cyclades):
    """Wait for server to finish [BUILD, STOPPED, REBOOT, ACTIVE]"""

    arguments = dict(
        progress_bar=ProgressBarArgument(
            'do not show progress bar',
            ('-N', '--no-progress-bar'),
            False
        )
    )

    @errors.generic.all
    @errors.cyclades.connection
    @errors.cyclades.server_id
    def _run(self, server_id, currect_status):
        (progress_bar, wait_cb) = self._safe_progress_bar(
            'Server %s still in %s mode' % (server_id, currect_status))

        try:
            new_mode = self.client.wait_server(
                server_id,
                currect_status,
                wait_cb=wait_cb)
        except Exception:
            self._safe_progress_bar_finish(progress_bar)
            raise
        finally:
            self._safe_progress_bar_finish(progress_bar)
        if new_mode:
            print('Server %s is now in %s mode' % (server_id, new_mode))
        else:
            raiseCLIError(None, 'Time out')

    def main(self, server_id, currect_status='BUILD'):
        super(self.__class__, self)._run()
        self._run(server_id=server_id, currect_status=currect_status)


@command(flavor_cmds)
class flavor_list(_init_cyclades, _optional_json):
    """List available hardware flavors"""

    arguments = dict(
        detail=FlagArgument('show detailed output', ('-l', '--details')),
        limit=IntArgument('limit # of listed flavors', ('-n', '--number')),
        more=FlagArgument(
            'output results in pages (-n to set items per page, default 10)',
            '--more'),
        enum=FlagArgument('Enumerate results', '--enumerate')
    )

    @errors.generic.all
    @errors.cyclades.connection
    def _run(self):
        flavors = self.client.list_flavors(self['detail'])
        if not (self['detail'] or self['json_output']):
            remove_from_items(flavors, 'links')
        pg_size = 10 if self['more'] and not self['limit'] else self['limit']
        self._print(
            flavors,
            with_redundancy=self['detail'],
            page_size=pg_size,
            with_enumeration=self['enum'])

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
            self.client.get_flavor_details(int(flavor_id)), print_dict)

    def main(self, flavor_id):
        super(self.__class__, self)._run()
        self._run(flavor_id=flavor_id)


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
        self._print(network, print_dict, exclude=('id'))

    def main(self, network_id):
        super(self.__class__, self)._run()
        self._run(network_id=network_id)


@command(network_cmds)
class network_list(_init_cyclades, _optional_json):
    """List networks"""

    arguments = dict(
        detail=FlagArgument('show detailed output', ('-l', '--details')),
        limit=IntArgument('limit # of listed networks', ('-n', '--number')),
        more=FlagArgument(
            'output results in pages (-n to set items per page, default 10)',
            '--more'),
        enum=FlagArgument('Enumerate results', '--enumerate')
    )

    @errors.generic.all
    @errors.cyclades.connection
    def _run(self):
        networks = self.client.list_networks(self['detail'])
        if not (self['detail'] or self['json_output']):
            remove_from_items(networks, 'links')
        kwargs = dict(with_enumeration=self['enum'])
        if self['more']:
            kwargs['page_size'] = self['limit'] or 10
        elif self['limit']:
            networks = networks[:self['limit']]
        self._print(networks, **kwargs)

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(network_cmds)
class network_create(_init_cyclades, _optional_json):
    """Create an (unconnected) network"""

    arguments = dict(
        cidr=ValueArgument('explicitly set cidr', '--with-cidr'),
        gateway=ValueArgument('explicitly set gateway', '--with-gateway'),
        dhcp=FlagArgument('Use dhcp (default: off)', '--with-dhcp'),
        type=ValueArgument(
            'Valid network types are '
            'CUSTOM, IP_LESS_ROUTED, MAC_FILTERED (default), PHYSICAL_VLAN',
            '--with-type',
            default='MAC_FILTERED')
    )

    @errors.generic.all
    @errors.cyclades.connection
    @errors.cyclades.network_max
    def _run(self, name):
        self._print(self.client.create_network(
            name,
            cidr=self['cidr'],
            gateway=self['gateway'],
            dhcp=self['dhcp'],
            type=self['type']), print_dict)

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
class network_delete(_init_cyclades, _optional_output_cmd):
    """Delete a network"""

    @errors.generic.all
    @errors.cyclades.connection
    @errors.cyclades.network_id
    @errors.cyclades.network_in_use
    def _run(self, network_id):
        self._optional_output(self.client.delete_network(int(network_id)))

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
                    nic_id,
                    server_id),
                status=404)
        print('Disconnected %s connections' % num_of_disconnected)

    def main(self, nic_id):
        super(self.__class__, self)._run()
        server_id = self._server_id_from_nic(nic_id=nic_id)
        self._run(nic_id=nic_id, server_id=server_id)
