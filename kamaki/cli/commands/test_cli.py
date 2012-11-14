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

from kamaki.cli import get_cmd_terms, command
from kamaki.cli.commands import _command_init
from kamaki.cli.command_tree import CommandTree
from kamaki.cli.argument import FlagArgument

sample_cmds = CommandTree(
    'sample',
    'Sample commands for developing your own')
test_cmds = CommandTree(
    'test',
    'Test commands for testing clients')
_commands = [sample_cmds, test_cmds]


print('Command Terms: ', get_cmd_terms())


class _test_init(_command_init):

    def main(self, *args, **kwargs):
        print(self.__class__)
        for v in args:
            print('\t\targ: %s' % v)
        for k, v in kwargs.items():
            print('\t\tkwarg: %s: %s' % (k, v))


@command(sample_cmds)
class sample_cmd0(_test_init):
    """ test cmd
    This is the zero command test and this is the long description of it
    """

    def main(self, mant):
        super(self.__class__, self).main(mant)


@command(sample_cmds)
class sample_cmd_all(_test_init):
    """test cmd all"""

    def main(self):
        super(self.__class__, self).main()


@command(sample_cmds)
class sample_cmd_some(_test_init):
    """test_cmd_some"""

    def main(self, opt='lala'):
        super(self.__class__, self).main(opt=opt)


@command(test_cmds)
class test_cmd0(_test_init):
    """ test cmd"""

    def main(self, mant):
        super(self.__class__, self).main(mant)


@command(test_cmds)
class test_cmd_all(_test_init):
    """test cmd all"""

    def __init__(self, arguments={}):
        super(self.__class__, self).__init__(arguments)
        self.arguments['testarg'] = FlagArgument('a test arg', '--test')

    def main(self):
        super(self.__class__, self).main()


@command(test_cmds)
class test_cmdion(_test_init):
    """test_cmd_some"""

    def main(self, opt='lala'):
        super(self.__class__, self).main(opt=opt)


@command(test_cmds)
class test_cmd_cmdion_comedian(_test_init):
    """test_cmd_some"""

    def main(self, opt='lala'):
        super(self.__class__, self).main(opt=opt)
