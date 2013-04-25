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
from kamaki.cli.utils import print_dict, print_items
from kamaki.clients.image import ImageClient
from kamaki.cli.argument import FlagArgument, ValueArgument, KeyValueArgument
from kamaki.cli.argument import IntArgument
from kamaki.cli.commands.cyclades import _init_cyclades
from kamaki.cli.commands import _command_init, errors


image_cmds = CommandTree(
    'image',
    'Cyclades/Plankton API image commands\n'
    'image compute:\tCyclades/Compute API image commands')
_commands = [image_cmds]


about_image_id = [
    'To see a list of available image ids: /image list']


class _init_image(_command_init):
    @errors.generic.all
    def _run(self):
        token = self.config.get('image', 'token')\
            or self.config.get('compute', 'token')\
            or self.config.get('global', 'token')
        base_url = self.config.get('image', 'url')\
            or self.config.get('compute', 'url')\
            or self.config.get('global', 'url')
        self.client = ImageClient(base_url=base_url, token=token)
        self._set_log_params()
        self._update_max_threads()

    def main(self):
        self._run()


# Plankton Image Commands


@command(image_cmds)
class image_list(_init_image):
    """List images accessible by user"""

    arguments = dict(
        detail=FlagArgument('show detailed output', ('-l', '--details')),
        container_format=ValueArgument(
            'filter by container format',
            '--container-format'),
        disk_format=ValueArgument('filter by disk format', '--disk-format'),
        name=ValueArgument('filter by name', '--name'),
        name_pref=ValueArgument(
            'filter by name prefix (case insensitive)',
            '--name-prefix'),
        name_suff=ValueArgument(
            'filter by name suffix (case insensitive)',
            '--name-suffix'),
        name_like=ValueArgument(
            'print only if name contains this (case insensitive)',
            '--name-like'),
        size_min=IntArgument('filter by minimum size', '--size-min'),
        size_max=IntArgument('filter by maximum size', '--size-max'),
        status=ValueArgument('filter by status', '--status'),
        owner=ValueArgument('filter by owner', '--owner'),
        order=ValueArgument(
            'order by FIELD ( - to reverse order)',
            '--order',
            default=''),
        limit=IntArgument('limit number of listed images', ('-n', '--number')),
        more=FlagArgument(
            'output results in pages (-n to set items per page, default 10)',
            '--more')
    )

    def _filtered_by_owner(self, detail, *list_params):
        images = []
        MINKEYS = set([
            'id', 'size', 'status', 'disk_format', 'container_format', 'name'])
        for img in self.client.list_public(True, *list_params):
            if img['owner'] == self['owner']:
                if not detail:
                    for key in set(img.keys()).difference(MINKEYS):
                        img.pop(key)
                images.append(img)
        return images

    def _filtered_by_name(self, images):
        np, ns, nl = self['name_pref'], self['name_suff'], self['name_like']
        return [img for img in images if (
            (not np) or img['name'].lower().startswith(np.lower())) and (
            (not ns) or img['name'].lower().endswith(ns.lower())) and (
            (not nl) or nl.lower() in img['name'].lower())]

    @errors.generic.all
    @errors.cyclades.connection
    def _run(self):
        super(self.__class__, self)._run()
        filters = {}
        for arg in set([
                'container_format',
                'disk_format',
                'name',
                'size_min',
                'size_max',
                'status']).intersection(self.arguments):
            filters[arg] = self[arg]

        order = self['order']
        detail = self['detail']
        if self['owner']:
            images = self._filtered_by_owner(detail, filters, order)
        else:
            images = self.client.list_public(detail, filters, order)
        images = self._filtered_by_name(images)

        if self['more']:
            print_items(
                images,
                title=('name',),
                with_enumeration=True,
                page_size=self['limit'] or 10)
        elif self['limit']:
            print_items(
                images[:self['limit']],
                title=('name',),
                with_enumeration=True)
        else:
            print_items(images, title=('name',), with_enumeration=True)

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(image_cmds)
class image_meta(_init_image):
    """Get image metadata
    Image metadata include:
    - image file information (location, size, etc.)
    - image information (id, name, etc.)
    - image os properties (os, fs, etc.)
    """

    @errors.generic.all
    @errors.plankton.connection
    @errors.plankton.id
    def _run(self, image_id):
        image = self.client.get_meta(image_id)
        print_dict(image)

    def main(self, image_id):
        super(self.__class__, self)._run()
        self._run(image_id=image_id)


@command(image_cmds)
class image_register(_init_image):
    """(Re)Register an image"""

    arguments = dict(
        checksum=ValueArgument('set image checksum', '--checksum'),
        container_format=ValueArgument(
            'set container format',
            '--container-format'),
        disk_format=ValueArgument('set disk format', '--disk-format'),
        #id=ValueArgument('set image ID', '--id'),
        owner=ValueArgument('set image owner (admin only)', '--owner'),
        properties=KeyValueArgument(
            'add property in key=value form (can be repeated)',
            ('-p', '--property')),
        is_public=FlagArgument('mark image as public', '--public'),
        size=IntArgument('set image size', '--size'),
        update=FlagArgument(
            'update existing image properties',
            ('-u', '--update'))
    )

    @errors.generic.all
    @errors.plankton.connection
    def _run(self, name, location):
        if not location.startswith('pithos://'):
            account = self.config.get('file', 'account') \
                or self.config.get('global', 'account')
            assert account, 'No user account provided'
            if account[-1] == '/':
                account = account[:-1]
            container = self.config.get('file', 'container') \
                or self.config.get('global', 'container')
            if not container:
                location = 'pithos://%s/%s' % (account, location)
            else:
                location = 'pithos://%s/%s/%s' % (account, container, location)

        params = {}
        for key in set([
                'checksum',
                'container_format',
                'disk_format',
                'owner',
                'size',
                'is_public']).intersection(self.arguments):
            params[key] = self[key]

            properties = self['properties']
        if self['update']:
            self.client.reregister(location, name, params, properties)
        else:
            r = self.client.register(name, location, params, properties)
            print_dict(r)

    def main(self, name, location):
        super(self.__class__, self)._run()
        self._run(name, location)


@command(image_cmds)
class image_members(_init_image):
    """Get image members"""

    @errors.generic.all
    @errors.plankton.connection
    @errors.plankton.id
    def _run(self, image_id):
        members = self.client.list_members(image_id)
        print_items(members)

    def main(self, image_id):
        super(self.__class__, self)._run()
        self._run(image_id=image_id)


@command(image_cmds)
class image_shared(_init_image):
    """List images shared by a member"""

    @errors.generic.all
    @errors.plankton.connection
    def _run(self, member):
        images = self.client.list_shared(member)
        print_items(images)

    def main(self, member):
        super(self.__class__, self)._run()
        self._run(member)


@command(image_cmds)
class image_addmember(_init_image):
    """Add a member to an image"""

    @errors.generic.all
    @errors.plankton.connection
    @errors.plankton.id
    def _run(self, image_id=None, member=None):
            self.client.add_member(image_id, member)

    def main(self, image_id, member):
        super(self.__class__, self)._run()
        self._run(image_id=image_id, member=member)


@command(image_cmds)
class image_delmember(_init_image):
    """Remove a member from an image"""

    @errors.generic.all
    @errors.plankton.connection
    @errors.plankton.id
    def _run(self, image_id=None, member=None):
            self.client.remove_member(image_id, member)

    def main(self, image_id, member):
        super(self.__class__, self)._run()
        self._run(image_id=image_id, member=member)


@command(image_cmds)
class image_setmembers(_init_image):
    """Set the members of an image"""

    @errors.generic.all
    @errors.plankton.connection
    @errors.plankton.id
    def _run(self, image_id, members):
            self.client.set_members(image_id, members)

    def main(self, image_id, *members):
        super(self.__class__, self)._run()
        self._run(image_id=image_id, members=members)


# Compute Image Commands


@command(image_cmds)
class image_compute(_init_cyclades):
    """Cyclades/Compute API image commands"""


@command(image_cmds)
class image_compute_list(_init_cyclades):
    """List images"""

    arguments = dict(
        detail=FlagArgument('show detailed output', ('-l', '--details')),
        limit=IntArgument('limit number listed images', ('-n', '--number')),
        more=FlagArgument(
            'output results in pages (-n to set items per page, default 10)',
            '--more')
    )

    def _make_results_pretty(self, images):
        for img in images:
            if 'metadata' in img:
                img['metadata'] = img['metadata']['values']

    @errors.generic.all
    @errors.cyclades.connection
    def _run(self):
        images = self.client.list_images(self['detail'])
        if self['detail']:
            self._make_results_pretty(images)
        if self['more']:
            print_items(images, page_size=self['limit'] or 10)
        else:
            print_items(images[:self['limit']])

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(image_cmds)
class image_compute_info(_init_cyclades):
    """Get detailed information on an image"""

    @errors.generic.all
    @errors.cyclades.connection
    @errors.plankton.id
    def _run(self, image_id):
        image = self.client.get_image_details(image_id)
        if 'metadata' in image:
            image['metadata'] = image['metadata']['values']
        print_dict(image)

    def main(self, image_id):
        super(self.__class__, self)._run()
        self._run(image_id=image_id)


@command(image_cmds)
class image_compute_delete(_init_cyclades):
    """Delete an image (WARNING: image file is also removed)"""

    @errors.generic.all
    @errors.cyclades.connection
    @errors.plankton.id
    def _run(self, image_id):
        self.client.delete_image(image_id)

    def main(self, image_id):
        super(self.__class__, self)._run()
        self._run(image_id=image_id)


@command(image_cmds)
class image_compute_properties(_init_cyclades):
    """Get properties related to OS installation in an image"""

    @errors.generic.all
    @errors.cyclades.connection
    @errors.plankton.id
    @errors.plankton.metadata
    def _run(self, image_id, key):
        r = self.client.get_image_metadata(image_id, key)
        print_dict(r)

    def main(self, image_id, key=''):
        super(self.__class__, self)._run()
        self._run(image_id=image_id, key=key)


@command(image_cmds)
class image_addproperty(_init_cyclades):
    """Add an OS-related property to an image"""

    @errors.generic.all
    @errors.cyclades.connection
    @errors.plankton.id
    @errors.plankton.metadata
    def _run(self, image_id, key, val):
        r = self.client.create_image_metadata(image_id, key, val)
        print_dict(r)

    def main(self, image_id, key, val):
        super(self.__class__, self)._run()
        self._run(image_id=image_id, key=key, val=val)


@command(image_cmds)
class image_compute_setproperty(_init_cyclades):
    """Update an existing property in an image"""

    @errors.generic.all
    @errors.cyclades.connection
    @errors.plankton.id
    @errors.plankton.metadata
    def _run(self, image_id, key, val):
        metadata = {key: val}
        r = self.client.update_image_metadata(image_id, **metadata)
        print_dict(r)

    def main(self, image_id, key, val):
        super(self.__class__, self)._run()
        self._run(image_id=image_id, key=key, val=val)


@command(image_cmds)
class image_compute_delproperty(_init_cyclades):
    """Delete a property of an image"""

    @errors.generic.all
    @errors.cyclades.connection
    @errors.plankton.id
    @errors.plankton.metadata
    def _run(self, image_id, key):
        self.client.delete_image_metadata(image_id, key)

    def main(self, image_id, key):
        super(self.__class__, self)._run()
        self._run(image_id=image_id, key=key)
