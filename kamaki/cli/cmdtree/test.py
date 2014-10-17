# Copyright 2013-2014 GRNET S.A. All rights reserved.
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

from unittest import TestCase
from itertools import product

from kamaki.cli import cmdtree


class Command(TestCase):

    def test___init__(self):
        for args in product(
                (None, '', 'cmd'),
                (None, '', 'Some help'),
                (None, '', {}, dict(cmd0a=None, cmd0b=None)),
                (None, cmdtree.Command('cmd_cmd0')),
                (None, 'long description')):
            path, help, subcommands, cmd_class, long_help = args
            try:
                cmd = cmdtree.Command(*args)
            except Exception as e:
                if path:
                    raise
                self.assertTrue(isinstance(e, AssertionError))
                continue
            self.assertEqual(cmd.help, help or '')
            self.assertEqual(cmd.subcommands, subcommands or {})
            self.assertEqual(cmd.cmd_class, cmd_class or None)
            self.assertEqual(cmd.long_help, long_help or '')

    def test_name(self):
        for path in ('cmd', 'cmd_cmd0', 'cmd_cmd0_cmd1', '', None):
            if path:
                cmd = cmdtree.Command(path)
                self.assertEqual(cmd.name, path.split('_')[-1])
            else:
                try:
                    cmdtree.Command(path)
                except Exception as e:
                    self.assertTrue(isinstance(e, AssertionError))

    def test_add_subcmd(self):
        cmd = cmdtree.Command('cmd')
        for subname in (None, 'cmd0', 'cmd_cmd0'):
            if subname:
                subcmd = cmdtree.Command(subname)
                if subname.startswith(cmd.name + '_'):
                    self.assertTrue(cmd.add_subcmd(subcmd))
                    self.assertTrue(subcmd.name in cmd.subcommands)
                else:
                    self.assertFalse(cmd.add_subcmd(subcmd))
                    self.assertTrue(len(cmd.subcommands) == 0)
            else:
                self.assertRaises(AttributeError, cmd.add_subcmd, subname)

    def test_get_subcmd(self):
        cmd = cmdtree.Command('cmd')
        cmd.subcommands = dict(
            cmd0a=cmdtree.Command('cmd_cmd0a', subcommands=dict(
                cmd1=cmdtree.Command('cmd_cmd0a_cmd1'))),
            cmd0b=cmdtree.Command('cmd_cmd0b'))
        for subname in ('', None, 'cmd0a', 'cmd1', 'cmd0b'):
            try:
                expected = cmd.subcommands[subname] if subname else None
            except KeyError:
                expected = None
            self.assertEqual(cmd.get_subcmd(subname), expected)

    def test_contains(self):
        cmd = cmdtree.Command('cmd')
        for subname in ('', 'cmd0'):
            self.assertFalse(cmd.contains(subname))
        cmd.subcommands = dict(
            cmd0a=cmdtree.Command('cmd_cmd0a'),
            cmd0b=cmdtree.Command('cmd_cmd0b'))
        for subname in ('cmd0a', 'cmd0b'):
            self.assertTrue(cmd.contains(subname))
        for subname in ('', 'cmd0c'):
            self.assertFalse(cmd.contains(subname))
        cmd.subcommands['cmd0a'].subcommands = dict(
            cmd1=cmdtree.Command('cmd_cmd0a_cmd1'))
        for subname in ('cmd0a', 'cmd0b'):
            self.assertTrue(cmd.contains(subname))
        for subname in ('', 'cmd0c', 'cmd1', 'cmd0a_cmd1'):
            self.assertFalse(cmd.contains(subname))

    def test_is_command(self):
        cmd = cmdtree.Command('cmd')
        cmd.subcommands = dict(
            itis=cmdtree.Command('cmd_itis', cmd_class=Command),
            itsnot=cmdtree.Command('cmd_itsnot'))
        self.assertFalse(cmd.is_command)
        self.assertTrue(cmd.subcommands['itis'].is_command)
        self.assertFalse(cmd.subcommands['itsnot'].is_command)

    def test_parent_path(self):
        cmd = cmdtree.Command('cmd')
        cmd.subcommands = dict(
            cmd0a=cmdtree.Command('cmd_cmd0a', subcommands=dict(
                cmd1=cmdtree.Command('cmd_cmd0a_cmd1'))),
            cmd0b=cmdtree.Command('cmd_cmd0b'))
        self.assertEqual(cmd.parent_path, '')
        self.assertEqual(cmd.subcommands['cmd0a'].parent_path, cmd.path)
        self.assertEqual(cmd.subcommands['cmd0b'].parent_path, cmd.path)
        cmd0a = cmd.subcommands['cmd0a']
        self.assertEqual(cmd0a.subcommands['cmd1'].parent_path, cmd0a.path)

    def test_parse_out(self):
        cmd = cmdtree.Command('cmd')
        cmd.subcommands = dict(
            cmd0a=cmdtree.Command('cmd_cmd0a', subcommands=dict(
                cmd1=cmdtree.Command('cmd_cmd0a_cmd1'))),
            cmd0b=cmdtree.Command('cmd_cmd0b'))
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

    def _add_commands(self, ctree):
        for cmd in self.commands:
            ctree.add_command(cmd.path, cmd.help, cmd.cmd_class)

    def _commands_are_equal(self, c1, c2):
        self.assertEqual(c1.path, c2.path)
        self.assertEqual(c1.name, c2.name)
        self.assertEqual(c1.cmd_class, c2.cmd_class)
        self.assertEqual(c1.help or '', c2.help or '')

    def setUp(self):
        cmd = cmdtree.Command('cmd', subcommands=dict(
            cmd0a=cmdtree.Command('cmd_cmd0a', subcommands=dict(
                cmd1a=cmdtree.Command(
                    'cmd_cmd0a_cmd1a', subcommands=dict(
                        cmd2=cmdtree.Command(
                            'cmd_cmd0a_cmd1a_cmd2', cmd_class=Command)
                        ),
                ),
                cmd1b=cmdtree.Command(
                    'cmd_cmd0a_cmd1b', subcommands=dict(
                        cmd2=cmdtree.Command(
                            'cmd_cmd0a_cmd1b_cmd2', cmd_class=Command)
                        ),
                )
            )),
            cmd0b=cmdtree.Command('cmd_cmd0b'),
            cmd0c=cmdtree.Command('cmd_cmd0c', subcommands=dict(
                cmd1a=cmdtree.Command('cmd_cmd0c_cmd1a'),
                cmd1b=cmdtree.Command(
                    'cmd_cmd0c_cmd1b', subcommands=dict(
                        cmd2=cmdtree.Command(
                            'cmd_cmd0c_cmd1b_cmd2', cmd_class=Command)
                        ),
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
            cmdtree.Command('othercmd')
        ]

    def tearDown(self):
        for cmd in self.commands:
            del cmd
        del self.commands

    def test___init__(self):
        name, description = 'sampleTree', 'a sample Tree'
        ctree = cmdtree.CommandTree(name)
        for attr, exp in (
                ('groups', {}), ('_all_commands', {}),
                ('name', name), ('description', '')):
            self.assertEqual(getattr(ctree, attr), exp)
        ctree = cmdtree.CommandTree(name, description)
        for attr, exp in (
                ('groups', {}), ('_all_commands', {}),
                ('name', name), ('description', description)):
            self.assertEqual(getattr(ctree, attr), exp)

    def test_exclude(self):
        ctree = cmdtree.CommandTree('excludeTree', 'test exclude group')
        exp = dict()
        for cmd in self.commands[0:6]:
            ctree.groups[cmd.name] = cmd
            exp[cmd.name] = cmd
        self.assertEqual(exp, ctree.groups)
        ctree.exclude(exp.keys()[1::2])
        for key in exp.keys()[1::2]:
            exp.pop(key)
        self.assertEqual(exp, ctree.groups)

    def test_add_command(self):
        ctree = cmdtree.CommandTree('addCommand', 'test add_command')
        self._add_commands(ctree)
        for cmd in self.commands:
            self.assertTrue(cmd, ctree._all_commands)
            if cmd.path.count('_'):
                self.assertFalse(cmd.name in ctree.groups)
            else:
                self.assertTrue(cmd.name in ctree.groups)
                self._commands_are_equal(cmd, ctree.groups[cmd.name])

    def test_find_best_match(self):
        ctree = cmdtree.CommandTree('bestMatch', 'test find_best_match')
        for cmd in self.commands:
            terms = cmd.path.split('_')
            best_match, rest = ctree.find_best_match(terms)
            if len(terms) > 1:
                self.assertEqual(best_match.path, '_'.join(terms[:-1]))
            else:
                self.assertEqual(best_match, None)
            self.assertEqual(rest, terms[-1:])
            ctree.add_command(cmd.path, cmd.help, cmd.cmd_class)
            best_match, rest = ctree.find_best_match(terms)
            self._commands_are_equal(best_match, cmd)
            self.assertEqual(rest, [])

    def test_add_tree(self):
        ctree = cmdtree.CommandTree('tree', 'the main tree')
        ctree1 = cmdtree.CommandTree('tree1', 'the first tree')
        ctree2 = cmdtree.CommandTree('tree2', 'the second tree')

        cmds = list(self.commands)
        del self.commands
        cmds1, cmds2 = cmds[:6], cmds[6:]
        self.commands = cmds1
        self._add_commands(ctree1)
        self.commands = cmds2
        self._add_commands(ctree2)
        self.commands = cmds

        def check_all(
                p1=False, p2=False, p3=False, p4=False, p5=False, p6=False):
            for cmd in cmds[:6]:
                self.assertEquals(cmd.path in ctree._all_commands, p1)
                self.assertEquals(cmd.path in ctree1._all_commands, p2)
                if cmd.path != 'cmd':
                    self.assertEquals(cmd.path in ctree2._all_commands, p3)
            for cmd in cmds[6:]:
                self.assertEquals(cmd.path in ctree._all_commands, p4)
                if cmd.path != 'cmd':
                    self.assertEquals(cmd.path in ctree1._all_commands, p5)
                self.assertEquals(cmd.path in ctree2._all_commands, p6)

        check_all(False, True, False, False, False, True)
        ctree.add_tree(ctree1)
        check_all(True, True, False, False, False, True)
        ctree.add_tree(ctree2)
        check_all(True, True, False, True, False, True)
        ctree2.add_tree(ctree1)
        check_all(True, True, True, True, False, True)

    def test_has_command(self):
        ctree = cmdtree.CommandTree('treeHasCommand', 'test has_command')
        for cmd in self.commands:
            self.assertFalse(ctree.has_command(cmd.path))
        self._add_commands(ctree)
        for cmd in self.commands:
            self.assertTrue(ctree.has_command(cmd.path))
        self.assertFalse(ctree.has_command('NON_EXISTING_COMMAND'))

    def test_get_command(self):
        ctree = cmdtree.CommandTree('treeGetCommand', 'test get_command')
        for cmd in self.commands:
            self.assertRaises(KeyError, ctree.get_command, cmd.path)
        self._add_commands(ctree)
        for cmd in self.commands:
            self._commands_are_equal(ctree.get_command(cmd.path), cmd)
        self.assertRaises(KeyError, ctree.get_command, 'NON_EXISTNG_COMMAND')

    def test_subnames(self):
        ctree = cmdtree.CommandTree('treeSubnames', 'test subnames')
        self.assertEqual(ctree.subnames(), [])
        self.assertRaises(KeyError, ctree.subnames, 'cmd')
        self._add_commands(ctree)
        for l1, l2 in (
                (ctree.subnames(), ['cmd', 'othercmd']),
                (ctree.subnames('cmd'), ['cmd0a', 'cmd0b', 'cmd0c']),
                (ctree.subnames('cmd_cmd0a'), ['cmd1a', 'cmd1b']),
                (ctree.subnames('cmd_cmd0a_cmd1a'), ['cmd2', ]),
                (ctree.subnames('cmd_cmd0a_cmd1b'), ['cmd2', ]),
                (ctree.subnames('cmd_cmd0a_cmd1a_cmd2'), []),
                (ctree.subnames('cmd_cmd0a_cmd1b_cmd2'), []),
                (ctree.subnames('cmd_cmd0b'), []),
                (ctree.subnames('cmd_cmd0c'), ['cmd1a', 'cmd1b']),
                (ctree.subnames('cmd_cmd0c_cmd1a'), []),
                (ctree.subnames('cmd_cmd0c_cmd1b'), ['cmd2', ]),
                (ctree.subnames('cmd_cmd0c_cmd1b_cmd2'), []),
                (ctree.subnames('othercmd'), [])):
            l1.sort(), l2.sort(), self.assertEqual(l1, l2)
        self.assertRaises(KeyError, ctree.subnames, 'NON_EXISTNG_CMD')

    def test_get_subcommands(self):
        ctree = cmdtree.CommandTree('treeSub', 'test get_subcommands')
        self.assertEqual(ctree.get_subcommands(), [])
        self.assertRaises(KeyError, ctree.get_subcommands, 'cmd')
        self._add_commands(ctree)
        for s1, l2 in (
                ('', ['cmd', 'othercmd']),
                ('cmd', ['cmd0a', 'cmd0b', 'cmd0c']),
                ('cmd_cmd0a', ['cmd1a', 'cmd1b']),
                ('cmd_cmd0a_cmd1a', ['cmd2', ]),
                ('cmd_cmd0a_cmd1b', ['cmd2', ]),
                ('cmd_cmd0a_cmd1a_cmd2', []),
                ('cmd_cmd0a_cmd1b_cmd2', []),
                ('cmd_cmd0b', []),
                ('cmd_cmd0c', ['cmd1a', 'cmd1b']),
                ('cmd_cmd0c_cmd1a', []),
                ('cmd_cmd0c_cmd1b', ['cmd2', ]),
                ('cmd_cmd0c_cmd1b_cmd2', []),
                ('othercmd', [])):
            l1 = [cmd.path for cmd in ctree.get_subcommands(s1)]
            l2 = ['_'.join([s1, i]) for i in l2] if s1 else l2
            l1.sort(), l2.sort(), self.assertEqual(l1, l2)
        self.assertRaises(KeyError, ctree.get_subcommands, 'NON_EXISTNG_CMD')


if __name__ == '__main__':
    from sys import argv
    from kamaki.cli.test import runTestCase
    runTestCase(Command, 'Command', argv[1:])
    runTestCase(CommandTree, 'CommandTree', argv[1:])
