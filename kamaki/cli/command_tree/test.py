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

    def setUp(self):
        pass

    def tearDown(self):
        pass

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


if __name__ == '__main__':
    from sys import argv
    from kamaki.cli.test import runTestCase
    runTestCase(Command, 'Command', argv[1:])
