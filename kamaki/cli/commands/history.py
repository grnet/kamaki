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
from kamaki.cli.argument import IntArgument, ValueArgument
from kamaki.cli.argument import ArgumentParseManager
from kamaki.cli.history import History
from kamaki.cli import command
from kamaki.cli.commands import _command_init, errors
from kamaki.cli import exec_cmd, print_error_message
from kamaki.cli.errors import CLIError, raiseCLIError
from kamaki.cli.utils import split_input
from kamaki.clients import ClientError


history_cmds = CommandTree('history', 'Kamaki command history')
_commands = [history_cmds]


def _get_num_list(num_str):
    if num_str.startswith('-'):
        num1, sep, num2 = num_str[1:].partition('-')
        num1 = '-%s' % num1
    else:
        num1, sep, num2 = num_str.partition('-')
    (num1, num2) = (num1.strip(), num2.strip())
    try:
        num1 = (-int(num1[1:])) if num1.startswith('-') else int(num1)
    except ValueError as e:
        raiseCLIError(e, 'Invalid id %s' % num1)
    if sep:
        try:
            num2 = (-int(num2[1:])) if num2.startswith('-') else int(num2)
            num2 += 1 if num2 > 0 else 0
        except ValueError as e:
            raiseCLIError(e, 'Invalid id %s' % num2)
    else:
        num2 = (1 + num1) if num1 else 0
    return [i for i in range(num1, num2)]


class _init_history(_command_init):
    @errors.generic.all
    @errors.history.init
    def _run(self):
        self.history = History(self.config.get('global', 'history_file'))

    def main(self):
        self._run()


@command(history_cmds)
class history_show(_init_history):
    """Show intersession command history
    ---
    - With no parameters : pick all commands in history records
    - With:
    .   1.  <order-id> : pick the <order-id>th command
    .   2.  <order-id-1>-<order-id-2> : pick all commands ordered in the range
    .       [<order-id-1> - <order-id-2>]
    .   - the above can be mixed and repeated freely, separated by spaces
    .       e.g., pick 2 4-7 -3
    .   - Use negative integers to count from the end of the list, e.g.,:
    .       -2 means : the command before the last one
    .       -2-5 means : last 2 commands + the first 5
    .       -5--2 means : the last 5 commands except the last 2
    """

    arguments = dict(
        limit=IntArgument(
            'number of lines to show',
            ('-n', '--numner'),
            default=0),
        match=ValueArgument('show lines that match given terms', '--match')
    )

    @errors.generic.all
    def _run(self, *cmd_ids):
        ret = self.history.get(match_terms=self['match'], limit=self['limit'])

        if not cmd_ids:
            self.print_list(ret)
            return

        num_list = []
        for num_str in cmd_ids:
            num_list += _get_num_list(num_str)

        for cmd_id in num_list:
            try:
                cur_id = int(cmd_id)
                if cur_id:
                    self.writeln(ret[cur_id - (1 if cur_id > 0 else 0)][:-1])
            except IndexError as e2:
                raiseCLIError(e2, 'Command id out of 1-%s range' % len(ret))

    def main(self, *cmd_ids):
        super(self.__class__, self)._run()
        self._run(*cmd_ids)


@command(history_cmds)
class history_clean(_init_history):
    """Clean up history (permanent)"""

    @errors.generic.all
    def _run(self):
        self.history.clean()

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(history_cmds)
class history_run(_init_history):
    """Run previously executed command(s)
    Use with:
    .   1.  <order-id> : pick the <order-id>th command
    .   2.  <order-id-1>-<order-id-2> : pick all commands ordered in the range
    .       [<order-id-1> - <order-id-2>]
    .   - Use negative integers to count from the end of the list, e.g.,:
    .       -2 means : the command before the last one
    .       -2-5 means : last 2 commands + the first 5
    .       -5--2 mean
    .   - to find order ids for commands try   /history show.
    """

    _cmd_tree = None

    def __init__(self, arguments={}, auth_base=None, cmd_tree=None):
        super(self.__class__, self).__init__(arguments, auth_base=auth_base)
        self._cmd_tree = cmd_tree

    @errors.generic.all
    def _run_from_line(self, line):
        terms = split_input(line)
        cmd, args = self._cmd_tree.find_best_match(terms)
        if cmd.is_command:
            try:
                instance = cmd.cmd_class(
                    self.arguments, auth_base=getattr(self, 'auth_base', None))
                instance.config = self.config
                prs = ArgumentParseManager(
                    cmd.path.split(), dict(instance.arguments))
                prs.syntax = '%s %s' % (
                    cmd.path.replace('_', ' '), cmd.cmd_class.syntax)
                prs.parse(args)
                exec_cmd(instance, prs.unparsed, prs.parser.print_help)
            except (CLIError, ClientError) as err:
                print_error_message(err, self._err)
            except Exception as e:
                self.error('Execution of [ %s ] failed\n\t%s' % (line, e))

    @errors.generic.all
    @errors.history._get_cmd_ids
    def _get_cmd_ids(self, cmd_ids):
        cmd_id_list = []
        for cmd_str in cmd_ids:
            cmd_id_list += _get_num_list(cmd_str)
        return cmd_id_list

    @errors.generic.all
    def _run(self, *command_ids):
        cmd_list = self._get_cmd_ids(command_ids)
        for cmd_id in cmd_list:
            r = self.history.retrieve(cmd_id)
            try:
                self.writeln('< %s >' % r[:-1])
            except (TypeError, KeyError):
                continue
            if self._cmd_tree:
                r = r[len('kamaki '):-1] if r.startswith('kamaki ') else r[:-1]
                self._run_from_line(r)

    def main(self, *command_ids):
        super(self.__class__, self)._run()
        self._run(*command_ids)
