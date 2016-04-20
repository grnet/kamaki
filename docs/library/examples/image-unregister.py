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
from kamaki.clients.pithos import PithosClient
from kamaki.clients.image import ImageClient

AUTHENTICATION_URL = "https://astakos.example.com/identity/v2.0"
TOKEN = "User-Token"
astakos = AstakosClient(AUTHENTICATION_URL, TOKEN)
user = astakos.authenticate()
uuid = user["access"]["user"]["id"]

service_type = PithosClient.service_type
endpoint = astakos.get_endpoint_url(service_type)
pithos = PithosClient(endpoint, TOKEN)
pithos.account = uuid

service_type = ImageClient.service_type
endpoint = astakos.get_endpoint_url(service_type)
image = ImageClient(endpoint, TOKEN)

#  Find the image by id
image_id = "my-image-id"
my_image = image.get_meta(image_id)

#  Check if it is my image
if my_image["owner"] == uuid:
    image.unregister(image_id)

    #  Delete the image files
    pithos.container = "images"
    separator = "{uuid}/{container}/".format(
        uuid=uuid, container=pithos.container)
    _, location = my_image["location"].split(separator)
    meta_object = "{0}.meta".format(location)

    pithos.del_object(location)
    pithos.del_object(meta_object)
else:
    print "This image wasn't registered by me"
