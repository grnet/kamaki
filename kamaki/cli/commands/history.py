#!/usr/bin/env python

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
# or implied, of GRNET S.A.

from kamaki.cli.command_tree import CommandTree
from kamaki.cli.argument import ValueArgument
from kamaki.cli.history import History
from kamaki.cli import command
from kamaki.cli.commands import _command_init, errors


history_cmds = CommandTree('history', 'Kamaki command history')
_commands = [history_cmds]


class _init_history(_command_init):
    @errors.generic.all
    @errors.history.init
    def _run(self):
        self.history = History(self.config.get('global', 'history_file'))

    def main(self):
        self._run()


@command(history_cmds)
class history_show(_init_history):
    """Show history
        Featutes:
        - slice notation (cmd numbers --> N or :N or N: or N1:N2)
        - text matching (--match)
    """

    arguments = dict(
        match=ValueArgument('Show lines matching this', '--match'),
    )

    @errors.generic.all
    def _run(self, cmd_slice):
        lines = ['%s.\t%s' % (i, l) for i, l in enumerate(self.history[:])][
            cmd_slice]
        if not isinstance(cmd_slice, slice):
            lines = [lines, ]
        if self['match']:
            lines = [l for l in lines if self._match(l, self['match'])]
        self.print_items([l[:-1] for l in lines])

    def main(self, cmd_numbers=''):
        super(self.__class__, self)._run()
        sl_args = [
            int(x) if x else None for x in cmd_numbers.split(':')] if (
                cmd_numbers) else [None, None]
        slice_cmds = slice(*sl_args) if len(sl_args) > 1 else sl_args[0]
        self._run(slice_cmds)


@command(history_cmds)
class history_clean(_init_history):
    """Clean up history (permanent)"""

    @errors.generic.all
    def _run(self):
        self.history.empty()

    def main(self):
        super(self.__class__, self)._run()
        self._run()
