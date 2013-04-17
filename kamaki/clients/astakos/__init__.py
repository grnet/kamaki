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

from kamaki.clients import Client, ClientError


class AstakosClient(Client):
    """Synnefo Astakos API client"""

    def __init__(self, base_url, token):
        super(AstakosClient, self).__init__(base_url, token)
        self._cache = {}

    def authenticate(self, token=None):
        """Get authentication information and store it in this client
        As long as the AstakosClient instance is alive, the latest
        authentication information for this token will be available

        :param token: (str) custom token to authenticate

        :returns: (dict) authentication information
        """
        self.token = token or self.token
        self._cache[self.token] = self.get('/im/authenticate').json
        return self._cache[self.token]

    def list(self):
        """list cached user information"""
        r = []
        for k, v in self._cache.items():
            r.append(dict(v))
            r[-1].update(dict(auth_token=k))
        return r

    def info(self, token=None):
        """Get (cached) user information"""
        token_bu = self.token
        token = token or self.token
        try:
            r = self._cache[token]
        except KeyError:
            r = self.authenticate(token)
        self.token = token_bu
        return r

    def term(self, key, token=None):
        """Get (cached) term, from user credentials"""
        return self.info(token).get(key, None)
