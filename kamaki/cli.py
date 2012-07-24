#!/usr/bin/env python

# Copyright 2011-2012 GRNET S.A. All rights reserved.
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
//This command will be named 'list' under group 'server'
...

@command(api='compute', name='ls')
class server_list(object):
//This command will be named 'ls' under group 'server'
...

The docstring of a command class will be used as the command description in
help messages, unless overriden with the 'description' decorator argument.

The syntax of a command will be generated dynamically based on the signature
of the 'main' method, unless overriden with the 'syntax' decorator argument:

def main(self, server_id, network=None):
// This syntax of this command will be: '<server id> [network]'
...

The order of commands is important, it will be preserved in the help output.
"""

from __future__ import print_function

import inspect
import logging
import sys

from argparse import ArgumentParser
from base64 import b64encode
from os.path import abspath, basename, exists
from sys import exit, stdout, stderr

try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

from colors import magenta, red, yellow
from progress.bar import IncrementalBar
from requests.exceptions import ConnectionError

from . import clients
from .config import Config
from .utils import print_list, print_dict, print_items, format_size

_commands = OrderedDict()


GROUPS = {
    'config': "Configuration commands",
    'server': "Compute API server commands",
    'flavor': "Compute API flavor commands",
    'image': "Compute or Glance API image commands",
    'network': "Compute API network commands (Cyclades extension)",
    'store': "Storage API commands",
    'astakos': "Astakos API commands"}

class ProgressBar(IncrementalBar):
    suffix = '%(percent)d%% - %(eta)ds'

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
            required = ' '.join('<%s>' % x.replace('____', '[:').replace('___', ':').replace('__',']').replace('_', ' ') for x in args[:n])
            optional = ' '.join('[%s]' % x.replace('____', '[:').replace('___', ':').replace('__', ']').replace('_', ' ') for x in args[n:])
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
        parser.add_argument('-a', dest='all', action='store_true',
                          default=False, help='include default values')

    def main(self):
        include_defaults = self.args.all
        for section in sorted(self.config.sections()):
            items = self.config.items(section, include_defaults)
            for key, val in sorted(items):
                print('%s.%s = %s' % (section, key, val))

@command(api='config')
class config_get(object):
    """Show a configuration option"""

    def main(self, option):
        section, sep, key = option.rpartition('.')
        section = section or 'global'
        value = self.config.get(section, key)
        if value is not None:
            print(value)

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
        parser.add_argument('-l', dest='detail', action='store_true',
                default=False, help='show detailed output')

    def main(self):
        servers = self.client.list_servers(self.args.detail)
        print_items(servers)

@command(api='compute')
class server_info(object):
    """Get server details"""

    def main(self, server_id):
        try:
            server = self.client.get_server_details(int(server_id))
        except ValueError:
            print(yellow('Server id must be a base10 integer'))
            return
        print_dict(server)

@command(api='compute')
class server_create(object):
    """Create a server"""

    def update_parser(self, parser):
        parser.add_argument('--personality', dest='personalities',
                          action='append', default=[],
                          metavar='PATH[,SERVER PATH[,OWNER[,GROUP,[MODE]]]]',
                          help='add a personality file')

    def main(self, name, flavor_id, image_id):
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

@command(api='compute')
class server_rename(object):
    """Update a server's name"""

    def main(self, server_id, new_name):
        try:
            self.client.update_server_name(int(server_id), new_name)
        except ValueError:
            print(yellow('Server id must be a base10 integer'))

@command(api='compute')
class server_delete(object):
    """Delete a server"""

    def main(self, server_id):
        try:
            self.client.delete_server(int(server_id))
        except ValueError:
            print(yellow('Server id must be a base10 integer'))

@command(api='compute')
class server_reboot(object):
    """Reboot a server"""

    def update_parser(self, parser):
        parser.add_argument('-f', dest='hard', action='store_true',
                default=False, help='perform a hard reboot')

    def main(self, server_id):
        try:
            self.client.reboot_server(int(server_id), self.args.hard)
        except ValueError:
            print(yellow('Server id must be a base10 integer'))

@command(api='cyclades')
class server_start(object):
    """Start a server"""

    def main(self, server_id):
        try:
            self.client.start_server(int(server_id))
        except ValueError:
            print(yellow('Server id must be a base10 integer'))

@command(api='cyclades')
class server_shutdown(object):
    """Shutdown a server"""

    def main(self, server_id):
        try:
            self.client.shutdown_server(int(server_id))
        except ValueError:
            print(yellow('Server id must be a base10 integer'))

@command(api='cyclades')
class server_console(object):
    """Get a VNC console"""

    def main(self, server_id):
        try:
            reply = self.client.get_server_console(int(server_id))
        except ValueError:
            print(yellow('Server id must be a base10 integer'))
            return
        print_dict(reply)

@command(api='cyclades')
class server_firewall(object):
    """Set the server's firewall profile"""

    def main(self, server_id, profile):
        try:
            self.client.set_firewall_profile(int(server_id), profile)
        except ValueError:
            print(yellow('Server id must be a base10 integer'))

@command(api='cyclades')
class server_addr(object):
    """List a server's addresses"""

    def main(self, server_id, network=None):
        try:
            reply = self.client.list_server_nic_details(int(server_id), network)
        except ValueError:
            print(yellow('Server id must be a base10 integer'))
            return
        print_list(reply)

@command(api='compute')
class server_meta(object):
    """Get a server's metadata"""

    def main(self, server_id, key=None):
        try:
            reply = self.client.get_server_metadata(int(server_id), key)
        except ValueError:
            print(yellow('Server id must be a base10 integer'))
            return
        print_dict(reply)

@command(api='compute')
class server_addmeta(object):
    """Add server metadata"""

    def main(self, server_id, key, val):
        try:
            reply = self.client.create_server_metadata(int(server_id), key, val)
        except ValueError:
            print(yellow('Server id must be a base10 integer'))
            return
        print_dict(reply)

@command(api='compute')
class server_setmeta(object):
    """Update server's metadata"""

    def main(self, server_id, key, val):
        metadata = {key: val}
        try:
            reply = self.client.update_server_metadata(int(server_id), **metadata)
        except ValueError:
            print(yellow('Server id must be a base10 integer'))
            return
        print_dict(reply)

@command(api='compute')
class server_delmeta(object):
    """Delete server metadata"""

    def main(self, server_id, key):
        try:
            self.client.delete_server_metadata(int(server_id), key)
        except ValueError:
            print(yellow('Server id must be a base10 integer'))
            return

@command(api='cyclades')
class server_stats(object):
    """Get server statistics"""

    def main(self, server_id):
        try:
            reply = self.client.get_server_stats(int(server_id))
        except ValueError:
            print(yellow('Server id must be a base10 integer'))
            return
        print_dict(reply, exclude=('serverRef',))

@command(api='compute')
class flavor_list(object):
    """List flavors"""

    def update_parser(self, parser):
        parser.add_argument('-l', dest='detail', action='store_true',
                default=False, help='show detailed output')

    def main(self):
        flavors = self.client.list_flavors(self.args.detail)
        print_items(flavors)

@command(api='compute')
class flavor_info(object):
    """Get flavor details"""

    def main(self, flavor_id):
        try:
            flavor = self.client.get_flavor_details(int(flavor_id))
        except ValueError:
            print(yellow('Flavor id must be a base10 integer'))
            return
        print_dict(flavor)

@command(api='compute')
class image_list(object):
    """List images"""

    def update_parser(self, parser):
        parser.add_argument('-l', dest='detail', action='store_true',
                default=False, help='show detailed output')

    def main(self):
        images = self.client.list_images(self.args.detail)
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
class image_properties(object):
    """Get image properties"""

    def main(self, image_id, key=None):
        reply = self.client.get_image_metadata(image_id, key)
        print_dict(reply)

@command(api='compute')
class image_addproperty(object):
    """Add an image property"""

    def main(self, image_id, key, val):
        reply = self.client.create_image_metadata(image_id, key, val)
        print_dict(reply)

@command(api='compute')
class image_setproperty(object):
    """Update an image property"""

    def main(self, image_id, key, val):
        metadata = {key: val}
        reply = self.client.update_image_metadata(image_id, **metadata)
        print_dict(reply)

@command(api='compute')
class image_delproperty(object):
    """Delete an image property"""

    def main(self, image_id, key):
        self.client.delete_image_metadata(image_id, key)

@command(api='cyclades')
class network_list(object):
    """List networks"""

    def update_parser(self, parser):
        parser.add_argument('-l', dest='detail', action='store_true',
                default=False, help='show detailed output')

    def main(self):
        networks = self.client.list_networks(self.args.detail)
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
    """Disconnect a nic that connects a server to a network"""

    def main(self, nic_id):
        try:
            server_id = nic_id.split('-')[1]
            self.client.disconnect_server(server_id, nic_id)
        except IndexError:
            print(yellow('nid_id format: nic-<server_id>-<nic_index>'))

@command(api='image')
class image_public(object):
    """List public images"""

    def update_parser(self, parser):
        parser.add_argument('-l', dest='detail', action='store_true',
                default=False, help='show detailed output')
        parser.add_argument('--container-format', dest='container_format',
                metavar='FORMAT', help='filter by container format')
        parser.add_argument('--disk-format', dest='disk_format',
                metavar='FORMAT', help='filter by disk format')
        parser.add_argument('--name', dest='name', metavar='NAME',
                help='filter by name')
        parser.add_argument('--size-min', dest='size_min', metavar='BYTES',
                help='filter by minimum size')
        parser.add_argument('--size-max', dest='size_max', metavar='BYTES',
                help='filter by maximum size')
        parser.add_argument('--status', dest='status', metavar='STATUS',
                help='filter by status')
        parser.add_argument('--order', dest='order', metavar='FIELD',
                help='order by FIELD (use a - prefix to reverse order)')

    def main(self):
        filters = {}
        for filter in ('container_format', 'disk_format', 'name', 'size_min',
                       'size_max', 'status'):
            val = getattr(self.args, filter, None)
            if val is not None:
                filters[filter] = val

        order = self.args.order or ''
        images = self.client.list_public(self.args.detail, filters=filters,
                                         order=order)
        print_items(images, title=('name',))

@command(api='image')
class image_meta(object):
    """Get image metadata"""

    def main(self, image_id):
        image = self.client.get_meta(image_id)
        print_dict(image)

@command(api='image')
class image_register(object):
    """Register an image"""

    def update_parser(self, parser):
        parser.add_argument('--checksum', dest='checksum', metavar='CHECKSUM',
                help='set image checksum')
        parser.add_argument('--container-format', dest='container_format',
                metavar='FORMAT', help='set container format')
        parser.add_argument('--disk-format', dest='disk_format',
                metavar='FORMAT', help='set disk format')
        parser.add_argument('--id', dest='id',
                metavar='ID', help='set image ID')
        parser.add_argument('--owner', dest='owner',
                metavar='USER', help='set image owner (admin only)')
        parser.add_argument('--property', dest='properties', action='append',
                metavar='KEY=VAL',
                help='add a property (can be used multiple times)')
        parser.add_argument('--public', dest='is_public', action='store_true',
                help='mark image as public')
        parser.add_argument('--size', dest='size', metavar='SIZE',
                help='set image size')

    def main(self, name, location):
        if not location.startswith('pithos://'):
            account = self.config.get('storage', 'account').split()[0]
            if account[-1] == '/':
                account = account[:-1]
            container = self.config.get('storage', 'container')
            location = 'pithos://%s/%s'%(account, location) \
                if container is None or len(container) == 0 \
                else 'pithos://%s/%s/%s' % (account, container, location)

        params = {}
        for key in ('checksum', 'container_format', 'disk_format', 'id',
                    'owner', 'size'):
            val = getattr(self.args, key)
            if val is not None:
                params[key] = val

        if self.args.is_public:
            params['is_public'] = 'true'

        properties = {}
        for property in self.args.properties or []:
            key, sep, val = property.partition('=')
            if not sep:
                print("Invalid property '%s'" % property)
                return 1
            properties[key.strip()] = val.strip()

        self.client.register(name, location, params, properties)

@command(api='image')
class image_members(object):
    """Get image members"""

    def main(self, image_id):
        members = self.client.list_members(image_id)
        for member in members:
            print(member['member_id'])

@command(api='image')
class image_shared(object):
    """List shared images"""

    def main(self, member):
        images = self.client.list_shared(member)
        for image in images:
            print(image['image_id'])

@command(api='image')
class image_addmember(object):
    """Add a member to an image"""

    def main(self, image_id, member):
        self.client.add_member(image_id, member)

@command(api='image')
class image_delmember(object):
    """Remove a member from an image"""

    def main(self, image_id, member):
        self.client.remove_member(image_id, member)

@command(api='image')
class image_setmembers(object):
    """Set the members of an image"""

    def main(self, image_id, *member):
        self.client.set_members(image_id, member)

class _store_account_command(object):
    """Base class for account level storage commands"""

    def update_parser(self, parser):
        parser.add_argument('--account', dest='account', metavar='NAME',
                          help="Specify an account to use")

    def progress(self, message):
        """Return a generator function to be used for progress tracking"""

        MESSAGE_LENGTH = 25

        def progress_gen(n):
            msg = message.ljust(MESSAGE_LENGTH)
            for i in ProgressBar(msg).iter(range(n)):
                yield
            yield

        return progress_gen

    def main(self):
        if self.args.account is not None:
            self.client.account = self.args.account

class _store_container_command(_store_account_command):
    """Base class for container level storage commands"""

    def update_parser(self, parser):
        super(_store_container_command, self).update_parser(parser)
        parser.add_argument('--container', dest='container', metavar='NAME',
                          help="Specify a container to use")

    def extract_container_and_path(self, container_with_path):
        assert isinstance(container_with_path, str)
        cnp = container_with_path.split(':')
        self.container = cnp[0]
        self.path = cnp[1] if len(cnp) > 1 else None
            

    def main(self, container_with_path=None):
        super(_store_container_command, self).main()
        if container_with_path is not None:
            self.extract_container_and_path(container_with_path)
            self.client.container = self.container
        elif self.args.container is not None:
            self.client.container = self.args.container
        else:
            self.container = None

@command(api='storage')
class store_list(_store_container_command):
    """List containers, object trees or objects in a directory
    """

    def print_objects(self, object_list):
        for obj in object_list:
            size = format_size(obj['bytes']) if 0 < obj['bytes'] else 'D'
            print('%6s %s' % (size, obj['name']))

    def print_containers(self, container_list):
        for container in container_list:
            size = format_size(container['bytes'])
            print('%s (%s, %s objects)' % (container['name'], size, container['count']))
            
    def main(self, container____path__=None):
        super(store_list, self).main(container____path__)
        if self.container is None:
            reply = self.client.list_containers()
            self.print_containers(reply)
        else:
            reply = self.client.list_objects() if self.path is None \
                else self.client.list_objects_in_path(path_prefix=self.path)
            self.print_objects(reply)

@command(api='storage')
class store_create(_store_container_command):
    """Create a container or a directory object"""

    def main(self, container____directory__):
        super(store_create, self).main(container____directory__)
        if self.path is None:
            self.client.create_container(self.container)
        else:
            self.client.create_directory(self.path)

@command(api='storage')
class store_copy(_store_container_command):
    """Copy an object"""

    def main(self, source_container___path, destination_container____path__):
        super(store_copy, self).main(source_container___path)
        dst = destination_container____path__.split(':')
        dst_cont = dst[0]
        dst_path = dst[1] if len(dst) > 1 else False
        self.client.copy_object(src_container = self.container, src_object = self.path, dst_container = dst_cont, dst_object = dst_path)

@command(api='storage')
class store_move(_store_container_command):
    """Move an object"""

    def main(self, source_container___path, destination_container____path__):
        super(store_move, self).main(source_container___path)
        dst = destination_container____path__.split(':')
        dst_cont = dst[0]
        dst_path = dst[1] if len(dst) > 1 else False
        self.client.move_object(src_container = self.container, src_object = self.path, dst_container = dst_cont, dst_object = dst_path)

@command(api='storage')
class store_append(_store_container_command):
    """Append local file to (existing) remote object"""

    def main(self, local_path, container___path):
        super(store_append, self).main(container___path)
        f = open(local_path, 'r')
        upload_cb = self.progress('Appending blocks')
        self.client.append_object(object=self.path, source_file = f, upload_cb = upload_cb)

@command(api='storage')
class store_truncate(_store_container_command):
    """Truncate remote file up to a size"""

    def main(self, container___path, size=0):
        super(store_truncate, self).main(container___path)
        self.client.truncate_object(self.path, size)

@command(api='storage')
class store_overwrite(_store_container_command):
    """Overwrite part (from start to end) of a remote file"""

    def main(self, local_path, container___path, start, end):
        super(store_overwrite, self).main(container___path)
        f = open(local_path, 'r')
        upload_cb = self.progress('Overwritting blocks')
        self.client.overwrite_object(object=self.path, start=start, end=end, source_file=f, upload_cb = upload_cb)

@command(api='storage')
class store_upload(_store_container_command):
    """Upload a file"""

    def main(self, local_path, container____path__):
        super(store_upload, self).main(container____path__)
        remote_path = basename(local_path) if self.path is None else self.path
        with open(local_path) as f:
            hash_cb = self.progress('Calculating block hashes')
            upload_cb = self.progress('Uploading blocks')
            self.client.create_object(remote_path, f, hash_cb=hash_cb, upload_cb=upload_cb)

@command(api='storage')
class store_download(_store_container_command):
    """Download a file"""

    def main(self, container___path, local_path='-'):
        super(store_download, self).main(container___path)
        f, size = self.client.get_object(self.path)
        out = open(local_path, 'w') if local_path != '-' else stdout

        blocksize = 4 * 1024 ** 2
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
    """Delete a container [or an object]"""

    def main(self, container____path__):
        super(store_delete, self).main(container____path__)
        if self.path is None:
            self.client.delete_container(self.container)
        else:
            self.client.delete_object(self.path)

@command(api='storage')
class store_purge(_store_account_command):
    """Purge a container"""

    def main(self, container):
        super(store_purge, self).main()
        self.client.container = container
        self.client.purge_container()

@command(api='storage')
class store_publish(_store_container_command):
    """Publish an object"""

    def main(self, container___path):
        super(store_publish, self).main(container___path)
        self.client.publish_object(self.path)

@command(api='storage')
class store_unpublish(_store_container_command):
    """Unpublish an object"""

    def main(self, container___path):
        super(store_unpublish, self).main(container___path)
        self.client.unpublish_object(self.path)

@command(api='storage')
class store_permitions(_store_container_command):
    """Get object read/write permitions"""

    def main(self, container___path):
        super(store_permitions, self).main(container___path)
        reply = self.client.get_object_sharing(self.path)
        print_dict(reply)

@command(api='storage')
class store_setpermitions(_store_container_command):
    """Set sharing permitions"""

    def main(self, container___path, *permitions):
        super(store_setpermitions, self).main(container___path)
        read = False
        write = False
        for perms in permitions:
            splstr = perms.split('=')
            if 'read' == splstr[0]:
                read = [user_or_group.strip() for user_or_group in splstr[1].split(',')]
            elif 'write' == splstr[0]:
                write = [user_or_group.strip() for user_or_group in splstr[1].split(',')]
            else:
                read = False
                write = False
        if not read and not write:
            print(u'Read/write permitions are given in the following format:')
            print(u'\tread=username,groupname,...')
            print(u'and/or')
            print(u'\twrite=username,groupname,...')
            return
        self.client.set_object_sharing(self.path, read_permition=read, write_permition=write)

@command(api='storage')
class store_delpermitions(_store_container_command):
    """Delete all sharing permitions"""

    def main(self, container___path):
        super(store_delpermitions, self).main(container___path)
        self.client.del_object_sharing(self.path)

@command(api='storage')
class store_info(_store_container_command):
    """Get information for account [, container [or object]]"""

    def main(self, container____path__=None):
        super(store_info, self).main(container____path__)
        if self.container is None:
            reply = self.client.get_account_info()
        elif self.path is None:
            reply = self.client.get_container_info(self.container)
        else:
            reply = self.client.get_object_info(self.path)
        print_dict(reply)

@command(api='storage')
class store_meta(_store_container_command):
    """Get custom meta-content for account [, container [or object]]"""

    def main(self, container____path__ = None):
        super(store_meta, self).main(container____path__)
        if self.container is None:
            reply = self.client.get_account_meta()
        elif self.path is None:
            reply = self.client.get_container_object_meta(self.container)
            print_dict(reply)
            reply = self.client.get_container_meta(self.container)
        else:
            reply = self.client.get_object_meta(self.path)
        print_dict(reply)

@command(api='storage')
class store_setmeta(_store_container_command):
    """Set a new metadatum for account [, container [or object]]"""

    def main(self, metakey, metavalue, container____path__=None):
        super(store_setmeta, self).main(container____path__)
        if self.container is None:
            self.client.set_account_meta({metakey:metavalue})
        elif self.path is None:
            self.client.set_container_meta({metakey:metavalue})
        else:
            self.client.set_object_meta(self.path, {metakey:metavalue})

@command(api='storage')
class store_delmeta(_store_container_command):
    """Delete an existing metadatum of account [, container [or object]]"""

    def main(self, metakey, container____path__=None):
        super(store_delmeta, self).main(container____path__)
        if self.container is None:
            self.client.del_account_meta(metakey)
        elif self.path is None:
            self.client.del_container_meta(metakey)
        else:
            self.client.delete_object_meta(metakey, self.path)

@command(api='storage')
class store_quota(_store_account_command):
    """Get  quota for account [or container]"""

    def main(self, container = None):
        super(store_quota, self).main()
        if container is None:
            reply = self.client.get_account_quota()
        else:
            reply = self.client.get_container_quota(container)
        print_dict(reply)

@command(api='storage')
class store_setquota(_store_account_command):
    """Set new quota (in KB) for account [or container]"""

    def main(self, quota, container = None):
        super(store_setquota, self).main()
        if container is None:
            self.client.set_account_quota(quota)
        else:
            self.client.container = container
            self.client.set_container_quota(quota)

@command(api='storage')
class store_versioning(_store_account_command):
    """Get  versioning for account [or container ]"""

    def main(self, container = None):
        super(store_versioning, self).main()
        if container is None:
            reply = self.client.get_account_versioning()
        else:
            reply = self.client.get_container_versioning(container)
        print_dict(reply)

@command(api='storage')
class store_setversioning(_store_account_command):
    """Set new versioning (auto, none) for account [or container]"""

    def main(self, versioning, container = None):
        super(store_setversioning, self).main()
        if container is None:
            self.client.set_account_versioning(versioning)
        else:
            self.client.container = container
            self.client.set_container_versioning(versioning)

@command(api='storage')
class store_test(_store_account_command):
    """Perform a developer-level custom test"""
    def main(self):
        super(store_test, self).main()
        self.client.container = 'testCo'

        r = self.client.object_put('lali', content_length=1, data='a',
            content_type='application/octet-stream', permitions={'read':'u1, u2', 'write':'u2, u3'})
        print(unicode(r))

@command(api='storage')
class store_group(_store_account_command):
    """Get user groups details for account"""

    def main(self):
        super(store_group, self).main()
        reply = self.client.get_account_group()
        print_dict(reply)

@command(api='storage')
class store_setgroup(_store_account_command):
    """Create/update a new user group on account"""

    def main(self, groupname, *users):
        super(store_setgroup, self).main()
        self.client.set_account_group(groupname, users)

@command(api='storage')
class store_delgroup(_store_account_command):
    """Delete a user group on an account"""

    def main(self, groupname):
        super(store_delgroup, self).main()
        self.client.del_account_group(groupname)

@command(api='astakos')
class astakos_authenticate(object):
    """Authenticate a user"""

    def main(self):
        reply = self.client.authenticate()
        print_dict(reply)

def print_groups():
    print('\nGroups:')
    for group in _commands:
        description = GROUPS.get(group, '')
        print(' ', group.ljust(12), description)

def print_commands(group):
    description = GROUPS.get(group, '')
    if description:
        print('\n' + description)

    print('\nCommands:')
    for name, cls in _commands[group].items():
        print(' ', name.ljust(14), cls.description)

def add_handler(name, level, prefix=''):
    h = logging.StreamHandler()
    fmt = logging.Formatter(prefix + '%(message)s')
    h.setFormatter(fmt)
    logger = logging.getLogger(name)
    logger.addHandler(h)
    logger.setLevel(level)

def main():
    exe = basename(sys.argv[0])
    parser = ArgumentParser(add_help=False)
    parser.prog = '%s <group> <command>' % exe
    parser.add_argument('-h', '--help', dest='help', action='store_true',
                      default=False,
                      help="Show this help message and exit")
    parser.add_argument('--config', dest='config', metavar='PATH',
                      help="Specify the path to the configuration file")
    parser.add_argument('-d', '--debug', dest='debug', action='store_true',
                      default=False,
                      help="Include debug output")
    parser.add_argument('-i', '--include', dest='include', action='store_true',
                      default=False,
                      help="Include protocol headers in the output")
    parser.add_argument('-s', '--silent', dest='silent', action='store_true',
                      default=False,
                      help="Silent mode, don't output anything")
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true',
                      default=False,
                      help="Make the operation more talkative")
    parser.add_argument('-V', '--version', dest='version', action='store_true',
                      default=False,
                      help="Show version number and quit")
    parser.add_argument('-o', dest='options', action='append',
                      default=[], metavar="KEY=VAL",
                      help="Override a config values")

    args, argv = parser.parse_known_args()

    if args.version:
        import kamaki
        print("kamaki %s" % kamaki.__version__)
        exit(0)

    config = Config(args.config) if args.config else Config()

    for option in args.options:
        keypath, sep, val = option.partition('=')
        if not sep:
            print("Invalid option '%s'" % option)
            exit(1)
        section, sep, key = keypath.partition('.')
        if not sep:
            print("Invalid option '%s'" % option)
            exit(1)
        config.override(section.strip(), key.strip(), val.strip())

    apis = set(['config'])
    for api in ('compute', 'image', 'storage', 'astakos'):
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

    group = argv.pop(0) if argv else None

    if not group:
        parser.print_help()
        print_groups()
        exit(0)

    if group not in _commands:
        parser.print_help()
        print_groups()
        exit(1)

    parser.prog = '%s %s <command>' % (exe, group)
    command = argv.pop(0) if argv else None

    if not command:
        parser.print_help()
        print_commands(group)
        exit(0)

    if command not in _commands[group]:
        parser.print_help()
        print_commands(group)
        exit(1)

    cmd = _commands[group][command]()

    parser.prog = '%s %s %s' % (exe, group, command)
    if cmd.syntax:
        parser.prog += '  %s' % cmd.syntax
    parser.description = cmd.description
    parser.epilog = ''
    if hasattr(cmd, 'update_parser'):
        cmd.update_parser(parser)

    args, argv = parser.parse_known_args()

    if args.help:
        parser.print_help()
        exit(0)

    if args.silent:
        add_handler('', logging.CRITICAL)
    elif args.debug:
        add_handler('requests', logging.INFO, prefix='* ')
        add_handler('clients.send', logging.DEBUG, prefix='> ')
        add_handler('clients.recv', logging.DEBUG, prefix='< ')
    elif args.verbose:
        add_handler('requests', logging.INFO, prefix='* ')
        add_handler('clients.send', logging.INFO, prefix='> ')
        add_handler('clients.recv', logging.INFO, prefix='< ')
    elif args.include:
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
    elif api == 'astakos':
        url = config.get('astakos', 'url')
        token = config.get('astakos', 'token') or config.get('global', 'token')
        cmd.client = clients.astakos(url, token)

    cmd.args = args
    cmd.config = config

    try:
        ret = cmd.main(*argv[2:])
        exit(ret)
    except TypeError as e:
        if e.args and e.args[0].startswith('main()'):
            parser.print_help()
            exit(1)
        else:
            raise
    except clients.ClientError as err:
        if err.status == 404:
            message = yellow(err.message)
        elif 500 <= err.status < 600:
            message = magenta(err.message)
        else:
            message = red(err.message)

        print(message, file=stderr)
        if err.details and (args.verbose or args.debug):
            print(err.details, file=stderr)
        exit(2)
    except ConnectionError as err:
        print(red("Connection error"), file=stderr)
        exit(1)

if __name__ == '__main__':
    main()
