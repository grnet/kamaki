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
    CycladesBlockStorageClient, CycladesComputeClient)

#  Initialize Astakos
AUTHENTICATION_URL = "https://astakos.example.com/identity/v2.0"
TOKEN = "User-Token"
astakos = AstakosClient(AUTHENTICATION_URL, TOKEN)

#  Initialize CycladesComputeClient
service_type = CycladesComputeClient.service_type
endpoint = astakos.get_endpoint_url(service_type)
compute = CycladesComputeClient(endpoint, TOKEN)

#  Servers
server_id_1, server_id_2 = "id-for-sever-1", "id-for-sever-2"

#  Initialize CycladesBlockStorageClient
service_type = CycladesBlockStorageClient.service_type
endpoint = astakos.get_endpoint_url(service_type)
blockstorage = CycladesBlockStorageClient(endpoint, TOKEN)

#  Create new volume on server_1
size_ = 20  # in GB
name = "USB stick"
usb = blockstorage.create_volume(size_, name, server_id=server_id_1)
blockstorage.wait_volume_until(usb["id"], "in_use")

#  Unplug and plug to the other server
compute.detach_volume(server_id_1, usb["id"])
blockstorage.wait_volume_while(usb["id"], "in_use")

compute.attach_volume(server_id_2, usb["id"])
blockstorage.wait_volume_until(usb["id"], "in_use")
