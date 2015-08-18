# Copyright 2012-2015 GRNET S.A. All rights reserved.
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
from os import path
from logging import getLogger
from io import StringIO
from pydoc import pager

from kamaki.cli import command
from kamaki.cli.cmdtree import CommandTree
from kamaki.cli.utils import filter_dicts_by_dict, format_size
from kamaki.clients.image import ImageClient
from kamaki.clients.pithos import PithosClient
from kamaki.clients import ClientError
from kamaki.cli.argument import (
    FlagArgument, ValueArgument, RepeatableArgument, KeyValueArgument,
    IntArgument, ProgressBarArgument, PithosLocationArgument)
from kamaki.cli.cmds.cyclades import _CycladesInit
from kamaki.cli.errors import CLIError, raiseCLIError, CLIInvalidArgument
from kamaki.cli.cmds import (
    CommandInit, errors, client_log, OptionalOutput, NameFilter, IDFilter)


image_cmds = CommandTree('image', 'Cyclades/Plankton API image commands')
imagecompute_cmds = CommandTree(
    'imagecompute', 'Cyclades/Compute API image commands')
namespaces = [image_cmds, imagecompute_cmds]


howto_image_file = [
    'To get current user id', '  kamaki user info',
    'To list all containers', '  kamaki container list',
    'To create a new container', '  kamaki container create CONTAINER',
    'To list container contents', '  kamaki file list /CONTAINER',
    'To upload files', '  kamaki file upload FILE /CONTAINER[/PATH]',
    'To register an image',
    '  kamaki image register --name=IMAGE_NAME --location=/CONTAINER/PATH']

about_image_id = ['To list all images', '  kamaki image list']


log = getLogger(__name__)


class _ImageInit(CommandInit):
    @errors.Generic.all
    @client_log
    def _run(self):
        self.client = self.get_client(ImageClient, 'plankton')

    def main(self):
        self._run()


# Plankton Image Commands

def load_image_meta(filepath):
    """
    :param filepath: (str) the (relative) path of the metafile

    :returns: (dict) json_formated

    :raises TypeError, AttributeError: Invalid json format

    :raises AssertionError: Valid json but invalid image properties dict
    """
    with open(path.abspath(filepath)) as f:
        meta_dict = load(f)
        try:
            for k, v in meta_dict.items():
                if k.lower() == 'properties':
                    for pk, pv in v.items():
                        prop_ok = not isinstance(pv, (dict, list))
                        assert prop_ok, 'Invalid property value (key %s)' % pk
                        key_ok = not (' ' in k or '-' in k)
                        assert key_ok, 'Invalid property key %s' % k
                    continue
                meta_ok = not isinstance(v, (dict, list))
                assert meta_ok, 'Invalid value (meta key %s)' % k
                meta_ok = ' ' not in k
                assert meta_ok, 'Invalid meta key [%s]' % k
                meta_dict[k] = '%s' % v
            return meta_dict
        except AssertionError:
            log.debug('Failed to load properties from file %s' % filepath)
            raise


@command(image_cmds)
class image_list(_ImageInit, OptionalOutput, NameFilter, IDFilter):
    """List images accessible by user"""

    arguments = dict(
        detail=FlagArgument('show detailed output', ('-l', '--details')),
        container_format=ValueArgument(
            'filter by container format',
            '--container-format'),
        disk_format=ValueArgument('filter by disk format', '--disk-format'),
        size_min=IntArgument('filter by minimum size', '--size-min'),
        size_max=IntArgument('filter by maximum size', '--size-max'),
        status=ValueArgument('filter by status', '--status'),
        owner=ValueArgument('filter by owner', '--owner'),
        owner_name=ValueArgument('filter by owners username', '--owner-name'),
        order=ValueArgument(
            'order by FIELD ( - to reverse order)',
            '--order',
            default=''),
        limit=IntArgument('limit number of listed images', ('-n', '--number')),
        more=FlagArgument(
            'output results in pages (-n to set items per page, default 10)',
            '--more'),
        enum=FlagArgument('Enumerate results', '--enumerate'),
        prop=KeyValueArgument('filter by property key=value', ('--property')),
        prop_like=KeyValueArgument(
            'fliter by property key=value where value is part of actual value',
            ('--property-like')),
        image_ID_for_members=ValueArgument(
            'List members of an image', '--members-of'),
    )

    def _filter_by_owner(self, images):
        ouuid = self['owner'] or self._username2uuid(self['owner_name'])
        return filter_dicts_by_dict(images, dict(owner=ouuid))

    def _add_owner_name(self, images):
        uuids = self._uuids2usernames(
            list(set([img['owner'] for img in images])))
        for img in images:
            img['owner'] += ' (%s)' % uuids[img['owner']]
        return images

    def _filter_by_properties(self, images):
        new_images = []
        for img in images:
            props = [dict(img['properties'])]
            if self['prop']:
                props = filter_dicts_by_dict(props, self['prop'])
            if props and self['prop_like']:
                props = filter_dicts_by_dict(
                    props, self['prop_like'], exact_match=False)
            if props:
                new_images.append(img)
        return new_images

    def _members(self, image_id):
        members = self.client.list_members(image_id)
        if not self['output_format']:
            uuids = [member['member_id'] for member in members]
            usernames = self._uuids2usernames(uuids)
            for member in members:
                member['member_id'] += ' (%s)' % usernames[member['member_id']]
        self.print_(members, title=('member_id',))

    @errors.Generic.all
    @errors.Cyclades.connection
    def _run(self):
        super(self.__class__, self)._run()
        if self['image_ID_for_members']:
            return self._members(self['image_ID_for_members'])
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
        detail = any([self[x] for x in (
            'detail', 'prop', 'prop_like', 'owner', 'owner_name')])

        images = self.client.list_public(detail, filters, order)

        if self['owner'] or self['owner_name']:
            images = self._filter_by_owner(images)
        if self['prop'] or self['prop_like']:
            images = self._filter_by_properties(images)
        images = self._filter_by_id(images)
        images = self._non_exact_name_filter(images)
        for img in [] if self['output_format'] else images:
            try:
                img['size'] = format_size(img['size'])
            except KeyError:
                continue

        if self['detail'] and not self['output_format']:
            images = self._add_owner_name(images)
        elif detail and not self['detail']:
            for img in images:
                for key in set(img).difference([
                        'id',
                        'name',
                        'status',
                        'container_format',
                        'disk_format',
                        'size']):
                    img.pop(key)
        kwargs = dict(with_enumeration=self['enum'])
        if self['limit']:
            images = images[:self['limit']]
        if self['more']:
            kwargs['out'] = StringIO()
            kwargs['title'] = ()
        self.print_(images, **kwargs)
        if self['more']:
            pager(kwargs['out'].getvalue())

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(image_cmds)
class image_info(_ImageInit, OptionalOutput):
    """Get image metadata"""

    arguments = dict(
        hashmap=FlagArgument(
            'Get image file hashmap instead of metadata', '--hashmap'),
    )

    @errors.Generic.all
    @errors.Image.connection
    @errors.Image.id
    def _run(self, image_id):
        meta = self.client.get_meta(image_id)
        if self['hashmap']:
            print meta['location']
            location = meta['location'].split('pithos://')[1]
            location = location.split('/')
            uuid, container = location[0], location[1]
            pithos = self.get_client(PithosClient, 'pithos')
            pithos.account, pithos.container = uuid, container
            path = '/'.join(location[2:])
            meta = pithos.get_object_hashmap(path)
        elif not self['output_format']:
            try:
                meta['owner'] += ' (%s)' % self._uuid2username(meta['owner'])
            except KeyError as ke:
                log.debug('%s' % ke)
            try:
                meta['size'] = format_size(meta['size'])
            except KeyError as ke:
                log.debug('%s' % ke)
        self.print_(meta, self.print_dict)

    def main(self, image_id):
        super(self.__class__, self)._run()
        self._run(image_id=image_id)


@command(image_cmds)
class image_modify(_ImageInit):
    """Add / update metadata and properties for an image
    Preserves values not explicitly modified
    """

    arguments = dict(
        image_name=ValueArgument('Change name', '--name'),
        disk_format=ValueArgument('Change disk format', '--disk-format'),
        container_format=ValueArgument(
            'Change container format', '--container-format'),
        status=ValueArgument('Change status', '--status'),
        publish=FlagArgument('Make the image public', '--public'),
        unpublish=FlagArgument('Make the image private', '--private'),
        property_to_set=KeyValueArgument(
            'set property in key=value form (can be repeated)',
            ('-p', '--property-set')),
        property_to_del=RepeatableArgument(
            'Delete property by key (can be repeated)', '--property-del'),
        member_ID_to_add=RepeatableArgument(
            'Add member to image (can be repeated)', '--member-add'),
        member_ID_to_remove=RepeatableArgument(
            'Remove a member (can be repeated)', '--member-del'),
    )
    required = [
        'image_name', 'disk_format', 'container_format', 'status', 'publish',
        'unpublish', 'property_to_set', 'member_ID_to_add',
        'member_ID_to_remove', 'property_to_del']

    @errors.Generic.all
    @errors.Image.connection
    @errors.Image.permissions
    @errors.Image.id
    def _run(self, image_id):
        for mid in (self['member_ID_to_add'] or []):
            self.client.add_member(image_id, mid)
        for mid in (self['member_ID_to_remove'] or []):
            self.client.remove_member(image_id, mid)
        meta = self.client.get_meta(image_id)
        for k, v in self['property_to_set'].items():
            meta['properties'][k.upper()] = v
        for k in (self['property_to_del'] or []):
            meta['properties'][k.upper()] = None
        self.client.update_image(
            image_id,
            name=self['image_name'],
            disk_format=self['disk_format'],
            container_format=self['container_format'],
            status=self['status'],
            public=self['publish'] or (False if self['unpublish'] else None),
            **meta['properties'])

    def main(self, image_id):
        super(self.__class__, self)._run()
        self._run(image_id=image_id)


@command(image_cmds)
class image_register(_ImageInit, OptionalOutput):
    """(Re)Register an image file to an Image service
    The image file must be stored at a pithos repository
    Some metadata can be set by user (e.g., disk-format) while others are set
    by the system (e.g., image id).
    Custom user metadata are termed as "properties".
    A register command creates a remote meta file at
    /CONTAINER/IMAGE_PATH.meta
    Users may download and edit this file and use it to re-register.
    In case of a meta file, runtime arguments for metadata or properties
    override meta file settings.
    """
    container_info_cache = {}
    arguments = dict(
        checksum=ValueArgument('Set image checksum', '--checksum'),
        container_format=ValueArgument(
            'Set container format', '--container-format'),
        disk_format=ValueArgument('Set disk format', '--disk-format'),
        owner_name=ValueArgument('Set user uuid by user name', '--owner-name'),
        properties=KeyValueArgument(
            'Add property (user-specified metadata) in key=value form'
            '(can be repeated)',
            ('-p', '--property')),
        is_public=FlagArgument('Mark image as public', '--public'),
        size=IntArgument('Set image size in bytes', '--size'),
        metafile=ValueArgument(
            'Load metadata from a json-formated file IMAGE_FILE.meta :'
            '{"key1": "val1", "key2": "val2", ..., "properties: {...}"}',
            ('--metafile')),
        force_upload=FlagArgument(
            'Overwrite remote files (image file, metadata file)',
            ('-f', '--force')),
        no_metafile_upload=FlagArgument(
            'Do not store metadata in remote meta file',
            ('--no-metafile-upload')),
        container=ValueArgument(
            'Pithos+ container containing the image file',
            ('-C', '--container')),
        uuid=ValueArgument('Custom user uuid', '--uuid'),
        local_image_path=ValueArgument(
            'Local image file path to upload and register '
            '(still need target file in the form /CONTAINER/REMOTE-PATH )',
            '--upload-image-file'),
        progress_bar=ProgressBarArgument(
            'Do not use progress bar', '--no-progress-bar', default=False),
        name=ValueArgument('The name of the new image', '--name'),
        pithos_location=PithosLocationArgument(
            'The Pithos+ image location to put the image at. Format:       '
            'pithos://USER_UUID/CONTAINER/IMAGE_PATH             or   '
            '/CONTAINER/IMAGE_PATH',
            '--location')
    )
    required = ('name', 'pithos_location')

    def _get_pithos_client(self, locator):
        pithos = self.get_client(PithosClient, 'pithos')
        pithos.account, pithos.container = locator.uuid, locator.container
        return pithos

    def _load_params_from_file(self, location):
        params, properties = dict(), dict()
        pfile = self['metafile']
        if pfile:
            try:
                for k, v in load_image_meta(pfile).items():
                    key = k.lower().replace('-', '_')
                    if key == 'properties':
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

    def _assert_remote_file_not_exist(self, pithos, path):
        if pithos and not self['force_upload']:
            try:
                pithos.get_object_info(path)
                raise CLIError('File already exists', importance=2, details=[
                    'A remote file /%s/%s already exists' % (
                        pithos.container, path),
                    'Use %s to force upload' % self.arguments[
                        'force_upload'].lvalue])
            except ClientError as ce:
                if ce.status != 404:
                    raise

    @errors.Generic.all
    @errors.Image.connection
    def _run(self, name, locator):
        location, pithos = locator.value, None
        if self['local_image_path']:
            with open(self['local_image_path']) as f:
                pithos = self._get_pithos_client(locator)
                self._assert_remote_file_not_exist(pithos, locator.object)
                (pbar, upload_cb) = self._safe_progress_bar('Uploading')
                if pbar:
                    hash_bar = pbar.clone()
                    hash_cb = hash_bar.get_generator('Calculating hashes')
                try:
                    pithos.upload_object(
                        locator.object, f,
                        hash_cb=hash_cb, upload_cb=upload_cb,
                        container_info_cache=self.container_info_cache)
                finally:
                    if pbar:
                        pbar.finish()

        (params, properties, new_loc) = self._load_params_from_file(location)
        if location != new_loc:
            locator.value = new_loc
        self._load_params_from_args(params, properties)

        if not self['no_metafile_upload']:
            # check if metafile exists
            pithos = pithos or self._get_pithos_client(locator)
            meta_path = '%s.meta' % locator.object
            self._assert_remote_file_not_exist(pithos, meta_path)

        # register the image
        try:
            r = self.client.register(name, location, params, properties)
        except ClientError as ce:
            if ce.status in (400, 404):
                raise CLIError(
                    'Nonexistent image file location %s' % location,
                    details=[
                        '%s' % ce,
                        'Does the image file %s exist at container %s ?' % (
                            locator.object, locator.container)
                    ] + howto_image_file)
            raise
        r['owner'] += ' (%s)' % self._uuid2username(r['owner'])
        self.print_(r, self.print_dict)

        # upload the metadata file
        if not self['no_metafile_upload']:
            try:
                meta_headers = pithos.upload_from_string(
                    meta_path, dumps(r, indent=2),
                    sharing=dict(read='*' if params.get('is_public') else ''),
                    container_info_cache=self.container_info_cache)
            except TypeError:
                self.error('Failed to dump metafile /%s/%s' % (
                    locator.container, meta_path))
                return
            if self['output_format']:
                self.print_json(dict(
                    metafile_location='/%s/%s' % (
                        locator.container, meta_path),
                    headers=meta_headers))
            else:
                self.error('Metadata file uploaded as /%s/%s (version %s)' % (
                    locator.container,
                    meta_path,
                    meta_headers['x-object-version']))

    def main(self):
        super(self.__class__, self)._run()
        locator = self.arguments['pithos_location']
        locator.setdefault('uuid', self.astakos.user_term('id'))
        locator.object = locator.object or path.basename(
            self['local_image_path'] or '')
        if not locator.object:
            raise CLIInvalidArgument(
                'Missing the image file or object', details=[
                    'Pithos+ URI %s does not point to a physical image' % (
                        locator.value),
                    'A physical image is necessary.',
                    'It can be a remote Pithos+ object or a local file.',
                    'To specify a remote image object:',
                    '  %s [pithos://UUID]/CONTAINER/PATH' % locator.lvalue,
                    'To specify a local file:',
                    '  %s [pithos://UUID]/CONTAINER[/PATH] %s LOCAL_PATH' % (
                        locator.lvalue,
                        self.arguments['local_image_path'].lvalue)])
        self.arguments['pithos_location'].setdefault(
            'uuid', self.astakos.user_term('id'))
        self._run(self['name'], locator)


@command(image_cmds)
class image_unregister(_ImageInit):
    """Unregister an image (does not delete the image file)"""

    @errors.Generic.all
    @errors.Image.connection
    @errors.Image.permissions
    @errors.Image.id
    def _run(self, image_id):
        self.client.unregister(image_id)

    def main(self, image_id):
        super(self.__class__, self)._run()
        self._run(image_id=image_id)


# Compute Image Commands

@command(imagecompute_cmds)
class imagecompute_list(_CycladesInit, OptionalOutput, NameFilter, IDFilter):
    """List images"""
    arguments = dict(
        detail=FlagArgument('show detailed output', ('-l', '--details')),
        limit=IntArgument('limit number listed images', ('-n', '--number')),
        more=FlagArgument('handle long lists of results', '--more'),
        enum=FlagArgument('Enumerate results', '--enumerate'),
        user_id=ValueArgument('filter by user_id', '--user-id'),
        user_name=ValueArgument('filter by username', '--user-name'),
        meta=KeyValueArgument(
            'filter by metadata key=value (can be repeated)', ('--metadata')),
        meta_like=KeyValueArgument(
            'filter by metadata key=value (can be repeated)',
            ('--metadata-like'))
    )

    def _filter_by_metadata(self, images):
        new_images = []
        for img in images:
            meta = [dict(img['metadata'])]
            if self['meta']:
                meta = filter_dicts_by_dict(meta, self['meta'])
            if meta and self['meta_like']:
                meta = filter_dicts_by_dict(
                    meta, self['meta_like'], exact_match=False)
            if meta:
                new_images.append(img)
        return new_images

    def _filter_by_user(self, images):
        uuid = self['user_id'] or self._username2uuid(self['user_name'])
        return filter_dicts_by_dict(images, dict(user_id=uuid))

    def _add_name(self, images, key='user_id'):
        uuids = self._uuids2usernames(
            list(set([img[key] for img in images])))
        for img in images:
            img[key] += ' (%s)' % uuids[img[key]]
        return images

    @errors.Generic.all
    @errors.Cyclades.connection
    def _run(self):
        withmeta = bool(self['meta'] or self['meta_like'])
        withuser = bool(self['user_id'] or self['user_name'])
        detail = self['detail'] or withmeta or withuser
        images = self.client.list_images(detail)
        images = self._filter_by_name(images)
        images = self._filter_by_id(images)
        if withuser:
            images = self._filter_by_user(images)
        if withmeta:
            images = self._filter_by_metadata(images)
        if self['detail'] and not self['output_format']:
            images = self._add_name(self._add_name(images, 'tenant_id'))
        elif detail and not self['detail']:
            for img in images:
                for key in set(img).difference(['id', 'name']):
                    img.pop(key)
        kwargs = dict(with_enumeration=self['enum'])
        if self['limit']:
            images = images[:self['limit']]
        if self['more']:
            kwargs['out'] = StringIO()
            kwargs['title'] = ()
        self.print_(images, **kwargs)
        if self['more']:
            pager(kwargs['out'].getvalue())

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(imagecompute_cmds)
class imagecompute_info(_CycladesInit, OptionalOutput):
    """Get detailed information on an image"""

    @errors.Generic.all
    @errors.Cyclades.connection
    @errors.Image.id
    def _run(self, image_id):
        image = self.client.get_image_details(image_id)
        uuids = [image['user_id']]
        usernames = self._uuids2usernames(uuids)
        image['user_id'] += ' (%s)' % usernames[image['user_id']]
        self.print_(image, self.print_dict)

    def main(self, image_id):
        super(self.__class__, self)._run()
        self._run(image_id=image_id)


@command(imagecompute_cmds)
class imagecompute_delete(_CycladesInit):
    """Delete an image (WARNING: image file is also removed)"""

    @errors.Generic.all
    @errors.Cyclades.connection
    @errors.Image.permissions
    @errors.Image.id
    def _run(self, image_id):
        self.client.delete_image(image_id)

    def main(self, image_id):
        super(self.__class__, self)._run()
        self._run(image_id=image_id)


@command(imagecompute_cmds)
class imagecompute_modify(_CycladesInit):
    """Modify image properties (metadata)"""

    arguments = dict(
        property_to_add=KeyValueArgument(
            'Add property in key=value format (can be repeated)',
            ('--property-add')),
        property_to_del=RepeatableArgument(
            'Delete property by key (can be repeated)',
            ('--property-del'))
    )
    required = ['property_to_add', 'property_to_del']

    @errors.Generic.all
    @errors.Cyclades.connection
    @errors.Image.permissions
    @errors.Image.id
    def _run(self, image_id):
        if self['property_to_add']:
            self.client.update_image_metadata(
                image_id, **self['property_to_add'])
        for key in (self['property_to_del'] or []):
            self.client.delete_image_metadata(image_id, key)

    def main(self, image_id):
        super(self.__class__, self)._run()
        self._run(image_id=image_id)
