# Copyright 2012-2015 GRNET S.A. All rights reserved.
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

from kamaki.cli import exec_cmd, print_error_message, print_subcommands_help
from kamaki.cli.argument import ArgumentParseManager
from kamaki.cli.utils import print_dict, split_input, pref_enc
from kamaki.cli.history import History
from kamaki.cli.errors import CLIError
from kamaki.clients import ClientError
from kamaki.cli.logger import add_file_logger

log = add_file_logger(__name__)


def init_shell(exe_string, parser, username='', userid=''):
    parser.arguments.pop('version', None)
    shell = Shell()
    shell.set_prompt(exe_string)
    from kamaki import __version__ as version
    shell.greet(version, username, userid)
    shell.do_EOF = shell.do_exit
    from kamaki.cli.cmdtree import CommandTree
    shell.cmd_tree = CommandTree(
        'kamaki', 'A command line tool for poking clouds')
    return shell


class Shell(Cmd):
    """Kamaki interactive shell"""
    _prefix = '['
    _suffix = ']: '
    cmd_tree = None
    _history = None
    _context_stack = []
    _prompt_stack = []
    _parser = None
    astakos = None
    cloud = None

    undoc_header = 'interactive shell commands:'

    def emptyline(self):
        self.lastcmd = ''

    def postcmd(self, post, line):
        if self._context_stack:
            self._roll_command()
            self._restore(self._context_stack.pop())
            self.set_prompt(
                self._prompt_stack.pop()[len(self._prefix):-len(self._suffix)])

        return Cmd.postcmd(self, post, line)

    def precmd(self, line):
        if line.startswith('/'):
            start, end = len(self._prefix), -len(self._suffix)
            cur_cmd_path = self.prompt.replace(' ', '_')[start:end]
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

    def greet(self, version, username='', userid=''):
        print('kamaki v%s - Interactive Shell\n' % version)
        print('\t/exit     \tterminate kamaki')
        print('\texit or ^D\texit context')
        print('\t? or help \tavailable commands')
        print('\t?command  \thelp on command')
        print('\t!<command>\texecute OS shell command')
        print('')
        if username or userid:
            print('Session user is %s (uuid: %s)' % (username, userid))

    def set_prompt(self, new_prompt):
        self.prompt = '%s%s%s' % (self._prefix, new_prompt, self._suffix)

    def cmdloop(self):
        while True:
            try:
                Cmd.cmdloop(self)
            except KeyboardInterrupt:
                print(' - interrupted')
                continue
            break

    def do_exit(self, line):
        print('')
        start, end = len(self._prefix), -len(self._suffix)
        if self.prompt[start:end] == self.cmd_tree.name:
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
    def _register_method(cls, method, name):
        cls.__dict__[name] = method

    @classmethod
    def _unregister_method(cls, name):
        try:
            cls.__dict__.pop(name)
        except KeyError:
            pass

    def _roll_command(self, cmd_path=None):
        for subname in self.cmd_tree.subnames(cmd_path):
            self._unregister_method('do_%s' % subname)
            self._unregister_method('complete_%s' % subname)
            self._unregister_method('help_%s' % subname)

    @classmethod
    def _backup(cls):
        return dict(cls.__dict__)

    @classmethod
    def _restore(cls, oldcontext):
        cls.__dict__ = oldcontext

    @staticmethod
    def _create_help_method(cmd_name, args, required, descr, syntax):
        tmp_args = dict(args)
        tmp_args.pop('cloud', None)
        tmp_args.pop('debug', None)
        tmp_args.pop('verbose', None)
        tmp_args.pop('verbose_with_data', None)
        tmp_args.pop('config', None)
        tmp_args.pop('ignore_ssl', None)
        tmp_args.pop('ca_file', None)
        help_parser = ArgumentParseManager(
            cmd_name, tmp_args, required,
            syntax=syntax, description=descr, check_required=False)
        return help_parser.print_help

    def _register_command(self, cmd_path):
        cmd = self.cmd_tree.get_command(cmd_path)
        arguments = self._parser.arguments

        def do_method(new_context, line):
            """ Template for all cmd.Cmd methods of the form do_<cmd name>
                Parse cmd + args and decide to execute or change context
                <cmd> <term> <term> <args> is always parsed to most specific
                even if cmd_term_term is not a terminal path
            """
            line = line.decode(pref_enc)
            subcmd, cmd_args = cmd.parse_out(split_input(line))
            self._history.add(' '.join([cmd.path.replace('_', ' '), line]))
            cmd_parser = ArgumentParseManager(
                cmd.name, dict(self._parser.arguments))
            cmd_parser.parser.description = subcmd.help

            # exec command or change context
            if subcmd.is_command:  # exec command
                try:
                    cls = subcmd.cmd_class
                    cmd_parser.required = getattr(cls, 'required', None)
                    ldescr = getattr(cls, 'long_description', '')
                    if subcmd.path == 'history_run':
                        instance = cls(
                            dict(cmd_parser.arguments), self.astakos,
                            cmd_tree=self.cmd_tree)
                    else:
                        instance = cls(
                            dict(cmd_parser.arguments),
                            self.astakos, self.cloud)
                    cmd_parser.update_arguments(instance.arguments)
                    cmd_parser.arguments = instance.arguments
                    subpath = subcmd.path.split('_')[
                        (len(cmd.path.split('_')) - 1):]
                    cmd_parser.syntax = '%s %s' % (
                        ' '.join(subpath), instance.syntax)
                    help_method = self._create_help_method(
                        cmd.name, cmd_parser.arguments,
                        cmd_parser.required, subcmd.help, cmd_parser.syntax)
                    if '-h' in cmd_args or '--help' in cmd_args:
                        help_method()
                        if ldescr.strip():
                            print('\nDetails:')
                            print('%s' % ldescr)
                        return
                    cmd_parser.parse(cmd_args)

                    for name, arg in instance.arguments.items():
                        arg.value = getattr(
                            cmd_parser.parsed, name, arg.default)

                    exec_cmd(instance, cmd_parser.unparsed, help_method)
                except (ClientError, CLIError) as err:
                    print_error_message(err)
            elif ('-h' in cmd_args or '--help' in cmd_args) or len(cmd_args):
                # print options
                print('%s' % cmd.help)
                print_subcommands_help(cmd)
            else:  # change context
                backup_context = self._backup()
                old_prompt = self.prompt
                new_context._roll_command(cmd.parent_path)
                new_context.set_prompt(subcmd.path.replace('_', ' '))
                newcmds = [scmd for scmd in subcmd.subcommands.values()]
                for scmd in newcmds:
                    new_context._register_command(scmd.path)
                new_context.cmdloop()
                self.prompt = old_prompt
                # when new context is over, roll back to the old one
                self._restore(backup_context)
        self._register_method(do_method, 'do_%s' % cmd.name)

        def help_method(self):
            print('%s (%s -h for more options)' % (cmd.help, cmd.name))
            if cmd.is_command:
                cls = cmd.cmd_class
                ldescr = getattr(cls, 'long_description', '')
                plist = self.prompt[len(self._prefix):-len(self._suffix)]
                plist = plist.split(' ')
                clist = cmd.path.split('_')
                upto = 0
                if ldescr:
                    print('%s' % ldescr)
                for i, term in enumerate(plist):
                    try:
                        if clist[i] == term:
                            upto += 1
                    except IndexError:
                        break
                print('Syntax: %s %s' % (' '.join(clist[upto:]), cls.syntax))
            if cmd.subcommands:
                print_subcommands_help(cmd)

        self._register_method(help_method, 'help_%s' % cmd.name)

        def complete_method(self, text, line, begidx, endidx):
            subcmd, cmd_args = cmd.parse_out(split_input(line)[1:])
            if subcmd.is_command:
                cls = subcmd.cmd_class
                instance = cls(dict(arguments))
                empty, sep, subname = subcmd.path.partition(cmd.path)
                cmd_name = '%s %s' % (cmd.name, subname.replace('_', ' '))
                print('\n%s\nSyntax:\t%s %s' % (
                    cls.help, cmd_name, cls.syntax))
                cmd_args = {}
                for arg in instance.arguments.values():
                    cmd_args[','.join(arg.parsed_name)] = arg.help
                print_dict(cmd_args, indent=2)
                stdout.write('%s %s' % (self.prompt, line))
            return subcmd.subnames()
        self._register_method(complete_method, 'complete_%s' % cmd.name)

    @property
    def doc_header(self):
        tmp_partition = self.prompt.partition(self._prefix)
        tmp_partition = tmp_partition[2].partition(self._suffix)
        hdr = tmp_partition[0].strip()
        return '%s commands:' % hdr

    def run(self, astakos, cloud, parser, path=''):
        self.astakos = astakos
        self.cloud = cloud
        self._parser = parser
        cnf = parser.arguments['config']
        self._history = History(cnf.get('global', 'history_file'))
        self._history.limit = cnf.get('global', 'history_limit')
        if path:
            cmd = self.cmd_tree.get_command(path)
            intro = cmd.path.replace('_', ' ')
        else:
            intro = self.cmd_tree.name

        acceptable = parser.arguments['config'].groups
        total = self.cmd_tree.groups.keys()
        self.cmd_tree.exclude(set(total).difference(acceptable))

        for subcmd in self.cmd_tree.get_subcommands(path):
            self._register_command(subcmd.path)

        self.set_prompt(intro)

        try:
            self.cmdloop()
        except Exception as e:
            print('(%s)' % e)
            from traceback import print_stack
            print_stack()
