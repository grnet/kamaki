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

from clint import args
from clint.textui import puts, puts_err, indent, progress
from clint.textui.colored import magenta, red, yellow
from clint.textui.cols import columns

from requests.exceptions import ConnectionError

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
    
    def update_parser(self, parser):
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
    """List servers"""
    
    def update_parser(self, parser):
        parser.add_option('-l', dest='detail', action='store_true',
                default=False, help='show detailed output')
    
    def main(self):
        servers = self.client.list_servers(self.options.detail)
        print_items(servers)


@command(api='compute')
class server_info(object):
    """Get server details"""
    
    def main(self, server_id):
        server = self.client.get_server_details(int(server_id))
        print_dict(server)


@command(api='compute')
class server_create(object):
    """Create a server"""
    
    def update_parser(self, parser):
        parser.add_option('--personality', dest='personalities',
                          action='append', default=[],
                          metavar='PATH[,SERVER PATH[,OWNER[,GROUP,[MODE]]]]',
                          help='add a personality file')
        parser.epilog = "If missing, optional personality values will be " \
                        "filled based on the file at PATH."
    
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
    """Update a server's name"""
    
    def main(self, server_id, new_name):
        self.client.update_server_name(int(server_id), new_name)


@command(api='compute')
class server_delete(object):
    """Delete a server"""
    
    def main(self, server_id):
        self.client.delete_server(int(server_id))


@command(api='compute')
class server_reboot(object):
    """Reboot a server"""
    
    def update_parser(self, parser):
        parser.add_option('-f', dest='hard', action='store_true',
                default=False, help='perform a hard reboot')
    
    def main(self, server_id):
        self.client.reboot_server(int(server_id), self.options.hard)


@command(api='cyclades')
class server_start(object):
    """Start a server"""
    
    def main(self, server_id):
        self.client.start_server(int(server_id))


@command(api='cyclades')
class server_shutdown(object):
    """Shutdown a server"""
    
    def main(self, server_id):
        self.client.shutdown_server(int(server_id))


@command(api='cyclades')
class server_console(object):
    """Get a VNC console"""
    
    def main(self, server_id):
        reply = self.client.get_server_console(int(server_id))
        print_dict(reply)


@command(api='cyclades')
class server_firewall(object):
    """Set the server's firewall profile"""
    
    def main(self, server_id, profile):
        self.client.set_firewall_profile(int(server_id), profile)


@command(api='cyclades')
class server_addr(object):
    """List a server's addresses"""
    
    def main(self, server_id, network=None):
        reply = self.client.list_server_addresses(int(server_id), network)
        margin = max(len(x['name']) for x in reply)
        print_addresses(reply, margin)


@command(api='compute')
class server_meta(object):
    """Get a server's metadata"""
    
    def main(self, server_id, key=None):
        reply = self.client.get_server_metadata(int(server_id), key)
        print_dict(reply)


@command(api='compute')
class server_addmeta(object):
    """Add server metadata"""
    
    def main(self, server_id, key, val):
        reply = self.client.create_server_metadata(int(server_id), key, val)
        print_dict(reply)


@command(api='compute')
class server_setmeta(object):
    """Update server's metadata"""
    
    def main(self, server_id, key, val):
        metadata = {key: val}
        reply = self.client.update_server_metadata(int(server_id), **metadata)
        print_dict(reply)


@command(api='compute')
class server_delmeta(object):
    """Delete server metadata"""
    
    def main(self, server_id, key):
        self.client.delete_server_metadata(int(server_id), key)


@command(api='cyclades')
class server_stats(object):
    """Get server statistics"""
    
    def main(self, server_id):
        reply = self.client.get_server_stats(int(server_id))
        print_dict(reply, exclude=('serverRef',))


@command(api='compute')
class flavor_list(object):
    """List flavors"""
    
    def update_parser(self, parser):
        parser.add_option('-l', dest='detail', action='store_true',
                default=False, help='show detailed output')
    
    def main(self):
        flavors = self.client.list_flavors(self.options.detail)
        print_items(flavors)


@command(api='compute')
class flavor_info(object):
    """Get flavor details"""
    
    def main(self, flavor_id):
        flavor = self.client.get_flavor_details(int(flavor_id))
        print_dict(flavor)


@command(api='compute')
class image_list(object):
    """List images"""
    
    def update_parser(self, parser):
        parser.add_option('-l', dest='detail', action='store_true',
                default=False, help='show detailed output')
    
    def main(self):
        images = self.client.list_images(self.options.detail)
        print_items(images)


@command(api='compute')
class image_info(object):
    """Get image details"""
    
    def main(self, image_id):
        image = self.client.get_image_details(image_id)
        print_dict(image)


@command(api='compute')
class image_delete(object):
    """Delete image"""
    
    def main(self, image_id):
        self.client.delete_image(image_id)


@command(api='compute')
class image_meta(object):
    """Get image metadata"""
    
    def main(self, image_id, key=None):
        reply = self.client.get_image_metadata(image_id, key)
        print_dict(reply)


@command(api='compute')
class image_addmeta(object):
    """Add image metadata"""
    
    def main(self, image_id, key, val):
        reply = self.client.create_image_metadata(image_id, key, val)
        print_dict(reply)


@command(api='compute')
class image_setmeta(object):
    """Update image metadata"""
    
    def main(self, image_id, key, val):
        metadata = {key: val}
        reply = self.client.update_image_metadata(image_id, **metadata)
        print_dict(reply)


@command(api='compute')
class image_delmeta(object):
    """Delete image metadata"""
    
    def main(self, image_id, key):
        self.client.delete_image_metadata(image_id, key)


@command(api='cyclades')
class network_list(object):
    """List networks"""
    
    def update_parser(self, parser):
        parser.add_option('-l', dest='detail', action='store_true',
                default=False, help='show detailed output')
    
    def main(self):
        networks = self.client.list_networks(self.options.detail)
        print_items(networks)


@command(api='cyclades')
class network_create(object):
    """Create a network"""
    
    def main(self, name):
        reply = self.client.create_network(name)
        print_dict(reply)


@command(api='cyclades')
class network_info(object):
    """Get network details"""
    
    def main(self, network_id):
        network = self.client.get_network_details(network_id)
        print_dict(network)


@command(api='cyclades')
class network_rename(object):
    """Update network name"""
    
    def main(self, network_id, new_name):
        self.client.update_network_name(network_id, new_name)


@command(api='cyclades')
class network_delete(object):
    """Delete a network"""
    
    def main(self, network_id):
        self.client.delete_network(network_id)


@command(api='cyclades')
class network_connect(object):
    """Connect a server to a network"""
    
    def main(self, server_id, network_id):
        self.client.connect_server(server_id, network_id)


@command(api='cyclades')
class network_disconnect(object):
    """Disconnect a server from a network"""
    
    def main(self, server_id, network_id):
        self.client.disconnect_server(server_id, network_id)


@command(api='image')
class glance_list(object):
    """List images"""
    
    def update_parser(self, parser):
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
    """Get image metadata"""
    
    def main(self, image_id):
        image = self.client.get_meta(image_id)
        print_dict(image)


@command(api='image')
class glance_register(object):
    """Register an image"""
    
    def update_parser(self, parser):
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
                    'owner', 'size'):
            val = getattr(self.options, key)
            if val is not None:
                params[key] = val
        
        if self.options.is_public:
            params['is_public'] = 'true'
        
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
    """Get image members"""
    
    def main(self, image_id):
        members = self.client.list_members(image_id)
        for member in members:
            print member['member_id']


@command(api='image')
class glance_shared(object):
    """List shared images"""
    
    def main(self, member):
        images = self.client.list_shared(member)
        for image in images:
            print image['image_id']


@command(api='image')
class glance_addmember(object):
    """Add a member to an image"""
    
    def main(self, image_id, member):
        self.client.add_member(image_id, member)


@command(api='image')
class glance_delmember(object):
    """Remove a member from an image"""
    
    def main(self, image_id, member):
        self.client.remove_member(image_id, member)


@command(api='image')
class glance_setmembers(object):
    """Set the members of an image"""
    
    def main(self, image_id, *member):
        self.client.set_members(image_id, member)


class _store_account_command(object):
    """Base class for account level storage commands"""
    
    def update_parser(self, parser):
        parser.add_option('--account', dest='account', metavar='NAME',
                          help="Specify an account to use")
    
    def progress(self, message):
        """Return a generator function to be used for progress tracking"""
        
        MESSAGE_LENGTH = 25
        MAX_PROGRESS_LENGTH = 32
        
        def progress_gen(n):
            msg = message.ljust(MESSAGE_LENGTH)
            width = min(n, MAX_PROGRESS_LENGTH)
            hide = self.config.get('global', 'silent') or (n < 2)
            for i in progress.bar(range(n), msg, width, hide):
                yield
            yield
        
        return progress_gen
    
    def main(self):
        if self.options.account is not None:
            self.client.account = self.options.account


class _store_container_command(_store_account_command):
    """Base class for container level storage commands"""
    
    def update_parser(self, parser):
        super(_store_container_command, self).update_parser(parser)
        parser.add_option('--container', dest='container', metavar='NAME',
                          help="Specify a container to use")
    
    def main(self):
        super(_store_container_command, self).main()
        if self.options.container is not None:
            self.client.container = self.options.container


@command(api='storage')
class store_create(_store_account_command):
    """Create a container"""
    
    def main(self, container):
        if self.options.account:
            self.client.account = self.options.account
        self.client.create_container(container)


@command(api='storage')
class store_container(_store_account_command):
    """Get container info"""
    
    def main(self, container):
        if self.options.account:
            self.client.account = self.options.account
        reply = self.client.get_container_meta(container)
        print_dict(reply)


@command(api='storage')
class store_list(_store_container_command):
    """List objects"""
    
    def format_size(self, size):
        units = ('B', 'K', 'M', 'G', 'T')
        size = float(size)
        for unit in units:
            if size <= 1024:
                break
            size /= 1024
        s = ('%.1f' % size).rstrip('.0')
        return s + unit
    
    
    def main(self, path=''):
        super(store_list, self).main()
        for object in self.client.list_objects():
            size = self.format_size(object['bytes'])
            print '%6s %s' % (size, object['name'])
        

@command(api='storage')
class store_upload(_store_container_command):
    """Upload a file"""
    
    def main(self, path, remote_path=None):
        super(store_upload, self).main()
        
        if remote_path is None:
            remote_path = basename(path)
        with open(path) as f:
            hash_cb = self.progress('Calculating block hashes')
            upload_cb = self.progress('Uploading blocks')
            self.client.create_object(remote_path, f, hash_cb=hash_cb,
                                      upload_cb=upload_cb)


@command(api='storage')
class store_download(_store_container_command):
    """Download a file"""
        
    def main(self, remote_path, local_path='-'):
        super(store_download, self).main()
        
        f, size = self.client.get_object(remote_path)
        out = open(local_path, 'w') if local_path != '-' else stdout
        
        blocksize = 4 * 1024**2
        nblocks = 1 + (size - 1) // blocksize
        
        cb = self.progress('Downloading blocks') if local_path != '-' else None
        if cb:
            gen = cb(nblocks)
            gen.next()
        
        data = f.read(blocksize)
        while data:
            out.write(data)
            data = f.read(blocksize)
            if cb:
                gen.next()


@command(api='storage')
class store_delete(_store_container_command):
    """Delete a file"""
    
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


def add_handler(name, level, prefix=''):
    h = logging.StreamHandler()
    fmt = logging.Formatter(prefix + '%(message)s')
    h.setFormatter(fmt)
    logger = logging.getLogger(name)
    logger.addHandler(h)
    logger.setLevel(level)


def main():
    parser = OptionParser(add_help_option=False)
    parser.usage = '%prog <group> <command> [options]'
    parser.add_option('-h', '--help', dest='help', action='store_true',
                      default=False,
                      help="Show this help message and exit")
    parser.add_option('--config', dest='config', metavar='PATH',
                      help="Specify the path to the configuration file")
    parser.add_option('-d', '--debug', dest='debug', action='store_true',
                      default=False,
                      help="Include debug output")
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
    
    options, arguments = parser.parse_args(argv)
    
    if options.help:
        parser.print_help()
        exit(0)
    
    if options.silent:
        add_handler('', logging.CRITICAL)
    elif options.debug:
        add_handler('requests', logging.INFO, prefix='* ')
        add_handler('clients.send', logging.DEBUG, prefix='> ')
        add_handler('clients.recv', logging.DEBUG, prefix='< ')
    elif options.verbose:
        add_handler('requests', logging.INFO, prefix='* ')
        add_handler('clients.send', logging.INFO, prefix='> ')
        add_handler('clients.recv', logging.INFO, prefix='< ')
    elif options.include:
        add_handler('clients.recv', logging.INFO)
    else:
        add_handler('', logging.WARNING)
    
    api = cmd.api
    if api in ('compute', 'cyclades'):
        url = config.get('compute', 'url')
        token = config.get('compute', 'token') or config.get('global', 'token')
        if config.getboolean('compute', 'cyclades_extensions'):
            cmd.client = clients.cyclades(url, token)
        else:
            cmd.client = clients.compute(url, token)
    elif api in ('storage', 'pithos'):
        url = config.get('storage', 'url')
        token = config.get('storage', 'token') or config.get('global', 'token')
        account = config.get('storage', 'account')
        container = config.get('storage', 'container')
        if config.getboolean('storage', 'pithos_extensions'):
            cmd.client = clients.pithos(url, token, account, container)
        else:
            cmd.client = clients.storage(url, token, account, container)
    elif api == 'image':
        url = config.get('image', 'url')
        token = config.get('image', 'token') or config.get('global', 'token')
        cmd.client = clients.image(url, token)
    
    cmd.options = options
    cmd.config = config
    
    try:
        ret = cmd.main(*arguments[3:])
        exit(ret)
    except TypeError as e:
        if e.args and e.args[0].startswith('main()'):
            parser.print_help()
            exit(1)
        else:
            raise
    except clients.ClientError as err:
        if err.status == 404:
            color = yellow
        elif 500 <= err.status < 600:
            color = magenta
        else:
            color = red
        
        puts_err(color(err.message))
        if err.details and (options.verbose or options.debug):
            puts_err(err.details)
        exit(2)
    except ConnectionError as err:
        puts_err(red("Connection error"))
        exit(1)


if __name__ == '__main__':
    main()
