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
from StringIO import StringIO
from sys import stdin, stdout
#from itertools import product

from kamaki.cli import argument
from kamaki.cli.config import Config


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

    #  A cloud name in config with a URL but no TOKEN
    SEMI_CLOUD = 'production'

    # A cloud name that is not configured in config
    INVALID_CLOUD = 'QWERTY_123456'

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
        self.assertEqual(c.value.get('global', 'config_cli'), 'config')

    def test_groups(self):
        c = argument._config_arg
        c.value = None
        self.assertTrue(set(c.groups).issuperset([
            'image', 'config', 'history']))

    def test_cli_specs(self):
        c = argument._config_arg
        c.value = None
        self.assertTrue(set(c.cli_specs).issuperset([
            ('image', 'image'), ('config', 'config'), ('history', 'history')]))

    def test_get_global(self):
        c = argument._config_arg
        c.value = None
        for k, v in (
                ('config_cli', 'config'),
                ('image_cli', 'image'),
                ('history_cli', 'history')):
            self.assertEqual(c.get_global(k), v)

    def test_get_cloud(self):
        """test_get_cloud (!! hard-set SEMI/INVALID_CLOUD to run this !!)"""
        c = argument._config_arg
        c.value = None
        if not self.SEMI_CLOUD:
            stdout.write(
                '\n\tA cloud name set in config file with URL but no TOKEN: ')
            self.SEMI_CLOUD = stdin.readline()[:-1]
        self.assertTrue(len(c.get_cloud(self.SEMI_CLOUD, 'url')) > 0)
        self.assertRaises(KeyError, c.get_cloud, self.SEMI_CLOUD, 'token')

        if not self.INVALID_CLOUD:
            stdout.write('\tok\n\tA cloud name NOT in your config file: ')
            self.INVALID_CLOUD = stdin.readline()[:-1]
        self.assertRaises(KeyError, c.get_cloud, self.INVALID_CLOUD, 'url')


if __name__ == '__main__':
    from sys import argv
    from kamaki.cli.test import runTestCase
    runTestCase(Argument, 'Argument', argv[1:])
    runTestCase(ConfigArgument, 'ConfigArgument', argv[1:])
