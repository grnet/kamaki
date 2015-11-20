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
# or implied, of GRNET S.A.

from kamaki.clients.compute import ComputeClient
from kamaki.clients.blockstorage import BlockStorageClient
from kamaki.clients.utils import path4url


class CycladesComputeRestClient(ComputeClient):
    """Synnefo Cyclades REST API Client"""

    def servers_stats_get(self, server_id, **kwargs):
        """GET endpoint_url/servers/<server_id>/stats"""
        path = path4url('servers', server_id, 'stats')
        return self.get(path, success=200, **kwargs)

    def servers_diagnostics_get(self, server_id, **kwargs):
        """GET endpoint_url/servers/<server_id>/diagnostics"""
        path = path4url('servers', server_id, 'diagnostics')
        return self.get(path, success=200, **kwargs)

    def volume_attachment_get(self, server_id, attachment_id=None, **kwargs):
        path_args = ['servers', server_id, 'os-volume_attachments']
        path_args += [attachment_id, ] if attachment_id else []
        path = path4url(*path_args)
        success = kwargs.pop('success', 200)
        return self.get(path, success=success, **kwargs)

    def volume_attachment_post(self, server_id, volume_id, **kwargs):
        path = path4url('servers', server_id, 'os-volume_attachments')
        data = dict(volumeAttachment=dict(volumeId=volume_id))
        success = kwargs.pop('success', 202)
        return self.post(path, json=data, success=success, **kwargs)

    def volume_attachment_delete(self, server_id, attachment_id, **kwargs):
        path = path4url(
            'servers', server_id, 'os-volume_attachments', attachment_id)
        success = kwargs.pop('success', 202)
        return self.delete(path, success=success, **kwargs)


#  Backwards compatibility
CycladesRestClient = CycladesComputeRestClient


class CycladesBlockStorageRestClient(BlockStorageClient):
    """Synnefo Cyclades Block Storage REST API Client"""

    def volumes_post(
            self, size, display_name,
            server_id=None,
            display_description=None,
            snapshot_id=None,
            imageRef=None,
            volume_type=None,
            metadata=None,
            project=None,
            success=202,
            **kwargs):
        path = path4url('volumes')
        volume = dict(size=int(size), display_name=display_name)
        if server_id is not None:
            volume['server_id'] = server_id
        if display_description is not None:
            volume['display_description'] = display_description
        if snapshot_id is not None:
            volume['snapshot_id'] = snapshot_id
        if imageRef is not None:
            volume['imageRef'] = imageRef
        if volume_type is not None:
            volume['volume_type'] = volume_type
        if metadata is not None:
            volume['metadata'] = metadata
        if project is not None:
            volume['project'] = project
        return self.post(
            path, json=dict(volume=volume), success=success, **kwargs)

    def volumes_action_post(self, volume_id, json_data, success=200, **kwargs):
        path = path4url('volumes', volume_id, 'action')
        return self.post(path, json=json_data, success=success, **kwargs)
