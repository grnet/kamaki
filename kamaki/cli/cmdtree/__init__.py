# Copyright 2012-2014 GRNET S.A. All rights reserved.
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


class Command(object):
    """Store a command and the next-level (2 levels)"""

    def __init__(
            self, path,
            help='', subcommands={}, cmd_class=None, long_help=''):
        assert path, 'Cannot initialize a command without a command path'
        self.path = path
        self.help = help or ''
        self.subcommands = dict(subcommands) if subcommands else {}
        self.cmd_class = cmd_class
        self.long_help = '%s' % (long_help or '')

    @property
    def name(self):
        if not getattr(self, '_name', None):
            self._name = self.path.split('_')[-1]
        return '%s' % self._name

    def add_subcmd(self, subcmd):
        if subcmd.path == '%s_%s' % (self.path, subcmd.name):
            self.subcommands[subcmd.name] = subcmd
            return True
        return False

    def get_subcmd(self, name):
        try:
            return self.subcommands[name]
        except KeyError:
            return None

    def contains(self, name):
        """Check if a name is a direct child of self"""
        return name in self.subcommands

    @property
    def is_command(self):
        return len(self.subcommands) == 0 if self.cmd_class else False

    @property
    def parent_path(self):
        try:
            return self.path[:self.path.rindex('_')]
        except ValueError:
            return ''

    def parse_out(self, args):
        """Find the deepest subcommand matching a series of terms
        but stop the first time a term doesn't match

        :param args: (list) terms to match commands against

        :returns: (parsed out command, the rest of the arguments)

        :raises TypeError: if args is not inalterable
        """
        cmd = self
        index = 0
        for term in args:
            try:
                cmd = cmd.subcommands[term]
            except KeyError:
                break
            index += 1
        return cmd, args[index:]

    def pretty_print(self, recursive=False):
        print('%s\t\t(Name: %s is_cmd: %s help: %s)' % (
            self.path, self.name, self.is_command, self.help))
        for cmd in self.subcommands.values():
            cmd.pretty_print(recursive)


class CommandTree(object):

    def __init__(self, name, description='', long_description=''):
        self.name = name
        self.description = description
        self.long_description = '%s' % (long_description or '')
        self.groups = dict()
        self._all_commands = dict()

    def exclude(self, groups_to_exclude=[]):
        for group in groups_to_exclude:
            self.groups.pop(group, None)

    def add_command(
            self, command_path,
            description=None, cmd_class=None, long_description=''):
        terms = command_path.split('_')
        try:
            cmd = self.groups[terms[0]]
        except KeyError:
            cmd = Command(terms[0])
            self.groups[terms[0]] = cmd
            self._all_commands[terms[0]] = cmd
        path = terms[0]
        for term in terms[1:]:
            path += '_' + term
            try:
                cmd = cmd.subcommands[term]
            except KeyError:
                new_cmd = Command(path)
                self._all_commands[path] = new_cmd
                cmd.add_subcmd(new_cmd)
                cmd = new_cmd
        cmd.cmd_class = cmd_class or None
        cmd.help = description or None
        cmd.long_help = long_description or cmd.long_help

    def find_best_match(self, terms):
        """Find a command that best matches a given list of terms

        :param terms: (list of str) match against paths in cmd_tree, e.g.,
            ['aa', 'bb', 'cc'] matches aa_bb_cc

        :returns: (Command, list) the matching command, the remaining terms or
            None
        """
        path = []
        for term in terms:
            check_path = path + [term]
            if '_'.join(check_path) not in self._all_commands:
                break
            path = check_path
        if path:
            return (self._all_commands['_'.join(path)], terms[len(path):])
        return (None, terms)

    def add_tree(self, new_tree):
        tname = new_tree.name
        tdesc = new_tree.description
        self.groups.update(new_tree.groups)
        self._all_commands.update(new_tree._all_commands)
        try:
            self._all_commands[tname].help = tdesc
        except KeyError:
            self.add_command(tname, tdesc)

    def has_command(self, path):
        return path in self._all_commands

    def get_command(self, path):
        return self._all_commands[path]

    def subnames(self, path=None):
        if path in (None, ''):
            return self.groups.keys()
        return self._all_commands[path].subcommands.keys()

    def get_subcommands(self, path=None):
        return self._all_commands[path].subcommands.values() if (
            path) else self.groups.values()

    def pretty_print(self, group=None):
        if group is None:
            for group in self.groups:
                self.pretty_print(group)
        else:
            self.groups[group].pretty_print(recursive=True)
