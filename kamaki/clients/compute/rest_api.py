# Copyright 2012-2013 GRNET S.A. All rights reserved.
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

from kamaki.clients import Client
from kamaki.clients.utils import path4url
import json


class ComputeRestClient(Client):
    service_type = 'compute'

    # NON-cyclades
    def limits_get(self, success=200, **kwargs):
        """GET endpoint_url/limits

        :param success: success code or list or tupple of accepted success
            codes. if server response code is not in this list, a ClientError
            raises

        :returns: request response
        """
        path = path4url('limits')
        return self.get(path, success=success, **kwargs)

    def servers_get(
            self,
            server_id='', detail=False,
            changes_since=None,
            image=None,
            flavor=None,
            name=None,
            marker=None,
            limit=None,
            status=None,
            host=None,
            success=200,
            **kwargs):
        """GET endpoint_url/servers/['detail' | <server_id>]

        :param server_id: (int or int str) ignored if detail

        :param detail: (boolean)

        :param changes-since: A time/date stamp for when the server last
            changed status

        :param image: Name of the image in URL format

        :param flavor: Name of the flavor in URL format

        :param name: Name of the server as a string

        :param marker: UUID of the server at which you want to set a marker

        :param limit: (int) limit of values to return

        :param status: Status of the server (e.g. filter on "ACTIVE")

        :param host: Name of the host as a string

        :returns: request response
        """
        if not server_id:
            self.set_param('changes-since', changes_since, iff=changes_since)
            self.set_param('image', image, iff=image)
            self.set_param('flavor', flavor, iff=flavor)
            self.set_param('name', name, iff=name)
            self.set_param('marker', marker, iff=marker)
            self.set_param('limit', limit, iff=limit)
            self.set_param('status', status, iff=status)
            self.set_param('host', host, iff=host)

        path = path4url('servers', 'detail' if detail else (server_id or ''))
        return self.get(path, success=success, **kwargs)

    def servers_post(
            self,
            security_group=None,
            user_data=None,
            availability_zone=None,
            json_data=None,
            success=202,
            **kwargs):
        """POST endpoint_url/servers

        :param json_data: a json-formated dict that will be send as data

        :param security_group: (str)

        :param user_data: Use to pass configuration information or scripts upon
            launch. Must be Base64 encoded.

        :param availability_zone: (str)

        :returns: request response
        """

        self.set_param('security_group', security_group, iff=security_group)
        self.set_param('user_data', user_data, iff=user_data)
        self.set_param(
            'availability_zone', availability_zone, iff=availability_zone)

        if json_data:
            json_data = json.dumps(json_data)
            self.set_header('Content-Type', 'application/json')
            self.set_header('Content-Length', len(json_data))

        path = path4url('servers')
        return self.post(path, data=json_data, success=success, **kwargs)

    def servers_put(
            self,
            server_id, server_name=None, json_data=None, success=204,
            **kwargs):
        """PUT endpoint_url/servers/<server_id>

        :param json_data: a json-formated dict that will be send as data

        :param success: success code (iterable of) codes

        :raises ClientError: if returned code not in success list

        :returns: request response
        """
        self.set_param('server', server_name, iff=server_name)

        if json_data:
            json_data = json.dumps(json_data)
            self.set_header('Content-Type', 'application/json')
            self.set_header('Content-Length', len(json_data))
        path = path4url('servers', server_id)
        return self.put(path, data=json_data, success=success, **kwargs)

    def servers_delete(self, server_id, success=204, **kwargs):
        """DEL ETE endpoint_url/servers/<server_id>

        :param json_data: a json-formated dict that will be send as data

        :param success: success code (iterable of) codes

        :raises ClientError: if returned code not in success list

        :returns: request response
        """
        path = path4url('servers', server_id)
        return self.delete(path, success=success, **kwargs)

    def servers_metadata_get(self, server_id, key=None, success=200, **kwargs):
        """GET endpoint_url/servers/<server_id>/metadata[/key]

        :returns: request response
        """
        path = path4url('servers', server_id, 'metadata', key or '')
        return self.get(path, success=success, **kwargs)

    def servers_metadata_post(
            self, server_id, json_data=None, success=202, **kwargs):
        """POST endpoint_url/servers/<server_id>/metadata

        :returns: request response
        """
        if json_data:
            json_data = json.dumps(json_data)
            self.set_header('Content-Type', 'application/json')
            self.set_header('Content-Length', len(json_data))
        path = path4url('servers', server_id, 'metadata')
        return self.post(path, data=json_data, success=success, **kwargs)

    def servers_metadata_put(
            self, server_id, key=None, json_data=None, success=204, **kwargs):
        """PUT endpoint_url/servers/<server_id>/metadata[/key]

        :returns: request response
        """
        if json_data:
            json_data = json.dumps(json_data)
            self.set_header('Content-Type', 'application/json')
            self.set_header('Content-Length', len(json_data))
        path = path4url('servers', server_id, 'metadata', key or '')
        return self.put(path, data=json_data, success=success, **kwargs)

    def servers_metadata_delete(self, server_id, key, success=204, **kwargs):
        """DEL ETE endpoint_url/servers/<server_id>/metadata[/key]

        :returns: request response
        """
        path = path4url('servers', server_id, 'metadata', key)
        return self.delete(path, success=success, **kwargs)

    def servers_action_post(
            self, server_id, json_data=None, success=202, **kwargs):
        """POST endpoint_url/servers/<server_id>/action

        :returns: request response
        """
        if json_data:
            json_data = json.dumps(json_data)
            self.set_header('Content-Type', 'application/json')
            self.set_header('Content-Length', len(json_data))
        path = path4url('servers', server_id, 'action')
        return self.post(path, data=json_data, success=success, **kwargs)

    def servers_ips_get(
            self, server_id,
            network_id=None, changes_since=None, success=(304, 200),
            **kwargs):
        """GET endpoint_url/servers/<server_id>/ips[/network_id]

        :param changes_since: time/date stamp in UNIX/epoch time. Checks for
            changes since a previous request.

        :returns: request response
        """
        self.set_param('changes-since', changes_since, iff=changes_since)
        path = path4url('servers', server_id, 'ips', network_id or '')
        return self.get(path, success=success, **kwargs)

    def images_get(
            self,
            image_id='',
            detail=False,
            changes_since=None,
            server_name=None,
            name=None,
            status=None,
            marker=None,
            limit=None,
            type=None,
            success=200,
            **kwargs):
        """GET endpoint_url[/image_id][/command]

        :param image_id: (str) ignored if detail

        :param detail: (bool)

        --- Parameters ---
        :param changes_since: when the image last changed status

        :param server_name: Name of the server in URL format

        :param name: Name of the image

        :param status: Status of the image (e.g. filter on "ACTIVE")

        :param marker: UUID of the image at which you want to set a marker

        :param limit: Integer value for the limit of values to return

        :param type: Type of image (e.g. BASE, SERVER, or ALL)

        :returns: request response
        """
        if not image_id:
            self.set_param('changes-since', changes_since, iff=changes_since)
            self.set_param('name', name, iff=name)
            self.set_param('status', status, iff=status)
            self.set_param('marker', marker, iff=marker)
            self.set_param('limit', limit, iff=limit)
            self.set_param('type', type, iff=type)
            self.set_param('server', server_name, iff=server_name)

        path = path4url('images', 'detail' if detail else (image_id or ''))
        return self.get(path, success=success, **kwargs)

    def images_delete(self, image_id='', success=204, **kwargs):
        """DEL ETE endpoint_url/images/<image_id>

        :returns: request response
        """
        path = path4url('images', image_id)
        return self.delete(path, success=success, **kwargs)

    def images_metadata_get(self, image_id, key=None, success=200, **kwargs):
        """GET endpoint_url/<image_id>/metadata[/key]

        :returns: request response
        """
        path = path4url('images', image_id, 'metadata', key or '')
        return self.get(path, success=success, **kwargs)

    def images_metadata_post(
            self, image_id, json_data=None, success=201, **kwargs):
        """POST endpoint_url/images/<image_id>/metadata

        :returns: request response
        """
        if json_data is not None:
            json_data = json.dumps(json_data)
            self.set_header('Content-Type', 'application/json')
            self.set_header('Content-Length', len(json_data))

        path = path4url('images', image_id, 'metadata')
        return self.post(path, data=json_data, success=success, **kwargs)

    def images_metadata_put(
            self, image_id, key=None, json_data=None, success=201, **kwargs):
        """PUT endpoint_url/images/<image_id>/metadata

        :returns: request response
        """
        if json_data is not None:
            json_data = json.dumps(json_data)
            self.set_header('Content-Type', 'application/json')
            self.set_header('Content-Length', len(json_data))

        path = path4url('images', image_id, 'metadata')
        return self.put(path, data=json_data, success=success, **kwargs)

    def images_metadata_delete(self, image_id, key, success=204, **kwargs):
        """DEL ETE endpoint_url/images/<image_id>/metadata/key

        :returns: request response
        """
        path = path4url('images', image_id, 'metadata', key)
        return self.delete(path, success=success, **kwargs)

    def flavors_get(
            self,
            flavor_id='',
            detail=False,
            changes_since=None,
            minDisk=None,
            minRam=None,
            marker=None,
            limit=None,
            success=200,
            **kwargs):
        """GET endpoint_url[/flavor_id][/command]

        :param flavor_id: ignored if detail

        :param detail: (bool)

        --- Parameters ---

        :param changes_since: when the flavor last changed

        :param minDisk: minimum disk space in GB filter

        :param minRam: minimum RAM filter

        :param marker: UUID of the flavor at which to set a marker

        :param limit: limit the number of returned values

        :returns: request response
        """
        if not flavor_id:
            self.set_param('changes-since', changes_since, iff=changes_since)
            self.set_param('minDisk', minDisk, iff=minDisk)
            self.set_param('minRam', minRam, iff=minRam)
            self.set_param('marker', marker, iff=marker)
            self.set_param('limit', limit, iff=limit)

        path = path4url('flavors', 'detail' if detail else (flavor_id or ''))
        return self.get(path, success=success, **kwargs)

    def floating_ip_pools_get(self, success=200, **kwargs):
        path = path4url('os-floating-ip-pools')
        return self.get(path, success=success, **kwargs)

    def floating_ips_get(self, ip='', success=200, **kwargs):
        path = path4url('os-floating-ips', ip or '')
        return self.get(path, success=success, **kwargs)

    def floating_ips_post(self, json_data, ip='', success=200, **kwargs):
        path = path4url('os-floating-ips', ip or '')
        return self.post(path, json=json_data, success=success, **kwargs)

    def floating_ips_delete(self, ip='', success=204, **kwargs):
        path = path4url('os-floating-ips', ip or '')
        return self.delete(path, success=success, **kwargs)
