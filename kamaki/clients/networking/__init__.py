# Copyright 2013 GRNET S.A. All rights reserved.
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

from kamaki.clients import ClientError
from kamaki.clients.networking.rest_api import NetworkingRestClient


class NetworkingClient(NetworkingRestClient):
    """OpenStack Network API 2.0 client"""

    def list_networks(self):
        r = self.networks_get(success=200)
        return r.json['networks']

    def create_network(self, name, admin_state_up=None, shared=None):
        req = dict(network=dict(
            name=name or '', admin_state_up=bool(admin_state_up)))
        r = self.networks_post(json_data=req, shared=shared, success=201)
        return r.json['network']

    def create_networks(self, networks, shared=None):
        """
        :param networks: (list or tuple) [
            {name: ..., admin_state_up: ...},
            {name:..., admin_state_up: ...}]
            name is mandatory, the rest is optional
            e.g. create_networks(({name: 'net1', shared: True}, {name: net2}))
        :returns: list of dicts of created networks
        :raises ValueError: if networks is misformated
        :raises ClientError: if the request failed or didn't return 201
        """
        try:
            msg = 'The networks parameter must be list or tuple'
            assert (
                isinstance(networks, list) or isinstance(networks, tuple)), msg
            for network in networks:
                msg = 'Network specification %s is not a dict' % network
                assert isinstance(network, dict), msg
                err = set(network).difference(('name', 'admin_state_up'))
                if err:
                    raise ValueError(
                        'Invalid key(s): %s in network specification %s' % (
                            err, network))
                msg = 'Name is missing in network specification: %s' % network
                assert network.get('name', None), msg
                network.setdefault('admin_state_up', False)
        except AssertionError as ae:
            raise ValueError('%s' % ae)

        req = dict(networks=list(networks))
        r = self.networks_post(json_data=req, shared=shared, success=201)
        return r.json['networks']

    def get_network_details(self, network_id):
        r = self.networks_get(network_id, success=200)
        return r.json['network']

    def update_network(
            self, network_id, name=None, admin_state_up=None, shared=None):
        network = dict()
        if name:
            network['name'] = name
        if admin_state_up not in (None, ):
            network['admin_state_up'] = admin_state_up
        network = dict(network=network)
        r = self.networks_put(
            network_id, json_data=network, shared=shared, success=200)
        return r.json['network']

    def delete_network(self, network_id):
        r = self.networks_delete(network_id, success=204)
        return r.headers
