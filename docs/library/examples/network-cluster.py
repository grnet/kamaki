# Copyright 2016 GRNET S.A. All rights reserved.
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

from kamaki.clients.astakos import AstakosClient
from kamaki.clients.cyclades import (
    CycladesComputeClient, CycladesNetworkClient)

AUTHENTICATION_URL = "https://astakos.example.com/identity/v2.0"
TOKEN = "User-Token"
astakos = AstakosClient(AUTHENTICATION_URL, TOKEN)

service_type = CycladesComputeClient.service_type
endpoint = astakos.get_endpoint_url(service_type)
compute = CycladesComputeClient(endpoint, TOKEN)

service_type = CycladesNetworkClient.service_type
endpoint = astakos.get_endpoint_url(service_type)
network = CycladesNetworkClient(endpoint, TOKEN)

#  Create VPN and reserve an IP
type_ = CycladesNetworkClient.types[0]
vpn = network.create_network(type_, name="Cluster Network")
unused_ips = filter(lambda ip: not ip["port_id"], network.list_floatingips())
ip = unused_ips[0] if unused_ips else network.create_floatingip()
ip_net = ip["floating_network_id"]

#  Server data
flavor = 420
image = "image-id-for-a-debian-image"

#  Create nodes
networks = [dict(uuid=vpn["id"]), ]
node_1 = compute.create_server("Node 1", flavor, image, networks=networks)
node_2 = compute.create_server("Node 2", flavor, image, networks=networks)

#  Create gateway
networks.append(dict(uuid=ip_net, fixed_ip=ip["floating_ip_address"]))
gateway = compute.create_server("Gateway", flavor, image, networks=networks)

#  Wait servers to get ready
compute.wait_server_until(node_1["id"], "ACTIVE")
compute.wait_server_until(node_2["id"], "ACTIVE")
compute.wait_server_until(gateway["id"], "ACTIVE")
