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

from json import load, dumps
from os.path import abspath
from logging import getLogger

from kamaki.cli import command
from kamaki.cli.command_tree import CommandTree
from kamaki.cli.utils import print_dict, print_items, print_json
from kamaki.clients.image import ImageClient
from kamaki.clients.pithos import PithosClient
from kamaki.clients.astakos import AstakosClient
from kamaki.clients import ClientError
from kamaki.cli.argument import FlagArgument, ValueArgument, KeyValueArgument
from kamaki.cli.argument import IntArgument
from kamaki.cli.commands.cyclades import _init_cyclades
from kamaki.cli.commands import _command_init, errors, _optional_output_cmd
from kamaki.cli.errors import raiseCLIError


image_cmds = CommandTree(
    'image',
    'Cyclades/Plankton API image commands\n'
    'image compute:\tCyclades/Compute API image commands')
_commands = [image_cmds]


about_image_id = [
    'To see a list of available image ids: /image list']


log = getLogger(__name__)


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


def _validate_image_props(json_dict, return_str=False):
    """
    :param json_dict" (dict) json-formated, of the form
        {"key1": "val1", "key2": "val2", ...}

    :param return_str: (boolean) if true, return a json dump

    :returns: (dict)

    :raises TypeError, AttributeError: Invalid json format

    :raises AssertionError: Valid json but invalid image properties dict
    """
    json_str = dumps(json_dict, indent=2)
    for k, v in json_dict.items():
        dealbreaker = isinstance(v, dict) or isinstance(v, list)
        assert not dealbreaker, 'Invalid property value for key %s' % k
        dealbreaker = ' ' in k
        assert not dealbreaker, 'Invalid key [%s]' % k
        json_dict[k] = '%s' % v
    return json_str if return_str else json_dict


def _load_image_props(filepath):
    """
    :param filepath: (str) the (relative) path of the metafile

    :returns: (dict) json_formated

    :raises TypeError, AttributeError: Invalid json format

    :raises AssertionError: Valid json but invalid image properties dict
    """
    with open(abspath(filepath)) as f:
        meta_dict = load(f)
        try:
            return _validate_image_props(meta_dict)
        except AssertionError:
            log.debug('Failed to load properties from file %s' % filepath)
            raise


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
            '--more'),
        enum=FlagArgument('Enumerate results', '--enumerate'),
        json_output=FlagArgument('Show results in json', ('-j', '--json'))
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

        if self['json_output']:
            print_json(images)
            return
        images = self._filtered_by_name(images)
        if self['more']:
            print_items(
                images,
                with_enumeration=self['enum'], page_size=self['limit'] or 10)
        elif self['limit']:
            print_items(images[:self['limit']], with_enumeration=self['enum'])
        else:
            print_items(images, with_enumeration=self['enum'])

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

    arguments = dict(
        json_output=FlagArgument('Show results in json', ('-j', '--json'))
    )

    @errors.generic.all
    @errors.plankton.connection
    @errors.plankton.id
    def _run(self, image_id):
        printer = print_json if self['json_output'] else print_dict
        printer(self.client.get_meta(image_id))

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
        #update=FlagArgument(
        #    'update existing image properties',
        #    ('-u', '--update')),
        json_output=FlagArgument('Show results in json', ('-j', '--json')),
        property_file=ValueArgument(
            'Load properties from a json-formated file <img-file>.meta :'
            '{"key1": "val1", "key2": "val2", ...}',
            ('--property-file')),
        prop_file_force=FlagArgument(
            'Store remote property object, even it already exists',
            ('-f', '--force-upload-property-file')),
        no_prop_file_upload=FlagArgument(
            'Do not store properties in remote property file',
            ('--no-property-file-upload')),
        container=ValueArgument(
            'Remote image container', ('-C', '--container')),
        fileowner=ValueArgument(
            'UUID of the user who owns the image file', ('--fileowner'))
    )

    def _get_uuid(self):
        uuid = self['fileowner'] or self.config.get('image', 'fileowner')
        if uuid:
            return uuid
        atoken = self.client.token
        user = AstakosClient(self.config.get('user', 'url'), atoken)
        return user.term('uuid')

    def _get_pithos_client(self, uuid, container):
        purl = self.config.get('file', 'url')
        ptoken = self.client.token
        return PithosClient(purl, ptoken, uuid, container)

    def _store_remote_property_file(self, pclient, remote_path, properties):
        return pclient.upload_from_string(
            remote_path, _validate_image_props(properties, return_str=True))

    def _get_container_path(self, container_path):
        container = self['container'] or self.config.get('image', 'container')
        if container:
            return container, container_path

        container, sep, path = container_path.partition(':')
        if not sep or not container or not path:
            raiseCLIError(
                '%s is not a valid pithos+ remote location' % container_path,
                importance=2,
                details=[
                    'To set "image" as container and "my_dir/img.diskdump" as',
                    'the image path, try one of the following as '
                    'container:path',
                    '- <image container>:<remote path>',
                    '    e.g. image:/my_dir/img.diskdump',
                    '- <remote path> -C <image container>',
                    '    e.g. /my_dir/img.diskdump -C image'])
        return container, path

    @errors.generic.all
    @errors.plankton.image_file
    @errors.plankton.connection
    def _run(self, name, container_path):
        container, path = self._get_container_path(container_path)
        uuid = self._get_uuid()
        prop_path = '%s.meta' % path

        pclient = None if (
            self['no_prop_file_upload']) else self._get_pithos_client(
                uuid, container)
        if pclient and not self['prop_file_force']:
            try:
                pclient.get_object_info(prop_path)
                raiseCLIError('Property file %s: %s already exists' % (
                    container, prop_path))
            except ClientError as ce:
                if ce.status != 404:
                    raise

        location = 'pithos://%s/%s/%s' % (uuid, container, path)

        params = {}
        for key in set([
                'checksum',
                'container_format',
                'disk_format',
                'owner',
                'size',
                'is_public']).intersection(self.arguments):
            params[key] = self[key]

        #load properties
        properties = dict()
        pfile = self['property_file']
        if pfile:
            try:
                for k, v in _load_image_props(pfile).items():
                    properties[k.lower()] = v
            except Exception as e:
                raiseCLIError(
                    e, 'Format error in property file %s' % pfile,
                    details=[
                        'Expected content format:',
                        '  {',
                        '    "key1": "value1",',
                        '    "key2": "value2",',
                        '    ...',
                        '  }',
                        '',
                        'Parser:'
                    ])
        for k, v in self['properties'].items():
            properties[k.lower()] = v

        printer = print_json if self['json_output'] else print_dict
        printer(self.client.register(name, location, params, properties))

        if pclient:
            prop_headers = pclient.upload_from_string(
                prop_path, _validate_image_props(properties, return_str=True))
            if self['json_output']:
                print_json(dict(
                    property_file_location='%s:%s' % (container, prop_path),
                    headers=prop_headers))
            else:
                print('Property file uploaded as %s:%s (version %s)' % (
                    container, prop_path, prop_headers['x-object-version']))

    def main(self, name, container___path):
        super(self.__class__, self)._run()
        self._run(name, container___path)


@command(image_cmds)
class image_unregister(_init_image, _optional_output_cmd):
    """Unregister an image (does not delete the image file)"""

    @errors.generic.all
    @errors.plankton.connection
    @errors.plankton.id
    def _run(self, image_id):
        self._optional_output(self.client.unregister(image_id))

    def main(self, image_id):
        super(self.__class__, self)._run()
        self._run(image_id=image_id)


@command(image_cmds)
class image_shared(_init_image):
    """List images shared by a member"""

    arguments = dict(
        json_output=FlagArgument('Show results in json', ('-j', '--json'))
    )

    @errors.generic.all
    @errors.plankton.connection
    def _run(self, member):
        r = self.client.list_shared(member)
        if self['json_output']:
            print_json(r)
        else:
            print_items(r, title=('image_id',))

    def main(self, member):
        super(self.__class__, self)._run()
        self._run(member)


@command(image_cmds)
class image_members(_init_image):
    """Manage members. Members of an image are users who can modify it"""


@command(image_cmds)
class image_members_list(_init_image):
    """List members of an image"""

    arguments = dict(
        json_output=FlagArgument('Show results in json', ('-j', '--json'))
    )

    @errors.generic.all
    @errors.plankton.connection
    @errors.plankton.id
    def _run(self, image_id):
        members = self.client.list_members(image_id)
        if self['json_output']:
            print_json(members)
        else:
            print_items(members, title=('member_id',), with_redundancy=True)

    def main(self, image_id):
        super(self.__class__, self)._run()
        self._run(image_id=image_id)


@command(image_cmds)
class image_members_add(_init_image, _optional_output_cmd):
    """Add a member to an image"""

    @errors.generic.all
    @errors.plankton.connection
    @errors.plankton.id
    def _run(self, image_id=None, member=None):
            self._optional_output(self.client.add_member(image_id, member))

    def main(self, image_id, member):
        super(self.__class__, self)._run()
        self._run(image_id=image_id, member=member)


@command(image_cmds)
class image_members_delete(_init_image, _optional_output_cmd):
    """Remove a member from an image"""

    @errors.generic.all
    @errors.plankton.connection
    @errors.plankton.id
    def _run(self, image_id=None, member=None):
            self._optional_output(self.client.remove_member(image_id, member))

    def main(self, image_id, member):
        super(self.__class__, self)._run()
        self._run(image_id=image_id, member=member)


@command(image_cmds)
class image_members_set(_init_image, _optional_output_cmd):
    """Set the members of an image"""

    @errors.generic.all
    @errors.plankton.connection
    @errors.plankton.id
    def _run(self, image_id, members):
            self._optional_output(self.client.set_members(image_id, members))

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
            '--more'),
        enum=FlagArgument('Enumerate results', '--enumerate'),
        json_output=FlagArgument('Show results in json', ('-j', '--json'))
    )

    def _make_results_pretty(self, images):
        for img in images:
            if 'metadata' in img:
                img['metadata'] = img['metadata']['values']

    @errors.generic.all
    @errors.cyclades.connection
    def _run(self):
        images = self.client.list_images(self['detail'])
        if self['json_output']:
            print_json(images)
            return
        if self['detail']:
            self._make_results_pretty(images)
        if self['more']:
            print_items(
                images,
                page_size=self['limit'] or 10, with_enumeration=self['enum'])
        else:
            print_items(images[:self['limit']], with_enumeration=self['enum'])

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(image_cmds)
class image_compute_info(_init_cyclades):
    """Get detailed information on an image"""

    arguments = dict(
        json_output=FlagArgument('Show results in json', ('-j', '--json'))
    )

    @errors.generic.all
    @errors.cyclades.connection
    @errors.plankton.id
    def _run(self, image_id):
        image = self.client.get_image_details(image_id)
        if self['json_output']:
            print_json(image)
            return
        if 'metadata' in image:
            image['metadata'] = image['metadata']['values']
        print_dict(image)

    def main(self, image_id):
        super(self.__class__, self)._run()
        self._run(image_id=image_id)


@command(image_cmds)
class image_compute_delete(_init_cyclades, _optional_output_cmd):
    """Delete an image (WARNING: image file is also removed)"""

    @errors.generic.all
    @errors.cyclades.connection
    @errors.plankton.id
    def _run(self, image_id):
        self._optional_output(self.client.delete_image(image_id))

    def main(self, image_id):
        super(self.__class__, self)._run()
        self._run(image_id=image_id)


@command(image_cmds)
class image_compute_properties(_init_cyclades):
    """Manage properties related to OS installation in an image"""


@command(image_cmds)
class image_compute_properties_list(_init_cyclades):
    """List all image properties"""

    arguments = dict(
        json_output=FlagArgument('Show results in json', ('-j', '--json'))
    )

    @errors.generic.all
    @errors.cyclades.connection
    @errors.plankton.id
    def _run(self, image_id):
        printer = print_json if self['json_output'] else print_dict
        printer(self.client.get_image_metadata(image_id))

    def main(self, image_id):
        super(self.__class__, self)._run()
        self._run(image_id=image_id)


@command(image_cmds)
class image_compute_properties_get(_init_cyclades):
    """Get an image property"""

    arguments = dict(
        json_output=FlagArgument('Show results in json', ('-j', '--json'))
    )

    @errors.generic.all
    @errors.cyclades.connection
    @errors.plankton.id
    @errors.plankton.metadata
    def _run(self, image_id, key):
        printer = print_json if self['json_output'] else print_dict
        printer(self.client.get_image_metadata(image_id, key))

    def main(self, image_id, key):
        super(self.__class__, self)._run()
        self._run(image_id=image_id, key=key)


@command(image_cmds)
class image_compute_properties_add(_init_cyclades):
    """Add a property to an image"""

    arguments = dict(
        json_output=FlagArgument('Show results in json', ('-j', '--json'))
    )

    @errors.generic.all
    @errors.cyclades.connection
    @errors.plankton.id
    @errors.plankton.metadata
    def _run(self, image_id, key, val):
        printer = print_json if self['json_output'] else print_dict
        printer(self.client.create_image_metadata(image_id, key, val))

    def main(self, image_id, key, val):
        super(self.__class__, self)._run()
        self._run(image_id=image_id, key=key, val=val)


@command(image_cmds)
class image_compute_properties_set(_init_cyclades):
    """Add / update a set of properties for an image
    proeprties must be given in the form key=value, e.v.
    /image compute properties set <image-id> key1=val1 key2=val2
    """
    arguments = dict(
        json_output=FlagArgument('Show results in json', ('-j', '--json'))
    )

    @errors.generic.all
    @errors.cyclades.connection
    @errors.plankton.id
    def _run(self, image_id, keyvals):
        metadata = dict()
        for keyval in keyvals:
            key, val = keyval.split('=')
            metadata[key] = val
        printer = print_json if self['json_output'] else print_dict
        printer(self.client.update_image_metadata(image_id, **metadata))

    def main(self, image_id, *key_equals_value):
        super(self.__class__, self)._run()
        self._run(image_id=image_id, keyvals=key_equals_value)


@command(image_cmds)
class image_compute_properties_delete(_init_cyclades, _optional_output_cmd):
    """Delete a property from an image"""

    @errors.generic.all
    @errors.cyclades.connection
    @errors.plankton.id
    @errors.plankton.metadata
    def _run(self, image_id, key):
        self._optional_output(self.client.delete_image_metadata(image_id, key))

    def main(self, image_id, key):
        super(self.__class__, self)._run()
        self._run(image_id=image_id, key=key)
