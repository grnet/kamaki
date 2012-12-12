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
from kamaki.cli.argument import ArgumentParseManager
from kamaki.cli.history import History
from kamaki.cli import command
from kamaki.cli.commands import _command_init
from kamaki.cli import _exec_cmd, _print_error_message
from kamaki.cli.errors import CLIError, raiseCLIError
from kamaki.cli.utils import split_input
from kamaki.clients import ClientError


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
class history_load(_init_history):
    """Re-call a previously called command"""

    _cmd_tree = None

    def __init__(self, arguments={}, cmd_tree=None):
        super(self.__class__, self).__init__(arguments)
        self._cmd_tree = cmd_tree

    def _run_from_line(self, line):
        terms = split_input(line)
        cmd, args = self._cmd_tree.find_best_match(terms)
        if not cmd.is_command:
            return
        try:
            instance = cmd.get_class()(self.arguments)
            instance.config = self.config
            prs = ArgumentParseManager(cmd.path.split(),
                dict(instance.arguments))
            prs.syntax = '%s %s' % (cmd.path.replace('_', ' '),
                cmd.get_class().syntax)
            prs.parse(args)
            _exec_cmd(instance, prs.unparsed, prs.parser.print_help)
        except (CLIError, ClientError) as err:
            _print_error_message(err)
        except Exception as e:
            print('Execution of [ %s ] failed' % line)
            print('\t%s' % e)

    def _get_cmd_ids(self, cmd_ids):
        cmd_id_list = []
        for cmd_str in cmd_ids:
            num1, sep, num2 = cmd_str.partition('-')
            try:
                if sep:
                    for i in range(int(num1), int(num2) + 1):
                        cmd_id_list.append(i)
                else:
                    cmd_id_list.append(int(cmd_str))
            except ValueError:
                raiseCLIError('Invalid history id %s' % cmd_str)
        return cmd_id_list

    def main(self, *command_ids):
        super(self.__class__, self).main()
        cmd_list = self._get_cmd_ids(command_ids)
        for cmd_id in cmd_list:
            r = self.history.retrieve(cmd_id)
            print(r[:-1])
            if self._cmd_tree:
                r = r[len('kamaki '):-1] if r.startswith('kamaki ') else r[:-1]
                self._run_from_line(r)
