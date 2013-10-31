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

from kamaki.clients import Client, ClientError
from kamaki.clients.utils import path4url
from json import dumps


class NetworkRestClient(Client):

    def networks_get(self, network_id=None, **kwargs):
        path = path4url('networks', network_id) if (
            network_id) else path4url('networks')
        return self.get(path, **kwargs)

    def networks_post(self, json_data=None, shared=None, **kwargs):
        path = path4url('networks')
        self.set_param(shared, bool(shared), iff=shared)
        return self.post(
            path, data=dumps(json_data) if json_data else None, **kwargs)

    def networks_put(
            self, network_id,
            json_data=None, admin_state_up=None, shared=None, **kwargs):
        path = path4url('networks', network_id)

        self.set_param(
            'admin_state_up', bool(admin_state_up), iff=admin_state_up)
        self.set_param(shared, bool(shared), iff=shared)

        return self.put(
            path, data=dumps(json_data) if json_data else None, **kwargs)

    def networks_delete(self, network_id, **kwargs):
        return self.delete(path4url('networks', network_id), **kwargs)

    def subnets_get(self, json_data=None, subnet_id=None, **kwargs):
        if subnet_id:
            return self.get(path4url('subnets', subnet_id), **kwargs)
        elif json_data:
            return self.get(
                path4url('subnets'), data=dumps(json_data), **kwargs)
        else:
            raise ClientError('No subnet_id or json_data in GET subnets')

    def subnets_post(self, **kwargs):
        return self.post(path4url('subnets'), **kwargs)

    def subnets_put(self, subnet_id, **kwargs):
        return self.put(path4url('subnets', subnet_id), **kwargs)

    def subnets_delete(self, subnet_id, **kwargs):
        return self.delete(path4url('subnets', subnet_id), **kwargs)

    def ports_get(self, port_id=None, **kwargs):
        path = path4url('ports', port_id) if port_id else path4url('ports')
        return self.get(path, **kwargs)

    def ports_post(
            self,
            json_data=None,
            name=None, mac_address=None, fixed_ips=None, security_groups=None,
            **kwargs):
        self.set_param('name', name, iff=name)
        self.set_param('mac_address', mac_address, iff=mac_address)
        self.set_param('fixed_ips', fixed_ips, iff=fixed_ips)
        self.set_param('security_groups', security_groups, iff=security_groups)
        data = dumps(json_data) if json_data else None
        self.post(path4url('ports'), data=data, **kwargs)

    def ports_put(
            self, port_id,
            json_data=None,
            name=None, mac_address=None, fixed_ips=None, security_groups=None,
            **kwargs):
        self.set_param('name', name, iff=name)
        self.set_param('mac_address', mac_address, iff=mac_address)
        self.set_param('fixed_ips', fixed_ips, iff=fixed_ips)
        self.set_param('security_groups', security_groups, iff=security_groups)
        data = dumps(json_data) if json_data else None
        self.put(path4url('ports', port_id), data=data, **kwargs)

    def ports_delete(self, port_id, **kwargs):
        return self.delete(path4url('ports', port_id), **kwargs)
