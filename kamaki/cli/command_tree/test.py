# Copyright 2013 GRNET S.A. All rights reserved.
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

#from mock import patch, call
from unittest import TestCase
from itertools import product

from kamaki.cli import command_tree


class Command(TestCase):

    def test___init__(self):
        for args in product(
                (None, '', 'cmd'),
                (None, '', 'Some help'),
                (None, '', {}, dict(cmd0a=None, cmd0b=None)),
                (None, command_tree.Command('cmd_cmd0'))):
            path, help, subcommands, cmd_class = args
            try:
                cmd = command_tree.Command(*args)
            except Exception as e:
                if path:
                    raise
                self.assertTrue(isinstance(e, AssertionError))
                continue
            self.assertEqual(cmd.help, help or '')
            self.assertEqual(cmd.subcommands, subcommands or {})
            self.assertEqual(cmd.cmd_class, cmd_class or None)

    def test_name(self):
        for path in ('cmd', 'cmd_cmd0', 'cmd_cmd0_cmd1', '', None):
            if path:
                cmd = command_tree.Command(path)
                self.assertEqual(cmd.name, path.split('_')[-1])
            else:
                try:
                    command_tree.Command(path)
                except Exception as e:
                    self.assertTrue(isinstance(e, AssertionError))

    def test_add_subcmd(self):
        cmd = command_tree.Command('cmd')
        for subname in (None, 'cmd0', 'cmd_cmd0'):
            if subname:
                subcmd = command_tree.Command(subname)
                if subname.startswith(cmd.name + '_'):
                    self.assertTrue(cmd.add_subcmd(subcmd))
                    self.assertTrue(subcmd.name in cmd.subcommands)
                else:
                    self.assertFalse(cmd.add_subcmd(subcmd))
                    self.assertTrue(len(cmd.subcommands) == 0)
            else:
                self.assertRaises(cmd.add_subcmd, subname, AttributeError)

    def test_get_subcmd(self):
        cmd = command_tree.Command('cmd')
        cmd.subcommands = dict(
            cmd0a=command_tree.Command('cmd_cmd0a', subcommands=dict(
                cmd1=command_tree.Command('cmd_cmd0a_cmd1'))),
            cmd0b=command_tree.Command('cmd_cmd0b'))
        for subname in ('', None, 'cmd0a', 'cmd1', 'cmd0b'):
            try:
                expected = cmd.subcommands[subname] if subname else None
            except KeyError:
                expected = None
            self.assertEqual(cmd.get_subcmd(subname), expected)

    def test_contains(self):
        cmd = command_tree.Command('cmd')
        for subname in ('', 'cmd0'):
            self.assertFalse(cmd.contains(subname))
        cmd.subcommands = dict(
            cmd0a=command_tree.Command('cmd_cmd0a'),
            cmd0b=command_tree.Command('cmd_cmd0b'))
        for subname in ('cmd0a', 'cmd0b'):
            self.assertTrue(cmd.contains(subname))
        for subname in ('', 'cmd0c'):
            self.assertFalse(cmd.contains(subname))
        cmd.subcommands['cmd0a'].subcommands = dict(
            cmd1=command_tree.Command('cmd_cmd0a_cmd1'))
        for subname in ('cmd0a', 'cmd0b'):
            self.assertTrue(cmd.contains(subname))
        for subname in ('', 'cmd0c', 'cmd1', 'cmd0a_cmd1'):
            self.assertFalse(cmd.contains(subname))

    def test_is_command(self):
        cmd = command_tree.Command('cmd')
        cmd.subcommands = dict(
            itis=command_tree.Command('cmd_itis', cmd_class=Command),
            itsnot=command_tree.Command('cmd_itsnot'))
        self.assertFalse(cmd.is_command)
        self.assertTrue(cmd.subcommands['itis'].is_command)
        self.assertFalse(cmd.subcommands['itsnot'].is_command)

    def test_parent_path(self):
        cmd = command_tree.Command('cmd')
        cmd.subcommands = dict(
            cmd0a=command_tree.Command('cmd_cmd0a', subcommands=dict(
                cmd1=command_tree.Command('cmd_cmd0a_cmd1'))),
            cmd0b=command_tree.Command('cmd_cmd0b'))
        self.assertEqual(cmd.parent_path, '')
        self.assertEqual(cmd.subcommands['cmd0a'].parent_path, cmd.path)
        self.assertEqual(cmd.subcommands['cmd0b'].parent_path, cmd.path)
        cmd0a = cmd.subcommands['cmd0a']
        self.assertEqual(cmd0a.subcommands['cmd1'].parent_path, cmd0a.path)

    def test_parse_out(self):
        cmd = command_tree.Command('cmd')
        cmd.subcommands = dict(
            cmd0a=command_tree.Command('cmd_cmd0a', subcommands=dict(
                cmd1=command_tree.Command('cmd_cmd0a_cmd1'))),
            cmd0b=command_tree.Command('cmd_cmd0b'))
        for invalids in (None, 42, 0.88):
            self.assertRaises(TypeError, cmd.parse_out, invalids)
        for c, l, expc, expl in (
                (cmd, ['cmd'], cmd, ['cmd']),
                (cmd, ['XXX'], cmd, ['XXX']),
                (cmd, ['cmd0a'], cmd.subcommands['cmd0a'], []),
                (cmd, ['XXX', 'cmd0a'], cmd, ['XXX', 'cmd0a']),
                (cmd, ['cmd0a', 'XXX'], cmd.subcommands['cmd0a'], ['XXX']),
                (cmd, ['cmd0a', 'cmd0b'], cmd.subcommands['cmd0a'], ['cmd0b']),
                (cmd, ['cmd0b', 'XXX'], cmd.subcommands['cmd0b'], ['XXX']),
                (
                    cmd, ['cmd0a', 'cmd1'],
                    cmd.subcommands['cmd0a'].subcommands['cmd1'], []),
                (
                    cmd, ['cmd0a', 'cmd1', 'XXX'],
                    cmd.subcommands['cmd0a'].subcommands['cmd1'], ['XXX']),
                (
                    cmd, ['cmd0a', 'XXX', 'cmd1'],
                    cmd.subcommands['cmd0a'], ['XXX', 'cmd1'])):
            self.assertEqual((expc, expl), c.parse_out(l))


class CommandTree(TestCase):

    def setUp(self):
        cmd = command_tree.Command('cmd', subcommands=dict(
            cmd0a=command_tree.Command('cmd_cmd0a', subcommands=dict(
                cmd1a=command_tree.Command(
                    'cmd_cmd0a_cmd1a', subcommands=dict(
                        cmd2=command_tree.Command('cmd_cmd0a_cmd1a_cmd2'),
                    )
                ),
                cmd1b=command_tree.Command(
                    'cmd_cmd0a_cmd1b', subcommands=dict(
                        cmd2=command_tree.Command('cmd_cmd0a_cmd1b_cmd2'),
                    )
                )
            )),
            cmd0b=command_tree.Command('cmd_cmd0b'),
            cmd0c=command_tree.Command('cmd_cmd0c', subcommands=dict(
                cmd1a=command_tree.Command('cmd_cmd0c_cmd1a'),
                cmd1b=command_tree.Command(
                    'cmd_cmd0c_cmd1b', subcommands=dict(
                        cmd2=command_tree.Command('cmd_cmd0c_cmd1b_cmd2'),
                    )
                )
            ))
        ))
        self.commands = [
            cmd,
            cmd.subcommands['cmd0a'],
            cmd.subcommands['cmd0a'].subcommands['cmd1a'],
            cmd.subcommands['cmd0a'].subcommands['cmd1a'].subcommands['cmd2'],
            cmd.subcommands['cmd0a'].subcommands['cmd1b'],
            cmd.subcommands['cmd0a'].subcommands['cmd1b'].subcommands['cmd2'],
            cmd.subcommands['cmd0b'],
            cmd.subcommands['cmd0c'],
            cmd.subcommands['cmd0c'].subcommands['cmd1a'],
            cmd.subcommands['cmd0c'].subcommands['cmd1b'],
            cmd.subcommands['cmd0c'].subcommands['cmd1b'].subcommands['cmd2'],
        ]

    def tearDown(self):
        for cmd in self.commands:
            del cmd
        del self.commands

    def test___init__(self):
        ctree = command_tree.CommandTree('sampleTree', 'a sample Tree')
        ctree.pretty_print()


if __name__ == '__main__':
    from sys import argv
    from kamaki.cli.test import runTestCase
    runTestCase(Command, 'Command', argv[1:])
    runTestCase(CommandTree, 'CommandTree', argv[1:])
