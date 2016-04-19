# Copyright 2011-2015 GRNET S.A. All rights reserved.
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
from kamaki.clients.pithos import PithosClient

AUTHENTICATION_URL = "https://astakos.example.com/identity/v2.0"
TOKEN = "User-Token"
astakos = AstakosClient(AUTHENTICATION_URL, TOKEN)

#  Our data
container_name = "course_container"
user = astakos.authenticate()
uuid = user["access"]["user"]["id"]

#  Initialize a Pithos client
service_type = PithosClient.service_type
endpoint = astakos.get_endpoint_url(service_type)
pithos = PithosClient(endpoint, TOKEN, uuid, container_name)

#  To what project is this container assigned to?
container = pithos.get_container_info(container_name)
container_project = container["x-container-policy-project"]

#  Get quota info
quotas = astakos.get_quotas()
container_quotas = quotas[container_project]["pithos.diskspace"]
usage, limit = container_quotas["usage"], container_quotas["limit"]

if usage < limit:
    print "Quotas for container {0} are OK".format(container_name)
else:
    #  We need to reassign to another project
    new_project = "a9f87654-3af2-1e09-8765-43a2df1098765"
    pithos.reassign_container(project_id=new_project)
    print "Container {name} is reassigned to project {id}".format(
        name=container_name, id=new_project)
