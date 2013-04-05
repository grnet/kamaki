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

from kamaki.clients import Client


class Command(object):
    """Store a command and the next-level (2 levels)"""
    _name = None
    path = None
    cmd_class = None
    subcommands = {}
    help = ' '

    def __init__(self, path, help=' ', subcommands={}, cmd_class=None):
        self.path = path
        self.help = help
        self.subcommands = dict(subcommands)
        self.cmd_class = cmd_class

    @property
    def name(self):
        if self._name is None:
            self._name = self.path.split('_')[-1]
        return str(self._name)

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
        return self.cmd_class is not None and len(self.subcommands) == 0

    @property
    def has_description(self):
        return len(self.help.strip()) > 0

    @property
    def description(self):
        return self.help

    @property
    def parent_path(self):
        parentpath, sep, name = self.path.rpartition('_')
        return parentpath

    def set_class(self, cmd_class):
        self.cmd_class = cmd_class

    def get_class(self):
        return self.cmd_class

    def has_subname(self, subname):
        return subname in self.subcommands

    def get_subnames(self):
        return self.subcommands.keys()

    def get_subcommands(self):
        return self.subcommands.values()

    def sublen(self):
        return len(self.subcommands)

    def parse_out(self, args):
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
        print('Path: %s (Name: %s) is_cmd: %s\n\thelp: %s' % (
            self.path,
            self.name,
            self.is_command,
            self.help))
        for cmd in self.get_subcommands():
            cmd.pretty_print(recursive)


class CommandTree(object):

    groups = {}
    _all_commands = {}
    name = None
    description = None

    def __init__(self, name, description=''):
        self.name = name
        self.description = description

    def add_command(self, command_path, description=None, cmd_class=None):
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
        if cmd_class:
            cmd.set_class(cmd_class)
        if description is not None:
            cmd.help = description

    def find_best_match(self, terms):
        """Find a command that best matches a given list of terms

        :param terms: (list of str) match them against paths in cmd_tree

        :returns: (Command, list) the matching command, the remaining terms
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
        self.set_description(tname, tdesc)

    def has_command(self, path):
        return path in self._all_commands

    def get_command(self, path):
        return self._all_commands[path]

    def get_groups(self):
        return self.groups.values()

    def get_group_names(self):
        return self.groups.keys()

    def set_description(self, path, description):
        self._all_commands[path].help = description

    def get_description(self, path):
        return self._all_commands[path].help

    def set_class(self, path, cmd_class):
        self._all_commands[path].set_class(cmd_class)

    def get_class(self, path):
        return self._all_commands[path].get_class()

    def get_subnames(self, path=None):
        if path in (None, ''):
            return self.get_group_names()
        return self._all_commands[path].get_subnames()

    def get_subcommands(self, path=None):
        if path in (None, ''):
            return self.get_groups()
        return self._all_commands[path].get_subcommands()

    def get_parent(self, path):
        if '_' not in path:
            return None
        terms = path.split('_')
        parent_path = '_'.join(terms[:-1])
        return self._all_commands[parent_path]

    def get_closest_ancestor_command(self, path):
        path, sep, name = path.rpartition('_')
        while len(path) > 0:
            cmd = self._all_commands[path]
            if cmd.is_command:
                return cmd
            path, sep, name = path.rpartition('_')
        return None

        if '_' not in path:
            return None
        terms = path.split()[:-1]
        while len(terms) > 0:
            tmp_path = '_'.join(terms)
            cmd = self._all_commands[tmp_path]
            if cmd.is_command:
                return cmd
            terms = terms[:-1]
        raise KeyError('No ancestor commands')

    def pretty_print(self, group=None):
        if group is None:
            for group in self.groups:
                self.pretty_print(group)
        else:
            self.groups[group].pretty_print(recursive=True)
