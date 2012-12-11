#!/usr/bin/env python

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

from kamaki.cli.command_tree import CommandTree
from kamaki.cli.argument import IntArgument, ValueArgument
from kamaki.cli.history import History
from kamaki.cli import command
from kamaki.cli.commands import _command_init


history_cmds = CommandTree('history', 'Command history')
_commands = [history_cmds]


class _init_history(_command_init):
    def main(self):
        self.history = History(self.config.get('history', 'file'))


@command(history_cmds)
class history_show(_init_history):
    """Show history [containing terms...]"""

    def __init__(self, arguments={}):
        super(self.__class__, self).__init__(arguments)
        self.arguments['limit'] =\
            IntArgument('number of lines to show', '-n', default=0)
        self.arguments['match'] =\
            ValueArgument('show lines that match all given terms', '--match')

    def main(self):
        super(self.__class__, self).main()
        ret = self.history.get(match_terms=self.get_argument('match'),
            limit=self.get_argument('limit'))
        print(''.join(ret))


@command(history_cmds)
class history_clean(_init_history):
    """Clean up history"""

    def main(self):
        super(self.__class__, self).main()
        self.history.clean()

@command(history_cmds)
class history_recall(_init_history):
    """Re-call a previously called command"""

    def main(self, commandid):
        super(self.__class__, self).main()
        r = self.history.retrieve(commandid)
        print(r)
