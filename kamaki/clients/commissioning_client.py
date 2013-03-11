# Copyright 2012 GRNET S.A. All rights reserved.
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

from kamaki.clients.commissioning import Callpoint, CallError
from kamaki.clients.commissioning.utils.debug import debug
from kamaki.clients import Client

from json import loads as json_loads, dumps as json_dumps


class CommissioningClient(Callpoint):

    def __init__(self, base_url, token, poolsize):
        super(CommissioningClient, self).__init__()
        self._kc = Client(base_url, token)
        self._kc.http_client.poolsize = poolsize

    def do_make_call(self, api_call, data):

        _kc = self._kc

        gettable = ['list', 'get', 'read']
        method = (_kc.get if any(api_call.startswith(x) for x in gettable)
                  else _kc.post)

        path = api_call
        json_data = json_dumps(data)
        debug("%s %s\n%s\n<<<\n", method.func_name, path, json_data)

        resp = method(path, data=json_data, success=(200, 450, 500))
        debug(">>>\nStatus: %s", resp.status_code)

        body = resp.text
        debug("\n%s\n<<<\n", body[:128] if body else None)

        status = int(resp.status_code)
        if status == 200:
            return json_loads(body)
        else:
            try:
                error = json_loads(body)
            except ValueError:
                exc = CallError(body, call_error='ValueError')
            else:
                exc = CallError.from_dict(error)
            raise exc
