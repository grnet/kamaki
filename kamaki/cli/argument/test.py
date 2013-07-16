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
#from itertools import product

from kamaki.cli import argument


class Argument(TestCase):

    def test___init__(self):
        self.assertRaises(ValueError, argument.Argument, 'non-integer')
        self.assertRaises(AssertionError, argument.Argument, 1)
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


if __name__ == '__main__':
    from sys import argv
    from kamaki.cli.test import runTestCase
    runTestCase(Argument, 'Argument', argv[1:])
