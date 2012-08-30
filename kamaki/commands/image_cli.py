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
# or implied, of GRNET S.A.command

from kamaki.cli import command, set_api_description
from kamaki.utils import print_dict, print_items
set_api_description('image', "Compute/Cyclades or Glance API image commands")
from kamaki.clients.image import ImageClient, ClientError
from .cli_utils import raiseCLIError

class _init_image(object):
    def main(self):
        try:
            token = self.config.get('image', 'token') or self.config.get('global', 'token')
            base_url = self.config.get('image', 'url') or self.config.get('global', 'url')
            self.client = ImageClient(base_url=base_url, token=token)
        except ClientError as err:
            raiseCLIError(err)

@command()
class image_public(_init_image):
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
    	super(self.__class__, self).main()
        filters = {}
        for filter in ('container_format', 'disk_format', 'name', 'size_min',
                       'size_max', 'status'):
            val = getattr(self.args, filter, None)
            if val is not None:
                filters[filter] = val

        order = self.args.order or ''
        try:
            images = self.client.list_public(self.args.detail,
                filters=filters, order=order)
        except ClientError as err:
            raiseCLIError(err)
        print_items(images, title=('name',))

@command()
class image_meta(_init_image):
    """Get image metadata"""

    def main(self, image_id):
    	super(self.__class__, self).main()
        try:
            image = self.client.get_meta(image_id)
        except ClientError as err:
            raiseCLIError(err)
        print_dict(image)

@command()
class image_register(_init_image):
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
    	super(self.__class__, self).main()
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
                raise CLIError(message="Invalid property '%s'" % property, importance=1)
            properties[key.strip()] = val.strip()

        try:
            self.client.register(name, location, params, properties)
        except ClientError as err:
            raiseCLIError(err)

@command()
class image_members(_init_image):
    """Get image members"""

    def main(self, image_id):
    	super(self.__class__, self).main()
        try:
            members = self.client.list_members(image_id)
        except ClientError as err:
            raiseCLIError(err)
        for member in members:
            print(member['member_id'])

@command()
class image_shared(_init_image):
    """List shared images"""

    def main(self, member):
    	super(self.__class__, self).main()
        try:
            images = self.client.list_shared(member)
        except ClientError as err:
            raiseCLIError(err)
        for image in images:
            print(image['image_id'])

@command()
class image_addmember(_init_image):
    """Add a member to an image"""

    def main(self, image_id, member):
    	super(self.__class__, self).main()
        try:
            self.client.add_member(image_id, member)
        except ClientError as err:
            raiseCLIError(err)

@command()
class image_delmember(_init_image):
    """Remove a member from an image"""

    def main(self, image_id, member):
        super(self.__class__, self).main()
        try:
            self.client.remove_member(image_id, member)
        except ClientError as err:
            raiseCLIError(err)

@command()
class image_setmembers(_init_image):
    """Set the members of an image"""

    def main(self, image_id, *member):
        super(self.__class__, self).main()
        try:
            self.client.set_members(image_id, member)
        except ClientError as err:
            raiseCLIError(err)
