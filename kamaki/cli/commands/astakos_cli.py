# Copyright 2011-2012 GRNET S.A. All rights reserved.
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
# or implied, of GRNET S.A.command

from kamaki.cli import command
from kamaki.clients.astakos import AstakosClient
from kamaki.cli.utils import print_dict
from kamaki.cli.errors import raiseCLIError
from kamaki.cli.commands import _command_init
from kamaki.cli.command_tree import CommandTree

astakos_cmds = CommandTree('astakos', 'Astakos API commands')
_commands = [astakos_cmds]


class _astakos_init(_command_init):
    def main(self):
        token = self.config.get('astakos', 'token')\
            or self.config.get('global', 'token')
        base_url = self.config.get('astakos', 'url')\
            or self.config.get('global', 'url')
        if base_url is None:
            raiseCLIError(None, 'Missing astakos server URL')
        self.client = AstakosClient(base_url=base_url, token=token)


@command(astakos_cmds)
class astakos_authenticate(_astakos_init):
    """Authenticate a user, show user information"""

    def main(self, token=None):
        super(self.__class__, self).main()
        try:
            reply = self.client.authenticate(token)
        except Exception as err:
            raiseCLIError(err)
        print_dict(reply)


@command(astakos_cmds)
class astakos_user_byemail(_astakos_init):
    """Get user by e-mail"""

    def main(self, email, token=None):
        super(self.__class__, self).main()
        try:
            reply = self.client.get_user_by_email(email, token)
        except Exception as err:
            raiseCLIError(err)
        print_dict(reply)


@command(astakos_cmds)
class astakos_user_byusername(_astakos_init):
    """Get user by e-mail"""

    def main(self, username, token=None):
        super(self.__class__, self).main()
        try:
            reply = self.client.get_user_by_username(username, token)
        except Exception as err:
            raiseCLIError(err)
        print_dict(reply)
