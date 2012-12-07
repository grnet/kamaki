# Copyright 2012-2013 GRNET S.A. All rights reserved.
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
from kamaki.cli.commands import _command_init
from kamaki.cli.command_tree import CommandTree
from kamaki.clients import tests

test_cmds = CommandTree('test', 'Unitest clients')
_commands = [test_cmds]


#print('Command Terms: ', get_cmd_terms())


class _test_init(_command_init):

    def main(self, client, method=None):
        tests.cnf = self.config
        if method:
            tests.main([client, method])
        else:
            tests.main([client])


@command(test_cmds)
class test_error(_test_init):
    """Create an error message with optional message"""

    def main(self, errmsg='', importance=0, index=0):
        from kamaki.cli.errors import raiseCLIError
        l = [1, 2]
        try:
            l[int(index)]
        except Exception as err:
            raiseCLIError(err, errmsg, importance)
        raiseCLIError(None, errmsg, importance)


@command(test_cmds)
class test_args(_test_init):
    """Test how arguments are treated by kamaki"""

    def main(self, *args):
        print(args)


@command(test_cmds)
class test_all(_test_init):
    """test all clients"""

    def main(self):
        for client in ('pithos', 'cyclades', 'image', 'astakos'):
            super(self.__class__, self).main(client)


@command(test_cmds)
class test_pithos(_test_init):
    """ test Pithos client"""

    def main(self, method=None):
        super(self.__class__, self).main('pithos', method)


@command(test_cmds)
class test_cyclades(_test_init):
    """ test Cyclades client"""

    def main(self, method=None):
        super(self.__class__, self).main('cyclades', method)


@command(test_cmds)
class test_image(_test_init):
    """ test Image client"""

    def main(self, method=None):
        super(self.__class__, self).main('image', method)


@command(test_cmds)
class test_astakos(_test_init):
    """ test Astakos client"""

    def main(self, method=None):
        super(self.__class__, self).main('astakos', method)
