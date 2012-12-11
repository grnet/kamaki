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
from kamaki.clients.utils import path4url


class AstakosClient(Client):
    """GRNet Astakos API client"""

    def __init__(self, base_url, token):
        super(AstakosClient, self).__init__(base_url, token)

    def _is_email(self, a_str):
        if isinstance(a_str, str):
            username, sep, domain = a_str.partition('@')
            if username and domain:
                return True
        return False

    def authenticate(self, token=None):
        """
        :param token: (str) token to authenticate, if not given, read it from
            config object

        :returns: (dict) authentication information
        """
        if token:
            self.token = token
        r = self.get('/im/authenticate')
        return r.json

    def get_user_by_email(self, email, admin=False, token=None):
        """
        :param email: (str)

        :param token: (str) token to authenticate, if not given, read it from
            config object

        :returns: a json formatted dictionary containing information about a
            specific user

        :raises ClientError: (600) if not formated as email
        """
        if not self._is_email(email):
            raise ClientError('%s is not formated as email' % email, 600)
        if token:
            self.token = token
        self.set_param('email', email)

        path = path4url('im', 'admin' if admin else 'service', 'api/2.0/users')
        r = self.get(path)
        return r.json

    def get_user_by_username(self, username, admin=False, token=None):
        """
        :param username: (str)

        :param token: (str) token to authenticate, if not given, read it from
            config object

        :returns: a json formatted dictionary containing information about a
            specific user

        :raises ClientError: (600) if not formated as email
        """
        if token:
            self.token = token
        path = path4url('im', 'admin' if admin else 'service', 'api/2.0/users')
        r = self.get('%s/{%s}' % (path, username))
        return r.json
