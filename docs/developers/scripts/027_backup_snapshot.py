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
from kamaki.clients import astakos, cyclades, ClientError, pithos, image
from kamaki.clients.utils import https

https.patch_with_certs('/etc/ssl/certs/ca-certificates.crt')
cnf = Config()
CLOUD = cnf.get('global', 'default_cloud')
URL = cnf.get_cloud(CLOUD, 'url')
TOKEN = cnf.get_cloud(CLOUD, 'token')
identity_client = astakos.CachedAstakosClient(URL, TOKEN)

pithosURL = identity_client.get_endpoint_url(pithos.PithosClient.service_type)
storage_client = pithos.PithosClient(pithosURL, TOKEN)
storage_client.account = identity_client.user_info()['id']
storage_client.container = 'pithos'

imageURL = identity_client.get_endpoint_url(image.ImageClient.service_type)
image_client = image.ImageClient(imageURL, TOKEN)

computeURL = identity_client.get_endpoint_url(
    cyclades.CycladesComputeClient.service_type)
compute_client = cyclades.CycladesComputeClient(computeURL, TOKEN)

volumeURL = identity_client.get_endpoint_url(
    cyclades.CycladesBlockStorageClient.service_type)
volume_client = cyclades.CycladesBlockStorageClient(volumeURL, TOKEN)

srv = compute_client.get_server_details(478999)

new_snapshot = volume_client.create_snapshot(srv['volumes'][0], 'new.snapshot')

from time import sleep
print 'wait 10...'
sleep(10)

compute_client.create_server(
    name='Reserve', image_id=new_snapshot['id'], flavor_id=srv['flavor']['id'])

obj = new_snapshot['display_name']
storage_client.container = 'snapshots'
with open(obj, 'w+') as f:
    storage_client.download_object(obj, f)

with open(obj, 'r') as f:
    storage_client.upload_object(obj, f)

location = (storage_client.account, storage_client.container, obj)
props = dict(exclude_all_taks=True)
snp = image_client.register('Restored snapshot', location, properties=props)

compute_client.create_server(
    name='Reserve', image_id=snp['id'], flavor_id=srv['flavor']['id'])
