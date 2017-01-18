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

#  Initialize Astakos
AUTHENTICATION_URL = "https://astakos.example.com/identity/v2.0"
TOKEN = "User-Token"
astakos = AstakosClient(AUTHENTICATION_URL, TOKEN)

#  Initialize CycladesComputeClient
service_type = CycladesComputeClient.service_type
endpoint = astakos.get_endpoint_url(service_type)
compute = CycladesComputeClient(endpoint, TOKEN)

#  Get server current status
server_id = "my-server-id"
server = compute.get_server_details(server_id)
status = server["status"]

#  Shutdown server
if status == "ACTIVE":
    compute.server_reboot(server_id)
elif status == "STOPPED":
    compute.server_start(server_id)

new_status = compute.wait_sever_while(server_id, "REBOOT")
print "Server {id} is now {status}".format(id=server_id, status=new_status)
