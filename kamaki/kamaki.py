#!/usr/bin/env python

# Copyright 2011 GRNET S.A. All rights reserved.
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

import inspect
import logging
import os
import sys

from collections import defaultdict
from optparse import OptionParser

from client import Client, ClientError


API_ENV = 'KAMAKI_API'
URL_ENV = 'KAMAKI_URL'
TOKEN_ENV = 'KAMAKI_TOKEN'
RCFILE = '.kamakirc'


log = logging.getLogger('kamaki')


def print_addresses(addresses, margin):
    for address in addresses:
        if address['id'] == 'public':
            net = 'public'
        else:
            net = '%s/%s' % (address['id'], address['name'])
        print '%s:' % net.rjust(margin + 4)
        
        ether = address.get('mac', None)
        if ether:
            print '%s: %s' % ('ether'.rjust(margin + 8), ether)
        
        firewall = address.get('firewallProfile', None)
        if firewall:
            print '%s: %s' % ('firewall'.rjust(margin + 8), firewall)
        
        for ip in address.get('values', []):
            key = 'inet' if ip['version'] == 4 else 'inet6'
            print '%s: %s' % (key.rjust(margin + 8), ip['addr'])


def print_metadata(metadata, margin):
    print '%s:' % 'metadata'.rjust(margin)
    for key, val in metadata.get('values', {}).items():
        print '%s: %s' % (key.rjust(margin + 4), val)


def print_dict(d, exclude=()):
    if not d:
        return
    margin = max(len(key) for key in d) + 1
    
    for key, val in sorted(d.items()):
        if key in exclude:
            continue
        
        if key == 'addresses':
            print '%s:' % 'addresses'.rjust(margin)
            print_addresses(val.get('values', []), margin)
            continue
        elif key == 'metadata':
            print_metadata(val, margin)
            continue
        elif key == 'servers':
            val = ', '.join(str(x) for x in val['values'])
        
        print '%s: %s' % (key.rjust(margin), val)


def print_items(items, detail=False):
    for item in items:
        print '%s %s' % (item['id'], item.get('name', ''))
        if detail:
            print_dict(item, exclude=('id', 'name'))
            print


class Command(object):
    """Abstract class.
    
    All commands should subclass this class.
    """
    
    api = 'openstack'
    group = '<group>'
    name = '<command>'
    syntax = ''
    description = ''
    
    def __init__(self, argv):
        self._init_parser(argv)
        self._init_logging()
        self._init_conf()
        if self.name != '<command>':
            self.client = Client(self.url, self.token)
    
    def _init_parser(self, argv):
        parser = OptionParser()
        parser.usage = '%%prog %s %s %s [options]' % (self.group, self.name,
                                                        self.syntax)
        parser.add_option('--api', dest='api', metavar='API',
                            help='API can be either openstack or synnefo')
        parser.add_option('--url', dest='url', metavar='URL',
                            help='API URL')
        parser.add_option('--token', dest='token', metavar='TOKEN',
                            help='use token TOKEN')
        parser.add_option('-v', action='store_true', dest='verbose',
                            default=False, help='use verbose output')
        parser.add_option('-d', action='store_true', dest='debug',
                            default=False, help='use debug output')
        
        self.add_options(parser)
        
        options, args = parser.parse_args(argv)
        
        # Add options to self
        for opt in parser.option_list:
            key = opt.dest
            if key:
                val = getattr(options, key)
                setattr(self, key, val)
        
        self.args = args
        self.parser = parser
    
    def _init_logging(self):
        if self.debug:
            log.setLevel(logging.DEBUG)
        elif self.verbose:
            log.setLevel(logging.INFO)
        else:
            log.setLevel(logging.WARNING)
        
    def _init_conf(self):
        if not self.api:
            self.api = os.environ.get(API_ENV, None)
        if not self.url:
            self.url = os.environ.get(URL_ENV, None)
        if not self.token:
            self.token = os.environ.get(TOKEN_ENV, None)
        
        path = os.path.join(os.path.expanduser('~'), RCFILE)
        if not os.path.exists(path):
            return

        for line in open(path):
            key, sep, val = line.partition('=')
            if not sep:
                continue
            key = key.strip().lower()
            val = val.strip()
            if key == 'api' and not self.api:
                self.api = val
            elif key == 'url' and not self.url:
                self.url = val
            elif key == 'token' and not self.token:
                self.token = val
    
    def add_options(self, parser):
        pass
    
    def main(self, *args):
        pass
    
    def execute(self):
        try:
            self.main(*self.args)
        except TypeError:
            self.parser.print_help()


# Server Group

class ListServers(Command):
    group = 'server'
    name = 'list'
    description = 'list servers'
    
    def add_options(self, parser):
        parser.add_option('-l', action='store_true', dest='detail',
                            default=False, help='show detailed output')
    
    def main(self):
        servers = self.client.list_servers(self.detail)
        print_items(servers, self.detail)


class GetServerDetails(Command):
    group = 'server'
    name = 'info'
    syntax = '<server id>'
    description = 'get server details'
    
    def main(self, server_id):
        server = self.client.get_server_details(int(server_id))
        print_dict(server)


class CreateServer(Command):
    group = 'server'
    name = 'create'
    syntax = '<server name>'
    description = 'create server'

    def add_options(self, parser):
        parser.add_option('-f', dest='flavor', metavar='FLAVOR_ID', default=1,
                            help='use flavor FLAVOR_ID')
        parser.add_option('-i', dest='image', metavar='IMAGE_ID', default=1,
                            help='use image IMAGE_ID')
        parser.add_option('--personality', dest='personality', action='append',
                            metavar='PATH,SERVERPATH',
                            help='add a personality file')
    
    def main(self, name):
        flavor_id = int(self.flavor)
        image_id = int(self.image)
        personality = []
        if self.personality:
            for p in self.personality:
                lpath, sep, rpath = p.partition(',')
                if not lpath or not rpath:
                    log.error("Invalid personality argument '%s'", p)
                    return
                if not os.path.exists(lpath):
                    log.error("File %s does not exist", lpath)
                    return
                with open(lpath) as f:
                    personality.append((rpath, f.read()))
        
        reply = self.client.create_server(name, flavor_id, image_id,
                                            personality)
        print_dict(reply)


class UpdateServerName(Command):
    group = 'server'
    name = 'rename'
    syntax = '<server id> <new name>'
    description = 'update server name'
    
    def main(self, server_id, new_name):
        self.client.update_server_name(int(server_id), new_name)


class DeleteServer(Command):
    group = 'server'
    name = 'delete'
    syntax = '<server id>'
    description = 'delete server'
    
    def main(self, server_id):
        self.client.delete_server(int(server_id))


class RebootServer(Command):
    group = 'server'
    name = 'reboot'
    syntax = '<server id>'
    description = 'reboot server'
    
    def add_options(self, parser):
        parser.add_option('-f', action='store_true', dest='hard',
                            default=False, help='perform a hard reboot')
    
    def main(self, server_id):
        self.client.reboot_server(int(server_id), self.hard)


class StartServer(Command):
    api = 'synnefo'
    group = 'server'
    name = 'start'
    syntax = '<server id>'
    description = 'start server'
    
    def main(self, server_id):
        self.client.start_server(int(server_id))


class StartServer(Command):
    api = 'synnefo'
    group = 'server'
    name = 'shutdown'
    syntax = '<server id>'
    description = 'shutdown server'
    
    def main(self, server_id):
        self.client.shutdown_server(int(server_id))


class ServerConsole(Command):
    api = 'synnefo'
    group = 'server'
    name = 'console'
    syntax = '<server id>'
    description = 'get VNC console'

    def main(self, server_id):
        reply = self.client.get_server_console(int(server_id))
        print_dict(reply)


class SetFirewallProfile(Command):
    api = 'synnefo'
    group = 'server'
    name = 'firewall'
    syntax = '<server id> <profile>'
    description = 'set the firewall profile'
    
    def main(self, server_id, profile):
        self.client.set_firewall_profile(int(server_id), profile)


class ListAddresses(Command):
    group = 'server'
    name = 'addr'
    syntax = '<server id> [network]'
    description = 'list server addresses'
    
    def main(self, server_id, network=None):
        reply = self.client.list_server_addresses(int(server_id), network)
        margin = max(len(x['name']) for x in reply)
        print_addresses(reply, margin)


class GetServerMeta(Command):
    group = 'server'
    name = 'meta'
    syntax = '<server id> [key]'
    description = 'get server metadata'
    
    def main(self, server_id, key=None):
        reply = self.client.get_server_metadata(int(server_id), key)
        print_dict(reply)


class CreateServerMetadata(Command):
    group = 'server'
    name = 'addmeta'
    syntax = '<server id> <key> <val>'
    description = 'add server metadata'
    
    def main(self, server_id, key, val):
        reply = self.client.create_server_metadata(int(server_id), key, val)
        print_dict(reply)


class UpdateServerMetadata(Command):
    group = 'server'
    name = 'setmeta'
    syntax = '<server id> <key> <val>'
    description = 'update server metadata'
    
    def main(self, server_id, key, val):
        metadata = {key: val}
        reply = self.client.update_server_metadata(int(server_id), **metadata)
        print_dict(reply)


class DeleteServerMetadata(Command):
    group = 'server'
    name = 'delmeta'
    syntax = '<server id> <key>'
    description = 'delete server metadata'
    
    def main(self, server_id, key):
        self.client.delete_server_metadata(int(server_id), key)


class GetServerStats(Command):
    api = 'synnefo'
    group = 'server'
    name = 'stats'
    syntax = '<server id>'
    description = 'get server statistics'
    
    def main(self, server_id):
        reply = self.client.get_server_stats(int(server_id))
        print_dict(reply, exclude=('serverRef',))


# Flavor Group

class ListFlavors(Command):
    group = 'flavor'
    name = 'list'
    description = 'list flavors'
    
    def add_options(self, parser):
        parser.add_option('-l', action='store_true', dest='detail',
                            default=False, help='show detailed output')

    def main(self):
        flavors = self.client.list_flavors(self.detail)
        print_items(flavors, self.detail)


class GetFlavorDetails(Command):
    group = 'flavor'
    name = 'info'
    syntax = '<flavor id>'
    description = 'get flavor details'
    
    def main(self, flavor_id):
        flavor = self.client.get_flavor_details(int(flavor_id))
        print_dict(flavor)


class ListImages(Command):
    group = 'image'
    name = 'list'
    description = 'list images'

    def add_options(self, parser):
        parser.add_option('-l', action='store_true', dest='detail',
                            default=False, help='show detailed output')

    def main(self):
        images = self.client.list_images(self.detail)
        print_items(images, self.detail)


class GetImageDetails(Command):
    group = 'image'
    name = 'info'
    syntax = '<image id>'
    description = 'get image details'
    
    def main(self, image_id):
        image = self.client.get_image_details(int(image_id))
        print_dict(image)


class CreateImage(Command):
    group = 'image'
    name = 'create'
    syntax = '<server id> <image name>'
    description = 'create image'
    
    def main(self, server_id, name):
        reply = self.client.create_image(int(server_id), name)
        print_dict(reply)


class DeleteImage(Command):
    group = 'image'
    name = 'delete'
    syntax = '<image id>'
    description = 'delete image'
    
    def main(self, image_id):
        self.client.delete_image(int(image_id))


class GetImageMetadata(Command):
    group = 'image'
    name = 'meta'
    syntax = '<image id> [key]'
    description = 'get image metadata'
    
    def main(self, image_id, key=None):
        reply = self.client.get_image_metadata(int(image_id), key)
        print_dict(reply)


class CreateImageMetadata(Command):
    group = 'image'
    name = 'addmeta'
    syntax = '<image id> <key> <val>'
    description = 'add image metadata'
    
    def main(self, image_id, key, val):
        reply = self.client.create_image_metadata(int(image_id), key, val)
        print_dict(reply)


class UpdateImageMetadata(Command):
    group = 'image'
    name = 'setmeta'
    syntax = '<image id> <key> <val>'
    description = 'update image metadata'
    
    def main(self, image_id, key, val):
        metadata = {key: val}
        reply = self.client.update_image_metadata(int(image_id), **metadata)
        print_dict(reply)


class DeleteImageMetadata(Command):
    group = 'image'
    name = 'delmeta'
    syntax = '<image id> <key>'
    description = 'delete image metadata'
    
    def main(self, image_id, key):
        self.client.delete_image_metadata(int(image_id), key)


class ListNetworks(Command):
    api = 'synnefo'
    group = 'network'
    name = 'list'
    description = 'list networks'
    
    def add_options(self, parser):
        parser.add_option('-l', action='store_true', dest='detail',
                            default=False, help='show detailed output')
    
    def main(self):
        networks = self.client.list_networks(self.detail)
        print_items(networks, self.detail)


class CreateNetwork(Command):
    api = 'synnefo'
    group = 'network'
    name = 'create'
    syntax = '<network name>'
    description = 'create a network'
    
    def main(self, name):
        reply = self.client.create_network(name)
        print_dict(reply)


class GetNetworkDetails(Command):
    api = 'synnefo'
    group = 'network'
    name = 'info'
    syntax = '<network id>'
    description = 'get network details'

    def main(self, network_id):
        network = self.client.get_network_details(network_id)
        print_dict(network)


class RenameNetwork(Command):
    api = 'synnefo'
    group = 'network'
    name = 'rename'
    syntax = '<network id> <new name>'
    description = 'update network name'
    
    def main(self, network_id, name):
        self.client.update_network_name(network_id, name)


class DeleteNetwork(Command):
    api = 'synnefo'
    group = 'network'
    name = 'delete'
    syntax = '<network id>'
    description = 'delete a network'
    
    def main(self, network_id):
        self.client.delete_network(network_id)

class ConnectServer(Command):
    api = 'synnefo'
    group = 'network'
    name = 'connect'
    syntax = '<server id> <network id>'
    description = 'connect a server to a network'
    
    def main(self, server_id, network_id):
        self.client.connect_server(server_id, network_id)


class DisconnectServer(Command):
    api = 'synnefo'
    group = 'network'
    name = 'disconnect'
    syntax = '<server id> <network id>'
    description = 'disconnect a server from a network'

    def main(self, server_id, network_id):
        self.client.disconnect_server(server_id, network_id)



def print_usage(exe, groups, group=None):
    nop = Command([])
    nop.parser.print_help()
    
    print
    print 'Commands:'
    
    if group:
        items = [(group, groups[group])]
    else:
        items = sorted(groups.items())
    
    for group, commands in items:
        for command, cls in sorted(commands.items()):
            name = '  %s %s' % (group, command)
            print '%s %s' % (name.ljust(22), cls.description)
        print


def main():
    nop = Command([])
    groups = defaultdict(dict)
    module = sys.modules[__name__]
    for name, cls in inspect.getmembers(module, inspect.isclass):
        if issubclass(cls, Command) and cls != Command:
            if nop.api == 'openstack' and nop.api != cls.api:
                continue    # Ignore synnefo commands
            groups[cls.group][cls.name] = cls
    
    argv = list(sys.argv)
    exe = os.path.basename(argv.pop(0))
    group = argv.pop(0) if argv else None
    command = argv.pop(0) if argv else None
    
    if group not in groups:
        group = None
    
    if not group or command not in groups[group]:
        print_usage(exe, groups, group)
        sys.exit(1)
    
    cls = groups[group][command]
    
    try:
        cmd = cls(argv)
        cmd.execute()
    except ClientError, err:
        log.error('%s', err.message)
        log.info('%s', err.details)


if __name__ == '__main__':
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter('%(message)s'))
    log.addHandler(ch)
    
    main()
