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
from kamaki.cli.utils import print_dict, print_items
from kamaki.clients.image import ImageClient, ClientError
from kamaki.cli.argument import FlagArgument, ValueArgument, KeyValueArgument
from kamaki.cli.argument import IntArgument
from kamaki.cli.commands.cyclades_cli import _init_cyclades
from kamaki.cli.commands.cyclades_cli import raise_if_connection_error
from kamaki.cli.commands import _command_init


image_cmds = CommandTree(
    'image',
    'Compute/Cyclades or Glance API image commands')
_commands = [image_cmds]


about_image_id = ['To see a list of available image ids: /image list']


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
            default=''),
        limit=IntArgument('limit the number of images in list', '-n'),
        more=FlagArgument(
            'output results in pages (-n to set items per page, default 10)',
            '--more')
    )

    def main(self):
        super(self.__class__, self).main()
        filters = {}
        for arg in set([
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
        except ClientError as ce:
            raise_if_connection_error(ce, base_url='image.url')
            raiseCLIError(ce)
        except Exception as err:
            raiseCLIError(err)
        if self['more']:
            print_items(
                images,
                title=('name',),
                with_enumeration=True,
                page_size=self['limit'] if self['limit'] else 10)
        elif self['limit']:
            print_items(
                images[:self['limit']],
                title=('name',),
                with_enumeration=True)
        else:
            print_items(images, title=('name',), with_enumeration=True)


@command(image_cmds)
class image_meta(_init_image):
    """Get image metadata
    Image metadata include:
    - image file information (location, size, etc.)
    - image information (id, name, etc.)
    - image os properties (os, fs, etc.)
    """

    def main(self, image_id):
        super(self.__class__, self).main()
        try:
            image = self.client.get_meta(image_id)
        except ClientError as ce:
            if ce.status == 404:
                raiseCLIError(ce,
                    'No image with id %s found' % image_id,
                    details=about_image_id)
            raise_if_connection_error(ce, base_url='image.url')
            raiseCLIError(ce)
        except Exception as err:
            raiseCLIError(err)
        print_dict(image)


@command(image_cmds)
class image_register(_init_image):
    """(Re)Register an image"""

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
        update=FlagArgument('update existing image properties', '--update')
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
        except ClientError as ce:
            raise_if_connection_error(ce, base_url='image.url')
            raiseCLIError(ce)
        except Exception as err:
            raiseCLIError(err)


@command(image_cmds)
class image_members(_init_image):
    """Get image members"""

    def main(self, image_id):
        super(self.__class__, self).main()
        try:
            members = self.client.list_members(image_id)
        except ClientError as ce:
            raise_if_connection_error(ce, base_url='image.url')
            raiseCLIError(ce)
        except Exception as err:
            raiseCLIError(err)
        print_items(members)


@command(image_cmds)
class image_shared(_init_image):
    """List images shared by a member"""

    def main(self, member):
        super(self.__class__, self).main()
        try:
            images = self.client.list_shared(member)
        except ClientError as ce:
            raise_if_connection_error(ce, base_url='image.url')
            raiseCLIError(ce)
        except Exception as err:
            raiseCLIError(err)
        print_items(images)


@command(image_cmds)
class image_addmember(_init_image):
    """Add a member to an image"""

    def main(self, image_id, member):
        super(self.__class__, self).main()
        try:
            self.client.add_member(image_id, member)
        except ClientError as ce:
            if ce.status == 404:
                raiseCLIError(ce,
                    'No image with id %s found' % image_id,
                    details=about_image_id)
            raise_if_connection_error(ce, base_url='image.url')
            raiseCLIError(ce)
        except Exception as err:
            raiseCLIError(err)


@command(image_cmds)
class image_delmember(_init_image):
    """Remove a member from an image"""

    def main(self, image_id, member):
        super(self.__class__, self).main()
        try:
            self.client.remove_member(image_id, member)
        except ClientError as ce:
            if ce.status == 404:
                raiseCLIError(ce,
                    'No image with id %s found' % image_id,
                    details=about_image_id)
            raise_if_connection_error(ce, base_url='image.url')
            raiseCLIError(ce)
        except Exception as err:
            raiseCLIError(err)


@command(image_cmds)
class image_setmembers(_init_image):
    """Set the members of an image"""

    def main(self, image_id, *member):
        super(self.__class__, self).main()
        try:
            self.client.set_members(image_id, member)
        except ClientError as ce:
            if ce.status == 404:
                raiseCLIError(ce,
                    'No image with id %s found' % image_id,
                    details=about_image_id)
            raise_if_connection_error(ce, base_url='image.url')
            raiseCLIError(ce)
        except Exception as err:
            raiseCLIError(err)


@command(image_cmds)
class image_list(_init_cyclades):
    """List images"""

    arguments = dict(
        detail=FlagArgument('show detailed output', '-l'),
        limit=IntArgument('limit the number of VMs to list', '-n'),
        more=FlagArgument(
            'output results in pages (-n to set items per page, default 10)',
            '--more')
    )

    def _make_results_pretty(self, images):
        for img in images:
            if 'metadata' in img:
                img['metadata'] = img['metadata']['values']

    def main(self):
        super(self.__class__, self).main()
        try:
            images = self.client.list_images(self['detail'])
            if self['detail']:
                self._make_results_pretty(images)
            if self['more']:
                print_items(images,
                    page_size=self['limit'] if self['limit'] else 10)
            elif self['limit']:
                print_items(images[:self['limit']])
            else:
                print_items(images)
        except ClientError as ce:
            raise_if_connection_error(ce)
            raiseCLIError(ce)
        except Exception as err:
            raiseCLIError(err)


@command(image_cmds)
class image_info(_init_cyclades):
    """Get detailed information on an image"""

    @classmethod
    def _make_results_pretty(self, image):
        if 'metadata' in image:
            image['metadata'] = image['metadata']['values']

    def main(self, image_id):
        super(self.__class__, self).main()
        try:
            image = self.client.get_image_details(image_id)
            self._make_results_pretty(image)
        except ClientError as ce:
            if ce.status == 404 and 'image' in ('%s' % ce).lower():
                raiseCLIError(ce,
                    'No image with id %s found' % image_id,
                    details=about_image_id)
            raise_if_connection_error(ce)
            raiseCLIError(ce)
        except Exception as err:
            raiseCLIError(err)
        print_dict(image)


@command(image_cmds)
class image_delete(_init_cyclades):
    """Delete an image (image file remains intact)"""

    def main(self, image_id):
        super(self.__class__, self).main()
        try:
            self.client.delete_image(image_id)
        except ClientError as ce:
            if ce.status == 404 and 'image' in ('%s' % ce).lower():
                raiseCLIError(ce,
                    'No image with id %s found' % image_id,
                    details=about_image_id)
            raise_if_connection_error(ce)
            raiseCLIError(ce)
        except Exception as err:
            raiseCLIError(err)


@command(image_cmds)
class image_properties(_init_cyclades):
    """Get properties related to OS installation in an image"""

    def main(self, image_id, key=''):
        super(self.__class__, self).main()
        try:
            reply = self.client.get_image_metadata(image_id, key)
        except ClientError as ce:
            if ce.status == 404:
                if 'image' in ('%s' % ce).lower():
                    raiseCLIError(ce,
                        'No image with id %s found' % image_id,
                        details=about_image_id)
                elif 'metadata' in ('%s' % ce).lower():
                    raiseCLIError(ce,
                        'No properties with key %s in this image' % key)
            raise_if_connection_error(ce)
            raiseCLIError(ce)
        except Exception as err:
            raiseCLIError(err)
        print_dict(reply)


@command(image_cmds)
class image_addproperty(_init_cyclades):
    """Add an OS-related property to an image"""

    def main(self, image_id, key, val):
        super(self.__class__, self).main()
        try:
            assert(key)
            reply = self.client.create_image_metadata(image_id, key, val)
        except ClientError as ce:
            if ce.status == 404 and 'image' in ('%s' % ce).lower():
                raiseCLIError(ce,
                    'No image with id %s found' % image_id,
                    details=about_image_id)
            raise_if_connection_error(ce)
            raiseCLIError(ce)
        except Exception as err:
            raiseCLIError(err)
        print_dict(reply)


@command(image_cmds)
class image_setproperty(_init_cyclades):
    """Update an existing property in an image"""

    def main(self, image_id, key, val):
        super(self.__class__, self).main()
        metadata = {key: val}
        try:
            reply = self.client.update_image_metadata(image_id, **metadata)
        except ClientError as ce:
            if ce.status == 404 and 'image' in ('%s' % ce).lower():
                raiseCLIError(ce,
                    'No image with id %s found' % image_id,
                    details=about_image_id)
            raise_if_connection_error(ce)
            raiseCLIError(ce)
        except Exception as err:
            raiseCLIError(err)
        print_dict(reply)


@command(image_cmds)
class image_delproperty(_init_cyclades):
    """Delete a property of an image"""

    def main(self, image_id, key):
        super(self.__class__, self).main()
        try:
            self.client.delete_image_metadata(image_id, key)
        except ClientError as ce:
            if ce.status == 404:
                if 'image' in ('%s' % ce).lower():
                    raiseCLIError(ce,
                        'No image with id %s found' % image_id,
                        details=about_image_id)
                elif 'metadata' in ('%s' % ce).lower():
                    raiseCLIError(ce,
                        'No properties with key %s in this image' % key)
            raise_if_connection_error(ce)
            raiseCLIError(ce)
        except Exception as err:
            raiseCLIError(err)
