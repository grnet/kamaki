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
# or implied, of GRNET S.A.command

from kamaki.cli import command
from kamaki.cli.command_tree import CommandTree
from kamaki.cli.errors import raiseCLIError
from kamaki.cli.utils import print_dict, print_items, bold
from kamaki.clients.image import ImageClient, ClientError
from kamaki.cli.argument import\
    FlagArgument, ValueArgument, KeyValueArgument, IntArgument
from kamaki.cli.commands.cyclades_cli import _init_cyclades
from kamaki.cli.commands import _command_init


image_cmds = CommandTree(
    'image',
    'Compute/Cyclades or Glance API image commands')
_commands = [image_cmds]


class _init_image(_command_init):
    def main(self):
        try:
            token = self.config.get('image', 'token')\
                or self.config.get('compute', 'token')\
                or self.config.get('global', 'token')
            base_url = self.config.get('image', 'url')\
                or self.config.get('compute', 'url')\
                or self.config.get('global', 'url')
            self.client = ImageClient(base_url=base_url, token=token)
        except Exception as err:
            raiseCLIError(err)


@command(image_cmds)
class image_public(_init_image):
    """List public images"""

    arguments = dict(
        detail=FlagArgument('show detailed output', '-l'),
        container_format=ValueArgument(
            'filter by container format',
            '--container-format'),
        disk_format=ValueArgument('filter by disk format', '--disk-format'),
        name=ValueArgument('filter by name', '--name'),
        size_min=IntArgument('filter by minimum size', '--size-min'),
        size_max=IntArgument('filter by maximum size', '--size-max'),
        status=ValueArgument('filter by status', '--status'),
        order=ValueArgument(
            'order by FIELD ( - to reverse order)',
            '--order',
            default='')
    )

    def main(self):
        super(self.__class__, self).main()
        filters = {}
        for arg in set(
            [
                'container_format',
                'disk_format',
                'name',
                'size_min',
                'size_max',
                'status'
            ]).intersection(self.arguments):
            filters[arg] = self[arg]

        order = self['order']
        detail = self['detail']
        try:
            images = self.client.list_public(detail, filters, order)
        except Exception as err:
            raiseCLIError(err)
        print_items(images, title=('name',), with_enumeration=True)


@command(image_cmds)
class image_meta(_init_image):
    """Get image metadata"""

    def main(self, image_id):
        super(self.__class__, self).main()
        try:
            image = self.client.get_meta(image_id)
        except ClientError as err:
            raiseCLIError(err)
        print_dict(image)


@command(image_cmds)
class image_register(_init_image):
    """(Re)Register an image
        call with --update to update image properties
    """

    arguments = dict(
        checksum=ValueArgument('set image checksum', '--checksum'),
        container_format=ValueArgument(
            'set container format',
            '--container-format'),
        disk_format=ValueArgument('set disk format', '--disk-format'),
        id=ValueArgument('set image ID', '--id'),
        owner=ValueArgument('set image owner (admin only)', '--owner'),
        properties=KeyValueArgument(
            'add property in key=value form (can be repeated)',
            '--property'),
        is_public=FlagArgument('mark image as public', '--public'),
        size=IntArgument('set image size', '--size'),
        update=FlagArgument('update an existing image properties', '--update')
    )

    def main(self, name, location):
        super(self.__class__, self).main()
        if not location.startswith('pithos://'):
            account = self.config.get('store', 'account') \
                or self.config.get('global', 'account')
            if account[-1] == '/':
                account = account[:-1]
            container = self.config.get('store', 'container') \
                or self.config.get('global', 'container')
            if container is None or len(container) == 0:
                location = 'pithos://%s/%s' % (account, location)
            else:
                location = 'pithos://%s/%s/%s' % (account, container, location)

        params = {}
        for key in set(
            [
                'checksum',
                'container_format',
                'disk_format',
                'id',
                'owner',
                'size',
                'is_public'
            ]).intersection(self.arguments):
            params[key] = self[key]

        try:
            properties = self['properties']
            if self['update']:
                self.client.reregister(location, name, params, properties)
            else:
                self.client.register(name, location, params, properties)
        except Exception as err:
            raiseCLIError(err)


@command(image_cmds)
class image_members(_init_image):
    """Get image members"""

    def main(self, image_id):
        super(self.__class__, self).main()
        try:
            members = self.client.list_members(image_id)
        except Exception as err:
            raiseCLIError(err)
        for member in members:
            print(member['member_id'])


@command(image_cmds)
class image_shared(_init_image):
    """List shared images"""

    def main(self, member):
        super(self.__class__, self).main()
        try:
            images = self.client.list_shared(member)
        except Exception as err:
            raiseCLIError(err)
        for image in images:
            print(image['image_id'])


@command(image_cmds)
class image_addmember(_init_image):
    """Add a member to an image"""

    def main(self, image_id, member):
        super(self.__class__, self).main()
        try:
            self.client.add_member(image_id, member)
        except Exception as err:
            raiseCLIError(err)


@command(image_cmds)
class image_delmember(_init_image):
    """Remove a member from an image"""

    def main(self, image_id, member):
        super(self.__class__, self).main()
        try:
            self.client.remove_member(image_id, member)
        except Exception as err:
            raiseCLIError(err)


@command(image_cmds)
class image_setmembers(_init_image):
    """Set the members of an image"""

    def main(self, image_id, *member):
        super(self.__class__, self).main()
        try:
            self.client.set_members(image_id, member)
        except Exception as err:
            raiseCLIError(err)


@command(image_cmds)
class image_list(_init_cyclades):
    """List images"""

    arguments = dict(
        detail= FlagArgument('show detailed output', '-l')
    )

    def _print(self, images):
        for img in images:
            iname = img.pop('name')
            iid = img.pop('id')
            print('%s (%s)' % (unicode(iid), bold(iname)))
            if self['detail']:
                if 'metadata' in img:
                    img['metadata'] = img['metadata']['values']
                print_dict(img, ident=2)

    def main(self):
        super(self.__class__, self).main()
        try:
            images = self.client.list_images(self['detail'])
        except Exception as err:
            raiseCLIError(err)
        self._print(images)


@command(image_cmds)
class image_info(_init_cyclades):
    """Get image details"""

    @classmethod
    def _print(self, image):
        if 'metadata' in image:
            image['metadata'] = image['metadata']['values']
        print_dict(image)

    def main(self, image_id):
        super(self.__class__, self).main()
        try:
            image = self.client.get_image_details(image_id)
        except Exception as err:
            raiseCLIError(err)
        self._print(image)


@command(image_cmds)
class image_delete(_init_cyclades):
    """Delete image"""

    def main(self, image_id):
        super(self.__class__, self).main()
        try:
            self.client.delete_image(image_id)
        except Exception as err:
            raiseCLIError(err)


@command(image_cmds)
class image_properties(_init_cyclades):
    """Get image properties"""

    def main(self, image_id, key=''):
        super(self.__class__, self).main()
        try:
            reply = self.client.get_image_metadata(image_id, key)
        except Exception as err:
            raiseCLIError(err)
        print_dict(reply)


@command(image_cmds)
class image_addproperty(_init_cyclades):
    """Add an image property"""

    def main(self, image_id, key, val):
        super(self.__class__, self).main()
        try:
            reply = self.client.create_image_metadata(image_id, key, val)
        except Exception as err:
            raiseCLIError(err)
        print_dict(reply)


@command(image_cmds)
class image_setproperty(_init_cyclades):
    """Update an image property"""

    def main(self, image_id, key, val):
        super(self.__class__, self).main()
        metadata = {key: val}
        try:
            reply = self.client.update_image_metadata(image_id, **metadata)
        except Exception as err:
            raiseCLIError(err)
        print_dict(reply)


@command(image_cmds)
class image_delproperty(_init_cyclades):
    """Delete an image property"""

    def main(self, image_id, key):
        super(self.__class__, self).main()
        try:
            self.client.delete_image_metadata(image_id, key)
        except Exception as err:
            raiseCLIError(err)
