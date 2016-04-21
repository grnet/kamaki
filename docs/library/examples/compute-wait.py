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
from kamaki.clients.cyclades import CycladesComputeClient

AUTHENTICATION_URL = "https://astakos.example.com/identity/v2.0"
TOKEN = "User-Token"
astakos = AstakosClient(AUTHENTICATION_URL, TOKEN)

service_type = CycladesComputeClient.service_type
endpoint = astakos.get_endpoint_url(service_type)
compute = CycladesComputeClient(endpoint, TOKEN)

#  Create a server (automatic IP)
name = "My public server"
flavor = "420"
image = "image-id-for-debian"
project = "a1234567-a890-1234-56ae-78f90bb1c2db"

server = compute.create_server(name, flavor, image, project=project)
print "Server status is {0}".server["status"]

new_status = compute.wait_server_until(server["id"], "ACTIVE")
if new_status != "ACTIVE":
    print "Waiting for server to build: time out..., server is in {0}".format(
        new_status)
else:
    #  Find ip
    nics = filter(lambda nic: bool(nic["ipv4"]), server["attachments"])
    ip = nics[0]["ipv4"]

    #  Create server
    print "Server {id} is now {status}\n\tName: {name}\n\tIP: {ip}".format(
        id=server["id"], status=server["status"], name=server["name"], ip=ip)
