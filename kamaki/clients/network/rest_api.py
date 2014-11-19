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

from kamaki.clients import Client
from kamaki.clients.utils import path4url


class NetworkRestClient(Client):
    service_type = 'network'

    def networks_get(self, network_id=None, **kwargs):
        if network_id:
            return self.get(path4url('networks', network_id), **kwargs)
        return self.get(path4url('networks'), **kwargs)

    def networks_post(self, json_data, **kwargs):
        return self.post(path4url('networks'), json=json_data, **kwargs)

    def networks_put(self, network_id, json_data, **kwargs):
        return self.put(
            path4url('networks', network_id), json=json_data, **kwargs)

    def networks_delete(self, network_id, **kwargs):
        return self.delete(path4url('networks', network_id), **kwargs)

    def subnets_get(self, subnet_id=None, **kwargs):
        if subnet_id:
            return self.get(path4url('subnets', subnet_id), **kwargs)
        return self.get(path4url('subnets'), **kwargs)

    def subnets_post(self, json_data, **kwargs):
        return self.post(path4url('subnets'), json=json_data, **kwargs)

    def subnets_put(self, subnet_id, **kwargs):
        return self.put(path4url('subnets', subnet_id), **kwargs)

    def subnets_delete(self, subnet_id, **kwargs):
        return self.delete(path4url('subnets', subnet_id), **kwargs)

    def ports_get(self, port_id=None, **kwargs):
        if port_id:
            return self.get(path4url('ports', port_id), **kwargs)
        return self.get(path4url('ports'), **kwargs)

    def ports_post(self, json_data=None, **kwargs):
        return self.post(path4url('ports'), json=json_data, **kwargs)

    def ports_put(self, port_id, json_data=None, **kwargs):
        return self.put(path4url('ports', port_id), json=json_data, **kwargs)

    def ports_delete(self, port_id, **kwargs):
        return self.delete(path4url('ports', port_id), **kwargs)

    #  floatingips (L3) extentions

    def floatingips_get(self, floatingip_id=None, **kwargs):
        return self.get(path4url('floatingips', floatingip_id or ''), **kwargs)

    def floatingips_post(self, json_data, **kwargs):
        return self.post(path4url('floatingips'), json=json_data, **kwargs)

    def floatingips_put(self, floatingip_id, json_data, **kwargs):
        return self.put(
            path4url('floatingips', floatingip_id), json=json_data, **kwargs)

    def floatingips_delete(self, floatingip_id, **kwargs):
        return self.delete(path4url('floatingips', floatingip_id), **kwargs)
