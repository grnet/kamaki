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

from kamaki.cli import command, set_api_description
set_api_description('server', "Compute/Cyclades API server commands")
set_api_description('flavor', "Compute/Cyclades API flavor commands")
set_api_description('image', "Compute/Cyclades or Glance API image commands")
set_api_description('network', "Compute/Cyclades API network commands")
from .cyclades import CycladesClient

from colors import yellow

class _init_cyclades(object):
    def main(self):
        token = self.config.get('store', 'token') or self.config.get('global', 'token')
        base_url = self.config.get('store', 'url') or self.config.get('global', 'url')
        self.client = CycladesClient(base_url=base_url, token=token)

@command()
class server_list(_init_cyclades):
    """List servers"""

    def update_parser(self, parser):
        parser.add_argument('-l', dest='detail', action='store_true',
                default=False, help='show detailed output')

    def main(self):
        super(self.__class__, self).main()
        servers = self.client.list_servers(self.args.detail)
        print_items(servers)

@command()
class server_info(_init_cyclades):
    """Get server details"""

    def main(self, server_id):
        super(self.__class__, self).main()
        try:
            server = self.client.get_server_details(int(server_id))
        except ValueError:
            print(yellow('Server id must be a base10 integer'))
            return
        print_dict(server)

@command()
class server_create(_init_cyclades):
    """Create a server"""

    def update_parser(self, parser):
        parser.add_argument('--personality', dest='personalities',
                          action='append', default=[],
                          metavar='PATH[,SERVER PATH[,OWNER[,GROUP,[MODE]]]]',
                          help='add a personality file')

    def main(self, name, flavor_id, image_id):
        super(self.__class__, self).main()
        personalities = []
        for personality in self.args.personalities:
            p = personality.split(',')
            p.extend([None] * (5 - len(p)))     # Fill missing fields with None

            path = p[0]

            if not path:
                print("Invalid personality argument '%s'" % p)
                return 1
            if not exists(path):
                print("File %s does not exist" % path)
                return 1

            with open(path) as f:
                contents = b64encode(f.read())

            d = {'path': p[1] or abspath(path), 'contents': contents}
            if p[2]:
                d['owner'] = p[2]
            if p[3]:
                d['group'] = p[3]
            if p[4]:
                d['mode'] = int(p[4])
            personalities.append(d)

        reply = self.client.create_server(name, int(flavor_id), image_id,
                personalities)
        print_dict(reply)

@command()
class server_rename(_init_cyclades):
    """Update a server's name"""

    def main(self, server_id, new_name):
        super(self.__class__, self).main()
        try:
            self.client.update_server_name(int(server_id), new_name)
        except ValueError:
            print(yellow('Server id must be a base10 integer'))

@command()
class server_delete(_init_cyclades):
    """Delete a server"""

    def main(self, server_id):
        super(self.__class__, self).main()
        try:
            self.client.delete_server(int(server_id))
        except ValueError:
            print(yellow('Server id must be a base10 integer'))

@command()
class server_reboot(_init_cyclades):
    """Reboot a server"""

    def update_parser(self, parser):
        parser.add_argument('-f', dest='hard', action='store_true',
                default=False, help='perform a hard reboot')

    def main(self, server_id):
        super(self.__class__, self).main()
        try:
            self.client.reboot_server(int(server_id), self.args.hard)
        except ValueError:
            print(yellow('Server id must be a base10 integer'))

@command()
class server_start(_init_cyclades):
    """Start a server"""

    def main(self, server_id):
        super(self.__class__, self).main()
        try:
            self.client.start_server(int(server_id))
        except ValueError:
            print(yellow('Server id must be a base10 integer'))

@command()
class server_shutdown(_init_cyclades):
    """Shutdown a server"""

    def main(self, server_id):
        super(self.__class__, self).main()
        try:
            self.client.shutdown_server(int(server_id))
        except ValueError:
            print(yellow('Server id must be a base10 integer'))

@command()
class server_console(_init_cyclades):
    """Get a VNC console"""

    def main(self, server_id):
        super(self.__class__, self).main()
        try:
            reply = self.client.get_server_console(int(server_id))
        except ValueError:
            print(yellow('Server id must be a base10 integer'))
            return
        print_dict(reply)

@command()
class server_firewall(_init_cyclades):
    """Set the server's firewall profile"""

    def main(self, server_id, profile):
        super(self.__class__, self).main()
        try:
            self.client.set_firewall_profile(int(server_id), profile)
        except ValueError:
            print(yellow('Server id must be a base10 integer'))

@command()
class server_addr(_init_cyclades):
    """List a server's addresses"""

    def main(self, server_id, network=None):
        super(self.__class__, self).main()
        try:
            reply = self.client.list_server_nic_details(int(server_id), network)
        except ValueError:
            print(yellow('Server id must be a base10 integer'))
            return
        print_list(reply)

@command()
class server_meta(_init_cyclades):
    """Get a server's metadata"""

    def main(self, server_id, key=None):
        super(self.__class__, self).main()
        try:
            reply = self.client.get_server_metadata(int(server_id), key)
        except ValueError:
            print(yellow('Server id must be a base10 integer'))
            return
        print_dict(reply)

@command()
class server_addmeta(_init_cyclades):
    """Add server metadata"""

    def main(self, server_id, key, val):
        super(self.__class__, self).main()
        try:
            reply = self.client.create_server_metadata(int(server_id), key, val)
        except ValueError:
            print(yellow('Server id must be a base10 integer'))
            return
        print_dict(reply)

@command()
class server_setmeta(_init_cyclades):
    """Update server's metadata"""

    def main(self, server_id, key, val):
        super(self.__class__, self).main()
        metadata = {key: val}
        try:
            reply = self.client.update_server_metadata(int(server_id), **metadata)
        except ValueError:
            print(yellow('Server id must be a base10 integer'))
            return
        print_dict(reply)

@command()
class server_delmeta(_init_cyclades):
    """Delete server metadata"""

    def main(self, server_id, key):
        super(self.__class__, self).main()
        try:
            self.client.delete_server_metadata(int(server_id), key)
        except ValueError:
            print(yellow('Server id must be a base10 integer'))
            return

@command()
class server_stats(_init_cyclades):
    """Get server statistics"""

    def main(self, server_id):
        super(self.__class__, self).main()
        try:
            reply = self.client.get_server_stats(int(server_id))
        except ValueError:
            print(yellow('Server id must be a base10 integer'))
            return
        print_dict(reply, exclude=('serverRef',))

@command()
class flavor_list(_init_cyclades):
    """List flavors"""

    def update_parser(self, parser):
        parser.add_argument('-l', dest='detail', action='store_true',
                default=False, help='show detailed output')

    def main(self):
        super(self.__class__, self).main()
        flavors = self.client.list_flavors(self.args.detail)
        print_items(flavors)

@command()
class flavor_info(_init_cyclades):
    """Get flavor details"""

    def main(self, flavor_id):
        super(self.__class__, self).main()
        try:
            flavor = self.client.get_flavor_details(int(flavor_id))
        except ValueError:
            print(yellow('Flavor id must be a base10 integer'))
            return
        print_dict(flavor)

@command()
class image_list(_init_cyclades):
    """List images"""

    def update_parser(self, parser):
        parser.add_argument('-l', dest='detail', action='store_true',
                default=False, help='show detailed output')

    def main(self):
        super(self.__class__, self).main()
        images = self.client.list_images(self.args.detail)
        print_items(images)

@command()
class image_info(_init_cyclades):
    """Get image details"""

    def main(self, image_id):
        super(self.__class__, self).main()
        image = self.client.get_image_details(image_id)
        print_dict(image)

@command()
class image_delete(_init_cyclades):
    """Delete image"""

    def main(self, image_id):
        super(self.__class__, self).main()
        self.client.delete_image(image_id)

@command()
class image_properties(_init_cyclades):
    """Get image properties"""

    def main(self, image_id, key=None):
        super(self.__class__, self).main()
        reply = self.client.get_image_metadata(image_id, key)
        print_dict(reply)

@command()
class image_addproperty(_init_cyclades):
    """Add an image property"""

    def main(self, image_id, key, val):
        super(self.__class__, self).main()
        reply = self.client.create_image_metadata(image_id, key, val)
        print_dict(reply)

@command()
class image_setproperty(_init_cyclades):
    """Update an image property"""

    def main(self, image_id, key, val):
        super(self.__class__, self).main()
        metadata = {key: val}
        reply = self.client.update_image_metadata(image_id, **metadata)
        print_dict(reply)

@command()
class image_delproperty(_init_cyclades):
    """Delete an image property"""

    def main(self, image_id, key):
        super(self.__class__, self).main()
        self.client.delete_image_metadata(image_id, key)

@command()
class network_list(_init_cyclades):
    """List networks"""

    def update_parser(self, parser):
        parser.add_argument('-l', dest='detail', action='store_true',
                default=False, help='show detailed output')

    def main(self):
        super(self.__class__, self).main()
        networks = self.client.list_networks(self.args.detail)
        print_items(networks)

@command()
class network_create(_init_cyclades):
    """Create a network"""

    def main(self, name):
        super(self.__class__, self).main()
        reply = self.client.create_network(name)
        print_dict(reply)

@command()
class network_info(_init_cyclades):
    """Get network details"""

    def main(self, network_id):
        super(self.__class__, self).main()
        network = self.client.get_network_details(network_id)
        print_dict(network)

@command()
class network_rename(_init_cyclades):
    """Update network name"""

    def main(self, network_id, new_name):
        super(self.__class__, self).main()
        self.client.update_network_name(network_id, new_name)

@command()
class network_delete(_init_cyclades):
    """Delete a network"""

    def main(self, network_id):
        super(self.__class__, self).main()
        self.client.delete_network(network_id)

@command()
class network_connect(_init_cyclades):
    """Connect a server to a network"""

    def main(self, server_id, network_id):
        super(self.__class__, self).main()
        self.client.connect_server(server_id, network_id)

@command()
class network_disconnect(_init_cyclades):
    """Disconnect a nic that connects a server to a network"""

    def main(self, nic_id):
        super(self.__class__, self).main()
        try:
            server_id = nic_id.split('-')[1]
            self.client.disconnect_server(server_id, nic_id)
        except IndexError:
            print(yellow('nid_id format: nic-<server_id>-<nic_index>'))