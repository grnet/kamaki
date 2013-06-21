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
from kamaki.cli.utils import print_dict, print_json
from kamaki.clients.image import ImageClient
from kamaki.clients.pithos import PithosClient
from kamaki.clients.astakos import AstakosClient
from kamaki.clients import ClientError
from kamaki.cli.argument import FlagArgument, ValueArgument, KeyValueArgument
from kamaki.cli.argument import IntArgument
from kamaki.cli.commands.cyclades import _init_cyclades
from kamaki.cli.errors import raiseCLIError, CLIBaseUrlError
from kamaki.cli.commands import _command_init, errors, addLogSettings
from kamaki.cli.commands import _optional_output_cmd, _optional_json


image_cmds = CommandTree(
    'image',
    'Cyclades/Plankton API image commands\n'
    'image compute:\tCyclades/Compute API image commands')
_commands = [image_cmds]


howto_image_file = [
    'Kamaki commands to:',
    ' get current user id: /user authenticate',
    ' check available containers: /file list',
    ' create a new container: /file create <container>',
    ' check container contents: /file list <container>',
    ' upload files: /file upload <image file> <container>']

about_image_id = ['To see a list of available image ids: /image list']


log = getLogger(__name__)


class _init_image(_command_init):
    @errors.generic.all
    @addLogSettings
    def _run(self):
        if getattr(self, 'cloud', None):
            img_url = self._custom_url('image') or self._custom_url('plankton')
            if img_url:
                token = self._custom_token('image')\
                    or self._custom_token('plankton')\
                    or self.config.get_cloud(self.cloud, 'token')
                self.client = ImageClient(base_url=img_url, token=token)
                return
        if getattr(self, 'auth_base', False):
            plankton_endpoints = self.auth_base.get_service_endpoints(
                self._custom_type('image') or self._custom_type(
                    'plankton') or 'image',
                self._custom_version('image') or self._custom_version(
                    'plankton') or '')
            base_url = plankton_endpoints['publicURL']
            token = self.auth_base.token
        else:
            raise CLIBaseUrlError(service='plankton')
        self.client = ImageClient(base_url=base_url, token=token)

    def main(self):
        self._run()


# Plankton Image Commands


def _validate_image_meta(json_dict, return_str=False):
    """
    :param json_dict" (dict) json-formated, of the form
        {"key1": "val1", "key2": "val2", ...}

    :param return_str: (boolean) if true, return a json dump

    :returns: (dict) if return_str is not True, else return str

    :raises TypeError, AttributeError: Invalid json format

    :raises AssertionError: Valid json but invalid image properties dict
    """
    json_str = dumps(json_dict, indent=2)
    for k, v in json_dict.items():
        if k.lower() == 'properties':
            for pk, pv in v.items():
                prop_ok = not (isinstance(pv, dict) or isinstance(pv, list))
                assert prop_ok, 'Invalid property value for key %s' % pk
                key_ok = not (' ' in k or '-' in k)
                assert key_ok, 'Invalid property key %s' % k
            continue
        meta_ok = not (isinstance(v, dict) or isinstance(v, list))
        assert meta_ok, 'Invalid value for meta key %s' % k
        meta_ok = ' ' not in k
        assert meta_ok, 'Invalid meta key [%s]' % k
        json_dict[k] = '%s' % v
    return json_str if return_str else json_dict


def _load_image_meta(filepath):
    """
    :param filepath: (str) the (relative) path of the metafile

    :returns: (dict) json_formated

    :raises TypeError, AttributeError: Invalid json format

    :raises AssertionError: Valid json but invalid image properties dict
    """
    with open(abspath(filepath)) as f:
        meta_dict = load(f)
        try:
            return _validate_image_meta(meta_dict)
        except AssertionError:
            log.debug('Failed to load properties from file %s' % filepath)
            raise


def _validate_image_location(location):
    """
    :param location: (str) pithos://<user-id>/<container>/<img-file-path>

    :returns: (<user-id>, <container>, <img-file-path>)

    :raises AssertionError: if location is invalid
    """
    prefix = 'pithos://'
    msg = 'Invalid prefix for location %s , try: %s' % (location, prefix)
    assert location.startswith(prefix), msg
    service, sep, rest = location.partition('://')
    assert sep and rest, 'Location %s is missing user-id' % location
    uuid, sep, rest = rest.partition('/')
    assert sep and rest, 'Location %s is missing container' % location
    container, sep, img_path = rest.partition('/')
    assert sep and img_path, 'Location %s is missing image path' % location
    return uuid, container, img_path


@command(image_cmds)
class image_list(_init_image, _optional_json):
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
        enum=FlagArgument('Enumerate results', '--enumerate')
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
        kwargs = dict(with_enumeration=self['enum'])
        if self['more']:
            kwargs['page_size'] = self['limit'] or 10
        elif self['limit']:
            images = images[:self['limit']]
        self._print(images, **kwargs)

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(image_cmds)
class image_meta(_init_image, _optional_json):
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
        self._print([self.client.get_meta(image_id)])

    def main(self, image_id):
        super(self.__class__, self)._run()
        self._run(image_id=image_id)


@command(image_cmds)
class image_register(_init_image, _optional_json):
    """(Re)Register an image"""

    arguments = dict(
        checksum=ValueArgument('set image checksum', '--checksum'),
        container_format=ValueArgument(
            'set container format',
            '--container-format'),
        disk_format=ValueArgument('set disk format', '--disk-format'),
        owner=ValueArgument('set image owner (admin only)', '--owner'),
        properties=KeyValueArgument(
            'add property in key=value form (can be repeated)',
            ('-p', '--property')),
        is_public=FlagArgument('mark image as public', '--public'),
        size=IntArgument('set image size', '--size'),
        metafile=ValueArgument(
            'Load metadata from a json-formated file <img-file>.meta :'
            '{"key1": "val1", "key2": "val2", ..., "properties: {...}"}',
            ('--metafile')),
        metafile_force=FlagArgument(
            'Store remote metadata object, even if it already exists',
            ('-f', '--force')),
        no_metafile_upload=FlagArgument(
            'Do not store metadata in remote meta file',
            ('--no-metafile-upload')),

    )

    def _get_user_id(self):
        atoken = self.client.token
        if getattr(self, 'auth_base', False):
            return self.auth_base.term('id', atoken)
        else:
            astakos_url = self.config.get('user', 'url')\
                or self.config.get('astakos', 'url')
            if not astakos_url:
                raise CLIBaseUrlError(service='astakos')
            user = AstakosClient(astakos_url, atoken)
            return user.term('id')

    def _get_pithos_client(self, container):
        if self['no_metafile_upload']:
            return None
        ptoken = self.client.token
        if getattr(self, 'auth_base', False):
            pithos_endpoints = self.auth_base.get_service_endpoints(
                'object-store')
            purl = pithos_endpoints['publicURL']
        else:
            purl = self.config.get_cloud('pithos', 'url')
        if not purl:
            raise CLIBaseUrlError(service='pithos')
        return PithosClient(purl, ptoken, self._get_user_id(), container)

    def _store_remote_metafile(self, pclient, remote_path, metadata):
        return pclient.upload_from_string(
            remote_path, _validate_image_meta(metadata, return_str=True))

    def _load_params_from_file(self, location):
        params, properties = dict(), dict()
        pfile = self['metafile']
        if pfile:
            try:
                for k, v in _load_image_meta(pfile).items():
                    key = k.lower().replace('-', '_')
                    if k == 'properties':
                        for pk, pv in v.items():
                            properties[pk.upper().replace('-', '_')] = pv
                    elif key == 'name':
                            continue
                    elif key == 'location':
                        if location:
                            continue
                        location = v
                    else:
                        params[key] = v
            except Exception as e:
                raiseCLIError(e, 'Invalid json metadata config file')
        return params, properties, location

    def _load_params_from_args(self, params, properties):
        for key in set([
                'checksum',
                'container_format',
                'disk_format',
                'owner',
                'size',
                'is_public']).intersection(self.arguments):
            params[key] = self[key]
        for k, v in self['properties'].items():
            properties[k.upper().replace('-', '_')] = v

    def _validate_location(self, location):
        if not location:
            raiseCLIError(
                'No image file location provided',
                importance=2, details=[
                    'An image location is needed. Image location format:',
                    '  pithos://<user-id>/<container>/<path>',
                    ' an image file at the above location must exist.'
                    ] + howto_image_file)
        try:
            return _validate_image_location(location)
        except AssertionError as ae:
            raiseCLIError(
                ae, 'Invalid image location format',
                importance=1, details=[
                    'Valid image location format:',
                    '  pithos://<user-id>/<container>/<img-file-path>'
                    ] + howto_image_file)

    @errors.generic.all
    @errors.plankton.connection
    def _run(self, name, location):
        (params, properties, location) = self._load_params_from_file(location)
        uuid, container, img_path = self._validate_location(location)
        self._load_params_from_args(params, properties)
        pclient = self._get_pithos_client(container)

        #check if metafile exists
        meta_path = '%s.meta' % img_path
        if pclient and not self['metafile_force']:
            try:
                pclient.get_object_info(meta_path)
                raiseCLIError('Metadata file %s:%s already exists' % (
                    container, meta_path))
            except ClientError as ce:
                if ce.status != 404:
                    raise

        #register the image
        try:
            r = self.client.register(name, location, params, properties)
        except ClientError as ce:
            if ce.status in (400, ):
                raiseCLIError(
                    ce, 'Nonexistent image file location %s' % location,
                    details=[
                        'Make sure the image file exists'] + howto_image_file)
            raise
        self._print(r, print_dict)

        #upload the metadata file
        if pclient:
            try:
                meta_headers = pclient.upload_from_string(
                    meta_path, dumps(r, indent=2))
            except TypeError:
                print('Failed to dump metafile %s:%s' % (container, meta_path))
                return
            if self['json_output']:
                print_json(dict(
                    metafile_location='%s:%s' % (container, meta_path),
                    headers=meta_headers))
            else:
                print('Metadata file uploaded as %s:%s (version %s)' % (
                    container, meta_path, meta_headers['x-object-version']))

    def main(self, name, location):
        super(self.__class__, self)._run()
        self._run(name, location)


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
class image_shared(_init_image, _optional_json):
    """List images shared by a member"""

    @errors.generic.all
    @errors.plankton.connection
    def _run(self, member):
        self._print(self.client.list_shared(member), title=('image_id',))

    def main(self, member):
        super(self.__class__, self)._run()
        self._run(member)


@command(image_cmds)
class image_members(_init_image):
    """Manage members. Members of an image are users who can modify it"""


@command(image_cmds)
class image_members_list(_init_image, _optional_json):
    """List members of an image"""

    @errors.generic.all
    @errors.plankton.connection
    @errors.plankton.id
    def _run(self, image_id):
        self._print(self.client.list_members(image_id), title=('member_id',))

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
class image_compute_list(_init_cyclades, _optional_json):
    """List images"""

    arguments = dict(
        detail=FlagArgument('show detailed output', ('-l', '--details')),
        limit=IntArgument('limit number listed images', ('-n', '--number')),
        more=FlagArgument(
            'output results in pages (-n to set items per page, default 10)',
            '--more'),
        enum=FlagArgument('Enumerate results', '--enumerate')
    )

    @errors.generic.all
    @errors.cyclades.connection
    def _run(self):
        images = self.client.list_images(self['detail'])
        kwargs = dict(with_enumeration=self['enum'])
        if self['more']:
            kwargs['page_size'] = self['limit'] or 10
        elif self['limit']:
            images = images[:self['limit']]
        self._print(images, **kwargs)

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(image_cmds)
class image_compute_info(_init_cyclades, _optional_json):
    """Get detailed information on an image"""

    @errors.generic.all
    @errors.cyclades.connection
    @errors.plankton.id
    def _run(self, image_id):
        image = self.client.get_image_details(image_id)
        self._print(image, print_dict)

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
class image_compute_properties_list(_init_cyclades, _optional_json):
    """List all image properties"""

    @errors.generic.all
    @errors.cyclades.connection
    @errors.plankton.id
    def _run(self, image_id):
        self._print(self.client.get_image_metadata(image_id), print_dict)

    def main(self, image_id):
        super(self.__class__, self)._run()
        self._run(image_id=image_id)


@command(image_cmds)
class image_compute_properties_get(_init_cyclades, _optional_json):
    """Get an image property"""

    @errors.generic.all
    @errors.cyclades.connection
    @errors.plankton.id
    @errors.plankton.metadata
    def _run(self, image_id, key):
        self._print(self.client.get_image_metadata(image_id, key), print_dict)

    def main(self, image_id, key):
        super(self.__class__, self)._run()
        self._run(image_id=image_id, key=key)


@command(image_cmds)
class image_compute_properties_add(_init_cyclades, _optional_json):
    """Add a property to an image"""

    @errors.generic.all
    @errors.cyclades.connection
    @errors.plankton.id
    @errors.plankton.metadata
    def _run(self, image_id, key, val):
        self._print(
            self.client.create_image_metadata(image_id, key, val), print_dict)

    def main(self, image_id, key, val):
        super(self.__class__, self)._run()
        self._run(image_id=image_id, key=key, val=val)


@command(image_cmds)
class image_compute_properties_set(_init_cyclades, _optional_json):
    """Add / update a set of properties for an image
    proeprties must be given in the form key=value, e.v.
    /image compute properties set <image-id> key1=val1 key2=val2
    """

    @errors.generic.all
    @errors.cyclades.connection
    @errors.plankton.id
    def _run(self, image_id, keyvals):
        meta = dict()
        for keyval in keyvals:
            key, val = keyval.split('=')
            meta[key] = val
        self._print(
            self.client.update_image_metadata(image_id, **meta), print_dict)

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
