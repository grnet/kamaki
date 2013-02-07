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
    """GRNet Astakos API client"""

    _cache = {}

    def __init__(self, base_url, token):
        super(AstakosClient, self).__init__(base_url, token)

    def authenticate(self, token=None):
        """
        :param token: (str) custom token to authenticate

        :returns: (dict) authentication information
        """
        self.token = token or self.token
        self._cache[token] = self.get('/im/authenticate')
        return self._cache[token].json

    def _user_info(self, token=None):
        token = token or self.token
        try:
            return self._cache[token]
        except KeyError:
            return self.authenticate(token)

    def uuid(self, token=None):
        return self._user_info(token)['uuid'].strip()

    def name(self, token=None):
        return self._user_info(token)['name'].strip()

    def username(self, token=None):
        return self._user_info(token)['username'].strip()

    def token_created(self, token=None):
        return self._user_info(token)['auth_token_created'].strip()

    def token_expires(self, token=None):
        return self._user_info(token)['auth_token_expires'].strip()

    def email(self, token=None):
        return self._user_info(token)['email'].strip()

    def id(self, token=None):
        """Internal reference for Astakos objects (not a unique user id)
        For a unique identifier use uuid
        """
        return self._user_info(token)['id'].strip()
