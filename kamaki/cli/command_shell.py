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

from cmd import Cmd
from os import popen
from sys import stdout
from argparse import ArgumentParser

from kamaki.cli import _exec_cmd, _print_error_message
from kamaki.cli.argument import _arguments, update_arguments
from kamaki.cli.utils import print_dict
from kamaki.cli.history import History
from kamaki.cli.errors import CLIError


def _init_shell(exe_string, arguments):
    arguments.pop('version', None)
    arguments.pop('options', None)
    arguments.pop('history', None)
    shell = Shell()
    shell.set_prompt(exe_string)
    from kamaki import __version__ as version
    shell.greet(version)
    shell.do_EOF = shell.do_exit
    from kamaki.cli.command_tree import CommandTree
    shell.cmd_tree = CommandTree(
        'kamaki', 'A command line tool for poking clouds')
    return shell


class Shell(Cmd):
    """Kamaki interactive shell"""
    _prefix = '['
    _suffix = ']:'
    cmd_tree = None
    _history = None
    _arguments = None
    _context_stack = []
    _prompt_stack = []

    undoc_header = 'interactive shell commands:'

    def postcmd(self, post, line):
        if self._context_stack:
            self._roll_command()
            self._restore(self._context_stack.pop())
            self.set_prompt(self._prompt_stack.pop()[1:-2])

        return Cmd.postcmd(self, post, line)

    def precmd(self, line):
        if line.startswith('/'):
            cur_cmd_path = self.prompt.replace(' ', '_')[1:-2]
            if cur_cmd_path != self.cmd_tree.name:
                cur_cmd = self.cmd_tree.get_command(cur_cmd_path)
                self._context_stack.append(self._backup())
                self._prompt_stack.append(self.prompt)
                new_context = self
                self._roll_command(cur_cmd.path)
                new_context.set_prompt(self.cmd_tree.name)
                for grp_cmd in self.cmd_tree.get_subcommands():
                    self._register_command(grp_cmd.path)
            return line[1:]
        return line

    def greet(self, version):
        print('kamaki v%s - Interactive Shell\n\t(exit or ^D to exit)\n'\
            % version)

    def set_prompt(self, new_prompt):
        self.prompt = '[%s]:' % new_prompt

    def do_exit(self, line):
        print('')
        if self.prompt[1:-2] == self.cmd_tree.name:
            exit(0)
        return True

    def do_shell(self, line):
        output = popen(line).read()
        print(output)

    @property
    def path(self):
        if self._cmd:
            return self._cmd.path
        return ''

    @classmethod
    def _register_method(self, method, name):
        self.__dict__[name] = method

    @classmethod
    def _unregister_method(self, name):
        try:
            self.__dict__.pop(name)
        except KeyError:
            pass

    def _roll_command(self, cmd_path=None):
        for subname in self.cmd_tree.get_subnames(cmd_path):
            self._unregister_method('do_%s' % subname)
            self._unregister_method('complete_%s' % subname)
            self._unregister_method('help_%s' % subname)

    @classmethod
    def _backup(self):
        return dict(self.__dict__)

    @classmethod
    def _restore(self, oldcontext):
        self.__dict__ = oldcontext

    def _register_command(self, cmd_path):
        cmd = self.cmd_tree.get_command(cmd_path)
        arguments = self._arguments

        def do_method(new_context, line):
            """ Template for all cmd.Cmd methods of the form do_<cmd name>
                Parse cmd + args and decide to execute or change context
                <cmd> <term> <term> <args> is always parsed to most specific
                even if cmd_term_term is not a terminal path
            """
            subcmd, cmd_args = cmd.parse_out(line.split())
            if self._history:
                self._history.add(' '.join([cmd.path.replace('_', ' '), line]))
            cmd_parser = ArgumentParser(cmd.name, add_help=False)
            cmd_parser.description = subcmd.help

            # exec command or change context
            if subcmd.is_command:  # exec command
                cls = subcmd.get_class()
                instance = cls(dict(arguments))
                cmd_parser.prog = '%s %s' % (cmd_parser.prog.replace('_', ' '),
                    cls.syntax)
                update_arguments(cmd_parser, instance.arguments)
                if '-h' in cmd_args or '--help' in cmd_args:
                    cmd_parser.print_help()
                    return
                parsed, unparsed = cmd_parser.parse_known_args(cmd_args)

                for name, arg in instance.arguments.items():
                    arg.value = getattr(parsed, name, arg.default)
                try:
                    _exec_cmd(instance, unparsed, cmd_parser.print_help)
                except CLIError as err:
                    _print_error_message(err)
            elif ('-h' in cmd_args or '--help' in cmd_args) \
            or len(cmd_args):  # print options
                print('%s: %s' % (cmd.name, subcmd.help))
                options = {}
                for sub in subcmd.get_subcommands():
                    options[sub.name] = sub.help
                print_dict(options)
            else:  # change context
                #new_context = this
                backup_context = self._backup()
                old_prompt = self.prompt
                new_context._roll_command(cmd.parent_path)
                new_context.set_prompt(subcmd.path.replace('_', ' '))
                newcmds = [subcmd for subcmd in subcmd.get_subcommands()]
                for subcmd in newcmds:
                    new_context._register_command(subcmd.path)
                new_context.cmdloop()
                self.prompt = old_prompt
                #when new context is over, roll back to the old one
                self._restore(backup_context)
        self._register_method(do_method, 'do_%s' % cmd.name)

        def help_method(self):
            print('%s (%s -h for more options)' % (cmd.help, cmd.name))
        self._register_method(help_method, 'help_%s' % cmd.name)

        def complete_method(self, text, line, begidx, endidx):
            subcmd, cmd_args = cmd.parse_out(line.split()[1:])
            if subcmd.is_command:
                cls = subcmd.get_class()
                instance = cls(dict(arguments))
                empty, sep, subname = subcmd.path.partition(cmd.path)
                cmd_name = '%s %s' % (cmd.name, subname.replace('_', ' '))
                print('\n%s\nSyntax:\t%s %s'\
                    % (cls.description, cmd_name, cls.syntax))
                cmd_args = {}
                for arg in instance.arguments.values():
                    cmd_args[','.join(arg.parsed_name)] = arg.help
                print_dict(cmd_args, ident=2)
                stdout.write('%s %s' % (self.prompt, line))
            return subcmd.get_subnames()
        self._register_method(complete_method, 'complete_%s' % cmd.name)

    @property
    def doc_header(self):
        tmp_partition = self.prompt.partition(self._prefix)
        tmp_partition = tmp_partition[2].partition(self._suffix)
        hdr = tmp_partition[0].strip()
        return '%s commands:' % hdr

    def run(self, arguments, path=''):
        self._history = History(arguments['config'].get('history', 'file'))
        self._arguments = arguments
        if path:
            cmd = self.cmd_tree.get_command(path)
            intro = cmd.path.replace('_', ' ')
        else:
            intro = self.cmd_tree.name

        for subcmd in self.cmd_tree.get_subcommands(path):
            self._register_command(subcmd.path)

        self.set_prompt(intro)

        self.cmdloop()
