# Copyright 2014 GRNET S.A. All rights reserved.
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

from kamaki.clients import Client, utils


class BlockStorageRestClient(Client):
    """Block Storage (cinder) REST API"""
    service_type = 'volume'

    def volumes_get(self, detail=None, volume_id=None, success=200, **kwargs):
        """GET endpoint_url/volumes[/<detail> | /<volume_id>]

        :param detail: (boolean)
        :param volume_id: (str)
        """
        path = utils.path4url(
            'volumes', 'detail' if detail else volume_id or '')
        return self.get(path, success=success, **kwargs)

    def volumes_post(
            self, size,
            availability_zone=None,
            source_volid=None,
            display_description=None,
            snapshot_id=None,
            display_name=None,
            imageRef=None,
            volume_type=None,
            bootable=None,
            metadata=None,
            success=202,
            **kwargs):
        """POST endpoint_url/volumes

        :param size: (int) Volume size in GBs

        :param availability_zone: (str)
        :param source_volid: (str) ID for existing volume to create from
        :param display_description: (str)
        :param snapshot_id: (str) ID of existing snapshot to create from
        :param display_name: (str)
        :param imageRef: (str) ID of image to create from
        :param volume_type: (str)
        :param bootable: (boolean)
        :param metadata: (dict) {metakey: metavalue, ...}
        """
        path = utils.path4url('volumes')
        volume = dict(size=int(size))
        if availability_zone is not None:
            volume['availability_zone'] = availability_zone
        if source_volid is not None:
            volume['source_volid'] = source_volid
        if display_description is not None:
            volume['display_description'] = display_description
        if snapshot_id is not None:
            volume['snapshot_id'] = snapshot_id
        if display_name is not None:
            volume['display_name'] = display_name
        if imageRef is not None:
            volume['imageRef'] = imageRef
        if volume_type is not None:
            volume['volume_type'] = volume_type
        if bootable is not None:
            volume['bootable'] = bootable
        if metadata is not None:
            volume['metadata'] = metadata
        return self.post(
            path, json=dict(volume=volume), success=success, **kwargs)

    def volumes_put(
            self, volume_id,
            display_description=None,
            display_name=None,
            delete_on_termination=None,
            metadata=None,
            success=200,
            **kwargs):
        """PUT endpoint_url/volumes/volume_id

        :param volume_id: (str)

        :param display_description: (str)
        :param display_name: (str)
        :param metadata: (dict) {metakey: metavalue, ...}
        """
        path = utils.path4url('volumes', volume_id)
        volume = dict()
        if display_description is not None:
            volume['display_description'] = display_description
        if display_name is not None:
            volume['display_name'] = display_name
        if delete_on_termination is not None:
            volume['delete_on_termination'] = bool(delete_on_termination)
        if metadata is not None:
            volume['metadata'] = metadata
        return self.put(
            path, json=dict(volume=volume), success=success, **kwargs)

    def volumes_delete(self, volume_id, success=202, **kwargs):
        """DEL ETE endpoint_url/volumes/volume_id
        :param volume_id: (str)
        """
        return self.delete(
            utils.path4url('volumes', volume_id), success=success, **kwargs)

    def snapshots_get(
            self, detail=None, snapshot_id=None, success=200, **kwargs):
        """GET endpoint_url/snapshots[/<detail> | /<snapshot_id>]

        :param detail: (boolean)

        :param snapshot_id: (str)
        """
        path = utils.path4url(
            'snapshots', 'detail' if detail else snapshot_id or '')
        return self.get(path, success=success, **kwargs)

    def snapshots_post(
            self, volume_id,
            force=None,
            display_name=None,
            display_description=None,
            success=202,
            **kwargs):
        """POST endpoint_url/snapshots

        :param volume_id: (str)

        :param force: (boolean)
        :param display_name: (str)
        :param display_description: (str)
        """
        path = utils.path4url('snapshots')
        snapshot = dict(volume_id=volume_id)
        if force is not None:
            snapshot['force'] = bool(force)
        if display_name is not None:
            snapshot['display_name'] = display_name
        if display_description is not None:
            snapshot['display_description'] = display_description
        return self.post(
            path, json=dict(snapshot=snapshot), success=success, **kwargs)

    def snapshots_put(
            self, snapshot_id,
            display_description=None,
            display_name=None,
            success=200,
            **kwargs):
        """PUT endpoint_url/snapshots/spapshot_id

        :param snapshot_id: (str)

        :param display_description: (str)
        :param display_name: (str)
        """
        path = utils.path4url('snapshots', snapshot_id)
        snapshot = dict()
        if display_description is not None:
            snapshot['display_description'] = display_description
        if display_name is not None:
            snapshot['display_name'] = display_name
        return self.put(
            path, json=dict(snapshot=snapshot), success=success, **kwargs)

    def snapshots_delete(self, snapshot_id, success=202, **kwargs):
        """DEL ETE endpoint_url/snapshots/snapshot_id
        :param snapshot_id: (str)
        """
        path = utils.path4url('snapshots', snapshot_id)
        return self.delete(path, success=success, **kwargs)

    def types_get(self, type_id=None, success=200, **kwargs):
        """GET endpoint_url/types[/<type_id>]"""
        path = utils.path4url('types', type_id or '')
        return self.get(path, success=success, **kwargs)
