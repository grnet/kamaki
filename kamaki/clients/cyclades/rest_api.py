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

from kamaki.clients.compute import ComputeClient
from kamaki.clients.utils import path4url
import json


class CycladesRestClient(ComputeClient):
    """Synnefo Cyclades REST API Client"""

    def servers_stats_get(self, server_id, success=200, **kwargs):
        """GET base_url/servers/<server_id>/stats"""
        path = path4url('servers', server_id, 'stats')
        return self.get(path, success=success, **kwargs)

    def networks_get(
            self,
            network_id='',
            command='',
            success=(200, 203),
            **kwargs):
        """GET base_url/networks[/network_id][/command] request

        :param network_id: integer (str or int)

        :param command: (str) 'detail' or ''

        :param success: success code or list or tuple of accepted success
            codes. if server response code is not in this list, a ClientError
            raises

        :returns: request response
        """
        path = path4url('networks', network_id, command)
        return self.get(path, success=success, **kwargs)

    def networks_delete(
            self,
            network_id='',
            command='',
            success=204,
            **kwargs):
        """DEL ETE base_url/networks[/network_id][/command] request

        :param network_id: integer (str or int)

        :param command: (str) 'detail' or ''

        :param success: success code or list or tuple of accepted success
            codes. if server response code is not in this list, a ClientError
            raises

        :returns: request response
        """
        path = path4url('networks', network_id, command)
        return self.delete(path, success=success, **kwargs)

    def networks_post(
            self,
            network_id='',
            command='',
            json_data=None,
            success=202,
            **kwargs):
        """POST base_url/servers[/server_id]/[command] request

        :param network_id: integer (str or int)

        :param command: (str) 'detail' or ''

        :param json_data: (dict) will be send as data

        :param success: success code or list or tuple of accepted success
            codes. if server response code is not in this list, a ClientError
            raises

        :returns: request response
        """
        data = json_data
        if json_data is not None:
            data = json.dumps(json_data)
            self.set_header('Content-Type', 'application/json')
            self.set_header('Content-Length', len(data))

        path = path4url('networks', network_id, command)
        return self.post(path, data=data, success=success, **kwargs)

    def networks_put(
            self,
            network_id='',
            command='',
            json_data=None,
            success=204,
            **kwargs):
        """PUT base_url/servers[/server_id]/[command] request

        :param network_id: integer (str or int)

        :param command: (str) 'detail' or ''

        :param json_data: (dict) will be send as data

        :param success: success code or list or tuple of accepted success
            codes. if server response code is not in this list, a ClientError
            raises

        :returns: request response
        """
        data = json_data
        if json_data is not None:
            data = json.dumps(json_data)
            self.set_header('Content-Type', 'application/json')
            self.set_header('Content-Length', len(data))

        path = path4url('networks', network_id, command)
        return self.put(path, data=data, success=success, **kwargs)
