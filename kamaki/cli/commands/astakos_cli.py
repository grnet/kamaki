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
from kamaki.clients.astakos import AstakosClient, ClientError
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
    """Authenticate a user
    Get user information (e.g. unique account name) from token
    Token should be set in settings:
    *  check if a token is set    /config get token
    *  permanently set a token    /config set token <token>
    Token can also be provided as a parameter
    """

    def main(self, custom_token=None):
        super(self.__class__, self).main()
        try:
            reply = self.client.authenticate(custom_token)
        except ClientError as ce:
            if (ce.status == 401):
                raiseCLIError(ce,
                    details=['See if token is set: /config get token',
                    'If not, set a token:',
                    '  1.(permanent):    /config set token <token>',
                    '  2.(temporary):    rerun with <token> parameter'])
            raiseCLIError(ce)
        except Exception as err:
            raiseCLIError(err)
        print_dict(reply)
