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
<<<<<<< HEAD
from kamaki.cli.utils import print_dict, print_items
from kamaki.cli.errors import raiseCLIError, CLISyntaxError
from kamaki.cli.commands import _command_init
=======
from kamaki.cli.utils import print_dict
from kamaki.cli.commands import _command_init, errors
>>>>>>> develop
from kamaki.cli.command_tree import CommandTree
from kamaki.cli.argument import ValueArgument

astakos_cmds = CommandTree('astakos', 'Astakos API commands')
_commands = [astakos_cmds]


class _astakos_init(_command_init):

    @errors.generic.all
    @errors.astakos.load
    def _run(self):
        token = self.config.get('astakos', 'token')\
            or self.config.get('global', 'token')
        base_url = self.config.get('astakos', 'url')\
            or self.config.get('global', 'url')
        self.client = AstakosClient(base_url=base_url, token=token)

    def main(self):
        self._run


@command(astakos_cmds)
class astakos_authenticate(_astakos_init):
<<<<<<< HEAD
    """Authenticate a user, show user information"""

    def main(self, token=None):
        super(self.__class__, self).main()
        try:
            reply = self.client.authenticate(token)
        except Exception as err:
            raiseCLIError(err)
        print_dict(reply)


@command(astakos_cmds)
class astakos_admin_userinfo(_astakos_init):
    """Get user info, provided you have admin privileges"""

    def __init__(self, arguments={}):
        super(self.__class__, self).__init__(arguments)
        self.arguments['email'] = ValueArgument('target user email', '--email')
        self.arguments['username'] = ValueArgument('target username',
            '--username')

    def main(self, admin_token=None):
        super(self.__class__, self).main()
        email = self.get_argument('email')
        username = self.get_argument('username')
        try:
            if email and username:
                raise CLISyntaxError(
                    'Arguments %s and %s are mutually exclusive' % (
                        self.arguments['email'].parsed_name,
                        self.arguments['username'].parsed_name
                        ), importance=1)
            elif email:
                reply = self.client.get_user_by_email(email,
                    admin=True,
                    token=admin_token)
            elif username:
                reply = self.client.get_user_by_username(username,
                    admin=True,
                    token=admin_token)
            else:
                raise CLISyntaxError(
                    'Exactly one of %s or %s is obligatory' % (
                        self.arguments['email'].parsed_name,
                        self.arguments['username'].parsed_name
                        ), importance=1)
        except Exception as err:
            raiseCLIError(err)
        print_dict(reply)


@command(astakos_cmds)
class astakos_service_userinfo(_astakos_init):
    """Get user info with service token"""

    def __init__(self, arguments={}):
        super(self.__class__, self).__init__(arguments)
        self.arguments['email'] = ValueArgument('target user email', '--email')
        self.arguments['username'] = ValueArgument('target username',
            '--username')

    def main(self, service_token=None):
        super(self.__class__, self).main()
        email = self.get_argument('email')
        username = self.get_argument('username')
        try:
            if email and username:
                raise CLISyntaxError(
                    'Arguments %s and %s are mutually exclusive' % (
                        self.arguments['email'].parsed_name,
                        self.arguments['username'].parsed_name
                        ), importance=1)
            elif email:
                reply = self.client.get_user_by_email(email,
                    token=service_token)
            elif username:
                reply = self.client.get_user_by_username(username,
                    token=service_token)
            else:
                raise CLISyntaxError(
                    'Exactly one of %s or %s is obligatory' % (
                        self.arguments['email'].parsed_name,
                        self.arguments['username'].parsed_name
                        ), importance=1)
        except Exception as err:
            raiseCLIError(err)
        print_dict(reply)


@command(astakos_cmds)
class astakos_service_list(_astakos_init):
    """List cloud services associated with astakos"""

    def main(self, token=None):
        super(self.__class__, self).main()
        reply = self.client.list_services(token)
        print_items(reply)
=======
    """Authenticate a user
    Get user information (e.g. unique account name) from token
    Token should be set in settings:
    *  check if a token is set    /config get token
    *  permanently set a token    /config set token <token>
    Token can also be provided as a parameter
    """

    @errors.generic.all
    @errors.astakos.authenticate
    def _run(self, custom_token=None):
        super(self.__class__, self)._run()
        reply = self.client.authenticate(custom_token)
        print_dict(reply)

    def main(self, custom_token=None):
        self._run(custom_token)
>>>>>>> develop
