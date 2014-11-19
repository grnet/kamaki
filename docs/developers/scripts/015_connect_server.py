# Copyright 2014 GRNET S.A. All rights reserved.
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

from kamaki.cli.config import Config
from kamaki.clients import astakos, cyclades, ClientError
from kamaki.clients.utils import https

https.patch_with_certs('/etc/ssl/certs/ca-certificates.crt')
cnf = Config()
CLOUD = cnf.get('global', 'default_cloud')
URL = cnf.get_cloud(CLOUD, 'url')
TOKEN = cnf.get_cloud(CLOUD, 'token')
identity_client = astakos.CachedAstakosClient(URL, TOKEN)

computeURL = identity_client.get_endpoint_url(
    cyclades.CycladesComputeClient.service_type)
compute_client = cyclades.CycladesComputeClient(computeURL, TOKEN)

srv = dict(id=613275, metadata=dict(USERS='root'), adminPass='some password')
srv['SNF:fqdn'] = 'snf-613275.example.com'

import json

vnc_console = compute_client.get_server_console(srv['id'])
print 'The following VNC credentials will be invalidated shortly'
print json.dumps(vnc_console, indent=2)
print 'VM credentials:\n\t', srv['metadata']['USERS'], '\n\t', srv['adminPass']

conn_info = dict(fqdn=srv['SNF:fqdn'], ipv4=[], ipv6=[])

nics = compute_client.get_server_nics(srv['id'])
for port in nics['attachments']:
    if port['ipv4']:
        conn_info['ipv4'].append(port['ipv4'])
    if port['ipv6']:
        conn_info['ipv6'].append(port['ipv6'])

print json.dumps(conn_info, indent=2)
