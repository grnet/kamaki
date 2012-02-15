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

"""
To add a command create a new class and add a 'command' decorator. The class
must have a 'main' method which will contain the code to be executed.
Optionally a command can implement an 'update_parser' class method in order
to add command line arguments, or modify the OptionParser in any way.

The name of the class is important and it will determine the name and grouping
of the command. This behavior can be overriden with the 'group' and 'name'
decorator arguments:

    @command(api='compute')
    class server_list(object):
        # This command will be named 'list' under group 'server'
        ...

    @command(api='compute', name='ls')
    class server_list(object):
        # This command will be named 'ls' under group 'server'
        ...

The docstring of a command class will be used as the command description in
help messages, unless overriden with the 'description' decorator argument.

The syntax of a command will be generated dynamically based on the signature
of the 'main' method, unless overriden with the 'syntax' decorator argument:

    def main(self, server_id, network=None):
        # This syntax of this command will be: '<server id> [network]'
        ...

The order of commands is important, it will be preserved in the help output.
"""

import inspect
import logging
import os

from base64 import b64encode
from grp import getgrgid
from optparse import OptionParser
from os.path import abspath, basename, exists, expanduser
from pwd import getpwuid
from sys import argv, exit, stdout

from clint.textui import puts, puts_err, indent
from clint.textui.cols import columns

from kamaki import clients
from kamaki.config import Config
from kamaki.utils import OrderedDict, print_addresses, print_dict, print_items


# Path to the file that stores the configuration
CONFIG_PATH = expanduser('~/.kamakirc')

# Name of a shell variable to bypass the CONFIG_PATH value
CONFIG_ENV = 'KAMAKI_CONFIG'


_commands = OrderedDict()


GROUPS = {
    'config': "Configuration commands",
    'server': "Compute API server commands",
    'flavor': "Compute API flavor commands",
    'image': "Compute API image commands",
    'network': "Compute API network commands (Cyclades extension)",
    'glance': "Image API commands",
    'store': "Storage API commands"}


def command(api=None, group=None, name=None, syntax=None):
    """Class decorator that registers a class as a CLI command."""
    
    def decorator(cls):
        grp, sep, cmd = cls.__name__.partition('_')
        if not sep:
            grp, cmd = None, cls.__name__
        
        cls.api = api
        cls.group = group or grp
        cls.name = name or cmd
        cls.description = description or cls.__doc__
        cls.syntax = syntax
        
        short_description, sep, long_description = cls.__doc__.partition('\n')
        cls.description = short_description
        cls.long_description = long_description or short_description
        
        cls.syntax = syntax
        if cls.syntax is None:
            # Generate a syntax string based on main's arguments
            spec = inspect.getargspec(cls.main.im_func)
            args = spec.args[1:]
            n = len(args) - len(spec.defaults or ())
            required = ' '.join('<%s>' % x.replace('_', ' ') for x in args[:n])
            optional = ' '.join('[%s]' % x.replace('_', ' ') for x in args[n:])
            cls.syntax = ' '.join(x for x in [required, optional] if x)
            if spec.varargs:
                cls.syntax += ' <%s ...>' % spec.varargs
        
        if cls.group not in _commands:
            _commands[cls.group] = OrderedDict()
        _commands[cls.group][cls.name] = cls
        return cls
    return decorator


@command(api='config')
class config_list(object):
    """List configuration options"""
    
    def update_parser(cls, parser):
        parser.add_option('-a', dest='all', action='store_true',
                          default=False, help='include default values')
    
    def main(self):
        include_defaults = self.options.all
        for section in sorted(self.config.sections()):
            items = self.config.items(section, include_defaults)
            for key, val in sorted(items):
                puts('%s.%s = %s' % (section, key, val))


@command(api='config')
class config_get(object):
    """Show a configuration option"""
    
    def main(self, option):
        section, sep, key = option.rpartition('.')
        section = section or 'global'
        value = self.config.get(section, key)
        if value is not None:
            print value


@command(api='config')
class config_set(object):
    """Set a configuration option"""
    
    def main(self, option, value):
        section, sep, key = option.rpartition('.')
        section = section or 'global'
        self.config.set(section, key, value)
        self.config.write()


@command(api='config')
class config_delete(object):
    """Delete a configuration option (and use the default value)"""
    
    def main(self, option):
        section, sep, key = option.rpartition('.')
        section = section or 'global'
        self.config.remove_option(section, key)
        self.config.write()


@command(api='compute')
class server_list(object):
    """list servers"""
    
    def update_parser(cls, parser):
        parser.add_option('-l', dest='detail', action='store_true',
                default=False, help='show detailed output')
    
    def main(self):
        servers = self.client.list_servers(self.options.detail)
        print_items(servers)


@command(api='compute')
class server_info(object):
    """get server details"""
    
    def main(self, server_id):
        server = self.client.get_server_details(int(server_id))
        print_dict(server)


@command(api='compute')
class server_create(object):
    """create server"""
    
    def update_parser(cls, parser):
        parser.add_option('--personality', dest='personalities',
                action='append', default=[],
                metavar='PATH[,SERVER PATH[,OWNER[,GROUP,[MODE]]]]',
                help='add a personality file')
        parser.epilog = "If missing, optional personality values will be " \
                "filled based on the file at PATH if missing."
    
    def main(self, name, flavor_id, image_id):
        personalities = []
        for personality in self.options.personalities:
            p = personality.split(',')
            p.extend([None] * (5 - len(p)))     # Fill missing fields with None
            
            path = p[0]
            
            if not path:
                log.error("Invalid personality argument '%s'", p)
                return 1
            if not exists(path):
                log.error("File %s does not exist", path)
                return 1
            
            with open(path) as f:
                contents = b64encode(f.read())
            
            st = os.stat(path)
            personalities.append({
                'path': p[1] or abspath(path),
                'owner': p[2] or getpwuid(st.st_uid).pw_name,
                'group': p[3] or getgrgid(st.st_gid).gr_name,
                'mode': int(p[4]) if p[4] else 0x7777 & st.st_mode,
                'contents': contents})
        
        reply = self.client.create_server(name, int(flavor_id), image_id,
                personalities)
        print_dict(reply)


@command(api='compute')
class server_rename(object):
    """update server name"""
    
    def main(self, server_id, new_name):
        self.client.update_server_name(int(server_id), new_name)


@command(api='compute')
class server_delete(object):
    """delete server"""
    
    def main(self, server_id):
        self.client.delete_server(int(server_id))


@command(api='compute')
class server_reboot(object):
    """reboot server"""
    
    def update_parser(cls, parser):
        parser.add_option('-f', dest='hard', action='store_true',
                default=False, help='perform a hard reboot')
    
    def main(self, server_id):
        self.client.reboot_server(int(server_id), self.options.hard)


@command(api='cyclades')
class server_start(object):
    """start server"""
    
    def main(self, server_id):
        self.client.start_server(int(server_id))


@command(api='cyclades')
class server_shutdown(object):
    """shutdown server"""
    
    def main(self, server_id):
        self.client.shutdown_server(int(server_id))


@command(api='cyclades')
class server_console(object):
    """get a VNC console"""
    
    def main(self, server_id):
        reply = self.client.get_server_console(int(server_id))
        print_dict(reply)


@command(api='cyclades')
class server_firewall(object):
    """set the firewall profile"""
    
    def main(self, server_id, profile):
        self.client.set_firewall_profile(int(server_id), profile)


@command(api='cyclades')
class server_addr(object):
    """list server addresses"""
    
    def main(self, server_id, network=None):
        reply = self.client.list_server_addresses(int(server_id), network)
        margin = max(len(x['name']) for x in reply)
        print_addresses(reply, margin)


@command(api='compute')
class server_meta(object):
    """get server metadata"""
    
    def main(self, server_id, key=None):
        reply = self.client.get_server_metadata(int(server_id), key)
        print_dict(reply)


@command(api='compute')
class server_addmeta(object):
    """add server metadata"""
    
    def main(self, server_id, key, val):
        reply = self.client.create_server_metadata(int(server_id), key, val)
        print_dict(reply)


@command(api='compute')
class server_setmeta(object):
    """update server metadata"""
    
    def main(self, server_id, key, val):
        metadata = {key: val}
        reply = self.client.update_server_metadata(int(server_id), **metadata)
        print_dict(reply)


@command(api='compute')
class server_delmeta(object):
    """delete server metadata"""
    
    def main(self, server_id, key):
        self.client.delete_server_metadata(int(server_id), key)


@command(api='cyclades')
class server_stats(object):
    """get server statistics"""
    
    def main(self, server_id):
        reply = self.client.get_server_stats(int(server_id))
        print_dict(reply, exclude=('serverRef',))


@command(api='compute')
class flavor_list(object):
    """list flavors"""
    
    def update_parser(cls, parser):
        parser.add_option('-l', dest='detail', action='store_true',
                default=False, help='show detailed output')
    
    def main(self):
        flavors = self.client.list_flavors(self.options.detail)
        print_items(flavors)


@command(api='compute')
class flavor_info(object):
    """get flavor details"""
    
    def main(self, flavor_id):
        flavor = self.client.get_flavor_details(int(flavor_id))
        print_dict(flavor)


@command(api='compute')
class image_list(object):
    """list images"""
    
    def update_parser(cls, parser):
        parser.add_option('-l', dest='detail', action='store_true',
                default=False, help='show detailed output')
    
    def main(self):
        images = self.client.list_images(self.options.detail)
        print_items(images)


@command(api='compute')
class image_info(object):
    """get image details"""
    
    def main(self, image_id):
        image = self.client.get_image_details(image_id)
        print_dict(image)


@command(api='compute')
class image_delete(object):
    """delete image"""
    
    def main(self, image_id):
        self.client.delete_image(image_id)


@command(api='compute')
class image_meta(object):
    """get image metadata"""
    
    def main(self, image_id, key=None):
        reply = self.client.get_image_metadata(image_id, key)
        print_dict(reply)


@command(api='compute')
class image_addmeta(object):
    """add image metadata"""
    
    def main(self, image_id, key, val):
        reply = self.client.create_image_metadata(image_id, key, val)
        print_dict(reply)


@command(api='compute')
class image_setmeta(object):
    """update image metadata"""
    
    def main(self, image_id, key, val):
        metadata = {key: val}
        reply = self.client.update_image_metadata(image_id, **metadata)
        print_dict(reply)


@command(api='compute')
class image_delmeta(object):
    """delete image metadata"""
    
    def main(self, image_id, key):
        self.client.delete_image_metadata(image_id, key)


@command(api='cyclades')
class network_list(object):
    """list networks"""
    
    def update_parser(cls, parser):
        parser.add_option('-l', dest='detail', action='store_true',
                default=False, help='show detailed output')
    
    def main(self):
        networks = self.client.list_networks(self.options.detail)
        print_items(networks)


@command(api='cyclades')
class network_create(object):
    """create a network"""
    
    def main(self, name):
        reply = self.client.create_network(name)
        print_dict(reply)


@command(api='cyclades')
class network_info(object):
    """get network details"""
    
    def main(self, network_id):
        network = self.client.get_network_details(network_id)
        print_dict(network)


@command(api='cyclades')
class network_rename(object):
    """update network name"""
    
    def main(self, network_id, new_name):
        self.client.update_network_name(network_id, new_name)


@command(api='cyclades')
class network_delete(object):
    """delete a network"""
    
    def main(self, network_id):
        self.client.delete_network(network_id)


@command(api='cyclades')
class network_connect(object):
    """connect a server to a network"""
    
    def main(self, server_id, network_id):
        self.client.connect_server(server_id, network_id)


@command(api='cyclades')
class network_disconnect(object):
    """disconnect a server from a network"""
    
    def main(self, server_id, network_id):
        self.client.disconnect_server(server_id, network_id)


@command(api='image')
class glance_list(object):
    """list images"""
    
    def update_parser(cls, parser):
        parser.add_option('-l', dest='detail', action='store_true',
                default=False, help='show detailed output')
        parser.add_option('--container-format', dest='container_format',
                metavar='FORMAT', help='filter by container format')
        parser.add_option('--disk-format', dest='disk_format',
                metavar='FORMAT', help='filter by disk format')
        parser.add_option('--name', dest='name', metavar='NAME',
                help='filter by name')
        parser.add_option('--size-min', dest='size_min', metavar='BYTES',
                help='filter by minimum size')
        parser.add_option('--size-max', dest='size_max', metavar='BYTES',
                help='filter by maximum size')
        parser.add_option('--status', dest='status', metavar='STATUS',
                help='filter by status')
        parser.add_option('--order', dest='order', metavar='FIELD',
                help='order by FIELD (use a - prefix to reverse order)')
    
    def main(self):
        filters = {}
        for filter in ('container_format', 'disk_format', 'name', 'size_min',
                       'size_max', 'status'):
            val = getattr(self.options, filter, None)
            if val is not None:
                filters[filter] = val
        
        order = self.options.order or ''
        images = self.client.list_public(self.options.detail, filters=filters,
                                         order=order)
        print_items(images, title=('name',))


@command(api='image')
class glance_meta(object):
    """get image metadata"""
    
    def main(self, image_id):
        image = self.client.get_meta(image_id)
        print_dict(image)


@command(api='image')
class glance_register(object):
    """register an image"""
    
    def update_parser(cls, parser):
        parser.add_option('--checksum', dest='checksum', metavar='CHECKSUM',
                help='set image checksum')
        parser.add_option('--container-format', dest='container_format',
                metavar='FORMAT', help='set container format')
        parser.add_option('--disk-format', dest='disk_format',
                metavar='FORMAT', help='set disk format')
        parser.add_option('--id', dest='id',
                metavar='ID', help='set image ID')
        parser.add_option('--owner', dest='owner',
                metavar='USER', help='set image owner (admin only)')
        parser.add_option('--property', dest='properties', action='append',
                metavar='KEY=VAL',
                help='add a property (can be used multiple times)')
        parser.add_option('--public', dest='is_public', action='store_true',
                help='mark image as public')
        parser.add_option('--size', dest='size', metavar='SIZE',
                help='set image size')
    
    def main(self, name, location):
        params = {}
        for key in ('checksum', 'container_format', 'disk_format', 'id',
                    'owner', 'is_public', 'size'):
            val = getattr(self.options, key)
            if val is not None:
                params[key] = val
        
        properties = {}
        for property in self.options.properties or []:
            key, sep, val = property.partition('=')
            if not sep:
                log.error("Invalid property '%s'", property)
                return 1
            properties[key.strip()] = val.strip()
        
        self.client.register(name, location, params, properties)


@command(api='image')
class glance_members(object):
    """get image members"""
    
    def main(self, image_id):
        members = self.client.list_members(image_id)
        for member in members:
            print member['member_id']


@command(api='image')
class glance_shared(object):
    """list shared images"""
    
    def main(self, member):
        images = self.client.list_shared(member)
        for image in images:
            print image['image_id']


@command(api='image')
class glance_addmember(object):
    """add a member to an image"""
    
    def main(self, image_id, member):
        self.client.add_member(image_id, member)


@command(api='image')
class glance_delmember(object):
    """remove a member from an image"""
    
    def main(self, image_id, member):
        self.client.remove_member(image_id, member)


@command(api='image')
class glance_setmembers(object):
    """set the members of an image"""
    
    def main(self, image_id, *member):
        self.client.set_members(image_id, member)


class store_command(object):
    """base class for all store_* commands"""
    
    def update_parser(cls, parser):
        parser.add_option('--account', dest='account', metavar='NAME',
                help='use account NAME')
        parser.add_option('--container', dest='container', metavar='NAME',
                help='use container NAME')
    
    def main(self):
        self.config.override('storage_account', self.options.account)
        self.config.override('storage_container', self.options.container)
        
        # Use the more efficient Pithos client if available
        if 'pithos' in self.config.get('apis').split():
            self.client = clients.PithosClient(self.config)


@command(api='storage')
class store_create(object):
    """create a container"""
    
    def update_parser(cls, parser):
        parser.add_option('--account', dest='account', metavar='ACCOUNT',
                help='use account ACCOUNT')
    
    def main(self, container):
        self.config.override('storage_account', self.options.account)
        self.client.create_container(container)


@command(api='storage')
class store_container(store_command):
    """get container info"""
    
    def main(self):
        store_command.main(self)
        reply = self.client.get_container_meta()
        print_dict(reply)


@command(api='storage')
class store_upload(store_command):
    """upload a file"""
    
    def main(self, path, remote_path=None):
        store_command.main(self)
        if remote_path is None:
            remote_path = basename(path)
        with open(path) as f:
            self.client.create_object(remote_path, f)


@command(api='storage')
class store_download(store_command):
    """download a file"""
    
    def main(self, remote_path, local_path):
        store_command.main(self)
        f = self.client.get_object(remote_path)
        out = open(local_path, 'w') if local_path != '-' else stdout
        block = 4096
        data = f.read(block)
        while data:
            out.write(data)
            data = f.read(block)


@command(api='storage')
class store_delete(store_command):
    """delete a file"""
    
    def main(self, path):
        store_command.main(self)
        self.client.delete_object(path)


def print_groups():
    puts('\nGroups:')
    with indent(2):
        for group in _commands:
            description = GROUPS.get(group, '')
            puts(columns([group, 12], [description, 60]))


def print_commands(group):
    description = GROUPS.get(group, '')
    if description:
        puts('\n' + description)
    
    puts('\nCommands:')
    with indent(2):
        for name, cls in _commands[group].items():
            puts(columns([name, 12], [cls.description, 60]))


def main():
    parser = OptionParser(add_help_option=False)
    parser.usage = '%prog <group> <command> [options]'
    parser.add_option('-h', '--help', dest='help', action='store_true',
                      default=False,
                      help="Show this help message and exit")
    parser.add_option('--config', dest='config', metavar='PATH',
                      help="Specify the path to the configuration file")
    parser.add_option('-i', '--include', dest='include', action='store_true',
                      default=False,
                      help="Include protocol headers in the output")
    parser.add_option('-s', '--silent', dest='silent', action='store_true',
                      default=False,
                      help="Silent mode, don't output anything")
    parser.add_option('-v', '--verbose', dest='verbose', action='store_true',
                      default=False,
                      help="Make the operation more talkative")
    parser.add_option('-V', '--version', dest='version', action='store_true',
                      default=False,
                      help="Show version number and quit")
    parser.add_option('-o', dest='options', action='append',
                      default=[], metavar="KEY=VAL",
                      help="Override a config values")
    
    if args.contains(['-V', '--version']):
        import kamaki
        print "kamaki %s" % kamaki.__version__
        exit(0)
    
    if args.contains(['-s', '--silent']):
        level = logging.CRITICAL
    elif args.contains(['-v', '--verbose']):
        level = logging.INFO
    else:
        level = logging.WARNING
    
    logging.basicConfig(level=level, format='%(message)s')
    
    if '--config' in args:
        config_path = args.grouped['--config'].get(0)
    else:
        config_path = os.environ.get(CONFIG_ENV, CONFIG_PATH)
    
    config = Config(config_path)
    
    for option in args.grouped.get('-o', []):
        keypath, sep, val = option.partition('=')
        if not sep:
            log.error("Invalid option '%s'", option)
            exit(1)
        section, sep, key = keypath.partition('.')
        if not sep:
            log.error("Invalid option '%s'", option)
            exit(1)
        config.override(section.strip(), key.strip(), val.strip())
    
    apis = set(['config'])
    for api in ('compute', 'image', 'storage'):
        if config.getboolean(api, 'enable'):
            apis.add(api)
    if config.getboolean('compute', 'cyclades_extensions'):
        apis.add('cyclades')
    if config.getboolean('storage', 'pithos_extensions'):
        apis.add('pithos')
    
    # Remove commands that belong to APIs that are not included
    for group, group_commands in _commands.items():
        for name, cls in group_commands.items():
            if cls.api not in apis:
                del group_commands[name]
        if not group_commands:
            del _commands[group]
    
    if not args.grouped['_']:
        parser.print_help()
        print_groups()
        exit(0)
    
    group = args.grouped['_'][0]
    
    if group not in _commands:
        parser.print_help()
        print_groups()
        exit(1)
    
    parser.usage = '%%prog %s <command> [options]' % group
    
    if len(args.grouped['_']) == 1:
        parser.print_help()
        print_commands(group)
        exit(0)
    
    name = args.grouped['_'][1]
    
    if name not in _commands[group]:
        parser.print_help()
        print_commands(group)
        exit(1)
    
    cmd = _commands[group][name]()
    
    syntax = '%s [options]' % cmd.syntax if cmd.syntax else '[options]'
    parser.usage = '%%prog %s %s %s' % (group, name, syntax)
    parser.description = cmd.description
    parser.epilog = ''
    if hasattr(cmd, 'update_parser'):
        cmd.update_parser(parser)
    
    if args.contains(['-h', '--help']):
        parser.print_help()
        exit(0)
    
    cmd.options, cmd.args = parser.parse_args(argv)
    
    api = cmd.api
    if api == 'config':
        cmd.config = config
    elif api in ('compute', 'image', 'storage'):
        token = config.get(api, 'token') or config.get('gobal', 'token')
        url = config.get(api, 'url')
        client_cls = getattr(clients, api)
        kwargs = dict(base_url=url, token=token)
        
        # Special cases
        if api == 'compute' and config.getboolean(api, 'cyclades_extensions'):
            client_cls = clients.cyclades
        elif api == 'storage':
            kwargs['account'] = config.get(api, 'account')
            kwargs['container'] = config.get(api, 'container')
            if config.getboolean(api, 'pithos_extensions'):
                client_cls = clients.pithos
        
        cmd.client = client_cls(**kwargs)
        
    try:
        ret = cmd.main(*args.grouped['_'][2:])
        exit(ret)
    except TypeError as e:
        if e.args and e.args[0].startswith('main()'):
            parser.print_help()
            exit(1)
        else:
            raise
    except clients.ClientError, err:
        log.error('%s', err.message)
        log.info('%s', err.details)
        exit(2)


if __name__ == '__main__':
    main()
