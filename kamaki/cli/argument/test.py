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

from mock import patch, call
from unittest import TestCase
from StringIO import StringIO
from itertools import product

from kamaki.cli import argument
from kamaki.cli.config import Config


cnf_path = 'kamaki.cli.config.Config'


class Argument(TestCase):

    def test___init__(self):
        self.assertRaises(ValueError, argument.Argument, 'non-integer')
        self.assertRaises(AssertionError, argument.Argument, 1)
        self.assertRaises(AssertionError, argument.Argument, 0, 'noname')
        self.assertRaises(AssertionError, argument.Argument, 0, '--no name')
        self.assertRaises(AssertionError, argument.Argument, 0, ['-n', 'n m'])
        for arity, help, parsed_name, default in (
                (0, 'help 0', '--zero', None),
                (1, 'help 1', ['--one', '-o'], 'lala'),
                (-1, 'help -1', ['--help', '--or', '--more'], 0),
                (0, 'help 0 again', ['--again', ], True)):
            a = argument.Argument(arity, help, parsed_name, default)
            if arity:
                self.assertEqual(arity, a.arity)
            self.assertEqual(help, a.help)

            exp_name = parsed_name if (
                isinstance(parsed_name, list)) else [parsed_name, ]
            self.assertEqual(exp_name, a.parsed_name)

            exp_default = default or (None if arity else False)
            self.assertEqual(exp_default, a.default)

    def test_value(self):
        a = argument.Argument(1, parsed_name='--value')
        for value in (None, '', 0, 0.1, -12, [1, 'a', 2.8], (3, 'lala'), 'pi'):
            a.value = value
            self.assertEqual(value, a.value)

    def test_update_parser(self):
        for i, arity in enumerate((-1, 0, 1)):
            arp = argument.ArgumentParser()
            pname, aname = '--pname%s' % i, 'a_name_%s' % i
            a = argument.Argument(arity, 'args', pname, 42)
            a.update_parser(arp, aname)

            f = StringIO()
            arp.print_usage(file=f), f.seek(0)
            usage, exp = f.readline(), '[%s%s]\n' % (
                pname, (' %s' % aname.upper()) if arity else '')
            self.assertEqual(usage[-len(exp):], exp)
            del arp


class ConfigArgument(TestCase):

    def setUp(self):
        argument._config_arg = argument.ConfigArgument('Recovered Path')

    def test_value(self):
        c = argument._config_arg
        self.assertEqual(c.value, None)
        exp = '/some/random/path'
        c.value = exp
        self.assertTrue(isinstance(c.value, Config))
        self.assertEqual(c.file_path, exp)
        self.assertEqual(c.value.path, exp)

    def test_get(self):
        c = argument._config_arg
        c.value = None
        with patch('%s.get' % cnf_path, return_value='config') as get:
            self.assertEqual(c.value.get('global', 'config_cli'), 'config')
            self.assertEqual(get.mock_calls[-1], call('global', 'config_cli'))

    @patch('%s.keys' % cnf_path, return_value=(
        'image_cli', 'config_cli', 'history_cli', 'file'))
    def test_groups(self, keys):
        c = argument._config_arg
        c.value = None
        cset = set(c.groups)
        self.assertTrue(cset.issuperset(['image', 'config', 'history']))
        self.assertEqual(keys.mock_calls[-1], call('global'))
        self.assertFalse('file' in cset)
        self.assertEqual(keys.mock_calls[-1], call('global'))

    @patch('%s.items' % cnf_path, return_value=(
        ('image_cli', 'image'), ('file', 'pithos'),
        ('config_cli', 'config'), ('history_cli', 'history')))
    def test_cli_specs(self, items):
        c = argument._config_arg
        c.value = None
        cset = set(c.cli_specs)
        self.assertTrue(cset.issuperset([
            ('image', 'image'), ('config', 'config'), ('history', 'history')]))
        self.assertEqual(items.mock_calls[-1], call('global'))
        self.assertFalse(cset.issuperset([('file', 'pithos'), ]))
        self.assertEqual(items.mock_calls[-1], call('global'))

    def test_get_global(self):
        c = argument._config_arg
        c.value = None
        for k, v in (
                ('config_cli', 'config'),
                ('image_cli', 'image'),
                ('history_cli', 'history')):
            with patch('%s.get_global' % cnf_path, return_value=v) as gg:
                self.assertEqual(c.get_global(k), v)
                self.assertEqual(gg.mock_calls[-1], call(k))

    def test_get_cloud(self):
        c = argument._config_arg
        c.value = None
        with patch(
                '%s.get_cloud' % cnf_path,
                return_value='http://cloud') as get_cloud:
            self.assertTrue(len(c.get_cloud('mycloud', 'url')) > 0)
            self.assertEqual(get_cloud.mock_calls[-1],  call('mycloud', 'url'))
        with patch(
                '%s.get_cloud' % cnf_path,
                side_effect=KeyError('no token')) as get_cloud:
            self.assertRaises(KeyError, c.get_cloud, 'mycloud', 'token')
        invalidcloud = 'PLEASE_DO_NOT_EVER_NAME_YOUR_CLOUD_LIKE_THIS111'
        self.assertRaises(KeyError, c.get_cloud, invalidcloud, 'url')


class RuntimeConfigArgument(TestCase):

    def setUp(self):
        argument._config_arg = argument.ConfigArgument('Recovered Path')

    @patch('kamaki.cli.argument.Argument.__init__')
    def test___init__(self, arg):
        config, help, pname, default = 'config', 'help', 'pname', 'default'
        rca = argument.RuntimeConfigArgument(config, help, pname, default)
        self.assertTrue(isinstance(rca, argument.RuntimeConfigArgument))
        self.assertEqual(rca._config_arg, config)
        self.assertEqual(arg.mock_calls[-1], call(1, help, pname, default))

    @patch('%s.override' % cnf_path)
    def test_value(self, override):
        config, help, pname, default = argument._config_arg, 'help', '-n', 'df'
        config.value = None
        rca = argument.RuntimeConfigArgument(config, help, pname, default)
        self.assertEqual(rca.value, default)

        for options in ('grp', 'grp.opt', 'k v', '=nokey', 2.8, None, 42, ''):
            self.assertRaises(TypeError, rca.value, options)

        for options in ('key=val', 'grp.key=val', 'dotted.opt.key=val'):
            rca.value = options
            option, sep, val = options.partition('=')
            grp, sep, key = option.partition('.')
            grp, key = (grp, key) if key else ('global', grp)
            self.assertEqual(override.mock_calls[-1], call(grp, key, val))


class FlagArgument(TestCase):

    @patch('kamaki.cli.argument.Argument.__init__')
    def test___init__(self, arg):
        help, pname, default = 'help', 'pname', 'default'
        fa = argument.FlagArgument(help, pname, default)
        self.assertTrue(isinstance(fa, argument.FlagArgument))
        arg.assert_called_once(0, help, pname, default)


class ValueArgument(TestCase):

    @patch('kamaki.cli.argument.Argument.__init__')
    def test___init__(self, arg):
        help, pname, default = 'help', 'pname', 'default'
        fa = argument.ValueArgument(help, pname, default)
        self.assertTrue(isinstance(fa, argument.ValueArgument))
        arg.assert_called_once(1, help, pname, default)


if __name__ == '__main__':
    from sys import argv
    from kamaki.cli.test import runTestCase
    runTestCase(Argument, 'Argument', argv[1:])
    runTestCase(ConfigArgument, 'ConfigArgument', argv[1:])
    runTestCase(RuntimeConfigArgument, 'RuntimeConfigArgument', argv[1:])
    runTestCase(FlagArgument, 'FlagArgument', argv[1:])
    runTestCase(FlagArgument, 'ValueArgument', argv[1:])
