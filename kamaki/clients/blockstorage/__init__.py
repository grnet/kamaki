# Copyright 2014-2015 GRNET S.A. All rights reserved.
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

from kamaki.clients.blockstorage.rest_api import BlockStorageRestClient
from kamaki.clients import ClientError, Waiter, wait


class BlockStorageClient(BlockStorageRestClient, Waiter):
    """OpenStack Block Storage v2 client"""

    def list_volumes(self, detail=None):
        """:returns: (list)"""
        r = self.volumes_get(detail=detail)
        return r.json['volumes']

    def get_volume_details(self, volume_id):
        """:returns: (dict)"""
        r = self.volumes_get(volume_id=volume_id)
        return r.json['volume']

    def create_volume(
            self, size,
            availability_zone=None,
            source_volid=None,
            display_name=None,
            display_description=None,
            snapshot_id=None,
            imageRef=None,
            volume_type=None,
            bootable=None,
            metadata=None):
        """:returns: (dict) new volumes' details"""
        r = self.volumes_post(
            size,
            availability_zone=availability_zone,
            source_volid=source_volid,
            display_name=display_name,
            display_description=display_description,
            snapshot_id=snapshot_id,
            imageRef=imageRef,
            volume_type=volume_type,
            bootable=bootable,
            metadata=metadata)
        return r.json['volume']

    def update_volume(
            self, volume_id,
            display_name=None,
            display_description=None,
            delete_on_termination=None,
            metadata=None):
        """:returns: (dict) volumes' new details"""
        args = (
            display_description, display_name, delete_on_termination, metadata)
        if args == (None, None, None, None):
            return self.get_volume_details(volume_id)
        r = self.volumes_put(
            volume_id,
            display_name=display_name,
            display_description=display_description,
            delete_on_termination=delete_on_termination,
            metadata=metadata)
        return r.json['volume']

    def delete_volume(self, volume_id):
        r = self.volumes_delete(volume_id)
        return r.headers

    def list_snapshots(self, detail=None):
        """:returns: (list)"""
        r = self.snapshots_get(detail=detail)
        return r.json['snapshots']

    def get_snapshot_details(self, snapshot_id):
        """:returns: (dict)"""
        r = self.snapshots_get(snapshot_id=snapshot_id)
        return r.json['snapshot']

    def create_snapshot(
            self, volume_id,
            force=None, display_name=None, display_description=None):
        """:returns: (dict) new snapshots' details"""
        r = self.snapshots_post(
            volume_id,
            force=force,
            display_name=display_name,
            display_description=display_description)
        return r.json['snapshot']

    def update_snapshot(
            self, snapshot_id, display_name=None, display_description=None):
        """:returns: (dict) snapshots' new details"""
        if (display_name, display_description) == (None, None):
            return self.get_snapshot_details(snapshot_id)
        r = self.snapshots_put(
            snapshot_id,
            display_name=display_name, display_description=display_description)
        return r.json['snapshot']

    def delete_snapshot(self, snapshot_id):
        r = self.snapshots_delete(snapshot_id)
        return r.headers

    def list_volume_types(self):
        r = self.types_get()
        return r.json['volume_types']

    def get_volume_type_details(self, type_id):
        r = self.types_get(type_id)
        return r.json['volume_type']

    #  Wait methods

    def get_volume_status(self, volume_id):
        """Deprecated, will be removed in 0.15"""
        r = self.get_volume_details(volume_id)
        return r['status'], None

    def wait_volume(
            self, volume_id, stop=None, delay=1, timeout=100, wait_cb=None):
        """Wait (block) while the stop method returns True, poll for status
            each time
        :param volume_id: (str)
        :param stop: (method) takes the volume details dict as input, returns
            true if the blocking must stop. Default: wait while 'creating'
        :param delay: (int) seconds between polls
        :param timeout: (int) in seconds
        :param wait_cb: (method) optional call back method called after each
            poll, provided by the caller. Typically used to monitor progress
            Takes volume details dict as parameter
        """
        return wait(
            self.get_volume_details, (volume_id, ),
            stop or (lambda i: i['status'] != 'creating'),
            delay, timeout, wait_cb)

    def wait_volume_while(
            self, volume_id,
            current_status='creating', delay=1, max_wait=100, wait_cb=None):
        return wait(
            self.get_volume_details, (volume_id, ),
            lambda i: i['status'] != current_status,
            delay, max_wait, wait_cb)

    def wait_volume_until(
            self, volume_id,
            target_status='in_use', delay=1, max_wait=100, wait_cb=None):
        return wait(
            self.get_volume_details, (volume_id, ),
            lambda i: i['status'] == target_status,
            delay, max_wait, wait_cb)
